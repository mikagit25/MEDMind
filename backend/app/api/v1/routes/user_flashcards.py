"""User-generated flashcards (UGC) — personal study cards."""
import secrets
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import UserFlashcard, SharedDeck, DeckCollaborator
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


# ── Community / Public Flashcards ─────────────────────────────────────────

@router.patch("/{card_id}/publish")
async def toggle_publish(
    card_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Toggle a card's public visibility."""
    card = (await db.execute(
        select(UserFlashcard).where(UserFlashcard.id == card_id, UserFlashcard.user_id == user.id)
    )).scalar_one_or_none()
    if not card:
        raise HTTPException(404, "Card not found")
    card.is_public = not card.is_public
    await db.commit()
    return {"id": str(card.id), "is_public": card.is_public}


@router.get("/community")
async def browse_community_cards(
    search: Optional[str] = Query(None),
    tags: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Browse publicly shared flashcards from the community."""
    from sqlalchemy import or_, and_
    q = select(UserFlashcard, User.first_name, User.last_name).join(
        User, User.id == UserFlashcard.user_id
    ).where(UserFlashcard.is_public == True)  # noqa: E712

    if search:
        like = f"%{search.lower()}%"
        q = q.where(or_(
            UserFlashcard.question.ilike(like),
            UserFlashcard.answer.ilike(like),
        ))
    if difficulty:
        q = q.where(UserFlashcard.difficulty == difficulty)
    if tags:
        for tag in tags.split(","):
            q = q.where(UserFlashcard.tags.any(tag.strip()))

    total = (await db.execute(
        select(func.count()).select_from(q.subquery())
    )).scalar() or 0

    rows = (await db.execute(
        q.order_by(UserFlashcard.created_at.desc()).offset(offset).limit(limit)
    )).all()

    cards = []
    for card, fn, ln in rows:
        author = f"{fn or ''} {ln or ''}".strip() or "Anonymous"
        cards.append({
            "id": str(card.id),
            "question": card.question,
            "answer": card.answer,
            "tags": card.tags or [],
            "difficulty": card.difficulty,
            "author": author,
            "created_at": card.created_at.isoformat() if card.created_at else None,
        })
    return {"cards": cards, "total": total, "offset": offset}


@router.post("/community/{card_id}/clone", status_code=201)
async def clone_community_card(
    card_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Clone a public card into your personal deck."""
    original = (await db.execute(
        select(UserFlashcard).where(UserFlashcard.id == card_id, UserFlashcard.is_public == True)  # noqa: E712
    )).scalar_one_or_none()
    if not original:
        raise HTTPException(404, "Card not found or not public")

    # Enforce per-tier limits
    existing = (await db.execute(
        select(func.count()).where(UserFlashcard.user_id == user.id)
    )).scalar() or 0
    limit_val = MAX_CARDS_PAID if user.subscription_tier != "free" else MAX_CARDS_FREE
    if existing >= limit_val:
        raise HTTPException(403, f"Card limit reached ({limit_val} for your tier)")

    clone = UserFlashcard(
        user_id=user.id,
        question=original.question,
        answer=original.answer,
        tags=list(original.tags or []),
        difficulty=original.difficulty,
        module_id=original.module_id,
        is_public=False,
    )
    db.add(clone)
    await db.commit()
    await db.refresh(clone)
    return _card_out(clone)


# ── Shared Decks ──────────────────────────────────────────────────────────────

class SharedDeckCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=500)
    card_ids: List[UUID] = Field(..., min_length=1, max_length=200)


class SharedDeckOut(BaseModel):
    token: str
    name: str
    description: Optional[str]
    card_count: int
    view_count: int
    share_url: str
    created_at: Optional[str]


def _deck_out(deck: SharedDeck, site_url: str = "https://medmind.pro") -> dict:
    return {
        "token": deck.token,
        "name": deck.name,
        "description": deck.description,
        "card_count": len(deck.cards) if deck.cards else 0,
        "view_count": deck.view_count,
        "share_url": f"{site_url}/decks/shared/{deck.token}",
        "created_at": deck.created_at.isoformat() if deck.created_at else None,
    }


@router.post("/decks/share")
async def create_shared_deck(
    payload: SharedDeckCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a shareable snapshot deck from selected personal flashcards."""
    # Fetch the requested cards (must belong to this user)
    result = await db.execute(
        select(UserFlashcard).where(
            UserFlashcard.user_id == user.id,
            UserFlashcard.id.in_(payload.card_ids),
        )
    )
    cards = result.scalars().all()
    if not cards:
        raise HTTPException(status_code=404, detail="No matching cards found")

    # Generate unique token
    for _ in range(10):
        token = secrets.token_urlsafe(8)[:10]
        existing = await db.execute(select(SharedDeck).where(SharedDeck.token == token))
        if not existing.scalar_one_or_none():
            break

    snapshot = [
        {"question": c.question, "answer": c.answer, "difficulty": c.difficulty}
        for c in cards
    ]

    deck = SharedDeck(
        owner_id=user.id,
        name=payload.name,
        description=payload.description,
        token=token,
        cards=snapshot,
    )
    db.add(deck)
    await db.commit()
    await db.refresh(deck)
    return _deck_out(deck)


@router.get("/decks/share")
async def list_my_shared_decks(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all shared decks created by the current user."""
    result = await db.execute(
        select(SharedDeck)
        .where(SharedDeck.owner_id == user.id)
        .where(SharedDeck.is_active.is_(True))
        .order_by(SharedDeck.created_at.desc())
    )
    decks = result.scalars().all()
    return [_deck_out(d) for d in decks]


@router.delete("/decks/share/{token}")
async def deactivate_shared_deck(
    token: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Deactivate (revoke) a shared deck link."""
    result = await db.execute(
        select(SharedDeck).where(SharedDeck.token == token).where(SharedDeck.owner_id == user.id)
    )
    deck = result.scalar_one_or_none()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")
    deck.is_active = False
    await db.commit()
    return {"message": "Deck link deactivated"}


# ── V5 Phase 4: deck collaborators ────────────────────────────────────────────

class CollaboratorAdd(BaseModel):
    email: str


@router.post("/decks/share/{token}/collaborators", status_code=201)
async def add_deck_collaborator(
    token: str,
    body: CollaboratorAdd,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Deck owner invites a co-editor by email."""
    deck = (await db.execute(
        select(SharedDeck).where(SharedDeck.token == token, SharedDeck.owner_id == user.id, SharedDeck.is_active == True)
    )).scalar_one_or_none()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    invitee = (await db.execute(
        select(User).where(User.email == body.email)
    )).scalar_one_or_none()
    if not invitee:
        raise HTTPException(status_code=404, detail="User not found with that email")
    if str(invitee.id) == str(user.id):
        raise HTTPException(status_code=400, detail="Cannot add yourself as collaborator")

    existing = (await db.execute(
        select(DeckCollaborator).where(DeckCollaborator.deck_id == deck.id, DeckCollaborator.user_id == invitee.id)
    )).scalar_one_or_none()
    if existing:
        return {"message": "Already a collaborator", "user_id": str(invitee.id)}

    db.add(DeckCollaborator(deck_id=deck.id, user_id=invitee.id, role="editor"))
    await db.commit()
    return {
        "message": "Collaborator added",
        "user_id": str(invitee.id),
        "name": f"{invitee.first_name or ''} {invitee.last_name or ''}".strip() or invitee.email,
    }


@router.get("/decks/share/{token}/collaborators")
async def list_deck_collaborators(
    token: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List co-editors of a shared deck (owner only)."""
    deck = (await db.execute(
        select(SharedDeck).where(SharedDeck.token == token, SharedDeck.owner_id == user.id)
    )).scalar_one_or_none()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    collabs = (await db.execute(
        select(DeckCollaborator).where(DeckCollaborator.deck_id == deck.id)
    )).scalars().all()

    result = []
    for c in collabs:
        result.append({
            "user_id": str(c.user_id),
            "name": f"{c.user.first_name or ''} {c.user.last_name or ''}".strip() or "User",
            "role": c.role,
            "added_at": c.added_at.isoformat() if c.added_at else None,
        })
    return {"collaborators": result}


@router.delete("/decks/share/{token}/collaborators/{user_id}", status_code=204)
async def remove_deck_collaborator(
    token: str,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Remove a co-editor (owner only)."""
    deck = (await db.execute(
        select(SharedDeck).where(SharedDeck.token == token, SharedDeck.owner_id == user.id)
    )).scalar_one_or_none()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found")

    collab = (await db.execute(
        select(DeckCollaborator).where(DeckCollaborator.deck_id == deck.id, DeckCollaborator.user_id == user_id)
    )).scalar_one_or_none()
    if not collab:
        raise HTTPException(status_code=404, detail="Collaborator not found")
    await db.delete(collab)
    await db.commit()
