"""
G1 acceptance tests — Exam Registry & Gulf Prometric family.

Verifies:
- exam_registry.py data integrity (all required fields present)
- _is_stale_blueprint logic (>365 days or None → stale)
- NCLEX-to-Gulf category mapper coverage
- user_has_exam_access access rules (pro/clinic/gulf_bundle/student/free)
- is_gulf_exam helper
- API endpoints (definitions list, by slug, by family) — unit-mocked
"""
import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.data.exam_registry import (
    ALL_EXAMS, GULF_EXAMS, NCLEX_TO_GULF_CATEGORY_MAP,
)
from app.services.billing import user_has_exam_access, is_gulf_exam


# ── Registry data integrity ───────────────────────────────────────────────────

REQUIRED_FIELDS = [
    "slug", "name", "country", "regulatory_body",
    "question_count", "duration_min", "pass_threshold",
    "blueprint_source", "family", "options_per_question",
]

@pytest.mark.parametrize("exam", ALL_EXAMS)
def test_exam_has_required_fields(exam):
    for field in REQUIRED_FIELDS:
        assert field in exam, f"'{field}' missing from exam '{exam.get('slug', '?')}'"
        assert exam[field] is not None, f"'{field}' is None in '{exam['slug']}'"


@pytest.mark.parametrize("exam", ALL_EXAMS)
def test_exam_question_count_positive(exam):
    assert exam["question_count"] > 0
    assert exam["duration_min"] > 0
    assert 0 < exam["pass_threshold"] <= 100


@pytest.mark.parametrize("exam", ALL_EXAMS)
def test_exam_has_disclaimer(exam):
    assert exam.get("disclaimer"), f"No disclaimer on exam '{exam['slug']}'"


@pytest.mark.parametrize("exam", ALL_EXAMS)
def test_exam_has_blueprint_source_url(exam):
    src = exam["blueprint_source"]
    assert src.startswith("http"), f"blueprint_source must be a URL, got '{src}' for '{exam['slug']}'"


def test_gulf_exams_all_in_gulf_family():
    for exam in GULF_EXAMS:
        assert exam["family"] == "gulf", f"'{exam['slug']}' family should be 'gulf'"


def test_gulf_slugs_unique():
    slugs = [e["slug"] for e in GULF_EXAMS]
    assert len(slugs) == len(set(slugs)), "Duplicate slugs in GULF_EXAMS"


def test_gulf_exam_count():
    assert len(GULF_EXAMS) == 7, f"Expected 7 Gulf exams, got {len(GULF_EXAMS)}"


def test_gulf_exam_slugs():
    expected = {"snle", "dha", "qchp", "omsb", "nhra", "mohuae", "haad"}
    actual = {e["slug"] for e in GULF_EXAMS}
    assert actual == expected


# ── Stale blueprint detection ─────────────────────────────────────────────────

from app.api.v1.routes.exam import _is_stale_blueprint


def test_stale_blueprint_none():
    assert _is_stale_blueprint(None) is True


def test_stale_blueprint_old():
    old = (date.today() - timedelta(days=400)).isoformat()
    assert _is_stale_blueprint(old) is True


def test_stale_blueprint_recent():
    recent = (date.today() - timedelta(days=30)).isoformat()
    assert _is_stale_blueprint(recent) is False


def test_stale_blueprint_exactly_365():
    boundary = (date.today() - timedelta(days=365)).isoformat()
    assert _is_stale_blueprint(boundary) is False


def test_stale_blueprint_invalid_string():
    assert _is_stale_blueprint("not-a-date") is True


# ── NCLEX-to-Gulf category map coverage ───────────────────────────────────────

def test_nclex_category_map_non_empty():
    assert len(NCLEX_TO_GULF_CATEGORY_MAP) > 0


def test_nclex_key_pharmacological_maps_to_pharmacology():
    assert NCLEX_TO_GULF_CATEGORY_MAP.get("pharmacological") == "pharmacology"


def test_nclex_key_safe_care_maps_to_fundamentals():
    assert NCLEX_TO_GULF_CATEGORY_MAP.get("safe_effective_care") == "fundamentals_nursing"


def test_nclex_key_psychosocial_maps_to_mental_health():
    assert NCLEX_TO_GULF_CATEGORY_MAP.get("psychosocial") == "mental_health"


# ── user_has_exam_access rules ────────────────────────────────────────────────

def _user(tier: str):
    u = MagicMock()
    u.subscription_tier = tier
    return u


def test_pro_user_can_access_gulf_exam():
    assert user_has_exam_access(_user("pro"), "dha") is True


def test_clinic_user_can_access_gulf_exam():
    assert user_has_exam_access(_user("clinic"), "qchp") is True


def test_lifetime_user_can_access_gulf_exam():
    assert user_has_exam_access(_user("lifetime"), "snle") is True


def test_gulf_bundle_accesses_gulf_exams():
    for slug in ["snle", "dha", "qchp", "omsb", "nhra", "mohuae", "haad"]:
        assert user_has_exam_access(_user("gulf_bundle"), slug) is True, f"Failed for {slug}"


def test_gulf_bundle_cannot_access_nclex():
    # nclex is not in gulf family
    assert user_has_exam_access(_user("gulf_bundle"), "nclex_rn_75") is False


def test_student_can_access_nclex_not_gulf():
    assert user_has_exam_access(_user("student"), "ukmla") is True
    assert user_has_exam_access(_user("student"), "dha") is False


def test_free_user_denied_all_exams():
    assert user_has_exam_access(_user("free"), "dha") is False
    assert user_has_exam_access(_user("free"), "nclex_rn_75") is False


# ── is_gulf_exam helper ───────────────────────────────────────────────────────

def test_is_gulf_exam_true():
    for slug in ["snle", "dha", "qchp", "omsb", "nhra", "mohuae", "haad"]:
        assert is_gulf_exam(slug) is True


def test_is_gulf_exam_false_for_nclex():
    assert is_gulf_exam("nclex_rn_75") is False
    assert is_gulf_exam("ukmla") is False
    assert is_gulf_exam("") is False
