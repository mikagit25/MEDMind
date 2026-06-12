"""Phase 9: Clinical Calculators backend tests."""
import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str) -> str:
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Str0ng!Pass99",
        "first_name": "Calc",
        "last_name": "Tester",
        "consent_terms": True,
        "consent_data_processing": True,
    })
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": "Str0ng!Pass99"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── GET /calculators (public) ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_calculators_public(client: AsyncClient):
    """Catalog is accessible without authentication."""
    resp = await client.get("/api/v1/calculators")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 20


@pytest.mark.asyncio
async def test_list_calculators_has_required_fields(client: AsyncClient):
    """Each catalog entry has slug, name, category."""
    resp = await client.get("/api/v1/calculators")
    assert resp.status_code == 200
    slugs = set()
    for calc in resp.json():
        assert "slug" in calc
        assert "name" in calc
        assert "category" in calc
        slugs.add(calc["slug"])
    assert "cha2ds2-vasc" in slugs
    assert "egfr-ckd-epi" in slugs
    assert "bmi" in slugs


# ── POST /calculators/{slug}/save-result ─────────────────────────────────────

@pytest.mark.asyncio
async def test_save_result_requires_auth(client: AsyncClient):
    """Save endpoint returns 401 without JWT."""
    resp = await client.post(
        "/api/v1/calculators/cha2ds2-vasc/save-result",
        json={"inputs": {"cb_0": 1}, "score": "3", "risk_level": "High"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_save_result_authenticated(client: AsyncClient):
    """Authenticated user can save a calculator result."""
    token = await _register_and_login(client, "calc_save@test.medmind")
    resp = await client.post(
        "/api/v1/calculators/cha2ds2-vasc/save-result",
        json={"inputs": {"cb_0": 1, "cb_1": 0}, "score": "1", "risk_level": "Low"},
        headers=_h(token),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["slug"] == "cha2ds2-vasc"
    assert data["score"] == "1"
    assert data["risk_level"] == "Low"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_save_result_unknown_slug(client: AsyncClient):
    """Saving for an unknown slug returns 404."""
    token = await _register_and_login(client, "calc_unknown@test.medmind")
    resp = await client.post(
        "/api/v1/calculators/not-a-real-calc/save-result",
        json={"inputs": {}, "score": "0"},
        headers=_h(token),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_save_result_with_note(client: AsyncClient):
    """Optional note field is persisted."""
    token = await _register_and_login(client, "calc_note@test.medmind")
    resp = await client.post(
        "/api/v1/calculators/bmi/save-result",
        json={"inputs": {"height": 175, "weight": 80}, "score": "26.1", "note": "Follow-up in 3 months"},
        headers=_h(token),
    )
    assert resp.status_code == 201
    assert resp.json()["note"] == "Follow-up in 3 months"


# ── GET /calculators/history ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_history_requires_auth(client: AsyncClient):
    """History endpoint returns 401 without JWT."""
    resp = await client.get("/api/v1/calculators/history")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_history_returns_saved_results(client: AsyncClient):
    """Saved results appear in history."""
    token = await _register_and_login(client, "calc_history@test.medmind")
    await client.post(
        "/api/v1/calculators/gcs/save-result",
        json={"inputs": {"eyes": 4, "verbal": 5, "motor": 6}, "score": "15", "risk_level": "Normal"},
        headers=_h(token),
    )
    await client.post(
        "/api/v1/calculators/qsofa/save-result",
        json={"inputs": {"resp": 1, "sbp": 1, "mental": 0}, "score": "2", "risk_level": "High"},
        headers=_h(token),
    )
    resp = await client.get("/api/v1/calculators/history", headers=_h(token))
    assert resp.status_code == 200
    slugs = [r["slug"] for r in resp.json()]
    assert "gcs" in slugs
    assert "qsofa" in slugs


@pytest.mark.asyncio
async def test_history_slug_filter(client: AsyncClient):
    """?slug= filter returns only matching results."""
    token = await _register_and_login(client, "calc_filter@test.medmind")
    await client.post(
        "/api/v1/calculators/wells-dvt/save-result",
        json={"inputs": {"cb_0": 1}, "score": "1", "risk_level": "Low"},
        headers=_h(token),
    )
    await client.post(
        "/api/v1/calculators/bmi/save-result",
        json={"inputs": {"h": 170, "w": 70}, "score": "24.2"},
        headers=_h(token),
    )
    resp = await client.get("/api/v1/calculators/history?slug=wells-dvt", headers=_h(token))
    assert resp.status_code == 200
    for item in resp.json():
        assert item["slug"] == "wells-dvt"


@pytest.mark.asyncio
async def test_history_is_user_scoped(client: AsyncClient):
    """User A's history is not visible to User B."""
    token_a = await _register_and_login(client, "calc_scope_a@test.medmind")
    token_b = await _register_and_login(client, "calc_scope_b@test.medmind")
    await client.post(
        "/api/v1/calculators/curb-65/save-result",
        json={"inputs": {"cb_0": 1}, "score": "1"},
        headers=_h(token_a),
    )
    resp = await client.get("/api/v1/calculators/history?slug=curb-65", headers=_h(token_b))
    assert resp.status_code == 200
    assert resp.json() == []


# ── DELETE /calculators/history/{id} ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_result(client: AsyncClient):
    """Authenticated user can delete their own result."""
    token = await _register_and_login(client, "calc_delete@test.medmind")
    create_resp = await client.post(
        "/api/v1/calculators/has-bled/save-result",
        json={"inputs": {"hypertension": 1}, "score": "1", "risk_level": "Low"},
        headers=_h(token),
    )
    assert create_resp.status_code == 201
    result_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/calculators/history/{result_id}", headers=_h(token))
    assert del_resp.status_code == 204

    history = await client.get("/api/v1/calculators/history?slug=has-bled", headers=_h(token))
    ids = [r["id"] for r in history.json()]
    assert result_id not in ids


@pytest.mark.asyncio
async def test_delete_result_requires_auth(client: AsyncClient):
    """Delete endpoint returns 401 without JWT."""
    token = await _register_and_login(client, "calc_delauth@test.medmind")
    create_resp = await client.post(
        "/api/v1/calculators/abcd2/save-result",
        json={"inputs": {}, "score": "0"},
        headers=_h(token),
    )
    result_id = create_resp.json()["id"]
    resp = await client.delete(f"/api/v1/calculators/history/{result_id}")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_delete_result_wrong_user(client: AsyncClient):
    """User B cannot delete User A's result."""
    token_a = await _register_and_login(client, "calc_del_a@test.medmind")
    token_b = await _register_and_login(client, "calc_del_b@test.medmind")
    create_resp = await client.post(
        "/api/v1/calculators/sofa/save-result",
        json={"inputs": {}, "score": "2"},
        headers=_h(token_a),
    )
    result_id = create_resp.json()["id"]
    resp = await client.delete(f"/api/v1/calculators/history/{result_id}", headers=_h(token_b))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_invalid_uuid(client: AsyncClient):
    """Invalid UUID returns 422."""
    token = await _register_and_login(client, "calc_uuid@test.medmind")
    resp = await client.delete("/api/v1/calculators/history/not-a-uuid", headers=_h(token))
    assert resp.status_code == 422
