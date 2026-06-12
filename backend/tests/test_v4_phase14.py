"""Phase 14: Community Flashcard Browser + Progress PDF Export tests."""
import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str) -> str:
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Str0ng!Pass99",
        "first_name": "Phase14",
        "last_name": "Tester",
        "consent_terms": True,
        "consent_data_processing": True,
    })
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": "Str0ng!Pass99"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Community flashcards: auth guards ────────────────────────────────────────

@pytest.mark.asyncio
async def test_community_browse_requires_auth(client: AsyncClient):
    """GET /my/flashcards/community returns 401 without JWT."""
    resp = await client.get("/api/v1/my/flashcards/community")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_community_clone_requires_auth(client: AsyncClient):
    """POST /my/flashcards/community/{id}/clone returns 401 without JWT."""
    resp = await client.post("/api/v1/my/flashcards/community/nonexistent-id/clone")
    assert resp.status_code == 401


# ── Community flashcards: response shape ─────────────────────────────────────

@pytest.mark.asyncio
async def test_community_browse_returns_list(client: AsyncClient):
    """GET /my/flashcards/community returns {cards, total, offset} for authenticated user."""
    token = await _register_and_login(client, "phase14_browse@test.medmind")
    resp = await client.get("/api/v1/my/flashcards/community", headers=_h(token))
    assert resp.status_code == 200
    data = resp.json()
    assert "cards" in data
    assert "total" in data
    assert "offset" in data
    assert isinstance(data["cards"], list)
    assert isinstance(data["total"], int)


@pytest.mark.asyncio
async def test_community_browse_accepts_filters(client: AsyncClient):
    """GET /my/flashcards/community accepts search, difficulty, limit, offset params."""
    token = await _register_and_login(client, "phase14_filter@test.medmind")
    resp = await client.get(
        "/api/v1/my/flashcards/community",
        params={"search": "cardiology", "difficulty": "easy", "limit": 5, "offset": 0},
        headers=_h(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "cards" in data


@pytest.mark.asyncio
async def test_community_clone_nonexistent_returns_404(client: AsyncClient):
    """Cloning a card that doesn't exist returns 404."""
    token = await _register_and_login(client, "phase14_clone_miss@test.medmind")
    resp = await client.post(
        "/api/v1/my/flashcards/community/00000000-0000-0000-0000-000000000000/clone",
        headers=_h(token),
    )
    assert resp.status_code == 404


# ── Progress PDF export: auth guard ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_progress_export_pdf_requires_auth(client: AsyncClient):
    """GET /progress/export/pdf returns 401 without JWT."""
    resp = await client.get("/api/v1/progress/export/pdf")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_progress_export_pdf_returns_pdf_content_type(client: AsyncClient):
    """GET /progress/export/pdf returns application/pdf for authenticated user."""
    token = await _register_and_login(client, "phase14_pdf@test.medmind")
    resp = await client.get("/api/v1/progress/export/pdf", headers=_h(token))
    assert resp.status_code == 200
    assert "pdf" in resp.headers.get("content-type", "").lower()
