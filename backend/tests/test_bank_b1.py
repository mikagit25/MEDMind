"""Bank-Scale B1 — Content Source Registry tests.

Verifies:
- ContentSource model fields and constraints
- Seed data integrity (license, text_reuse_allowed, verified_at, source_type)
- GET /public/content-sources returns all sources
- source_type filter works
- NC/ND/unclear sources have text_reuse_allowed=False
- Public domain / CC-BY sources have text_reuse_allowed=True
- Each source has verified_at set
- attribution_template present for text_reuse_allowed=True sources
"""
from __future__ import annotations
import pytest
import pytest_asyncio
from app.scripts.seed_content_sources import SOURCES
from app.models.models import ContentSource


@pytest_asyncio.fixture
async def seeded_sources(db_session, client):
    """Populate the test DB with all seed sources, then yield the client."""
    for src in SOURCES:
        existing = await db_session.get(ContentSource, src["slug"])
        if not existing:
            db_session.add(ContentSource(**src))
    await db_session.commit()
    yield client


# ── Unit: seed data integrity ─────────────────────────────────────────────────

def test_all_sources_have_required_fields():
    """Every seed entry has slug, title, publisher, url, license, source_type, verified_at."""
    required = ("slug", "title", "publisher", "url", "license", "source_type", "verified_at")
    for src in SOURCES:
        for field in required:
            assert field in src and src[field], f"Missing {field!r} in {src.get('slug')}"


def test_nc_nd_sources_have_text_reuse_false():
    """Sources with NC or ND licenses must have text_reuse_allowed=False."""
    nc_nd_slugs = {"statpearls", "who", "medlineplus_adam"}
    for src in SOURCES:
        if src["slug"] in nc_nd_slugs:
            assert src["text_reuse_allowed"] is False, (
                f"{src['slug']} has NC/ND license but text_reuse_allowed=True"
            )


def test_public_domain_sources_have_text_reuse_true():
    """Public domain US gov sources must have text_reuse_allowed=True."""
    pd_slugs = {"medlineplus_topics", "cdc"}
    for src in SOURCES:
        if src["slug"] in pd_slugs:
            assert src["text_reuse_allowed"] is True, (
                f"{src['slug']} is public domain but text_reuse_allowed=False"
            )


def test_text_reuse_true_sources_have_attribution_template():
    """Every text_reuse_allowed=True source must have an attribution_template."""
    for src in SOURCES:
        if src["text_reuse_allowed"]:
            assert src.get("attribution_template"), (
                f"{src['slug']} allows text reuse but has no attribution_template"
            )


def test_unclear_sources_have_text_reuse_false():
    """Sources with 'unclear' license must be conservative (text_reuse_allowed=False)."""
    for src in SOURCES:
        if "unclear" in src.get("license", "").lower():
            assert src["text_reuse_allowed"] is False, (
                f"{src['slug']} has unclear license but text_reuse_allowed=True"
            )


def test_all_sources_have_valid_source_type():
    """source_type must be one of the allowed values."""
    valid_types = {"reference", "guideline", "gov_health", "official_exam_blueprint"}
    for src in SOURCES:
        assert src["source_type"] in valid_types, (
            f"{src['slug']} has invalid source_type {src['source_type']!r}"
        )


def test_minimum_source_count():
    """At least 10 sources seeded — B1 requires comprehensive coverage."""
    assert len(SOURCES) >= 10, f"Only {len(SOURCES)} sources defined, need ≥10"


def test_blueprint_sources_present():
    """Key exam blueprints must be in the registry."""
    slugs = {s["slug"] for s in SOURCES}
    assert "ncsbn_nclex_rn" in slugs, "NCSBN NCLEX blueprint missing"
    assert "scfhs_snle" in slugs, "SNLE blueprint missing"
    assert "dha_blueprint" in slugs, "DHA blueprint missing"


def test_key_clinical_references_present():
    """Core clinical references must be registered."""
    slugs = {s["slug"] for s in SOURCES}
    assert "statpearls" in slugs
    assert "cdc" in slugs
    assert "medlineplus_topics" in slugs


# ── HTTP: GET /public/content-sources ────────────────────────────────────────

@pytest.mark.asyncio
async def test_content_sources_public_no_auth(seeded_sources):
    """GET /public/content-sources requires no authentication."""
    resp = await seeded_sources.get("/api/v1/public/content-sources")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 10


@pytest.mark.asyncio
async def test_content_sources_have_required_keys(seeded_sources):
    """Each source in response has all required fields."""
    resp = await seeded_sources.get("/api/v1/public/content-sources")
    assert resp.status_code == 200
    for src in resp.json():
        for field in ("slug", "title", "publisher", "url", "license", "text_reuse_allowed", "source_type"):
            assert field in src, f"Missing {field!r} in response item"


@pytest.mark.asyncio
async def test_content_sources_filter_by_type(seeded_sources):
    """?source_type= filter returns only matching entries."""
    resp = await seeded_sources.get("/api/v1/public/content-sources?source_type=gov_health")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    for src in data:
        assert src["source_type"] == "gov_health"


@pytest.mark.asyncio
async def test_content_sources_filter_blueprint(seeded_sources):
    """Filter official_exam_blueprint returns at least 3 entries."""
    resp = await seeded_sources.get("/api/v1/public/content-sources?source_type=official_exam_blueprint")
    assert resp.status_code == 200
    assert len(resp.json()) >= 3


@pytest.mark.asyncio
async def test_content_sources_nc_nd_are_false_in_response(seeded_sources):
    """StatPearls must have text_reuse_allowed=false in API response."""
    resp = await seeded_sources.get("/api/v1/public/content-sources")
    assert resp.status_code == 200
    by_slug = {s["slug"]: s for s in resp.json()}
    assert "statpearls" in by_slug
    assert by_slug["statpearls"]["text_reuse_allowed"] is False


@pytest.mark.asyncio
async def test_content_sources_public_domain_are_true_in_response(seeded_sources):
    """CDC must have text_reuse_allowed=true in API response."""
    resp = await seeded_sources.get("/api/v1/public/content-sources")
    assert resp.status_code == 200
    by_slug = {s["slug"]: s for s in resp.json()}
    assert "cdc" in by_slug
    assert by_slug["cdc"]["text_reuse_allowed"] is True
