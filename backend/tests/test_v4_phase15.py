"""Phase 15: Drug Interaction Checker tests."""
import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str) -> str:
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Str0ng!Pass99",
        "first_name": "Phase15",
        "last_name": "Tester",
        "consent_terms": True,
        "consent_data_processing": True,
    })
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": "Str0ng!Pass99"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Auth: endpoint is optional-auth, so no hard 401 block ────────────────────

@pytest.mark.asyncio
async def test_interaction_check_no_auth_allowed(client: AsyncClient):
    """POST /drugs/check-interactions works without auth (optional auth)."""
    resp = await client.post(
        "/api/v1/drugs/check-interactions",
        json={"drug_ids": [
            "00000000-0000-0000-0000-000000000001",
            "00000000-0000-0000-0000-000000000002",
        ]},
    )
    # 200 with empty interactions (unknown drug IDs have no entries) or 422
    assert resp.status_code in (200, 422)


# ── Validation ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_interaction_check_single_drug_returns_422(client: AsyncClient):
    """Fewer than 2 drug IDs returns 422."""
    token = await _register_and_login(client, "phase15_single@test.medmind")
    resp = await client.post(
        "/api/v1/drugs/check-interactions",
        json={"drug_ids": ["00000000-0000-0000-0000-000000000001"]},
        headers=_h(token),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_interaction_check_empty_returns_422(client: AsyncClient):
    """Empty drug_ids list returns 422."""
    token = await _register_and_login(client, "phase15_empty@test.medmind")
    resp = await client.post(
        "/api/v1/drugs/check-interactions",
        json={"drug_ids": []},
        headers=_h(token),
    )
    assert resp.status_code == 422


# ── Response shape ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_interaction_check_returns_correct_shape(client: AsyncClient):
    """POST /drugs/check-interactions returns {interactions, pairs_checked}."""
    token = await _register_and_login(client, "phase15_shape@test.medmind")
    resp = await client.post(
        "/api/v1/drugs/check-interactions",
        json={"drug_ids": [
            "00000000-0000-0000-0000-000000000001",
            "00000000-0000-0000-0000-000000000002",
        ]},
        headers=_h(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "interactions" in data
    assert "pairs_checked" in data
    assert isinstance(data["interactions"], list)
    assert isinstance(data["pairs_checked"], int)


@pytest.mark.asyncio
async def test_interaction_check_three_drugs_counts_pairs(client: AsyncClient):
    """3 drugs → pairs_checked == 3 (C(3,2) = 3)."""
    token = await _register_and_login(client, "phase15_pairs@test.medmind")
    resp = await client.post(
        "/api/v1/drugs/check-interactions",
        json={"drug_ids": [
            "00000000-0000-0000-0000-000000000001",
            "00000000-0000-0000-0000-000000000002",
            "00000000-0000-0000-0000-000000000003",
        ]},
        headers=_h(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["pairs_checked"] == 3


@pytest.mark.asyncio
async def test_interaction_check_unknown_drugs_returns_empty(client: AsyncClient):
    """Drug IDs with no DB entries return empty interactions list."""
    token = await _register_and_login(client, "phase15_unknown@test.medmind")
    resp = await client.post(
        "/api/v1/drugs/check-interactions",
        json={"drug_ids": [
            "00000000-0000-0000-0000-000000000001",
            "00000000-0000-0000-0000-000000000002",
        ]},
        headers=_h(token),
    )
    assert resp.status_code == 200
    assert resp.json()["interactions"] == []


# ── Dose calculator ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dose_calculate_returns_result(client: AsyncClient):
    """POST /drugs/calculate-dose returns dose calculation with disclaimer."""
    resp = await client.post(
        "/api/v1/drugs/calculate-dose",
        json={
            "drug_name": "amoxicillin",
            "weight_kg": 70,
            "dose_per_kg": 25,
            "unit": "mg",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["adjusted_dose"] == pytest.approx(1750.0)
    assert "disclaimer" in data


@pytest.mark.asyncio
async def test_dose_calculate_renal_adjustment(client: AsyncClient):
    """Renal GFR < 30 reduces dose by 50%."""
    resp = await client.post(
        "/api/v1/drugs/calculate-dose",
        json={
            "drug_name": "test_drug",
            "weight_kg": 60,
            "dose_per_kg": 10,
            "unit": "mg",
            "renal_gfr": 20,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["adjusted_dose"] == pytest.approx(300.0)  # 600 * 0.5
    assert data["renal_factor"] == pytest.approx(0.5)
