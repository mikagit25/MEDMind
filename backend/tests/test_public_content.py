"""Tests for /api/v1/public/* endpoints (Phase 3)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


# ── _slugify ──────────────────────────────────────────────────────────────────

def test_slugify_basic():
    from app.api.v1.routes.public_content import _slugify
    assert _slugify("Atrial Fibrillation") == "atrial-fibrillation"


def test_slugify_special_chars():
    from app.api.v1.routes.public_content import _slugify
    # β is stripped (non-ASCII), leaving blocker-cardio with a leading dash stripped
    result = _slugify("β-Blocker (Cardio)")
    assert "blocker" in result and "cardio" in result


def test_slugify_extra_dashes():
    from app.api.v1.routes.public_content import _slugify
    assert _slugify("ACE  Inhibitor") == "ace-inhibitor"


def test_slugify_lowercase():
    from app.api.v1.routes.public_content import _slugify
    assert _slugify("Hypertension") == "hypertension"


def test_slugify_already_slug():
    from app.api.v1.routes.public_content import _slugify
    assert _slugify("heart-failure") == "heart-failure"


# ── Rate limiting ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rate_limit_increments_counter():
    """Rate limiter should call redis INCR and set TTL on first call."""
    from app.api.v1.routes.public_content import check_public_rate_limit
    mock_request = MagicMock()
    mock_request.headers.get.return_value = "1.2.3.4"
    mock_redis = AsyncMock()
    mock_redis.incr.return_value = 1

    with patch("app.api.v1.routes.public_content.get_redis", return_value=mock_redis):
        await check_public_rate_limit(mock_request)

    mock_redis.incr.assert_called_once()
    mock_redis.expire.assert_called_once()


@pytest.mark.asyncio
async def test_rate_limit_blocks_at_121():
    """Should raise 429 when request count exceeds 120."""
    from fastapi import HTTPException
    from app.api.v1.routes.public_content import check_public_rate_limit
    mock_request = MagicMock()
    mock_request.headers.get.return_value = "1.2.3.4"
    mock_redis = AsyncMock()
    mock_redis.incr.return_value = 121  # Over limit

    with patch("app.api.v1.routes.public_content.get_redis", return_value=mock_redis):
        with pytest.raises(HTTPException) as exc_info:
            await check_public_rate_limit(mock_request)

    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_rate_limit_allows_at_120():
    """Should not raise at exactly 120 requests."""
    from app.api.v1.routes.public_content import check_public_rate_limit
    mock_request = MagicMock()
    mock_request.headers.get.return_value = "1.2.3.4"
    mock_redis = AsyncMock()
    mock_redis.incr.return_value = 120

    with patch("app.api.v1.routes.public_content.get_redis", return_value=mock_redis):
        await check_public_rate_limit(mock_request)  # Should not raise


# ── Cache helpers ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cache_miss_returns_none():
    from app.api.v1.routes.public_content import _cache_get
    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    with patch("app.api.v1.routes.public_content.get_redis", return_value=mock_redis):
        result = await _cache_get("missing-key")

    assert result is None


@pytest.mark.asyncio
async def test_cache_hit_returns_data():
    import json
    from app.api.v1.routes.public_content import _cache_get
    mock_redis = AsyncMock()
    mock_redis.get.return_value = json.dumps({"foo": "bar"})

    with patch("app.api.v1.routes.public_content.get_redis", return_value=mock_redis):
        result = await _cache_get("some-key")

    assert result == {"foo": "bar"}


@pytest.mark.asyncio
async def test_cache_set_uses_setex():
    import json
    from app.api.v1.routes.public_content import _cache_set
    mock_redis = AsyncMock()

    with patch("app.api.v1.routes.public_content.get_redis", return_value=mock_redis):
        await _cache_set("my-key", {"x": 1}, ttl=3600)

    mock_redis.setex.assert_called_once_with("my-key", 3600, json.dumps({"x": 1}))


# ── Glossary aggregation logic ────────────────────────────────────────────────

def test_glossary_deduplication():
    """Same term from two lessons should produce only one entry."""
    from app.api.v1.routes.public_content import _slugify

    seen: dict = {}
    rows = [
        ("Lesson 1", [{"term": "Angina", "simple_definition": "Chest pain due to low blood flow"}], "CARDIO-001", "Cardiology Basics"),
        ("Lesson 2", [{"term": "Angina", "simple_definition": "Pain from heart ischemia"}], "CARDIO-002", "Advanced Cardiology"),
    ]
    for lesson_title, glossary, module_code, module_title in rows:
        for entry in glossary:
            slug = _slugify(entry["term"])
            if slug not in seen:
                seen[slug] = entry

    assert len(seen) == 1
    assert "angina" in seen


def test_glossary_letter_filter():
    from app.api.v1.routes.public_content import _slugify

    terms = [
        {"term": "Angina", "simple_definition": "..."},
        {"term": "Bradycardia", "simple_definition": "..."},
        {"term": "Arrhythmia", "simple_definition": "..."},
    ]
    letter = "A"
    filtered = [t for t in terms if t["term"].lower().startswith(letter.lower())]
    assert len(filtered) == 2
    assert all(t["term"].startswith("A") for t in filtered)


def test_glossary_search_filter():
    terms = [
        {"term": "Angina", "simple_definition": "Chest pain due to ischemia"},
        {"term": "Bradycardia", "simple_definition": "Slow heart rate"},
    ]
    search = "pain"
    filtered = [
        t for t in terms
        if search.lower() in t["term"].lower() or search.lower() in t["simple_definition"].lower()
    ]
    assert len(filtered) == 1
    assert filtered[0]["term"] == "Angina"


# ── Drug endpoint schemas ─────────────────────────────────────────────────────

def test_public_drug_schema_excludes_dosing():
    """PublicDrug schema must not have dosing or adverse_effects fields."""
    from app.api.v1.routes.public_content import PublicDrug
    fields = set(PublicDrug.model_fields.keys())
    assert "dosing" not in fields
    assert "adverse_effects" not in fields


def test_public_drug_schema_includes_disclaimer():
    from app.api.v1.routes.public_content import PublicDrug
    fields = set(PublicDrug.model_fields.keys())
    assert "disclaimer" in fields


def test_public_drug_has_required_educational_fields():
    from app.api.v1.routes.public_content import PublicDrug
    fields = set(PublicDrug.model_fields.keys())
    assert "mechanism" in fields
    assert "indications" in fields
    assert "contraindications" in fields
    assert "black_box_warning" in fields


# ── Topic detail schema ───────────────────────────────────────────────────────

def test_public_topic_detail_has_disclaimer():
    from app.api.v1.routes.public_content import PublicTopicDetail
    fields = set(PublicTopicDetail.model_fields.keys())
    assert "disclaimer" in fields


def test_public_topic_has_lessons():
    from app.api.v1.routes.public_content import PublicTopicDetail
    fields = set(PublicTopicDetail.model_fields.keys())
    assert "lessons" in fields
    assert "total_glossary_terms" in fields


# ── Response shapes ───────────────────────────────────────────────────────────

def test_glossary_list_response_shape():
    from app.api.v1.routes.public_content import PublicGlossaryList, PublicGlossaryTerm
    term = PublicGlossaryTerm(
        term="Hypertension",
        simple_definition="High blood pressure",
        slug="hypertension",
        lesson_title="Intro to Cardiology",
        module_code="CARDIO-001",
        module_title="Cardiology",
    )
    resp = PublicGlossaryList(terms=[term.model_dump()], total=1)
    assert resp.total == 1
    assert len(resp.terms) == 1


def test_public_topic_response_shape():
    from app.api.v1.routes.public_content import PublicTopic
    topic = PublicTopic(
        module_code="CARDIO-001",
        slug="cardio-001",
        title="Cardiology Basics",
        description="Introduction to cardiovascular medicine",
        lay_summary="Your heart pumps blood through your body...",
        lesson_count=5,
        specialty="Cardiology",
    )
    assert topic.slug == "cardio-001"
    assert topic.lesson_count == 5
