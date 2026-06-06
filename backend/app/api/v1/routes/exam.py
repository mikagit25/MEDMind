"""Board Exam Prep Mode.

Timed exam sessions simulating USMLE / NCLEX / UKMLA style exams.
Sessions pull MCQ questions from the DB, apply a timer, score, and analyze weak areas.

Endpoints
─────────
GET  /exam/modes                   — list available exam modes (USMLE, NCLEX, etc.)
POST /exam/sessions                — create a timed session
GET  /exam/sessions/{id}           — get session with questions (no answers revealed)
POST /exam/sessions/{id}/answer    — submit answer for a question
POST /exam/sessions/{id}/submit    — finalize session (time up or done)
GET  /exam/sessions/{id}/results   — results + weak area breakdown
GET  /exam/history                 — past sessions summary
"""
import uuid as uuid_lib
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import User

router = APIRouter(prefix="/exam", tags=["exam"])

# ── Exam mode definitions ──────────────────────────────────────────────────

EXAM_MODES = [
    {
        "id": "usmle_step1",
        "name": "USMLE Step 1",
        "description": "Basic sciences — 40 questions, 60 min",
        "questions": 40,
        "duration_min": 60,
        "specialty_filter": None,
        "difficulty": "hard",
        "icon": "🩺",
        "price_usd": None,  # included in Pro+
    },
    {
        "id": "usmle_step2",
        "name": "USMLE Step 2 CK",
        "description": "Clinical knowledge — 40 questions, 60 min",
        "questions": 40,
        "duration_min": 60,
        "specialty_filter": None,
        "difficulty": "hard",
        "icon": "🏥",
        "price_usd": None,
    },
    {
        "id": "nclex_rn",
        "name": "NCLEX-RN",
        "description": "Nursing licensure — 30 questions, 45 min",
        "questions": 30,
        "duration_min": 45,
        "specialty_filter": None,
        "difficulty": "medium",
        "icon": "👩‍⚕️",
        "price_usd": None,
    },
    {
        "id": "ukmla",
        "name": "UKMLA / MLA",
        "description": "UK licensing — 30 questions, 45 min",
        "questions": 30,
        "duration_min": 45,
        "specialty_filter": None,
        "difficulty": "medium",
        "icon": "🇬🇧",
        "price_usd": None,
    },
    {
        "id": "quick_20",
        "name": "Quick Practice",
        "description": "20 mixed questions, 20 min — any level",
        "questions": 20,
        "duration_min": 20,
        "specialty_filter": None,
        "difficulty": None,
        "icon": "⚡",
        "price_usd": None,
    },
]

# In-memory session store (for MVP — use Redis/DB in production)
_sessions: dict = {}


# ── Schemas ────────────────────────────────────────────────────────────────

class StartSession(BaseModel):
    mode_id: str
    specialty_filter: Optional[str] = None


class AnswerBody(BaseModel):
    question_index: int
    selected_option: str


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/modes")
async def list_modes(user: User = Depends(get_current_user)):
    """Return available exam modes."""
    available = []
    for m in EXAM_MODES:
        available.append({
            **m,
            "locked": user.subscription_tier == "free",
            "lock_reason": "Pro subscription required" if user.subscription_tier == "free" else None,
        })
    return available


@router.post("/sessions", status_code=201)
async def create_session(
    body: StartSession,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new timed exam session."""
    if user.subscription_tier == "free":
        raise HTTPException(403, "Board Exam mode requires a Pro subscription. Upgrade to unlock.")

    mode = next((m for m in EXAM_MODES if m["id"] == body.mode_id), None)
    if not mode:
        raise HTTPException(404, f"Unknown exam mode: {body.mode_id}")

    # Pull MCQ questions from DB
    from app.models.models import MCQQuestion
    q = select(MCQQuestion)
    if mode["difficulty"]:
        q = q.where(MCQQuestion.difficulty == mode["difficulty"])
    q = q.order_by(func.random()).limit(mode["questions"])
    mcqs = (await db.execute(q)).scalars().all()

    if len(mcqs) < 5:
        raise HTTPException(503, "Not enough questions available for this exam mode yet. Check back soon.")

    session_id = str(uuid_lib.uuid4())
    questions = [
        {
            "index": i,
            "id": str(mcq.id),
            "question": mcq.question,
            "options": mcq.options if isinstance(mcq.options, dict) else {},
            "module_id": str(mcq.module_id) if mcq.module_id else None,
            "_correct": mcq.correct_option,  # hidden, not sent to client
        }
        for i, mcq in enumerate(mcqs)
    ]

    _sessions[session_id] = {
        "id": session_id,
        "user_id": str(user.id),
        "mode_id": body.mode_id,
        "mode_name": mode["name"],
        "questions": questions,
        "answers": {},
        "started_at": datetime.utcnow().isoformat(),
        "ends_at": (datetime.utcnow() + timedelta(minutes=mode["duration_min"])).isoformat(),
        "submitted": False,
        "duration_min": mode["duration_min"],
    }

    # Return questions WITHOUT correct answers
    public_questions = [
        {k: v for k, v in q_.items() if k != "_correct"}
        for q_ in questions
    ]

    return {
        "session_id": session_id,
        "mode": mode["name"],
        "total_questions": len(questions),
        "duration_min": mode["duration_min"],
        "ends_at": _sessions[session_id]["ends_at"],
        "questions": public_questions,
    }


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    user: User = Depends(get_current_user),
):
    """Get session state (without answers)."""
    sess = _sessions.get(session_id)
    if not sess or sess["user_id"] != str(user.id):
        raise HTTPException(404, "Session not found")

    public_questions = [
        {k: v for k, v in q_.items() if k != "_correct"}
        for q_ in sess["questions"]
    ]
    answered = list(sess["answers"].keys())
    time_left = max(
        0,
        int((datetime.fromisoformat(sess["ends_at"]) - datetime.utcnow()).total_seconds())
    )

    return {
        "session_id": session_id,
        "mode": sess["mode_name"],
        "questions": public_questions,
        "answered_indices": answered,
        "submitted": sess["submitted"],
        "time_left_seconds": time_left,
        "ends_at": sess["ends_at"],
    }


@router.post("/sessions/{session_id}/answer")
async def submit_answer(
    session_id: str,
    body: AnswerBody,
    user: User = Depends(get_current_user),
):
    """Record an answer for a question during the session."""
    sess = _sessions.get(session_id)
    if not sess or sess["user_id"] != str(user.id):
        raise HTTPException(404, "Session not found")
    if sess["submitted"]:
        raise HTTPException(400, "Session already submitted")
    if datetime.utcnow() > datetime.fromisoformat(sess["ends_at"]):
        raise HTTPException(400, "Session time has expired")

    idx = body.question_index
    if idx < 0 or idx >= len(sess["questions"]):
        raise HTTPException(400, "Invalid question index")

    sess["answers"][str(idx)] = body.selected_option
    return {"recorded": True, "question_index": idx}


@router.post("/sessions/{session_id}/submit")
async def finalize_session(
    session_id: str,
    user: User = Depends(get_current_user),
):
    """Finalize session and get results."""
    sess = _sessions.get(session_id)
    if not sess or sess["user_id"] != str(user.id):
        raise HTTPException(404, "Session not found")
    if sess["submitted"]:
        return _build_results(sess)

    sess["submitted"] = True
    sess["submitted_at"] = datetime.utcnow().isoformat()
    return _build_results(sess)


@router.get("/sessions/{session_id}/results")
async def get_results(
    session_id: str,
    user: User = Depends(get_current_user),
):
    sess = _sessions.get(session_id)
    if not sess or sess["user_id"] != str(user.id):
        raise HTTPException(404, "Session not found")
    if not sess["submitted"]:
        raise HTTPException(400, "Session not yet submitted")
    return _build_results(sess)


def _build_results(sess: dict) -> dict:
    questions = sess["questions"]
    answers = sess["answers"]
    total = len(questions)
    correct = 0
    wrong = []
    per_question = []

    for q_ in questions:
        idx = str(q_["index"])
        selected = answers.get(idx)
        is_correct = selected == q_["_correct"]
        if is_correct:
            correct += 1
        else:
            wrong.append({
                "index": q_["index"],
                "question": q_["question"],
                "your_answer": selected,
                "correct_answer": q_["_correct"],
            })
        per_question.append({
            "index": q_["index"],
            "correct": is_correct,
            "selected": selected,
            "correct_answer": q_["_correct"] if not is_correct else None,
        })

    score_pct = round((correct / total) * 100) if total else 0
    passed = score_pct >= 60

    start = datetime.fromisoformat(sess["started_at"])
    end = datetime.fromisoformat(sess.get("submitted_at", datetime.utcnow().isoformat()))
    time_taken_min = round((end - start).total_seconds() / 60, 1)

    return {
        "session_id": sess["id"],
        "mode": sess["mode_name"],
        "total_questions": total,
        "correct": correct,
        "wrong": total - correct,
        "score_pct": score_pct,
        "passed": passed,
        "time_taken_min": time_taken_min,
        "per_question": per_question,
        "wrong_questions": wrong[:10],  # top 10 wrong for review
        "message": "Well done! 🎉" if passed else "Keep practicing — you'll get there! 💪",
    }


@router.get("/history")
async def exam_history(user: User = Depends(get_current_user)):
    """Return summary of past sessions for this user."""
    user_sessions = [
        s for s in _sessions.values()
        if s["user_id"] == str(user.id) and s["submitted"]
    ]
    user_sessions.sort(key=lambda s: s.get("submitted_at", ""), reverse=True)

    return [
        {
            "session_id": s["id"],
            "mode": s["mode_name"],
            "started_at": s["started_at"],
            "score_pct": _build_results(s)["score_pct"],
            "passed": _build_results(s)["passed"],
            "total_questions": len(s["questions"]),
            "time_taken_min": _build_results(s)["time_taken_min"],
        }
        for s in user_sessions[:20]
    ]
