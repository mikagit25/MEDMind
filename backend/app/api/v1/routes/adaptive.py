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
    """Return the cached study plan without recalculating. Returns empty plan if none generated yet."""
    cached = await get_cached(f"study_plan:{user.id}")
    if not cached:
        return {
            "generated_at": None,
            "valid_until": None,
            "weak_modules": [],
            "recommended_actions": [],
            "daily_goal_minutes": 20,
            "focus_areas": [],
            "weak_areas": [],
            "next_modules": [],
            "due_reviews": [],
            "up_next": [],
        }
    return cached
