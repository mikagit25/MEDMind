"""V4 Phase 1 — Content Verification Pipeline tests.

Tests:
  1. Status machine: pending → passed | failed
  2. Publication gateway: pending/failed content NOT served by public endpoints
  3. Claim-checker: unit tests with mocked AI calls
  4. Content-feedback endpoint: submit and validate
"""
from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Article, ContentFeedback, NewsArticle
from app.services.content_verifier import (
    PUBLISHED_STATUSES,
    BLOCKED_STATUSES,
    is_publicly_servable,
    verify_article,
)

# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_article(db: AsyncSession, **kwargs) -> Article:
    defaults = dict(
        id=uuid.uuid4(),
        slug=f"test-{uuid.uuid4().hex[:8]}",
        title="Test Article",
        excerpt="Test excerpt",
        body=[{"type": "p", "content": "Beta-blockers reduce mortality in heart failure by 34%."}],
        category="cardiology",
        verification_status="pending",
        is_published=True,
        review_status="published",
    )
    defaults.update(kwargs)
    article = Article(**defaults)
    db.add(article)
    return article


def _make_news(db: AsyncSession, **kwargs) -> NewsArticle:
    defaults = dict(
        id=uuid.uuid4(),
        slug=f"news-{uuid.uuid4().hex[:8]}",
        title="Test News",
        summary="Test summary",
        category="cardiology",
        source_name="PubMed",
        source_url="https://pubmed.example.com/12345",
        source_hash=uuid.uuid4().hex,
        verification_status="pending",
        is_published=True,
        review_status="published",
    )
    defaults.update(kwargs)
    news = NewsArticle(**defaults)
    db.add(news)
    return news


# ── Unit: status machine ───────────────────────────────────────────────────────

class TestStatusMachine:
    def test_published_statuses(self):
        assert "passed" in PUBLISHED_STATUSES
        assert "human_reviewed" in PUBLISHED_STATUSES

    def test_blocked_statuses(self):
        assert "pending" in BLOCKED_STATUSES
        assert "failed" in BLOCKED_STATUSES

    def test_is_publicly_servable_passed(self):
        assert is_publicly_servable("passed") is True

    def test_is_publicly_servable_human_reviewed(self):
        assert is_publicly_servable("human_reviewed") is True

    def test_is_publicly_servable_pending(self):
        assert is_publicly_servable("pending") is False

    def test_is_publicly_servable_failed(self):
        assert is_publicly_servable("failed") is False

    def test_is_publicly_servable_none(self):
        assert is_publicly_servable(None) is False


# ── Unit: claim-checker (mocked AI) ───────────────────────────────────────────

class TestContentVerifier:
    @pytest.mark.asyncio
    async def test_verify_empty_article_returns_pending(self):
        result = await verify_article("test-id", [], sources=None)
        assert result["status"] == "pending"

    @pytest.mark.asyncio
    async def test_verify_no_sources_all_not_addressed(self):
        """With no sources to check against, we can't confirm anything."""
        body = [{"type": "p", "content": "Aspirin reduces fever."}]
        # Mock _extract_claims to return one claim, _fetch_source_text returns empty
        with patch(
            "app.services.content_verifier._extract_claims",
            new_callable=AsyncMock,
            return_value=["Aspirin reduces fever."],
        ), patch(
            "app.services.content_verifier._fetch_source_text",
            new_callable=AsyncMock,
            return_value="",
        ):
            result = await verify_article("test-id", body, sources=[{"url": "https://example.com"}])
        # No confirmed claims → pending
        assert result["status"] == "pending"

    @pytest.mark.asyncio
    async def test_verify_confirmed_claim_passes(self):
        """When all claims are confirmed by sources, status becomes 'passed'."""
        body = [{"type": "p", "content": "Aspirin reduces fever."}]
        with patch(
            "app.services.content_verifier._extract_claims",
            new_callable=AsyncMock,
            return_value=["Aspirin reduces fever."],
        ), patch(
            "app.services.content_verifier._fetch_source_text",
            new_callable=AsyncMock,
            return_value="Studies show aspirin reduces fever effectively.",
        ), patch(
            "app.services.content_verifier._check_claim_against_source",
            new_callable=AsyncMock,
            return_value={"result": "yes", "citation": "aspirin reduces fever"},
        ):
            result = await verify_article(
                "test-id",
                body,
                sources=[{"url": "https://example.com", "type": "study"}],
            )
        assert result["status"] == "passed"
        assert len(result["report"]) == 1
        assert result["report"][0]["result"] == "yes"

    @pytest.mark.asyncio
    async def test_verify_contradicted_claim_fails(self):
        """When a claim is contradicted, status becomes 'failed'."""
        body = [{"type": "p", "content": "Drug X has no side effects."}]
        with patch(
            "app.services.content_verifier._extract_claims",
            new_callable=AsyncMock,
            return_value=["Drug X has no side effects."],
        ), patch(
            "app.services.content_verifier._fetch_source_text",
            new_callable=AsyncMock,
            return_value="Drug X has significant side effects including nausea.",
        ), patch(
            "app.services.content_verifier._check_claim_against_source",
            new_callable=AsyncMock,
            return_value={"result": "no", "citation": "significant side effects"},
        ):
            result = await verify_article(
                "test-id",
                body,
                sources=[{"url": "https://example.com", "type": "study"}],
            )
        assert result["status"] == "failed"
        assert result["report"][0]["result"] == "no"

    @pytest.mark.asyncio
    async def test_verify_dry_run_returns_result(self):
        """dry_run=True should still return result without DB side effects."""
        body = [{"type": "p", "content": "Test claim."}]
        with patch(
            "app.services.content_verifier._extract_claims",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await verify_article("test-id", body, sources=None, dry_run=True)
        assert "status" in result
        assert "report" in result
        assert "verified_at" in result


# ── Integration: publication gateway ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_pending_article_not_served(client: AsyncClient, db_session: AsyncSession):
    """Articles with verification_status=pending must return 404 on public endpoints."""
    article = _make_article(db_session, verification_status="pending")
    await db_session.commit()

    resp = await client.get(f"/api/v1/articles/{article.slug}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_failed_article_not_served(client: AsyncClient, db_session: AsyncSession):
    """Articles with verification_status=failed must return 404."""
    article = _make_article(db_session, verification_status="failed")
    await db_session.commit()

    resp = await client.get(f"/api/v1/articles/{article.slug}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_passed_article_is_served(client: AsyncClient, db_session: AsyncSession):
    """Articles with verification_status=passed should be accessible."""
    article = _make_article(db_session, verification_status="passed")
    await db_session.commit()

    resp = await client.get(f"/api/v1/articles/{article.slug}")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_human_reviewed_article_is_served(client: AsyncClient, db_session: AsyncSession):
    """Articles with verification_status=human_reviewed should be accessible."""
    article = _make_article(db_session, verification_status="human_reviewed")
    await db_session.commit()

    resp = await client.get(f"/api/v1/articles/{article.slug}")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_pending_article_not_in_list(client: AsyncClient, db_session: AsyncSession):
    """Pending articles must not appear in the public articles list."""
    pending = _make_article(db_session, slug=f"pending-{uuid.uuid4().hex[:6]}", verification_status="pending")
    passed = _make_article(db_session, slug=f"passed-{uuid.uuid4().hex[:6]}", verification_status="passed")
    await db_session.commit()

    resp = await client.get("/api/v1/articles")
    assert resp.status_code == 200
    slugs = [a["slug"] for a in resp.json().get("articles", [])]
    assert pending.slug not in slugs
    assert passed.slug in slugs


@pytest.mark.asyncio
async def test_pending_article_not_in_sitemap(client: AsyncClient, db_session: AsyncSession):
    """Pending articles must not appear in sitemap data."""
    pending = _make_article(db_session, slug=f"sitemap-pending-{uuid.uuid4().hex[:6]}", verification_status="pending")
    passed = _make_article(db_session, slug=f"sitemap-passed-{uuid.uuid4().hex[:6]}", verification_status="passed")
    await db_session.commit()

    resp = await client.get("/api/v1/articles/sitemap-data")
    assert resp.status_code == 200
    slugs = [a["slug"] for a in resp.json()]
    assert pending.slug not in slugs
    assert passed.slug in slugs


@pytest.mark.asyncio
async def test_pending_news_not_served(client: AsyncClient, db_session: AsyncSession):
    """News with verification_status=pending must return 404."""
    news = _make_news(db_session, verification_status="pending")
    await db_session.commit()

    resp = await client.get(f"/api/v1/news/{news.slug}")
    assert resp.status_code == 404


# ── Integration: content-feedback endpoint ────────────────────────────────────

@pytest.mark.asyncio
async def test_submit_content_feedback(client: AsyncClient, db_session: AsyncSession):
    """Valid feedback should be stored with 201 status."""
    article = _make_article(db_session, verification_status="passed")
    await db_session.commit()

    resp = await client.post("/api/v1/articles/feedback", json={
        "content_type": "article",
        "content_id": str(article.id),
        "problem_type": "factual_error",
        "comment": "The dosage mentioned seems incorrect.",
    })
    assert resp.status_code == 201
    assert resp.json() == {"ok": True}


@pytest.mark.asyncio
async def test_submit_feedback_invalid_content_type(client: AsyncClient):
    """Invalid content_type should return 422."""
    resp = await client.post("/api/v1/articles/feedback", json={
        "content_type": "invalid",
        "content_id": "some-id",
        "problem_type": "factual_error",
    })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_submit_feedback_invalid_problem_type(client: AsyncClient):
    """Invalid problem_type should return 422."""
    resp = await client.post("/api/v1/articles/feedback", json={
        "content_type": "article",
        "content_id": "some-id",
        "problem_type": "wrong_type",
    })
    assert resp.status_code == 422
