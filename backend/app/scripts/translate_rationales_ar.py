"""Translate Gulf exam question rationales, explanations, key_takeaway to Arabic.

Idempotent: skips questions that already have explanation_ar.
Targets Gulf exam questions only (exam_slugs IS NOT NULL).
Uses Groq content pipeline keys (KEY_3/KEY_6/MODULE_2/CASES/VET_MODULES).

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

_GROQ_KEYS = _dedup([
    os.getenv("GROQ_API_KEY_3", ""),
    os.getenv("GROQ_API_KEY_6", ""),
    os.getenv("GROQ_KEY_MODULE_2", ""),
    os.getenv("GROQ_KEY_CASES", ""),
    os.getenv("GROQ_KEY_VET_MODULES", ""),
])
_CEREBRAS_KEYS = _dedup([
    os.getenv("CEREBRAS_API_KEY", ""),
    os.getenv("CEREBRAS_API_KEY_2", ""),
    os.getenv("CEREBRAS_API_KEY_3", ""),
    os.getenv("CEREBRAS_API_KEY_4", ""),
    os.getenv("CEREBRAS_API_KEY_5", ""),
])

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"

# Unified slot pool: (key, url, model)
ALL_LLM_SLOTS = (
    [(k, GROQ_URL, "llama-3.3-70b-versatile") for k in _GROQ_KEYS] +
    [(k, CEREBRAS_URL, "llama-3.3-70b") for k in _CEREBRAS_KEYS]
)

# Legacy aliases for logging
GROQ_KEYS = [s[0] for s in ALL_LLM_SLOTS]
GROQ_MODEL = "llama-3.3-70b-versatile"
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


class GroqClient:
    def __init__(self):
        self._reset_at: dict[str, float] = {slot[0]: 0.0 for slot in ALL_LLM_SLOTS}

    def _best_slot(self) -> tuple:
        return min(ALL_LLM_SLOTS, key=lambda s: self._reset_at[s[0]])

    def mark_limited(self, key: str, reset_in: float) -> None:
        self._reset_at[key] = time.time() + reset_in

    @staticmethod
    def _parse_retry_after(msg: str) -> float:
        try:
            part = msg.split("in ")[-1].strip()
            m = re.match(r"(?:(\d+)m)?(\d+(?:\.\d+)?)s?", part)
            if m:
                return float(m.group(1) or 0) * 60 + float(m.group(2) or 0)
        except Exception:
            pass
        return 120.0

    async def call(self, prompt: str, max_wait: int = 3600) -> str | None:
        while True:
            key, url, model = self._best_slot()
            wait = self._reset_at[key] - time.time()
            if wait > max_wait:
                print(f"  All {len(ALL_LLM_SLOTS)} LLM slots limited >{max_wait//60}min. Exiting — cron will retry.")
                return None
            if wait > 0:
                provider = "Groq" if "groq" in url else "Cerebras"
                print(f"  Waiting {wait:.0f}s for [{provider}] slot rotation…")
                await asyncio.sleep(wait + 1)
            try:
                async with httpx.AsyncClient(timeout=60) as client:
                    resp = await client.post(
                        url,
                        headers={"Authorization": f"Bearer {key}"},
                        json={"model": model,
                              "messages": [{"role": "user", "content": prompt}],
                              "max_tokens": 4000, "temperature": 0.2},
                    )
                if resp.status_code == 429:
                    retry_after = self._parse_retry_after(
                        resp.json().get("error", {}).get("message", "")
                    )
                    provider = "Groq" if "groq" in url else "Cerebras"
                    idx = ALL_LLM_SLOTS.index((key, url, model)) + 1
                    print(f"  [{provider} slot {idx}/{len(ALL_LLM_SLOTS)}] limited {retry_after:.0f}s")
                    self.mark_limited(key, retry_after)
                    continue
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
            except Exception as e:
                print(f"  Error: {e}")
                await asyncio.sleep(2)


async def run(max_questions: int | None = None, dry_run: bool = False, exam_slug: str | None = None) -> None:
    if not GROQ_KEYS:
        print("ERROR: No Groq content pipeline keys configured")
        sys.exit(1)

    client = GroqClient()

    async with AsyncSessionLocal() as db:
        q = select(MCQQuestion).where(
            MCQQuestion.exam_slugs.isnot(None),
            MCQQuestion.explanation.isnot(None),
            or_(
                MCQQuestion.explanation_ar.is_(None),
                MCQQuestion.key_takeaway_ar.is_(None),
            ),
        )
        if exam_slug:
            q = q.where(MCQQuestion.exam_slugs.op("@>")(f'["{exam_slug}"]'))
        if max_questions:
            q = q.limit(max_questions * 2)

        result = await db.execute(q)
        questions = result.scalars().all()

        untranslated = [q for q in questions if q.explanation_ar is None]
        if max_questions:
            untranslated = untranslated[:max_questions]

        print(f"Found {len(untranslated)} Gulf questions to translate to Arabic"
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
                q.explanation_ar    = item.get("explanation") or None
                q.rationales_ar     = item.get("rationales") or None
                q.key_takeaway_ar   = item.get("key_takeaway") or None
                q.test_taking_tip_ar = item.get("test_taking_tip") or None
                translated += 1

            await db.commit()
            print(f"    ✓ {translated} translated so far")
            await asyncio.sleep(20)

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
