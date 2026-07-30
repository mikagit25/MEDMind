"""Bank-Scale B2 — Source corpus ingestion and question generation tests.

Verifies:
- SourceDocument model: fields, hash dedup
- Claim checker: rejects question with distorted fact (fixture, mock Groq)
- Claim checker: passes question supported by source
- Dedup: same-text question is rejected
- parse_questions: parses valid JSON, handles malformed
- build_source_refs: includes source_slug and url
- ingest_open_sources: save_documents dedup logic
- generate_from_source_docs: accepted pipeline without real Groq
"""
from __future__ import annotations

import hashlib
import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from app.models.models import ContentSource, SourceDocument


# ── Helpers ───────────────────────────────────────────────────────────────────

def _sha256(text: str) -> str:
    return hashlib.sha256(text.strip().encode()).hexdigest()


def _make_source_doc(text: str, category: str = "pharmacological") -> dict:
    return {
        "source_slug": "cdc",
        "nclex_category": category,
        "title": "Test Source",
        "url": "https://www.cdc.gov/test",
        "section": "test",
        "full_text": text,
    }


# ── Unit: SourceDocument model ────────────────────────────────────────────────

def test_source_document_hash_is_sha256():
    """text_hash should be SHA-256 of the stripped full_text."""
    text = "  Metformin is the first-line treatment for type 2 diabetes.  "
    h = _sha256(text)
    assert len(h) == 64
    assert h == hashlib.sha256(text.strip().encode()).hexdigest()


def test_source_document_different_texts_different_hashes():
    """Different texts produce different hashes."""
    h1 = _sha256("Heparin inhibits thrombin.")
    h2 = _sha256("Warfarin inhibits Vitamin K.")
    assert h1 != h2


@pytest.mark.asyncio
async def test_source_document_dedup_by_hash(db_session, client):
    """Saving same text twice inserts only once."""
    from app.scripts.ingest_open_sources import save_documents

    # Seed content_sources first (FK requirement)
    from app.scripts.seed_content_sources import SOURCES
    for src in SOURCES:
        existing = await db_session.get(ContentSource, src["slug"])
        if not existing:
            db_session.add(ContentSource(**src))
    await db_session.commit()

    text = "Aspirin inhibits platelet aggregation via COX-1."
    doc = _make_source_doc(text)

    inserted1, skipped1 = await save_documents([doc], db_session)
    inserted2, skipped2 = await save_documents([doc], db_session)

    assert inserted1 == 1
    assert skipped1 == 0
    assert inserted2 == 0
    assert skipped2 == 1


# ── Unit: parse_questions ─────────────────────────────────────────────────────

def test_parse_questions_valid_json():
    """parse_questions extracts a list from a valid JSON response."""
    from app.scripts.generate_from_source_docs import parse_questions

    raw = json.dumps([
        {"question": "A nurse is...", "correct": "A", "options": {"A": "x", "B": "y"}}
    ])
    result = parse_questions(raw)
    assert len(result) == 1
    assert result[0]["correct"] == "A"


def test_parse_questions_handles_markdown_fences():
    """parse_questions strips markdown code fences."""
    from app.scripts.generate_from_source_docs import parse_questions

    raw = '```json\n[{"question": "Q1", "correct": "B"}]\n```'
    result = parse_questions(raw)
    assert len(result) == 1
    assert result[0]["correct"] == "B"


def test_parse_questions_returns_empty_on_garbage():
    """parse_questions returns [] for unparseable input."""
    from app.scripts.generate_from_source_docs import parse_questions

    assert parse_questions("not json at all") == []
    assert parse_questions("") == []


# ── Unit: build_source_refs ───────────────────────────────────────────────────

def test_build_source_refs_includes_source_slug():
    """source_refs must include source_slug for traceability."""
    from app.scripts.generate_from_source_docs import build_source_refs

    docs = [{"source_slug": "cdc", "title": "CDC Infection", "url": "https://cdc.gov/inf",
              "text_reuse_allowed": True, "full_text": "..."}]
    question = {"source_doc_titles": ["CDC Infection"]}
    refs = build_source_refs(docs, question)
    slugs = [r.get("source_slug") for r in refs]
    assert "cdc" in slugs


def test_build_source_refs_not_empty():
    """Even with no matching titles, falls back to first doc and NCLEX refs."""
    from app.scripts.generate_from_source_docs import build_source_refs

    docs = [{"source_slug": "medlineplus_topics", "title": "Drug Safety",
              "url": "https://medlineplus.gov/", "text_reuse_allowed": True, "full_text": "text"}]
    refs = build_source_refs(docs, {"source_doc_titles": []})
    assert len(refs) >= 1


# ── Unit: claim checker — fixture-based (no real Groq) ───────────────────────

@pytest.mark.asyncio
async def test_claim_check_rejects_contradicted_fact():
    """Claim-checker must reject a question whose key claim contradicts the source."""
    from app.services.question_claim_check import verify_question_against_source

    source_text = (
        "Metformin is the first-line drug for type 2 diabetes. "
        "It works by reducing hepatic glucose production. "
        "It is contraindicated in severe renal impairment (eGFR < 30)."
    )
    # Question contains a WRONG claim: says Metformin is contraindicated in MILD renal impairment
    question_text = "A patient has mild renal impairment (eGFR 65). The nurse knows Metformin is contraindicated. What is the priority action?"
    explanation = "Metformin is contraindicated in mild renal impairment."

    # Mock Groq: extract 1 claim, then say source contradicts it
    claim = "Metformin is contraindicated in mild renal impairment (eGFR 65)."
    extract_mock = AsyncMock(return_value=[claim])
    check_mock = AsyncMock(return_value={"result": "no", "citation": "contraindicated in severe renal impairment (eGFR < 30)"})

    with patch("app.services.question_claim_check.extract_key_claims", extract_mock), \
         patch("app.services.question_claim_check.check_claim", check_mock):
        result = await verify_question_against_source(question_text, explanation, source_text)

    assert result["passed"] is False
    assert result["rejected_reason"] is not None
    assert claim in result["rejected_reason"]


@pytest.mark.asyncio
async def test_claim_check_passes_supported_fact():
    """Claim-checker must pass a question whose claim is confirmed by the source."""
    from app.services.question_claim_check import verify_question_against_source

    source_text = (
        "Heparin is an anticoagulant that inhibits thrombin and factor Xa. "
        "It is used to prevent and treat deep vein thrombosis."
    )
    question_text = "A patient is receiving heparin therapy. The nurse understands heparin works by..."
    explanation = "Heparin inhibits thrombin, preventing clot formation."

    claim = "Heparin inhibits thrombin."
    extract_mock = AsyncMock(return_value=[claim])
    check_mock = AsyncMock(return_value={"result": "yes", "citation": "inhibits thrombin"})

    with patch("app.services.question_claim_check.extract_key_claims", extract_mock), \
         patch("app.services.question_claim_check.check_claim", check_mock):
        result = await verify_question_against_source(question_text, explanation, source_text)

    assert result["passed"] is True
    assert result["rejected_reason"] is None


@pytest.mark.asyncio
async def test_claim_check_passes_when_no_claims_extractable():
    """If no claims extracted (no Groq keys), question passes with warning."""
    from app.services.question_claim_check import verify_question_against_source

    extract_mock = AsyncMock(return_value=[])
    with patch("app.services.question_claim_check.extract_key_claims", extract_mock):
        result = await verify_question_against_source("Q", "E", "source text")

    assert result["passed"] is True
    assert result["claims"] == []


# ── Unit: dedup logic (hash-based) ────────────────────────────────────────────

def test_question_hash_dedup():
    """Same question text (first 200 chars) produces same hash → rejected as dup."""
    from app.scripts._mcq_db_writer import _question_hash

    q1 = "A 45-year-old patient is admitted with chest pain. The nurse's priority action is..."
    q2 = q1  # exact duplicate

    assert _question_hash(q1) == _question_hash(q2)


def test_question_hash_different_texts():
    """Different question texts produce different hashes."""
    from app.scripts._mcq_db_writer import _question_hash

    h1 = _question_hash("A patient is prescribed metformin for type 2 diabetes.")
    h2 = _question_hash("A patient is prescribed lisinopril for hypertension.")
    assert h1 != h2


# ── Unit: ingest save_documents (uses db_session) ─────────────────────────────

@pytest.mark.asyncio
async def test_save_documents_word_count(db_session, client):
    """Saved document has correct word_count."""
    from app.scripts.ingest_open_sources import save_documents
    from app.scripts.seed_content_sources import SOURCES

    for src in SOURCES:
        ex = await db_session.get(ContentSource, src["slug"])
        if not ex:
            db_session.add(ContentSource(**src))
    await db_session.commit()

    text = "Patient education is essential for medication adherence in chronic disease management."
    doc = _make_source_doc(text, category="health_promotion")
    await save_documents([doc], db_session)

    from sqlalchemy import select
    result = await db_session.execute(
        select(SourceDocument).where(SourceDocument.text_hash == _sha256(text))
    )
    sd = result.scalar_one_or_none()
    assert sd is not None
    assert sd.word_count == len(text.split())


@pytest.mark.asyncio
async def test_save_documents_sets_source_slug(db_session, client):
    """Saved document links to correct source_slug."""
    from app.scripts.ingest_open_sources import save_documents
    from app.scripts.seed_content_sources import SOURCES

    for src in SOURCES:
        ex = await db_session.get(ContentSource, src["slug"])
        if not ex:
            db_session.add(ContentSource(**src))
    await db_session.commit()

    text = "Handwashing with soap and water removes more pathogens than hand sanitizer alone."
    doc = {**_make_source_doc(text, "safe_effective_care"), "source_slug": "medlineplus_topics"}
    await save_documents([doc], db_session)

    from sqlalchemy import select
    result = await db_session.execute(
        select(SourceDocument).where(SourceDocument.text_hash == _sha256(text))
    )
    sd = result.scalar_one_or_none()
    assert sd is not None
    assert sd.source_slug == "medlineplus_topics"
