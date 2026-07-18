"""Affiliate / influencer partner system.

Endpoints
─────────
POST /affiliate/click           — track referral link click (public, no auth)
POST /affiliate/apply           — apply to become affiliate (any logged-in user)
GET  /affiliate/me              — own affiliate profile + stats (role=affiliate required)
GET  /affiliate/conversions     — own conversion history
POST /affiliate/payout-request  — request payout
"""
import hashlib
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import Affiliate, AffiliateClick, AffiliateConversion, User

router = APIRouter(prefix="/affiliate", tags=["affiliate"])


# ── helpers ──────────────────────────────────────────────────────────────────

def _ip_hash(ip: Optional[str]) -> Optional[str]:
    if not ip:
        return None
    return hashlib.sha256(ip.encode()).hexdigest()


async def _get_active_affiliate(code: str, db: AsyncSession) -> Optional[Affiliate]:
    result = await db.execute(
        select(Affiliate).where(Affiliate.code == code.upper(), Affiliate.status == "active")
    )
    return result.scalar_one_or_none()


def _calc_commission(affiliate: Affiliate, amount_paid: float) -> float:
    if affiliate.commission_type == "percent":
        return round(amount_paid * affiliate.commission_value / 100, 2)
    return round(affiliate.commission_value, 2)  # fixed


# ── schemas ───────────────────────────────────────────────────────────────────

class ClickBody(BaseModel):
    code: str
    referrer: Optional[str] = None
    utm_source: Optional[str] = None
    utm_medium: Optional[str] = None
    utm_campaign: Optional[str] = None


class ApplyBody(BaseModel):
    code: str                          # desired affiliate code (e.g. "DR_IVANOV")
    payout_type: str = "paypal"        # paypal | bank | crypto
    payout_address: str                # PayPal email or bank details
    notes: Optional[str] = None       # motivation / channel description


class PayoutRequestBody(BaseModel):
    message: Optional[str] = None


# ── public ────────────────────────────────────────────────────────────────────

@router.post("/click", status_code=200)
async def track_click(
    body: ClickBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Record a referral link click. Called by frontend when ?ref= param detected."""
    affiliate = await _get_active_affiliate(body.code, db)
    if not affiliate:
        return {"ok": False}

    ip = request.client.host if request.client else None
    click = AffiliateClick(
        affiliate_id=affiliate.id,
        ip_hash=_ip_hash(ip),
        user_agent=request.headers.get("user-agent", "")[:500],
        referrer=(body.referrer or "")[:500],
        utm_source=(body.utm_source or "")[:100],
        utm_medium=(body.utm_medium or "")[:100],
        utm_campaign=(body.utm_campaign or "")[:100],
    )
    db.add(click)
    affiliate.total_clicks += 1
    await db.commit()
    return {"ok": True}


# ── authenticated ─────────────────────────────────────────────────────────────

@router.post("/apply")
async def apply(
    body: ApplyBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Apply to become an affiliate. Creates a pending affiliate record."""
    # Check not already affiliate
    existing = await db.execute(select(Affiliate).where(Affiliate.user_id == user.id))
    if existing.scalar_one_or_none():
        raise HTTPException(400, "You already have an affiliate application")

    code = body.code.strip().upper().replace(" ", "_")
    if len(code) < 3 or len(code) > 30:
        raise HTTPException(400, "Code must be 3–30 characters")

    # Check code uniqueness
    code_taken = await db.execute(select(Affiliate).where(Affiliate.code == code))
    if code_taken.scalar_one_or_none():
        raise HTTPException(409, "This code is already taken. Please choose another.")

    affiliate = Affiliate(
        user_id=user.id,
        code=code,
        status="pending",
        payout_info={"type": body.payout_type, "address": body.payout_address},
        notes=body.notes,
    )
    db.add(affiliate)
    await db.commit()
    return {
        "status": "pending",
        "code": code,
        "message": "Application submitted. We'll review it within 1-3 business days.",
    }


def _require_affiliate(user: User) -> User:
    if user.role not in ("affiliate", "admin"):
        raise HTTPException(403, "Affiliate account required")
    return user


@router.get("/me")
async def get_me(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_affiliate(user)
    result = await db.execute(select(Affiliate).where(Affiliate.user_id == user.id))
    affiliate = result.scalar_one_or_none()
    if not affiliate:
        raise HTTPException(404, "Affiliate profile not found")

    return {
        "id": str(affiliate.id),
        "code": affiliate.code,
        "status": affiliate.status,
        "commission_type": affiliate.commission_type,
        "commission_value": affiliate.commission_value,
        "payout_info": affiliate.payout_info,
        "cookie_days": affiliate.cookie_days,
        "total_clicks": affiliate.total_clicks,
        "total_signups": affiliate.total_signups,
        "total_conversions": affiliate.total_conversions,
        "total_earned": affiliate.total_earned,
        "total_paid": affiliate.total_paid,
        "pending_payout": round(affiliate.total_earned - affiliate.total_paid, 2),
        "referral_url": f"https://medmind.pro/?ref={affiliate.code}",
        "created_at": affiliate.created_at.isoformat(),
    }


@router.get("/conversions")
async def get_conversions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_affiliate(user)
    result = await db.execute(select(Affiliate).where(Affiliate.user_id == user.id))
    affiliate = result.scalar_one_or_none()
    if not affiliate:
        raise HTTPException(404, "Affiliate profile not found")

    convs = await db.execute(
        select(AffiliateConversion)
        .where(AffiliateConversion.affiliate_id == affiliate.id)
        .order_by(AffiliateConversion.created_at.desc())
        .limit(200)
    )
    rows = convs.scalars().all()
    return [
        {
            "id": str(r.id),
            "event_type": r.event_type,
            "tier": r.tier,
            "amount_paid": r.amount_paid,
            "commission_amount": r.commission_amount,
            "is_paid_out": r.is_paid_out,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.post("/payout-request")
async def payout_request(
    body: PayoutRequestBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_affiliate(user)
    result = await db.execute(select(Affiliate).where(Affiliate.user_id == user.id))
    affiliate = result.scalar_one_or_none()
    if not affiliate:
        raise HTTPException(404, "Affiliate profile not found")

    pending = round(affiliate.total_earned - affiliate.total_paid, 2)
    if pending < 10:
        raise HTTPException(400, f"Minimum payout is $10. You have ${pending:.2f} pending.")

    # In a real flow this would send an email/Slack notification to admin.
    # For now, just record it in affiliate notes.
    note = f"[PAYOUT REQUEST {datetime.utcnow().date()}] ${pending:.2f} — {body.message or ''}"
    affiliate.notes = ((affiliate.notes or "") + "\n" + note).strip()
    await db.commit()

    return {
        "ok": True,
        "pending": pending,
        "message": f"Payout request for ${pending:.2f} submitted. We'll process it within 5 business days.",
    }


# ── utility used by auth.py and payments.py ──────────────────────────────────

async def record_signup_conversion(
    affiliate_id, user_id, db: AsyncSession
):
    """Called from auth register when user has a valid ref cookie."""
    result = await db.execute(select(Affiliate).where(Affiliate.id == affiliate_id))
    affiliate = result.scalar_one_or_none()
    if not affiliate or affiliate.status != "active":
        return
    conv = AffiliateConversion(
        affiliate_id=affiliate.id,
        user_id=user_id,
        event_type="signup",
    )
    db.add(conv)
    affiliate.total_signups += 1


async def record_subscription_conversion(
    affiliate_id, user_id, tier: str, amount_paid: float,
    stripe_invoice_id: Optional[str], db: AsyncSession
):
    """Called from Stripe webhook when referred user completes a paid subscription."""
    result = await db.execute(select(Affiliate).where(Affiliate.id == affiliate_id))
    affiliate = result.scalar_one_or_none()
    if not affiliate or affiliate.status != "active":
        return
    commission = _calc_commission(affiliate, amount_paid)
    conv = AffiliateConversion(
        affiliate_id=affiliate.id,
        user_id=user_id,
        event_type="subscription",
        tier=tier,
        amount_paid=amount_paid,
        commission_amount=commission,
        stripe_invoice_id=stripe_invoice_id,
    )
    db.add(conv)
    affiliate.total_conversions += 1
    affiliate.total_earned = round(affiliate.total_earned + commission, 2)
