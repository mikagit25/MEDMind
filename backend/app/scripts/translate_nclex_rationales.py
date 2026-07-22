"""G2.1 — Translate NCLEX rationales, explanations, key_takeaway, test_taking_tip to Spanish.

Idempotent: skips questions that already have rationales_es.
Prioritises questions with highest session view counts (most-seen first).
Uses Cerebras keys (separate rate pool from Groq enrichment pipeline).

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


class CerebrasClient:
    def __init__(self):
        self._reset_at: dict[str, float] = {k: 0.0 for k in CEREBRAS_KEYS}

    def _best_key(self) -> str:
        return min(CEREBRAS_KEYS, key=lambda k: self._reset_at[k])

    def mark_limited(self, key: str, reset_in: float) -> None:
        self._reset_at[key] = time.time() + reset_in

    async def call(self, prompt: str, max_wait: int = 3600) -> str | None:
        while True:
            key = self._best_key()
            wait = self._reset_at[key] - time.time()
            if wait > max_wait:
                print(f"  ⚠ All Cerebras keys limited >{max_wait//60}min. Exiting — cron will retry.")
                return None
            if wait > 0:
                print(f"  Waiting {wait:.0f}s for Cerebras key rotation…")
                await asyncio.sleep(wait + 1)
            try:
                async with httpx.AsyncClient(timeout=90) as client:
                    resp = await client.post(
                        CEREBRAS_URL,
                        headers={"Authorization": f"Bearer {key}", "content-type": "application/json"},
                        json={"model": CEREBRAS_MODEL,
                              "messages": [{"role": "user", "content": prompt}],
                              "max_tokens": 4096},
                    )
                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("retry-after", "60"))
                    idx = CEREBRAS_KEYS.index(key) + 1
                    print(f"  Cerebras key {idx}/{len(CEREBRAS_KEYS)} limited {retry_after:.0f}s")
                    self.mark_limited(key, retry_after)
                    continue
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
            except Exception as e:
                print(f"  Error: {e}")
                await asyncio.sleep(3)


async def run(max_questions: int | None = None, dry_run: bool = False) -> None:
    if not CEREBRAS_KEYS:
        print("ERROR: No Cerebras keys configured")
        sys.exit(1)

    client = CerebrasClient()

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
