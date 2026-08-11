"""Spaced-Repetition System for lessons and articles (V5 Phase 5).

Endpoints:
  POST /srs/enqueue                  — opt a lesson/article into SM-2 queue
  GET  /srs/queue                    — today's due items with cached MCQs
  POST /srs/review/{item_id}         — submit review quality (0-5) → SM-2 update
  GET  /srs/stats                    — enrolled count + due today
  DELETE /srs/items/{item_id}        — remove item from queue
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.models import Article, Lesson, LessonMcqCache, LessonSrsItem, User

router = APIRouter(prefix="/srs", tags=["srs"])

VALID_ENTITY_TYPES = {"lesson", "article"}
REVIEW_INTERVAL_DAYS = [1, 3, 7, 21]   # first four intervals (SM-2 then takes over)


# ── SM-2 ─────────────────────────────────────────────────────────────────────

def _sm2(ease_factor: float, interval: int, quality: int) -> tuple[float, int]:
    ef = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    ef = max(1.3, ef)
    if quality < 3:
        new_interval = 1
    elif interval <= 1:
        new_interval = 6
    else:
        new_interval = round(interval * ef)
    return ef, new_interval


# ── Schemas ───────────────────────────────────────────────────────────────────

class EnqueueRequest(BaseModel):
    entity_type: str
    entity_id: uuid.UUID


class ReviewRequest(BaseModel):
    quality: int = Field(..., ge=0, le=5)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def _get_entity_title(entity_type: str, entity_id: uuid.UUID, db: AsyncSession) -> str:
    if entity_type == "lesson":
        obj = await db.get(Lesson, entity_id)
        return obj.title if obj else "Lesson"
    if entity_type == "article":
        obj = await db.get(Article, entity_id)
        return obj.title if obj else "Article"
    return "Item"


async def _ensure_mcq_cache(
    entity_type: str,
    entity_id: uuid.UUID,
    db: AsyncSession,
) -> list[dict]:
    """Return cached MCQs for the entity, generating if missing."""
    row = (await db.execute(
        select(LessonMcqCache).where(
            LessonMcqCache.entity_type == entity_type,
            LessonMcqCache.entity_id == entity_id,
        )
    )).scalar_one_or_none()

    if row:
        return row.questions if isinstance(row.questions, list) else []

    # Generate 3 questions via AI
    questions: list[dict] = []
    if entity_type == "lesson":
        lesson = await db.get(Lesson, entity_id)
        if lesson:
            try:
                from app.prompts.tutor_prompts import LESSON_MCQ_SYSTEM, lesson_mcq_prompt
                from app.services.ai_router import call_generation_ai
                from app.services.content_sanitizer import sanitize_for_llm_context

                text = sanitize_for_llm_context(lesson.content, max_chars=3000)
                prompt = lesson_mcq_prompt(lesson.title or "Lesson", text, "medium")
                raw, _ = await call_generation_ai(system=LESSON_MCQ_SYSTEM, user_message=prompt, max_tokens=2000)

                clean = raw.strip()
                if clean.startswith("```"):
                    clean = clean.split("```")[1]
                    if clean.startswith("json"):
                        clean = clean[4:]
                parsed = json.loads(clean)
                questions = parsed.get("questions", [])[:3]
            except Exception:
                pass

    # Save cache (even empty, to avoid repeated AI calls on failures)
    db.add(LessonMcqCache(
        entity_type=entity_type,
        entity_id=entity_id,
        questions=questions,
    ))
    await db.flush()
    return questions


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/enqueue", status_code=201)
async def enqueue_item(
    body: EnqueueRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Opt a completed lesson or article into the SM-2 review queue."""
    if body.entity_type not in VALID_ENTITY_TYPES:
        raise HTTPException(status_code=422, detail="entity_type must be 'lesson' or 'article'")

    # Verify entity exists
    if body.entity_type == "lesson":
        if not await db.get(Lesson, body.entity_id):
            raise HTTPException(status_code=404, detail="Lesson not found")
    else:
        if not await db.get(Article, body.entity_id):
            raise HTTPException(status_code=404, detail="Article not found")

    # Check user SRS preference
    prefs = current_user.preferences or {}
    if prefs.get("srs_enabled") is False:
        return {"enrolled": False, "reason": "srs_disabled"}

    # Idempotent — don't re-enqueue if already in queue
    existing = (await db.execute(
        select(LessonSrsItem).where(
            LessonSrsItem.user_id == current_user.id,
            LessonSrsItem.entity_type == body.entity_type,
            LessonSrsItem.entity_id == body.entity_id,
        )
    )).scalar_one_or_none()

    if existing:
        return {
            "enrolled": True,
            "already_enrolled": True,
            "next_review_at": existing.next_review_at.isoformat(),
        }

    now = _utcnow()
    item = LessonSrsItem(
        user_id=current_user.id,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        ease_factor=2.5,
        interval_days=1,
        next_review_at=now + timedelta(days=1),
    )
    db.add(item)
    await db.flush()

    # Warm the MCQ cache asynchronously (best-effort)
    await _ensure_mcq_cache(body.entity_type, body.entity_id, db)
    await db.commit()
    await db.refresh(item)

    return {
        "enrolled": True,
        "already_enrolled": False,
        "item_id": str(item.id),
        "next_review_at": item.next_review_at.isoformat(),
    }


@router.get("/queue")
async def get_queue(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return due SRS items with cached MCQs for the review session."""
    now = _utcnow()
    rows = (await db.execute(
        select(LessonSrsItem).where(
            LessonSrsItem.user_id == current_user.id,
            LessonSrsItem.next_review_at <= now,
        ).order_by(LessonSrsItem.next_review_at.asc())
    )).scalars().all()

    items = []
    for item in rows:
        title = await _get_entity_title(item.entity_type, item.entity_id, db)
        questions = await _ensure_mcq_cache(item.entity_type, item.entity_id, db)
        items.append({
            "item_id": str(item.id),
            "entity_type": item.entity_type,
            "entity_id": str(item.entity_id),
            "title": title,
            "interval_days": item.interval_days,
            "review_count": item.review_count,
            "next_review_at": item.next_review_at.isoformat(),
            "questions": questions,
        })

    await db.commit()
    return {"items": items, "total": len(items)}


@router.post("/review/{item_id}")
async def submit_review(
    item_id: uuid.UUID,
    body: ReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a review quality score (0–5) for an SRS item; SM-2 schedules the next repetition."""
    item = (await db.execute(
        select(LessonSrsItem).where(
            LessonSrsItem.id == item_id,
            LessonSrsItem.user_id == current_user.id,
        )
    )).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="SRS item not found")

    new_ef, new_interval = _sm2(float(item.ease_factor), item.interval_days, body.quality)
    now = _utcnow()
    item.ease_factor = new_ef
    item.interval_days = new_interval
    item.last_reviewed_at = now
    item.next_review_at = now + timedelta(days=new_interval)
    item.review_count += 1

    await db.commit()
    return {
        "item_id": str(item.id),
        "ease_factor": float(new_ef),
        "interval_days": new_interval,
        "next_review_at": item.next_review_at.isoformat(),
        "review_count": item.review_count,
    }


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return total enrolled items and due-today count."""
    now = _utcnow()
    total = (await db.execute(
        select(func.count()).select_from(LessonSrsItem).where(
            LessonSrsItem.user_id == current_user.id
        )
    )).scalar_one()

    due_today = (await db.execute(
        select(func.count()).select_from(LessonSrsItem).where(
            LessonSrsItem.user_id == current_user.id,
            LessonSrsItem.next_review_at <= now,
        )
    )).scalar_one()

    return {"total_enrolled": total, "due_today": due_today}


@router.delete("/items/{item_id}", status_code=204)
async def remove_item(
    item_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove an item from the SRS queue (opt-out)."""
    item = (await db.execute(
        select(LessonSrsItem).where(
            LessonSrsItem.id == item_id,
            LessonSrsItem.user_id == current_user.id,
        )
    )).scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="SRS item not found")
    await db.delete(item)
    await db.commit()
