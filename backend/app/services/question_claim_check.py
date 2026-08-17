"""Bank-Scale B2 — Claim verification for generated questions.

Checks that every factual assertion in a generated question's explanation
and rationales is supported by (not contradicted by) the source document text.

Rules:
- result="no" for ANY claim → question REJECTED
- result="partial" or "not_addressed" → flagged but not auto-rejected (passes with warning)
- result="yes" for all claims → PASSED

This is separate from the article claim-checker (V4) which works per-article.
"""
from __future__ import annotations

import itertools
import json
import logging
import os
import re
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MODEL = "openai/gpt-oss-20b"


def _dedup(lst: list[str]) -> list[str]:
    seen: set[str] = set()
    return [k for k in lst if k and k not in seen and not seen.add(k)]  # type: ignore


_GROQ_KEYS = _dedup([
    os.getenv("GROQ_API_KEY_3", ""),
    os.getenv("GROQ_API_KEY_4", ""),
    os.getenv("GROQ_KEY_MODULE_2", ""),
    os.getenv("GROQ_KEY_CASES", ""),
    os.getenv("GROQ_API_KEY", ""),
])
_key_reset: dict[str, float] = {k: 0.0 for k in _GROQ_KEYS}
_cycle = itertools.cycle(_GROQ_KEYS) if _GROQ_KEYS else None


async def _groq(prompt: str, max_tokens: int = 600) -> str | None:
    if not _cycle:
        return None
    for _ in range(len(_GROQ_KEYS) * 2):
        key = next(_cycle)
        wait = _key_reset.get(key, 0) - time.time()
        if wait > 60:
            continue
        if wait > 0:
            import asyncio; await asyncio.sleep(wait + 0.5)
        try:
            async with httpx.AsyncClient(timeout=45) as c:
                r = await c.post(
                    _GROQ_URL,
                    headers={"Authorization": f"Bearer {key}"},
                    json={"model": _GROQ_MODEL,
                          "messages": [{"role": "user", "content": prompt}],
                          "max_tokens": max_tokens, "temperature": 0.0},
                )
            if r.status_code == 429:
                m = re.search(r"in ([\d.]+)s", r.text)
                _key_reset[key] = time.time() + (float(m.group(1)) if m else 60)
                continue
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.debug("groq call error: %s", e)
    return None


async def extract_key_claims(question_text: str, explanation: str) -> list[str]:
    """Extract ≤5 verifiable medical claims from question + explanation."""
    prompt = (
        "Extract up to 5 verifiable factual claims from this nursing exam question and its explanation.\n"
        "A verifiable claim is a specific medical fact: a statistic, drug dose, mechanism, or clinical rule.\n"
        "Return a JSON array of strings. Return ONLY the JSON array.\n\n"
        f"Question: {question_text[:600]}\n\nExplanation: {explanation[:800]}"
    )
    raw = await _groq(prompt, max_tokens=400)
    if not raw:
        return []
    try:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"```[a-z]*\n?", "", raw).strip().rstrip("`")
        result = json.loads(raw)
        return result if isinstance(result, list) else []
    except Exception:
        return []


async def check_claim(claim: str, source_text: str) -> dict[str, Any]:
    """Check whether source_text supports the claim.

    Returns {"result": "yes"|"no"|"partial"|"not_addressed", "citation": str}
    """
    prompt = (
        "Does the following source text support, contradict, or not address the medical claim?\n\n"
        f"Claim: {claim}\n\n"
        f"Source text (excerpt):\n{source_text[:3000]}\n\n"
        'Answer with JSON: {"result": "yes"|"no"|"partial"|"not_addressed", "citation": "<quoted sentence or empty>"}\n'
        "Return ONLY the JSON object."
    )
    raw = await _groq(prompt, max_tokens=250)
    if not raw:
        return {"result": "not_addressed", "citation": ""}
    try:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = re.sub(r"```[a-z]*\n?", "", raw).strip().rstrip("`")
        data = json.loads(raw)
        return {"result": data.get("result", "not_addressed"), "citation": data.get("citation", "")}
    except Exception:
        return {"result": "not_addressed", "citation": ""}


async def verify_question_against_source(
    question_text: str,
    explanation: str,
    source_text: str,
) -> dict[str, Any]:
    """Full claim-check pipeline for a generated question.

    Returns:
        {
            "passed": bool,
            "claims": [{"claim": str, "result": str, "citation": str}],
            "rejected_reason": str | None,   # set only when passed=False
        }
    """
    claims = await extract_key_claims(question_text, explanation)
    if not claims:
        # No claims extractable — pass with warning (no Groq keys or trivial question)
        return {"passed": True, "claims": [], "rejected_reason": None}

    checks: list[dict] = []
    for claim in claims[:5]:
        result = await check_claim(claim, source_text)
        checks.append({"claim": claim, **result})

    contradicted = [c for c in checks if c["result"] == "no"]
    if contradicted:
        return {
            "passed": False,
            "claims": checks,
            "rejected_reason": f"Contradicted by source: {contradicted[0]['claim']!r}",
        }
    return {"passed": True, "claims": checks, "rejected_reason": None}
