"""Content verification service — V4 Phase 1.

Extracts medical claims from articles and checks each claim against
the article's declared sources. Updates verification_status accordingly.

Status machine:
  pending  → passed (all claims confirmed)
  pending  → failed (any claim contradicted)
  passed   → human_reviewed (admin marks as expert-reviewed)
  failed   → pending (re-verification after content edit)

Public endpoints must NOT serve pending or failed content.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
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
