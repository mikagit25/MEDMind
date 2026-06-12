"""V4 Phase 3 — Trust pages & Reviewer API tests.

Tests:
  1. GET /api/v1/reviewers — returns empty list when no reviewers
  2. GET /api/v1/reviewers — returns active reviewer, excludes inactive
  3. GET /api/v1/reviewers/{slug} — 404 for unknown slug
  4. GET /api/v1/reviewers/{slug} — returns profile with reviewed_articles
  5. GET /api/v1/articles/{slug} — response includes reviewed_by and updated_at fields
"""
from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Article, Reviewer


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_reviewer(db: AsyncSession, **kwargs) -> Reviewer:
    defaults = dict(
        id=uuid.uuid4(),
        slug=f"dr-test-{uuid.uuid4().hex[:6]}",
        name="Dr. Test Reviewer",
        credentials="MD, PhD",
        bio="Board-certified specialist with 15 years of clinical experience.",
        institution="Test University Hospital",
        avatar_url=None,
        specialties=["cardiology", "internal_medicine"],
        linkedin_url=None,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    defaults.update(kwargs)
    r = Reviewer(**defaults)
    db.add(r)
    return r


def _make_article(db: AsyncSession, **kwargs) -> Article:
    defaults = dict(
        id=uuid.uuid4(),
        slug=f"article-{uuid.uuid4().hex[:8]}",
        title="Hypertension Management Guidelines",
        excerpt="Current guidelines for hypertension management.",
        body=[],
        category="cardiology",
        verification_status="passed",
        is_published=True,
        review_status="published",
    )
    defaults.update(kwargs)
    a = Article(**defaults)
    db.add(a)
    return a


# ── Reviewer list endpoint ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reviewer_list_empty(client: AsyncClient, db_session: AsyncSession):
    """Empty DB returns an empty list, not an error."""
    resp = await client.get("/api/v1/reviewers")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_reviewer_list_returns_active_only(client: AsyncClient, db_session: AsyncSession):
    """Only active reviewers appear in the list."""
    active = _make_reviewer(db_session, slug="active-reviewer", name="Active Reviewer", is_active=True)
    inactive = _make_reviewer(db_session, slug="inactive-reviewer", name="Inactive Reviewer", is_active=False)
    await db_session.commit()

    resp = await client.get("/api/v1/reviewers")
    assert resp.status_code == 200
    data = resp.json()
    slugs = [r["slug"] for r in data]
    assert "active-reviewer" in slugs
    assert "inactive-reviewer" not in slugs


@pytest.mark.asyncio
async def test_reviewer_list_fields(client: AsyncClient, db_session: AsyncSession):
    """Reviewer list items contain expected fields."""
    _make_reviewer(
        db_session,
        slug="dr-smith",
        name="Dr. Jane Smith",
        credentials="MD",
        institution="General Hospital",
        is_active=True,
    )
    await db_session.commit()

    resp = await client.get("/api/v1/reviewers")
    assert resp.status_code == 200
    item = next(r for r in resp.json() if r["slug"] == "dr-smith")
    assert item["name"] == "Dr. Jane Smith"
    assert item["credentials"] == "MD"
    assert item["institution"] == "General Hospital"
    assert "specialties" in item
    assert "avatar_url" in item


# ── Reviewer detail endpoint ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reviewer_detail_not_found(client: AsyncClient, db_session: AsyncSession):
    """Unknown slug returns 404."""
    resp = await client.get("/api/v1/reviewers/does-not-exist")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_reviewer_detail_inactive_404(client: AsyncClient, db_session: AsyncSession):
    """Inactive reviewer returns 404 even if slug exists."""
    _make_reviewer(db_session, slug="retired-dr", is_active=False)
    await db_session.commit()
    resp = await client.get("/api/v1/reviewers/retired-dr")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_reviewer_detail_profile(client: AsyncClient, db_session: AsyncSession):
    """Active reviewer detail includes all profile fields."""
    rev = _make_reviewer(
        db_session,
        slug="dr-jones",
        name="Dr. Alex Jones",
        credentials="MBBS, FRCP",
        bio="Cardiologist at Central Hospital.",
        linkedin_url="https://linkedin.com/in/drjones",
        is_active=True,
    )
    await db_session.commit()

    resp = await client.get("/api/v1/reviewers/dr-jones")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Dr. Alex Jones"
    assert data["credentials"] == "MBBS, FRCP"
    assert data["bio"] == "Cardiologist at Central Hospital."
    assert data["linkedin_url"] == "https://linkedin.com/in/drjones"
    assert "reviewed_articles" in data
    assert isinstance(data["reviewed_articles"], list)


@pytest.mark.asyncio
async def test_reviewer_detail_with_articles(client: AsyncClient, db_session: AsyncSession):
    """Reviewer detail returns articles reviewed by this person."""
    rev_name = "Dr. Maria Rossi"
    rev = _make_reviewer(
        db_session,
        slug="dr-rossi",
        name=rev_name,
        is_active=True,
    )
    art1 = _make_article(
        db_session,
        slug="article-rossi-1",
        title="Atrial Fibrillation",
        reviewed_by=rev_name,
        is_published=True,
        review_status="published",
    )
    art2 = _make_article(
        db_session,
        slug="article-other",
        title="Diabetes Overview",
        reviewed_by="Other Reviewer",
        is_published=True,
        review_status="published",
    )
    await db_session.commit()

    resp = await client.get("/api/v1/reviewers/dr-rossi")
    assert resp.status_code == 200
    data = resp.json()
    reviewed_slugs = [a["slug"] for a in data["reviewed_articles"]]
    assert "article-rossi-1" in reviewed_slugs
    assert "article-other" not in reviewed_slugs


# ── Article detail includes trust fields ───────────────────────────────────────

@pytest.mark.asyncio
async def test_article_detail_includes_reviewed_by(client: AsyncClient, db_session: AsyncSession):
    """Article detail response exposes reviewed_by and updated_at fields."""
    art = _make_article(
        db_session,
        slug="reviewed-article",
        reviewed_by="Dr. Expert Reviewer",
        updated_at=datetime(2026, 6, 1),
    )
    await db_session.commit()

    resp = await client.get("/api/v1/articles/reviewed-article")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("reviewed_by") == "Dr. Expert Reviewer"
    assert data.get("updated_at") is not None


@pytest.mark.asyncio
async def test_article_detail_reviewed_by_null(client: AsyncClient, db_session: AsyncSession):
    """Articles without a reviewer return reviewed_by as null (no error)."""
    _make_article(db_session, slug="unreviewed-article", reviewed_by=None)
    await db_session.commit()

    resp = await client.get("/api/v1/articles/unreviewed-article")
    assert resp.status_code == 200
    data = resp.json()
    assert "reviewed_by" in data
    assert data["reviewed_by"] is None
