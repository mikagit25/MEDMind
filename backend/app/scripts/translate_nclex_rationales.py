"""G2.1 — Translate NCLEX rationales, explanations, key_takeaway, test_taking_tip to Spanish.

Idempotent: skips questions that already have rationales_es.
Prioritises questions with highest session view counts (most-seen first).
Falls back through Cerebras → OpenRouter → Groq (multi-key).

Usage:
  python -m app.scripts.translate_nclex_rationales            # all untranslated
  python -m app.scripts.translate_nclex_rationales --max 100  # limit per run
  python -m app.scripts.translate_nclex_rationales --dry-run  # preview, no writes
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

# Spanish medical glossary overrides — critical terms that must NOT be auto-translated
ES_GLOSSARY = {
    "NCLEX": "NCLEX",
    "SBAR": "SBAR",
    "NEWS2": "NEWS2",
    "ABCs": "ABCs",
    "Maslow": "Maslow",
    "CAT": "CAT",
    "IV": "IV",
    "PRN": "PRN",
    "NPO": "NPO",
    "STAT": "STAT",
}


def _build_translate_prompt(batch: list[dict]) -> str:
    items_str = json.dumps(batch, ensure_ascii=False, indent=2)
    glossary = ", ".join(f"{k}→{v}" for k, v in ES_GLOSSARY.items())
    return f"""Translate the following NCLEX nursing question explanations into professional medical Spanish (español médico).

Rules:
- Translate all text fields to Spanish
- Preserve JSON structure exactly — same keys, same types
- Keep medical abbreviations as-is: {glossary}
- "correct"/"incorrect" values stay in English (they are code values)
- Maintain clinical precision — do not simplify or omit any detail
- Natural Latin American medical Spanish (not castellano)

Input (JSON array of objects with fields: id, explanation, rationales, key_takeaway, test_taking_tip):
{items_str}

Return ONLY a valid JSON array with the same structure but all text translated to Spanish.
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
        self._groq_reset: dict[str, float] = {k: 0.0 for k in GROQ_KEYS}

    async def call(self, prompt: str) -> str | None:
        if CEREBRAS_KEYS and not self._cerebras_billing_failed:
            result = await self._call_cerebras(prompt)
            if result is not None:
                return result
        if OPENROUTER_KEY and not self._openrouter_billing_failed:
            result = await self._call_openrouter(prompt)
            if result is not None:
                return result
        if GROQ_KEYS:
            return await self._call_groq(prompt)
        print("  All providers exhausted — stopping.")
        return None

    async def _call_cerebras(self, prompt: str) -> str | None:
        key = min(self._cerebras_reset, key=lambda k: self._cerebras_reset[k])
        wait = self._cerebras_reset[key] - time.time()
        if wait > 600:
            return None
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
            key = min(GROQ_KEYS, key=lambda k: self._groq_reset.get(k, 0.0))
            wait = self._groq_reset.get(key, 0.0) - time.time()
            idx = GROQ_KEYS.index(key) + 1
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


CerebrasClient = TranslationClient


async def run(max_questions: int | None = None, dry_run: bool = False) -> None:
    if not CEREBRAS_KEYS and not OPENROUTER_KEY and not GROQ_KEYS:
        print("ERROR: No API keys configured (Cerebras / OpenRouter / Groq)")
        sys.exit(1)

    client = TranslationClient()

    async with AsyncSessionLocal() as db:
        # Fetch NCLEX questions (not vet) that need Spanish translation.
        # Includes ordered/calculation questions that have key_takeaway but NULL rationales.
        q = select(MCQQuestion).where(
            MCQQuestion.nclex_client_needs.isnot(None),
            or_(
                MCQQuestion.rationales.isnot(None),   # MCQ/SATA with per-option rationales
                MCQQuestion.key_takeaway.isnot(None),  # ordered/calculation with only key_takeaway
            ),
            MCQQuestion.key_takeaway_es.is_(None),
        )
        if max_questions:
            q = q.limit(max_questions * 2)  # fetch extra to account for skips

        result = await db.execute(q)
        questions = result.scalars().all()

        untranslated = [
            q for q in questions
            if q.key_takeaway_es is None
        ]
        if max_questions:
            untranslated = untranslated[:max_questions]

        print(f"Found {len(untranslated)} questions to translate to Spanish (using Cerebras {CEREBRAS_MODEL})")
        if dry_run:
            print("[DRY RUN] No writes will be made.")
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

            print(f"  Batch {i//BATCH_SIZE + 1}: translating {len(batch_qs)} questions…")
            raw = await client.call(_build_translate_prompt(batch_input))
            if raw is None:
                print("  All keys exhausted — stopping.")
                break

            parsed = _parse_response(raw)
            if not parsed or len(parsed) != len(batch_qs):
                print(f"  Parse error (got {len(parsed) if parsed else 0} items, expected {len(batch_qs)}) — skipping batch")
                continue

            by_id = {item["id"]: item for item in parsed}
            for q in batch_qs:
                item = by_id.get(str(q.id))
                if not item:
                    continue
                q.explanation_es     = item.get("explanation") or None
                q.rationales_es      = item.get("rationales") or None
                q.key_takeaway_es    = item.get("key_takeaway") or None
                q.test_taking_tip_es = item.get("test_taking_tip") or None
                translated += 1

            await db.commit()
            print(f"    ✓ {translated} translated so far")
            await asyncio.sleep(5)

        remaining = len(untranslated) - translated
        print(f"\nDone — translated: {translated} | remaining: {remaining}")


def main() -> None:
    max_q = None
    dry_run = "--dry-run" in sys.argv
    if "--max" in sys.argv:
        idx = sys.argv.index("--max")
        if idx + 1 < len(sys.argv):
            max_q = int(sys.argv[idx + 1])
    asyncio.run(run(max_questions=max_q, dry_run=dry_run))


if __name__ == "__main__":
    main()
