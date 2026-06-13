"""Phase 17: Calculator History — backend tests.

Feature: Authenticated users can save calculator results and retrieve their
history. The calculatorsApi.saveResult / getHistory / deleteResult methods
are now wired to a real page (/app/(app)/calculators).
"""
import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str) -> str:
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Str0ng!Pass99",
        "first_name": "Phase17",
        "last_name": "Tester",
        "consent_terms": True,
        "consent_data_processing": True,
    })
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": "Str0ng!Pass99"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Catalog (public) ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_calculators_public(client: AsyncClient):
    """GET /calculators returns catalog without auth."""
    resp = await client.get("/api/v1/calculators")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    slugs = {c["slug"] for c in data}
    assert "egfr-ckd-epi" in slugs
    assert "bmi" in slugs
    assert "cha2ds2-vasc" in slugs


# ── Auth guards ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_save_result_requires_auth(client: AsyncClient):
    """POST /calculators/{slug}/save-result returns 401 without JWT."""
    resp = await client.post(
        "/api/v1/calculators/bmi/save-result",
        json={"inputs": {"weight": 70, "height": 175}, "score": "22.9", "risk_level": "normal"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_history_requires_auth(client: AsyncClient):
    """GET /calculators/history returns 401 without JWT."""
    resp = await client.get("/api/v1/calculators/history")
    assert resp.status_code == 401


# ── Happy path ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_save_result_returns_201(client: AsyncClient):
    """Authenticated user can save a calculator result."""
    token = await _register_and_login(client, "phase17_save@test.medmind")
    resp = await client.post(
        "/api/v1/calculators/egfr-ckd-epi/save-result",
        json={
            "inputs": {"creatinine": 1.2, "age": 55, "sex": "male"},
            "score": "62",
            "risk_level": "G2 — Mildly decreased",
        },
        headers=_h(token),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["slug"] == "egfr-ckd-epi"
    assert data["score"] == "62"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_save_result_with_note(client: AsyncClient):
    """Calculator result note is saved and returned."""
    token = await _register_and_login(client, "phase17_note@test.medmind")
    resp = await client.post(
        "/api/v1/calculators/bmi/save-result",
        json={
            "inputs": {"weight": 85, "height": 180},
            "score": "26.2",
            "risk_level": "overweight",
            "note": "Patient follow-up in 3 months",
        },
        headers=_h(token),
    )
    assert resp.status_code == 201
    assert resp.json()["note"] == "Patient follow-up in 3 months"


@pytest.mark.asyncio
async def test_history_contains_saved_result(client: AsyncClient):
    """Saved result appears in GET /calculators/history."""
    token = await _register_and_login(client, "phase17_history@test.medmind")
    await client.post(
        "/api/v1/calculators/cha2ds2-vasc/save-result",
        json={"inputs": {"age": 72, "sex": "female", "chf": 1}, "score": "3", "risk_level": "high"},
        headers=_h(token),
    )
    resp = await client.get("/api/v1/calculators/history", headers=_h(token))
    assert resp.status_code == 200
    items = resp.json()
    assert any(r["slug"] == "cha2ds2-vasc" for r in items)


@pytest.mark.asyncio
async def test_history_filter_by_slug(client: AsyncClient):
    """History filtered by slug only returns results for that calculator."""
    token = await _register_and_login(client, "phase17_filter@test.medmind")
    for slug in ("bmi", "gcs"):
        await client.post(
            f"/api/v1/calculators/{slug}/save-result",
            json={"inputs": {"x": 1}, "score": "10"},
            headers=_h(token),
        )
    resp = await client.get("/api/v1/calculators/history?slug=bmi", headers=_h(token))
    assert resp.status_code == 200
    items = resp.json()
    assert all(r["slug"] == "bmi" for r in items)


@pytest.mark.asyncio
async def test_delete_result_removes_from_history(client: AsyncClient):
    """DELETE /calculators/history/{id} removes the result."""
    token = await _register_and_login(client, "phase17_delete@test.medmind")
    save_resp = await client.post(
        "/api/v1/calculators/sofa/save-result",
        json={"inputs": {"resp": 3, "cvs": 2}, "score": "5", "risk_level": "high"},
        headers=_h(token),
    )
    result_id = save_resp.json()["id"]
    del_resp = await client.delete(f"/api/v1/calculators/history/{result_id}", headers=_h(token))
    assert del_resp.status_code == 204
    # Confirm it's gone
    hist = await client.get("/api/v1/calculators/history", headers=_h(token))
    assert all(r["id"] != result_id for r in hist.json())


@pytest.mark.asyncio
async def test_save_result_unknown_slug_returns_404(client: AsyncClient):
    """Saving to a non-existent calculator slug returns 404."""
    token = await _register_and_login(client, "phase17_404@test.medmind")
    resp = await client.post(
        "/api/v1/calculators/imaginary-calc/save-result",
        json={"inputs": {"x": 1}, "score": "5"},
        headers=_h(token),
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_history_isolated_per_user(client: AsyncClient):
    """Users cannot see each other's calculator history."""
    token_a = await _register_and_login(client, "phase17_iso_a@test.medmind")
    token_b = await _register_and_login(client, "phase17_iso_b@test.medmind")
    await client.post(
        "/api/v1/calculators/curb-65/save-result",
        json={"inputs": {"bun": 22, "resp": 31}, "score": "2"},
        headers=_h(token_a),
    )
    resp_b = await client.get("/api/v1/calculators/history", headers=_h(token_b))
    assert resp_b.status_code == 200
    assert all(r["slug"] != "curb-65" for r in resp_b.json())
