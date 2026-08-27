"""Translate MCQ question rationales, explanations, key_takeaway to Arabic.

Idempotent: skips questions that already have explanation_ar.
Covers three question categories via --type flag:
  gulf   — Gulf exam questions (exam_slugs IS NOT NULL)  [default]
  nclex  — NCLEX questions (nclex_client_needs IS NOT NULL)
  module — specialty module questions (no exam_slugs, no nclex_client_needs)
  all    — all three categories combined

Uses Cerebras keys (separate rate pool from Groq enrichment pipeline).

Usage:
  python -m app.scripts.translate_rationales_ar                    # Gulf only
  python -m app.scripts.translate_rationales_ar --type nclex       # NCLEX
  python -m app.scripts.translate_rationales_ar --type module      # modules
  python -m app.scripts.translate_rationales_ar --type all         # everything
  python -m app.scripts.translate_rationales_ar --max 100          # limit per run
  python -m app.scripts.translate_rationales_ar --dry-run          # preview only
  python -m app.scripts.translate_rationales_ar --slug snle        # one exam (gulf)
"""

import asyncio
import json
import os
import re
import sys
import time

import httpx
from sqlalchemy import select, or_

from app.core.database import AsyncSessionLocal
from app.models.models import MCQQuestion

def _dedup(keys: list) -> list:
    seen: set = set()
    return [k for k in keys if k and not (k in seen or seen.add(k))]

CEREBRAS_KEYS = _dedup([
    os.getenv("CEREBRAS_API_KEY", ""),
    os.getenv("CEREBRAS_API_KEY_2", ""),
    os.getenv("CEREBRAS_API_KEY_3", ""),
    os.getenv("CEREBRAS_API_KEY_4", ""),
    os.getenv("CEREBRAS_API_KEY_5", ""),
])

CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
CEREBRAS_MODEL = "gemma-4-31b"

OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "meta-llama/llama-3.3-70b-instruct"

# Groq: free tier, multiple keys, used as final fallback
GROQ_KEYS = _dedup([
    os.getenv("GROQ_KEY_MODULE", ""),
    os.getenv("GROQ_KEY_MODULE_2", ""),
    os.getenv("GROQ_API_KEY_3", ""),
    os.getenv("GROQ_API_KEY_4", ""),
    os.getenv("GROQ_API_KEY_5", ""),
    os.getenv("GROQ_API_KEY_6", ""),
    os.getenv("GROQ_API_KEY_7", ""),
    os.getenv("GROQ_KEY_CASES", ""),
    os.getenv("GROQ_KEY_VET_ARTICLES", ""),
    os.getenv("GROQ_KEY_VET_MODULES", ""),
])
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "qwen/qwen3.6-27b"

BATCH_SIZE = 5

AR_MEDICAL_GLOSSARY = {
    "NCLEX": "NCLEX",
    "IV": "IV",
    "PRN": "PRN",
    "NPO": "NPO",
    "STAT": "STAT",
    "SBAR": "SBAR",
    "SpO2": "SpO2",
    "ECG": "ECG",
    "ICU": "ICU",
    "ABCs": "ABCs",
}


def _build_translate_prompt(batch: list[dict]) -> str:
    items_str = json.dumps(batch, ensure_ascii=False, indent=2)
    glossary = ", ".join(f"{k}→{v}" for k, v in AR_MEDICAL_GLOSSARY.items())
    return f"""Translate the following Gulf nursing exam question explanations into professional medical Arabic (اللغة العربية الطبية).

Rules:
- Translate all text fields to Modern Standard Arabic (فصحى) with medical terminology
- Preserve JSON structure exactly — same keys, same types
- Keep medical abbreviations as-is: {glossary}
- Use standard Gulf/Middle Eastern medical Arabic terminology
- "correct"/"incorrect" values stay in English (they are code values)
- Maintain clinical precision — do not simplify or omit any detail
- Use RTL-appropriate sentence structure

Input (JSON array of objects with fields: id, explanation, rationales, key_takeaway, test_taking_tip):
{items_str}

Return ONLY a valid JSON array with the same structure but all text translated to Arabic.
No markdown, no commentary, no extra text."""


def _parse_response(raw: str) -> list[dict] | None:
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return None


class TranslationClient:
    """Tries Cerebras → OpenRouter → Groq (multi-key rotation) in order."""

    def __init__(self):
        self._cerebras_reset: dict[str, float] = {k: 0.0 for k in CEREBRAS_KEYS}
        self._cerebras_billing_failed = False
        self._openrouter_billing_failed = False
        # Groq: track per-key TPM/TPD resets
        self._groq_reset: dict[str, float] = {k: 0.0 for k in GROQ_KEYS}

    async def call(self, prompt: str) -> str | None:
        # 1. Try Cerebras
        if CEREBRAS_KEYS and not self._cerebras_billing_failed:
            result = await self._call_cerebras(prompt)
            if result is not None:
                return result

        # 2. Try OpenRouter
        if OPENROUTER_KEY and not self._openrouter_billing_failed:
            result = await self._call_openrouter(prompt)
            if result is not None:
                return result

        # 3. Try Groq (free, multi-key)
        if GROQ_KEYS:
            return await self._call_groq(prompt)

        print("  All providers exhausted — stopping.")
        return None

    async def _call_cerebras(self, prompt: str) -> str | None:
        key = min(self._cerebras_reset, key=lambda k: self._cerebras_reset[k])
        wait = self._cerebras_reset[key] - time.time()
        if wait > 600:
            return None  # all keys long-limited, skip to next provider
        if wait > 0:
            await asyncio.sleep(wait + 1)
        try:
            async with httpx.AsyncClient(timeout=90) as c:
                resp = await c.post(
                    CEREBRAS_URL,
                    headers={"Authorization": f"Bearer {key}", "content-type": "application/json"},
                    json={"model": CEREBRAS_MODEL,
                          "messages": [{"role": "user", "content": prompt}],
                          "max_tokens": 4096},
                )
            if resp.status_code == 402:
                print(f"  Cerebras 402 (billing) — switching to OpenRouter/Groq")
                self._cerebras_billing_failed = True
                return None
            if resp.status_code == 429:
                retry_after = float(resp.headers.get("retry-after", "60"))
                self._cerebras_reset[key] = time.time() + retry_after
                return None
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"  Cerebras error: {e}")
            return None

    async def _call_openrouter(self, prompt: str) -> str | None:
        try:
            async with httpx.AsyncClient(timeout=90) as c:
                resp = await c.post(
                    OPENROUTER_URL,
                    headers={"Authorization": f"Bearer {OPENROUTER_KEY}", "content-type": "application/json"},
                    json={"model": OPENROUTER_MODEL,
                          "messages": [{"role": "user", "content": prompt}],
                          "max_tokens": 4096},
                )
            if resp.status_code == 402:
                print(f"  OpenRouter 402 (billing) — switching to Groq")
                self._openrouter_billing_failed = True
                return None
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"  OpenRouter error: {e}")
            return None

    async def _call_groq(self, prompt: str) -> str | None:
        if not GROQ_KEYS:
            return None
        for attempt in range(len(GROQ_KEYS) * 3):
            # Pick key with earliest reset time
            key = min(GROQ_KEYS, key=lambda k: self._groq_reset.get(k, 0.0))
            wait = self._groq_reset.get(key, 0.0) - time.time()
            idx = GROQ_KEYS.index(key) + 1
            # If the best key resets in >10min — all keys are heavily limited
            if wait > 600:
                print(f"  Groq: all keys limited >{wait/60:.0f}min — stopping (cron will retry)")
                return None
            if wait > 0:
                print(f"  Groq key {idx}/{len(GROQ_KEYS)} TPM {wait:.0f}s — waiting…")
                await asyncio.sleep(wait + 2)
            try:
                async with httpx.AsyncClient(timeout=90) as c:
                    resp = await c.post(
                        GROQ_URL,
                        headers={"Authorization": f"Bearer {key}", "content-type": "application/json"},
                        json={"model": GROQ_MODEL,
                              "messages": [{"role": "user", "content": prompt}],
                              "max_tokens": 4096,
                              "temperature": 0.2,
                              "reasoning_effort": "none"},
                    )
                if resp.status_code == 429:
                    body = resp.text
                    m = re.search(r"in ([\d.]+)s", body)
                    retry = float(m.group(1)) if m else 60
                    if "per day" in body or "TPD" in body or "daily" in body.lower():
                        self._groq_reset[key] = time.time() + 86400
                        print(f"  Groq key {idx}/{len(GROQ_KEYS)} TPD exhausted — rotating")
                    else:
                        self._groq_reset[key] = time.time() + retry + 5
                        print(f"  Groq key {idx}/{len(GROQ_KEYS)} TPM {retry:.0f}s — rotating")
                    continue
                if resp.status_code == 413:
                    self._groq_reset[key] = time.time() + 65
                    continue
                resp.raise_for_status()
                raw = resp.json()["choices"][0]["message"]["content"]
                raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
                return raw
            except Exception as e:
                print(f"  Groq error: {e}")
                return None
        return None


# Keep old name as alias for backward compatibility with cron scripts
CerebrasClient = TranslationClient


async def run(
    max_questions: int | None = None,
    dry_run: bool = False,
    exam_slug: str | None = None,
    qtype: str = "gulf",
) -> None:
    if not CEREBRAS_KEYS and not OPENROUTER_KEY and not GROQ_KEYS:
        print("ERROR: No API keys configured (Cerebras / OpenRouter / Groq)")
        sys.exit(1)

    client = CerebrasClient()

    async with AsyncSessionLocal() as db:
        needs_ar = or_(
            MCQQuestion.explanation_ar.is_(None),
            MCQQuestion.rationales_ar.is_(None),
            MCQQuestion.key_takeaway_ar.is_(None),
        )

        if qtype == "gulf":
            base_filter = [MCQQuestion.exam_slugs.isnot(None)]
            label = "Gulf"
        elif qtype == "nclex":
            base_filter = [MCQQuestion.nclex_client_needs.isnot(None)]
            label = "NCLEX"
        elif qtype == "module":
            base_filter = [
                MCQQuestion.nclex_client_needs.is_(None),
                MCQQuestion.exam_slugs.is_(None),
            ]
            label = "Module"
        else:  # all
            base_filter = []
            label = "All"

        q = select(MCQQuestion).where(
            *base_filter,
            MCQQuestion.explanation.isnot(None),
            needs_ar,
        )
        if exam_slug:
            from sqlalchemy import type_coerce
            from sqlalchemy.dialects.postgresql import JSONB as _JSONB
            q = q.where(MCQQuestion.exam_slugs.op("@>")(type_coerce([exam_slug], _JSONB)))
        if max_questions:
            q = q.limit(max_questions * 2)

        result = await db.execute(q)
        questions = result.scalars().all()

        untranslated = [q for q in questions if q.explanation_ar is None or q.rationales_ar is None]
        if max_questions:
            untranslated = untranslated[:max_questions]

        print(f"Found {len(untranslated)} {label} questions to translate to Arabic (using Cerebras {CEREBRAS_MODEL})"
              + (f" (slug={exam_slug})" if exam_slug else ""))
        if dry_run:
            print("[DRY RUN] No writes.")
            for q in untranslated[:5]:
                print(f"  Would translate: {str(q.id)[:8]}… — {(q.question or '')[:60]}")
            return

        translated = 0
        for i in range(0, len(untranslated), BATCH_SIZE):
            batch_qs = untranslated[i:i + BATCH_SIZE]
            batch_input = [
                {
                    "id": str(q.id),
                    "explanation": q.explanation or "",
                    "rationales": q.rationales or {},
                    "key_takeaway": q.key_takeaway or "",
                    "test_taking_tip": q.test_taking_tip or "",
                }
                for q in batch_qs
            ]

            print(f"  Batch {i//BATCH_SIZE + 1}: translating {len(batch_qs)} questions to Arabic…")
            raw = await client.call(_build_translate_prompt(batch_input))
            if raw is None:
                print("  All keys exhausted — stopping.")
                break

            parsed = _parse_response(raw)
            if not parsed or len(parsed) != len(batch_qs):
                print(f"  Parse error (got {len(parsed) if parsed else 0} items, expected {len(batch_qs)}) — skipping")
                continue

            by_id = {item["id"]: item for item in parsed}
            for q in batch_qs:
                item = by_id.get(str(q.id))
                if not item:
                    continue
                q.explanation_ar     = item.get("explanation") or None
                q.rationales_ar      = item.get("rationales") or None
                q.key_takeaway_ar    = item.get("key_takeaway") or None
                q.test_taking_tip_ar = item.get("test_taking_tip") or None
                translated += 1

            await db.commit()
            print(f"    ✓ {translated} translated so far")
            await asyncio.sleep(5)

        remaining = len(untranslated) - translated
        print(f"\nDone — translated: {translated} | remaining: {remaining}")


def main() -> None:
    max_q = None
    dry_run = "--dry-run" in sys.argv
    exam_slug = None
    qtype = "gulf"
    if "--max" in sys.argv:
        idx = sys.argv.index("--max")
        if idx + 1 < len(sys.argv):
            max_q = int(sys.argv[idx + 1])
    if "--slug" in sys.argv:
        idx = sys.argv.index("--slug")
        if idx + 1 < len(sys.argv):
            exam_slug = sys.argv[idx + 1]
    if "--type" in sys.argv:
        idx = sys.argv.index("--type")
        if idx + 1 < len(sys.argv):
            qtype = sys.argv[idx + 1]
    asyncio.run(run(max_questions=max_q, dry_run=dry_run, exam_slug=exam_slug, qtype=qtype))


if __name__ == "__main__":
    main()
