"""Product analytics — event ingestion endpoint.

Privacy rules (enforced here):
- IP never stored raw — not even logged.
- meta field MUST NOT contain free-form user text (prompts, search queries, answers).
- user_id nullable — anonymous events accepted.
- Rate-limited: 60 events/min per IP.
"""
import hashlib
import logging
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_optional
from app.core.database import get_db
from app.core.redis_client import get_redis
from app.models.models import AnalyticsEvent, User

log = logging.getLogger(__name__)
router = APIRouter(prefix="/analytics", tags=["analytics"])

ALLOWED_EVENTS = frozenset({
    "signup", "onboarding_step", "onboarding_completed",
    "lesson_started", "lesson_completed",
    "module_started", "module_completed",
    "flashcard_review", "ai_question", "quiz_completed",
    "public_page_view", "search", "app_open",
    # B5 — Freemium
    "paywall_hit",          # user hit a paid feature gate (meta: {feature, tier_required})
    "anon_limit_hit",       # anonymous user exhausted daily question limit
    "free_practice",        # anonymous question served (meta: {category})
})

# 60 events per minute per IP
_RL_WINDOW = 60
_RL_MAX = 60


async def _check_rate_limit(request: Request) -> None:
    client_ip = (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    key = f"anl_rl:{hashlib.md5(client_ip.encode()).hexdigest()}"
    redis = await get_redis()
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, _RL_WINDOW)
    if count > _RL_MAX:
        raise HTTPException(status_code=429, detail="Too many analytics events")


class EventIn(BaseModel):
    event_type: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    meta: Optional[dict[str, Any]] = None
    locale: Optional[str] = None
    platform: Optional[str] = "web"
    anon_id: Optional[str] = None

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        if v not in ALLOWED_EVENTS:
            raise ValueError(f"Unknown event_type: {v}")
        return v

    @field_validator("meta")
    @classmethod
    def no_free_text(cls, v: Optional[dict]) -> Optional[dict]:
        """Reject any meta that contains 'text', 'query', 'prompt', 'message' keys."""
        if v is None:
            return v
        forbidden = {"text", "query", "prompt", "message", "content", "question", "answer"}
        found = forbidden & set(v.keys())
        if found:
            raise ValueError(f"meta must not contain free-form text keys: {found}")
        return v


class BatchIn(BaseModel):
    events: list[EventIn]

    @field_validator("events")
    @classmethod
    def max_batch(cls, v: list) -> list:
        if len(v) > 20:
            raise ValueError("Batch size exceeds 20 events")
        return v


@router.post("/track", status_code=204)
async def track_events(
    body: BatchIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Ingest a batch of analytics events (up to 20). No auth required."""
    await _check_rate_limit(request)

    user_id: Optional[UUID] = user.id if user else None

    for ev in body.events:
        db.add(AnalyticsEvent(
            user_id=user_id,
            anon_id=ev.anon_id,
            event_type=ev.event_type,
            entity_type=ev.entity_type,
            entity_id=ev.entity_id,
            meta=ev.meta,
            locale=ev.locale,
            platform=ev.platform or "web",
            created_at=datetime.utcnow(),
        ))

    await db.commit()
