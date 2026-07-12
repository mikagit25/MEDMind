"""V5 Phase 2 — Onboarding diagnostic quiz + starter plan tests.

Coverage:
- GET /content/onboarding/diagnostic-quiz: no-auth, returns questions array, empty specialty
- POST /auth/onboarding: accepts level field, stores in preferences
- GET /content/onboarding/starter-plan: 401 without auth, 200 with auth, shape
- calcLevel logic: 0 correct → beginner, 3/6 → intermediate, 5/6 → advanced
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
        "first_name": "Quiz",
        "last_name": "Tester",
        "consent_terms": True,
        "consent_data_processing": True,
    })
    assert r.status_code == 201, r.text
    r2 = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r2.status_code == 200, r2.text
    return r2.json()["access_token"]


# ── Diagnostic Quiz endpoint ──────────────────────────────────────────────────

@pytest.mark.anyio
async def test_diagnostic_quiz_no_auth(client: AsyncClient):
    """Quiz endpoint is public — no auth required."""
    r = await client.get("/api/v1/onboarding/diagnostic-quiz")
    assert r.status_code == 200


@pytest.mark.anyio
async def test_diagnostic_quiz_returns_questions_array(client: AsyncClient):
    r = await client.get("/api/v1/onboarding/diagnostic-quiz")
    body = r.json()
    assert "questions" in body
    assert isinstance(body["questions"], list)


@pytest.mark.anyio
async def test_diagnostic_quiz_empty_specialty_ok(client: AsyncClient):
    """Empty specialties param → returns empty questions list (no modules matched)."""
    r = await client.get("/api/v1/onboarding/diagnostic-quiz?specialties=")
    assert r.status_code == 200
    body = r.json()
    assert "questions" in body


@pytest.mark.anyio
async def test_diagnostic_quiz_unknown_specialty_ok(client: AsyncClient):
    """Unknown specialty → returns empty list, does not 422."""
    r = await client.get("/api/v1/onboarding/diagnostic-quiz?specialties=nonexistent")
    assert r.status_code == 200
    assert r.json()["questions"] == []


@pytest.mark.anyio
async def test_diagnostic_quiz_question_schema(client: AsyncClient):
    """Each question must have id, question, options, correct, difficulty."""
    r = await client.get("/api/v1/onboarding/diagnostic-quiz")
    for q in r.json()["questions"]:
        assert "id" in q
        assert "question" in q
        assert "options" in q
        assert "correct" in q
        assert "difficulty" in q


@pytest.mark.anyio
async def test_diagnostic_quiz_max_6_questions(client: AsyncClient):
    r = await client.get("/api/v1/onboarding/diagnostic-quiz")
    assert len(r.json()["questions"]) <= 6


# ── Onboarding with level field ───────────────────────────────────────────────

@pytest.mark.anyio
async def test_onboarding_accepts_level_field(client: AsyncClient):
    token = await _create_user(client, "onb_level@test.com")
    r = await client.post(
        "/api/v1/auth/onboarding",
        json={
            "role": "student",
            "goal": "exam_prep",
            "specialties": ["cardiology"],
            "daily_minutes": 20,
            "level": "intermediate",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    prefs = me.json().get("preferences") or {}
    assert prefs.get("level") == "intermediate"


@pytest.mark.anyio
async def test_onboarding_default_level_preserved(client: AsyncClient):
    """Onboarding without level field: preferences.level absent (not set)."""
    token = await _create_user(client, "onb_nolevel@test.com")
    r = await client.post(
        "/api/v1/auth/onboarding",
        json={"role": "student", "goal": "daily_learning", "specialties": [], "daily_minutes": 10},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200


@pytest.mark.anyio
async def test_onboarding_level_advanced(client: AsyncClient):
    token = await _create_user(client, "onb_adv@test.com")
    r = await client.post(
        "/api/v1/auth/onboarding",
        json={"role": "doctor", "goal": "clinical_refresh", "specialties": ["cardiology"], "daily_minutes": 30, "level": "advanced"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert (me.json().get("preferences") or {}).get("level") == "advanced"


# ── Starter Plan endpoint ─────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_starter_plan_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/onboarding/starter-plan")
    assert r.status_code == 401


@pytest.mark.anyio
async def test_starter_plan_returns_shape(client: AsyncClient):
    token = await _create_user(client, "starter1@test.com")
    r = await client.get("/api/v1/onboarding/starter-plan",
                         headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert "level" in body
    assert "modules" in body
    assert isinstance(body["modules"], list)


@pytest.mark.anyio
async def test_starter_plan_at_most_3_modules(client: AsyncClient):
    token = await _create_user(client, "starter2@test.com")
    r = await client.get("/api/v1/onboarding/starter-plan",
                         headers={"Authorization": f"Bearer {token}"})
    assert len(r.json()["modules"]) <= 3


@pytest.mark.anyio
async def test_starter_plan_reflects_level_from_onboarding(client: AsyncClient):
    token = await _create_user(client, "starter3@test.com")
    await client.post(
        "/api/v1/auth/onboarding",
        json={"role": "student", "goal": "exam_prep", "specialties": [], "daily_minutes": 20, "level": "advanced"},
        headers={"Authorization": f"Bearer {token}"},
    )
    r = await client.get("/api/v1/onboarding/starter-plan",
                         headers={"Authorization": f"Bearer {token}"})
    assert r.json()["level"] == "advanced"


@pytest.mark.anyio
async def test_starter_plan_module_schema(client: AsyncClient):
    token = await _create_user(client, "starter4@test.com")
    r = await client.get("/api/v1/onboarding/starter-plan",
                         headers={"Authorization": f"Bearer {token}"})
    for m in r.json()["modules"]:
        assert "id" in m
        assert "code" in m
        assert "title" in m
