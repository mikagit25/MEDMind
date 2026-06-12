"""V4 Phase 2 — Translation QA Pipeline tests.

Tests:
  1. Number/unit corruption → failed
  2. Negation loss → failed
  3. Glossary mismatch (>30% threshold) → failed
  4. Clean translation → passed
  5. Public article fallback when translation QA is failed
  6. Glossary loading
"""
from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Article, ArticleTranslation
from app.services.content_verifier import (
    _check_numbers,
    _check_glossary_terms,
    _load_glossary,
    check_translation_quality,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_article(db: AsyncSession, **kwargs) -> Article:
    defaults = dict(
        id=uuid.uuid4(),
        slug=f"test-{uuid.uuid4().hex[:8]}",
        title="Beta-blocker Use in Heart Failure",
        excerpt="Beta-blockers reduce mortality in heart failure by 34%.",
        body=[{"type": "p", "content": "Beta-blockers reduce mortality in heart failure by 34% according to a randomized controlled trial."}],
        category="cardiology",
        verification_status="passed",
        is_published=True,
        review_status="published",
    )
    defaults.update(kwargs)
    article = Article(**defaults)
    db.add(article)
    return article


def _make_translation(db: AsyncSession, article: Article, locale: str = "ru", **kwargs) -> ArticleTranslation:
    defaults = dict(
        article_id=article.id,
        locale=locale,
        title="Бета-адреноблокаторы при сердечной недостаточности",
        excerpt="Бета-адреноблокаторы снижают смертность при сердечной недостаточности на 34%.",
        body=[{"type": "p", "content": "Бета-адреноблокаторы снижают смертность при сердечной недостаточности на 34%."}],
        status="done",
        translation_verification_status="passed",
    )
    defaults.update(kwargs)
    tr = ArticleTranslation(**defaults)
    db.add(tr)
    return tr


# ── Unit: _check_numbers ──────────────────────────────────────────────────────

class TestCheckNumbers:
    def test_no_numbers_no_issues(self):
        assert _check_numbers("hypertension treatment", "лечение гипертензии") == []

    def test_matching_number_no_issue(self):
        assert _check_numbers("dose 500mg", "доза 500мг") == []

    def test_matching_number_exact(self):
        issues = _check_numbers("administer 10mg warfarin", "дать 10mg варфарин")
        assert issues == []

    def test_missing_number_flagged(self):
        issues = _check_numbers("mortality reduced by 34%", "смертность снизилась")
        assert len(issues) == 1
        assert issues[0]["issue"] == "missing_in_translation"
        assert "34%" in issues[0]["token"]

    def test_multiple_numbers_one_missing(self):
        original = "give 500mg twice daily for 7 days"
        translated = "давать 500мг дважды в день"
        issues = _check_numbers(original, translated)
        # 7 days is missing
        tokens = [i["token"] for i in issues]
        assert any("7" in t for t in tokens)


# ── Unit: _check_glossary_terms ───────────────────────────────────────────────

class TestCheckGlossaryTerms:
    def test_glossary_loads(self):
        glossary = _load_glossary("ru")
        assert isinstance(glossary, dict)
        assert len(glossary) > 100

    def test_glossary_en_loads(self):
        glossary = _load_glossary("en")
        assert "hypertension" in glossary

    def test_glossary_unknown_lang_returns_empty(self):
        glossary = _load_glossary("xx_nonexistent")
        assert glossary == {}

    def test_correct_glossary_term_no_issue(self):
        issues = _check_glossary_terms(
            "treatment of hypertension",
            "лечение артериальной гипертензии",
            "ru",
        )
        assert issues == []

    def test_wrong_glossary_term_detected(self):
        # Using wrong translation for hypertension
        issues = _check_glossary_terms(
            "hypertension management guidelines",
            "управление высоким давлением руководящие принципы",
            "ru",
        )
        hyp_issues = [i for i in issues if "hypertension" in i.get("term", "").lower()]
        assert len(hyp_issues) > 0

    def test_term_not_in_original_not_checked(self):
        # No hypertension in original — should not raise issue
        issues = _check_glossary_terms(
            "common cold treatment",
            "лечение простуды",
            "ru",
        )
        assert issues == []


# ── Unit: check_translation_quality ──────────────────────────────────────────

class TestTranslationQuality:
    @pytest.mark.asyncio
    async def test_number_corruption_fails(self):
        """A translation that drops a dosage number should fail."""
        original = "Administer 500mg aspirin daily to prevent cardiovascular events."
        translated = "Давать аспирин ежедневно для предотвращения сердечно-сосудистых событий."

        with patch(
            "app.services.content_verifier._check_negation_preserved",
            new_callable=AsyncMock,
            return_value={"preserved": True, "note": "no negations"},
        ):
            result = await check_translation_quality(original, translated, "ru")

        assert result["status"] == "failed"
        assert "number_corruption" in result["failures"]
        assert len(result["report"]["numbers"]) > 0

    @pytest.mark.asyncio
    async def test_negation_loss_fails(self):
        """A translation that loses negation should fail."""
        original = "Do not administer this drug to patients with renal failure."
        translated = "Давать этот препарат пациентам с почечной недостаточностью."

        with patch(
            "app.services.content_verifier._check_negation_preserved",
            new_callable=AsyncMock,
            return_value={"preserved": False, "note": "negation 'do not' was lost"},
        ):
            result = await check_translation_quality(original, translated, "ru")

        assert result["status"] == "failed"
        assert "negation_lost" in result["failures"]

    @pytest.mark.asyncio
    async def test_clean_translation_passes(self):
        """A good translation should pass."""
        original = "Beta-blockers reduce mortality in heart failure by 34%."
        translated = "Бета-адреноблокаторы снижают смертность при сердечной недостаточности на 34%."

        with patch(
            "app.services.content_verifier._check_negation_preserved",
            new_callable=AsyncMock,
            return_value={"preserved": True, "note": "no negations"},
        ):
            result = await check_translation_quality(original, translated, "ru")

        assert result["status"] == "passed"
        assert result["failures"] == []
        assert "numbers" in result["report"]
        assert "glossary" in result["report"]

    @pytest.mark.asyncio
    async def test_result_has_required_keys(self):
        """Result always has status, failures, report, checked_at."""
        with patch(
            "app.services.content_verifier._check_negation_preserved",
            new_callable=AsyncMock,
            return_value={"preserved": True, "note": "ok"},
        ):
            result = await check_translation_quality("test", "тест", "ru")

        assert "status" in result
        assert "failures" in result
        assert "report" in result
        assert "checked_at" in result


# ── Integration: fallback to English on failed translation ────────────────────

@pytest.mark.asyncio
async def test_failed_translation_serves_english(client: AsyncClient, db_session: AsyncSession):
    """When translation_verification_status=failed, the English version is served."""
    article = _make_article(db_session)
    _make_translation(db_session, article, locale="ru", translation_verification_status="failed")
    await db_session.commit()

    resp = await client.get(f"/api/v1/articles/{article.slug}?locale=ru")
    assert resp.status_code == 200
    data = resp.json()
    # Should serve English title (not Russian)
    assert data["title"] == article.title
    # Should indicate translation is under review
    assert data.get("translation_under_review") is True


@pytest.mark.asyncio
async def test_passed_translation_serves_translation(client: AsyncClient, db_session: AsyncSession):
    """When translation_verification_status=passed, the translated version is served."""
    article = _make_article(db_session)
    tr = _make_translation(db_session, article, locale="ru", translation_verification_status="passed")
    await db_session.commit()

    resp = await client.get(f"/api/v1/articles/{article.slug}?locale=ru")
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == tr.title
    assert data.get("is_translated") is True
    assert data.get("translation_under_review") is None


@pytest.mark.asyncio
async def test_pending_translation_serves_translation(client: AsyncClient, db_session: AsyncSession):
    """When translation_verification_status=pending, translation is still served (not blocked)."""
    article = _make_article(db_session)
    tr = _make_translation(db_session, article, locale="de", translation_verification_status="pending")
    await db_session.commit()

    resp = await client.get(f"/api/v1/articles/{article.slug}?locale=de")
    assert resp.status_code == 200
    data = resp.json()
    # pending translations are served (only failed are blocked)
    assert data["title"] == tr.title
    assert data.get("is_translated") is True
