"""Locale L2 — Jurisdiction sensitivity audit and quarantine gate.

Verifies:
- MCQQuestion jurisdiction fields: jurisdiction_sensitive, jurisdiction_verified_for, origin
- Sensitivity classifier: _classify(text) triggers on US artifacts
- GET /admin/jurisdiction-audit — requires admin, returns audit structure
"""
from __future__ import annotations

import uuid
import pytest
from sqlalchemy import select

from app.models.models import MCQQuestion, Module


# ── Shared helper: create Module + MCQQuestion ────────────────────────────────

async def _seed_mcq(db, exam_slug: str = "snle", **kw) -> MCQQuestion:
    mod = Module(
        id=uuid.uuid4(),
        title=f"L2 Test Module {uuid.uuid4().hex[:4]}",
        specialty_id=None,
        code=f"L2-TST-{uuid.uuid4().hex[:6]}",
        module_type="specialty_module",
        is_published=False,
    )
    db.add(mod)
    await db.flush()

    defaults = dict(
        id=uuid.uuid4(),
        module_id=mod.id,
        question="A Gulf nurse must report medication errors per local policy.",
        options={"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"},
        correct="A",
        explanation="Rationale for correct option.",
        status="active",
        exam_slugs=[exam_slug],
        nclex_client_needs="safe_effective_care",
        question_type="mcq",
        difficulty="medium",
        origin="gulf_native",
        jurisdiction_sensitive=False,
        jurisdiction_verified_for=None,
    )
    defaults.update(kw)
    q = MCQQuestion(**defaults)
    db.add(q)
    await db.commit()
    return q


# ── Unit: model quarantine fields ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mcq_jurisdiction_sensitive_default_false(db_session, client):
    q = await _seed_mcq(db_session)

    result = await db_session.execute(
        select(MCQQuestion).where(MCQQuestion.id == q.id)
    )
    fetched = result.scalar_one_or_none()
    assert fetched is not None
    assert fetched.jurisdiction_sensitive is False
    assert fetched.jurisdiction_verified_for is None


@pytest.mark.asyncio
async def test_mcq_quarantined_question_persists(db_session, client):
    q = await _seed_mcq(db_session, jurisdiction_sensitive=True, jurisdiction_verified_for=None)

    result = await db_session.execute(
        select(MCQQuestion).where(MCQQuestion.id == q.id)
    )
    fetched = result.scalar_one_or_none()
    assert fetched.jurisdiction_sensitive is True
    assert fetched.jurisdiction_verified_for is None


@pytest.mark.asyncio
async def test_mcq_verified_exits_quarantine(db_session, client):
    q = await _seed_mcq(
        db_session,
        jurisdiction_sensitive=True,
        jurisdiction_verified_for=["sa"],
    )

    result = await db_session.execute(
        select(MCQQuestion).where(MCQQuestion.id == q.id)
    )
    fetched = result.scalar_one_or_none()
    assert fetched.jurisdiction_verified_for == ["sa"]


@pytest.mark.asyncio
async def test_mcq_origin_field_nclex_mapped(db_session, client):
    q = await _seed_mcq(db_session, origin="nclex_mapped")

    result = await db_session.execute(
        select(MCQQuestion).where(MCQQuestion.id == q.id)
    )
    fetched = result.scalar_one_or_none()
    assert fetched.origin == "nclex_mapped"


@pytest.mark.asyncio
async def test_mcq_origin_field_gulf_native(db_session, client):
    q = await _seed_mcq(db_session, origin="gulf_native")

    result = await db_session.execute(
        select(MCQQuestion).where(MCQQuestion.id == q.id)
    )
    fetched = result.scalar_one_or_none()
    assert fetched.origin == "gulf_native"


@pytest.mark.asyncio
async def test_mcq_audit_notes_persist(db_session, client):
    import json
    domains = ["us_911", "non_si_units"]
    q = await _seed_mcq(
        db_session,
        jurisdiction_sensitive=True,
        jurisdiction_audit_notes=json.dumps(domains),
    )

    result = await db_session.execute(
        select(MCQQuestion).where(MCQQuestion.id == q.id)
    )
    fetched = result.scalar_one_or_none()
    assert fetched.jurisdiction_audit_notes is not None
    assert "us_911" in fetched.jurisdiction_audit_notes


# ── Unit: sensitivity classifier ─────────────────────────────────────────────

def test_classifier_flags_911():
    from app.scripts.audit_jurisdiction_sensitivity import _classify
    # US_911_PATTERN uses \b911\b (no hyphens)
    _, domains = _classify("Call 911 for cardiac arrest.")
    assert len(domains) > 0


def test_classifier_flags_hipaa():
    from app.scripts.audit_jurisdiction_sensitivity import _classify
    _, domains = _classify("Per HIPAA, patient records must be protected.")
    assert len(domains) > 0


def test_classifier_flags_mg_dl():
    from app.scripts.audit_jurisdiction_sensitivity import _classify
    _, domains = _classify("Blood glucose is 200 mg/dL — what action?")
    assert len(domains) > 0
    assert "non_si_units" in domains


def test_classifier_no_flag_si_units():
    from app.scripts.audit_jurisdiction_sensitivity import _classify
    is_sensitive, domains = _classify("Blood glucose is 11.1 mmol/L — what action?")
    # mmol/L is SI — should NOT trigger non_si_units
    assert "non_si_units" not in domains


def test_classifier_returns_tuple():
    from app.scripts.audit_jurisdiction_sensitivity import _classify
    result = _classify("Standard nursing procedure.")
    assert isinstance(result, tuple)
    assert len(result) == 2
    is_sensitive, domains = result
    assert isinstance(is_sensitive, bool)
    assert isinstance(domains, list)


def test_classifier_clean_text_not_sensitive():
    from app.scripts.audit_jurisdiction_sensitivity import _classify
    # mmHg is in NON_SI pattern — use kPa or avoid units altogether
    is_sensitive, domains = _classify(
        "The nurse administers paracetamol 1g IV. Temperature 38.5°C. Oxygen saturation 98%."
    )
    assert not is_sensitive
    assert domains == []


def test_classifier_cdc_flags_us_agency():
    from app.scripts.audit_jurisdiction_sensitivity import _classify
    _, domains = _classify("CDC recommends updated immunisation schedule.")
    assert len(domains) > 0


def test_classifier_brand_drug_flags():
    from app.scripts.audit_jurisdiction_sensitivity import _classify
    _, domains = _classify("Administer Narcan 0.4mg IV for opioid reversal.")
    assert len(domains) > 0


# ── API: jurisdiction audit ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_jurisdiction_audit_requires_admin(client):
    r = await client.get("/api/v1/admin/jurisdiction-audit")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_jurisdiction_audit_returns_structure(admin_client):
    """Without exam_slug filter, the endpoint uses simple null checks (SQLite-safe)."""
    r = await admin_client.get("/api/v1/admin/jurisdiction-audit")
    assert r.status_code == 200
    data = r.json()
    assert "gulf_questions_total" in data
    assert "quarantined" in data
    assert "domain_breakdown" in data
    assert isinstance(data["domain_breakdown"], dict)


@pytest.mark.asyncio
async def test_jurisdiction_audit_counts_quarantined(admin_client, db_session):
    """Quarantined questions appear in the count."""
    await _seed_mcq(
        db_session,
        jurisdiction_sensitive=True,
        jurisdiction_verified_for=None,
    )

    r = await admin_client.get("/api/v1/admin/jurisdiction-audit")
    assert r.status_code == 200
    data = r.json()
    assert data["quarantined"] >= 1
