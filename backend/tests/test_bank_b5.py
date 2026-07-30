"""Bank-Scale B5 — Freemium layout tests.

Verifies:
- FREEMIUM_CONFIG has required keys: anon_daily_questions, anon_features, paid_features
- anon_daily_questions is a positive int
- check_anon_limit: allowed=True when usage=0
- check_anon_limit: allowed=False when usage>=limit
- increment_anon_usage: increments counter
- GET /public/practice/free: returns questions when under limit
- GET /public/practice/free: returns paywall=True when limit hit
- GET /public/practice/free/status: returns usage structure
- GET /public/freemium/config: returns config structure (no auth needed)
- paywall_hit event accepted by analytics endpoint
- Feature flags: freemium flags present in DEFAULTS
"""
from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio


# ── Unit: FREEMIUM_CONFIG ─────────────────────────────────────────────────────

def test_freemium_config_has_required_keys():
    """FREEMIUM_CONFIG must have required keys."""
    from app.core.freemium import FREEMIUM_CONFIG

    assert "anon_daily_questions" in FREEMIUM_CONFIG
    assert "anon_features" in FREEMIUM_CONFIG
    assert "free_registered_features" in FREEMIUM_CONFIG
    assert "paid_features" in FREEMIUM_CONFIG


def test_freemium_anon_daily_limit_is_positive():
    """Daily question limit must be a positive integer."""
    from app.core.freemium import FREEMIUM_CONFIG

    limit = FREEMIUM_CONFIG["anon_daily_questions"]
    assert isinstance(limit, int)
    assert limit > 0


def test_freemium_paid_features_not_in_anon():
    """Paid features must not appear in the anonymous feature list."""
    from app.core.freemium import FREEMIUM_CONFIG

    anon_set = set(FREEMIUM_CONFIG["anon_features"])
    paid_set = set(FREEMIUM_CONFIG["paid_features"])
    overlap = anon_set & paid_set
    assert not overlap, f"Paid features incorrectly in anon list: {overlap}"


# ── Unit: check_anon_limit ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_check_anon_limit_allowed_when_zero():
    """With 0 usage, limit check should return allowed=True."""
    from app.core.freemium import check_anon_limit

    fake_redis = AsyncMock()
    fake_redis.get = AsyncMock(return_value=None)   # no usage

    with patch("app.core.freemium.get_redis", AsyncMock(return_value=fake_redis)):
        result = await check_anon_limit("192.168.1.1", "2026-07-30")

    assert result["allowed"] is True
    assert result["used"] == 0
    assert result["remaining"] == result["limit"]


@pytest.mark.asyncio
async def test_check_anon_limit_blocked_at_limit():
    """When usage equals limit, allowed should be False."""
    from app.core.freemium import check_anon_limit, FREEMIUM_CONFIG

    limit = FREEMIUM_CONFIG["anon_daily_questions"]
    fake_redis = AsyncMock()
    fake_redis.get = AsyncMock(return_value=str(limit))

    with patch("app.core.freemium.get_redis", AsyncMock(return_value=fake_redis)):
        result = await check_anon_limit("10.0.0.1", "2026-07-30")

    assert result["allowed"] is False
    assert result["remaining"] == 0
    assert result["used"] == limit


@pytest.mark.asyncio
async def test_increment_anon_usage():
    """increment_anon_usage increments Redis counter and sets TTL on first call."""
    from app.core.freemium import increment_anon_usage

    store: dict = {}

    async def fake_incr(key):
        store[key] = store.get(key, 0) + 1
        return store[key]

    async def fake_expire(key, ttl):
        pass

    fake_redis = AsyncMock()
    fake_redis.incr = AsyncMock(side_effect=fake_incr)
    fake_redis.expire = AsyncMock(side_effect=fake_expire)

    with patch("app.core.freemium.get_redis", AsyncMock(return_value=fake_redis)):
        count1 = await increment_anon_usage("1.2.3.4", "2026-07-30")
        count2 = await increment_anon_usage("1.2.3.4", "2026-07-30")

    assert count1 == 1
    assert count2 == 2
    assert fake_redis.expire.called   # TTL set on first increment


# ── Unit: Feature flags ───────────────────────────────────────────────────────

def test_freemium_feature_flags_in_defaults():
    """B5 freemium flags must appear in feature_flags DEFAULTS."""
    from app.core.feature_flags import DEFAULTS

    assert "freemium_anon_practice" in DEFAULTS
    assert "freemium_progress_save" in DEFAULTS
    assert "freemium_mock_exam" in DEFAULTS
    assert "freemium_full_readiness" in DEFAULTS


# ── API: /public/freemium/config ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_freemium_config_endpoint(client):
    """GET /public/freemium/config returns config without auth."""
    r = await client.get("/api/v1/public/freemium/config")
    assert r.status_code == 200
    data = r.json()
    assert "anon_daily_questions" in data
    assert "anon_features" in data
    assert "paid_features" in data
    assert isinstance(data["anon_daily_questions"], int)


# ── API: /public/practice/free/status ────────────────────────────────────────

@pytest.mark.asyncio
async def test_free_practice_status(client):
    """GET /public/practice/free/status returns usage structure."""
    r = await client.get("/api/v1/public/practice/free/status")
    assert r.status_code == 200
    data = r.json()
    assert "allowed" in data
    assert "used" in data
    assert "limit" in data
    assert "remaining" in data


# ── API: /public/practice/free ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_free_practice_returns_structure(client):
    """GET /public/practice/free returns expected structure."""
    r = await client.get("/api/v1/public/practice/free?limit=3")
    assert r.status_code == 200
    data = r.json()
    assert "questions" in data
    assert "used" in data
    assert "limit" in data
    assert "remaining" in data
    assert "paywall" in data


@pytest.mark.asyncio
async def test_free_practice_empty_when_no_questions(client):
    """With no questions in DB, returns empty list but no error."""
    r = await client.get("/api/v1/public/practice/free?limit=5")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data["questions"], list)


@pytest.mark.asyncio
async def test_free_practice_paywall_when_limit_hit(client):
    """When daily limit is exhausted, paywall=True and no questions returned."""
    from app.core.freemium import FREEMIUM_CONFIG

    limit = FREEMIUM_CONFIG["anon_daily_questions"]

    # Mock check_anon_limit to return limit exhausted
    exhausted = {"allowed": False, "used": limit, "limit": limit, "remaining": 0}

    with patch("app.core.freemium.get_redis",
               AsyncMock(return_value=AsyncMock(get=AsyncMock(return_value=str(limit))))):
        r = await client.get("/api/v1/public/practice/free?limit=5")

    assert r.status_code == 200
    data = r.json()
    assert data["paywall"] is True
    assert data["questions"] == []
    assert "paywall_message" in data


# ── API: paywall_hit analytics event ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_paywall_hit_event_accepted(client):
    """paywall_hit event should be accepted by analytics endpoint."""
    r = await client.post("/api/v1/analytics/track", json={"events": [{
        "event_type": "paywall_hit",
        "entity_type": "feature",
        "meta": {"feature": "unlimited_practice", "tier_required": "paid"},
    }]})
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_anon_limit_hit_event_accepted(client):
    """anon_limit_hit event should be accepted by analytics endpoint."""
    r = await client.post("/api/v1/analytics/track", json={"events": [{
        "event_type": "anon_limit_hit",
        "meta": {"category": "pharmacological"},
    }]})
    assert r.status_code == 204
