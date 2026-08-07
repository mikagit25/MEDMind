"""Translate Gulf exam question rationales, explanations, key_takeaway to Arabic.

Idempotent: skips questions that already have explanation_ar.
Targets Gulf exam questions only (exam_slugs IS NOT NULL).
Uses Cerebras keys (separate rate pool from Groq enrichment pipeline).

Usage:
  python -m app.scripts.translate_rationales_ar            # all untranslated
  python -m app.scripts.translate_rationales_ar --max 100  # limit per run
  python -m app.scripts.translate_rationales_ar --dry-run  # preview only
  python -m app.scripts.translate_rationales_ar --slug snle # only for one exam
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


async def run(max_questions: int | None = None, dry_run: bool = False, exam_slug: str | None = None) -> None:
    if not CEREBRAS_KEYS:
        print("ERROR: No Cerebras keys configured")
        sys.exit(1)

    client = CerebrasClient()

    async with AsyncSessionLocal() as db:
        q = select(MCQQuestion).where(
            MCQQuestion.exam_slugs.isnot(None),
            MCQQuestion.explanation.isnot(None),
            or_(
                MCQQuestion.explanation_ar.is_(None),
                MCQQuestion.rationales_ar.is_(None),
                MCQQuestion.key_takeaway_ar.is_(None),
            ),
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

        print(f"Found {len(untranslated)} Gulf questions to translate to Arabic (using Cerebras {CEREBRAS_MODEL})"
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
    if "--max" in sys.argv:
        idx = sys.argv.index("--max")
        if idx + 1 < len(sys.argv):
            max_q = int(sys.argv[idx + 1])
    if "--slug" in sys.argv:
        idx = sys.argv.index("--slug")
        if idx + 1 < len(sys.argv):
            exam_slug = sys.argv[idx + 1]
    asyncio.run(run(max_questions=max_q, dry_run=dry_run, exam_slug=exam_slug))


if __name__ == "__main__":
    main()
