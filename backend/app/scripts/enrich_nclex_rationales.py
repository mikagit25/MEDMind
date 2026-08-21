"""Enrich existing NCLEX questions with rationales, key_takeaway, test_taking_tip.

All 1185 questions in DB were generated with explanation+options but rationales=NULL.
This script generates the missing fields using a multi-provider key pool.

Provider priority (rotates on rate-limit):
  Groq pool  — KEY_1/KEY_2/KEY_6 (user tutor, free when no users online)
               + KEY_3/MODULE/MODULE_2/CASES/VET_MODULES (content pipeline)
  Gemini pool — GEMINI_API_KEY_1 through _5 (free tier, 5-key rotation)

Keys NOT used: GROQ_API_KEY_4 (vet articles), GROQ_KEY_VET_ARTICLES (articles).

Usage:
  python -m app.scripts.enrich_nclex_rationales              # all missing
  python -m app.scripts.enrich_nclex_rationales --max 200   # limit per run
  python -m app.scripts.enrich_nclex_rationales --dry-run   # preview only
  python -m app.scripts.enrich_nclex_rationales --type mcq  # only MCQ questions
"""

from __future__ import annotations

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

# ── Provider key pools ────────────────────────────────────────────────────────

def _dedup(keys: list[str]) -> list[str]:
    seen: set[str] = set()
    return [k for k in keys if k and not (k in seen or seen.add(k))]  # type: ignore[func-returns-value]

GROQ_KEYS = _dedup([
    # Content pipeline pool — KEY_4 reserved for articles, KEY_5 for news
    os.getenv("GROQ_API_KEY_3", ""),
    os.getenv("GROQ_API_KEY_6", ""),
    os.getenv("GROQ_KEY_MODULE", ""),
    os.getenv("GROQ_KEY_MODULE_2", ""),
    os.getenv("GROQ_KEY_CASES", ""),
    os.getenv("GROQ_KEY_VET_MODULES", ""),
    # NOT included: KEY_1/KEY_2 (user tutor), KEY_4 (articles), KEY_5 (news), VET_ARTICLES
])

GEMINI_KEYS = _dedup([
    os.getenv("GEMINI_API_KEY", ""),
    os.getenv("GEMINI_API_KEY_2", ""),
    os.getenv("GEMINI_API_KEY_3", ""),
    os.getenv("GEMINI_API_KEY_4", ""),
    os.getenv("GEMINI_API_KEY_5", ""),
])

CEREBRAS_KEYS = _dedup([
    os.getenv("CEREBRAS_API_KEY", ""),
    os.getenv("CEREBRAS_API_KEY_2", ""),
    os.getenv("CEREBRAS_API_KEY_3", ""),
    os.getenv("CEREBRAS_API_KEY_4", ""),
    os.getenv("CEREBRAS_API_KEY_5", ""),
])

GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_URL   = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
CEREBRAS_URL   = "https://api.cerebras.ai/v1/chat/completions"
CEREBRAS_MODEL = "gpt-oss-120b"

BATCH_SIZE = 3    # questions per LLM call (rationale prompts are long)
MAX_TOKENS = 4000


# ── Prompt builders ───────────────────────────────────────────────────────────

def _build_prompt_mcq(batch: list[dict]) -> str:
    """Prompt for MCQ and SATA questions — full per-option rationales."""
    items_json = json.dumps(batch, ensure_ascii=False, indent=2)
    return f"""You are an expert NCLEX question writer. For each question below, generate:
1. "rationales" — a JSON object keyed by option letter, each with "text" (clinical reasoning) and "why" ("correct" or "incorrect")
2. "key_takeaway" — ONE sentence summarizing the core nursing principle
3. "test_taking_tip" — ONE sentence tip for eliminating distractors on the NCLEX

Rules:
- Use the provided "explanation" to determine which option(s) are correct
- "why" values MUST be exactly "correct" or "incorrect" (lowercase English only)
- For SATA questions, multiple options have "why": "correct"
- Clinical reasoning must be specific, not generic
- key_takeaway and test_taking_tip must be complete sentences under 30 words each

Input (JSON array):
{items_json}

Return ONLY a valid JSON array with exactly {len(batch)} objects, each with fields:
  "id", "rationales", "key_takeaway", "test_taking_tip"

No markdown, no code fences, no extra text. Return raw JSON array only."""


def _build_prompt_other(batch: list[dict]) -> str:
    """Prompt for ordered/calculation questions — only key_takeaway + test_taking_tip."""
    items_json = json.dumps(batch, ensure_ascii=False, indent=2)
    return f"""You are an expert NCLEX question writer. For each question below, generate:
1. "key_takeaway" — ONE sentence summarizing the core nursing principle tested
2. "test_taking_tip" — ONE sentence clinical reasoning tip for this type of question

Rules:
- key_takeaway and test_taking_tip must be complete sentences under 30 words each
- Use the provided "explanation" as context

Input (JSON array):
{items_json}

Return ONLY a valid JSON array with exactly {len(batch)} objects, each with fields:
  "id", "key_takeaway", "test_taking_tip"

No markdown, no code fences, no extra text. Return raw JSON array only."""


# ── Response parser ───────────────────────────────────────────────────────────

def _parse(raw: str, expected: int) -> list[dict] | None:
    raw = raw.strip()
    # Strip markdown code fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        return None
    try:
        parsed = json.loads(match.group())
        return parsed if isinstance(parsed, list) and len(parsed) == expected else None
    except json.JSONDecodeError:
        return None


# ── Multi-provider client ─────────────────────────────────────────────────────

class MultiProviderClient:
    def __init__(self) -> None:
        # reset_at[key] = epoch when key becomes available again
        self._groq_reset: dict[str, float] = {k: 0.0 for k in GROQ_KEYS}
        self._gemini_reset: dict[str, float] = {k: 0.0 for k in GEMINI_KEYS}
        self._cerebras_reset: dict[str, float] = {k: 0.0 for k in CEREBRAS_KEYS}

    # ── Groq ──────────────────────────────────────────────────────────────────

    def _best_groq(self) -> str | None:
        if not GROQ_KEYS:
            return None
        return min(GROQ_KEYS, key=lambda k: self._groq_reset[k])

    def _best_gemini(self) -> str | None:
        if not GEMINI_KEYS:
            return None
        return min(GEMINI_KEYS, key=lambda k: self._gemini_reset[k])

    def _best_cerebras(self) -> str | None:
        if not CEREBRAS_KEYS:
            return None
        return min(CEREBRAS_KEYS, key=lambda k: self._cerebras_reset[k])

    async def _call_groq(self, prompt: str, key: str) -> str | None:
        try:
            async with httpx.AsyncClient(timeout=60) as c:
                resp = await c.post(
                    GROQ_URL,
                    headers={"Authorization": f"Bearer {key}"},
                    json={
                        "model": GROQ_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": MAX_TOKENS,
                        "temperature": 0.3,
                    },
                )
            if resp.status_code == 429:
                try:
                    msg = resp.json()["error"]["message"]
                    wait = float(re.search(r"in ([\d.]+)s", msg).group(1))  # type: ignore
                except Exception:
                    wait = 60.0
                self._groq_reset[key] = time.time() + wait
                idx = GROQ_KEYS.index(key) + 1
                print(f"    Groq key {idx}/{len(GROQ_KEYS)} rate-limited {wait:.0f}s")
                return None
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"    Groq error: {e}")
            return None

    async def _call_cerebras(self, prompt: str, key: str) -> str | None:
        try:
            async with httpx.AsyncClient(timeout=60) as c:
                resp = await c.post(
                    CEREBRAS_URL,
                    headers={"Authorization": f"Bearer {key}"},
                    json={
                        "model": CEREBRAS_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": MAX_TOKENS,
                        "temperature": 0.3,
                    },
                )
            if resp.status_code == 429:
                self._cerebras_reset[key] = time.time() + 60.0
                idx = CEREBRAS_KEYS.index(key) + 1
                print(f"    Cerebras key {idx}/{len(CEREBRAS_KEYS)} rate-limited 60s")
                return None
            if resp.status_code == 402:
                self._cerebras_reset[key] = time.time() + 86400.0
                idx = CEREBRAS_KEYS.index(key) + 1
                print(f"    Cerebras key {idx}/{len(CEREBRAS_KEYS)} payment required — skipping for 24h")
                return None
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"    Cerebras error: {e}")
            return None

    async def _call_gemini(self, prompt: str, key: str) -> str | None:
        try:
            async with httpx.AsyncClient(timeout=60) as c:
                resp = await c.post(
                    f"{GEMINI_URL}?key={key}",
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "temperature": 0.3,
                            "maxOutputTokens": MAX_TOKENS,
                        },
                    },
                )
            if resp.status_code == 429:
                self._gemini_reset[key] = time.time() + 65.0
                idx = GEMINI_KEYS.index(key) + 1
                print(f"    Gemini key {idx}/{len(GEMINI_KEYS)} rate-limited 65s")
                return None
            resp.raise_for_status()
            candidates = resp.json().get("candidates", [])
            if not candidates:
                return None
            parts = candidates[0].get("content", {}).get("parts", [])
            return parts[0].get("text") if parts else None
        except Exception as e:
            print(f"    Gemini error: {e}")
            return None

    async def call(self, prompt: str, max_wait: int = 90) -> str | None:
        """Try Groq → Cerebras → Gemini pools. Returns None if all exhausted."""
        total_keys = len(GROQ_KEYS) + len(CEREBRAS_KEYS) + len(GEMINI_KEYS)
        if total_keys == 0:
            print("ERROR: No API keys configured.")
            return None

        attempts = total_keys * 3

        for _ in range(attempts):
            groq_key     = self._best_groq()
            cerebras_key = self._best_cerebras()
            gemini_key   = self._best_gemini()

            groq_wait     = (self._groq_reset.get(groq_key, 0)     - time.time()) if groq_key     else float("inf")
            cerebras_wait = (self._cerebras_reset.get(cerebras_key, 0) - time.time()) if cerebras_key else float("inf")
            gemini_wait   = (self._gemini_reset.get(gemini_key, 0)   - time.time()) if gemini_key   else float("inf")

            # Pick the soonest-available provider
            if groq_key and groq_wait <= 0:
                result = await self._call_groq(prompt, groq_key)
                if result is not None:
                    return result
                continue

            if cerebras_key and cerebras_wait <= 0:
                result = await self._call_cerebras(prompt, cerebras_key)
                if result is not None:
                    return result
                continue

            if gemini_key and gemini_wait <= 0:
                result = await self._call_gemini(prompt, gemini_key)
                if result is not None:
                    return result
                continue

            # All keys rate-limited — wait for the soonest one
            soonest_wait = min(groq_wait, cerebras_wait, gemini_wait)
            if soonest_wait > max_wait:
                print(f"  All {total_keys} keys limited >{max_wait}s — stopping this run.")
                return None
            if soonest_wait > 0:
                print(f"  Waiting {soonest_wait:.0f}s for next available key…")
                await asyncio.sleep(soonest_wait + 1)

        return None


# ── Main logic ────────────────────────────────────────────────────────────────

async def run(
    max_questions: int | None = None,
    dry_run: bool = False,
    only_type: str | None = None,
) -> None:
    total_keys = len(GROQ_KEYS) + len(CEREBRAS_KEYS) + len(GEMINI_KEYS)
    print(f"Keys: {len(GROQ_KEYS)} Groq + {len(CEREBRAS_KEYS)} Cerebras + {len(GEMINI_KEYS)} Gemini = {total_keys} total")
    if total_keys == 0:
        print("ERROR: No API keys configured — set at least one GROQ_API_KEY, CEREBRAS_API_KEY, or GEMINI_API_KEY")
        sys.exit(1)

    client = MultiProviderClient()

    async with AsyncSessionLocal() as db:
        q = select(MCQQuestion).where(
            MCQQuestion.question.isnot(None),
            MCQQuestion.options.isnot(None),
            MCQQuestion.rationales.is_(None),
            MCQQuestion.key_takeaway.is_(None),
        )
        if only_type:
            q = q.where(MCQQuestion.question_type == only_type)
        if max_questions:
            q = q.limit(max_questions * 2)

        result = await db.execute(q)
        questions = result.scalars().all()

        if max_questions:
            questions = questions[:max_questions]

        total = len(questions)
        print(f"Found {total} questions to enrich" + (f" (type={only_type})" if only_type else ""))

        if dry_run:
            print("[DRY RUN] No writes.")
            by_type: dict[str, int] = {}
            for q_obj in questions[:10]:
                t = q_obj.question_type or "mcq"
                by_type[t] = by_type.get(t, 0) + 1
                print(f"  Would enrich [{t}]: {str(q_obj.id)[:8]}… — {(q_obj.question or '')[:60]}")
            print(f"  (showing first 10 of {total})")
            return

        enriched = 0
        failed   = 0

        for i in range(0, total, BATCH_SIZE):
            batch_qs = questions[i:i + BATCH_SIZE]

            # Split by type: MCQ/SATA get full rationales; ordered/calculation get only key_takeaway
            mcq_batch  = [q for q in batch_qs if q.question_type in ("mcq", "sata", None)]
            other_batch = [q for q in batch_qs if q.question_type in ("ordered", "calculation")]

            batch_num = i // BATCH_SIZE + 1
            total_batches = (total + BATCH_SIZE - 1) // BATCH_SIZE

            for sub_batch, is_mcq in [(mcq_batch, True), (other_batch, False)]:
                if not sub_batch:
                    continue

                print(f"  Batch {batch_num}/{total_batches}"
                      f" ({'MCQ/SATA' if is_mcq else 'ordered/calc'},"
                      f" {len(sub_batch)} questions)…")

                input_items = [
                    {
                        "id": str(q.id),
                        "question": q.question or "",
                        "options": q.options or {},
                        "explanation": q.explanation or "",
                        "question_type": q.question_type or "mcq",
                    }
                    for q in sub_batch
                ]

                prompt = _build_prompt_mcq(input_items) if is_mcq else _build_prompt_other(input_items)
                raw = await client.call(prompt)

                if raw is None:
                    print(f"    All keys exhausted — stopping.")
                    print(f"\nDone — enriched: {enriched} | failed/skipped: {failed} | remaining: {total - enriched - failed}")
                    await db.commit()
                    return

                parsed = _parse(raw, len(sub_batch))
                if not parsed:
                    print(f"    Parse error (got {len(parsed) if parsed else 0} items, expected {len(sub_batch)}) — skipping")
                    failed += len(sub_batch)
                    continue

                by_id = {item["id"]: item for item in parsed}
                for q_obj in sub_batch:
                    item = by_id.get(str(q_obj.id))
                    if not item:
                        failed += 1
                        continue

                    if is_mcq:
                        rationales = item.get("rationales")
                        # Validate rationale structure
                        if isinstance(rationales, dict) and rationales:
                            q_obj.rationales = rationales
                        # Always save key_takeaway and test_taking_tip
                    q_obj.key_takeaway    = item.get("key_takeaway") or None
                    q_obj.test_taking_tip = item.get("test_taking_tip") or None
                    enriched += 1

                await db.commit()
                print(f"    ✓ {enriched} enriched so far")

            await asyncio.sleep(0.3)

        print(f"\nDone — enriched: {enriched} | failed/skipped: {failed} | remaining: {total - enriched - failed}")


def main() -> None:
    dry_run    = "--dry-run" in sys.argv
    only_type  = None
    max_q      = None

    if "--type" in sys.argv:
        idx = sys.argv.index("--type")
        if idx + 1 < len(sys.argv):
            only_type = sys.argv[idx + 1]

    if "--max" in sys.argv:
        idx = sys.argv.index("--max")
        if idx + 1 < len(sys.argv):
            max_q = int(sys.argv[idx + 1])

    asyncio.run(run(max_questions=max_q, dry_run=dry_run, only_type=only_type))


if __name__ == "__main__":
    main()
