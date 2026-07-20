"""Stripe payments routes."""
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from sqlalchemy.exc import IntegrityError

from app.core.database import get_db
from app.core.config import settings
from app.models.models import BillingEvent, StripeWebhookEvent, User
from app.api.deps import get_current_user
from app.services.billing import audit_log, start_dunning
from app.data.regional_pricing import get_price, get_tier, BASE_PRICES_USD
from app.services.region_service import resolve_pricing_tier

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["payments"])

# Stripe price IDs — set these in .env / Stripe dashboard
PRICE_IDS = {
    "student": "price_student_monthly",   # override in .env
    "pro": "price_pro_monthly",
    "clinic": "price_clinic_monthly",
    "lifetime": "price_lifetime_once",
}

# Tier from Stripe price map (populated from webhook)
PRICE_TO_TIER: dict[str, str] = {}  # built dynamically or hardcoded


class CheckoutRequest(BaseModel):
    tier: str  # student | pro | clinic | lifetime
    success_url: str = ""   # defaults to settings.FRONTEND_URL at request time
    cancel_url: str = ""


class PortalRequest(BaseModel):
    return_url: str = ""    # defaults to settings.FRONTEND_URL at request time


_PLACEHOLDER_KEYS = ("placeholder", "sk_test_your", "sk_live_your", "your_stripe")

def get_stripe():
    """Return configured stripe module or raise a clean 503."""
    try:
        import stripe  # type: ignore
    except ImportError:
        raise HTTPException(status_code=503, detail="Payment processing unavailable. Contact support.")
    key = settings.STRIPE_SECRET_KEY or ""
    if not key or any(p in key.lower() for p in _PLACEHOLDER_KEYS):
        raise HTTPException(
            status_code=503,
            detail="Payment processing is not configured yet. Please contact support or try a promo code."
        )
    stripe.api_key = key
    return stripe


@router.post("/create-checkout")
async def create_checkout(
    request: Request,
    data: CheckoutRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a Stripe Checkout Session for subscription or one-time payment.

    G3: Regional pricing applied via dynamic price_data when user is in Tier B/C.
    Stripe always charges in USD; local-currency equivalents are informational only.
    """
    if data.tier not in PRICE_IDS:
        raise HTTPException(status_code=400, detail=f"Unknown tier: {data.tier}")

    stripe = get_stripe()

    try:
        # Get or create Stripe customer
        customer_id = user.stripe_customer_id
        if not customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                metadata={"user_id": str(user.id)},
            )
            customer_id = customer.id
            user.stripe_customer_id = customer_id
            await db.commit()

        is_lifetime = data.tier == "lifetime"

        # G3: resolve regional tier and price
        tier, country, source = await resolve_pricing_tier(request, user)
        regional_price = get_price(data.tier, tier)
        base_price = BASE_PRICES_USD.get(data.tier, 0.0)
        use_regional = tier != "A" and regional_price < base_price

        frontend = settings.FRONTEND_URL.rstrip("/")
        success_url = (data.success_url or f"{frontend}/settings?payment=success") + "&session_id={CHECKOUT_SESSION_ID}"
        cancel_url = data.cancel_url or f"{frontend}/settings?payment=cancelled"

        if use_regional:
            # Dynamic price — Stripe charges this exact amount in USD
            unit_amount = int(regional_price * 100)  # cents
            line_item = {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": unit_amount,
                    "product_data": {
                        "name": f"MedMind AI — {data.tier.title()} Plan",
                        "metadata": {"tier": data.tier},
                    },
                    **({"recurring": {"interval": "month"}} if not is_lifetime else {}),
                },
                "quantity": 1,
            }
        else:
            line_item = {"price": PRICE_IDS[data.tier], "quantity": 1}

        session_params = {
            "customer": customer_id,
            "line_items": [line_item],
            "mode": "payment" if is_lifetime else "subscription",
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata": {
                "user_id": str(user.id),
                "tier": data.tier,
                "billing_region": tier,      # G3: stored in meta for webhook
                "billing_country": country,
            },
        }

        session = stripe.checkout.Session.create(**session_params)
        return {
            "url": session.url,
            "session_id": session.id,
            "regional_price": regional_price,
            "billing_tier": tier,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Stripe checkout error: %s", e)
        raise HTTPException(status_code=503, detail="Could not start checkout. Please try again later.")


@router.post("/portal")
async def create_portal(
    data: PortalRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a Stripe Customer Portal session for managing subscriptions."""
    if not user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No Stripe customer found")

    stripe = get_stripe()
    return_url = data.return_url or f"{settings.FRONTEND_URL.rstrip('/')}/settings"
    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=return_url,
    )
    return {"url": session.url}


@router.get("/subscription")
async def get_subscription(user: User = Depends(get_current_user)):
    """Get user's current subscription info."""
    return {
        "tier": user.subscription_tier,
        "expires": user.subscription_expires.isoformat() if user.subscription_expires else None,
        "stripe_customer_id": user.stripe_customer_id,
    }


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    stripe_signature: Optional[str] = Header(None, alias="stripe-signature"),
):
    """Handle Stripe webhook events."""
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Webhook secret not configured")

    stripe = get_stripe()
    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    event_id = event.get("id", "")
    event_type = event["type"]

    # ── Idempotency: skip if already processed ────────────────────────────────
    existing = await db.execute(
        select(StripeWebhookEvent).where(StripeWebhookEvent.event_id == event_id)
    )
    if existing.scalar_one_or_none():
        logger.info("Webhook duplicate skipped: %s", event_id)
        return {"received": True, "duplicate": True}

    # Record event (will raise IntegrityError on true race — both return 200 to Stripe)
    webhook_row = StripeWebhookEvent(event_id=event_id, event_type=event_type)
    db.add(webhook_row)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        return {"received": True, "duplicate": True}

    try:
        if event_type == "checkout.session.completed":
            session = event["data"]["object"]
            user_id = session.get("metadata", {}).get("user_id")
            tier = session.get("metadata", {}).get("tier")
            if user_id and tier:
                await _activate_subscription(user_id, tier, session, db)

        elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
            subscription = event["data"]["object"]
            customer_id = subscription.get("customer")
            status = subscription.get("status")
            if customer_id:
                await _handle_subscription_change(customer_id, status, subscription, db)

        elif event_type == "invoice.payment_failed":
            invoice = event["data"]["object"]
            customer_id = invoice.get("customer")
            invoice_id = invoice.get("id")
            if customer_id:
                result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
                user = result.scalar_one_or_none()
                if user:
                    await start_dunning(db, user, stripe_invoice_id=invoice_id)
                    try:
                        from app.services.email_service import send_payment_failed_email
                        await send_payment_failed_email(user.email, user.first_name or "User")
                    except Exception as e:
                        logger.error("Failed to send payment failure email to %s: %s", user.email, e)

        webhook_row.status = "ok"
        await db.commit()

    except Exception as exc:
        webhook_row.status = "error"
        webhook_row.error_msg = str(exc)[:500]
        await db.commit()
        logger.error("Webhook handler error [%s %s]: %s", event_type, event_id, exc)
        # Telegram alert
        try:
            from app.services.telegram_service import send_telegram_message
            await send_telegram_message(
                f"⚠️ Stripe webhook error\n"
                f"Event: {event_type} ({event_id})\n"
                f"Error: {exc}"
            )
        except Exception:
            pass

    return {"received": True}


async def _activate_subscription(user_id: str, tier: str, session: dict, db: AsyncSession):
    """Activate subscription after successful payment."""
    import uuid as _uuid
    try:
        uid = _uuid.UUID(user_id)
    except (ValueError, AttributeError):
        return
    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if not user:
        return

    old_tier = user.subscription_tier
    user.subscription_tier = tier
    if tier == "lifetime":
        user.subscription_expires = None  # never expires
    else:
        user.subscription_expires = datetime.utcnow() + timedelta(days=35)

    if not user.stripe_customer_id and session.get("customer"):
        user.stripe_customer_id = session["customer"]

    # Clear dunning state if payment succeeded
    prefs: dict = dict(user.preferences or {})
    prefs.pop("dunning_started_at", None)
    user.preferences = prefs

    # G3: capture billing country & region from checkout metadata (authoritative source)
    meta = session.get("metadata") or {}
    stripe_country = meta.get("billing_country")
    stripe_region  = meta.get("billing_region")
    if stripe_country and not user.billing_country:
        user.billing_country = stripe_country.upper()[:2]
        user.billing_region  = stripe_region or get_tier(stripe_country)

    amount = float(session.get("amount_total", 0) or 0) / 100
    await audit_log(
        db,
        event_type="subscription_activated",
        source="webhook",
        user_id=user.id,
        old_tier=old_tier,
        new_tier=tier,
        amount=amount,
        stripe_invoice_id=session.get("payment_intent"),
        meta={"billing_region": stripe_region, "billing_country": stripe_country},
    )
    await db.commit()

    # Affiliate commission: if user was referred, record subscription conversion
    try:
        if user.referred_by_affiliate_id:
            from app.api.v1.routes.affiliate import record_subscription_conversion
            amount_paid = float(session.get("amount_total", 0) or 0) / 100  # Stripe uses cents
            invoice_id = session.get("payment_intent") or session.get("subscription")
            await record_subscription_conversion(
                affiliate_id=user.referred_by_affiliate_id,
                user_id=user.id,
                tier=tier,
                amount_paid=amount_paid,
                stripe_invoice_id=str(invoice_id) if invoice_id else None,
                db=db,
            )
            await db.commit()
    except Exception:
        pass  # Never block payment activation on affiliate errors


@router.get("/billing-events")
async def list_billing_events(
    limit: int = Query(50, le=200),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if user.role not in ("admin", "superadmin"):
        raise HTTPException(403, "Admin access required")
    result = await db.execute(
        select(BillingEvent).order_by(BillingEvent.created_at.desc()).limit(limit)
    )
    events = result.scalars().all()
    return {"events": [
        {
            "id": str(e.id),
            "event_type": e.event_type,
            "source": e.source,
            "user_id": str(e.user_id) if e.user_id else None,
            "old_tier": e.old_tier,
            "new_tier": e.new_tier,
            "amount": e.amount,
            "stripe_invoice_id": e.stripe_invoice_id,
            "reason": e.reason,
            "meta": e.meta,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]}


async def _handle_subscription_change(customer_id: str, status: str, subscription: dict, db: AsyncSession):
    """Handle subscription status changes (renewal, cancellation, etc.)."""
    result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
    user = result.scalar_one_or_none()
    if not user:
        return

    old_tier = user.subscription_tier
    if status == "active":
        period_end = subscription.get("current_period_end")
        if period_end:
            user.subscription_expires = datetime.utcfromtimestamp(period_end)
        await audit_log(db, event_type="subscription_renewed", source="webhook",
                        user_id=user.id, old_tier=old_tier, new_tier=old_tier,
                        reason=f"Stripe status={status}")
    elif status in ("canceled", "unpaid", "past_due"):
        user.subscription_tier = "free"
        user.subscription_expires = None
        await audit_log(db, event_type="subscription_downgraded", source="webhook",
                        user_id=user.id, old_tier=old_tier, new_tier="free",
                        reason=f"Stripe status={status}")

    await db.commit()
