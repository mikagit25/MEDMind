"""G2.1 — Translate NCLEX rationales, explanations, key_takeaway, test_taking_tip to Spanish.

Idempotent: skips questions that already have rationales_es.
Prioritises questions with highest session view counts (most-seen first).
Uses Groq content pipeline keys (KEY_3/KEY_4/CASES/MODULE_2).

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
from pathlib import Path

import httpx
from sqlalchemy import select, func, or_, text

from app.core.database import AsyncSessionLocal
from app.models.models import MCQQuestion

# Content pipeline keys only — never GROQ_API_KEY / GROQ_API_KEY_2 (user tutor)
GROQ_KEYS = [k for k in [
    os.getenv("GROQ_API_KEY_3", ""),
    os.getenv("GROQ_API_KEY_6", ""),
    os.getenv("GROQ_KEY_MODULE_2", ""),
    os.getenv("GROQ_KEY_CASES", ""),
    os.getenv("GROQ_KEY_VET_MODULES", ""),
    # KEY_4 reserved for articles, KEY_5 for news, KEY_1/KEY_2 for user tutor
] if k]
_seen: set = set()
GROQ_KEYS = [k for k in GROQ_KEYS if not (k in _seen or _seen.add(k))]

GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
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


class GroqClient:
    def __init__(self):
        self._reset_at: dict[str, float] = {k: 0.0 for k in GROQ_KEYS}

    def _best_key(self) -> str:
        return min(GROQ_KEYS, key=lambda k: self._reset_at[k])

    def mark_limited(self, key: str, reset_in: float) -> None:
        self._reset_at[key] = time.time() + reset_in

    @staticmethod
    def _parse_retry_after(msg: str) -> float:
        """Parse Groq retry-after from message like '44m47.04s', '90s', '1m30s'."""
        try:
            part = msg.split("in ")[-1].strip()
            m = re.match(r"(?:(\d+)m)?(\d+(?:\.\d+)?)s?", part)
            if m:
                return float(m.group(1) or 0) * 60 + float(m.group(2) or 0)
        except Exception:
            pass
        return 120.0  # safe default

    async def call(self, prompt: str, max_wait: int = 3600) -> str | None:
        while True:
            key = self._best_key()
            wait = self._reset_at[key] - time.time()
            if wait > max_wait:
                print(f"  ⚠ All keys limited >{max_wait//60}min. Exiting — cron will retry.")
                return None
            if wait > 0:
                print(f"  Waiting {wait:.0f}s for key rotation…")
                await asyncio.sleep(wait + 1)
            try:
                async with httpx.AsyncClient(timeout=60) as client:
                    resp = await client.post(
                        GROQ_URL,
                        headers={"Authorization": f"Bearer {key}"},
                        json={"model": GROQ_MODEL,
                              "messages": [{"role": "user", "content": prompt}],
                              "max_tokens": 4000, "temperature": 0.3},
                    )
                if resp.status_code == 429:
                    retry_after = self._parse_retry_after(
                        resp.json().get("error", {}).get("message", "")
                    )
                    print(f"  Key {GROQ_KEYS.index(key)+1}/{len(GROQ_KEYS)} limited, resets in {retry_after:.0f}s")
                    self.mark_limited(key, retry_after)
                    continue
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
            except Exception as e:
                print(f"  Error: {e}")
                await asyncio.sleep(2)


async def run(max_questions: int | None = None, dry_run: bool = False) -> None:
    if not GROQ_KEYS:
        print("ERROR: No Groq content pipeline keys configured")
        sys.exit(1)

    client = GroqClient()

    async with AsyncSessionLocal() as db:
        # Fetch NCLEX questions (not vet) that have rationales but no Spanish translation yet
        q = select(MCQQuestion).where(
            MCQQuestion.rationales.isnot(None),
            MCQQuestion.nclex_client_needs.isnot(None),
            or_(
                MCQQuestion.rationales_es.is_(None),
                MCQQuestion.key_takeaway_es.is_(None),
            ),
        )
        if max_questions:
            q = q.limit(max_questions * 2)  # fetch extra to account for skips

        result = await db.execute(q)
        questions = result.scalars().all()

        untranslated = [
            q for q in questions
            if q.rationales_es is None
        ]
        if max_questions:
            untranslated = untranslated[:max_questions]

        print(f"Found {len(untranslated)} questions to translate to Spanish")
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

            # Map by id
            by_id = {item["id"]: item for item in parsed}
            for q in batch_qs:
                item = by_id.get(str(q.id))
                if not item:
                    continue
                q.explanation_es    = item.get("explanation") or None
                q.rationales_es     = item.get("rationales") or None
                q.key_takeaway_es   = item.get("key_takeaway") or None
                q.test_taking_tip_es = item.get("test_taking_tip") or None
                translated += 1

            await db.commit()
            print(f"    ✓ {translated} translated so far")
            await asyncio.sleep(20)  # avoid per-minute token limits between batches

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
