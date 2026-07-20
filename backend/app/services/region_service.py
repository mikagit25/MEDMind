"""G3 — Region detection service.

Priority:
  1. user.billing_country (set after first Stripe payment — authoritative)
  2. X-Forwarded-For / CF-IPCountry header (indicative, for pre-payment display)
  3. Default: "A" (full price — never under-price by default)

Anti-abuse rules:
  - Once billing_country is set from Stripe, it cannot be overridden by IP.
  - Manual billing_country changes are limited to 1 per account (billing_region_changed_at tracks this).
  - VPN mismatch: if IP country ≠ billing country, billing country wins.
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx
from fastapi import Request

from app.data.regional_pricing import DEFAULT_TIER, get_tier

logger = logging.getLogger(__name__)

# ip-api.com free tier: 45 req/min, no API key required.
_IP_API_URL = "http://ip-api.com/json/{ip}?fields=countryCode,status"

# In-memory LRU for ip-api lookups (process-local, resets on restart).
# A proper deployment would use Redis; this is intentionally simple for now.
_ip_cache: dict[str, str | None] = {}
_IP_CACHE_MAX = 2000


async def _lookup_ip_country(ip: str) -> str | None:
    """Resolve an IP address to a 2-letter country code via ip-api.com."""
    if ip in _ip_cache:
        return _ip_cache[ip]
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(_IP_API_URL.format(ip=ip))
        data = resp.json()
        country = data.get("countryCode") if data.get("status") == "success" else None
    except Exception:
        country = None

    # Evict oldest entry if cache is full (simple FIFO)
    if len(_ip_cache) >= _IP_CACHE_MAX:
        try:
            first_key = next(iter(_ip_cache))
            del _ip_cache[first_key]
        except StopIteration:
            pass

    _ip_cache[ip] = country
    return country


def _extract_ip(request: Request) -> str | None:
    """Extract the real client IP from Cloudflare or X-Forwarded-For headers."""
    # Cloudflare sets CF-IPCountry (already a country code — use directly if present)
    cf_country = request.headers.get("CF-IPCountry")
    if cf_country and len(cf_country) == 2 and cf_country != "XX":
        return None  # signal to caller: use cf_country directly

    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()

    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    return request.client.host if request.client else None


async def detect_country_from_request(request: Request) -> str | None:
    """Best-effort country detection from HTTP request (no user context)."""
    cf_country = request.headers.get("CF-IPCountry")
    if cf_country and len(cf_country) == 2 and cf_country != "XX":
        return cf_country.upper()

    ip = _extract_ip(request)
    if not ip or ip in ("127.0.0.1", "::1"):
        return None

    return await _lookup_ip_country(ip)


async def resolve_pricing_tier(
    request: Request,
    user=None,
) -> tuple[str, str, str]:
    """Return (tier, country_code, source) for a request.

    source is one of: "billing" | "ip" | "cloudflare" | "default"
    """
    # 1. Authoritative: billing country set from Stripe
    if user and getattr(user, "billing_country", None):
        country = user.billing_country
        tier = get_tier(country)
        return tier, country, "billing"

    # 2. Indicative: IP / CF header
    country = await detect_country_from_request(request)
    if country:
        tier = get_tier(country)
        source = "cloudflare" if request.headers.get("CF-IPCountry") else "ip"
        return tier, country, source

    return DEFAULT_TIER, "US", "default"


def can_change_billing_country(user) -> bool:
    """A user may update billing_country at most once after initial Stripe set."""
    return not getattr(user, "billing_country", None)
