"""V4 Phase 8 — Mobile App backend tests.

Tests:
  1. PATCH /auth/push-token requires authentication (401 without token)
  2. PATCH /auth/push-token stores the token for the current user
  3. PATCH /auth/push-token with empty string returns 400
  4. PATCH /auth/push-token strips whitespace and validates
  5. PATCH /auth/push-token updates token when called again (idempotent update)
  6. Push token is user-scoped — updating one user does not affect another
"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import User


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _register_and_login(client: AsyncClient, email: str) -> str:
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Str0ng!Pass99",
        "first_name": "Mobile",
        "last_name": "User",
        "consent_terms": True,
        "consent_data_processing": True,
    })
    r = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "Str0ng!Pass99",
    })
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


async def _get_user_by_token(client: AsyncClient, token: str, db: AsyncSession) -> User:
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    user_id = uuid.UUID(me.json()["id"])
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one()


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_push_token_requires_auth(client: AsyncClient):
    """PATCH /auth/push-token without a token returns 401."""
    r = await client.patch("/api/v1/auth/push-token", json={"push_token": "ExponentPushToken[abc]"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_push_token_stores_token(client: AsyncClient, db_session: AsyncSession):
    """Authenticated PATCH stores the Expo push token in the DB."""
    token = await _register_and_login(client, "push_store@test.medmind")
    expo_token = "ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]"

    r = await client.patch(
        "/api/v1/auth/push-token",
        json={"push_token": expo_token},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    user = await _get_user_by_token(client, token, db_session)
    await db_session.refresh(user)
    assert user.push_token == expo_token


@pytest.mark.asyncio
async def test_push_token_empty_string_returns_400(client: AsyncClient):
    """Empty push_token value returns 400."""
    token = await _register_and_login(client, "push_empty@test.medmind")
    r = await client.patch(
        "/api/v1/auth/push-token",
        json={"push_token": ""},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_push_token_whitespace_returns_400(client: AsyncClient):
    """Whitespace-only push_token returns 400 (stripped to empty)."""
    token = await _register_and_login(client, "push_ws@test.medmind")
    r = await client.patch(
        "/api/v1/auth/push-token",
        json={"push_token": "   "},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_push_token_update_is_idempotent(client: AsyncClient, db_session: AsyncSession):
    """Calling PATCH /auth/push-token twice updates the token (last write wins)."""
    token = await _register_and_login(client, "push_update@test.medmind")

    first_expo = "ExponentPushToken[first_token_111]"
    second_expo = "ExponentPushToken[second_token_222]"

    await client.patch(
        "/api/v1/auth/push-token",
        json={"push_token": first_expo},
        headers={"Authorization": f"Bearer {token}"},
    )
    r = await client.patch(
        "/api/v1/auth/push-token",
        json={"push_token": second_expo},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200

    user = await _get_user_by_token(client, token, db_session)
    await db_session.refresh(user)
    assert user.push_token == second_expo


@pytest.mark.asyncio
async def test_push_token_is_user_scoped(client: AsyncClient, db_session: AsyncSession):
    """Registering a push token for user A does not affect user B."""
    token_a = await _register_and_login(client, "push_user_a@test.medmind")
    token_b = await _register_and_login(client, "push_user_b@test.medmind")

    expo_a = "ExponentPushToken[user_a_token]"

    await client.patch(
        "/api/v1/auth/push-token",
        json={"push_token": expo_a},
        headers={"Authorization": f"Bearer {token_a}"},
    )

    user_b = await _get_user_by_token(client, token_b, db_session)
    await db_session.refresh(user_b)
    assert user_b.push_token != expo_a
