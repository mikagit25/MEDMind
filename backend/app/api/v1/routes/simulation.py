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

    case = (await db.execute(select(ClinicalCase).where(ClinicalCase.id == session.case_id))).scalar_one_or_none()
    if not case:
        raise HTTPException(404, "Clinical case not found")
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

    case = (await db.execute(select(ClinicalCase).where(ClinicalCase.id == session.case_id))).scalar_one_or_none()
    if not case:
        raise HTTPException(404, "Clinical case not found")

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

    # Species-specific physiology and role context
    SPECIES_PHYSIOLOGY: dict[str, dict] = {
        "canine": {
            "normal_vitals": "HR 60-140 bpm, RR 10-30/min, temp 38.3-39.2°C, BP ~120/80 mmHg",
            "key_diseases": "parvovirus, pyometra, Addison's, hypothyroidism, cruciate rupture, pancreatitis",
            "narrator_role": "dog owner",
            "narrator_intro": "I've brought my dog in today.",
            "symptom_style": "describe symptoms as an owner: 'he's not eating', 'she's been vomiting', 'he's limping on the back leg'",
            "breed_note": "Mention breed if relevant — e.g., Labradors prone to obesity/cruciate, Collies may have MDR1 mutation.",
        },
        "feline": {
            "normal_vitals": "HR 140-220 bpm, RR 15-30/min, temp 38.1-39.2°C",
            "key_diseases": "CKD, hyperthyroidism, FIP, HCM, feline asthma, FLUTD, diabetes",
            "narrator_role": "cat owner",
            "narrator_intro": "I've brought my cat in today.",
            "symptom_style": "describe symptoms as an owner: 'she's drinking more water', 'he stopped grooming', 'she's hiding under the bed'",
            "breed_note": "Persian/Ragdoll prone to PKD; Burmese to diabetes; all cats at risk from paracetamol/permethrin.",
        },
        "equine": {
            "normal_vitals": "HR 28-44 bpm, RR 8-16/min, temp 37.5-38.5°C, gut sounds in all 4 quadrants",
            "key_diseases": "colic (medical vs surgical), laminitis, strangles, equine influenza, PPID (Cushing's), gastric ulcers",
            "narrator_role": "horse trainer or owner",
            "narrator_intro": "I've called you out to see one of my horses.",
            "symptom_style": "describe as a trainer: 'he's been pawing at the ground', 'she's off her feed', 'he's been rolling and won't get up', 'reduced gut sounds on the right'",
            "breed_note": "Warmbloods prone to OCD; Arabians to HYPP; ponies to laminitis/metabolic disease.",
        },
        "bovine": {
            "normal_vitals": "HR 40-80 bpm, RR 12-36/min, temp 38.5-39.5°C, rumen contractions 1-2/min",
            "key_diseases": "milk fever (hypocalcaemia), ketosis, LDA, mastitis, BVD, respiratory disease, foot rot",
            "narrator_role": "farmer",
            "narrator_intro": "One of my cows is unwell.",
            "symptom_style": "describe as a farmer: 'she went off her milk', 'she's down and can't get up', 'reduced rumen motility', 'the udder is hard and hot'",
            "breed_note": "Dairy herds: watch for production diseases postpartum (milk fever, ketosis, LDA).",
        },
    }

    physio = SPECIES_PHYSIOLOGY.get(data.species, {})

    # Build patient card prompt
    seed_line = f"Patient profile: {data.patient_seed}" if data.patient_seed else ""

    if data.species == "human":
        role_block = (
            "You are playing the role of a human patient.\n"
            "Use lay terms (not medical jargon). Respond as a real patient would.\n"
        )
        opening_cue = "Hello, I'm your doctor today. What brings you in?"
    else:
        role_block = (
            f"You are playing the role of a {physio.get('narrator_role', 'animal owner')} "
            f"presenting an animal to a veterinary student.\n"
            f"{physio.get('narrator_intro', '')}\n"
            f"Describe symptoms as an owner/farmer would: {physio.get('symptom_style', '')}\n"
            f"Normal vitals for reference (know these but don't volunteer them): {physio.get('normal_vitals', '')}\n"
            f"Relevant diseases for this species: {physio.get('key_diseases', '')}\n"
            f"{physio.get('breed_note', '')}\n"
        )
        opening_cue = f"Hello, I'm the vet student on duty today. {physio.get('narrator_intro', 'What seems to be the problem?')}"

    system_prompt = (
        f"{role_block}\n"
        f"Specialty context: {data.specialty}. Difficulty: {data.difficulty}.\n"
        f"{seed_line}\n\n"
        "RULES:\n"
        "1. Stay in character at all times.\n"
        "2. Only reveal information when the student asks the right questions.\n"
        "3. Keep a hidden 'patient card': chief complaint, history, key findings, diagnosis.\n"
        "4. Never reveal the diagnosis directly.\n"
        "5. For beginner: give clear, direct answers.\n"
        "   For intermediate: occasionally mention irrelevant symptoms to test differential.\n"
        "   For advanced: be vague, omit key details unless specifically probed.\n"
        "6. If asked something the owner/patient wouldn't know, say so naturally.\n\n"
        "Start with your opening statement in 1-2 sentences."
    )

    try:
        message = await _claude.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=system_prompt,
            messages=[{"role": "user", "content": opening_cue}],
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
            {"role": "user", "content": opening_cue},
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
