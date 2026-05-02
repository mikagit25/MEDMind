"""Achievements — full catalog, check-and-award logic, and list endpoint."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import (
    AIConversation,
    FlashcardReview,
    User,
    UserAchievement,
    UserBookmark,
    UserNote,
    UserProgress,
)

router = APIRouter(prefix="/achievements", tags=["achievements"])

# ============================================================
# ACHIEVEMENT CATALOG
# ============================================================
ACHIEVEMENTS = [
    {"code": "first_lesson",    "title": "First Steps",      "desc": "Complete your first lesson",         "icon": "🎓", "xp": 50},
    {"code": "module_complete", "title": "Module Master",     "desc": "Complete an entire module",          "icon": "📚", "xp": 200},
    {"code": "streak_3",        "title": "On Fire",           "desc": "Study 3 days in a row",              "icon": "🔥", "xp": 75},
    {"code": "streak_7",        "title": "Dedicated",         "desc": "Study 7 days in a row",              "icon": "🌟", "xp": 200},
    {"code": "streak_30",       "title": "Iron Will",         "desc": "Study 30 days in a row",             "icon": "💪", "xp": 1000},
    {"code": "xp_100",          "title": "Getting Started",   "desc": "Earn 100 XP",                        "icon": "⚡", "xp": 0},
    {"code": "xp_500",          "title": "Climbing Up",       "desc": "Earn 500 XP",                        "icon": "🚀", "xp": 0},
    {"code": "xp_2000",         "title": "Scholar",           "desc": "Earn 2000 XP",                       "icon": "🎖️", "xp": 0},
    {"code": "xp_5000",         "title": "Expert",            "desc": "Earn 5000 XP",                       "icon": "🏆", "xp": 0},
    {"code": "flashcard_10",    "title": "Card Shark",        "desc": "Review 10 flashcards",               "icon": "🃏", "xp": 50},
    {"code": "flashcard_50",    "title": "Flashcard Pro",     "desc": "Review 50 flashcards",               "icon": "🃏", "xp": 150},
    {"code": "mcq_10",          "title": "Quiz Taker",        "desc": "Answer 10 MCQ questions",            "icon": "❓", "xp": 50},
    {"code": "mcq_100",         "title": "Quiz Champion",     "desc": "Answer 100 MCQ questions",           "icon": "💯", "xp": 300},
    {"code": "ai_learner",      "title": "AI Learner",        "desc": "Start 5 AI Tutor conversations",     "icon": "🤖", "xp": 75},
    {"code": "bookmarker",      "title": "Curator",           "desc": "Bookmark 5 items",                   "icon": "🔖", "xp": 25},
    {"code": "note_taker",      "title": "Note Taker",        "desc": "Write your first note",              "icon": "📝", "xp": 25},
    {"code": "note_writer",     "title": "Avid Writer",       "desc": "Write 10 notes",                     "icon": "✍️", "xp": 100},
]

ACHIEVEMENT_MAP = {a["code"]: a for a in ACHIEVEMENTS}


# ============================================================
# SCHEMAS
# ============================================================
class AchievementOut(BaseModel):
    code: str
    title: str
    desc: str
    icon: str
    xp_reward: int
    unlocked: bool
    unlocked_at: Optional[str]


# ============================================================
# INTERNAL HELPER
# ============================================================
async def award_achievement(user: User, code: str, db: AsyncSession) -> bool:
    """Award an achievement if not already unlocked. Returns True if newly awarded."""
    existing = await db.execute(
        select(UserAchievement).where(
            UserAchievement.user_id == user.id,
            UserAchievement.achievement_code == code,
        )
    )
    if existing.scalar_one_or_none():
        return False

    meta = ACHIEVEMENT_MAP.get(code)
    db.add(UserAchievement(user_id=user.id, achievement_code=code))
    if meta and meta["xp"] > 0:
        user.xp = (user.xp or 0) + meta["xp"]

    # Create in-app notification
    from app.services.notification_service import notify_achievement
    await notify_achievement(
        db, user.id,
        achievement_code=code,
        achievement_name=meta["title"] if meta else code,
        xp_bonus=meta["xp"] if meta else 0,
    )

    await db.commit()
    return True


# ============================================================
# ROUTES
# ============================================================
@router.get("", response_model=List[AchievementOut])
async def list_achievements(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Full catalog with unlocked status for current user."""
    result = await db.execute(
        select(UserAchievement).where(UserAchievement.user_id == user.id)
    )
    unlocked = {r.achievement_code: r for r in result.scalars().all()}

    return [
        AchievementOut(
            code=a["code"],
            title=a["title"],
            desc=a["desc"],
            icon=a["icon"],
            xp_reward=a["xp"],
            unlocked=a["code"] in unlocked,
            unlocked_at=(
                unlocked[a["code"]].unlocked_at.isoformat()
                if a["code"] in unlocked
                else None
            ),
        )
        for a in ACHIEVEMENTS
    ]


async def run_achievement_check(user: User, db: AsyncSession) -> list[str]:
    """Check and award achievements. Call from any route after a progress event.
    Returns list of newly awarded achievement codes."""
    newly_awarded: list[str] = []

    prog_result = await db.execute(
        select(UserProgress).where(UserProgress.user_id == user.id)
    )
    all_progress = prog_result.scalars().all()

    total_lessons = sum(len(p.lessons_completed or []) for p in all_progress)
    completed_modules = sum(1 for p in all_progress if (p.completion_percent or 0) >= 100)
    total_mcq = sum(p.mcq_attempts or 0 for p in all_progress)

    fc_result = await db.execute(
        select(func.count()).select_from(FlashcardReview).where(FlashcardReview.user_id == user.id)
    )
    total_flashcards = int(fc_result.scalar_one() or 0)

    ai_result = await db.execute(
        select(func.count()).select_from(AIConversation).where(AIConversation.user_id == user.id)
    )
    total_ai = int(ai_result.scalar_one() or 0)

    bm_result = await db.execute(
        select(func.count()).select_from(UserBookmark).where(UserBookmark.user_id == user.id)
    )
    total_bookmarks = int(bm_result.scalar_one() or 0)

    note_result = await db.execute(
        select(func.count()).select_from(UserNote).where(UserNote.user_id == user.id)
    )
    total_notes = int(note_result.scalar_one() or 0)

    xp = user.xp or 0
    streak = user.streak_days or 0

    conditions: list[tuple[str, bool]] = [
        ("first_lesson",    total_lessons >= 1),
        ("module_complete", completed_modules >= 1),
        ("streak_3",        streak >= 3),
        ("streak_7",        streak >= 7),
        ("streak_30",       streak >= 30),
        ("xp_100",          xp >= 100),
        ("xp_500",          xp >= 500),
        ("xp_2000",         xp >= 2000),
        ("xp_5000",         xp >= 5000),
        ("flashcard_10",    total_flashcards >= 10),
        ("flashcard_50",    total_flashcards >= 50),
        ("mcq_10",          total_mcq >= 10),
        ("mcq_100",         total_mcq >= 100),
        ("ai_learner",      total_ai >= 5),
        ("bookmarker",      total_bookmarks >= 5),
        ("note_taker",      total_notes >= 1),
        ("note_writer",     total_notes >= 10),
    ]

    for code, condition in conditions:
        if condition:
            awarded = await award_achievement(user, code, db)
            if awarded:
                newly_awarded.append(code)

    return newly_awarded


@router.post("/check", response_model=List[str])
async def check_and_award(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Evaluate all achievement conditions and award any newly earned ones."""
    return await run_achievement_check(user, db)
