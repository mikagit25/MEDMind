"""V7 Phase 7 — Daily streak & XP goal endpoints.

Verifies:
- GET /progress/daily returns correct schema (unauthenticated → 401/403)
- GET /progress/daily returns data for authenticated user
- PATCH /progress/daily-goal sets goal and clamps to [10, 500]
- Goal reads back correctly from GET /progress/daily
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_daily_requires_auth(client: AsyncClient):
    """Unauthenticated request returns 401 or 403."""
    r = await client.get("/api/v1/progress/daily")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_daily_goal_set_requires_auth(client: AsyncClient):
    """Unauthenticated PATCH returns 401 or 403."""
    r = await client.patch("/api/v1/progress/daily-goal?goal_xp=100")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_daily_returns_schema(client: AsyncClient):
    """Authenticated user gets expected keys from /progress/daily."""
    # Register + login
    creds = {"email": "daily_test@medmind.pro", "password": "Test!Pass99",
             "first_name": "Daily", "last_name": "User",
             "consent_terms": True, "consent_data_processing": True}
    await client.post("/api/v1/auth/register", json=creds)
    login = await client.post("/api/v1/auth/login",
                              json={"email": creds["email"], "password": creds["password"]})
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.get("/api/v1/progress/daily", headers=headers)
    assert r.status_code == 200
    data = r.json()
    for key in ("streak_days", "longest_streak", "xp_today", "daily_goal_xp",
                "goal_pct", "goal_met", "xp_total", "level"):
        assert key in data, f"Missing key: {key}"
    assert isinstance(data["streak_days"], int)
    assert isinstance(data["goal_met"], bool)
    assert 0 <= data["goal_pct"] <= 100


@pytest.mark.asyncio
async def test_set_daily_goal_and_read_back(client: AsyncClient):
    """PATCH /progress/daily-goal updates goal; GET /progress/daily reflects it."""
    creds = {"email": "daily_goal_test@medmind.pro", "password": "Test!Pass99",
             "first_name": "Goal", "last_name": "User",
             "consent_terms": True, "consent_data_processing": True}
    await client.post("/api/v1/auth/register", json=creds)
    login = await client.post("/api/v1/auth/login",
                              json={"email": creds["email"], "password": creds["password"]})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.patch("/api/v1/progress/daily-goal?goal_xp=150", headers=headers)
    assert r.status_code == 200
    assert r.json()["daily_goal_xp"] == 150

    r2 = await client.get("/api/v1/progress/daily", headers=headers)
    assert r2.json()["daily_goal_xp"] == 150


@pytest.mark.asyncio
async def test_set_daily_goal_clamps_low(client: AsyncClient):
    """goal_xp below 10 is clamped to 10."""
    creds = {"email": "daily_clamp_low@medmind.pro", "password": "Test!Pass99",
             "first_name": "Clamp", "last_name": "Low",
             "consent_terms": True, "consent_data_processing": True}
    await client.post("/api/v1/auth/register", json=creds)
    login = await client.post("/api/v1/auth/login",
                              json={"email": creds["email"], "password": creds["password"]})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.patch("/api/v1/progress/daily-goal?goal_xp=1", headers=headers)
    assert r.status_code == 200
    assert r.json()["daily_goal_xp"] == 10


@pytest.mark.asyncio
async def test_set_daily_goal_clamps_high(client: AsyncClient):
    """goal_xp above 500 is clamped to 500."""
    creds = {"email": "daily_clamp_high@medmind.pro", "password": "Test!Pass99",
             "first_name": "Clamp", "last_name": "High",
             "consent_terms": True, "consent_data_processing": True}
    await client.post("/api/v1/auth/register", json=creds)
    login = await client.post("/api/v1/auth/login",
                              json={"email": creds["email"], "password": creds["password"]})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.patch("/api/v1/progress/daily-goal?goal_xp=9999", headers=headers)
    assert r.status_code == 200
    assert r.json()["daily_goal_xp"] == 500
