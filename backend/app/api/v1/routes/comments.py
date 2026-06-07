"""Comments API — per article and per news item.

Public:
  GET  /comments/{content_type}/{slug}       — list comments (hidden excluded)

Authenticated:
  POST /comments/{content_type}/{slug}       — post a comment
  DELETE /comments/{id}                      — delete own comment
  POST /comments/{id}/like                   — toggle like
  POST /comments/{id}/report                 — report (auto-hides at 5 reports)

Admin:
  PATCH /comments/{id}/hide                  — force-hide a comment
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, constr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_user_optional, get_db, require_admin
from app.models.models import Comment, CommentLike, CommentReport, User

router = APIRouter(prefix="/comments", tags=["comments"])

CONTENT_TYPES = {"article", "news"}
AUTO_HIDE_THRESHOLD = 5  # reports needed to auto-hide


# ── Schemas ───────────────────────────────────────────────────────────────────

class CommentCreate(BaseModel):
    body: constr(min_length=5, max_length=2000)  # type: ignore[valid-type]


class CommentOut(BaseModel):
    id: str
    user_id: str
    user_name: str
    user_avatar: Optional[str]
    body: str
    created_at: str
    likes: int
    liked_by_me: bool
    reported_by_me: bool


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt(dt: Optional[datetime]) -> str:
    if not dt:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


async def _build_out(
    comment: Comment,
    db: AsyncSession,
    current_user_id: Optional[uuid.UUID] = None,
) -> CommentOut:
    u: User = comment.user
    user_name = " ".join(filter(None, [u.first_name, u.last_name])) or u.email.split("@")[0]

    likes_count = (
        await db.execute(
            select(func.count()).select_from(CommentLike).where(CommentLike.comment_id == comment.id)
        )
    ).scalar_one()

    liked_by_me = False
    reported_by_me = False
    if current_user_id:
        liked_by_me = bool(
            (await db.execute(
                select(CommentLike).where(
                    CommentLike.comment_id == comment.id,
                    CommentLike.user_id == current_user_id,
                )
            )).scalar_one_or_none()
        )
        reported_by_me = bool(
            (await db.execute(
                select(CommentReport).where(
                    CommentReport.comment_id == comment.id,
                    CommentReport.user_id == current_user_id,
                )
            )).scalar_one_or_none()
        )

    return CommentOut(
        id=str(comment.id),
        user_id=str(comment.user_id),
        user_name=user_name,
        user_avatar=u.avatar_url,
        body=comment.body,
        created_at=_fmt(comment.created_at),
        likes=likes_count,
        liked_by_me=liked_by_me,
        reported_by_me=reported_by_me,
    )


# ── Public ────────────────────────────────────────────────────────────────────

@router.get("/{content_type}/{slug}", response_model=list[CommentOut])
async def list_comments(
    content_type: str,
    slug: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    if content_type not in CONTENT_TYPES:
        raise HTTPException(status_code=404, detail="Unknown content type")

    result = await db.execute(
        select(Comment)
        .where(
            Comment.content_type == content_type,
            Comment.content_slug == slug,
            Comment.is_hidden == False,  # noqa: E712
        )
        .order_by(Comment.created_at.asc())
        .limit(limit)
        .offset(offset)
    )
    comments = result.scalars().all()

    uid = current_user.id if current_user else None
    return [await _build_out(c, db, uid) for c in comments]


# ── Authenticated ─────────────────────────────────────────────────────────────

@router.post("/{content_type}/{slug}", response_model=CommentOut, status_code=201)
async def post_comment(
    content_type: str,
    slug: str,
    payload: CommentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if content_type not in CONTENT_TYPES:
        raise HTTPException(status_code=404, detail="Unknown content type")

    comment = Comment(
        user_id=current_user.id,
        content_type=content_type,
        content_slug=slug,
        body=payload.body.strip(),
    )
    db.add(comment)
    await db.flush()
    await db.refresh(comment, ["user"])
    await db.commit()
    return await _build_out(comment, db, current_user.id)


@router.delete("/{comment_id}", status_code=204)
async def delete_comment(
    comment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not your comment")
    await db.delete(comment)
    await db.commit()


@router.post("/{comment_id}/like")
async def toggle_like(
    comment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Comment).where(Comment.id == comment_id, Comment.is_hidden == False))  # noqa: E712
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Comment not found")

    existing = (await db.execute(
        select(CommentLike).where(
            CommentLike.comment_id == comment_id,
            CommentLike.user_id == current_user.id,
        )
    )).scalar_one_or_none()

    if existing:
        await db.delete(existing)
        liked = False
    else:
        db.add(CommentLike(comment_id=comment_id, user_id=current_user.id))
        liked = True

    await db.commit()

    likes = (await db.execute(
        select(func.count()).select_from(CommentLike).where(CommentLike.comment_id == comment_id)
    )).scalar_one()

    return {"likes": likes, "liked": liked}


@router.post("/{comment_id}/report")
async def report_comment(
    comment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    already = (await db.execute(
        select(CommentReport).where(
            CommentReport.comment_id == comment_id,
            CommentReport.user_id == current_user.id,
        )
    )).scalar_one_or_none()

    if already:
        return {"reported": True, "message": "Already reported"}

    db.add(CommentReport(comment_id=comment_id, user_id=current_user.id))
    comment.report_count += 1
    if comment.report_count >= AUTO_HIDE_THRESHOLD:
        comment.is_hidden = True

    await db.commit()
    return {"reported": True}


# ── Admin ─────────────────────────────────────────────────────────────────────

@router.patch("/{comment_id}/hide", dependencies=[Depends(require_admin())])
async def hide_comment(
    comment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    comment.is_hidden = True
    await db.commit()
    return {"hidden": True}
