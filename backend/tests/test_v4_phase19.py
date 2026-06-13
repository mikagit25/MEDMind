"""Phase 19: FHIR Learning Record Export — backend tests.

The feature surfaces the backend FHIR R4 export endpoints through a dedicated
frontend page. Previously /fhir/* routes had no frontend coverage at all.
"""
import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str) -> str:
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Str0ng!Pass99",
        "first_name": "Phase19",
        "last_name": "Tester",
        "consent_terms": True,
        "consent_data_processing": True,
    })
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": "Str0ng!Pass99"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Public endpoints ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fhir_metadata_public(client: AsyncClient):
    """GET /fhir/metadata returns CapabilityStatement without auth."""
    resp = await client.get("/api/v1/fhir/metadata")
    assert resp.status_code == 200
    data = resp.json()
    assert data["resourceType"] == "CapabilityStatement"
    assert data["fhirVersion"] == "4.0.1"


# ── Auth guards ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_practitioner_requires_auth(client: AsyncClient):
    """GET /fhir/Practitioner/me returns 401 without JWT."""
    resp = await client.get("/api/v1/fhir/Practitioner/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_bundle_requires_auth(client: AsyncClient):
    """GET /fhir/Bundle/me returns 401 without JWT."""
    resp = await client.get("/api/v1/fhir/Bundle/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_diagnostic_report_requires_auth(client: AsyncClient):
    """GET /fhir/DiagnosticReport/me returns 401 without JWT."""
    resp = await client.get("/api/v1/fhir/DiagnosticReport/me")
    assert resp.status_code == 401


# ── Practitioner ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_practitioner_shape(client: AsyncClient):
    """Practitioner resource has correct FHIR R4 structure."""
    token = await _register_and_login(client, "phase19_pract@test.medmind")
    resp = await client.get("/api/v1/fhir/Practitioner/me", headers=_h(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["resourceType"] == "Practitioner"
    assert "id" in data
    assert "name" in data
    assert isinstance(data["name"], list)


# ── DiagnosticReport ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_diagnostic_report_shape(client: AsyncClient):
    """DiagnosticReport has correct FHIR R4 structure."""
    token = await _register_and_login(client, "phase19_diag@test.medmind")
    resp = await client.get("/api/v1/fhir/DiagnosticReport/me", headers=_h(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["resourceType"] == "DiagnosticReport"
    assert "status" in data
    assert "subject" in data


# ── Bundle ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bundle_shape(client: AsyncClient):
    """Bundle has correct FHIR R4 collection structure."""
    token = await _register_and_login(client, "phase19_bundle@test.medmind")
    resp = await client.get("/api/v1/fhir/Bundle/me", headers=_h(token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["resourceType"] == "Bundle"
    assert data["type"] == "collection"
    assert "entry" in data
    assert isinstance(data["entry"], list)
    assert "total" in data


@pytest.mark.asyncio
async def test_bundle_contains_required_resources(client: AsyncClient):
    """Bundle entry list contains at least Practitioner and Observation."""
    token = await _register_and_login(client, "phase19_bundle2@test.medmind")
    resp = await client.get("/api/v1/fhir/Bundle/me", headers=_h(token))
    assert resp.status_code == 200
    entries = resp.json()["entry"]
    resource_types = {e["resource"]["resourceType"] for e in entries}
    assert "Practitioner" in resource_types
    assert "Observation" in resource_types


@pytest.mark.asyncio
async def test_bundle_is_valid_json(client: AsyncClient):
    """Bundle response is well-formed JSON with proper FHIR meta."""
    token = await _register_and_login(client, "phase19_json@test.medmind")
    resp = await client.get("/api/v1/fhir/Bundle/me", headers=_h(token))
    assert resp.status_code == 200
    data = resp.json()
    assert "meta" in data
    assert "lastUpdated" in data["meta"]
    assert "timestamp" in data
