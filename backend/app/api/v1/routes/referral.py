"""Referral / invite system.

Each user gets a unique referral code stored in profile_data["referral_code"].
When a new user registers with ?ref=CODE, the referrer gets 30 days Pro added.

Endpoints
─────────
GET  /referral          — get own code + stats
POST /referral/apply    — apply a referral code (once, at any time within 7 days of signup)
"""
import hashlib
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import User

router = APIRouter(prefix="/referral", tags=["referral"])

REFERRAL_REWARD_DAYS = 30   # days of Pro added to referrer per successful referral
REFERRAL_BONUS_DAYS  = 7    # days of Pro added to the new user who used a code


def _make_code(user_id: str) -> str:
    """Deterministic 8-char referral code from user UUID."""
    h = hashlib.sha256(f"medmind:referral:{user_id}".encode()).hexdigest()
    return h[:8].upper()


@router.get("")
async def get_referral_info(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return own referral code and how many people have used it."""
    code = _make_code(str(user.id))
    profile = user.profile_data or {}
    referred_count = profile.get("referral_count", 0)
    total_days_earned = referred_count * REFERRAL_REWARD_DAYS
    return {
        "code": code,
        "referral_url": f"https://medmind.pro/register?ref={code}",
        "referred_count": referred_count,
        "total_days_earned": total_days_earned,
        "reward_per_referral": REFERRAL_REWARD_DAYS,
        "new_user_bonus": REFERRAL_BONUS_DAYS,
    }


class ApplyBody(BaseModel):
    code: str


@router.post("/apply")
async def apply_referral_code(
    body: ApplyBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Apply a referral code. Can only be done once and within 30 days of account creation."""
    profile = user.profile_data or {}

    # Already used a code
    if profile.get("referred_by"):
        raise HTTPException(400, "You have already used a referral code")

    # Only within 30 days of signup
    if user.created_at and (datetime.utcnow() - user.created_at).days > 30:
        raise HTTPException(400, "Referral codes can only be applied within 30 days of signup")

    code = body.code.strip().upper()
    if len(code) != 8:
        raise HTTPException(400, "Invalid referral code format")

    # Cannot use your own code
    own_code = _make_code(str(user.id))
    if code == own_code:
        raise HTTPException(400, "You cannot use your own referral code")

    # Find the referrer by their code
    # We need to scan users and compute their code — use profile_data cache if stored
    all_users = (await db.execute(select(User).where(User.is_active == True))).scalars().all()
    referrer = next((u for u in all_users if _make_code(str(u.id)) == code), None)
    if not referrer:
        raise HTTPException(404, "Referral code not found")

    # Grant bonus days to new user
    _extend_subscription(user, REFERRAL_BONUS_DAYS)
    user.profile_data = {**profile, "referred_by": code}

    # Grant reward days to referrer
    ref_profile = referrer.profile_data or {}
    ref_count = ref_profile.get("referral_count", 0) + 1
    referrer.profile_data = {**ref_profile, "referral_count": ref_count}
    _extend_subscription(referrer, REFERRAL_REWARD_DAYS)

    await db.commit()
    return {
        "success": True,
        "message": f"Code applied! You received {REFERRAL_BONUS_DAYS} days of Pro access.",
        "referrer": f"{referrer.first_name or ''} {referrer.last_name or ''}".strip() or "a MedMind member",
    }


def _extend_subscription(user: User, days: int):
    """Extend a user's subscription by N days, upgrading to pro if on free tier."""
    now = datetime.utcnow()
    if user.subscription_tier in ("free", None, ""):
        user.subscription_tier = "pro"
        user.subscription_expires = now + timedelta(days=days)
    else:
        base = user.subscription_expires if (user.subscription_expires and user.subscription_expires > now) else now
        user.subscription_expires = base + timedelta(days=days)
