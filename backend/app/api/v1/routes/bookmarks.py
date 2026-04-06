"""User bookmarks — save any content item (lesson, module, case, drug, flashcard)."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import User, UserBookmark

router = APIRouter(prefix="/bookmarks", tags=["bookmarks"])

VALID_TYPES = {"lesson", "module", "case", "drug", "flashcard", "mcq"}


class BookmarkOut(BaseModel):
    id: UUID
    content_type: str
    content_id: UUID
    created_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_obj(cls, b: UserBookmark) -> "BookmarkOut":
        return cls(
            id=b.id,
            content_type=b.content_type,
            content_id=b.content_id,
            created_at=b.created_at.isoformat() if b.created_at else "",
        )


@router.get("", response_model=List[BookmarkOut])
async def list_bookmarks(
    content_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(UserBookmark).where(UserBookmark.user_id == user.id)
    if content_type:
        stmt = stmt.where(UserBookmark.content_type == content_type)
    stmt = stmt.order_by(UserBookmark.created_at.desc())
    result = await db.execute(stmt)
    return [BookmarkOut.from_orm_obj(b) for b in result.scalars().all()]


@router.post("/{content_type}/{content_id}", response_model=BookmarkOut, status_code=201)
async def add_bookmark(
    content_type: str,
    content_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if content_type not in VALID_TYPES:
        raise HTTPException(status_code=422, detail=f"Invalid content_type. Must be one of: {', '.join(VALID_TYPES)}")

    # Upsert: ignore if already bookmarked
    existing = await db.execute(
        select(UserBookmark).where(
            UserBookmark.user_id == user.id,
            UserBookmark.content_type == content_type,
            UserBookmark.content_id == content_id,
        )
    )
    bookmark = existing.scalar_one_or_none()
    if bookmark:
        return BookmarkOut.from_orm_obj(bookmark)

    bookmark = UserBookmark(
        user_id=user.id,
        content_type=content_type,
        content_id=content_id,
    )
    db.add(bookmark)
    await db.commit()
    await db.refresh(bookmark)
    return BookmarkOut.from_orm_obj(bookmark)


@router.delete("/{content_type}/{content_id}", status_code=204)
async def remove_bookmark(
    content_type: str,
    content_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(UserBookmark).where(
            UserBookmark.user_id == user.id,
            UserBookmark.content_type == content_type,
            UserBookmark.content_id == content_id,
        )
    )
    bookmark = result.scalar_one_or_none()
    if not bookmark:
        return  # already removed — idempotent
    await db.delete(bookmark)
    await db.commit()


@router.get("/check/{content_type}/{content_id}")
async def check_bookmark(
    content_type: str,
    content_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Returns {bookmarked: bool} — used by UI to show correct state."""
    result = await db.execute(
        select(UserBookmark).where(
            UserBookmark.user_id == user.id,
            UserBookmark.content_type == content_type,
            UserBookmark.content_id == content_id,
        )
    )
    return {"bookmarked": result.scalar_one_or_none() is not None}
