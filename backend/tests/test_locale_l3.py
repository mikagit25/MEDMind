"""Locale L3 — Locale linter: pure unit tests.

Verifies:
- lint_question: each of the 5 violation classes triggers correctly
- lint_question: clean Gulf-appropriate content passes
- lint_questions_batch: correctly splits passed/failed lists
- LintResult: correct field values on pass and fail
- Jurisdiction context: EXAM_TO_PROFILE mapping covers all 7 Gulf exams
"""
from __future__ import annotations

import pytest
from app.services.locale_linter import lint_question, lint_questions_batch, LintResult
from app.prompts.jurisdiction_context import EXAM_TO_PROFILE


# ── Bad question fixture (triggers all 5 violations) ─────────────────────────

_BAD_Q = {
    "question": "Call 911 and follow HIPAA guidelines for this patient.",
    "options": {"A": "Contact CDC immediately", "B": "Give Narcan 0.4mg", "C": "Option C", "D": "Option D"},
    "explanation": "Blood glucose is 250 mg/dL. Per CMS rules, document using US standards.",
}

_GOOD_Q = {
    "question": "A patient's blood glucose is 13.9 mmol/L. What is the priority action?",
    "options": {
        "A": "Administer insulin as prescribed",
        "B": "Give oral paracetamol 500mg",
        "C": "Notify SCFHS immediately",
        "D": "Increase IV fluids to 100 mL/h",
    },
    "explanation": "Per DOH guidelines, hyperglycaemia > 11 mmol/L requires prompt intervention.",
}


# ── Violation class: us_emergency_number_911 ──────────────────────────────────

def test_lint_flags_911():
    q = {"question": "Dial 911 for cardiac arrest.", "options": {}, "explanation": ""}
    result = lint_question(q, exam_slug="snle")
    assert not result.passed
    assert "us_emergency_number_911" in result.violations


def test_lint_flags_911_hyphenated():
    q = {"question": "Call 9-1-1 now.", "options": {}, "explanation": ""}
    result = lint_question(q, exam_slug="dha")
    assert not result.passed
    assert "us_emergency_number_911" in result.violations


# ── Violation class: us_regulatory_reference ──────────────────────────────────

def test_lint_flags_hipaa():
    q = {"question": "HIPAA protects patient privacy.", "options": {}, "explanation": ""}
    result = lint_question(q, exam_slug="snle")
    assert not result.passed
    assert "us_regulatory_reference" in result.violations


def test_lint_flags_joint_commission():
    q = {"question": "The Joint Commission accredits hospitals.", "options": {}, "explanation": ""}
    result = lint_question(q, exam_slug="snle")
    assert not result.passed
    assert "us_regulatory_reference" in result.violations


def test_lint_flags_medicare():
    q = {"question": "Patient enrolled in Medicare.", "options": {}, "explanation": ""}
    result = lint_question(q, exam_slug="dha")
    assert not result.passed
    assert "us_regulatory_reference" in result.violations


# ── Violation class: us_agency_reference ─────────────────────────────────────

def test_lint_flags_cdc():
    q = {"question": "CDC recommends this vaccine schedule.", "options": {}, "explanation": ""}
    result = lint_question(q, exam_slug="snle")
    assert not result.passed
    assert "us_agency_reference" in result.violations


def test_lint_flags_fda():
    q = {"question": "FDA approved this medication.", "options": {}, "explanation": ""}
    result = lint_question(q, exam_slug="snle")
    assert not result.passed
    assert "us_agency_reference" in result.violations


# ── Violation class: non_si_unit ─────────────────────────────────────────────

def test_lint_flags_mg_dl():
    q = {"question": "Glucose is 180 mg/dL.", "options": {}, "explanation": ""}
    result = lint_question(q, exam_slug="snle")
    assert not result.passed
    assert "non_si_unit" in result.violations


def test_lint_flags_fahrenheit():
    q = {"question": "Temperature is 98.6°F.", "options": {}, "explanation": ""}
    result = lint_question(q, exam_slug="dha")
    assert not result.passed
    assert "non_si_unit" in result.violations


def test_lint_flags_pounds():
    q = {"question": "Patient weighs 150 lbs.", "options": {}, "explanation": ""}
    result = lint_question(q, exam_slug="snle")
    assert not result.passed
    assert "non_si_unit" in result.violations


# ── Violation class: us_brand_drug_name ───────────────────────────────────────

def test_lint_flags_narcan():
    q = {"question": "Administer Narcan 0.4mg IV.", "options": {}, "explanation": ""}
    result = lint_question(q, exam_slug="snle")
    assert not result.passed
    assert "us_brand_drug_name" in result.violations


def test_lint_flags_tylenol():
    q = {"question": "Give Tylenol 500mg for pain.", "options": {}, "explanation": ""}
    result = lint_question(q, exam_slug="dha")
    assert not result.passed
    assert "us_brand_drug_name" in result.violations


def test_lint_flags_epipen():
    q = {"question": "Inject EpiPen into the thigh.", "options": {}, "explanation": ""}
    result = lint_question(q, exam_slug="snle")
    assert not result.passed
    assert "us_brand_drug_name" in result.violations


# ── Good Gulf content passes ──────────────────────────────────────────────────

def test_lint_passes_si_units_generic_drugs():
    result = lint_question(_GOOD_Q, exam_slug="snle")
    assert result.passed
    assert result.violations == []
    assert result.matched_text == []


def test_lint_passes_mmol_l():
    q = {"question": "HbA1c is 53 mmol/mol.", "options": {}, "explanation": ""}
    result = lint_question(q, exam_slug="snle")
    assert result.passed


def test_lint_passes_celsius():
    q = {"question": "Patient temperature 38.5°C.", "options": {}, "explanation": ""}
    result = lint_question(q, exam_slug="dha")
    assert result.passed


def test_lint_passes_paracetamol():
    q = {"question": "Administer paracetamol 1g IV.", "options": {}, "explanation": ""}
    result = lint_question(q, exam_slug="snle")
    assert result.passed


# ── All 5 violations at once ──────────────────────────────────────────────────

def test_lint_bad_question_all_5_violations():
    result = lint_question(_BAD_Q, exam_slug="snle")
    assert not result.passed
    assert len(result.violations) == 5
    assert "us_emergency_number_911" in result.violations
    assert "us_regulatory_reference" in result.violations
    assert "us_agency_reference" in result.violations
    assert "non_si_unit" in result.violations
    assert "us_brand_drug_name" in result.violations


# ── LintResult fields ─────────────────────────────────────────────────────────

def test_lint_result_exam_slug_stored():
    result = lint_question(_GOOD_Q, exam_slug="qchp")
    assert result.exam_slug == "qchp"


def test_lint_result_matched_text_populated_on_fail():
    q = {"question": "Call 911.", "options": {}, "explanation": ""}
    result = lint_question(q, exam_slug="snle")
    assert len(result.matched_text) >= 1


def test_lint_result_is_dataclass():
    result = lint_question(_GOOD_Q)
    assert isinstance(result, LintResult)


# ── Batch linting ─────────────────────────────────────────────────────────────

def test_batch_splits_passed_and_failed():
    questions = [_GOOD_Q, _BAD_Q, _GOOD_Q]
    passed, failed = lint_questions_batch(questions, exam_slug="snle")
    assert len(passed) == 2
    assert len(failed) == 1


def test_batch_failed_has_lint_violations_key():
    questions = [_BAD_Q]
    passed, failed = lint_questions_batch(questions, exam_slug="snle")
    assert len(failed) == 1
    assert "_lint_violations" in failed[0]
    assert "_lint_matched" in failed[0]


def test_batch_all_pass():
    questions = [_GOOD_Q, _GOOD_Q]
    passed, failed = lint_questions_batch(questions, exam_slug="dha")
    assert len(passed) == 2
    assert len(failed) == 0


def test_batch_empty_input():
    passed, failed = lint_questions_batch([], exam_slug="snle")
    assert passed == []
    assert failed == []


# ── Jurisdiction context: EXAM_TO_PROFILE mapping ────────────────────────────

def test_exam_to_profile_covers_all_gulf_exams():
    required = {"snle", "dha", "haad", "doh", "qchp", "omsb", "nhra", "moh_kw"}
    assert required.issubset(set(EXAM_TO_PROFILE.keys())), (
        f"Missing Gulf exams in EXAM_TO_PROFILE: {required - set(EXAM_TO_PROFILE.keys())}"
    )


def test_exam_to_profile_snle_maps_to_sa():
    assert EXAM_TO_PROFILE["snle"] == "sa"


def test_exam_to_profile_dha_maps_to_ae_dubai():
    assert EXAM_TO_PROFILE["dha"] == "ae_dubai"


def test_exam_to_profile_qchp_maps_to_qa():
    assert EXAM_TO_PROFILE["qchp"] == "qa"
