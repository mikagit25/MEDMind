"""Phase 20: AI Conversation History — backend tests.

The feature exposes GET /ai/conversations (list) and
GET /ai/conversations/{id}/messages (detail) through a new /ai-history page.
Previously these endpoints had no frontend page.
"""
import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str) -> str:
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Str0ng!Pass99",
        "first_name": "Phase20",
        "last_name": "Tester",
        "consent_terms": True,
        "consent_data_processing": True,
    })
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": "Str0ng!Pass99"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Auth guards ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_conversations_requires_auth(client: AsyncClient):
    """GET /ai/conversations returns 401 without JWT."""
    resp = await client.get("/api/v1/ai/conversations")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_messages_requires_auth(client: AsyncClient):
    """GET /ai/conversations/{id}/messages returns 401 without JWT."""
    fake_id = "00000000-0000-0000-0000-000000000001"
    resp = await client.get(f"/api/v1/ai/conversations/{fake_id}/messages")
    assert resp.status_code == 401


# ── Happy path ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_conversations_returns_list(client: AsyncClient):
    """GET /ai/conversations returns a list (may be empty for new user)."""
    token = await _register_and_login(client, "phase20_list@test.medmind")
    resp = await client.get("/api/v1/ai/conversations", headers=_h(token))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_conversation_list_shape(client: AsyncClient):
    """GET /ai/conversations returns a list; each item has required fields."""
    token = await _register_and_login(client, "phase20_shape@test.medmind")
    conv_resp = await client.get("/api/v1/ai/conversations", headers=_h(token))
    assert conv_resp.status_code == 200
    convs = conv_resp.json()
    assert isinstance(convs, list)
    # New user has no conversations — validate shape if any exist
    for conv in convs:
        assert "id" in conv
        assert "mode" in conv
        assert "created_at" in conv
        assert "updated_at" in conv


@pytest.mark.asyncio
async def test_messages_for_unknown_conversation_404(client: AsyncClient):
    """GET /ai/conversations/{id}/messages with unknown ID returns 404."""
    token = await _register_and_login(client, "phase20_404@test.medmind")
    fake_id = "00000000-0000-0000-0000-000000000099"
    resp = await client.get(
        f"/api/v1/ai/conversations/{fake_id}/messages",
        headers=_h(token),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_conversations_isolated_per_user(client: AsyncClient):
    """Users' conversation lists are isolated from each other."""
    token_a = await _register_and_login(client, "phase20_iso_a@test.medmind")
    token_b = await _register_and_login(client, "phase20_iso_b@test.medmind")

    convs_a = (await client.get("/api/v1/ai/conversations", headers=_h(token_a))).json()
    convs_b = (await client.get("/api/v1/ai/conversations", headers=_h(token_b))).json()

    ids_a = {c["id"] for c in convs_a}
    ids_b = {c["id"] for c in convs_b}

    # Neither user's conversations should appear in the other's list
    assert ids_a.isdisjoint(ids_b)
