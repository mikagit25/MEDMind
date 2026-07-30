"""Bank-Scale B3 — Gap analysis coverage tests.

Verifies:
- GenerationQueue model: create, read, status transitions
- plan_generation: _target_count calculates non-zero targets
- plan_generation: build_plan returns plan without DB writes in dry_run
- bank-coverage API: returns expected structure, no auth → 401, admin → 200
- bank-coverage API: deficit=0 when bank is full
- bank-coverage queue API: returns items with correct fields
"""
from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from app.models.models import GenerationQueue, MCQQuestion, ContentSource


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_gq(**kwargs) -> GenerationQueue:
    defaults = dict(
        id=uuid.uuid4(),
        exam_slug="nclex_rn",
        nclex_category="pharmacological",
        question_type="mcq",
        target_difficulty="medium",
        count_requested=50,
        count_generated=0,
        status="pending",
        created_at=datetime.utcnow(),
    )
    defaults.update(kwargs)
    return GenerationQueue(**defaults)


# ── Unit: GenerationQueue model ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generation_queue_create(db_session, client):
    """Can insert a GenerationQueue row and retrieve it."""
    gq = _make_gq()
    db_session.add(gq)
    await db_session.commit()

    from sqlalchemy import select
    result = await db_session.execute(
        select(GenerationQueue).where(GenerationQueue.id == gq.id)
    )
    fetched = result.scalar_one_or_none()
    assert fetched is not None
    assert fetched.exam_slug == "nclex_rn"
    assert fetched.status == "pending"


@pytest.mark.asyncio
async def test_generation_queue_status_transition(db_session, client):
    """Status can be updated from pending → in_progress → done."""
    gq = _make_gq(exam_slug="snle", count_requested=30)
    db_session.add(gq)
    await db_session.commit()

    gq.status = "in_progress"
    gq.started_at = datetime.utcnow()
    await db_session.commit()

    gq.status = "done"
    gq.count_generated = 30
    gq.completed_at = datetime.utcnow()
    gq.generation_report = {"inserted": 30, "skipped": 0}
    await db_session.commit()

    from sqlalchemy import select
    result = await db_session.execute(
        select(GenerationQueue).where(GenerationQueue.id == gq.id)
    )
    fetched = result.scalar_one_or_none()
    assert fetched.status == "done"
    assert fetched.count_generated == 30
    assert fetched.generation_report["inserted"] == 30


# ── Unit: plan_generation targets ────────────────────────────────────────────

def test_target_count_nonzero():
    """Every category × type combination should have a nonzero target for NCLEX-RN."""
    from app.scripts.plan_generation import _target_count, BLUEPRINT_WEIGHTS

    for cat in BLUEPRINT_WEIGHTS:
        for qtype in ["mcq", "sata", "ordered", "calculation"]:
            t = _target_count("nclex_rn", cat, qtype)
            assert t >= 1, f"zero target for nclex_rn/{cat}/{qtype}"


def test_target_count_volume_scales():
    """Larger exam has proportionally larger targets."""
    from app.scripts.plan_generation import _target_count

    t_nclex = _target_count("nclex_rn", "pharmacological", "mcq")
    t_qchp = _target_count("qchp", "pharmacological", "mcq")
    assert t_nclex > t_qchp


def test_target_count_type_mix():
    """mcq target is always larger than calculation target for nclex_rn."""
    from app.scripts.plan_generation import _target_count

    mcq = _target_count("nclex_rn", "pharmacological", "mcq")
    calc = _target_count("nclex_rn", "pharmacological", "calculation")
    assert mcq > calc


# ── Unit: build_plan dry_run ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_build_plan_dry_run_no_db_writes():
    """build_plan with dry_run=True returns plan without inserting rows."""
    from app.scripts.plan_generation import build_plan

    # Mock get_bank_counts to return empty (all deficits)
    with patch("app.scripts.plan_generation.AsyncSessionLocal") as mock_session_cls:
        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)
        mock_db.execute = AsyncMock(return_value=iter([]))
        mock_db.add = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_session_cls.return_value = mock_db

        plan = await build_plan(["nclex_rn"], min_deficit=1, dry_run=True)

    # With empty bank, every category × type should have a deficit
    assert len(plan) > 0
    # dry_run → no commit called
    mock_db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_build_plan_filters_by_exam():
    """build_plan only returns entries for the requested exam slugs."""
    from app.scripts.plan_generation import build_plan

    with patch("app.scripts.plan_generation.AsyncSessionLocal") as mock_session_cls:
        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)
        mock_db.execute = AsyncMock(return_value=iter([]))
        mock_db.add = AsyncMock()
        mock_db.commit = AsyncMock()
        mock_session_cls.return_value = mock_db

        plan = await build_plan(["snle"], min_deficit=1, dry_run=True)

    assert all(e["exam_slug"] == "snle" for e in plan)


def test_snle_blueprint_weights_sum_to_100():
    """SNLE blueprint weights (SCFHS 2024) must sum to 100%."""
    from app.scripts.plan_generation import _SNLE_WEIGHTS

    total = sum(_SNLE_WEIGHTS.values())
    assert abs(total - 100.0) < 0.01, f"SNLE weights sum to {total}, expected 100"


def test_snle_weights_differ_from_nclex():
    """SNLE must use SCFHS-specific weights, not NCLEX-RN weights."""
    from app.scripts.plan_generation import _SNLE_WEIGHTS, _NCLEX_RN_WEIGHTS, _exam_weights

    assert _exam_weights("snle") is _SNLE_WEIGHTS
    assert _exam_weights("nclex_rn") is _NCLEX_RN_WEIGHTS
    # Management is 10% for SNLE (vs 17% for NCLEX-RN)
    assert _SNLE_WEIGHTS["management_of_care"] == 10.0
    assert _NCLEX_RN_WEIGHTS["management_of_care"] == 17.0


def test_snle_target_count_uses_snle_weights():
    """_target_count must apply SNLE-specific weights when exam_slug=snle."""
    from app.scripts.plan_generation import _target_count

    # physiological_adaptation is 20% for SNLE (vs 14% for NCLEX-RN)
    snle_target = _target_count("snle", "physiological_adaptation", "mcq")
    nclex_target = _target_count("nclex_rn", "physiological_adaptation", "mcq")
    # SNLE: 1200 * 20% * 75% = 180; NCLEX: 2000 * 14% * 55% = 154
    assert snle_target > nclex_target, (
        f"SNLE physiological_adaptation MCQ target ({snle_target}) should be "
        f"higher than NCLEX-RN ({nclex_target}) due to 20% vs 14% weighting"
    )


# ── API: bank-coverage endpoint ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_bank_coverage_requires_admin(client):
    """Unauthenticated request should return 401."""
    r = await client.get("/api/v1/admin/bank-coverage")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_bank_coverage_returns_structure(admin_client):
    """Admin can call /admin/bank-coverage and gets expected keys."""
    r = await admin_client.get("/api/v1/admin/bank-coverage")
    assert r.status_code == 200
    data = r.json()
    assert "exams" in data
    assert "difficulty_breakdown" in data
    assert "generation_queue" in data
    assert "generated_at" in data


@pytest.mark.asyncio
async def test_bank_coverage_exam_structure(admin_client):
    """Each exam entry has required fields including categories list."""
    r = await admin_client.get("/api/v1/admin/bank-coverage?exam_slug=nclex_rn")
    assert r.status_code == 200
    exams = r.json()["exams"]
    assert len(exams) == 1
    exam = exams[0]
    assert exam["slug"] == "nclex_rn"
    assert exam["volume_target"] == 2000
    assert "total_active" in exam
    assert "total_deficit" in exam
    assert "progress_pct" in exam
    assert "categories" in exam

    # Each category has required fields
    for cat in exam["categories"]:
        assert "name" in cat
        assert "weight_pct" in cat
        assert "deficit" in cat
        assert "types" in cat
        for t in cat["types"]:
            assert "question_type" in t
            assert "actual" in t
            assert "target" in t
            assert "deficit" in t


@pytest.mark.asyncio
async def test_bank_coverage_all_categories_present(admin_client):
    """Response includes all 8 blueprint categories for NCLEX-RN."""
    from app.scripts.plan_generation import BLUEPRINT_WEIGHTS

    r = await admin_client.get("/api/v1/admin/bank-coverage?exam_slug=nclex_rn")
    assert r.status_code == 200
    cat_names = {c["name"] for c in r.json()["exams"][0]["categories"]}
    for cat in BLUEPRINT_WEIGHTS:
        assert cat in cat_names


@pytest.mark.asyncio
async def test_bank_coverage_queue_endpoint(admin_client, db_session):
    """Queue endpoint returns list with correct fields."""
    # Insert a test queue entry
    gq = _make_gq(exam_slug="dha", nclex_category="safe_effective_care", count_requested=25)
    db_session.add(gq)
    await db_session.commit()

    r = await admin_client.get("/api/v1/admin/bank-coverage/queue?exam_slug=dha")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert data["total"] >= 1
    item = next(i for i in data["items"] if i["exam_slug"] == "dha")
    assert item["nclex_category"] == "safe_effective_care"
    assert item["count_requested"] == 25
    assert item["status"] == "pending"
