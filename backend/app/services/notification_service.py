"""Notification service — creates in-app notifications."""
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Notification


async def create_notification(
    db: AsyncSession,
    user_id: UUID,
    type: str,
    title: str,
    body: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
) -> Notification:
    """Create and persist a notification. Does NOT commit — caller commits."""
    n = Notification(
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        data=data or {},
    )
    db.add(n)
    return n


async def notify_achievement(
    db: AsyncSession,
    user_id: UUID,
    achievement_code: str,
    achievement_name: str,
    xp_bonus: int = 0,
) -> Notification:
    body = f"You unlocked: {achievement_name}"
    if xp_bonus:
        body += f" (+{xp_bonus} XP)"
    return await create_notification(
        db, user_id,
        type="achievement",
        title="Achievement Unlocked!",
        body=body,
        data={"achievement_code": achievement_code, "xp_bonus": xp_bonus},
    )


async def notify_flashcards_due(
    db: AsyncSession,
    user_id: UUID,
    count: int,
) -> Notification:
    return await create_notification(
        db, user_id,
        type="flashcard_due",
        title="Flashcards due for review",
        body=f"You have {count} flashcard{'s' if count != 1 else ''} due for review today.",
        data={"count": count},
    )


async def notify_daily_goal(
    db: AsyncSession,
    user_id: UUID,
    xp_earned: int,
    goal_minutes: int,
) -> Notification:
    return await create_notification(
        db, user_id,
        type="daily_goal",
        title="Daily goal reached!",
        body=f"You completed your {goal_minutes}-minute goal and earned {xp_earned} XP. Keep it up!",
        data={"xp_earned": xp_earned, "goal_minutes": goal_minutes},
    )


async def notify_system(
    db: AsyncSession,
    user_id: UUID,
    title: str,
    body: str,
) -> Notification:
    return await create_notification(
        db, user_id,
        type="system",
        title=title,
        body=body,
    )
