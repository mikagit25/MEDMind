"""L3.3 — Post-generation locale linter for Gulf exam questions.

Checks a generated question dict for jurisdiction-banned artifacts.
A failed lint means the question is NOT saved (caller must discard it).

Usage:
    from app.services.locale_linter import lint_question, LintResult

    result = lint_question(question_dict, exam_slug="snle")
    if not result.passed:
        log.warning("Lint failed (%s): %s", result.violations, question_text)
        continue  # discard question
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ── Banned patterns (Gulf jurisdiction) ───────────────────────────────────────

_US_EMERGENCY = re.compile(r"\b9-?1-?1\b")
_US_REGULATORY = re.compile(
    r"\b("
    r"HIPAA|HITECH|Joint Commission|JCAHO|OSHA|ADA\b|EMTALA|OBRA|"
    r"Nurse Practice Act|State Board of Nursing|Board of Registered Nursing|"
    r"CMS\b|Medicare\b|Medicaid\b|AHRQ"
    r")\b",
    re.IGNORECASE,
)
_US_AGENCIES = re.compile(
    r"\b("
    r"CDC\b|FDA\b|DEA\b|NIH\b|ACOG\b(?!\s+guidelines)|"
    r"AHA guidelines|ANA Code of Ethics|"
    r"Department of Health and Human Services|HHS\b"
    r")\b",
    re.IGNORECASE,
)

# mg/dL is NOT SI — Gulf uses mmol/L for glucose/cholesterol
# lb/lbs, °F, inches are not SI
_NON_SI = re.compile(
    r"\b("
    r"mg/dL|mg/dl|"
    r"\d+\s*(?:lb|lbs|pound|pounds)\b|"
    r"\d+\.?\d*\s*°F|"
    r"\d+\.?\d*\s*Fahrenheit|"
    r"\d+\s*(?:inch|inches|in\b|foot|feet|ft\b|mile|miles)"
    r")\b",
    re.IGNORECASE,
)

# Common US brand names that may not be registered in Gulf / are better replaced with generics
_TRADE_NAMES = re.compile(
    r"\b("
    r"Tylenol|Advil|Motrin|Benadryl|Zofran|Narcan\b|EpiPen|"
    r"Prilosec|Nexium|Lipitor|Zocor|Plavix|Coumadin(?!\s+generic)|"
    r"Synthroid|Xanax|Valium|Ativan|Lasix|Glucophage|"
    r"Augmentin|Zithromax|Diflucan|Cipro\b|Flagyl"
    r")\b",
    re.IGNORECASE,
)

_LINT_RULES: list[tuple[str, re.Pattern]] = [
    ("us_emergency_number_911", _US_EMERGENCY),
    ("us_regulatory_reference", _US_REGULATORY),
    ("us_agency_reference", _US_AGENCIES),
    ("non_si_unit", _NON_SI),
    ("us_brand_drug_name", _TRADE_NAMES),
]


@dataclass
class LintResult:
    passed: bool
    violations: list[str] = field(default_factory=list)
    matched_text: list[str] = field(default_factory=list)
    exam_slug: str = ""


def _extract_text(question: dict[str, Any]) -> str:
    """Collect all text content from a question dict."""
    parts: list[str] = []

    def add(v: Any) -> None:
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, dict):
            for val in v.values():
                add(val)
        elif isinstance(v, list):
            for item in v:
                add(item)

    for key in ("question", "options", "explanation", "rationales",
                "key_takeaway", "test_taking_tip"):
        if key in question:
            add(question[key])
    return " ".join(parts)


def lint_question(question: dict[str, Any], exam_slug: str = "") -> LintResult:
    """Check a single question dict against Gulf locale rules.

    Returns LintResult with passed=True only if all checks pass.
    The question must NOT be saved when passed=False.
    """
    text = _extract_text(question)
    violations: list[str] = []
    matched: list[str] = []

    for rule_name, pattern in _LINT_RULES:
        m = pattern.search(text)
        if m:
            violations.append(rule_name)
            matched.append(m.group())

    return LintResult(
        passed=len(violations) == 0,
        violations=violations,
        matched_text=matched,
        exam_slug=exam_slug,
    )


def lint_questions_batch(
    questions: list[dict[str, Any]], exam_slug: str = ""
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split a list of generated questions into (passed, failed).

    Returns two lists: questions that passed linting, and those that failed.
    Failed questions include a '_lint_violations' key for logging.
    """
    passed: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []

    for q in questions:
        result = lint_question(q, exam_slug=exam_slug)
        if result.passed:
            passed.append(q)
        else:
            q["_lint_violations"] = result.violations
            q["_lint_matched"] = result.matched_text
            failed.append(q)

    return passed, failed
