"""User-generated flashcards (UGC) — personal study cards."""
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import UserFlashcard
from app.api.deps import get_current_user
from app.models.models import User

router = APIRouter(prefix="/my/flashcards", tags=["user-flashcards"])

MAX_CARDS_FREE = 50
MAX_CARDS_PAID = 2000


# ── Schemas ────────────────────────────────────────────────────────────────

_VALID_DIFFICULTIES = {"easy", "medium", "hard"}


class FlashcardCreate(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    answer: str = Field(..., min_length=1, max_length=5000)
    tags: Optional[List[str]] = None
    difficulty: str = "medium"
    module_id: Optional[UUID] = None

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        # Strip whitespace, remove empty/too-long tags, cap at 20 tags
        cleaned = [t.strip()[:50] for t in v if t.strip()][:20]
        return cleaned or None

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v: str) -> str:
        if v not in _VALID_DIFFICULTIES:
            raise ValueError(f"difficulty must be one of: {', '.join(sorted(_VALID_DIFFICULTIES))}")
        return v


class FlashcardUpdate(BaseModel):
    question: Optional[str] = Field(None, min_length=3, max_length=2000)
    answer: Optional[str] = Field(None, min_length=1, max_length=5000)
    tags: Optional[List[str]] = None
    difficulty: Optional[str] = None

    @field_validator("tags")
    @classmethod
    def validate_tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return v
        return [t.strip()[:50] for t in v if t.strip()][:20] or None

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in _VALID_DIFFICULTIES:
            raise ValueError(f"difficulty must be one of: {', '.join(sorted(_VALID_DIFFICULTIES))}")
        return v


class ReviewRequest(BaseModel):
    quality: int = Field(..., ge=0, le=5)


def _sm2(ease_factor: float, interval: int, quality: int) -> tuple[float, int]:
    """SM-2 algorithm."""
    ef = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    ef = max(1.3, ef)
    if quality < 3:
        new_interval = 1
    elif interval <= 1:
        new_interval = 6
    else:
        new_interval = round(interval * ef)
    return ef, new_interval


def _card_out(card: UserFlashcard) -> dict:
    return {
        "id": str(card.id),
        "question": card.question,
        "answer": card.answer,
        "tags": card.tags or [],
        "difficulty": card.difficulty,
        "module_id": str(card.module_id) if card.module_id else None,
        "ease_factor": float(card.ease_factor),
        "interval_days": card.interval_days,
        "repetitions": card.repetitions,
        "last_reviewed_at": card.last_reviewed_at.isoformat() if card.last_reviewed_at else None,
        "next_review_at": card.next_review_at.isoformat() if card.next_review_at else None,
        "created_at": card.created_at.isoformat(),
    }


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.get("")
async def list_cards(
    q: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List the current user's personal flashcards."""
    query = select(UserFlashcard).where(UserFlashcard.user_id == user.id)
    if q:
        query = query.where(
            (UserFlashcard.question.ilike(f"%{q}%")) | (UserFlashcard.answer.ilike(f"%{q}%"))
        )
    if tag:
        query = query.where(UserFlashcard.tags.contains([tag]))
    query = query.order_by(UserFlashcard.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    cards = result.scalars().all()

    count_result = await db.execute(
        select(func.count()).select_from(UserFlashcard).where(UserFlashcard.user_id == user.id)
    )
    total = count_result.scalar() or 0
    return {"total": total, "items": [_card_out(c) for c in cards]}


@router.post("", status_code=201)
async def create_card(
    data: FlashcardCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a personal flashcard."""
    # Enforce tier limit
    count_result = await db.execute(
        select(func.count()).select_from(UserFlashcard).where(UserFlashcard.user_id == user.id)
    )
    count = count_result.scalar() or 0
    limit = MAX_CARDS_FREE if user.subscription_tier == "free" else MAX_CARDS_PAID
    if count >= limit:
        raise HTTPException(
            status_code=403,
            detail=f"Card limit reached ({limit} cards on {user.subscription_tier} plan). Upgrade for more.",
        )

    card = UserFlashcard(
        user_id=user.id,
        question=data.question,
        answer=data.answer,
        tags=data.tags or [],
        difficulty=data.difficulty or "medium",
        module_id=data.module_id,
    )
    db.add(card)
    await db.commit()
    await db.refresh(card)
    return _card_out(card)


@router.get("/due")
async def get_due_cards(
    limit: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return user's personal flashcards due for review (SM-2 queue)."""
    now = datetime.utcnow()
    result = await db.execute(
        select(UserFlashcard).where(
            UserFlashcard.user_id == user.id,
            (UserFlashcard.next_review_at <= now) | (UserFlashcard.next_review_at == None),  # noqa: E711
        )
        .order_by(UserFlashcard.next_review_at.asc().nulls_first())
        .limit(limit)
    )
    return [_card_out(c) for c in result.scalars().all()]


@router.patch("/{card_id}")
async def update_card(
    card_id: UUID,
    data: FlashcardUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(UserFlashcard).where(UserFlashcard.id == card_id, UserFlashcard.user_id == user.id)
    )
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Flashcard not found")

    if data.question is not None:
        card.question = data.question
    if data.answer is not None:
        card.answer = data.answer
    if data.tags is not None:
        card.tags = data.tags
    if data.difficulty is not None:
        card.difficulty = data.difficulty
    card.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(card)
    return _card_out(card)


@router.delete("/{card_id}", status_code=204)
async def delete_card(
    card_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(UserFlashcard).where(UserFlashcard.id == card_id, UserFlashcard.user_id == user.id)
    )
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Flashcard not found")
    await db.delete(card)
    await db.commit()


@router.post("/{card_id}/review")
async def review_card(
    card_id: UUID,
    data: ReviewRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Submit SM-2 review quality for a personal flashcard (0–5)."""
    result = await db.execute(
        select(UserFlashcard).where(UserFlashcard.id == card_id, UserFlashcard.user_id == user.id)
    )
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Flashcard not found")

    new_ef, new_interval = _sm2(float(card.ease_factor), card.interval_days, data.quality)
    card.ease_factor = new_ef
    card.interval_days = new_interval
    card.repetitions += 1
    card.last_quality = data.quality
    card.last_reviewed_at = datetime.utcnow()
    card.next_review_at = datetime.utcnow() + timedelta(days=new_interval)

    await db.commit()
    return {
        "next_review_at": card.next_review_at.isoformat(),
        "interval_days": new_interval,
        "ease_factor": new_ef,
    }
