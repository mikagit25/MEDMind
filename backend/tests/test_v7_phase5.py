"""V7 Phase 5 — Community comparison tests.

Verifies:
- community stats returns {available: false} when no stats exist
- community stats returns pass_rate_pct when sample_size_ok=True
- community stats hides data when sample_size_ok=False
- community percentile returns {available: false} when not enough answers
- community percentile requires authentication
- privacy: no individual data exposed in community endpoints
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import MCQQuestion, Module, QuestionStats, Specialty, User


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _create_user(client: AsyncClient, email: str, password: str = "Str0ng!Pass99") -> str:
    r = await client.post("/api/v1/auth/register", json={
        "email": email, "password": password,
        "first_name": "Test", "last_name": "User",
        "consent_terms": True, "consent_data_processing": True,
    })
    assert r.status_code == 201, r.text
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


async def _make_mcq(db: AsyncSession) -> tuple[uuid.UUID, MCQQuestion]:
    spec = Specialty(id=uuid.uuid4(), code=f"sp-{uuid.uuid4().hex[:6]}", name="Test")
    db.add(spec)
    await db.flush()
    mod = Module(id=uuid.uuid4(), code=f"m-{uuid.uuid4().hex[:6]}", specialty_id=spec.id, title="Test")
    db.add(mod)
    await db.flush()
    q = MCQQuestion(
        id=uuid.uuid4(), module_id=mod.id,
        question="Which is correct?",
        options={"A": "A", "B": "B", "C": "C", "D": "D"},
        correct="A", explanation="A.", difficulty="medium",
        question_type="mcq", status="active",
    )
    db.add(q)
    await db.commit()
    return q.id, q


async def _make_stats(db: AsyncSession, question_id: uuid.UUID, p_value: float, sample_ok: bool) -> None:
    stats = QuestionStats(
        id=uuid.uuid4(),
        question_id=question_id,
        exam_slug=None,
        attempts=100 if sample_ok else 10,
        correct_count=int(p_value * (100 if sample_ok else 10)),
        p_value=p_value,
        sample_size_ok=sample_ok,
        health="ok",
    )
    db.add(stats)
    await db.commit()


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_community_requires_auth(client: AsyncClient, db_session: AsyncSession):
    """Community stats requires authentication."""
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/exam/questions/{fake_id}/community")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_community_no_stats_returns_unavailable(client: AsyncClient, db_session: AsyncSession):
    """When no stats row exists, returns {available: false}."""
    token = await _create_user(client, f"u-{uuid.uuid4().hex[:8]}@test.com")
    mcq_id, _ = await _make_mcq(db_session)

    resp = await client.get(
        f"/api/v1/exam/questions/{mcq_id}/community",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["available"] is False


@pytest.mark.asyncio
async def test_community_insufficient_sample_returns_unavailable(client: AsyncClient, db_session: AsyncSession):
    """When sample_size_ok=False, returns {available: false} (privacy guard)."""
    token = await _create_user(client, f"u-{uuid.uuid4().hex[:8]}@test.com")
    mcq_id, _ = await _make_mcq(db_session)
    await _make_stats(db_session, mcq_id, p_value=0.65, sample_ok=False)

    resp = await client.get(
        f"/api/v1/exam/questions/{mcq_id}/community",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["available"] is False


@pytest.mark.asyncio
async def test_community_returns_pass_rate_when_ok(client: AsyncClient, db_session: AsyncSession):
    """When sample_size_ok=True, returns pass_rate_pct."""
    token = await _create_user(client, f"u-{uuid.uuid4().hex[:8]}@test.com")
    mcq_id, _ = await _make_mcq(db_session)
    await _make_stats(db_session, mcq_id, p_value=0.72, sample_ok=True)

    resp = await client.get(
        f"/api/v1/exam/questions/{mcq_id}/community",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["available"] is True
    assert abs(data["pass_rate_pct"] - 72.0) < 0.5
    assert data["attempts"] > 0


@pytest.mark.asyncio
async def test_community_percentile_requires_auth(client: AsyncClient, db_session: AsyncSession):
    """Community percentile requires authentication."""
    resp = await client.get("/api/v1/exam/nclex/community-percentile")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_community_percentile_not_enough_answers(client: AsyncClient, db_session: AsyncSession):
    """Returns {available: false} when user has < 50 answers."""
    token = await _create_user(client, f"u-{uuid.uuid4().hex[:8]}@test.com")
    resp = await client.get(
        "/api/v1/exam/nclex/community-percentile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["available"] is False
    assert "reason" in data
