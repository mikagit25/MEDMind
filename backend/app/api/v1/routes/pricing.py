"""G3 — Regional pricing API.

GET /pricing/regional  — returns price table for the current visitor's region.
"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.data.regional_pricing import BASE_PRICES_USD, all_tiers_table, get_price, price_table
from app.services.region_service import resolve_pricing_tier

from app.api.deps import get_current_user_optional as get_optional_user

router = APIRouter(prefix="/pricing", tags=["pricing"])


@router.get("/regional")
async def get_regional_pricing(
    request: Request,
    user=Depends(get_optional_user),
):
    """Return price table for the visitor's detected region.

    Response:
        tier        — "A" | "B" | "C"
        country     — ISO-2 country code (may be inferred from IP)
        source      — "billing" | "ip" | "cloudflare" | "default"
        prices      — {plan: price_usd} for this tier
        base_prices — {plan: price_usd} for Tier A (always shown for comparison)
        discount_pct — 0 | 50 | 70  (savings vs base)
    """
    tier, country, source = await resolve_pricing_tier(request, user)

    multiplier_map = {"A": 1.0, "B": 0.5, "C": 0.3}
    discount_pct = round((1 - multiplier_map.get(tier, 1.0)) * 100)

    return {
        "tier": tier,
        "country": country,
        "source": source,
        "prices": price_table(tier),
        "base_prices": price_table("A"),
        "discount_pct": discount_pct,
        "currency": "USD",
    }


@router.get("/all-tiers")
async def get_all_tiers(request: Request, user=Depends(get_optional_user)):
    """Admin / comparison view: all tier prices. Open endpoint (no secret data)."""
    return {
        "tiers": all_tiers_table(),
        "base": BASE_PRICES_USD,
    }
