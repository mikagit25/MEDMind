"""Clinical simulation — branching cases (FSM) and AI virtual patient."""
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.models import ClinicalCase, ClinicalCaseSession, User

router = APIRouter(tags=["simulation"])

_claude = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=30.0)


# ── FSM Case Sessions ─────────────────────────────────────────────────────────

class StepResponse(BaseModel):
    session_id: UUID
    step: Dict[str, Any]
    score: int
    status: str
    feedback: Optional[str] = None


@router.post("/cases/{case_id}/sessions", status_code=201)
async def start_case_session(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Start a new FSM session for a branching clinical case."""
    case = (await db.execute(select(ClinicalCase).where(ClinicalCase.id == case_id))).scalar_one_or_none()
    if not case:
        raise HTTPException(404, "Case not found")

    # If case has no FSM steps, it's a legacy static case
    if not case.steps:
        raise HTTPException(422, "This case does not have branching steps. Use the standard case endpoint.")

    # Find the initial step
    steps = case.steps if isinstance(case.steps, list) else []
    initial_id = case.initial_step_id or (steps[0]["id"] if steps else None)
    if not initial_id:
        raise HTTPException(422, "Case has no initial step defined")

    initial_step = next((s for s in steps if s["id"] == initial_id), None)
    if not initial_step:
        raise HTTPException(500, "Initial step not found in case steps")

    session = ClinicalCaseSession(
        case_id=case_id,
        user_id=user.id,
        current_step_id=initial_id,
        path_taken=[],
        score=0,
        status="in_progress",
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return {
        "session_id": str(session.id),
        "case_title": case.title,
        "current_step": initial_step,
        "score": 0,
        "status": "in_progress",
    }


@router.post("/cases/sessions/{session_id}/choose")
async def make_step_choice(
    session_id: UUID,
    choice_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Submit a choice for the current step and advance the FSM."""
    session = (await db.execute(
        select(ClinicalCaseSession).where(
            ClinicalCaseSession.id == session_id,
            ClinicalCaseSession.user_id == user.id,
        )
    )).scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Session not found")
    if session.status != "in_progress":
        raise HTTPException(400, f"Session is already '{session.status}'")

    case = (await db.execute(select(ClinicalCase).where(ClinicalCase.id == session.case_id))).scalar_one()
    steps = case.steps if isinstance(case.steps, list) else []
    current = next((s for s in steps if s["id"] == session.current_step_id), None)
    if not current:
        raise HTTPException(500, "Current step not found")

    choices = current.get("choices", [])
    chosen = next((c for c in choices if c["id"] == choice_id), None)
    if not chosen:
        raise HTTPException(400, f"Choice '{choice_id}' not valid for current step")

    # Record path
    path = list(session.path_taken or [])
    path.append({
        "step_id": session.current_step_id,
        "choice_id": choice_id,
        "timestamp": datetime.utcnow().isoformat(),
    })

    # Update score
    score_delta = chosen.get("score_delta", 0)
    new_score = max(0, min(case.max_score or 100, (session.score or 0) + score_delta))

    next_step_id = chosen.get("next_step")
    next_step = next((s for s in steps if s["id"] == next_step_id), None) if next_step_id else None

    if not next_step:
        # End of case
        session.status = "completed"
        session.completed_at = datetime.utcnow()
        session.path_taken = path
        session.score = new_score
        await db.commit()

        # Generate AI debrief asynchronously
        import asyncio
        asyncio.create_task(_generate_debrief(session.id, case, path, new_score))

        return {
            "status": "completed",
            "score": new_score,
            "max_score": case.max_score or 100,
            "outcome": chosen.get("outcome", ""),
            "debrief_pending": True,
            "message": "Case complete! Debrief is being generated.",
        }

    session.current_step_id = next_step_id
    session.path_taken = path
    session.score = new_score
    await db.commit()

    return {
        "status": "in_progress",
        "score": new_score,
        "outcome": chosen.get("outcome", ""),
        "next_step": next_step,
    }


@router.get("/cases/sessions/{session_id}")
async def get_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get current session state including debrief if completed."""
    session = (await db.execute(
        select(ClinicalCaseSession).where(
            ClinicalCaseSession.id == session_id,
            ClinicalCaseSession.user_id == user.id,
        )
    )).scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Session not found")

    case = (await db.execute(select(ClinicalCase).where(ClinicalCase.id == session.case_id))).scalar_one()

    return {
        "session_id": str(session.id),
        "case_title": case.title,
        "current_step_id": session.current_step_id,
        "path_taken": session.path_taken,
        "score": session.score,
        "max_score": case.max_score or 100,
        "status": session.status,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "debriefing": session.debriefing,
    }


async def _generate_debrief(session_id: UUID, case: ClinicalCase, path: list, score: int) -> None:
    """Background task: generate AI debrief comparing student path to ideal path."""
    from app.core.database import AsyncSessionLocal

    ideal = case.ideal_path or []
    student_steps = [p["step_id"] for p in path]
    missed = [s for s in ideal if s not in student_steps]
    extra = [s for s in student_steps if s not in ideal]

    prompt = (
        f"Clinical case: {case.title}\n"
        f"Ideal diagnostic/treatment path: {ideal}\n"
        f"Student's path: {student_steps}\n"
        f"Score: {score}/{case.max_score or 100}\n"
        f"Steps missed vs ideal: {missed}\n"
        f"Extra steps taken: {extra}\n\n"
        "Generate a concise clinical debrief (3-5 bullet points) comparing the student's "
        "decisions to the optimal approach. Be specific about what they did well and what "
        "they should reconsider. Focus on clinical reasoning, not just steps."
    )

    try:
        message = await _claude.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        debrief_text = message.content[0].text

        async with AsyncSessionLocal() as db:
            session = await db.get(ClinicalCaseSession, session_id)
            if session:
                session.debriefing = {
                    "text": debrief_text,
                    "ideal_path": ideal,
                    "student_path": student_steps,
                    "missed_steps": missed,
                    "score": score,
                    "generated_at": datetime.utcnow().isoformat(),
                }
                await db.commit()
    except Exception:
        pass  # debrief is non-critical


# ── Virtual Patient ───────────────────────────────────────────────────────────

class VirtualPatientStart(BaseModel):
    specialty: str = "internal_medicine"
    difficulty: str = "intermediate"   # beginner | intermediate | advanced
    species: str = "human"             # human | canine | feline | equine
    # Optional seed — if omitted, AI generates a random patient
    patient_seed: Optional[str] = None  # e.g. "65yo diabetic with foot pain"


class VirtualPatientMessage(BaseModel):
    session_token: str   # returned by /start
    message: str         # student's question to the patient


@router.post("/ai/virtual-patient/start")
async def start_virtual_patient(
    data: VirtualPatientStart,
    user: User = Depends(get_current_user),
):
    """
    Start a virtual patient simulation session.

    Returns a session_token and the patient's opening statement.
    The student then sends questions via /ai/virtual-patient/chat.
    """
    import secrets
    import json

    # Build patient card prompt
    seed_line = f"Patient profile: {data.patient_seed}" if data.patient_seed else ""
    species_note = "" if data.species == "human" else f"This is a {data.species} patient (veterinary case)."

    system_prompt = (
        f"You are playing the role of a medical patient in an educational simulation. {species_note}\n"
        f"Specialty context: {data.specialty}. Difficulty: {data.difficulty}.\n"
        f"{seed_line}\n\n"
        "RULES:\n"
        "1. Stay in character as the patient at all times.\n"
        "2. Only reveal information when the student asks the right questions.\n"
        "3. Use lay terms (not medical jargon) — patients don't know medical terminology.\n"
        "4. For beginner difficulty: give clear, direct answers.\n"
        "   For intermediate: occasionally mention irrelevant symptoms to test differential.\n"
        "   For advanced: be vague, anxious, and omit key details unless specifically probed.\n"
        "5. Keep a hidden 'patient card' in your mind with: chief complaint, history, key findings, diagnosis.\n"
        "6. Never reveal the diagnosis directly.\n"
        "7. If asked something the patient wouldn't know, say so naturally.\n\n"
        "Start by greeting the student/doctor and stating your chief complaint in 1-2 sentences."
    )

    try:
        message = await _claude.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=system_prompt,
            messages=[{"role": "user", "content": "Hello, I'm your doctor today. What brings you in?"}],
        )
        opening = message.content[0].text
    except Exception as e:
        raise HTTPException(502, f"AI service error: {e}")

    # Encode session context as a signed token (simple JSON for now — no secrets needed since it's educational)
    import base64
    session_data = {
        "system_prompt": system_prompt,
        "specialty": data.specialty,
        "difficulty": data.difficulty,
        "species": data.species,
        "history": [
            {"role": "user", "content": "Hello, I'm your doctor today. What brings you in?"},
            {"role": "assistant", "content": opening},
        ],
        "started_at": datetime.utcnow().isoformat(),
    }
    token = base64.b64encode(json.dumps(session_data).encode()).decode()

    return {
        "session_token": token,
        "patient_opening": opening,
        "instructions": (
            "Ask the patient questions to gather history. "
            "When ready, call POST /ai/virtual-patient/evaluate to get your assessment graded."
        ),
    }


@router.post("/ai/virtual-patient/chat")
async def chat_with_virtual_patient(
    data: VirtualPatientMessage,
    user: User = Depends(get_current_user),
):
    """Send a question/statement to the virtual patient and get their response."""
    import base64
    import json as _json

    try:
        session_data = _json.loads(base64.b64decode(data.session_token).decode())
    except Exception:
        raise HTTPException(400, "Invalid session token")

    history = session_data.get("history", [])
    history.append({"role": "user", "content": data.message})

    try:
        message = await _claude.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            system=session_data["system_prompt"],
            messages=history[-20:],  # keep last 20 turns
        )
        reply = message.content[0].text
    except Exception as e:
        raise HTTPException(502, f"AI service error: {e}")

    history.append({"role": "assistant", "content": reply})

    # Update token with new history
    session_data["history"] = history
    new_token = base64.b64encode(_json.dumps(session_data).encode()).decode()

    return {
        "patient_response": reply,
        "session_token": new_token,
        "turns": len([m for m in history if m["role"] == "user"]),
    }


@router.post("/ai/virtual-patient/evaluate")
async def evaluate_virtual_patient_session(
    data: VirtualPatientMessage,  # reuse schema — session_token + student's self-assessment
    user: User = Depends(get_current_user),
):
    """
    End the virtual patient session and get AI evaluation of the student's history-taking.
    The `message` field should be the student's working diagnosis and reasoning.
    """
    import base64
    import json as _json

    try:
        session_data = _json.loads(base64.b64decode(data.session_token).decode())
    except Exception:
        raise HTTPException(400, "Invalid session token")

    history = session_data.get("history", [])
    conversation_text = "\n".join(
        f"{'Student' if m['role'] == 'user' else 'Patient'}: {m['content']}"
        for m in history
    )

    eval_prompt = (
        f"You are a medical education evaluator. A student just completed a virtual patient interview.\n\n"
        f"CONVERSATION:\n{conversation_text}\n\n"
        f"STUDENT'S DIAGNOSIS/REASONING: {data.message}\n\n"
        "Evaluate the student's history-taking and diagnostic reasoning:\n"
        "1. **Key questions asked** — which important questions did they cover?\n"
        "2. **Missed questions** — what should they have asked but didn't?\n"
        "3. **Diagnostic reasoning** — is their working diagnosis reasonable given the history?\n"
        "4. **Score** — give a score out of 100 with brief justification.\n"
        "5. **Top 3 learning points** — what should they do differently next time?\n\n"
        "Format your response as structured markdown."
    )

    try:
        message = await _claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            messages=[{"role": "user", "content": eval_prompt}],
        )
        evaluation = message.content[0].text
    except Exception as e:
        raise HTTPException(502, f"AI service error: {e}")

    return {
        "evaluation": evaluation,
        "turns_taken": len([m for m in history if m["role"] == "user"]),
        "specialty": session_data.get("specialty"),
        "difficulty": session_data.get("difficulty"),
    }
