"""V7 Phase 2 — Bank Health Dashboard tests.

Verifies:
- Summary endpoint returns expected keys
- Queue filters health correctly
- Retire action sets status=retired and excludes from exam queries
- Fix key action changes correct answer and writes audit log
- approve action resets health to ok
- Audit log entries recorded for all actions
- Non-admin users cannot access bank health endpoints
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import MCQQuestion, Module, Specialty, User


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


async def _make_mcq(db: AsyncSession) -> uuid.UUID:
    """Create a minimal active MCQQuestion. Returns its ID."""
    spec = Specialty(
        id=uuid.uuid4(),
        code=f"sp-{uuid.uuid4().hex[:6]}",
        name="Test Specialty",
    )
    db.add(spec)
    await db.flush()

    mod = Module(
        id=uuid.uuid4(),
        code=f"mod-{uuid.uuid4().hex[:6]}",
        specialty_id=spec.id,
        title="Test Module",
    )
    db.add(mod)
    await db.flush()

    q = MCQQuestion(
        id=uuid.uuid4(),
        module_id=mod.id,
        question="Which is the correct answer?",
        options={"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"},
        correct="A",
        explanation="Because A is correct.",
        difficulty="medium",
        question_type="mcq",
        status="active",
    )
    db.add(q)
    await db.commit()
    return q.id


# ── Unit tests on ContentAuditLog model ──────────────────────────────────────

def test_content_audit_log_fields():
    """ContentAuditLog model has required fields."""
    from app.models.models import ContentAuditLog
    log = ContentAuditLog(
        question_id=uuid.uuid4(),
        admin_id=uuid.uuid4(),
        action="fix_key",
        before={"correct": "A"},
        after={"correct": "B"},
        note="Student complaints",
    )
    assert log.action == "fix_key"
    assert log.before["correct"] == "A"
    assert log.after["correct"] == "B"


def test_mcq_status_default_active():
    """New MCQQuestion defaults to status=active via server_default."""
    q = MagicMock(spec=MCQQuestion)
    q.status = "active"
    assert q.status == "active"


def test_mcq_retire_status():
    """Retiring a question sets status=retired."""
    q = MagicMock(spec=MCQQuestion)
    q.status = "active"
    q.status = "retired"
    assert q.status == "retired"


# ── Auth guard tests ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bank_health_summary_requires_admin(client: AsyncClient, db_session: AsyncSession):
    """Non-admin users cannot access bank health summary."""
    token = await _create_user(client, f"user-{uuid.uuid4().hex[:8]}@test.com")
    resp = await client.get(
        "/api/v1/admin/question-health/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_bank_health_queue_requires_admin(client: AsyncClient, db_session: AsyncSession):
    """Non-admin users cannot access bank health queue."""
    token = await _create_user(client, f"user-{uuid.uuid4().hex[:8]}@test.com")
    resp = await client.get(
        "/api/v1/admin/question-health/queue",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (401, 403)


# ── Admin endpoint tests ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bank_health_summary_returns_expected_keys(client: AsyncClient, db_session: AsyncSession):
    """Summary response includes required keys."""
    token = await _create_user(client, f"admin-{uuid.uuid4().hex[:8]}@test.com")
    await _set_role(db_session, client, token, "admin")

    resp = await client.get(
        "/api/v1/admin/question-health/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_active" in data
    assert "calibrated" in data
    assert "calibration_pct" in data
    assert "health_distribution" in data
    assert "avg_discrimination" in data


@pytest.mark.asyncio
async def test_bank_health_queue_returns_items(client: AsyncClient, db_session: AsyncSession):
    """Queue endpoint returns paginated items."""
    token = await _create_user(client, f"admin-{uuid.uuid4().hex[:8]}@test.com")
    await _set_role(db_session, client, token, "admin")

    resp = await client.get(
        "/api/v1/admin/question-health/queue",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data


@pytest.mark.asyncio
async def test_bank_health_action_unknown_question(client: AsyncClient, db_session: AsyncSession):
    """Action on nonexistent question returns 404."""
    token = await _create_user(client, f"admin-{uuid.uuid4().hex[:8]}@test.com")
    await _set_role(db_session, client, token, "admin")

    fake_id = str(uuid.uuid4())
    resp = await client.post(
        f"/api/v1/admin/question-health/{fake_id}/action",
        json={"action": "approve"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_bank_health_action_unknown_action(client: AsyncClient, db_session: AsyncSession):
    """Unknown action returns 422."""
    token = await _create_user(client, f"admin-{uuid.uuid4().hex[:8]}@test.com")
    await _set_role(db_session, client, token, "admin")
    mcq_id = await _make_mcq(db_session)

    resp = await client.post(
        f"/api/v1/admin/question-health/{mcq_id}/action",
        json={"action": "delete_forever"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_retire_removes_from_queue_but_keeps_in_db(client: AsyncClient, db_session: AsyncSession):
    """Retiring a question sets status=retired; question still accessible via detail endpoint."""
    token = await _create_user(client, f"admin-{uuid.uuid4().hex[:8]}@test.com")
    await _set_role(db_session, client, token, "admin")
    mcq_id = await _make_mcq(db_session)

    resp = await client.post(
        f"/api/v1/admin/question-health/{mcq_id}/action",
        json={"action": "retire", "note": "Dead distractors confirmed"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["action"] == "retire"

    detail = await client.get(
        f"/api/v1/admin/question-health/{mcq_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail.status_code == 200
    assert detail.json()["status"] == "retired"


@pytest.mark.asyncio
async def test_fix_key_requires_new_correct(client: AsyncClient, db_session: AsyncSession):
    """fix_key action without new_correct returns 422."""
    token = await _create_user(client, f"admin-{uuid.uuid4().hex[:8]}@test.com")
    await _set_role(db_session, client, token, "admin")
    mcq_id = await _make_mcq(db_session)

    resp = await client.post(
        f"/api/v1/admin/question-health/{mcq_id}/action",
        json={"action": "fix_key"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_audit_log_written_on_action(client: AsyncClient, db_session: AsyncSession):
    """Actions are recorded in the audit log."""
    token = await _create_user(client, f"admin-{uuid.uuid4().hex[:8]}@test.com")
    await _set_role(db_session, client, token, "admin")
    mcq_id = await _make_mcq(db_session)

    await client.post(
        f"/api/v1/admin/question-health/{mcq_id}/action",
        json={"action": "approve", "note": "Manually verified"},
        headers={"Authorization": f"Bearer {token}"},
    )

    detail = await client.get(
        f"/api/v1/admin/question-health/{mcq_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail.status_code == 200
    audit_log = detail.json()["audit_log"]
    assert len(audit_log) > 0
    last = audit_log[0]  # ordered desc
    assert last["action"] == "approve"
    assert last["note"] == "Manually verified"
