"""Content endpoint smoke tests."""
import pytest


@pytest.mark.asyncio
async def test_specialties_empty(client):
    """Returns empty list when no data seeded (test DB)."""
    r = await client.get("/api/v1/specialties")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_search_requires_min_length(client):
    r = await client.get("/api/v1/search?q=a")
    assert r.status_code == 422  # min_length=2


@pytest.mark.asyncio
async def test_search_works(client):
    r = await client.get("/api/v1/search?q=cardio")
    assert r.status_code == 200
    data = r.json()
    assert "modules" in data
    assert "lessons" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_module_not_found(client):
    r = await client.get("/api/v1/modules/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_drugs_requires_auth(client):
    r = await client.get("/api/v1/drugs?q=aspirin")
    assert r.status_code == 403
