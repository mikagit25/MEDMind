"""Teacher learning analytics — early warning system and course insights."""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import (
    Course, CourseEnrollment, User, UserProgress, Module,
    FlashcardReview, CourseModule,
)

router = APIRouter(prefix="/professor", tags=["analytics"])


def _require_teacher(user: User) -> None:
    if user.role not in ("teacher", "admin"):
        raise HTTPException(403, "Teacher or admin role required")


@router.get("/courses/{course_id}/at-risk")
async def get_at_risk_students(
    course_id: UUID,
    lookback_days: int = Query(14, ge=3, le=60, description="Days to look back for activity"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Early Warning System — identify students likely to disengage.

    Risk factors (weighted score 0-100):
    - No login in last N days (+40 pts)
    - Completion < 20% across enrolled modules (+30 pts)
    - Flashcard accuracy < 50% (+20 pts)
    - Streak = 0 (+10 pts)

    Students scoring 50+ are flagged as "at risk".
    """
    _require_teacher(user)

    # Verify teacher owns this course
    course = (await db.execute(
        select(Course).where(Course.id == course_id, Course.teacher_id == user.id)
    )).scalar_one_or_none()
    if not course:
        raise HTTPException(404, "Course not found or not yours")

    # Get enrolled students
    enrollments = (await db.execute(
        select(CourseEnrollment, User)
        .join(User, User.id == CourseEnrollment.student_id)
        .where(
            CourseEnrollment.course_id == course_id,
            CourseEnrollment.status == "active",
        )
    )).all()

    if not enrollments:
        return {"at_risk": [], "healthy": [], "total_enrolled": 0}

    cutoff = datetime.utcnow() - timedelta(days=lookback_days)

    # Get module IDs in course
    course_module_ids = [
        row[0] for row in (await db.execute(
            select(CourseModule.module_id).where(CourseModule.course_id == course_id)
        )).all()
    ]

    at_risk = []
    healthy = []

    for enrollment, student in enrollments:
        risk_score = 0
        risk_factors = []

        # 1. Inactivity
        last_active = student.last_active_date
        if last_active is None or last_active < cutoff:
            days_inactive = (datetime.utcnow() - last_active).days if last_active else 999
            risk_score += 40
            risk_factors.append(f"Inactive for {min(days_inactive, 999)} days")

        # 2. Module completion
        if course_module_ids:
            prog_rows = (await db.execute(
                select(func.avg(UserProgress.completion_percent))
                .where(
                    UserProgress.user_id == student.id,
                    UserProgress.module_id.in_(course_module_ids),
                )
            )).scalar() or 0
            avg_completion = float(prog_rows)
            if avg_completion < 20:
                risk_score += 30
                risk_factors.append(f"Only {avg_completion:.0f}% average completion")

        # 3. Flashcard accuracy
        due_count = (await db.execute(
            select(func.count(FlashcardReview.flashcard_id))
            .where(
                FlashcardReview.user_id == student.id,
                FlashcardReview.ease_factor < 1.8,  # struggling
            )
        )).scalar() or 0
        if due_count > 5:
            risk_score += 20
            risk_factors.append(f"{due_count} flashcards with low retention")

        # 4. Streak
        if (student.streak_days or 0) == 0:
            risk_score += 10
            risk_factors.append("No active streak")

        student_info = {
            "student_id": str(student.id),
            "name": f"{student.first_name or ''} {student.last_name or ''}".strip() or student.email,
            "email": student.email,
            "risk_score": min(risk_score, 100),
            "risk_factors": risk_factors,
            "last_active": last_active.isoformat() if last_active else None,
            "streak_days": student.streak_days or 0,
            "xp": student.xp,
        }

        if risk_score >= 50:
            at_risk.append(student_info)
        else:
            healthy.append(student_info)

    # Sort at-risk by highest risk first
    at_risk.sort(key=lambda x: x["risk_score"], reverse=True)

    return {
        "course_id": str(course_id),
        "course_title": course.title,
        "lookback_days": lookback_days,
        "total_enrolled": len(enrollments),
        "at_risk_count": len(at_risk),
        "at_risk": at_risk,
        "healthy": healthy,
    }


@router.get("/courses/{course_id}/content-insights")
async def get_content_insights(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Analyze which modules/lessons are causing the most difficulty.
    Shows average completion and flashcard retention per module.
    """
    _require_teacher(user)

    course = (await db.execute(
        select(Course).where(Course.id == course_id, Course.teacher_id == user.id)
    )).scalar_one_or_none()
    if not course:
        raise HTTPException(404, "Course not found or not yours")

    # Get modules in course with completion stats
    rows = (await db.execute(
        select(
            Module.id,
            Module.title,
            func.avg(UserProgress.completion_percent).label("avg_completion"),
            func.count(UserProgress.user_id).label("student_count"),
        )
        .join(CourseModule, CourseModule.module_id == Module.id)
        .outerjoin(UserProgress, UserProgress.module_id == Module.id)
        .where(CourseModule.course_id == course_id)
        .group_by(Module.id, Module.title)
        .order_by(func.avg(UserProgress.completion_percent).asc())
    )).all()

    insights = []
    for row in rows:
        avg = float(row[2] or 0)
        difficulty_label = (
            "very_hard" if avg < 30
            else "hard" if avg < 50
            else "moderate" if avg < 70
            else "easy"
        )
        insights.append({
            "module_id": str(row[0]),
            "title": row[1],
            "avg_completion_percent": round(avg, 1),
            "students_started": row[3] or 0,
            "difficulty_label": difficulty_label,
            "recommendation": (
                "Consider revising or supplementing this module — students struggle here."
                if avg < 50 else
                "Module is performing well."
            ),
        })

    return {
        "course_id": str(course_id),
        "course_title": course.title,
        "modules": insights,
    }
