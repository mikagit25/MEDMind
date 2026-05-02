"""Stripe payments routes."""
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db
from app.core.config import settings
from app.models.models import User
from app.api.deps import get_current_user

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


def get_stripe():
    """Get stripe module, raise if not configured."""
    try:
        import stripe  # type: ignore
        if not settings.STRIPE_SECRET_KEY or settings.STRIPE_SECRET_KEY.startswith("sk_test_your"):
            raise HTTPException(status_code=503, detail="Stripe not configured. Add STRIPE_SECRET_KEY to .env")
        stripe.api_key = settings.STRIPE_SECRET_KEY
        return stripe
    except ImportError:
        raise HTTPException(status_code=503, detail="stripe package not installed")


@router.post("/create-checkout")
async def create_checkout(
    data: CheckoutRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a Stripe Checkout Session for subscription or one-time payment."""
    if data.tier not in PRICE_IDS:
        raise HTTPException(status_code=400, detail=f"Unknown tier: {data.tier}")

    stripe = get_stripe()

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

    price_id = PRICE_IDS[data.tier]
    is_lifetime = data.tier == "lifetime"

    frontend = settings.FRONTEND_URL.rstrip("/")
    success_url = (data.success_url or f"{frontend}/settings?payment=success") + "&session_id={CHECKOUT_SESSION_ID}"
    cancel_url = data.cancel_url or f"{frontend}/settings?payment=cancelled"

    session_params = {
        "customer": customer_id,
        "line_items": [{"price": price_id, "quantity": 1}],
        "mode": "payment" if is_lifetime else "subscription",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": {"user_id": str(user.id), "tier": data.tier},
    }

    session = stripe.checkout.Session.create(**session_params)
    return {"url": session.url, "session_id": session.id}


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

    event_type = event["type"]

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
        if customer_id:
            result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
            user = result.scalar_one_or_none()
            if user:
                try:
                    from app.services.email_service import send_payment_failed_email
                    await send_payment_failed_email(user.email, user.first_name or "User")
                except Exception as e:
                    logger.error("Failed to send payment failure email to %s: %s", user.email, e)

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

    user.subscription_tier = tier
    if tier == "lifetime":
        user.subscription_expires = None  # never expires
    else:
        # Set expiry 1 month from now (Stripe will handle renewals via webhooks)
        user.subscription_expires = datetime.utcnow() + timedelta(days=35)

    # Save customer ID from checkout session
    if not user.stripe_customer_id and session.get("customer"):
        user.stripe_customer_id = session["customer"]

    await db.commit()


async def _handle_subscription_change(customer_id: str, status: str, subscription: dict, db: AsyncSession):
    """Handle subscription status changes (renewal, cancellation, etc.)."""
    result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
    user = result.scalar_one_or_none()
    if not user:
        return

    if status == "active":
        # Subscription renewed — extend expiry
        period_end = subscription.get("current_period_end")
        if period_end:
            user.subscription_expires = datetime.utcfromtimestamp(period_end)
    elif status in ("canceled", "unpaid", "past_due"):
        # Downgrade to free
        user.subscription_tier = "free"
        user.subscription_expires = None

    await db.commit()
