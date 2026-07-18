"""Board Exam Prep Mode — USMLE / NCLEX / UKMLA.

Timed sessions with DB-persisted state, CAT-lite difficulty adaptation,
and NCLEX category analytics.

Endpoints
─────────
GET  /exam/modes                         — list available modes
POST /exam/sessions                      — create timed session
GET  /exam/sessions/{id}                 — get session + questions
POST /exam/sessions/{id}/answer          — record answer
POST /exam/sessions/{id}/submit          — finalize + results
GET  /exam/sessions/{id}/results         — results + category breakdown
GET  /exam/history                       — past sessions
GET  /exam/nclex/analytics               — NCLEX category performance over time
"""

import uuid as uuid_lib
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import ExamSession, MCQQuestion, Module, User
from app.services.ai_router import call_claude_structured

router = APIRouter(prefix="/exam", tags=["exam"])

# ── Exam mode definitions ──────────────────────────────────────────────────────

EXAM_MODES = [
    {
        "id": "usmle_step1",
        "name": "USMLE Step 1",
        "description": "Basic sciences — 40 questions, 60 min",
        "questions": 40,
        "duration_min": 60,
        "nursing_only": False,
        "difficulty": "hard",
        "icon": "stethoscope",
        "pass_threshold": 60,
    },
    {
        "id": "usmle_step2",
        "name": "USMLE Step 2 CK",
        "description": "Clinical knowledge — 40 questions, 60 min",
        "questions": 40,
        "duration_min": 60,
        "nursing_only": False,
        "difficulty": "hard",
        "icon": "hospital",
        "pass_threshold": 60,
    },
    {
        "id": "nclex_rn_75",
        "name": "NCLEX-RN (75 questions)",
        "description": "Minimum-length NCLEX simulation — 75 questions, 90 min. Nursing questions only.",
        "questions": 75,
        "duration_min": 90,
        "nursing_only": True,
        "difficulty": None,  # CAT adapts difficulty
        "cat": True,
        "icon": "heart-pulse",
        "pass_threshold": 62,
    },
    {
        "id": "nclex_rn_85",
        "name": "NCLEX-RN (85 questions)",
        "description": "Standard NCLEX simulation — 85 questions, 105 min.",
        "questions": 85,
        "duration_min": 105,
        "nursing_only": True,
        "difficulty": None,
        "cat": True,
        "icon": "heart-pulse",
        "pass_threshold": 62,
    },
    {
        "id": "nclex_rn_145",
        "name": "NCLEX-RN (145 questions)",
        "description": "Maximum-length NCLEX simulation — 145 questions, 210 min.",
        "questions": 145,
        "duration_min": 210,
        "nursing_only": True,
        "difficulty": None,
        "cat": True,
        "icon": "heart-pulse",
        "pass_threshold": 62,
    },
    {
        "id": "nclex_category",
        "name": "NCLEX by Category",
        "description": "Practice 30 questions from a single NCLEX client-needs category.",
        "questions": 30,
        "duration_min": 45,
        "nursing_only": True,
        "difficulty": None,
        "cat": False,
        "icon": "layers",
        "pass_threshold": 60,
    },
    {
        "id": "ukmla",
        "name": "UKMLA / MLA",
        "description": "UK licensing — 30 questions, 45 min",
        "questions": 30,
        "duration_min": 45,
        "nursing_only": False,
        "difficulty": "medium",
        "cat": False,
        "icon": "flag",
        "pass_threshold": 60,
    },
    {
        "id": "quick_20",
        "name": "Quick Practice",
        "description": "20 mixed questions, 20 min — any level",
        "questions": 20,
        "duration_min": 20,
        "nursing_only": False,
        "difficulty": None,
        "cat": False,
        "icon": "zap",
        "pass_threshold": 60,
    },
    {
        "id": "nclex_demo",
        "name": "NCLEX Demo (Free)",
        "description": "Try 10 NCLEX-style nursing questions — no subscription needed.",
        "questions": 10,
        "duration_min": 15,
        "nursing_only": True,
        "difficulty": "medium",
        "cat": False,
        "icon": "heart-pulse",
        "pass_threshold": 60,
        "demo": True,
    },
]

NCLEX_CLIENT_NEEDS = [
    "safe_effective_care",
    "health_promotion",
    "psychosocial",
    "basic_care",
    "pharmacological",
    "reduction_risk",
    "physiological_adaptation",
]

NCLEX_CLIENT_NEEDS_LABELS = {
    "safe_effective_care": "Safe & Effective Care Environment",
    "health_promotion": "Health Promotion & Maintenance",
    "psychosocial": "Psychosocial Integrity",
    "basic_care": "Basic Care & Comfort",
    "pharmacological": "Pharmacological & Parenteral Therapies",
    "reduction_risk": "Reduction of Risk Potential",
    "physiological_adaptation": "Physiological Adaptation",
}

CJMM_LABELS = {
    "recognize_cues": "Recognize Cues",
    "analyze_cues": "Analyze Cues",
    "prioritize_hypotheses": "Prioritize Hypotheses",
    "generate_solutions": "Generate Solutions",
    "take_actions": "Take Actions",
    "evaluate_outcomes": "Evaluate Outcomes",
}

# CAT difficulty levels in order
CAT_DIFFICULTY_LADDER = ["easy", "medium", "hard"]


# ── Schemas ────────────────────────────────────────────────────────────────────

class StartSession(BaseModel):
    mode_id: str
    nclex_category: Optional[str] = None  # for nclex_category mode


class AnswerBody(BaseModel):
    question_index: int
    selected_option: str = ""
    selected_options: List[str] = []
    ordered_options: List[str] = []
    numeric_value: Optional[float] = None


# ── Helpers ────────────────────────────────────────────────────────────────────

def _score_question(q_data: dict, answer: Any) -> tuple[bool, str]:
    """Score one question. Returns (is_correct, display_of_correct_answer)."""
    qtype = q_data.get("question_type", "mcq")
    if qtype == "sata":
        submitted = sorted(s.upper() for s in (answer or []))
        correct = sorted(s.upper() for s in (q_data.get("_correct_answers") or []))
        return submitted == correct, ",".join(correct)
    elif qtype == "ordered":
        submitted = [s.upper() for s in (answer or [])]
        correct = [s.upper() for s in (q_data.get("_correct_order") or [])]
        return submitted == correct, "→".join(correct)
    elif qtype == "calculation":
        num_ans = q_data.get("_numeric_answer")
        tol = q_data.get("_numeric_tolerance") or 0.5
        unit = q_data.get("numeric_unit") or ""
        if answer is None or num_ans is None:
            return False, f"{num_ans} {unit}".strip()
        return abs(float(answer) - float(num_ans)) <= tol, f"{num_ans} {unit}".strip()
    else:
        correct = q_data.get("_correct", "")
        return str(answer or "").upper() == str(correct).upper(), correct


def _next_cat_difficulty(current: str, was_correct: bool) -> str:
    idx = CAT_DIFFICULTY_LADDER.index(current) if current in CAT_DIFFICULTY_LADDER else 1
    if was_correct:
        idx = min(idx + 1, len(CAT_DIFFICULTY_LADDER) - 1)
    else:
        idx = max(idx - 1, 0)
    return CAT_DIFFICULTY_LADDER[idx]


def _build_results(sess: ExamSession, questions_data: list) -> dict:
    answers = sess.answers or {}
    total = len(questions_data)
    correct_count = 0
    wrong_list = []
    per_q = []
    category_stats: dict[str, dict] = {}
    cjmm_stats: dict[str, dict] = {}

    for q in questions_data:
        idx = str(q["index"])
        answer = answers.get(idx)
        is_correct, correct_display = _score_question(q, answer)

        if is_correct:
            correct_count += 1

        # Category tracking
        cat = q.get("nclex_client_needs")
        if cat:
            if cat not in category_stats:
                category_stats[cat] = {"total": 0, "correct": 0, "label": NCLEX_CLIENT_NEEDS_LABELS.get(cat, cat)}
            category_stats[cat]["total"] += 1
            if is_correct:
                category_stats[cat]["correct"] += 1

        # CJMM tracking
        skill = q.get("cjmm_skill")
        if skill:
            if skill not in cjmm_stats:
                cjmm_stats[skill] = {"total": 0, "correct": 0, "label": CJMM_LABELS.get(skill, skill)}
            cjmm_stats[skill]["total"] += 1
            if is_correct:
                cjmm_stats[skill]["correct"] += 1

        if not is_correct:
            wrong_list.append({
                "index": q["index"],
                "id": q.get("id"),  # question UUID for AI explain endpoint
                "question": q["question"],
                "your_answer": answer,
                "correct_answer": correct_display,
                "explanation": q.get("explanation"),
                "nclex_client_needs": cat,
                "cjmm_skill": skill,
            })

        per_q.append({
            "index": q["index"],
            "correct": is_correct,
            "selected": answer,
            "correct_answer": correct_display if not is_correct else None,
            "nclex_client_needs": cat,
            "cjmm_skill": skill,
            "question_type": q.get("question_type", "mcq"),
            "ngn_type": q.get("ngn_type"),
        })

    mode = next((m for m in EXAM_MODES if m["id"] == sess.mode_id), {})
    pass_threshold = mode.get("pass_threshold", 60)
    score_pct = round((correct_count / total) * 100) if total else 0
    passed = score_pct >= pass_threshold

    # Category pct
    for c in category_stats.values():
        c["pct"] = round(c["correct"] / c["total"] * 100) if c["total"] else 0
    for c in cjmm_stats.values():
        c["pct"] = round(c["correct"] / c["total"] * 100) if c["total"] else 0

    # Weak categories (pct < 60%)
    weak_categories = [
        {"key": k, **v} for k, v in category_stats.items() if v["pct"] < 60
    ]
    weak_categories.sort(key=lambda x: x["pct"])

    start = sess.starts_at
    end = sess.ends_at if sess.status == "completed" else datetime.utcnow()
    time_taken_min = round((end - start).total_seconds() / 60, 1)

    return {
        "session_id": str(sess.id),
        "mode": sess.mode_name,
        "mode_id": sess.mode_id,
        "total_questions": total,
        "correct": correct_count,
        "wrong": total - correct_count,
        "score_pct": score_pct,
        "passed": passed,
        "pass_threshold": pass_threshold,
        "time_taken_min": time_taken_min,
        "cat_enabled": sess.cat_enabled,
        "per_question": per_q,
        "wrong_questions": wrong_list[:15],
        "nclex_category_breakdown": category_stats,
        "nclex_cjmm_breakdown": cjmm_stats,
        "weak_categories": weak_categories,
        "message": (
            "Excellent — NCLEX-ready performance!" if score_pct >= 75
            else "Good progress! Focus on the weak categories below." if passed
            else "Keep practicing — review the weak areas and try again!"
        ),
    }


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/modes")
async def list_modes(user: User = Depends(get_current_user)):
    result = []
    is_free = user.subscription_tier == "free"
    for m in EXAM_MODES:
        is_demo = m.get("demo", False)
        result.append({
            **m,
            "locked": is_free and not is_demo,
            "lock_reason": "Upgrade to Student or Pro to unlock board exams" if (is_free and not is_demo) else None,
        })
    return result


@router.get("/nclex/categories")
async def nclex_categories():
    """Return NCLEX client-needs categories for the category-practice mode."""
    return [
        {"key": k, "label": v}
        for k, v in NCLEX_CLIENT_NEEDS_LABELS.items()
    ]


@router.post("/sessions", status_code=201)
async def create_session(
    body: StartSession,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    mode = next((m for m in EXAM_MODES if m["id"] == body.mode_id), None)
    if not mode:
        raise HTTPException(404, f"Unknown exam mode: {body.mode_id}")

    if not mode.get("demo", False) and user.subscription_tier == "free":
        raise HTTPException(403, "Board Exam mode requires a Student or Pro subscription.")

    cat_mode = mode.get("cat", False)
    nursing_only = mode.get("nursing_only", False)
    start_difficulty = "medium"

    # Build query
    q = select(MCQQuestion)

    if nursing_only:
        q = q.join(Module, Module.id == MCQQuestion.module_id).where(
            Module.is_nursing == True,
            Module.is_published == True,
        )

    if body.mode_id == "nclex_category" and body.nclex_category:
        if body.nclex_category not in NCLEX_CLIENT_NEEDS:
            raise HTTPException(400, f"Unknown NCLEX category: {body.nclex_category}")
        q = q.where(MCQQuestion.nclex_client_needs == body.nclex_category)
    elif not cat_mode and mode.get("difficulty"):
        q = q.where(MCQQuestion.difficulty == mode["difficulty"])

    if cat_mode:
        # CAT starts at medium
        q = q.where(MCQQuestion.difficulty == start_difficulty)

    q = q.order_by(func.random()).limit(mode["questions"])
    mcqs = (await db.execute(q)).scalars().all()

    if len(mcqs) < 5:
        raise HTTPException(
            503,
            "Not enough questions available for this exam mode. "
            "The question bank is still growing — check back soon!"
        )

    now = datetime.utcnow()
    ends_at = now + timedelta(minutes=mode["duration_min"])

    question_ids = [str(mcq.id) for mcq in mcqs]
    questions_snapshot = [
        {
            "index": i,
            "id": str(mcq.id),
            "question": mcq.question,
            "options": mcq.options if isinstance(mcq.options, dict) else {},
            "question_type": getattr(mcq, "question_type", "mcq") or "mcq",
            "numeric_unit": getattr(mcq, "numeric_unit", None),
            "ngn_type": getattr(mcq, "ngn_type", None),
            "bowtie_data": getattr(mcq, "bowtie_data", None),
            "nclex_client_needs": getattr(mcq, "nclex_client_needs", None),
            "cjmm_skill": getattr(mcq, "cjmm_skill", None),
            "explanation": getattr(mcq, "explanation", None),
            # private scoring fields
            "_correct": mcq.correct,
            "_correct_answers": getattr(mcq, "correct_answers", None),
            "_correct_order": getattr(mcq, "correct_order", None),
            "_numeric_answer": getattr(mcq, "numeric_answer", None),
            "_numeric_tolerance": getattr(mcq, "numeric_tolerance", 0.5) or 0.5,
        }
        for i, mcq in enumerate(mcqs)
    ]

    session = ExamSession(
        id=uuid_lib.uuid4(),
        user_id=user.id,
        mode_id=body.mode_id,
        mode_name=mode["name"],
        status="active",
        question_ids=question_ids,
        answers={},
        total_questions=len(mcqs),
        duration_min=mode["duration_min"],
        starts_at=now,
        ends_at=ends_at,
        current_difficulty=start_difficulty,
        cat_enabled=cat_mode,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Return without private answer fields
    public_questions = [
        {k: v for k, v in q_.items() if not k.startswith("_")}
        for q_ in questions_snapshot
    ]

    # Store full snapshot in session cache (Redis in production; here we'll use per-session JSONB)
    # We re-fetch questions when needed from the question_ids list
    session.answers = {"_snapshot": questions_snapshot}  # store snapshot for scoring
    await db.commit()

    return {
        "session_id": str(session.id),
        "mode": mode["name"],
        "mode_id": body.mode_id,
        "total_questions": len(mcqs),
        "duration_min": mode["duration_min"],
        "ends_at": ends_at.isoformat(),
        "cat_enabled": cat_mode,
        "questions": public_questions,
        "nclex_category_filter": body.nclex_category,
    }


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sess = await _get_session(session_id, user.id, db)

    snapshot = (sess.answers or {}).get("_snapshot", [])
    answered_indices = [k for k in (sess.answers or {}) if k != "_snapshot"]
    time_left = max(0, int((sess.ends_at - datetime.utcnow()).total_seconds()))

    public_questions = [
        {k: v for k, v in q_.items() if not k.startswith("_")}
        for q_ in snapshot
    ]

    return {
        "session_id": session_id,
        "mode": sess.mode_name,
        "mode_id": sess.mode_id,
        "status": sess.status,
        "questions": public_questions,
        "answered_indices": answered_indices,
        "time_left_seconds": time_left,
        "ends_at": sess.ends_at.isoformat(),
        "cat_enabled": sess.cat_enabled,
        "current_difficulty": sess.current_difficulty,
    }


@router.post("/sessions/{session_id}/answer")
async def submit_answer(
    session_id: str,
    body: AnswerBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sess = await _get_session(session_id, user.id, db)
    if sess.status != "active":
        raise HTTPException(400, "Session is not active")
    if datetime.utcnow() > sess.ends_at:
        sess.status = "expired"
        await db.commit()
        raise HTTPException(400, "Session time has expired")

    snapshot = (sess.answers or {}).get("_snapshot", [])
    idx = body.question_index
    if idx < 0 or idx >= len(snapshot):
        raise HTTPException(400, "Invalid question index")

    qtype = snapshot[idx].get("question_type", "mcq")
    if qtype == "sata":
        answer = body.selected_options
    elif qtype == "ordered":
        answer = body.ordered_options
    elif qtype == "calculation":
        answer = body.numeric_value
    else:
        answer = body.selected_option

    # CAT: adjust difficulty based on answer correctness
    new_difficulty = sess.current_difficulty
    if sess.cat_enabled:
        is_correct, _ = _score_question(snapshot[idx], answer)
        new_difficulty = _next_cat_difficulty(sess.current_difficulty, is_correct)

    # Merge answer into the answers dict (keep _snapshot)
    answers = dict(sess.answers or {})
    answers[str(idx)] = answer
    if sess.cat_enabled:
        sess.current_difficulty = new_difficulty
    sess.answers = answers
    await db.commit()

    return {
        "recorded": True,
        "question_index": idx,
        "current_difficulty": new_difficulty if sess.cat_enabled else None,
    }


@router.post("/sessions/{session_id}/submit")
async def finalize_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sess = await _get_session(session_id, user.id, db)
    if sess.status == "completed":
        snapshot = (sess.answers or {}).get("_snapshot", [])
        return _build_results(sess, snapshot)

    snapshot = (sess.answers or {}).get("_snapshot", [])
    results = _build_results(sess, snapshot)

    now = datetime.utcnow()
    sess.status = "completed"
    sess.ends_at = min(sess.ends_at, now)
    sess.correct = results["correct"]
    sess.wrong = results["wrong"]
    sess.score_pct = results["score_pct"]
    sess.passed = results["passed"]
    sess.time_taken_min = results["time_taken_min"]
    sess.per_question = results["per_question"]
    await db.commit()

    return results


@router.get("/sessions/{session_id}/results")
async def get_results(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sess = await _get_session(session_id, user.id, db)
    if sess.status not in ("completed", "expired"):
        raise HTTPException(400, "Session not yet submitted")
    snapshot = (sess.answers or {}).get("_snapshot", [])
    return _build_results(sess, snapshot)


@router.get("/history")
async def exam_history(
    limit: int = Query(20, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ExamSession)
        .where(
            ExamSession.user_id == user.id,
            ExamSession.status.in_(["completed", "expired"]),
        )
        .order_by(ExamSession.created_at.desc())
        .limit(limit)
    )
    sessions = result.scalars().all()

    return [
        {
            "session_id": str(s.id),
            "mode": s.mode_name,
            "mode_id": s.mode_id,
            "started_at": s.starts_at.isoformat(),
            "score_pct": s.score_pct,
            "passed": s.passed,
            "correct": s.correct,
            "total_questions": s.total_questions,
            "time_taken_min": s.time_taken_min,
            "cat_enabled": s.cat_enabled,
        }
        for s in sessions
    ]


@router.get("/nclex/analytics")
async def nclex_analytics(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate NCLEX category performance across all completed sessions."""
    result = await db.execute(
        select(ExamSession)
        .where(
            ExamSession.user_id == user.id,
            ExamSession.status == "completed",
            ExamSession.mode_id.like("nclex_%"),
        )
        .order_by(ExamSession.created_at.desc())
        .limit(10)
    )
    sessions = result.scalars().all()

    if not sessions:
        return {"sessions_analyzed": 0, "category_performance": {}, "cjmm_performance": {}}

    # Aggregate per_question data across sessions
    category_totals: dict[str, dict] = {}
    cjmm_totals: dict[str, dict] = {}

    for sess in sessions:
        for pq in (sess.per_question or []):
            cat = pq.get("nclex_client_needs")
            skill = pq.get("cjmm_skill")
            is_correct = pq.get("correct", False)

            if cat:
                if cat not in category_totals:
                    category_totals[cat] = {"total": 0, "correct": 0, "label": NCLEX_CLIENT_NEEDS_LABELS.get(cat, cat)}
                category_totals[cat]["total"] += 1
                if is_correct:
                    category_totals[cat]["correct"] += 1

            if skill:
                if skill not in cjmm_totals:
                    cjmm_totals[skill] = {"total": 0, "correct": 0, "label": CJMM_LABELS.get(skill, skill)}
                cjmm_totals[skill]["total"] += 1
                if is_correct:
                    cjmm_totals[skill]["correct"] += 1

    for c in category_totals.values():
        c["pct"] = round(c["correct"] / c["total"] * 100) if c["total"] else 0
    for c in cjmm_totals.values():
        c["pct"] = round(c["correct"] / c["total"] * 100) if c["total"] else 0

    weak = [{"key": k, **v} for k, v in category_totals.items() if v["pct"] < 60]
    weak.sort(key=lambda x: x["pct"])

    return {
        "sessions_analyzed": len(sessions),
        "category_performance": category_totals,
        "cjmm_performance": cjmm_totals,
        "weak_categories": weak[:3],
        "overall_trend": [
            {
                "session_id": str(s.id),
                "date": s.starts_at.isoformat(),
                "score_pct": s.score_pct,
                "mode": s.mode_name,
            }
            for s in sessions
        ],
    }


async def _get_session(
    session_id: str, user_id: UUID, db: AsyncSession
) -> ExamSession:
    try:
        sid = uuid_lib.UUID(session_id)
    except ValueError:
        raise HTTPException(404, "Session not found")
    result = await db.execute(
        select(ExamSession).where(
            ExamSession.id == sid,
            ExamSession.user_id == user_id,
        )
    )
    sess = result.scalar_one_or_none()
    if not sess:
        raise HTTPException(404, "Session not found")
    return sess


# ── AI Explanation Endpoint ────────────────────────────────────────────────────

class ExplainRequest(BaseModel):
    question_id: str
    user_question: Optional[str] = None  # optional follow-up from user


@router.post("/questions/{question_id}/explain")
async def explain_question(
    question_id: str,
    body: ExplainRequest = ExplainRequest(question_id=""),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate an AI-powered deep explanation for a given MCQ question.

    Uses Claude Haiku (fast + cheap). No AI quota deducted — educational feature.
    """
    try:
        qid = uuid_lib.UUID(question_id)
    except ValueError:
        raise HTTPException(404, "Question not found")

    result = await db.execute(select(MCQQuestion).where(MCQQuestion.id == qid))
    q = result.scalar_one_or_none()
    if not q:
        raise HTTPException(404, "Question not found")

    # Build options text
    options = q.options or {}
    options_text = "\n".join(f"  {k}. {v}" for k, v in options.items())

    # Correct answer display
    if q.question_type == "sata":
        correct_display = ", ".join(q.correct_answers or [])
        answer_label = f"Correct answers: {correct_display} (Select All That Apply)"
    elif q.question_type == "ordered":
        correct_display = " → ".join(q.correct_order or [])
        answer_label = f"Correct order: {correct_display}"
    elif q.question_type == "calculation":
        answer_label = f"Correct answer: {q.numeric_answer} {q.numeric_unit or ''}"
    else:
        opt_text = options.get(q.correct or "", "")
        answer_label = f"Correct answer: {q.correct}. {opt_text}"

    nclex_cat = NCLEX_CLIENT_NEEDS_LABELS.get(q.nclex_client_needs or "", q.nclex_client_needs or "General Nursing")
    cjmm = CJMM_LABELS.get(q.cjmm_skill or "", "")

    follow_up = f"\n\nStudent's additional question: {body.user_question}" if body.user_question else ""

    system_prompt = (
        "You are an expert NCLEX-RN nursing educator with 20 years of clinical and teaching experience. "
        "Your explanations are clear, clinically accurate, and help students deeply understand the reasoning — "
        "not just memorize answers. Use plain English. Structure your response with clear sections."
    )

    user_msg = f"""A nursing student needs a detailed explanation for this NCLEX question.

QUESTION:
{q.question}

OPTIONS:
{options_text if options_text else '(Numeric entry question)'}

{answer_label}

NCLEX Category: {nclex_cat}
{f'Clinical Judgment Skill: {cjmm}' if cjmm else ''}

EXISTING EXPLANATION (brief):
{q.explanation or 'None provided.'}
{follow_up}

Please provide a COMPREHENSIVE explanation covering:

## Why the Correct Answer is Right
Explain the clinical reasoning. What assessment data, pathophysiology, or nursing principle makes this the best choice?

## Why Each Wrong Option is Incorrect
Go through each distractor and explain the clinical error or reasoning flaw.

## Key Nursing Concepts to Remember
Mnemonics, frameworks, or clinical pearls relevant to this topic.

## NCLEX Strategy Tip
How to approach this type of question on the real exam."""

    try:
        explanation, _ = await call_claude_structured(
            system=system_prompt,
            user_message=user_msg,
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
        )
    except Exception as e:
        raise HTTPException(503, f"AI service temporarily unavailable: {str(e)[:100]}")

    return {
        "question_id": question_id,
        "explanation": explanation,
        "nclex_category": nclex_cat,
        "cjmm_skill": cjmm,
    }
