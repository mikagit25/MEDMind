"""Billing service helpers — V6 Phase 6.

Provides:
- audit_log()        — write an immutable BillingEvent row
- is_self_referral() — affiliate anti-fraud
- flag_suspicious_conversion() — flag + put commission on hold
- run_dunning_check() — scheduled job: send dunning emails, downgrade after 7d grace
- run_subscription_reconciliation() — cron cross-check DB vs Stripe
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.models import (
    AffiliateClick,
    AffiliateConversion,
    BillingEvent,
    LifecycleSend,
    User,
)

logger = logging.getLogger(__name__)

_GRACE_DAYS = 7
_CLEARANCE_DAYS = 14
_SUSPICIOUS_SIGNUPS_THRESHOLD = 3  # same IP → hold


# ── Audit log ─────────────────────────────────────────────────────────────────

async def audit_log(
    db: AsyncSession,
    *,
    event_type: str,
    source: str,
    user_id=None,
    old_tier: str | None = None,
    new_tier: str | None = None,
    amount: float | None = None,
    stripe_invoice_id: str | None = None,
    reason: str | None = None,
    meta: dict | None = None,
) -> BillingEvent:
    ev = BillingEvent(
        user_id=user_id,
        event_type=event_type,
        source=source,
        old_tier=old_tier,
        new_tier=new_tier,
        amount=amount,
        stripe_invoice_id=stripe_invoice_id,
        reason=reason,
        meta=meta,
    )
    db.add(ev)
    return ev


# ── Affiliate anti-fraud ───────────────────────────────────────────────────────

def is_self_referral(affiliate_user_id, referred_user_id) -> bool:
    """Block if the same user tries to refer themselves."""
    return str(affiliate_user_id) == str(referred_user_id)


async def check_ip_suspicious(
    db: AsyncSession,
    affiliate_id,
    ip_hash: str | None,
) -> bool:
    """Return True if ≥ THRESHOLD signups from the same IP hash via this affiliate."""
    if not ip_hash:
        return False
    result = await db.execute(
        select(func.count(AffiliateClick.id)).where(
            AffiliateClick.affiliate_id == affiliate_id,
            AffiliateClick.ip_hash == ip_hash,
        )
    )
    count = result.scalar_one()
    return count >= _SUSPICIOUS_SIGNUPS_THRESHOLD


async def set_conversion_status(
    db: AsyncSession,
    conversion: AffiliateConversion,
    status: str,
    reason: str | None = None,
) -> None:
    conversion.commission_status = status
    if status == "hold":
        conversion.is_suspicious = True
    # Log to billing_events
    await audit_log(
        db,
        event_type=f"commission_{status}",
        source="admin" if reason else "system",
        user_id=conversion.user_id,
        amount=conversion.commission_amount,
        reason=reason,
        meta={"affiliate_id": str(conversion.affiliate_id),
              "conversion_id": str(conversion.id)},
    )


# ── Dunning ───────────────────────────────────────────────────────────────────

async def start_dunning(db: AsyncSession, user: User, stripe_invoice_id: str | None = None) -> None:
    """Called when invoice.payment_failed fires. Records dunning start."""
    prefs: dict = dict(user.preferences or {})
    if prefs.get("dunning_started_at"):
        return  # already in dunning
    prefs["dunning_started_at"] = datetime.utcnow().isoformat()
    user.preferences = prefs
    await audit_log(
        db,
        event_type="dunning_started",
        source="webhook",
        user_id=user.id,
        old_tier=user.subscription_tier,
        stripe_invoice_id=stripe_invoice_id,
        reason="invoice.payment_failed",
    )


async def run_dunning_check() -> None:
    """Daily cron: send dunning emails at day 0/3/7, downgrade after 7 days."""
    from app.core.email import _base_template, _send_smtp
    from app.core.config import settings

    async with AsyncSessionLocal() as db:
        now = datetime.utcnow()
        result = await db.execute(
            select(User).where(
                User.is_active == True,
                User.subscription_tier != "free",
            )
        )
        users = result.scalars().all()

        downgraded = 0
        emailed = 0

        for u in users:
            prefs: dict = u.preferences or {}
            dunning_str = prefs.get("dunning_started_at")
            if not dunning_str:
                continue

            try:
                dunning_start = datetime.fromisoformat(dunning_str)
            except ValueError:
                continue

            days_since = (now - dunning_start).days

            if days_since >= _GRACE_DAYS:
                # Downgrade to free
                old_tier = u.subscription_tier
                u.subscription_tier = "free"
                u.subscription_expires = None
                prefs.pop("dunning_started_at", None)
                u.preferences = prefs
                await audit_log(
                    db,
                    event_type="dunning_downgrade",
                    source="system",
                    user_id=u.id,
                    old_tier=old_tier,
                    new_tier="free",
                    reason=f"Grace period expired ({_GRACE_DAYS}d)",
                )
                downgraded += 1
                continue

            # Send email on day 0, 3, or 7 (use lifecycle_sends for idempotency)
            for day_offset, step_label in [(0, "dunning_d0"), (3, "dunning_d3")]:
                if days_since >= day_offset:
                    send_row_result = await db.execute(
                        select(LifecycleSend).where(
                            LifecycleSend.user_id == u.id,
                            LifecycleSend.campaign == "dunning",
                            LifecycleSend.step == step_label,
                        )
                    )
                    if send_row_result.scalar_one_or_none():
                        continue

                    name = u.first_name or "there"
                    days_left = _GRACE_DAYS - days_since
                    portal_url = f"{settings.FRONTEND_URL}/upgrade"
                    body = f"""
                      <p style="color:#4a453e;font-size:15px;line-height:1.6;margin:0 0 12px;">
                        Hi {name}, your recent payment didn't go through.
                      </p>
                      <p style="color:#4a453e;font-size:15px;line-height:1.6;margin:0 0 16px;">
                        You have <strong>{days_left} day{'s' if days_left != 1 else ''}</strong> to
                        update your payment method before your account is downgraded to the free plan.
                        All your data will be preserved.
                      </p>"""
                    html = _base_template(
                        "Action needed: update your payment method",
                        body,
                        "Update Payment Method",
                        portal_url,
                    )
                    try:
                        _send_smtp(u.email, "Action needed: your MedMind AI payment failed", html)
                        db.add(LifecycleSend(user_id=u.id, campaign="dunning", step=step_label))
                        emailed += 1
                    except Exception as exc:
                        logger.error("Dunning email failed for %s: %s", u.email, exc)

        await db.commit()
        if downgraded or emailed:
            logger.info("Dunning check: %d downgraded, %d emails sent", downgraded, emailed)


# ── Reconciliation ────────────────────────────────────────────────────────────

async def run_subscription_reconciliation() -> None:
    """Weekly cron: compare DB subscription tiers vs Stripe. Log discrepancies."""
    try:
        import stripe  # type: ignore
        from app.core.config import settings
        stripe.api_key = settings.STRIPE_SECRET_KEY
    except Exception:
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(
                User.stripe_customer_id != None,
                User.subscription_tier != "free",
            )
        )
        users = result.scalars().all()

        discrepancies = []
        for u in users:
            try:
                subs = stripe.Subscription.list(
                    customer=u.stripe_customer_id, status="all", limit=1
                )
                if not subs.data:
                    continue
                stripe_status = subs.data[0]["status"]
                if stripe_status not in ("active", "trialing") and u.subscription_tier != "free":
                    discrepancies.append({
                        "user_id": str(u.id),
                        "email": u.email,
                        "db_tier": u.subscription_tier,
                        "stripe_status": stripe_status,
                    })
            except Exception:
                continue

        if discrepancies:
            logger.warning("Stripe reconciliation: %d discrepancies found: %s",
                           len(discrepancies), discrepancies)
            # Telegram alert
            try:
                from app.services.telegram_service import send_telegram_message
                msg = f"⚠️ Stripe reconciliation: {len(discrepancies)} discrepancies\n"
                for d in discrepancies[:5]:
                    msg += f"  • {d['email']}: DB={d['db_tier']}, Stripe={d['stripe_status']}\n"
                await send_telegram_message(msg)
            except Exception:
                pass
        else:
            logger.info("Stripe reconciliation: all subscriptions consistent")


# ── Exam access helpers (G1) ──────────────────────────────────────────────────

from app.data.exam_registry import GULF_EXAMS as _GULF_EXAMS

_GULF_SLUGS: frozenset[str] = frozenset(e["slug"] for e in _GULF_EXAMS)

# Tiers with full access to all exams (no per-exam gate)
_FULL_ACCESS_TIERS = frozenset({"pro", "clinic", "lifetime"})
# Gulf Bundle tier gives access specifically to Gulf family
_GULF_BUNDLE_TIER = "gulf_bundle"


def user_has_exam_access(user, exam_slug: str) -> bool:
    """Return True if the user may take full (non-demo) sessions for exam_slug.

    Rules:
    - pro / clinic / lifetime → all exams
    - gulf_bundle → Gulf family only
    - student → NCLEX and other non-Gulf exams (no Gulf Bundle upsell)
    - free → demo only (caller must check separately)
    """
    tier = getattr(user, "subscription_tier", "free") or "free"
    if tier in _FULL_ACCESS_TIERS:
        return True
    if tier == _GULF_BUNDLE_TIER and exam_slug in _GULF_SLUGS:
        return True
    if tier == "student" and exam_slug not in _GULF_SLUGS:
        return True
    return False


def is_gulf_exam(exam_slug: str) -> bool:
    return exam_slug in _GULF_SLUGS
