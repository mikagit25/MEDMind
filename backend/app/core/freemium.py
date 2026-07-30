"""B5 — Freemium layout configuration.

All freemium boundaries are defined here in config, NOT in component code.
This allows changing the free/paid boundary based on analytics data without
a code deploy — just update FREEMIUM_CONFIG or the corresponding feature flags.

Freemium tiers:
  anonymous  — no registration required, daily IP-based question limit
  free       — registered, no subscription
  paid       — any active subscription (Student / Pro / Clinic)

Usage:
    from app.core.freemium import FREEMIUM_CONFIG, get_daily_limit, check_anon_limit
"""
from __future__ import annotations

import hashlib
from typing import Any

from app.core.redis_client import get_redis

# ── Freemium feature config (single source of truth) ────────────────────────

FREEMIUM_CONFIG: dict[str, Any] = {
    # Daily question limit for anonymous users (no registration)
    "anon_daily_questions": 20,

    # What anonymous users can access
    "anon_features": [
        "practice_by_category",     # practice questions by NCLEX category
        "rationales_visible",       # explanations shown after each answer
        "public_quizzes",           # published quizzes
        "glossary",                 # learning glossary
        "dose_calc_demo",           # dose-calc trainer (demo volume, 5 problems/day)
        "content_sources_page",     # B1 content source registry
    ],

    # What free registered users can access (beyond anonymous)
    "free_registered_features": [
        "progress_save",            # save practice history
        "srs_limited",             # spaced repetition (max 50 cards)
        "mock_exam_1",             # 1 free mock exam
        "basic_readiness",         # readiness without category breakdown
    ],

    # What paid users unlock (beyond free registered)
    "paid_features": [
        "unlimited_practice",
        "full_cat_mock",
        "readiness_by_category",
        "readiness_trend",
        "exam_plan",
        "mock_debrief",
        "ai_explain_unlimited",
        "offline_mobile",
        "certificates",
        "gulf_bundle",
        "multilingual_explanations",
    ],
}

# Redis key pattern for anonymous daily question counter
_ANON_KEY = "freemium:anon:{ip_hash}:{date}"


def _ip_hash(ip: str) -> str:
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


async def get_anon_usage(ip: str, date_str: str) -> int:
    """Return how many questions this IP has seen today."""
    redis = await get_redis()
    key = _ANON_KEY.format(ip_hash=_ip_hash(ip), date=date_str)
    val = await redis.get(key)
    return int(val) if val else 0


async def increment_anon_usage(ip: str, date_str: str) -> int:
    """Increment and return the new count. Sets 25-hour TTL on first call."""
    redis = await get_redis()
    key = _ANON_KEY.format(ip_hash=_ip_hash(ip), date=date_str)
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, 90000)   # 25 hours — covers timezone edge cases
    return count


async def check_anon_limit(ip: str, date_str: str) -> dict[str, Any]:
    """Check whether anonymous user has exceeded daily question limit.

    Returns:
        {
            "allowed": bool,
            "used": int,
            "limit": int,
            "remaining": int,
        }
    """
    limit = FREEMIUM_CONFIG["anon_daily_questions"]
    used = await get_anon_usage(ip, date_str)
    return {
        "allowed": used < limit,
        "used": used,
        "limit": limit,
        "remaining": max(0, limit - used),
    }
