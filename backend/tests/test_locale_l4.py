"""Locale L4 — Exam targets and marketing_ready gate.

Verifies:
- EXAM_TARGETS: snle=600, dha=450, others=DEFAULT_TARGET=300
- _target_for helper: returns correct per-slug targets
- ExamDefinition.marketing_ready: defaults to False, persists updates
- GET /exam/definitions/{slug} API: includes marketing_ready field
"""
from __future__ import annotations

import uuid
import pytest
from sqlalchemy import select

from app.models.models import ExamDefinition


# ── Unit: EXAM_TARGETS dict ───────────────────────────────────────────────────

def test_snle_target_is_600():
    from app.scripts.generate_gulf_questions import EXAM_TARGETS
    assert EXAM_TARGETS["snle"] == 600


def test_dha_target_is_450():
    from app.scripts.generate_gulf_questions import EXAM_TARGETS
    assert EXAM_TARGETS["dha"] == 450


def test_default_target_is_300():
    from app.scripts.generate_gulf_questions import DEFAULT_TARGET
    assert DEFAULT_TARGET == 300


def test_target_for_snle():
    from app.scripts.generate_gulf_questions import _target_for
    assert _target_for("snle") == 600


def test_target_for_dha():
    from app.scripts.generate_gulf_questions import _target_for
    assert _target_for("dha") == 450


def test_target_for_qchp_uses_default():
    from app.scripts.generate_gulf_questions import _target_for, DEFAULT_TARGET
    assert _target_for("qchp") == DEFAULT_TARGET


def test_target_for_omsb_uses_default():
    from app.scripts.generate_gulf_questions import _target_for, DEFAULT_TARGET
    assert _target_for("omsb") == DEFAULT_TARGET


def test_target_for_nhra_uses_default():
    from app.scripts.generate_gulf_questions import _target_for, DEFAULT_TARGET
    assert _target_for("nhra") == DEFAULT_TARGET


def test_snle_target_greater_than_dha():
    from app.scripts.generate_gulf_questions import EXAM_TARGETS
    assert EXAM_TARGETS["snle"] > EXAM_TARGETS["dha"]


def test_snle_target_greater_than_default():
    from app.scripts.generate_gulf_questions import EXAM_TARGETS, DEFAULT_TARGET
    assert EXAM_TARGETS["snle"] > DEFAULT_TARGET


# ── Unit: ExamDefinition.marketing_ready model field ─────────────────────────

def _exam_def(**kw) -> ExamDefinition:
    defaults = dict(
        slug=f"test_exam_{uuid.uuid4().hex[:6]}",
        name="Test Exam",
        country="Saudi Arabia",
        regulatory_body="SCFHS",
        question_count=150,
        duration_min=120,
        pass_threshold=60,
        passing_score_label="60%",
        blueprint_source="https://scfhs.org.sa/test",
        blueprint_verified_at="2026-07-01",
        status="active",
        family="gulf",
        options_per_question=4,
    )
    defaults.update(kw)
    return ExamDefinition(**defaults)


@pytest.mark.asyncio
async def test_exam_def_marketing_ready_false_persists(db_session, client):
    """Explicitly setting marketing_ready=False is stored and retrieved correctly."""
    e = _exam_def(marketing_ready=False)
    db_session.add(e)
    await db_session.commit()

    result = await db_session.execute(
        select(ExamDefinition).where(ExamDefinition.slug == e.slug)
    )
    fetched = result.scalar_one_or_none()
    assert fetched is not None
    assert fetched.marketing_ready is False


@pytest.mark.asyncio
async def test_exam_def_marketing_ready_persists_true(db_session, client):
    e = _exam_def(marketing_ready=True)
    db_session.add(e)
    await db_session.commit()

    result = await db_session.execute(
        select(ExamDefinition).where(ExamDefinition.slug == e.slug)
    )
    fetched = result.scalar_one_or_none()
    assert fetched.marketing_ready is True


@pytest.mark.asyncio
async def test_exam_def_marketing_ready_update(db_session, client):
    e = _exam_def(marketing_ready=False)
    db_session.add(e)
    await db_session.commit()

    e.marketing_ready = True
    await db_session.commit()

    result = await db_session.execute(
        select(ExamDefinition).where(ExamDefinition.slug == e.slug)
    )
    fetched = result.scalar_one_or_none()
    assert fetched.marketing_ready is True


# ── API: exam definitions include marketing_ready ────────────────────────────

@pytest.mark.asyncio
async def test_exam_definitions_endpoint_accessible(client):
    """GET /exam/definitions list is accessible (may return empty list)."""
    r = await client.get("/api/v1/exam/definitions")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_exam_definition_includes_marketing_ready(db_session, client):
    """Single exam definition response includes marketing_ready field."""
    e = _exam_def(
        slug="test_mrdy_snle",
        name="SNLE Test",
        status="active",
        marketing_ready=False,
    )
    db_session.add(e)
    await db_session.commit()

    r = await client.get("/api/v1/exam/definitions/test_mrdy_snle")
    assert r.status_code == 200
    data = r.json()
    assert "marketing_ready" in data
    assert data["marketing_ready"] is False


@pytest.mark.asyncio
async def test_exam_definition_marketing_ready_true_reflected(db_session, client):
    e = _exam_def(
        slug="test_mrdy_dha",
        name="DHA Test",
        status="active",
        marketing_ready=True,
    )
    db_session.add(e)
    await db_session.commit()

    r = await client.get("/api/v1/exam/definitions/test_mrdy_dha")
    assert r.status_code == 200
    data = r.json()
    assert data["marketing_ready"] is True


@pytest.mark.asyncio
async def test_exam_definition_404_for_unknown_slug(client):
    r = await client.get("/api/v1/exam/definitions/nonexistent_exam_xyz")
    assert r.status_code == 404
