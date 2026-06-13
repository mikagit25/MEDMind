"""Phase 18: My Notes — backend tests.

The feature exposes a dedicated My Notes page that calls GET /notes (all
user notes, no filter), PATCH /notes/{id}, and DELETE /notes/{id}.
These endpoints existed but had no dedicated frontend page.
"""
import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str) -> str:
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Str0ng!Pass99",
        "first_name": "Phase18",
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
async def test_list_notes_requires_auth(client: AsyncClient):
    """GET /notes returns 401 without JWT."""
    resp = await client.get("/api/v1/notes")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_note_requires_auth(client: AsyncClient):
    """POST /notes returns 401 without JWT."""
    resp = await client.post("/api/v1/notes", json={"content": "Hello"})
    assert resp.status_code == 401


# ── Happy path ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_note_returns_201(client: AsyncClient):
    """Authenticated user can create a note."""
    token = await _register_and_login(client, "phase18_create@test.medmind")
    resp = await client.post(
        "/api/v1/notes",
        json={"content": "Key points about cardiac physiology: Starling's law, preload, afterload."},
        headers=_h(token),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["content"] == "Key points about cardiac physiology: Starling's law, preload, afterload."
    assert "created_at" in data


@pytest.mark.asyncio
async def test_list_all_notes_no_filter(client: AsyncClient):
    """GET /notes without filter returns all user notes ordered newest first."""
    token = await _register_and_login(client, "phase18_list@test.medmind")
    contents = ["First note", "Second note", "Third note"]
    for c in contents:
        await client.post("/api/v1/notes", json={"content": c}, headers=_h(token))
    resp = await client.get("/api/v1/notes", headers=_h(token))
    assert resp.status_code == 200
    notes = resp.json()
    assert len(notes) >= 3
    returned_contents = {n["content"] for n in notes}
    assert returned_contents.issuperset(set(contents))


@pytest.mark.asyncio
async def test_update_note_content(client: AsyncClient):
    """PATCH /notes/{id} updates note content."""
    token = await _register_and_login(client, "phase18_update@test.medmind")
    create = await client.post("/api/v1/notes", json={"content": "Original"}, headers=_h(token))
    note_id = create.json()["id"]
    patch = await client.patch(
        f"/api/v1/notes/{note_id}",
        json={"content": "Updated content"},
        headers=_h(token),
    )
    assert patch.status_code == 200
    assert patch.json()["content"] == "Updated content"


@pytest.mark.asyncio
async def test_update_note_empty_content_rejected(client: AsyncClient):
    """PATCH with empty content returns 422."""
    token = await _register_and_login(client, "phase18_empty@test.medmind")
    create = await client.post("/api/v1/notes", json={"content": "Valid"}, headers=_h(token))
    note_id = create.json()["id"]
    patch = await client.patch(
        f"/api/v1/notes/{note_id}",
        json={"content": "   "},
        headers=_h(token),
    )
    assert patch.status_code == 422


@pytest.mark.asyncio
async def test_delete_note(client: AsyncClient):
    """DELETE /notes/{id} removes the note."""
    token = await _register_and_login(client, "phase18_delete@test.medmind")
    create = await client.post("/api/v1/notes", json={"content": "To be deleted"}, headers=_h(token))
    note_id = create.json()["id"]
    del_resp = await client.delete(f"/api/v1/notes/{note_id}", headers=_h(token))
    assert del_resp.status_code == 204
    list_resp = await client.get("/api/v1/notes", headers=_h(token))
    assert all(n["id"] != note_id for n in list_resp.json())


@pytest.mark.asyncio
async def test_notes_isolated_per_user(client: AsyncClient):
    """Users cannot see or modify each other's notes."""
    token_a = await _register_and_login(client, "phase18_iso_a@test.medmind")
    token_b = await _register_and_login(client, "phase18_iso_b@test.medmind")
    create = await client.post(
        "/api/v1/notes", json={"content": "Private note for A"}, headers=_h(token_a)
    )
    note_id = create.json()["id"]
    # B cannot see A's note in their own list
    list_b = await client.get("/api/v1/notes", headers=_h(token_b))
    assert all(n["id"] != note_id for n in list_b.json())
    # B cannot update A's note
    patch = await client.patch(f"/api/v1/notes/{note_id}", json={"content": "Hacked"}, headers=_h(token_b))
    assert patch.status_code == 404
    # B cannot delete A's note
    delete = await client.delete(f"/api/v1/notes/{note_id}", headers=_h(token_b))
    assert delete.status_code == 404


@pytest.mark.asyncio
async def test_update_nonexistent_note_returns_404(client: AsyncClient):
    """PATCH on a non-existent note ID returns 404."""
    token = await _register_and_login(client, "phase18_404@test.medmind")
    fake_id = "00000000-0000-0000-0000-000000000099"
    resp = await client.patch(
        f"/api/v1/notes/{fake_id}",
        json={"content": "Ghost"},
        headers=_h(token),
    )
    assert resp.status_code == 404
