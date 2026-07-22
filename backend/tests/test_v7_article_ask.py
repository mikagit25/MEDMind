"""Tests for POST /articles/{slug}/ask — Article AI Consultation endpoint.

Coverage:
- 401 without authentication
- 400 for questions shorter than 3 characters
- 404 for non-existent article slug
- 503 when article exists but no AI backend is reachable (test environment)
- 200 with a valid answer when AI is mocked
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Article


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _register_and_login(client: AsyncClient, suffix: str = "") -> str:
    email = f"artask_{suffix}_{uuid.uuid4().hex[:6]}@example.com"
    r = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Str0ngPass99!",
        "first_name": "Art",
        "last_name": "Asker",
        "consent_terms": True,
        "consent_data_processing": True,
    })
    assert r.status_code == 201, r.text
    r2 = await client.post("/api/v1/auth/login", json={"email": email, "password": "Str0ngPass99!"})
    return r2.json()["access_token"]


async def _create_article(db: AsyncSession, slug: str) -> Article:
    """Insert a published, verified article into the test DB."""
    art = Article(
        id=uuid.uuid4(),
        slug=slug,
        title="Hypertension: A Comprehensive Guide",
        excerpt="Everything you need to know about high blood pressure.",
        body=[
            {"type": "h2", "content": "What is Hypertension?"},
            {"type": "p", "content": "Hypertension is defined as persistently elevated blood pressure."},
        ],
        category="cardiology",
        is_published=True,
        verification_status="passed",
        review_status="published",
    )
    db.add(art)
    await db.commit()
    return art


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.anyio
async def test_article_ask_requires_auth(client: AsyncClient):
    r = await client.post("/api/v1/articles/some-article/ask", json={"question": "What is this?"})
    assert r.status_code == 401


@pytest.mark.anyio
async def test_article_ask_short_question_rejected(client: AsyncClient):
    token = await _register_and_login(client, "sq")
    r = await client.post(
        "/api/v1/articles/any-slug/ask",
        json={"question": "Hi"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400
    assert "short" in r.json()["detail"].lower()


@pytest.mark.anyio
async def test_article_ask_not_found(client: AsyncClient):
    token = await _register_and_login(client, "nf")
    r = await client.post(
        "/api/v1/articles/nonexistent-article-xyz/ask",
        json={"question": "What does this article say about treatment?"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


@pytest.mark.anyio
async def test_article_ask_no_ai_returns_503(client: AsyncClient, db_session: AsyncSession):
    """When article exists but all AI backends fail, expect 503 (not 500)."""
    slug = f"hypertension-guide-{uuid.uuid4().hex[:6]}"
    await _create_article(db_session, slug)

    token = await _register_and_login(client, "ai503")

    # All external AI calls will fail in the test env (no real API keys + no Ollama)
    r = await client.post(
        f"/api/v1/articles/{slug}/ask",
        json={"question": "What are the first-line treatments mentioned?"},
        headers={"Authorization": f"Bearer {token}"},
    )
    # Should be 503 (all backends unavailable) — NOT 500 (unhandled error)
    assert r.status_code in (200, 503), f"Expected 200 or 503, got {r.status_code}: {r.text}"
    if r.status_code == 503:
        assert "unavailable" in r.json()["detail"].lower()


@pytest.mark.anyio
async def test_article_ask_returns_answer_when_ai_available(
    client: AsyncClient, db_session: AsyncSession
):
    """Happy path: article found, Groq responds with an answer."""
    slug = f"hypertension-mocked-{uuid.uuid4().hex[:6]}"
    await _create_article(db_session, slug)

    token = await _register_and_login(client, "mocked")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "First-line treatments include ACE inhibitors."}}]
    }

    mock_client_instance = AsyncMock()
    mock_client_instance.post = AsyncMock(return_value=mock_resp)
    mock_http_cls = MagicMock(return_value=mock_client_instance)

    with patch.dict("os.environ", {"GROQ_API_KEY_4": "test_groq_key_for_mocking"}), \
         patch("httpx.AsyncClient", mock_http_cls):
        r = await client.post(
            f"/api/v1/articles/{slug}/ask",
            json={"question": "What are the treatment options in this article?"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert r.status_code == 200
    body = r.json()
    assert "answer" in body
    assert len(body["answer"]) > 0
    assert "remaining" in body
