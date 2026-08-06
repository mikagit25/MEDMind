"""Locale L5 — Local reviewer gate: access control and submission logic.

Verifies:
- Reviewer model: jurisdictions, license_country, license_number fields persist
- QuestionReview model: L5 rubric fields (locally_correct, scope_ok, etc.) persist
- GET /reviewer/queue/jurisdiction — requires auth, admin can access
- POST /reviewer/submit-jurisdiction/{id} — requires auth, 404 on unknown
- Submission: locally_correct=yes + scope_ok=yes → jurisdiction_verified_for set, action_taken=released_from_quarantine
- Submission: locally_correct=no → question status=retired, action_taken=retired
"""
from __future__ import annotations

import uuid
import pytest
from sqlalchemy import select

from app.models.models import Reviewer, QuestionReview, MCQQuestion, Module


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _seed_mcq(db, exam_slug: str = "snle", sensitive: bool = True) -> MCQQuestion:
    mod = Module(
        id=uuid.uuid4(),
        title=f"L5 Module {uuid.uuid4().hex[:4]}",
        specialty_id=None,
        code=f"L5-{uuid.uuid4().hex[:6]}",
        module_type="specialty_module",
        is_published=False,
    )
    db.add(mod)
    await db.flush()

    q = MCQQuestion(
        id=uuid.uuid4(),
        module_id=mod.id,
        question="Patient requires IV medication administration per local nursing protocol.",
        options={"A": "Proceed", "B": "Refuse", "C": "Consult physician", "D": "Document only"},
        correct="A",
        explanation="Per SCFHS guidelines, RNs may administer IV medications with a valid order.",
        status="active",
        exam_slugs=[exam_slug],
        nclex_client_needs="safe_effective_care",
        question_type="mcq",
        difficulty="medium",
        origin="gulf_native",
        jurisdiction_sensitive=sensitive,
        jurisdiction_verified_for=None,
    )
    db.add(q)
    await db.commit()
    return q


def _make_reviewer(slug_suffix: str = None, **kw) -> Reviewer:
    suffix = slug_suffix or uuid.uuid4().hex[:6]
    defaults = dict(
        id=uuid.uuid4(),
        slug=f"reviewer_{suffix}",
        name=f"Test Reviewer {suffix}",
        credentials="RN, BSN",
        is_active=True,
        jurisdictions=["sa"],
        license_country="Saudi Arabia",
        license_number="SCFHS-12345",
    )
    defaults.update(kw)
    return Reviewer(**defaults)


# ── Unit: Reviewer model jurisdiction fields ──────────────────────────────────

@pytest.mark.asyncio
async def test_reviewer_jurisdictions_field_persists(db_session, client):
    rev = _make_reviewer(jurisdictions=["sa", "ae_dubai"])
    db_session.add(rev)
    await db_session.commit()

    result = await db_session.execute(
        select(Reviewer).where(Reviewer.id == rev.id)
    )
    fetched = result.scalar_one_or_none()
    assert fetched is not None
    assert fetched.jurisdictions == ["sa", "ae_dubai"]


@pytest.mark.asyncio
async def test_reviewer_license_fields_persist(db_session, client):
    rev = _make_reviewer()
    db_session.add(rev)
    await db_session.commit()

    result = await db_session.execute(
        select(Reviewer).where(Reviewer.id == rev.id)
    )
    fetched = result.scalar_one_or_none()
    assert fetched.license_country == "Saudi Arabia"
    assert fetched.license_number == "SCFHS-12345"


@pytest.mark.asyncio
async def test_reviewer_jurisdictions_multiple(db_session, client):
    rev = _make_reviewer(jurisdictions=["sa", "ae_dubai", "qa"])
    db_session.add(rev)
    await db_session.commit()

    result = await db_session.execute(
        select(Reviewer).where(Reviewer.id == rev.id)
    )
    fetched = result.scalar_one_or_none()
    assert len(fetched.jurisdictions) == 3
    assert "qa" in fetched.jurisdictions


@pytest.mark.asyncio
async def test_reviewer_single_jurisdiction(db_session, client):
    rev = _make_reviewer(jurisdictions=["om"])
    db_session.add(rev)
    await db_session.commit()

    result = await db_session.execute(
        select(Reviewer).where(Reviewer.id == rev.id)
    )
    fetched = result.scalar_one_or_none()
    assert fetched.jurisdictions == ["om"]


# ── Unit: QuestionReview L5 rubric fields ─────────────────────────────────────

@pytest.mark.asyncio
async def test_question_review_l5_approved_fields_persist(db_session, client):
    q = await _seed_mcq(db_session)

    review = QuestionReview(
        id=uuid.uuid4(),
        question_id=q.id,
        reviewer_user_id=None,
        realism=4,
        clinical_accuracy=4,
        key_correct=4,
        rationale_quality=4,
        distractors_plausible=4,
        language_clarity=4,
        category_correct=4,
        decision="approve",
        locally_correct="yes",
        scope_ok="yes",
        culturally_appropriate="yes",
        local_note="Confirmed per SCFHS 2024 Nursing Competency Framework.",
        jurisdiction_slug="sa",
    )
    db_session.add(review)
    await db_session.commit()

    result = await db_session.execute(
        select(QuestionReview).where(QuestionReview.id == review.id)
    )
    fetched = result.scalar_one_or_none()
    assert fetched is not None
    assert fetched.locally_correct == "yes"
    assert fetched.scope_ok == "yes"
    assert fetched.culturally_appropriate == "yes"
    assert fetched.jurisdiction_slug == "sa"
    assert "SCFHS" in fetched.local_note


@pytest.mark.asyncio
async def test_question_review_l5_rejected_fields_persist(db_session, client):
    q = await _seed_mcq(db_session)

    review = QuestionReview(
        id=uuid.uuid4(),
        question_id=q.id,
        reviewer_user_id=None,
        realism=2,
        clinical_accuracy=2,
        key_correct=2,
        rationale_quality=2,
        distractors_plausible=2,
        language_clarity=2,
        category_correct=2,
        decision="reject",
        locally_correct="no",
        scope_ok="no",
        culturally_appropriate="needs_edit",
        jurisdiction_slug="sa",
    )
    db_session.add(review)
    await db_session.commit()

    result = await db_session.execute(
        select(QuestionReview).where(QuestionReview.id == review.id)
    )
    fetched = result.scalar_one_or_none()
    assert fetched.locally_correct == "no"
    assert fetched.scope_ok == "no"
    assert fetched.culturally_appropriate == "needs_edit"


@pytest.mark.asyncio
async def test_question_review_jurisdiction_slug_persists(db_session, client):
    q = await _seed_mcq(db_session, exam_slug="dha")

    review = QuestionReview(
        id=uuid.uuid4(),
        question_id=q.id,
        reviewer_user_id=None,
        realism=3, clinical_accuracy=3, key_correct=3,
        rationale_quality=3, distractors_plausible=3,
        language_clarity=3, category_correct=3,
        decision="approve",
        locally_correct="yes",
        scope_ok="yes",
        culturally_appropriate="yes",
        jurisdiction_slug="ae_dubai",
    )
    db_session.add(review)
    await db_session.commit()

    result = await db_session.execute(
        select(QuestionReview).where(QuestionReview.id == review.id)
    )
    fetched = result.scalar_one_or_none()
    assert fetched.jurisdiction_slug == "ae_dubai"


# ── API: auth guards ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_jurisdiction_queue_requires_auth(client):
    r = await client.get("/api/v1/reviewer/queue/jurisdiction?jurisdiction=sa")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_submit_jurisdiction_requires_auth(client):
    fake_id = str(uuid.uuid4())
    r = await client.post(
        f"/api/v1/reviewer/submit-jurisdiction/{fake_id}",
        json={
            "locally_correct": "yes",
            "scope_ok": "yes",
            "culturally_appropriate": "yes",
            "jurisdiction_slug": "sa",
        },
    )
    assert r.status_code in (401, 403)


# ── API: admin can access jurisdiction queue ──────────────────────────────────

@pytest.mark.asyncio
async def test_jurisdiction_queue_admin_returns_200(admin_client):
    r = await admin_client.get("/api/v1/reviewer/queue/jurisdiction?jurisdiction=sa")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_jurisdiction_queue_response_structure(admin_client):
    r = await admin_client.get("/api/v1/reviewer/queue/jurisdiction?jurisdiction=sa")
    assert r.status_code == 200
    data = r.json()
    # Response: {"questions": [...], "total": ..., "authorized_jurisdictions": [...]}
    assert "questions" in data
    assert "total" in data
    assert "authorized_jurisdictions" in data
    assert isinstance(data["questions"], list)


@pytest.mark.asyncio
async def test_jurisdiction_queue_total_is_int(admin_client):
    r = await admin_client.get("/api/v1/reviewer/queue/jurisdiction?jurisdiction=ae_dubai")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data["total"], int)


# ── API: submit jurisdiction — validation ─────────────────────────────────────

@pytest.mark.asyncio
async def test_submit_jurisdiction_404_unknown_question(admin_client):
    fake_id = str(uuid.uuid4())
    r = await admin_client.post(
        f"/api/v1/reviewer/submit-jurisdiction/{fake_id}",
        json={
            "locally_correct": "yes",
            "scope_ok": "yes",
            "culturally_appropriate": "yes",
            "jurisdiction_slug": "sa",
        },
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_submit_jurisdiction_invalid_locally_correct_value(admin_client, db_session):
    """Body validation: locally_correct must be yes|no|uncertain."""
    q = await _seed_mcq(db_session)
    r = await admin_client.post(
        f"/api/v1/reviewer/submit-jurisdiction/{q.id}",
        json={
            "locally_correct": "maybe",  # invalid per pattern ^(yes|no|uncertain)$
            "scope_ok": "yes",
            "culturally_appropriate": "yes",
            "jurisdiction_slug": "sa",
        },
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_submit_jurisdiction_invalid_scope_ok_value(admin_client, db_session):
    """Body validation: scope_ok must be yes|no."""
    q = await _seed_mcq(db_session)
    r = await admin_client.post(
        f"/api/v1/reviewer/submit-jurisdiction/{q.id}",
        json={
            "locally_correct": "yes",
            "scope_ok": "maybe",  # invalid
            "culturally_appropriate": "yes",
            "jurisdiction_slug": "sa",
        },
    )
    assert r.status_code == 422


# ── API: submit locally_correct=yes exits quarantine ─────────────────────────

@pytest.mark.asyncio
async def test_submit_jurisdiction_yes_action_released(admin_client, db_session):
    q = await _seed_mcq(db_session, exam_slug="snle", sensitive=True)

    r = await admin_client.post(
        f"/api/v1/reviewer/submit-jurisdiction/{q.id}",
        json={
            "locally_correct": "yes",
            "scope_ok": "yes",
            "culturally_appropriate": "yes",
            "jurisdiction_slug": "sa",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("action_taken") == "released_from_quarantine"


@pytest.mark.asyncio
async def test_submit_jurisdiction_yes_sets_verified_for(admin_client, db_session):
    q = await _seed_mcq(db_session, exam_slug="snle", sensitive=True)

    await admin_client.post(
        f"/api/v1/reviewer/submit-jurisdiction/{q.id}",
        json={
            "locally_correct": "yes",
            "scope_ok": "yes",
            "culturally_appropriate": "yes",
            "jurisdiction_slug": "sa",
        },
    )

    await db_session.refresh(q)
    assert q.jurisdiction_verified_for is not None
    assert "sa" in q.jurisdiction_verified_for


# ── API: submit locally_correct=no retires question ──────────────────────────

@pytest.mark.asyncio
async def test_submit_jurisdiction_no_action_retired(admin_client, db_session):
    q = await _seed_mcq(db_session, exam_slug="snle", sensitive=True)

    r = await admin_client.post(
        f"/api/v1/reviewer/submit-jurisdiction/{q.id}",
        json={
            "locally_correct": "no",
            "scope_ok": "no",
            "culturally_appropriate": "yes",
            "jurisdiction_slug": "sa",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("action_taken") == "retired"


@pytest.mark.asyncio
async def test_submit_jurisdiction_no_sets_retired_status(admin_client, db_session):
    q = await _seed_mcq(db_session, exam_slug="snle", sensitive=True)

    await admin_client.post(
        f"/api/v1/reviewer/submit-jurisdiction/{q.id}",
        json={
            "locally_correct": "no",
            "scope_ok": "no",
            "culturally_appropriate": "yes",
            "jurisdiction_slug": "sa",
        },
    )

    await db_session.refresh(q)
    assert q.status == "retired"
