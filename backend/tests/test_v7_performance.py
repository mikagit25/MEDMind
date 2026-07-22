"""V7 — Quiz Performance endpoint tests.

Coverage:
- GET /progress/quiz/performance: 401 without auth
- GET /progress/quiz/performance: 200 with auth, empty when no quiz attempts
- GET /progress/quiz/performance: returns by_specialty and by_module keys
- GET /progress/quiz/performance: correct accuracy calculation
"""
from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User, Module, Specialty, UserProgress


async def _register_and_login(client: AsyncClient, suffix: str = "") -> str:
    email = f"perf_test{suffix}_{uuid.uuid4().hex[:6]}@example.com"
    r = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Str0ngPass99!",
        "first_name": "Perf",
        "last_name": "Tester",
        "consent_terms": True,
        "consent_data_processing": True,
    })
    assert r.status_code == 201, r.text
    r2 = await client.post("/api/v1/auth/login", json={"email": email, "password": "Str0ngPass99!"})
    return r2.json()["access_token"]


@pytest.mark.anyio
async def test_quiz_performance_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/progress/quiz/performance")
    assert r.status_code == 401


@pytest.mark.anyio
async def test_quiz_performance_empty_when_no_attempts(client: AsyncClient):
    token = await _register_and_login(client)
    r = await client.get(
        "/api/v1/progress/quiz/performance",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "by_specialty" in body
    assert "by_module" in body
    assert body["by_specialty"] == []
    assert body["by_module"] == []


@pytest.mark.anyio
async def test_quiz_performance_with_data(client: AsyncClient, db_session: AsyncSession):
    token = await _register_and_login(client)

    # Get user id from auth
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    user_id = me.json()["id"]

    # Create specialty + module
    specialty = Specialty(
        id=uuid.uuid4(),
        code=f"cardio_{uuid.uuid4().hex[:6]}",
        name="Cardiology",
        icon="❤️",
        is_active=True,
    )
    db_session.add(specialty)

    module = Module(
        id=uuid.uuid4(),
        code=f"CARD_{uuid.uuid4().hex[:6]}",
        specialty_id=specialty.id,
        title="Cardiology Basics",
        is_published=True,
        language="en",
    )
    db_session.add(module)

    # Create UserProgress with 10 attempts, 80% score
    prog = UserProgress(
        user_id=uuid.UUID(user_id),
        module_id=module.id,
        mcq_attempts=10,
        mcq_score=80.0,
    )
    db_session.add(prog)
    await db_session.commit()

    r = await client.get(
        "/api/v1/progress/quiz/performance",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()

    assert len(body["by_specialty"]) >= 1
    spec = next((s for s in body["by_specialty"] if s["specialty_code"].startswith("cardio_")), None)
    assert spec is not None
    assert spec["total_attempts"] == 10
    assert spec["accuracy_pct"] == 80.0
    assert spec["specialty_icon"] == "❤️"

    assert len(body["by_module"]) >= 1
    mod = next((m for m in body["by_module"] if m["module_code"].startswith("CARD_")), None)
    assert mod is not None
    assert mod["attempts"] == 10
    assert mod["accuracy_pct"] == 80.0
