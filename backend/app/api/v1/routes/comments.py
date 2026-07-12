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

CONTENT_TYPES = {"article", "news", "module", "lesson"}
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


# ── V5 Phase 4: Module/Lesson Q&A — MUST be before generic /{content_type}/{slug} ──

class QACreate(BaseModel):
    body: constr(min_length=5, max_length=2000)  # type: ignore[valid-type]
    comment_type: str = "comment"   # "comment" | "question"
    parent_id: Optional[uuid.UUID] = None


@router.get("/module/{entity_id}")
async def list_module_qa(
    entity_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """List Q&A (questions + comments) for a module or lesson."""
    rows = (await db.execute(
        select(Comment)
        .where(
            Comment.entity_id == entity_id,
            Comment.is_hidden == False,
            Comment.parent_id == None,  # noqa: E711
        )
        .order_by(
            Comment.comment_type.desc(),
            Comment.upvotes.desc(),
            Comment.created_at.asc(),
        )
    )).scalars().all()

    result = []
    for c in rows:
        answers = []
        if c.comment_type == "question":
            ans_rows = (await db.execute(
                select(Comment).where(
                    Comment.parent_id == c.id,
                    Comment.is_hidden == False,
                ).order_by(Comment.created_at.asc())
            )).scalars().all()
            for a in ans_rows:
                answers.append({
                    "id": str(a.id),
                    "user_id": str(a.user_id),
                    "user_name": f"{a.user.first_name or ''} {a.user.last_name or ''}".strip() or "User",
                    "body": a.body,
                    "comment_type": a.comment_type,
                    "upvotes": a.upvotes,
                    "accepted_answer_id": str(c.accepted_answer_id) if c.accepted_answer_id else None,
                    "is_accepted": str(a.id) == str(c.accepted_answer_id) if c.accepted_answer_id else False,
                    "parent_id": str(a.parent_id),
                    "created_at": _fmt(a.created_at),
                })
        result.append({
            "id": str(c.id),
            "user_id": str(c.user_id),
            "user_name": f"{c.user.first_name or ''} {c.user.last_name or ''}".strip() or "User",
            "body": c.body,
            "comment_type": c.comment_type,
            "upvotes": c.upvotes,
            "accepted_answer_id": str(c.accepted_answer_id) if c.accepted_answer_id else None,
            "is_accepted": False,
            "parent_id": None,
            "created_at": _fmt(c.created_at),
            "answers": answers,
        })
    return {"items": result, "total": len(result)}


@router.post("/module/{entity_id}", status_code=201)
async def post_module_qa(
    entity_id: uuid.UUID,
    body: QACreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Post a question or comment on a module/lesson."""
    if body.comment_type not in ("comment", "question"):
        raise HTTPException(status_code=422, detail="comment_type must be 'comment' or 'question'")

    comment = Comment(
        user_id=current_user.id,
        content_type="module",
        content_slug=str(entity_id),
        body=body.body,
        entity_id=entity_id,
        comment_type=body.comment_type,
        parent_id=body.parent_id,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return {"id": str(comment.id), "status": "created"}


@router.post("/module/{comment_id}/upvote")
async def upvote_comment(
    comment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upvote a question or comment."""
    comment = (await db.execute(
        select(Comment).where(Comment.id == comment_id, Comment.is_hidden == False)
    )).scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    comment.upvotes += 1
    await db.commit()
    return {"upvotes": comment.upvotes}


@router.post("/module/{question_id}/accept/{answer_id}")
async def accept_answer(
    question_id: uuid.UUID,
    answer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Teacher or question author marks an answer as accepted."""
    question = (await db.execute(
        select(Comment).where(Comment.id == question_id, Comment.comment_type == "question")
    )).scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    is_author = str(question.user_id) == str(current_user.id)
    is_privileged = current_user.role in ("teacher", "admin")
    if not (is_author or is_privileged):
        raise HTTPException(status_code=403, detail="Only question author or teacher can accept answers")

    answer = (await db.execute(
        select(Comment).where(Comment.id == answer_id, Comment.parent_id == question_id)
    )).scalar_one_or_none()
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found under this question")

    question.accepted_answer_id = answer_id
    await db.commit()
    return {"accepted_answer_id": str(answer_id)}


@router.get("/module/{comment_id}/ai-hint")
async def get_ai_answer_hint(
    comment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Teacher gets an AI-drafted answer hint for a question (not auto-posted)."""
    if current_user.role not in ("teacher", "admin"):
        raise HTTPException(status_code=403, detail="Teacher role required")

    question = (await db.execute(
        select(Comment).where(Comment.id == comment_id, Comment.comment_type == "question")
    )).scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    try:
        import anthropic
        from app.core.config import settings
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=400,
            messages=[{
                "role": "user",
                "content": (
                    f"A student asked this medical education question:\n\n"
                    f"{question.body}\n\n"
                    "Draft a concise, accurate answer in 2-4 sentences. "
                    "Be factual and cite mechanism where relevant. "
                    "This is a draft for a teacher to review and edit before posting."
                ),
            }],
        )
        hint = msg.content[0].text
    except Exception:
        hint = "AI hint unavailable. Please draft your answer manually."

    return {"question": question.body, "ai_hint": hint}


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

