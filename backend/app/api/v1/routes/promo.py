"""Promo code redemption endpoints.

POST /promo/apply   — validate + apply a promo code for the current user
GET  /promo/check/{code} — peek at a code (validity + type) without applying
"""
from datetime import datetime, timedelta
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import PromoCode, PromoCodeUse, User

router = APIRouter(prefix="/promo", tags=["promo"])

VALID_TRIAL_TIERS = {"student", "pro", "clinic"}


def _validate_code(code: PromoCode, user_id) -> None:
    """Raise HTTPException if the code cannot be applied."""
    if not code.is_active:
        raise HTTPException(400, "This promo code is no longer active.")
    if code.expires_at and code.expires_at < datetime.utcnow():
        raise HTTPException(400, "This promo code has expired.")
    if code.max_uses is not None and code.used_count >= code.max_uses:
        raise HTTPException(400, "This promo code has reached its usage limit.")


class ApplyRequest(BaseModel):
    code: str


@router.post("/apply")
async def apply_promo(
    body: ApplyRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    normalized = body.code.strip().upper()
    result = await db.execute(
        select(PromoCode).where(func.upper(PromoCode.code) == normalized)
    )
    promo = result.scalar_one_or_none()
    if not promo:
        raise HTTPException(404, "Promo code not found.")

    _validate_code(promo, user.id)

    # one_per_user check
    if promo.one_per_user:
        existing = await db.execute(
            select(PromoCodeUse).where(
                PromoCodeUse.code_id == promo.id,
                PromoCodeUse.user_id == user.id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(409, "You have already used this promo code.")

    granted_tier = None
    granted_until = None

    if promo.discount_type == "trial":
        if not promo.trial_tier or promo.trial_tier not in VALID_TRIAL_TIERS:
            raise HTTPException(500, "Invalid trial configuration.")

        days = promo.trial_days or 30
        # Don't downgrade an active paid subscription
        current_is_paid = (
            user.subscription_tier != "free"
            and (user.subscription_expires is None or user.subscription_expires > datetime.utcnow())
        )
        if current_is_paid:
            # Extend existing subscription by trial_days instead of downgrading
            base = user.subscription_expires or datetime.utcnow()
            user.subscription_expires = base + timedelta(days=days)
        else:
            user.subscription_tier = promo.trial_tier
            user.subscription_expires = datetime.utcnow() + timedelta(days=days)

        granted_tier = promo.trial_tier
        granted_until = user.subscription_expires

    # Log the use
    use = PromoCodeUse(
        id=uuid.uuid4(),
        code_id=promo.id,
        user_id=user.id,
        used_at=datetime.utcnow(),
        granted_tier=granted_tier,
        granted_until=granted_until,
    )
    db.add(use)
    promo.used_count += 1
    await db.commit()
    await db.refresh(user)

    if promo.discount_type == "trial":
        return {
            "type": "trial",
            "tier": granted_tier,
            "expires_at": granted_until.isoformat() if granted_until else None,
            "message": f"{promo.trial_tier.capitalize()} access activated for {promo.trial_days or 30} days.",
        }

    # percent / fixed — return info for Stripe checkout flow
    return {
        "type": promo.discount_type,
        "discount_value": promo.discount_value,
        "code": promo.code,
        "message": f"{int(promo.discount_value or 0)}% discount code applied. Use at checkout.",
    }


@router.get("/check/{code}")
async def check_promo(
    code: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    normalized = code.strip().upper()
    result = await db.execute(
        select(PromoCode).where(func.upper(PromoCode.code) == normalized)
    )
    promo = result.scalar_one_or_none()
    if not promo:
        raise HTTPException(404, "Promo code not found.")
    try:
        _validate_code(promo, None)
    except HTTPException as e:
        return {"valid": False, "reason": e.detail}

    return {
        "valid": True,
        "type": promo.discount_type,
        "trial_tier": promo.trial_tier,
        "trial_days": promo.trial_days,
        "discount_value": promo.discount_value,
        "description": promo.description,
    }
