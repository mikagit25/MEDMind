"""
Backfill per-option rationales, key_takeaway, and test_taking_tip for existing MCQ questions.

Idempotent: skips questions that already have rationales.
Uses Groq KEY_3/KEY_4 (content pipeline keys) — never user tutor keys.

Usage:
  python -m app.scripts.backfill_rationales              # all questions without rationales
  python -m app.scripts.backfill_rationales --max 50     # limit to 50 questions per run
  python -m app.scripts.backfill_rationales --dry-run    # preview only, no DB writes
"""

import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

import httpx
from sqlalchemy import select, or_

from app.core.database import AsyncSessionLocal
from app.models.models import MCQQuestion

# Content pipeline keys only (never GROQ_API_KEY / GROQ_API_KEY_2 — those are user tutor)
GROQ_KEYS = [k for k in [
    os.getenv("GROQ_KEY_MODULE_2", ""),
    os.getenv("GROQ_KEY_CASES", ""),
    os.getenv("GROQ_KEY_VET_MODULES", ""),
    os.getenv("GROQ_API_KEY_3", ""),
] if k]
_seen: set = set()
GROQ_KEYS = [k for k in GROQ_KEYS if not (k in _seen or _seen.add(k))]

GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
BATCH_SIZE = 5  # questions per Groq call


def build_prompt(questions: list[dict]) -> str:
    items = []
    for i, q in enumerate(questions):
        opts = "\n".join(f"  {k}: {v}" for k, v in (q.get("options") or {}).items())
        items.append(
            f"### Question {i+1} (ID: {q['id']}, type: {q['question_type']})\n"
            f"{q['question']}\n\nOptions:\n{opts}\n"
            f"Correct: {q.get('correct') or q.get('correct_answers') or q.get('correct_order')}\n"
            f"Existing explanation: {(q.get('explanation') or '')[:300]}"
        )

    questions_block = "\n\n".join(items)

    return f"""You are an expert NCLEX-RN nursing educator. For each question below, generate:
1. Per-option rationales explaining WHY each option is correct or incorrect (use nursing priority logic: ABC, Maslow, nursing process)
2. A key_takeaway: one sentence summarizing the core nursing principle
3. A test_taking_tip: one sentence on how to eliminate wrong options on the NCLEX

Return ONLY a valid JSON array (one object per question, in the same order). No markdown, no extra text.

Format for each item:
{{
  "id": "<question ID as given>",
  "rationales": {{
    "A": {{"text": "...", "why": "correct" or "incorrect"}},
    "B": {{"text": "...", "why": "correct" or "incorrect"}},
    ...
  }},
  "key_takeaway": "...",
  "test_taking_tip": "..."
}}

Questions:

{questions_block}
"""


async def call_groq(prompt: str, reset_at: dict[str, float]) -> str:
    """Call Groq with key rotation. Returns raw text response."""
    for _attempt in range(len(GROQ_KEYS) * 3):
        now = time.time()
        key = min(GROQ_KEYS, key=lambda k: reset_at[k])
        wait = max(0.0, reset_at[key] - now)
        if wait > 120:
            raise RuntimeError(f"All keys rate-limited for >{wait:.0f}s. Exiting — retry later.")
        if wait > 0:
            print(f"  Sleeping {wait:.0f}s for rate-limit reset...")
            await asyncio.sleep(wait)

        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": GROQ_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 4000,
                    "temperature": 0.3,
                },
            )

        if resp.status_code == 429:
            retry_after = float(resp.headers.get("retry-after", "62")) + 1.0
            reset_at[key] = time.time() + retry_after
            print(f"  Key rate-limited, retry in {retry_after:.0f}s")
            continue
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    raise RuntimeError("Exhausted all retry attempts")


def parse_response(text: str) -> list[dict]:
    # Strip any markdown code fences
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()
    return json.loads(text)


async def backfill(max_questions: int | None, dry_run: bool):
    if not GROQ_KEYS:
        print("ERROR: No Groq content pipeline keys configured.")
        sys.exit(1)

    print(f"Groq keys available: {len(GROQ_KEYS)}")
    reset_at: dict[str, float] = {k: 0.0 for k in GROQ_KEYS}

    async with AsyncSessionLocal() as db:
        q = (
            select(MCQQuestion)
            .where(
                MCQQuestion.rationales.is_(None),
                MCQQuestion.question_type.in_(["mcq", "sata", "ordered"]),
            )
            .order_by(MCQQuestion.created_at)
        )
        if max_questions:
            q = q.limit(max_questions)

        result = await db.execute(q)
        questions = result.scalars().all()

    total = len(questions)
    print(f"Questions needing rationales: {total}")
    if total == 0:
        print("Nothing to backfill.")
        return

    if dry_run:
        print("DRY RUN — no DB writes.")
        for mq in questions[:5]:
            print(f"  Would process: {str(mq.id)[:8]}... {mq.question[:60]}")
        return

    updated = 0
    failed = 0

    for batch_start in range(0, total, BATCH_SIZE):
        batch = questions[batch_start : batch_start + BATCH_SIZE]
        print(f"\nBatch {batch_start // BATCH_SIZE + 1}: questions {batch_start+1}–{batch_start+len(batch)}/{total}")

        batch_data = [
            {
                "id": str(mq.id),
                "question": mq.question,
                "options": mq.options or {},
                "question_type": mq.question_type,
                "correct": mq.correct,
                "correct_answers": mq.correct_answers,
                "correct_order": mq.correct_order,
                "explanation": mq.explanation,
            }
            for mq in batch
        ]

        try:
            prompt = build_prompt(batch_data)
            raw = await call_groq(prompt, reset_at)
            results = parse_response(raw)
        except Exception as e:
            print(f"  ERROR generating batch: {e}")
            failed += len(batch)
            continue

        # Map by ID for robust matching
        result_map = {r["id"]: r for r in results if "id" in r}

        async with AsyncSessionLocal() as db:
            for mq in batch:
                sid = str(mq.id)
                r = result_map.get(sid)
                if not r:
                    print(f"  WARN: no result for {sid[:8]}...")
                    failed += 1
                    continue

                row = await db.get(MCQQuestion, mq.id)
                if row is None:
                    failed += 1
                    continue

                row.rationales = r.get("rationales")
                row.key_takeaway = r.get("key_takeaway")
                row.test_taking_tip = r.get("test_taking_tip")
                updated += 1
                print(f"  ✓ {sid[:8]}... key_takeaway: {(r.get('key_takeaway') or '')[:60]}")

            await db.commit()

        # Brief pause between batches to avoid rate limits
        await asyncio.sleep(2)

    print(f"\n{'='*40}")
    print(f"  Updated:  {updated}")
    print(f"  Failed:   {failed}")
    print(f"  Total:    {total}")
    print(f"{'='*40}")


async def main():
    args = sys.argv[1:]
    max_q = None
    dry_run = False

    i = 0
    while i < len(args):
        if args[i] == "--max" and i + 1 < len(args):
            max_q = int(args[i + 1])
            i += 2
        elif args[i] == "--dry-run":
            dry_run = True
            i += 1
        else:
            i += 1

    await backfill(max_q, dry_run)


if __name__ == "__main__":
    asyncio.run(main())
