"""Credit system for AI article generation.

Endpoints:
  GET  /credits/balance           — current balance + totals
  GET  /credits/packages          — available credit packages
  GET  /credits/pricing           — LLM pricing per model
  GET  /credits/transactions      — last 50 transactions
  POST /credits/purchase/checkout — create Stripe checkout session
  POST /credits/purchase/webhook  — Stripe webhook (payment completed)
"""
from __future__ import annotations

import uuid as _uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import AuthorCreditAccount, CreditTransaction, LLMPricing, User

router = APIRouter(prefix="/credits", tags=["credits"])

CREDIT_PACKAGES = [
    {"id": "starter",  "credits": 50,   "usd": 0.99,  "label": "Starter",  "bonus": "1 Ollama generation free"},
    {"id": "popular",  "credits": 200,  "usd": 2.99,  "label": "Popular",  "bonus": "Most popular"},
    {"id": "pro",      "credits": 1000, "usd": 11.99, "label": "Pro",      "bonus": "Save 40%"},
    {"id": "expert",   "credits": 5000, "usd": 49.99, "label": "Expert",   "bonus": "Save 50%"},
]


async def _get_or_create_account(user_id: _uuid.UUID, db: AsyncSession) -> AuthorCreditAccount:
    """Fetch or create a credit account, granting 10 welcome bonus credits on first use."""
    acc = await db.get(AuthorCreditAccount, user_id)
    if not acc:
        acc = AuthorCreditAccount(user_id=user_id, balance=10, total_purchased=0, total_spent=0)
        db.add(acc)
        db.add(CreditTransaction(
            user_id=user_id,
            type="bonus",
            credits=10,
            description="Welcome bonus — 10 free credits",
        ))
        await db.commit()
        await db.refresh(acc)
    return acc


@router.get("/balance")
async def get_balance(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the user's current credit balance."""
    acc = await _get_or_create_account(user.id, db)
    return {
        "balance": acc.balance,
        "total_purchased": acc.total_purchased,
        "total_spent": acc.total_spent,
        "updated_at": acc.updated_at.isoformat() if acc.updated_at else None,
    }


@router.get("/packages")
async def list_packages():
    """Return available credit purchase packages."""
    return CREDIT_PACKAGES


@router.get("/pricing")
async def list_pricing(db: AsyncSession = Depends(get_db)):
    """Return active LLM pricing entries."""
    rows = (
        await db.execute(select(LLMPricing).where(LLMPricing.is_active == True))
    ).scalars().all()
    return [
        {
            "model": r.model,
            "display_name": r.display_name,
            "description": r.description,
            "credits_per_article": r.credits_per_article,
            "usd_per_article": round(float(r.credits_per_article) * 0.01, 2),
            "actual_cost_usd": float(r.actual_cost_usd),
            "markup_multiplier": float(r.markup_multiplier),
        }
        for r in rows
    ]


@router.get("/transactions")
async def list_transactions(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return last 50 credit transactions for the current user."""
    rows = (
        await db.execute(
            select(CreditTransaction)
            .where(CreditTransaction.user_id == user.id)
            .order_by(CreditTransaction.created_at.desc())
            .limit(50)
        )
    ).scalars().all()
    return [
        {
            "id": str(r.id),
            "type": r.type,
            "credits": r.credits,
            "usd_amount": float(r.usd_amount) if r.usd_amount is not None else None,
            "model": r.model,
            "description": r.description,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.post("/purchase/checkout")
async def create_checkout(
    package_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe checkout session for credit purchase.

    If Stripe is not configured (STRIPE_SECRET_KEY is empty) returns a
    'coming_soon' response instead of raising an error.
    """
    pkg = next((p for p in CREDIT_PACKAGES if p["id"] == package_id), None)
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")

    from app.core.config import settings

    if not settings.STRIPE_SECRET_KEY:
        return {
            "coming_soon": True,
            "message": "Payment processing coming soon. Stay tuned!",
            "package": pkg,
        }

    try:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"MedMind Credits — {pkg['label']} ({pkg['credits']} credits)",
                            "description": f"AI article generation credits. {pkg.get('bonus', '')}",
                        },
                        "unit_amount": int(pkg["usd"] * 100),
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=(
                f"{settings.FRONTEND_URL}/teacher/articles"
                f"?credits=success&pkg={package_id}"
            ),
            cancel_url=f"{settings.FRONTEND_URL}/teacher/credits",
            metadata={
                "user_id": str(user.id),
                "package_id": package_id,
                "credits": str(pkg["credits"]),
            },
            customer_email=user.email,
        )
        return {"checkout_url": session.url, "session_id": session.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment error: {str(e)}")


@router.post("/purchase/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle Stripe webhook for successful payments (checkout.session.completed)."""
    from app.core.config import settings

    body = await request.body()
    sig = request.headers.get("stripe-signature", "")

    try:
        import stripe
        stripe.api_key = settings.STRIPE_SECRET_KEY
        event = stripe.Webhook.construct_event(body, sig, settings.STRIPE_WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event["type"] == "checkout.session.completed":
        meta = event["data"]["object"]["metadata"]
        user_id = _uuid.UUID(meta["user_id"])
        credits = int(meta["credits"])
        pkg_id = meta["package_id"]
        pkg = next((p for p in CREDIT_PACKAGES if p["id"] == pkg_id), None)
        usd = pkg["usd"] if pkg else 0

        acc = await _get_or_create_account(user_id, db)
        acc.balance += credits
        acc.total_purchased += credits
        db.add(CreditTransaction(
            user_id=user_id,
            type="purchase",
            credits=credits,
            usd_amount=usd,
            description=f"Purchased {credits} credits ({pkg_id} package)",
            stripe_payment_intent_id=event["data"]["object"].get("payment_intent"),
        ))
        await db.commit()

    return {"received": True}
