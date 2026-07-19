"""Unit tests for V6 Phase 5 — Lifecycle email campaigns."""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.lifecycle import (
    is_unsubscribed,
    make_unsub_token,
    verify_unsub_token,
    run_all_campaigns,
)


# ── Token helpers ──────────────────────────────────────────────────────────────

def test_unsub_token_roundtrip():
    token = make_unsub_token("user-123", "onboarding_d1")
    assert verify_unsub_token("user-123", "onboarding_d1", token)


def test_unsub_token_wrong_user():
    token = make_unsub_token("user-123", "onboarding_d1")
    assert not verify_unsub_token("user-456", "onboarding_d1", token)


def test_unsub_token_wrong_campaign():
    token = make_unsub_token("user-123", "onboarding_d1")
    assert not verify_unsub_token("user-123", "reactivation_7d", token)


# ── Unsubscribe logic ──────────────────────────────────────────────────────────

def _mock_user(**kwargs) -> MagicMock:
    u = MagicMock()
    u.preferences = kwargs
    return u


def test_is_unsubscribed_false_by_default():
    u = _mock_user()
    assert not is_unsubscribed(u, "onboarding_d1")


def test_is_unsubscribed_specific_campaign():
    u = _mock_user(email_unsubscribes=["onboarding_d1"])
    assert is_unsubscribed(u, "onboarding_d1")
    assert not is_unsubscribed(u, "reactivation_7d")


def test_is_unsubscribed_all():
    u = _mock_user(email_unsubscribes=["all"])
    assert is_unsubscribed(u, "onboarding_d1")
    assert is_unsubscribed(u, "readiness_weekly")


def test_is_unsubscribed_global_off():
    u = _mock_user(email_notifications=False)
    assert is_unsubscribed(u, "onboarding_d1")


def test_is_unsubscribed_global_on_specific_off():
    u = _mock_user(email_notifications=True, email_unsubscribes=["streak_risk"])
    assert not is_unsubscribed(u, "onboarding_d1")
    assert is_unsubscribed(u, "streak_risk")


# ── Idempotency via IntegrityError ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_try_send_idempotent():
    """Second send attempt returns False without sending another email."""
    from sqlalchemy.exc import IntegrityError
    from app.services.lifecycle import _try_send

    user = MagicMock()
    user.id = "uid-1"
    user.email = "test@example.com"
    user.preferences = {}

    db = AsyncMock()
    # Simulate flush raising IntegrityError (duplicate unique constraint)
    db.flush = AsyncMock(side_effect=IntegrityError("stmt", {}, Exception("dup")))
    db.rollback = AsyncMock()

    result = await _try_send(db, user, "onboarding_d1", "Subject", "<p>hi</p>", "hi")
    assert result is False
    db.rollback.assert_called_once()


# ── run_all_campaigns returns a dict of campaign → count ──────────────────────

@pytest.mark.asyncio
async def test_run_all_campaigns_returns_dict():
    """run_all_campaigns should return a dict with all expected campaign keys."""
    expected_keys = {
        "onboarding_d1", "onboarding_d3", "onboarding_d7",
        "reactivation_7d", "reactivation_21d", "reactivation_45d",
        "streak_risk", "readiness_weekly",
        "exam_countdown_7d", "exam_countdown_1d",
    }
    # Patch AsyncSessionLocal so no real DB is used
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    # Each sub-runner queries users — return empty scalars
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("app.services.lifecycle.AsyncSessionLocal", return_value=mock_session):
        results = await run_all_campaigns(now=datetime(2026, 7, 19, 6, 0, 0))

    assert set(results.keys()) == expected_keys
    assert all(isinstance(v, int) for v in results.values())
