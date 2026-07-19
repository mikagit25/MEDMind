"""Unit tests for V6 Phase 6 — Billing Hardening."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest
from sqlalchemy.exc import IntegrityError

from app.services.billing import (
    is_self_referral,
    audit_log,
    start_dunning,
    run_dunning_check,
    check_ip_suspicious,
    set_conversion_status,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_user(**kwargs):
    u = MagicMock()
    u.id = uuid.uuid4()
    u.email = "test@example.com"
    u.first_name = "Test"
    u.subscription_tier = kwargs.get("tier", "pro")
    u.subscription_expires = kwargs.get("expires", None)
    u.is_active = True
    u.preferences = dict(kwargs.get("preferences", {}))
    u.stripe_customer_id = kwargs.get("stripe_customer_id", None)
    return u


# ── Self-referral ──────────────────────────────────────────────────────────────

def test_self_referral_same_id():
    uid = uuid.uuid4()
    assert is_self_referral(uid, uid)


def test_self_referral_different_id():
    assert not is_self_referral(uuid.uuid4(), uuid.uuid4())


def test_self_referral_string_comparison():
    uid = uuid.uuid4()
    assert is_self_referral(str(uid), uid)
    assert is_self_referral(uid, str(uid))


# ── Audit log ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audit_log_creates_event():
    db = AsyncMock()
    db.add = MagicMock()

    ev = await audit_log(
        db,
        event_type="subscription_activated",
        source="webhook",
        user_id=uuid.uuid4(),
        old_tier="free",
        new_tier="pro",
        amount=40.0,
        reason="test",
    )
    db.add.assert_called_once_with(ev)
    assert ev.event_type == "subscription_activated"
    assert ev.source == "webhook"
    assert ev.old_tier == "free"
    assert ev.new_tier == "pro"
    assert ev.amount == 40.0


# ── IP suspicious check ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_check_ip_suspicious_below_threshold():
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 2
    db.execute = AsyncMock(return_value=mock_result)

    result = await check_ip_suspicious(db, uuid.uuid4(), "abc123hash")
    assert result is False


@pytest.mark.asyncio
async def test_check_ip_suspicious_at_threshold():
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 3
    db.execute = AsyncMock(return_value=mock_result)

    result = await check_ip_suspicious(db, uuid.uuid4(), "abc123hash")
    assert result is True


@pytest.mark.asyncio
async def test_check_ip_suspicious_no_hash():
    db = AsyncMock()
    result = await check_ip_suspicious(db, uuid.uuid4(), None)
    assert result is False
    db.execute.assert_not_called()


# ── Dunning ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_start_dunning_sets_timestamp():
    db = AsyncMock()
    db.add = MagicMock()
    user = _make_user(tier="pro")

    await start_dunning(db, user, stripe_invoice_id="inv_123")

    assert "dunning_started_at" in user.preferences
    db.add.assert_called_once()  # audit_log added a BillingEvent


@pytest.mark.asyncio
async def test_start_dunning_idempotent():
    db = AsyncMock()
    db.add = MagicMock()
    ts = (datetime.utcnow() - timedelta(days=2)).isoformat()
    user = _make_user(preferences={"dunning_started_at": ts})

    await start_dunning(db, user)

    # preferences unchanged
    assert user.preferences["dunning_started_at"] == ts
    # No second audit event
    db.add.assert_not_called()


@pytest.mark.asyncio
async def test_run_dunning_downgrade_after_grace():
    """Users with dunning started 7+ days ago must be downgraded."""
    user = _make_user(
        tier="pro",
        preferences={
            "dunning_started_at": (datetime.utcnow() - timedelta(days=7)).isoformat()
        },
    )

    mock_users_result = MagicMock()
    mock_users_result.scalars.return_value.all.return_value = [user]

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(return_value=mock_users_result)
    db_mock.add = MagicMock()
    db_mock.commit = AsyncMock()

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=db_mock)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.billing.AsyncSessionLocal", return_value=mock_session):
        with patch("app.core.email._send_smtp"):
            await run_dunning_check()

    assert user.subscription_tier == "free"
    assert "dunning_started_at" not in user.preferences


@pytest.mark.asyncio
async def test_run_dunning_no_downgrade_within_grace():
    """Users with dunning started < 7 days ago must NOT be downgraded."""
    user = _make_user(
        tier="pro",
        preferences={
            "dunning_started_at": (datetime.utcnow() - timedelta(days=3)).isoformat()
        },
    )

    mock_users_result = MagicMock()
    mock_users_result.scalars.return_value.all.return_value = [user]

    # Lifecycle send check — not yet sent
    mock_send_result = MagicMock()
    mock_send_result.scalar_one_or_none.return_value = None

    call_count = 0

    async def _execute_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return mock_users_result
        return mock_send_result

    db_mock = AsyncMock()
    db_mock.execute = AsyncMock(side_effect=_execute_side_effect)
    db_mock.add = MagicMock()
    db_mock.commit = AsyncMock()

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=db_mock)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with patch("app.services.billing.AsyncSessionLocal", return_value=mock_session):
        with patch("app.core.email._send_smtp") as mock_smtp:
            with patch("app.core.email._base_template", return_value="<html/>"):
                await run_dunning_check()

    # Tier unchanged
    assert user.subscription_tier == "pro"


# ── set_conversion_status ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_set_conversion_status_approved():
    db = AsyncMock()
    db.add = MagicMock()

    conv = MagicMock()
    conv.commission_status = "hold"
    conv.is_suspicious = True
    conv.user_id = uuid.uuid4()
    conv.affiliate_id = uuid.uuid4()
    conv.id = uuid.uuid4()
    conv.commission_amount = 10.0

    await set_conversion_status(db, conv, "approved", reason="Admin approval")
    assert conv.commission_status == "approved"
    db.add.assert_called_once()  # audit_log


@pytest.mark.asyncio
async def test_set_conversion_status_hold_sets_suspicious():
    db = AsyncMock()
    db.add = MagicMock()

    conv = MagicMock()
    conv.commission_status = "pending"
    conv.is_suspicious = False
    conv.user_id = uuid.uuid4()
    conv.affiliate_id = uuid.uuid4()
    conv.id = uuid.uuid4()
    conv.commission_amount = 5.0

    await set_conversion_status(db, conv, "hold")
    assert conv.commission_status == "hold"
    assert conv.is_suspicious is True
