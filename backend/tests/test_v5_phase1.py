"""V5 Phase 1 — Product Analytics tests.

Coverage:
- POST /analytics/track: happy path, anon, batch, unknown event_type, free-text rejected, batch limit
- Schema: meta keys must not contain free-form text
- Admin /admin/analytics/overview: 401 without auth, 403 non-admin, 200 admin, response shape
"""
from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _create_user(client: AsyncClient, email: str, password: str = "Str0ng!Pass99") -> str:
    r = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "first_name": "Ana",
        "last_name": "Test",
        "consent_terms": True,
        "consent_data_processing": True,
    })
    assert r.status_code == 201, r.text
    r2 = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r2.status_code == 200, r2.text
    return r2.json()["access_token"]


async def _set_role(db: AsyncSession, client: AsyncClient, token: str, role: str) -> None:
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    user_id = uuid.UUID(me.json()["id"])
    await db.execute(update(User).where(User.id == user_id).values(role=role))
    await db.commit()


# ── Patch product_analytics.get_redis so it uses FakeRedis ───────────────────

@pytest.fixture(autouse=True)
def _patch_product_analytics_redis(monkeypatch, fake_redis):
    import app.api.v1.routes.product_analytics as _pa

    async def _fake():
        return fake_redis

    monkeypatch.setattr(_pa, "get_redis", _fake)


# ── Track endpoint ────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_track_single_event(client: AsyncClient):
    r = await client.post("/api/v1/analytics/track", json={
        "events": [{"event_type": "public_page_view", "entity_id": "/articles/test"}]
    })
    assert r.status_code == 204


@pytest.mark.anyio
async def test_track_batch(client: AsyncClient):
    events = [{"event_type": "signup", "meta": {"role": "student"}}] * 5
    r = await client.post("/api/v1/analytics/track", json={"events": events})
    assert r.status_code == 204


@pytest.mark.anyio
async def test_track_anon_event_no_auth(client: AsyncClient):
    """Anonymous events (no JWT) must be accepted."""
    r = await client.post("/api/v1/analytics/track", json={
        "events": [{"event_type": "app_open", "platform": "mobile", "anon_id": "abc-123"}]
    })
    assert r.status_code == 204


@pytest.mark.anyio
async def test_track_unknown_event_type_rejected(client: AsyncClient):
    r = await client.post("/api/v1/analytics/track", json={
        "events": [{"event_type": "nonexistent_event"}]
    })
    assert r.status_code == 422


@pytest.mark.anyio
async def test_track_free_text_prompt_rejected(client: AsyncClient):
    """meta must not contain 'prompt' key."""
    r = await client.post("/api/v1/analytics/track", json={
        "events": [{"event_type": "ai_question", "meta": {"prompt": "What is MI?"}}]
    })
    assert r.status_code == 422


@pytest.mark.anyio
async def test_track_free_text_query_key_rejected(client: AsyncClient):
    """meta must not contain 'query' key."""
    r = await client.post("/api/v1/analytics/track", json={
        "events": [{"event_type": "search", "meta": {"query": "aspirin"}}]
    })
    assert r.status_code == 422


@pytest.mark.anyio
async def test_track_free_text_message_rejected(client: AsyncClient):
    """meta must not contain 'message' key."""
    r = await client.post("/api/v1/analytics/track", json={
        "events": [{"event_type": "ai_question", "meta": {"message": "help me"}}]
    })
    assert r.status_code == 422


@pytest.mark.anyio
async def test_track_structured_meta_accepted(client: AsyncClient):
    """Structured keys (mode, specialty, step) must pass validation."""
    r = await client.post("/api/v1/analytics/track", json={
        "events": [{"event_type": "ai_question", "meta": {"mode": "tutor", "specialty": "cardiology"}}]
    })
    assert r.status_code == 204


@pytest.mark.anyio
async def test_track_batch_exceeds_limit(client: AsyncClient):
    """Batches >20 events must be rejected with 422."""
    events = [{"event_type": "app_open"}] * 21
    r = await client.post("/api/v1/analytics/track", json={"events": events})
    assert r.status_code == 422


@pytest.mark.anyio
async def test_track_all_allowed_event_types(client: AsyncClient):
    allowed = [
        "signup", "onboarding_step", "onboarding_completed",
        "lesson_started", "lesson_completed",
        "module_started", "module_completed",
        "flashcard_review", "ai_question", "quiz_completed",
        "public_page_view", "search", "app_open",
    ]
    r = await client.post("/api/v1/analytics/track", json={
        "events": [{"event_type": et} for et in allowed]
    })
    assert r.status_code == 204


# ── Admin analytics overview ──────────────────────────────────────────────────

@pytest.mark.anyio
async def test_analytics_overview_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/admin/analytics/overview")
    assert r.status_code == 401


@pytest.mark.anyio
async def test_analytics_overview_non_admin_forbidden(client: AsyncClient, db_session: AsyncSession):
    token = await _create_user(client, "student_anl@test.com")
    r = await client.get("/api/v1/admin/analytics/overview",
                         headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


@pytest.mark.anyio
async def test_analytics_overview_admin_200(client: AsyncClient, db_session: AsyncSession):
    token = await _create_user(client, "admin_anl@test.com")
    await _set_role(db_session, client, token, "admin")
    r = await client.get("/api/v1/admin/analytics/overview",
                         headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


@pytest.mark.anyio
async def test_analytics_overview_has_all_blocks(client: AsyncClient, db_session: AsyncSession):
    token = await _create_user(client, "admin_anl2@test.com")
    await _set_role(db_session, client, token, "admin")
    r = await client.get("/api/v1/admin/analytics/overview",
                         headers={"Authorization": f"Bearer {token}"})
    body = r.json()
    for key in ("dau_series", "wau_series", "mau_series", "cohorts", "funnel", "abandoned_modules"):
        assert key in body, f"Missing key: {key}"


@pytest.mark.anyio
async def test_analytics_overview_funnel_steps_present(client: AsyncClient, db_session: AsyncSession):
    token = await _create_user(client, "admin_anl3@test.com")
    await _set_role(db_session, client, token, "admin")
    r = await client.get("/api/v1/admin/analytics/overview",
                         headers={"Authorization": f"Bearer {token}"})
    steps = {f["step"] for f in r.json()["funnel"]}
    assert "Signup" in steps
    assert "Onboarding completed" in steps
    assert "First lesson started" in steps
    assert "First lesson completed" in steps


@pytest.mark.anyio
async def test_analytics_overview_funnel_counts_ints(client: AsyncClient, db_session: AsyncSession):
    token = await _create_user(client, "admin_anl4@test.com")
    await _set_role(db_session, client, token, "admin")
    r = await client.get("/api/v1/admin/analytics/overview",
                         headers={"Authorization": f"Bearer {token}"})
    for item in r.json()["funnel"]:
        assert isinstance(item["count"], int), f"count is not int: {item}"


@pytest.mark.anyio
async def test_analytics_overview_cohorts_schema(client: AsyncClient, db_session: AsyncSession):
    token = await _create_user(client, "admin_anl5@test.com")
    await _set_role(db_session, client, token, "admin")
    r = await client.get("/api/v1/admin/analytics/overview",
                         headers={"Authorization": f"Bearer {token}"})
    for c in r.json()["cohorts"]:
        assert "week" in c
        assert "size" in c
        assert "d1_pct" in c
        assert "d7_pct" in c
        assert "d30_pct" in c
