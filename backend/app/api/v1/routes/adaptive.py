"""Adaptive learning — personalized study plan based on weak areas."""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.cache import get_cached, set_cached
from app.core.database import get_db
from app.models.models import (
    User, UserProgress, FlashcardReview, Flashcard, Module,
    MCQQuestion, Lesson,
)

router = APIRouter(prefix="/student", tags=["adaptive"])


class StudyPlan(BaseModel):
    generated_at: str
    valid_until: str
    weak_modules: List[Dict[str, Any]]
    recommended_actions: List[Dict[str, Any]]
    daily_goal_minutes: int
    focus_areas: List[str]
    # Frontend-compatible aliases
    weak_areas: List[Dict[str, Any]] = []
    next_modules: List[Dict[str, Any]] = []
    due_reviews: List[Dict[str, Any]] = []
    up_next: List[Dict[str, Any]] = []


@router.post("/plan/adapt", response_model=StudyPlan)
async def adapt_study_plan(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Recalculate the student's adaptive study plan based on:
    - Module completion percentages (weak areas < 70%)
    - Flashcard error rates (due + low ease_factor)
    - MCQ accuracy by module
    - Daily goal from preferences

    Returns a prioritized action list for the next study session.
    Cached for 1 hour — call after each study session to refresh.
    """
    cache_key = f"study_plan:{user.id}"
    cached = await get_cached(cache_key)
    if cached:
        return StudyPlan(**cached)

    prefs = user.preferences or {}
    daily_goal = prefs.get("daily_goal_minutes", 20)
    exam_date = prefs.get("exam_date")  # ISO date string

    # 1. Find weak modules (completion < 70%)
    prog_rows = (await db.execute(
        select(UserProgress, Module)
        .join(Module, Module.id == UserProgress.module_id)
        .where(
            UserProgress.user_id == user.id,
            UserProgress.completion_percent < 70,
            Module.is_published == True,
        )
        .order_by(UserProgress.completion_percent.asc())
        .limit(5)
    )).all()

    weak_modules = [
        {
            "module_id": str(p.module_id),
            "title": m.title,
            "completion_percent": float(p.completion_percent or 0),
            "last_activity": p.last_activity_at.isoformat() if p.last_activity_at else None,
            "priority": "high" if float(p.completion_percent or 0) < 30 else "medium",
        }
        for p, m in prog_rows
    ]

    # 2. Flashcards needing review (due + struggling, ease < 2.0)
    struggling_cards = (await db.execute(
        select(func.count(FlashcardReview.flashcard_id))
        .where(
            FlashcardReview.user_id == user.id,
            FlashcardReview.next_review_at <= datetime.utcnow(),
            FlashcardReview.ease_factor < 2.0,
        )
    )).scalar() or 0

    total_due = (await db.execute(
        select(func.count(FlashcardReview.flashcard_id))
        .where(
            FlashcardReview.user_id == user.id,
            FlashcardReview.next_review_at <= datetime.utcnow(),
        )
    )).scalar() or 0

    # 3. Build recommended actions (prioritized)
    actions: List[Dict[str, Any]] = []

    if total_due > 0:
        actions.append({
            "type": "review_flashcards",
            "priority": 1,
            "label": f"Review {total_due} due flashcards ({struggling_cards} need extra attention)",
            "estimated_minutes": min(total_due * 2, 30),
            "module_id": None,
        })

    for mod in weak_modules[:3]:
        actions.append({
            "type": "continue_module",
            "priority": 2 if mod["priority"] == "high" else 3,
            "label": f"Continue '{mod['title']}' ({mod['completion_percent']:.0f}% complete)",
            "estimated_minutes": 15,
            "module_id": mod["module_id"],
        })

    # Add exam urgency if exam is coming up
    if exam_date:
        try:
            exam_dt = datetime.fromisoformat(exam_date)
            days_left = (exam_dt - datetime.utcnow()).days
            if days_left <= 14:
                actions.insert(0, {
                    "type": "exam_prep",
                    "priority": 0,
                    "label": f"\u26a0\ufe0f Exam in {days_left} days \u2014 prioritize weak areas",
                    "estimated_minutes": daily_goal,
                    "module_id": None,
                })
        except (ValueError, TypeError):
            pass

    focus_areas = [m["title"] for m in weak_modules[:3]]

    # Build frontend-compatible arrays
    weak_areas = [
        {
            "module_id": m["module_id"],
            "module_title": m["title"],
            "title": m["title"],
            "reason": "weak_area",
            "priority_score": 100 - float(m["completion_percent"]),
            "suggested_action": f"{m['completion_percent']:.0f}% complete — needs work",
        }
        for m in weak_modules[:5]
    ]

    next_mods = [
        a for a in actions if a.get("type") == "continue_module"
    ]
    next_modules = [
        {
            "module_id": a["module_id"],
            "module_title": a["label"].split("'")[1] if "'" in a["label"] else a["label"],
            "title": a["label"],
            "reason": "next_in_path",
            "suggested_action": a["label"],
        }
        for a in next_mods[:5]
    ]

    due_reviews_list = []
    if total_due > 0:
        due_reviews_list = [
            {
                "module_id": None,
                "module_title": f"{total_due} flashcards due",
                "title": f"{total_due} flashcards due",
                "reason": "due_review",
                "suggested_action": f"{struggling_cards} struggling cards",
            }
        ]

    now = datetime.utcnow()
    plan = {
        "generated_at": now.isoformat(),
        "valid_until": (now + timedelta(hours=6)).isoformat(),
        "weak_modules": weak_modules,
        "recommended_actions": sorted(actions, key=lambda x: x["priority"]),
        "daily_goal_minutes": daily_goal,
        "focus_areas": focus_areas,
        "weak_areas": weak_areas,
        "next_modules": next_modules,
        "due_reviews": due_reviews_list,
        "up_next": next_modules,
    }

    await set_cached(cache_key, plan, ttl=3600)
    return StudyPlan(**plan)


@router.get("/plan/current")
async def get_current_plan(
    user: User = Depends(get_current_user),
):
    """Return the cached study plan without recalculating. Returns 404 if none generated yet."""
    cached = await get_cached(f"study_plan:{user.id}")
    if not cached:
        raise HTTPException(status_code=404, detail="No study plan found. Call POST /student/plan/adapt to generate one.")
    return cached


# ── Exam prep plan ────────────────────────────────────────────────────────────

EXAM_LABELS: dict[str, str] = {
    "usmle_step1": "USMLE Step 1",
    "usmle_step2": "USMLE Step 2 CK",
    "usmle_step3": "USMLE Step 3",
    "nclex_rn":    "NCLEX-RN",
    "nclex_pn":    "NCLEX-PN",
    "ukmla":       "UKMLA",
    "plab":        "PLAB",
    "custom":      "Board Exam",
}

class ExamPrepRequest(BaseModel):
    exam_type: str = "usmle_step2"
    exam_date: str  # ISO date string (YYYY-MM-DD)
    daily_hours: float = 2.0

class WeekPlan(BaseModel):
    week: int
    theme: str
    modules: List[Dict[str, Any]]  # [{module_id, title, priority, sessions}]
    daily_hours: float
    milestone: str

class ExamPrepPlan(BaseModel):
    exam_type: str
    exam_label: str
    exam_date: str
    days_remaining: int
    total_weeks: int
    daily_hours: float
    generated_at: str
    weeks: List[WeekPlan]
    tip: str


@router.post("/exam-prep/plan", response_model=ExamPrepPlan)
async def generate_exam_prep_plan(
    body: ExamPrepRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate a personalized week-by-week exam study plan using Claude."""
    import json as _json
    from app.services.ai_router import call_claude_structured

    # Validate exam_date
    try:
        exam_dt = datetime.fromisoformat(body.exam_date)
    except ValueError:
        raise HTTPException(status_code=422, detail="exam_date must be ISO format (YYYY-MM-DD)")

    days_remaining = (exam_dt.date() - datetime.utcnow().date()).days
    if days_remaining < 1:
        raise HTTPException(status_code=422, detail="exam_date must be in the future")
    if days_remaining > 730:
        raise HTTPException(status_code=422, detail="exam_date must be within 2 years")

    total_weeks = max(1, days_remaining // 7)
    exam_label = EXAM_LABELS.get(body.exam_type, EXAM_LABELS["custom"])

    # Check cache first
    cache_key = f"exam_plan:{user.id}:{body.exam_type}:{body.exam_date}"
    cached = await get_cached(cache_key)
    if cached:
        return ExamPrepPlan(**cached)

    # Fetch available modules
    modules_result = await db.execute(
        select(Module.id, Module.title, Module.code, Module.specialty_id)
        .where(Module.is_published == True)
        .order_by(Module.title)
        .limit(50)
    )
    all_modules = [
        {"id": str(r.id), "title": r.title, "code": r.code}
        for r in modules_result.all()
    ]

    # Fetch user progress (completion %)
    progress_result = await db.execute(
        select(UserProgress.module_id, UserProgress.completion_percent)
        .where(UserProgress.user_id == user.id)
    )
    progress_map = {str(r.module_id): float(r.completion_percent or 0) for r in progress_result.all()}

    # Classify modules into not_started, in_progress, completed
    for m in all_modules:
        pct = progress_map.get(m["id"], 0)
        m["completion_pct"] = round(pct)
        m["status"] = "completed" if pct >= 90 else ("in_progress" if pct > 0 else "not_started")

    modules_summary = "\n".join(
        f"- {m['title']} [{m['status']}, {m['completion_pct']}% done]"
        for m in all_modules[:30]
    )

    system_prompt = (
        "You are a medical education expert creating a personalized board exam study schedule. "
        "Return ONLY valid JSON — no markdown, no commentary. "
        "Format: {\"weeks\":[{\"week\":1,\"theme\":\"...\",\"modules\":[{\"module_id\":\"...\",\"title\":\"...\",\"sessions\":2}],"
        "\"daily_hours\":2.0,\"milestone\":\"...\"}],\"tip\":\"...\"}"
    )

    user_message = (
        f"Student is preparing for {exam_label} in {days_remaining} days ({total_weeks} weeks).\n"
        f"Available study time: {body.daily_hours} hours/day.\n\n"
        f"Available modules (title [status, % done]):\n{modules_summary}\n\n"
        f"Create a {min(total_weeks, 12)}-week study plan. Rules:\n"
        f"- Prioritize not_started modules with medically critical topics first\n"
        f"- Include in_progress modules early (to finish them)\n"
        f"- Skip completed modules unless they need review\n"
        f"- Each week has a clear theme (e.g. 'Cardiology & Pulmonology')\n"
        f"- sessions = number of study sessions for that module this week (1-3)\n"
        f"- milestone = what the student should be able to do by end of this week\n"
        f"- tip = one practical study tip for this exam type\n"
        f"Return ONLY the JSON object."
    )

    try:
        raw, _ = await call_claude_structured(system=system_prompt, user_message=user_message)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI service unavailable: {e}")

    # Parse response
    try:
        clean = raw.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        parsed = _json.loads(clean)
        weeks_raw = parsed.get("weeks", [])
        tip = parsed.get("tip", "Stay consistent — short daily sessions beat marathon cramming.")
    except Exception:
        raise HTTPException(status_code=502, detail="AI returned malformed response. Please try again.")

    # Merge in module IDs from our catalog (Claude may only know titles)
    title_to_id = {m["title"]: m["id"] for m in all_modules}
    weeks = []
    for i, w in enumerate(weeks_raw[:12], start=1):
        modules_out = []
        for m in w.get("modules", []):
            mid = m.get("module_id") or title_to_id.get(m.get("title", ""), "")
            if not mid:
                # Try fuzzy title match
                for mod in all_modules:
                    if mod["title"].lower() in str(m.get("title", "")).lower():
                        mid = mod["id"]
                        break
            modules_out.append({
                "module_id": mid,
                "title": m.get("title", ""),
                "sessions": max(1, int(m.get("sessions", 1))),
            })
        weeks.append(WeekPlan(
            week=i,
            theme=str(w.get("theme", f"Week {i}")),
            modules=modules_out,
            daily_hours=float(w.get("daily_hours", body.daily_hours)),
            milestone=str(w.get("milestone", "")),
        ))

    plan = ExamPrepPlan(
        exam_type=body.exam_type,
        exam_label=exam_label,
        exam_date=body.exam_date,
        days_remaining=days_remaining,
        total_weeks=total_weeks,
        daily_hours=body.daily_hours,
        generated_at=datetime.utcnow().isoformat(),
        weeks=weeks,
        tip=tip,
    )

    # Cache for 6 hours
    await set_cached(cache_key, plan.model_dump(), ttl=21600)
    return plan
