"""LLM-based re-audit of quarantined Gulf MCQ questions.

Re-classifies the 42 quarantined (jurisdiction_sensitive=True,
jurisdiction_verified_for=None) questions using semantic LLM analysis
instead of regex keyword matching.

Clears jurisdiction_sensitive=False for questions that are genuinely
universal (not actually jurisdiction-specific).

Run:
    docker exec medmind_backend python3 -m app.scripts.reaudit_quarantined
    docker exec medmind_backend python3 -m app.scripts.reaudit_quarantined --dry-run
"""
from __future__ import annotations

import asyncio
import argparse
import json
import logging
import os
import time
from typing import Optional

import httpx
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.models import MCQQuestion

log = logging.getLogger(__name__)

# ── LLM config ───────────────────────────────────────────────────────────────

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_KEYS = [k for k in [
    os.getenv("GROQ_API_KEY_3"),
    os.getenv("GROQ_API_KEY_4"),
    os.getenv("GROQ_API_KEY_1"),
    os.getenv("GROQ_API_KEY_2"),
] if k]

_CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
_CEREBRAS_KEYS = [k for k in [
    os.getenv("CEREBRAS_API_KEY_1"),
    os.getenv("CEREBRAS_API_KEY_2"),
] if k]

SYSTEM_PROMPT = """You are a medical education expert specializing in Gulf region nursing licensing exams (SNLE, DHA, HAAD, QCHP, OMSB, NHRA, MOHUAE).

Your task: determine if a given MCQ question is TRULY jurisdiction-sensitive for Gulf exams.

A question is TRULY jurisdiction-sensitive if it:
1. References US-specific laws/agencies that don't exist in the Gulf (HIPAA, EMTALA, Medicare, Medicaid, Nurse Practice Act, state boards)
2. Tests knowledge of clinical values using NON-SI units WHERE the unit itself matters for the answer (e.g., comparing mg/dL vs mmol/L thresholds where students need to know which range is normal)
3. References US emergency number 911 as the action to take
4. Tests legal/ethical frameworks specific to US (e.g., POLST, advance directives law, emancipated minor rules) that differ meaningfully in the Gulf
5. References US drug regulatory body (FDA) as the authoritative body for a clinical decision

A question is NOT jurisdiction-sensitive (universal) if it:
1. Contains mg/dL values in the scenario/rationale but the correct answer doesn't depend on knowing unit conversion (e.g., glucose 720 mg/dL is obviously high regardless of units)
2. Tests universal physiology, pharmacology, or clinical assessment that is the same worldwide
3. Mentions an organization in passing but the clinical decision is not based on that org's jurisdiction-specific rules
4. Is set in a Gulf context (mentions Saudi, UAE, Qatar, Bahrain hospitals explicitly) — these are APPROPRIATE, not problematic
5. Tests cultural/religious care practices that are actually RELEVANT and expected knowledge for Gulf nurses

Respond with JSON only:
{"sensitive": true/false, "reason": "one sentence explanation"}"""


async def _call_llm(question_text: str, options_text: str, rationale_text: str, key: str, url: str, model: str) -> Optional[dict]:
    prompt = f"""Question: {question_text}

Options: {options_text}

Rationale (excerpt): {rationale_text[:400]}

Is this question truly jurisdiction-sensitive for Gulf nursing exams? Respond JSON only."""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": 150,
                "temperature": 0,
            })
            if resp.status_code == 429:
                return None
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            # strip markdown fences if present
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            return json.loads(content)
    except Exception as e:
        log.debug("LLM call failed: %s", e)
        return None


async def _classify_with_llm(question: MCQQuestion) -> Optional[dict]:
    """Try Groq keys then Cerebras keys."""
    opts = question.options or {}
    if isinstance(opts, dict):
        opts_str = " | ".join(f"{k}: {v}" for k, v in opts.items())
    elif isinstance(opts, list):
        opts_str = " | ".join(str(o) for o in opts)
    else:
        opts_str = str(opts)

    rationale = question.explanation or question.key_takeaway or ""

    # Try Groq first (content pipeline keys)
    for key in _GROQ_KEYS:
        result = await _call_llm(question.question or "", opts_str, rationale, key, _GROQ_URL, "llama-3.3-70b-versatile")
        if result is not None:
            return result
        await asyncio.sleep(2)

    # Fallback: Cerebras
    for key in _CEREBRAS_KEYS:
        result = await _call_llm(question.question or "", opts_str, rationale, key, _CEREBRAS_URL, "gemma-4-31b")
        if result is not None:
            return result
        await asyncio.sleep(2)

    return None


async def run(dry_run: bool = False) -> None:
    async with AsyncSessionLocal() as db:
        r = await db.execute(
            select(MCQQuestion)
            .where(
                MCQQuestion.jurisdiction_sensitive == True,
                MCQQuestion.jurisdiction_verified_for == None,
                MCQQuestion.status == "active",
            )
        )
        questions = r.scalars().all()

    log.info("Quarantined questions to re-audit: %d", len(questions))

    cleared = 0
    confirmed = 0
    failed = 0

    async with AsyncSessionLocal() as db:
        for i, q in enumerate(questions):
            log.info("[%d/%d] %s...", i + 1, len(questions), (q.question or "")[:80])

            result = await _classify_with_llm(q)

            if result is None:
                log.warning("  → LLM unavailable, skipping")
                failed += 1
                await asyncio.sleep(5)
                continue

            is_sensitive = result.get("sensitive", True)
            reason = result.get("reason", "")

            if is_sensitive:
                confirmed += 1
                log.info("  → SENSITIVE (confirmed): %s", reason)
            else:
                cleared += 1
                log.info("  → CLEAR (false positive): %s", reason)
                if not dry_run:
                    q_obj = await db.get(MCQQuestion, q.id)
                    if q_obj:
                        q_obj.jurisdiction_sensitive = False
                        q_obj.jurisdiction_audit_notes = f"llm_cleared: {reason}"

            await asyncio.sleep(1)

        if not dry_run:
            await db.commit()

    print()
    print("=== RE-AUDIT COMPLETE ===")
    print(f"  Total audited : {len(questions)}")
    print(f"  Cleared (false positives) : {cleared}")
    print(f"  Confirmed sensitive       : {confirmed}")
    print(f"  LLM unavailable (skipped) : {failed}")
    if dry_run:
        print("  [DRY RUN — no DB changes]")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Classify but don't write to DB")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    await run(dry_run=args.dry_run)


if __name__ == "__main__":
    asyncio.run(main())
