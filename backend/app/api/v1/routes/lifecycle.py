"""Lifecycle campaign API — unsubscribe, open-pixel, notification prefs, admin stats."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import AnalyticsEvent, LifecycleSend, User
from app.services.lifecycle import verify_unsub_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/lifecycle", tags=["lifecycle"])

# 1×1 transparent GIF
_PIXEL = (
    b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00"
    b"\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x00\x00\x00\x00"
    b"\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02"
    b"\x44\x01\x00\x3b"
)

ALL_CAMPAIGNS = [
    "onboarding_d1",
    "onboarding_d3",
    "onboarding_d7",
    "reactivation_7d",
    "reactivation_21d",
    "reactivation_45d",
    "streak_risk",
    "readiness_weekly",
    "exam_countdown_7d",
    "exam_countdown_1d",
]


# ── Open pixel ────────────────────────────────────────────────────────────────

@router.get("/pixel/{uid}/{campaign}.gif", include_in_schema=False)
async def open_pixel(uid: str, campaign: str, db: AsyncSession = Depends(get_db)):
    """Track email open (1×1 pixel). Always returns the GIF."""
    try:
        db.add(AnalyticsEvent(
            user_id=uid,
            event_type="email_opened",
            entity_type="lifecycle_campaign",
            entity_id=campaign,
            platform="email",
        ))
        await db.commit()
    except Exception:
        pass
    return Response(content=_PIXEL, media_type="image/gif",
                    headers={"Cache-Control": "no-store, no-cache"})


# ── One-click unsubscribe (GET — required for email clients) ──────────────────

@router.get("/unsubscribe")
async def unsubscribe(
    uid: str = Query(...),
    campaign: str = Query(...),
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    if not verify_unsub_token(uid, campaign, token):
        raise HTTPException(400, "Invalid unsubscribe link")

    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    prefs: dict = dict(user.preferences or {})
    unsubs: list = list(prefs.get("email_unsubscribes", []))
    if campaign not in unsubs:
        unsubs.append(campaign)
    prefs["email_unsubscribes"] = unsubs
    user.preferences = prefs
    await db.commit()

    return {"unsubscribed": True, "campaign": campaign}


# ── Notification preferences ──────────────────────────────────────────────────

class NotifPrefsOut(BaseModel):
    email_notifications: bool
    email_unsubscribes: List[str]


class NotifPrefsIn(BaseModel):
    email_notifications: bool | None = None
    email_unsubscribes: List[str] | None = None


@router.get("/notification-prefs", response_model=NotifPrefsOut)
async def get_notification_prefs(
    user: User = Depends(get_current_user),
):
    prefs: dict = user.preferences or {}
    return NotifPrefsOut(
        email_notifications=prefs.get("email_notifications", True),
        email_unsubscribes=prefs.get("email_unsubscribes", []),
    )


@router.patch("/notification-prefs", response_model=NotifPrefsOut)
async def update_notification_prefs(
    body: NotifPrefsIn,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    prefs: dict = dict(user.preferences or {})

    if body.email_notifications is not None:
        prefs["email_notifications"] = body.email_notifications

    if body.email_unsubscribes is not None:
        # Only allow known campaign names + "all"
        valid = [c for c in body.email_unsubscribes if c in ALL_CAMPAIGNS or c == "all"]
        prefs["email_unsubscribes"] = valid

    user.preferences = prefs
    await db.commit()

    return NotifPrefsOut(
        email_notifications=prefs.get("email_notifications", True),
        email_unsubscribes=prefs.get("email_unsubscribes", []),
    )


# ── Admin: campaign stats ─────────────────────────────────────────────────────

@router.get("/admin/stats")
async def campaign_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role not in ("admin", "superadmin"):
        raise HTTPException(403, "Admin access required")

    # Sends per campaign
    sends_result = await db.execute(
        select(LifecycleSend.campaign, func.count(LifecycleSend.id).label("sent"))
        .group_by(LifecycleSend.campaign)
    )
    sends = {row.campaign: row.sent for row in sends_result}

    # Opens per campaign
    opens_result = await db.execute(
        select(AnalyticsEvent.entity_id, func.count(AnalyticsEvent.id).label("opens"))
        .where(AnalyticsEvent.event_type == "email_opened")
        .group_by(AnalyticsEvent.entity_id)
    )
    opens = {row.entity_id: row.opens for row in opens_result}

    stats = []
    for c in ALL_CAMPAIGNS:
        sent_count = sends.get(c, 0)
        open_count = opens.get(c, 0)
        open_rate = round(open_count / sent_count * 100, 1) if sent_count > 0 else 0.0
        stats.append({
            "campaign": c,
            "sent": sent_count,
            "opens": open_count,
            "open_rate_pct": open_rate,
        })

    return {"campaigns": stats}
