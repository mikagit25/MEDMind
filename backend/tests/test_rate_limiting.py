"""E5: AI rate-limiting — Free tier gets 429 on the 6th daily request."""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch


# ---------------------------------------------------------------------------
# Helper — register + login user, return auth header
# ---------------------------------------------------------------------------

async def _register_and_login(client, email: str, password: str = "Str0ng!Pass") -> str:
    r = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "first_name": "Rate",
        "last_name": "Tester",
        "consent_terms": True,
        "consent_data_processing": True,
    })
    assert r.status_code == 201, r.text
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_free_tier_rate_limit(client):
    """Free-tier user (5 req/day limit) gets 429 on the 6th AI ask."""
    token = await _register_and_login(client, "free_rl@test.medmind")
    headers = {"Authorization": f"Bearer {token}"}

    # Patch AI router so we don't need real API keys
    mock_reply = {"reply": "mock answer", "model": "claude-haiku", "from_cache": False, "tokens": 10}
    with patch("app.api.v1.routes.ai.route_ai_request", new_callable=AsyncMock, return_value=mock_reply):
        for i in range(1, 6):
            r = await client.post("/api/v1/ai/ask", headers=headers, json={
                "message": f"Question {i}",
                "specialty": "general",
                "mode": "tutor",
            })
            assert r.status_code == 200, f"Request {i} should succeed; got {r.status_code}: {r.text}"

        # 6th request → 429
        r = await client.post("/api/v1/ai/ask", headers=headers, json={
            "message": "One too many",
            "specialty": "general",
            "mode": "tutor",
        })
        assert r.status_code == 429, f"Expected 429 on 6th request; got {r.status_code}: {r.text}"
        detail = r.json().get("detail", "")
        assert "limit" in detail.lower() or "429" in str(r.status_code)


@pytest.mark.asyncio
async def test_free_tier_exactly_at_limit_succeeds(client):
    """The 5th request (exactly at limit) still succeeds."""
    token = await _register_and_login(client, "free_rl5@test.medmind")
    headers = {"Authorization": f"Bearer {token}"}

    mock_reply = {"reply": "ok", "model": "claude-haiku", "from_cache": False, "tokens": 5}
    with patch("app.api.v1.routes.ai.route_ai_request", new_callable=AsyncMock, return_value=mock_reply):
        for i in range(1, 6):
            r = await client.post("/api/v1/ai/ask", headers=headers, json={
                "message": f"Q{i}", "specialty": "general", "mode": "tutor",
            })
            assert r.status_code == 200, f"Request {i} should succeed"


@pytest.mark.asyncio
async def test_unauthenticated_ai_ask_returns_401(client):
    """AI ask without a token returns 401."""
    r = await client.post("/api/v1/ai/ask", json={
        "message": "Hello", "specialty": "general", "mode": "tutor",
    })
    assert r.status_code == 401
