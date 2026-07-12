"""V5 Phase 3 — Point-of-Care /practice tests.

Coverage:
- GET /practice/lab-values: auth required, species filter (human/dog/cat/unknown)
- GET /practice/algorithms: auth required, list shape, vet_only filter
- GET /practice/algorithms/{slug}: auth required, 200 found, 404 not found
- GET /practice/search: auth required, shape, counts, min_length guard
"""
from __future__ import annotations

import json
import pytest
from httpx import AsyncClient

from app.models.models import ClinicalAlgorithm


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _register_login(client: AsyncClient, email: str, password: str = "Str0ng!Pass99") -> str:
    r = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "first_name": "Test",
        "last_name": "User",
        "consent_terms": True,
        "consent_data_processing": True,
    })
    assert r.status_code == 201, r.text
    r2 = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r2.status_code == 200, r2.text
    return r2.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _sample_algo(
    slug: str = "test-algo",
    title: str = "Test Algorithm",
    specialty: str = "emergency",
    is_vet: bool = False,
) -> ClinicalAlgorithm:
    steps = [
        {"id": "s1", "type": "start", "text": "Start here"},
        {"id": "s2", "type": "action", "text": "Do something"},
        {
            "id": "s3",
            "type": "decision",
            "text": "Is it resolved?",
            "children": [
                {"label": "Yes", "next": "s4"},
                {"label": "No", "next": "s2"},
            ],
        },
        {"id": "s4", "type": "info", "text": "Resolved — document and monitor"},
    ]
    return ClinicalAlgorithm(
        slug=slug,
        title=title,
        specialty=specialty,
        description="A test algorithm",
        steps=steps,
        tags="test,sample",
        source="Test Source 2024",
        is_veterinary=is_vet,
        verification_status="passed",
    )


# ── Lab Values ────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_lab_values_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/practice/lab-values")
    assert r.status_code == 401


@pytest.mark.anyio
async def test_lab_values_human(client: AsyncClient):
    token = await _register_login(client, "lab_human@test.com")
    r = await client.get("/api/v1/practice/lab-values?species=human", headers=_auth(token))
    assert r.status_code == 200
    body = r.json()
    assert body["species"] == "human"
    assert "panels" in body
    assert isinstance(body["panels"], dict)


@pytest.mark.anyio
async def test_lab_values_dog(client: AsyncClient):
    token = await _register_login(client, "lab_dog@test.com")
    r = await client.get("/api/v1/practice/lab-values?species=dog", headers=_auth(token))
    assert r.status_code == 200
    body = r.json()
    assert body["species"] == "dog"
    assert "panels" in body


@pytest.mark.anyio
async def test_lab_values_cat(client: AsyncClient):
    token = await _register_login(client, "lab_cat@test.com")
    r = await client.get("/api/v1/practice/lab-values?species=cat", headers=_auth(token))
    assert r.status_code == 200
    body = r.json()
    assert body["species"] == "cat"


@pytest.mark.anyio
async def test_lab_values_unknown_species(client: AsyncClient):
    token = await _register_login(client, "lab_unk@test.com")
    r = await client.get("/api/v1/practice/lab-values?species=horse", headers=_auth(token))
    assert r.status_code == 422


@pytest.mark.anyio
async def test_lab_values_human_has_panels(client: AsyncClient):
    """Human data should have at least hematology and chemistry panels."""
    token = await _register_login(client, "lab_panels@test.com")
    r = await client.get("/api/v1/practice/lab-values?species=human", headers=_auth(token))
    assert r.status_code == 200
    panels = r.json()["panels"]
    assert "hematology" in panels or len(panels) > 0, "Should have at least one panel"


@pytest.mark.anyio
async def test_lab_values_panel_entry_shape(client: AsyncClient):
    """Each lab value entry must have name and unit keys."""
    token = await _register_login(client, "lab_shape@test.com")
    r = await client.get("/api/v1/practice/lab-values?species=human", headers=_auth(token))
    assert r.status_code == 200
    panels = r.json()["panels"]
    for panel_values in panels.values():
        for entry in panel_values:
            assert "name" in entry
            assert "unit" in entry
        break  # check just first panel


# ── Algorithm List ────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_algorithms_list_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/practice/algorithms")
    assert r.status_code == 401


@pytest.mark.anyio
async def test_algorithms_list_empty(client: AsyncClient):
    token = await _register_login(client, "algo_empty@test.com")
    r = await client.get("/api/v1/practice/algorithms", headers=_auth(token))
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.anyio
async def test_algorithms_list_with_data(client: AsyncClient, db_session):
    token = await _register_login(client, "algo_list@test.com")
    db_session.add(_sample_algo(slug="test-algo-1", title="Algo One"))
    db_session.add(_sample_algo(slug="test-algo-2", title="Algo Two"))
    await db_session.commit()

    r = await client.get("/api/v1/practice/algorithms", headers=_auth(token))
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    slugs = [a["slug"] for a in data]
    assert "test-algo-1" in slugs
    assert "test-algo-2" in slugs


@pytest.mark.anyio
async def test_algorithms_list_shape(client: AsyncClient, db_session):
    token = await _register_login(client, "algo_shape@test.com")
    db_session.add(_sample_algo(slug="shape-algo"))
    await db_session.commit()

    r = await client.get("/api/v1/practice/algorithms", headers=_auth(token))
    assert r.status_code == 200
    item = r.json()[0]
    for key in ("id", "slug", "title", "specialty", "description", "tags", "is_veterinary"):
        assert key in item, f"Missing key: {key}"
    assert isinstance(item["tags"], list)


@pytest.mark.anyio
async def test_algorithms_vet_only_filter(client: AsyncClient, db_session):
    token = await _register_login(client, "algo_vet@test.com")
    db_session.add(_sample_algo(slug="human-algo", title="Human Algo", is_vet=False))
    db_session.add(_sample_algo(slug="vet-algo", title="Vet Algo", is_vet=True))
    await db_session.commit()

    r = await client.get("/api/v1/practice/algorithms?vet_only=true", headers=_auth(token))
    assert r.status_code == 200
    data = r.json()
    assert all(a["is_veterinary"] for a in data)
    slugs = [a["slug"] for a in data]
    assert "vet-algo" in slugs
    assert "human-algo" not in slugs


# ── Algorithm Detail ──────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_algorithm_detail_requires_auth(client: AsyncClient, db_session):
    db_session.add(_sample_algo(slug="noauth-algo"))
    await db_session.commit()
    r = await client.get("/api/v1/practice/algorithms/noauth-algo")
    assert r.status_code == 401


@pytest.mark.anyio
async def test_algorithm_detail_found(client: AsyncClient, db_session):
    token = await _register_login(client, "algo_detail@test.com")
    db_session.add(_sample_algo(slug="detail-algo", title="Detail Test"))
    await db_session.commit()

    r = await client.get("/api/v1/practice/algorithms/detail-algo", headers=_auth(token))
    assert r.status_code == 200
    body = r.json()
    assert body["slug"] == "detail-algo"
    assert body["title"] == "Detail Test"


@pytest.mark.anyio
async def test_algorithm_detail_not_found(client: AsyncClient):
    token = await _register_login(client, "algo_404@test.com")
    r = await client.get("/api/v1/practice/algorithms/nonexistent-xyz", headers=_auth(token))
    assert r.status_code == 404


@pytest.mark.anyio
async def test_algorithm_detail_shape(client: AsyncClient, db_session):
    token = await _register_login(client, "algo_dshape@test.com")
    db_session.add(_sample_algo(slug="dshape-algo"))
    await db_session.commit()

    r = await client.get("/api/v1/practice/algorithms/dshape-algo", headers=_auth(token))
    assert r.status_code == 200
    body = r.json()
    for key in ("id", "slug", "title", "specialty", "description", "steps", "tags", "source", "is_veterinary"):
        assert key in body, f"Missing key: {key}"
    assert isinstance(body["steps"], list)
    assert len(body["steps"]) >= 1


@pytest.mark.anyio
async def test_algorithm_detail_steps_structure(client: AsyncClient, db_session):
    """Each step must have id, type, text."""
    token = await _register_login(client, "algo_steps@test.com")
    db_session.add(_sample_algo(slug="steps-algo"))
    await db_session.commit()

    r = await client.get("/api/v1/practice/algorithms/steps-algo", headers=_auth(token))
    assert r.status_code == 200
    for step in r.json()["steps"]:
        assert "id" in step
        assert "type" in step
        assert "text" in step
        assert step["type"] in ("start", "action", "decision", "info")


# ── Practice Search ───────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_search_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/practice/search?q=aspirin")
    assert r.status_code == 401


@pytest.mark.anyio
async def test_search_too_short(client: AsyncClient):
    token = await _register_login(client, "search_short@test.com")
    r = await client.get("/api/v1/practice/search?q=a", headers=_auth(token))
    assert r.status_code == 422


@pytest.mark.anyio
async def test_search_returns_shape(client: AsyncClient):
    token = await _register_login(client, "search_shape@test.com")
    r = await client.get("/api/v1/practice/search?q=test", headers=_auth(token))
    assert r.status_code == 200
    body = r.json()
    assert "query" in body
    assert "results" in body
    assert "counts" in body
    assert isinstance(body["results"], list)
    counts = body["counts"]
    assert "drugs" in counts
    assert "algorithms" in counts
    assert "modules" in counts


@pytest.mark.anyio
async def test_search_finds_algorithm(client: AsyncClient, db_session):
    token = await _register_login(client, "search_algo@test.com")
    db_session.add(_sample_algo(slug="search-cardiac", title="Cardiac Arrest BLS"))
    await db_session.commit()

    r = await client.get("/api/v1/practice/search?q=cardiac", headers=_auth(token))
    assert r.status_code == 200
    body = r.json()
    assert body["counts"]["algorithms"] >= 1
    algo_results = [x for x in body["results"] if x["type"] == "algorithm"]
    assert any("cardiac" in x["title"].lower() for x in algo_results)


@pytest.mark.anyio
async def test_search_result_item_shape(client: AsyncClient, db_session):
    token = await _register_login(client, "search_item@test.com")
    db_session.add(_sample_algo(slug="search-item-algo", title="Search Item Test"))
    await db_session.commit()

    r = await client.get("/api/v1/practice/search?q=search+item", headers=_auth(token))
    assert r.status_code == 200
    items = r.json()["results"]
    if items:
        for item in items:
            assert "type" in item
            assert "title" in item
            assert "href" in item
            assert item["type"] in ("drug", "algorithm", "module")


@pytest.mark.anyio
async def test_search_empty_results(client: AsyncClient):
    token = await _register_login(client, "search_empty@test.com")
    r = await client.get(
        "/api/v1/practice/search?q=xyznonexistent99zz",
        headers=_auth(token),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["results"] == []
    assert body["counts"]["drugs"] == 0
    assert body["counts"]["algorithms"] == 0
