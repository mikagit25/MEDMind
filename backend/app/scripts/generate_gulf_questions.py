"""G1.2 — Gulf Nursing Licensing Exam Question Generator.

Generates questions for Gulf Prometric exams (SNLE, DHA, QCHP, OMSB, NHRA,
MOH-UAE, HAAD) using the same Groq pipeline as NCLEX generation.
Target: 300 questions per exam slug.

Usage:
  python -m app.scripts.generate_gulf_questions            # check status
  python -m app.scripts.generate_gulf_questions --next     # generate next batch
  python -m app.scripts.generate_gulf_questions --slug dha # specific exam
"""

import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

import httpx

# ── Config ────────────────────────────────────────────────────────────────────
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

OUTPUT_DIR = Path("/tmp/gulf_qbank")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TRACKING_FILE = Path("/app/data/modules/gulf_qbank_progress.json") if \
    Path("/app/data/modules").exists() else Path("/tmp/gulf_qbank_progress.json")

TARGET_PER_EXAM = 300
BATCH_SIZE = 15

GULF_EXAM_TOPICS = [
    {
        "topic": "Fundamentals of Nursing",
        "category": "fundamentals_nursing",
        "subtopics": ["vital signs", "patient positioning", "wound care", "sterile technique",
                      "nursing process", "documentation", "infection control", "fall prevention"],
    },
    {
        "topic": "Medical-Surgical Nursing",
        "category": "medical_surgical",
        "subtopics": ["cardiovascular disorders", "respiratory conditions", "gastrointestinal nursing",
                      "endocrine disorders", "neurological nursing", "musculoskeletal care",
                      "renal conditions", "pre/post-operative care"],
    },
    {
        "topic": "Pharmacology for Nurses",
        "category": "pharmacology",
        "subtopics": ["medication administration", "drug calculations", "antibiotics",
                      "cardiovascular drugs", "analgesics", "insulin management",
                      "high-alert medications", "drug interactions"],
    },
    {
        "topic": "Maternal and Newborn Nursing",
        "category": "maternal_newborn",
        "subtopics": ["prenatal care", "labor and delivery", "postpartum care",
                      "newborn assessment", "breastfeeding", "obstetric complications"],
    },
    {
        "topic": "Pediatric Nursing",
        "category": "pediatrics",
        "subtopics": ["growth and development", "pediatric assessment", "immunizations",
                      "common childhood illnesses", "pediatric medication dosing"],
    },
    {
        "topic": "Mental Health Nursing",
        "category": "mental_health",
        "subtopics": ["therapeutic communication", "psychiatric disorders", "crisis intervention",
                      "psychotropic medications", "de-escalation techniques"],
    },
    {
        "topic": "Community and Public Health Nursing",
        "category": "community_public_health",
        "subtopics": ["health promotion", "disease prevention", "epidemiology basics",
                      "community health assessment", "vaccination programs"],
    },
    {
        "topic": "Nursing Leadership and Management",
        "category": "leadership_management",
        "subtopics": ["delegation", "prioritization", "patient safety", "quality improvement",
                      "scope of practice", "ethical and legal issues"],
    },
]


def _load_progress() -> dict:
    if TRACKING_FILE.exists():
        with open(TRACKING_FILE) as f:
            return json.load(f)
    return {}


def _save_progress(progress: dict) -> None:
    TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TRACKING_FILE, "w") as f:
        json.dump(progress, f, indent=2)


def _count_existing(slug: str) -> int:
    """Count questions already in the output file for this slug."""
    out = OUTPUT_DIR / f"gulf_qbank_{slug}.json"
    if not out.exists():
        return 0
    with open(out) as f:
        return len(json.load(f))


class RateLimiter:
    def __init__(self):
        self._reset_at: dict[str, float] = {k: 0.0 for k in GROQ_KEYS}

    def _best_key(self) -> str:
        return min(GROQ_KEYS, key=lambda k: self._reset_at[k])

    def mark_limited(self, key: str, reset_in: float) -> None:
        self._reset_at[key] = time.time() + reset_in

    async def generate(self, prompt: str, max_tokens: int = 3000, max_wait: int = 90) -> str | None:
        for attempt in range(len(GROQ_KEYS) * 4):
            key = self._best_key()
            wait = self._reset_at[key] - time.time()
            if wait > max_wait:
                print(f"  ⚠ All {len(GROQ_KEYS)} keys limited >{max_wait}s. Exiting — cron will retry.")
                return None
            if wait > 0:
                await asyncio.sleep(wait + 1)
            try:
                async with httpx.AsyncClient(timeout=60) as client:
                    resp = await client.post(
                        GROQ_URL,
                        headers={"Authorization": f"Bearer {key}"},
                        json={"model": GROQ_MODEL, "messages": [{"role": "user", "content": prompt}],
                              "max_tokens": max_tokens, "temperature": 0.7},
                    )
                if resp.status_code == 429:
                    try:
                        retry_after = float(resp.json()["error"]["message"].split("in ")[-1].split("s")[0])
                    except Exception:
                        retry_after = 60.0
                    print(f"  Key {GROQ_KEYS.index(key)+1}/{len(GROQ_KEYS)} limited, resets in {retry_after:.0f}s — switching")
                    self.mark_limited(key, retry_after)
                    continue
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
            except Exception as e:
                print(f"  Error: {e}")
                await asyncio.sleep(2)
        return None


def _build_prompt(exam_slug: str, topic: dict, n: int) -> str:
    subtopics = ", ".join(topic["subtopics"][:4])
    return f"""You are a Gulf nursing exam question writer. Generate exactly {n} original MCQ questions
for the {exam_slug.upper()} nursing licensing exam (Prometric format, 4 options A-D).

Topic: {topic['topic']}
Subtopics to cover: {subtopics}
Category: {topic['category']}

STRICT RULES:
- Each question must test clinical nursing judgment — NOT recall of isolated facts
- Questions must be scenario-based (describe a patient situation)
- Wrong options must be plausible (common misconceptions or partially correct)
- NO recalled or verbatim questions from any official bank
- Appropriate for a registered nurse licensing exam

Return ONLY valid JSON array:
[
  {{
    "question": "A nurse is caring for...",
    "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
    "correct": "B",
    "explanation": "B is correct because... A is wrong because... C is wrong because... D is wrong because...",
    "rationales": {{
      "A": {{"text": "why A is wrong", "why": "incorrect"}},
      "B": {{"text": "why B is correct", "why": "correct"}},
      "C": {{"text": "why C is wrong", "why": "incorrect"}},
      "D": {{"text": "why D is wrong", "why": "incorrect"}}
    }},
    "key_takeaway": "The key nursing principle here is...",
    "nclex_client_needs": "{topic['category']}",
    "difficulty": "medium",
    "tags": ["{exam_slug}", "{topic['category']}"]
  }}
]"""


def _parse_questions(raw: str) -> list[dict]:
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        return []
    try:
        qs = json.loads(match.group())
        return [q for q in qs if isinstance(q, dict) and "question" in q and "correct" in q]
    except json.JSONDecodeError:
        return []


async def generate_for_slug(slug: str) -> int:
    limiter = RateLimiter()
    existing = _count_existing(slug)
    needed = max(0, TARGET_PER_EXAM - existing)
    if needed == 0:
        print(f"  {slug}: already at {existing}/{TARGET_PER_EXAM} — skipping")
        return 0

    print(f"\n{'='*60}")
    print(f"  Generating for {slug.upper()}: {existing}/{TARGET_PER_EXAM} — need {needed} more")
    print(f"{'='*60}")

    out_file = OUTPUT_DIR / f"gulf_qbank_{slug}.json"
    all_questions: list[dict] = []
    if out_file.exists():
        with open(out_file) as f:
            all_questions = json.load(f)

    generated = 0
    for topic in GULF_EXAM_TOPICS:
        if generated >= needed:
            break
        batch = min(BATCH_SIZE, needed - generated)
        print(f"  → {topic['topic']} ({batch} questions)...")
        prompt = _build_prompt(slug, topic, batch)
        raw = await limiter.generate(prompt)
        if raw is None:
            break
        qs = _parse_questions(raw)
        for q in qs:
            q["exam_slugs"] = [slug]
        all_questions.extend(qs)
        generated += len(qs)
        print(f"    ✓ {len(qs)} generated (total {len(all_questions)})")
        await asyncio.sleep(1)

    with open(out_file, "w") as f:
        json.dump(all_questions, f, indent=2, ensure_ascii=False)

    return generated


async def main() -> None:
    from app.data.exam_registry import GULF_EXAMS
    gulf_slugs = [e["slug"] for e in GULF_EXAMS]

    target_slug: str | None = None
    if "--slug" in sys.argv:
        idx = sys.argv.index("--slug")
        if idx + 1 < len(sys.argv):
            target_slug = sys.argv[idx + 1]

    run_next = "--next" in sys.argv

    if not run_next and not target_slug:
        # Status report
        print("\nGulf question bank status:")
        for slug in gulf_slugs:
            count = _count_existing(slug)
            status = "✓" if count >= TARGET_PER_EXAM else f"{count}/{TARGET_PER_EXAM}"
            print(f"  {slug:<12} {status}")
        return

    if target_slug:
        total = await generate_for_slug(target_slug)
        print(f"\nDone: {total} questions generated for {target_slug}")
        return

    # --next: pick first slug under target
    for slug in gulf_slugs:
        if _count_existing(slug) < TARGET_PER_EXAM:
            total = await generate_for_slug(slug)
            print(f"\nDone: {total} questions generated for {slug}")
            remaining = sum(1 for s in gulf_slugs if _count_existing(s) < TARGET_PER_EXAM)
            print(f"Remaining slugs below target: {remaining}")
            return

    print("All Gulf exam slugs at target! Run import_gulf_questions when ready.")


if __name__ == "__main__":
    if not GROQ_KEYS:
        print("ERROR: No Groq keys found in environment")
        sys.exit(1)
    asyncio.run(main())
