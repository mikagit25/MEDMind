"""V7 Phase 3 — Post-exam survey loop tests.

Verifies:
- Pending survey endpoint returns False when no past exam outcome
- Submit survey sets result and reported_at
- Unsubscribe endpoint prevents further reminders
- Duplicate submission returns 409
- Admin readiness validation returns required keys
- Admin blueprint calibration returns required keys
- Insufficient data marked correctly in readiness report
- Non-admin cannot access admin endpoints
"""
from __future__ import annotations

import datetime as _dt
import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import ExamOutcome, User


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _create_user(client: AsyncClient, email: str, password: str = "Str0ng!Pass99") -> str:
    r = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "first_name": "Test",
        "last_name": "User",
        "consent_terms": True,
        "consent_data_processing": True,
    })
    assert r.status_code == 201, r.text
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


async def _set_role(db: AsyncSession, client: AsyncClient, token: str, role: str) -> None:
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    user_id = uuid.UUID(me.json()["id"])
    await db.execute(update(User).where(User.id == user_id).values(role=role))
    await db.commit()


async def _get_user_id(client: AsyncClient, token: str) -> uuid.UUID:
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    return uuid.UUID(me.json()["id"])


async def _make_outcome(db: AsyncSession, user_id: uuid.UUID, exam_date_offset_days: int = -3) -> ExamOutcome:
    """Create an ExamOutcome with exam_date in the past."""
    exam_date = (_dt.datetime.utcnow().date() + _dt.timedelta(days=exam_date_offset_days)).isoformat()
    outcome = ExamOutcome(
        id=uuid.uuid4(),
        user_id=user_id,
        exam_slug="nclex",
        exam_date=exam_date,
        readiness_at_exam=72.5,
    )
    db.add(outcome)
    await db.commit()
    await db.refresh(outcome)
    return outcome


# ── Unit tests ────────────────────────────────────────────────────────────────

def test_exam_outcome_model_fields():
    """ExamOutcome model has required fields."""
    o = ExamOutcome(
        user_id=uuid.uuid4(),
        exam_slug="nclex",
        exam_date="2026-07-01",
        readiness_at_exam=75.0,
    )
    assert o.exam_slug == "nclex"
    assert o.result is None
    assert o.reported_at is None
    assert not o.unsubscribed_from_survey


# ── HTTP tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pending_survey_none_when_no_outcomes(client: AsyncClient, db_session: AsyncSession):
    """No pending survey when user has no exam outcomes."""
    token = await _create_user(client, f"u-{uuid.uuid4().hex[:8]}@test.com")
    resp = await client.get("/api/v1/exam-outcomes/pending", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["pending"] is False


@pytest.mark.asyncio
async def test_pending_survey_returns_outcome(client: AsyncClient, db_session: AsyncSession):
    """Pending survey returned when past exam_date, result not submitted."""
    token = await _create_user(client, f"u-{uuid.uuid4().hex[:8]}@test.com")
    user_id = await _get_user_id(client, token)
    await _make_outcome(db_session, user_id, exam_date_offset_days=-3)

    resp = await client.get("/api/v1/exam-outcomes/pending", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["pending"] is True
    assert data["exam_slug"] == "nclex"
    assert "outcome_id" in data


@pytest.mark.asyncio
async def test_submit_survey_sets_result(client: AsyncClient, db_session: AsyncSession):
    """Submitting survey stores result and reported_at."""
    token = await _create_user(client, f"u-{uuid.uuid4().hex[:8]}@test.com")
    user_id = await _get_user_id(client, token)
    outcome = await _make_outcome(db_session, user_id)

    resp = await client.post(
        f"/api/v1/exam-outcomes/{outcome.id}/submit",
        json={
            "result": "passed",
            "nps_score": 9,
            "harder_topics": ["pharmacology", "infection-control"],
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    # Verify persisted
    await db_session.refresh(outcome)
    assert outcome.result == "passed"
    assert outcome.reported_at is not None
    assert outcome.nps_score == 9


@pytest.mark.asyncio
async def test_submit_survey_duplicate_returns_409(client: AsyncClient, db_session: AsyncSession):
    """Re-submitting the same survey returns 409."""
    token = await _create_user(client, f"u-{uuid.uuid4().hex[:8]}@test.com")
    user_id = await _get_user_id(client, token)
    outcome = await _make_outcome(db_session, user_id)

    payload = {"result": "failed"}
    h = {"Authorization": f"Bearer {token}"}
    await client.post(f"/api/v1/exam-outcomes/{outcome.id}/submit", json=payload, headers=h)
    resp = await client.post(f"/api/v1/exam-outcomes/{outcome.id}/submit", json=payload, headers=h)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_submit_invalid_result_returns_422(client: AsyncClient, db_session: AsyncSession):
    """Invalid result value returns 422."""
    token = await _create_user(client, f"u-{uuid.uuid4().hex[:8]}@test.com")
    user_id = await _get_user_id(client, token)
    outcome = await _make_outcome(db_session, user_id)

    resp = await client.post(
        f"/api/v1/exam-outcomes/{outcome.id}/submit",
        json={"result": "maybe"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_unsubscribe_sets_flag(client: AsyncClient, db_session: AsyncSession):
    """Unsubscribe sets unsubscribed_from_survey=True."""
    token = await _create_user(client, f"u-{uuid.uuid4().hex[:8]}@test.com")
    user_id = await _get_user_id(client, token)
    outcome = await _make_outcome(db_session, user_id)

    resp = await client.post(
        f"/api/v1/exam-outcomes/{outcome.id}/unsubscribe",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    await db_session.refresh(outcome)
    assert outcome.unsubscribed_from_survey is True

    # Should no longer appear in pending
    pending = await client.get("/api/v1/exam-outcomes/pending", headers={"Authorization": f"Bearer {token}"})
    assert pending.json()["pending"] is False


@pytest.mark.asyncio
async def test_readiness_validation_requires_admin(client: AsyncClient, db_session: AsyncSession):
    """Non-admin cannot access readiness validation."""
    token = await _create_user(client, f"u-{uuid.uuid4().hex[:8]}@test.com")
    resp = await client.get(
        "/api/v1/admin/readiness-validation",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_readiness_validation_returns_table(client: AsyncClient, db_session: AsyncSession):
    """Readiness validation returns expected structure."""
    token = await _create_user(client, f"a-{uuid.uuid4().hex[:8]}@test.com")
    await _set_role(db_session, client, token, "admin")

    resp = await client.get(
        "/api/v1/admin/readiness-validation",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "table" in data
    assert "total_outcomes" in data
    assert "marketing_correlation_safe" in data
    # When 0 outcomes, marketing should not be safe
    assert data["marketing_correlation_safe"] is False
    assert len(data["table"]) == 5  # 5 readiness buckets


@pytest.mark.asyncio
async def test_blueprint_calibration_returns_structure(client: AsyncClient, db_session: AsyncSession):
    """Blueprint calibration report returns expected keys."""
    token = await _create_user(client, f"a-{uuid.uuid4().hex[:8]}@test.com")
    await _set_role(db_session, client, token, "admin")

    resp = await client.get(
        "/api/v1/admin/blueprint-calibration",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "harder_than_expected" in data
    assert "weaker_preparation" in data
    assert "advisory_note" in data
    assert "total_responses" in data
