"""Role-based dashboard endpoints."""
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.cache import get_cached, set_cached, invalidate
from app.models.models import (
    User, UserProgress, FlashcardReview, Flashcard, Lesson,
    Module, CMECredit, CourseEnrollment, Course, UserAchievement,
)

STUDENT_DASHBOARD_TTL = 300  # 5 minutes

router = APIRouter(tags=["dashboard"])


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _base_stats(user: User, db: AsyncSession) -> Dict[str, Any]:
    """Shared stats used by all dashboard roles."""
    # Lessons completed
    prog_rows = (await db.execute(
        select(UserProgress).where(UserProgress.user_id == user.id)
    )).scalars().all()

    lessons_done = sum(len(p.lessons_completed or []) for p in prog_rows)
    modules_started = len(prog_rows)

    # Due flashcards
    due_count = (await db.execute(
        select(func.count(FlashcardReview.flashcard_id)).where(
            FlashcardReview.user_id == user.id,
            FlashcardReview.next_review_at <= datetime.utcnow(),
        )
    )).scalar() or 0

    # Achievements count
    ach_count = (await db.execute(
        select(func.count(UserAchievement.id)).where(
            UserAchievement.user_id == user.id
        )
    )).scalar() or 0

    return {
        "xp": user.xp,
        "level": user.level,
        "streak_days": user.streak_days or 0,
        "lessons_completed": lessons_done,
        "modules_started": modules_started,
        "flashcards_due": due_count,
        "achievements_count": ach_count,
    }


# ── Overview (all roles) ───────────────────────────────────────────────────────

@router.get("/dashboard/overview")
async def dashboard_overview(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """General dashboard — works for any role."""
    stats = await _base_stats(user, db)

    # Recent modules
    prog_rows = (await db.execute(
        select(UserProgress, Module)
        .join(Module, Module.id == UserProgress.module_id)
        .where(UserProgress.user_id == user.id)
        .order_by(desc(UserProgress.last_activity_at))
        .limit(5)
    )).all()

    recent_modules = [
        {
            "id": str(p.module_id),
            "title": m.title,
            "completion_percent": float(p.completion_percent or 0),
            "last_activity": p.last_activity_at.isoformat() if p.last_activity_at else None,
        }
        for p, m in prog_rows
    ]

    return {
        "role": user.role,
        "subscription_tier": user.subscription_tier,
        "stats": stats,
        "recent_modules": recent_modules,
    }


# ── Student dashboard ─────────────────────────────────────────────────────────

@router.get("/student/dashboard")
async def student_dashboard(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cache_key = f"student_dashboard:{user.id}"
    cached = await get_cached(cache_key)
    if cached:
        return cached

    stats = await _base_stats(user, db)

    # Modules with lowest completion (weak areas to revisit)
    weak_mods = (await db.execute(
        select(UserProgress, Module)
        .join(Module, Module.id == UserProgress.module_id)
        .where(
            UserProgress.user_id == user.id,
            UserProgress.completion_percent < 80,
        )
        .order_by(UserProgress.completion_percent.asc())
        .limit(3)
    )).all()

    weak_areas = [
        {
            "id": str(p.module_id),
            "title": m.title,
            "completion_percent": float(p.completion_percent or 0),
        }
        for p, m in weak_mods
    ]

    # Today's plan: due flashcards + next lesson
    due_cards = (await db.execute(
        select(func.count(FlashcardReview.flashcard_id)).where(
            FlashcardReview.user_id == user.id,
            FlashcardReview.next_review_at <= datetime.utcnow(),
        )
    )).scalar() or 0

    # Goals progress (daily_goal_minutes from preferences)
    prefs = user.preferences or {}
    daily_goal = prefs.get("daily_goal_minutes", 20)

    result = {
        "stats": stats,
        "weak_areas": weak_areas,
        "today_plan": {
            "flashcards_due": due_cards,
            "daily_goal_minutes": daily_goal,
            "suggested_action": "review_flashcards" if due_cards > 0 else "continue_module",
        },
    }
    await set_cached(cache_key, result, ttl=STUDENT_DASHBOARD_TTL)
    return result


# ── Doctor dashboard ──────────────────────────────────────────────────────────

@router.get("/doctor/dashboard")
async def doctor_dashboard(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stats = await _base_stats(user, db)

    # CME credits summary
    cme_rows = (await db.execute(
        select(CMECredit).where(CMECredit.user_id == user.id)
        .order_by(desc(CMECredit.completion_date))
    )).scalars().all()

    total_cme = sum(float(c.credits_earned or 0) for c in cme_rows)
    recent_cme = [
        {
            "id": str(c.id),
            "activity_title": c.activity_title,
            "credits": float(c.credits_earned or 0),
            "credit_type": c.credit_type,
            "completed_at": c.completion_date.isoformat() if c.completion_date else None,
        }
        for c in cme_rows[:5]
    ]

    return {
        "stats": stats,
        "cme": {
            "total_credits": total_cme,
            "credits_this_year": sum(
                float(c.credits_earned or 0) for c in cme_rows
                if c.completion_date and c.completion_date.year == datetime.utcnow().year
            ),
            "recent": recent_cme,
        },
    }


# ── CME credits list ──────────────────────────────────────────────────────────

@router.get("/doctor/cme-credits")
async def get_cme_credits(
    year: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = select(CMECredit, Module.title.label("module_title")).outerjoin(
        Module, Module.id == CMECredit.module_id
    ).where(CMECredit.user_id == user.id)

    if year:
        q = q.where(
            func.extract("year", CMECredit.completion_date) == year
        )

    q = q.order_by(desc(CMECredit.completion_date))
    rows = (await db.execute(q)).all()

    total = sum(float(r[0].credits_earned or 0) for r in rows)
    return {
        "total_credits": total,
        "year": year or "all",
        "credits": [
            {
                "id": str(r[0].id),
                "activity_title": r[0].activity_title,
                "module_title": r[1],
                "credits": float(r[0].credits_earned or 0),
                "credit_type": r[0].credit_type,
                "certificate_url": r[0].certificate_url,
                "completed_at": r[0].completion_date.isoformat() if r[0].completion_date else None,
            }
            for r in rows
        ],
    }


# ── Professor dashboard ───────────────────────────────────────────────────────

@router.get("/professor/dashboard")
async def professor_dashboard(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stats = await _base_stats(user, db)

    # Courses created by this professor
    courses = (await db.execute(
        select(Course).where(Course.teacher_id == user.id, Course.is_active == True)
        .order_by(desc(Course.created_at))
    )).scalars().all()

    courses_out = []
    for course in courses:
        # Count enrolled students
        student_count = (await db.execute(
            select(func.count(CourseEnrollment.id)).where(
                CourseEnrollment.course_id == course.id,
                CourseEnrollment.status == "active",
            )
        )).scalar() or 0

        courses_out.append({
            "id": str(course.id),
            "title": course.title,
            "invite_code": course.invite_code,
            "student_count": student_count,
            "starts_at": course.starts_at.isoformat() if course.starts_at else None,
            "ends_at": course.ends_at.isoformat() if course.ends_at else None,
        })

    return {
        "stats": stats,
        "courses": courses_out,
        "total_students": sum(c["student_count"] for c in courses_out),
    }
