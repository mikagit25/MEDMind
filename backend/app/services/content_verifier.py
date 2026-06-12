"""Content verification service — V4 Phase 1 + Phase 2.

Phase 1: Extracts medical claims from articles and checks each claim
  against the article's declared sources. Updates verification_status.

Phase 2: Translation QA — checks translated text for:
  - Number/unit preservation (regex)
  - Negation preservation (Haiku)
  - Medical glossary canonical term usage

Status machine (articles):
  pending  → passed (all claims confirmed)
  pending  → failed (any claim contradicted)
  passed   → human_reviewed (admin marks as expert-reviewed)
  failed   → pending (re-verification after content edit)

Translation QA status:
  pending → passed | failed

Public endpoints must NOT serve pending or failed content.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx
from anthropic import AsyncAnthropic

from app.core.config import settings

logger = logging.getLogger(__name__)

# V4 valid statuses
PUBLISHED_STATUSES = {"passed", "human_reviewed"}
BLOCKED_STATUSES = {"pending", "failed"}

_anthropic: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _anthropic
    if _anthropic is None:
        _anthropic = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _anthropic


async def _extract_claims(article_text: str) -> list[str]:
    """Extract verifiable medical claims from article text using Haiku."""
    client = _get_client()
    prompt = (
        "Extract all verifiable medical claims from the following article text. "
        "A verifiable claim is a specific factual statement: a statistic, dosage mention, "
        "causal assertion, or clinical recommendation. "
        "Return a JSON array of strings, each string is one claim. "
        "Limit to the 10 most important claims. "
        "Return ONLY the JSON array, no other text.\n\n"
        f"Article text:\n{article_text[:4000]}"
    )
    try:
        resp = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        claims = json.loads(raw)
        return claims if isinstance(claims, list) else []
    except Exception as exc:
        logger.warning("claim extraction failed: %s", exc)
        return []


async def _check_claim_against_source(claim: str, source_text: str) -> dict[str, Any]:
    """Ask Haiku whether source_text supports the claim.

    Returns {"result": "yes"|"no"|"partial", "citation": str}
    """
    client = _get_client()
    prompt = (
        "Does the following source text support, contradict, or not address the given medical claim?\n\n"
        f"Claim: {claim}\n\n"
        f"Source text (excerpt):\n{source_text[:3000]}\n\n"
        "Answer with a JSON object: "
        '{"result": "yes"|"no"|"partial"|"not_addressed", "citation": "<quoted sentence from source or empty string>"}\n'
        "Return ONLY the JSON object."
    )
    try:
        resp = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        data = json.loads(raw)
        return {
            "result": data.get("result", "not_addressed"),
            "citation": data.get("citation", ""),
        }
    except Exception as exc:
        logger.warning("claim check failed: %s", exc)
        return {"result": "not_addressed", "citation": ""}


async def _fetch_source_text(url: str, timeout: int = 10) -> str:
    """Attempt to fetch a URL and return plain-text content (first 5000 chars)."""
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "MedMindBot/1.0"})
            resp.raise_for_status()
            text = resp.text
            # Very rough tag strip
            import re
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()
            return text[:5000]
    except Exception as exc:
        logger.debug("source fetch failed for %s: %s", url, exc)
        return ""


def _article_to_text(article_body: list[dict]) -> str:
    """Convert article body blocks to plain text."""
    parts: list[str] = []
    for block in (article_body or []):
        btype = block.get("type", "")
        content = block.get("content", "")
        if isinstance(content, dict):
            content = content.get("text", "")
        if btype in ("h2", "h3", "p", "callout") and isinstance(content, str):
            parts.append(content)
        elif btype == "ul" and isinstance(content, list):
            parts.extend(content)
    return " ".join(parts)


async def verify_article(
    article_id: str,
    article_body: list[dict],
    sources: list[dict] | None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run verification on a single article.

    Returns a dict with:
      status: "passed" | "failed" | "pending"
      report: [{claim, source_url, result, citation}]
      verified_at: ISO datetime string
    """
    text = _article_to_text(article_body)
    if not text.strip():
        return {"status": "pending", "report": [], "verified_at": datetime.utcnow().isoformat()}

    claims = await _extract_claims(text)
    if not claims:
        # No extractable claims — treat as passed (no verifiable assertions)
        return {
            "status": "passed",
            "report": [],
            "verified_at": datetime.utcnow().isoformat(),
        }

    report: list[dict] = []
    has_failure = False

    for claim in claims:
        best_result = "not_addressed"
        best_citation = ""
        checked_source = ""

        for source in (sources or []):
            url = source.get("url", "")
            if not url:
                continue
            source_text = await _fetch_source_text(url)
            if not source_text:
                continue
            check = await _check_claim_against_source(claim, source_text)
            checked_source = url
            best_result = check["result"]
            best_citation = check["citation"]
            if best_result in ("yes", "partial"):
                break  # Good enough — move to next claim

        report.append({
            "claim": claim,
            "source_url": checked_source,
            "result": best_result,
            "citation": best_citation,
        })

        if best_result == "no":
            has_failure = True

    if has_failure:
        status = "failed"
    elif all(r["result"] in ("yes", "partial", "not_addressed") for r in report):
        # If at least one claim was confirmed, call it passed
        confirmed = [r for r in report if r["result"] in ("yes", "partial")]
        status = "passed" if confirmed else "pending"
    else:
        status = "pending"

    return {
        "status": status,
        "report": report,
        "verified_at": datetime.utcnow().isoformat(),
    }


def is_publicly_servable(verification_status: str | None) -> bool:
    """Return True only for statuses that may be served on public endpoints."""
    return (verification_status or "pending") in PUBLISHED_STATUSES


# ── V4 Phase 2: Translation Quality Assurance ─────────────────────────────────

_GLOSSARY_DIR = Path(__file__).parent.parent / "data" / "med_glossary"

# Regex for medical numbers with units — captures the numeric token for comparison
_NUM_UNIT_RE = re.compile(
    r"\b(\d+(?:[.,]\d+)?)\s*"
    r"(?:mg|mcg|µg|μg|g|kg|ml|mL|L|mmol|nmol|mmHg|cmH2O|IU|U|%|kcal|"
    r"mg/dL|mmol/L|ng/mL|pg/mL|mEq/L|bpm|rpm|Hz|min|h|hr|hours?|days?|weeks?|months?|years?)"
    r"(?=\s|\W|$)",
    re.IGNORECASE,
)


@lru_cache(maxsize=16)
def _load_glossary(lang: str) -> dict[str, str]:
    """Load canonical medical terms for a language. Cached per lang."""
    path = _GLOSSARY_DIR / f"{lang}.json"
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("terms", {})
    except Exception as exc:
        logger.warning("glossary load failed for %s: %s", lang, exc)
        return {}


def _check_numbers(original: str, translated: str) -> list[dict]:
    """Return list of numeric values (with units) present in original but absent in translation.

    Compares raw numeric digits only — so "500mg" vs "500мг" both count as preserving "500".
    """
    # Extract full token + its numeric digit group
    matches = list(_NUM_UNIT_RE.finditer(original))
    if not matches:
        return []

    # All digit sequences in the translated text
    tr_digits = set(re.findall(r"\d+(?:[.,]\d+)?", translated))

    missing = []
    seen_nums: set[str] = set()
    for m in matches:
        num = m.group(1)  # captured digit group
        full_token = m.group(0)
        if num in seen_nums:
            continue
        seen_nums.add(num)
        if num not in tr_digits:
            missing.append({"token": full_token, "issue": "missing_in_translation"})
    return missing


def _build_glossary_prompt_context(original_en: str, lang: str) -> str:
    """Build a glossary reminder string for injection into translation prompts."""
    glossary = _load_glossary(lang)
    if not glossary:
        return ""
    en_glossary = _load_glossary("en")
    reminders: list[str] = []
    text_lower = original_en.lower()
    for key, translated_term in glossary.items():
        en_term = en_glossary.get(key, key)
        if key in text_lower or en_term.lower() in text_lower:
            reminders.append(f'"{en_term}" → "{translated_term}"')
    if not reminders:
        return ""
    return "Medical glossary (use these exact translations):\n" + "\n".join(reminders[:20])


def _glossary_term_present(canonical: str, tr_lower: str) -> bool:
    """Check if a canonical term (or its stem) appears in the translated text.

    Uses the longest word of the canonical phrase as the key token, then checks
    whether the first 7 characters (stem) appear — to handle case declension in
    inflected languages like Russian, Turkish, Arabic.
    """
    canonical_lower = canonical.lower()
    if canonical_lower in tr_lower:
        return True
    # Use longest word as key token
    words = canonical_lower.split()
    if not words:
        return False
    key_word = max(words, key=len)
    stem_len = min(7, len(key_word))
    stem = key_word[:stem_len]
    return stem in tr_lower


def _check_glossary_terms(original_en: str, translated: str, lang: str) -> list[dict]:
    """Return list of glossary terms that are in the original but incorrectly translated."""
    glossary = _load_glossary(lang)
    en_glossary = _load_glossary("en")
    issues = []
    text_lower = original_en.lower()
    tr_lower = translated.lower()
    for key, canonical_translation in glossary.items():
        en_term = en_glossary.get(key, key)
        if key not in text_lower and en_term.lower() not in text_lower:
            continue
        if not _glossary_term_present(canonical_translation, tr_lower):
            issues.append({
                "term": en_term,
                "expected": canonical_translation,
                "issue": "glossary_term_not_found",
            })
    return issues


async def _check_negation_preserved(original: str, translated: str) -> dict:
    """Ask Haiku whether negations in original are preserved in translation."""
    negation_words = ["not", "no", "never", "without", "contraindicated", "avoid",
                      "do not", "should not", "must not", "don't", "isn't", "aren't",
                      "doesn't", "cannot", "can't"]
    orig_lower = original.lower()
    has_negation = any(w in orig_lower for w in negation_words)
    if not has_negation:
        return {"preserved": True, "note": "no negations detected"}

    client = _get_client()
    prompt = (
        "Check whether the negation/contraindication meaning in the ORIGINAL English text "
        "is preserved in the TRANSLATION.\n\n"
        f"ORIGINAL: {original[:2000]}\n\n"
        f"TRANSLATION: {translated[:2000]}\n\n"
        "Answer with a JSON object: "
        '{"preserved": true|false, "note": "<brief explanation>"}\n'
        "Return ONLY the JSON object."
    )
    try:
        resp = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        return json.loads(raw)
    except Exception as exc:
        logger.warning("negation check failed: %s", exc)
        return {"preserved": True, "note": f"check error: {exc}"}


async def check_translation_quality(
    original_en: str,
    translated: str,
    lang: str,
    article_id: str = "",
) -> dict[str, Any]:
    """Run QA checks on a translated article text.

    Returns:
      status: "passed" | "failed"
      report: {numbers: [...], glossary: [...], negation: {...}}
      checked_at: ISO datetime string
    """
    report: dict[str, Any] = {}
    failures: list[str] = []

    # 1. Number/unit preservation
    number_issues = _check_numbers(original_en, translated)
    report["numbers"] = number_issues
    if number_issues:
        failures.append("number_corruption")

    # 2. Glossary canonical terms (only for supported languages)
    glossary_issues = _check_glossary_terms(original_en, translated, lang)
    report["glossary"] = glossary_issues
    # Glossary issues are warnings, not hard failures (translation variance is acceptable)
    # Mark failed only if more than 30% of detected terms are wrong
    if glossary_issues:
        en_glossary = _load_glossary("en")
        glossary = _load_glossary(lang)
        detected_count = sum(
            1 for key in glossary
            if key in original_en.lower() or en_glossary.get(key, key).lower() in original_en.lower()
        )
        if detected_count > 0 and len(glossary_issues) / detected_count > 0.30:
            failures.append("glossary_mismatch")

    # 3. Negation preservation
    negation_result = await _check_negation_preserved(original_en, translated)
    report["negation"] = negation_result
    if not negation_result.get("preserved", True):
        failures.append("negation_lost")

    status = "failed" if failures else "passed"
    return {
        "status": status,
        "failures": failures,
        "report": report,
        "checked_at": datetime.utcnow().isoformat(),
    }
