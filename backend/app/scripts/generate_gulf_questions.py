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
from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.models.models import MCQQuestion, Module
from app.scripts._mcq_db_writer import get_gulf_sources, get_or_create_gulf_module, save_questions_to_db

# ── Config ────────────────────────────────────────────────────────────────────
# Each slot: (api_key, api_url, model_name)
def _dedup(keys: list) -> list:
    seen: set = set()
    return [k for k in keys if k and not (k in seen or seen.add(k))]

_GROQ_KEYS = _dedup([
    os.getenv("GROQ_KEY_MODULE_2", ""),
    os.getenv("GROQ_KEY_CASES", ""),
    os.getenv("GROQ_KEY_VET_MODULES", ""),
    os.getenv("GROQ_API_KEY_3", ""),
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

# Build unified key pool: (key, url, model)
ALL_LLM_SLOTS = (
    [(k, GROQ_URL, "llama-3.3-70b-versatile") for k in _GROQ_KEYS] +
    [(k, CEREBRAS_URL, "llama-3.3-70b") for k in _CEREBRAS_KEYS]
)

# Legacy alias for logging
GROQ_KEYS = [s[0] for s in ALL_LLM_SLOTS]  # used only for len() in logs
GROQ_MODEL = "llama-3.3-70b-versatile"

TARGET_PER_EXAM = 300
BATCH_SIZE = 15

# Blueprint weights derived from official regulatory documents:
#   SNLE: SCFHS Applicant Guide 2024 (scfhs.org.sa)
#   OMSB: Omani Examination for Nurses booklet (omsb.gov.om)
# Consensus weights cover all 7 Gulf Prometric exams.
# Sum of weights = 100; generation picks topics proportionally.
GULF_EXAM_TOPICS = [
    {
        "topic": "Adult Medical-Surgical Nursing",
        "category": "medical_surgical",
        "weight": 23,  # SNLE: part of Adult Nursing 40%; OMSB: Adult Health 30%
        "subtopics": ["cardiovascular disorders", "respiratory conditions", "gastrointestinal nursing",
                      "endocrine disorders (diabetes, thyroid)", "neurological nursing",
                      "musculoskeletal and renal conditions", "pre/post-operative care",
                      "oncology nursing", "fluid and electrolyte balance"],
    },
    {
        "topic": "Critical Care Nursing",
        "category": "critical_care",
        "weight": 10,  # SNLE: explicit subsection of Adult Nursing; absent in earlier generators
        "subtopics": ["hemodynamic monitoring", "mechanical ventilation care",
                      "shock management", "sepsis protocols", "IV therapy and infusions",
                      "ECG interpretation basics", "post-cardiac arrest care",
                      "multi-organ failure nursing"],
    },
    {
        "topic": "Nursing Fundamentals and Physical Assessment",
        "category": "fundamentals_nursing",
        "weight": 15,  # SNLE: Nursing Fundamentals 20% (shared with Pharmacology below)
        "subtopics": ["vital signs and physical assessment", "wound care and sterile technique",
                      "nursing process (ADPIE)", "infection control and isolation precautions",
                      "patient safety and fall prevention", "documentation and reporting",
                      "oxygenation and airway management", "basic sciences anatomy/physiology"],
    },
    {
        "topic": "Pharmacology for Nurses",
        "category": "pharmacology",
        "weight": 8,   # SNLE: subsection of Fundamentals; high-yield on all Gulf exams
        "subtopics": ["medication administration rights", "drug calculations and dosing",
                      "antibiotics and antimicrobials", "cardiovascular drugs (antihypertensives, diuretics)",
                      "analgesics and pain management", "insulin and hypoglycemic agents",
                      "high-alert medications", "drug interactions and contraindications"],
    },
    {
        "topic": "Maternal, Newborn and Gynecological Nursing",
        "category": "maternal_newborn",
        "weight": 15,  # SNLE: Maternal-Child 30% (shared with Pediatrics below)
        "subtopics": ["prenatal care and antepartum assessment", "labor and delivery complications",
                      "postpartum care and complications", "newborn assessment and APGAR",
                      "breastfeeding and neonatal nutrition", "obstetric emergencies",
                      "gynecological conditions", "neonatal intensive care basics"],
    },
    {
        "topic": "Pediatric Nursing",
        "category": "pediatrics",
        "weight": 10,  # SNLE: part of Maternal-Child 30%; OMSB: Child Health 10%
        "subtopics": ["growth and development milestones", "pediatric physical assessment",
                      "immunizations and vaccination schedules", "common childhood illnesses",
                      "pediatric medication dosing (weight-based)", "pediatric emergencies",
                      "child abuse recognition and reporting"],
    },
    {
        "topic": "Mental Health and Psychiatric Nursing",
        "category": "mental_health",
        "weight": 7,  # OMSB: Mental Health 10%; SNLE: part of Adult Nursing
        "subtopics": ["therapeutic communication techniques", "psychiatric disorders (schizophrenia, depression, bipolar)",
                      "crisis intervention and suicide risk", "psychotropic medications and side effects",
                      "de-escalation and restraint protocols", "substance use disorders"],
    },
    {
        "topic": "Community Health and Gerontological Nursing",
        "category": "community_public_health",
        "weight": 7,  # OMSB: Community Health & Gerontology 15%; SNLE: part of Adult Nursing
        "subtopics": ["health promotion and disease prevention", "epidemiology and communicable diseases",
                      "vaccination programs and public health", "gerontological assessment and care",
                      "age-related physiological changes", "chronic disease management in the community",
                      "cultural competency in Gulf healthcare settings"],
    },
    {
        "topic": "Nursing Leadership, Management and Professional Practice",
        "category": "leadership_management",
        "weight": 5,   # SNLE: Nursing Management 10%; OMSB: Principles of Care 20%
        "subtopics": ["delegation and assignment", "prioritization (ABC, Maslow's hierarchy)",
                      "patient safety and quality improvement", "scope of practice and ethical issues",
                      "legal and professional standards", "nursing informatics",
                      "chain of command and conflict resolution", "evidence-based practice"],
    },
]

# Precomputed weight list for weighted topic selection
_TOPIC_WEIGHTS = [t["weight"] for t in GULF_EXAM_TOPICS]


async def _count_existing_db(slug: str) -> int:
    """Count questions already in DB for this Gulf exam slug."""
    module_code = f"GULF-{slug.upper()}"
    async with AsyncSessionLocal() as db:
        mod_result = await db.execute(select(Module.id).where(Module.code == module_code))
        module_id = mod_result.scalar_one_or_none()
        if module_id is None:
            return 0
        count_result = await db.execute(
            select(func.count(MCQQuestion.id)).where(MCQQuestion.module_id == module_id)
        )
        return count_result.scalar() or 0


class RateLimiter:
    def __init__(self):
        self._reset_at: dict[str, float] = {slot[0]: 0.0 for slot in ALL_LLM_SLOTS}

    def _best_slot(self) -> tuple:
        return min(ALL_LLM_SLOTS, key=lambda s: self._reset_at[s[0]])

    def mark_limited(self, key: str, reset_in: float) -> None:
        self._reset_at[key] = time.time() + reset_in

    @staticmethod
    def _parse_retry_after(resp_json: dict) -> float:
        try:
            msg = resp_json.get("error", {}).get("message", "")
            part = msg.split("in ")[-1].strip()
            m = re.match(r"(?:(\d+)m)?(\d+(?:\.\d+)?)s?", part)
            return float(m.group(1) or 0) * 60 + float(m.group(2) or 0) if m else 120.0
        except Exception:
            return 120.0

    async def generate(self, prompt: str, max_tokens: int = 3000, max_wait: int = 90) -> str | None:
        for _attempt in range(len(ALL_LLM_SLOTS) * 4):
            key, url, model = self._best_slot()
            wait = self._reset_at[key] - time.time()
            if wait > max_wait:
                print(f"  ⚠ All {len(ALL_LLM_SLOTS)} LLM slots limited >{max_wait}s. Exiting — cron will retry.")
                return None
            if wait > 0:
                await asyncio.sleep(wait + 1)
            try:
                async with httpx.AsyncClient(timeout=60) as client:
                    resp = await client.post(
                        url,
                        headers={"Authorization": f"Bearer {key}"},
                        json={"model": model, "messages": [{"role": "user", "content": prompt}],
                              "max_tokens": max_tokens, "temperature": 0.7},
                    )
                if resp.status_code == 429:
                    retry_after = self._parse_retry_after(resp.json())
                    provider = "Groq" if "groq" in url else "Cerebras"
                    idx = ALL_LLM_SLOTS.index((key, url, model)) + 1
                    print(f"  [{provider} slot {idx}/{len(ALL_LLM_SLOTS)}] limited {retry_after:.0f}s — switching")
                    self.mark_limited(key, retry_after)
                    continue
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
            except Exception as e:
                print(f"  Error: {e}")
                await asyncio.sleep(2)
        return None


def _build_prompt(exam_slug: str, topic: dict, n: int) -> str:
    # Rotate subtopics to maximize variety across batches
    import random
    subtopics = random.sample(topic["subtopics"], min(4, len(topic["subtopics"])))
    subtopic_str = ", ".join(subtopics)
    return f"""You are a senior nursing educator writing exam questions for the {exam_slug.upper()} \
Prometric nursing licensing exam. Your questions must match the style of Saunders Comprehensive \
Review for the NCLEX-RN: clinical scenario first, then ask what the nurse does NEXT or FIRST.

Topic: {topic['topic']}
Subtopics to cover in this batch: {subtopic_str}
Blueprint category: {topic['category']}

QUESTION WRITING RULES (Saunders / Prometric style):
1. Always start with a patient scenario (age, condition, vital signs, lab values, or symptoms)
2. Ask for the PRIORITY action, FIRST intervention, or BEST response — not isolated facts
3. Apply clinical reasoning frameworks: ABC airway/breathing/circulation first; then Maslow's hierarchy
4. All 4 options must be clinically plausible — 3 wrong options should be reasonable nursing actions
   that are simply lower priority or applicable in a different context
5. Avoid trick questions, double negatives, and "all of the above / none of the above"
6. Mix difficulty: ~30% application (identify correct action), ~50% analysis (prioritize among correct
   actions), ~20% evaluation (assess outcome or safety)
7. Vary question stems: "The nurse should FIRST...", "Which finding requires IMMEDIATE action?",
   "The nurse prepares to..., which action is PRIORITY?", "The client states... The nurse responds..."

CLINICAL ACCURACY:
- Use current evidence-based practice standards
- Drug doses, lab values, and vital sign ranges must be clinically accurate
- Reflect Gulf healthcare context where relevant (e.g., Ramadan fasting considerations,
  cultural communication norms, heat-related illness in Middle East climate)

Return ONLY a valid JSON array of exactly {n} questions:
[
  {{
    "question": "A 58-year-old male with COPD is receiving oxygen at 2 L/min via nasal cannula. \
His SpO2 is 88% and he appears anxious. Which action should the nurse take FIRST?",
    "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
    "correct": "B",
    "explanation": "B is correct because... [clinical rationale]. A is incorrect because... \
C would be appropriate after... D is contraindicated because...",
    "rationales": {{
      "A": {{"text": "Detailed rationale for A", "why": "incorrect"}},
      "B": {{"text": "Detailed rationale for B", "why": "correct"}},
      "C": {{"text": "Detailed rationale for C", "why": "incorrect"}},
      "D": {{"text": "Detailed rationale for D", "why": "incorrect"}}
    }},
    "key_takeaway": "In COPD, hypoxic drive means high-flow O2 can suppress respiratory effort — \
target SpO2 88-92%.",
    "test_taking_tip": "When selecting priority actions, apply ABC first: airway and breathing \
issues always precede circulation and other concerns.",
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


async def generate_for_slug(slug: str, exam_name: str) -> int:
    limiter = RateLimiter()
    existing = await _count_existing_db(slug)
    needed = max(0, TARGET_PER_EXAM - existing)
    if needed == 0:
        print(f"  {slug}: already at {existing}/{TARGET_PER_EXAM} in DB — skipping")
        return 0

    print(f"\n{'='*60}")
    print(f"  Generating for {slug.upper()}: {existing}/{TARGET_PER_EXAM} — need {needed} more")
    print(f"{'='*60}")

    # Build weighted topic queue proportional to blueprint weights
    import random
    total_weight = sum(_TOPIC_WEIGHTS)
    topic_queue: list[dict] = []
    for topic, w in zip(GULF_EXAM_TOPICS, _TOPIC_WEIGHTS):
        count = round(needed * w / total_weight)
        topic_queue.extend([topic] * max(1, count // BATCH_SIZE + (1 if count % BATCH_SIZE else 0)))
    # Shuffle to avoid generating all of one topic consecutively
    random.shuffle(topic_queue)

    new_questions: list[dict] = []
    generated = 0
    for topic in topic_queue:
        if generated >= needed:
            break
        batch = min(BATCH_SIZE, needed - generated)
        print(f"  → {topic['topic']} (weight {topic['weight']}%, {batch} questions)...")
        prompt = _build_prompt(slug, topic, batch)
        raw = await limiter.generate(prompt)
        if raw is None:
            break
        qs = _parse_questions(raw)
        for q in qs:
            q["exam_slugs"] = [slug]
        new_questions.extend(qs)
        generated += len(qs)
        print(f"    ✓ {len(qs)} generated")
        await asyncio.sleep(5)

    if new_questions:
        module_id = await get_or_create_gulf_module(slug, exam_name)
        source_refs = get_gulf_sources(slug)
        saved, skipped = await save_questions_to_db(
            new_questions, module_id, source_refs,
            run_verification=True, print_fn=print,
        )
        print(f"  ✓ {saved} saved, {skipped} skipped for {slug}")
        return saved

    return 0


async def main() -> None:
    from app.data.exam_registry import GULF_EXAMS
    gulf_exams = {e["slug"]: e["name"] for e in GULF_EXAMS}
    gulf_slugs = list(gulf_exams.keys())

    target_slug: str | None = None
    if "--slug" in sys.argv:
        idx = sys.argv.index("--slug")
        if idx + 1 < len(sys.argv):
            target_slug = sys.argv[idx + 1]

    run_next = "--next" in sys.argv

    if not run_next and not target_slug:
        # Status report
        print("\nGulf question bank status (DB):")
        for slug in gulf_slugs:
            count = await _count_existing_db(slug)
            status = "✓" if count >= TARGET_PER_EXAM else f"{count}/{TARGET_PER_EXAM}"
            print(f"  {slug:<12} {status}")
        return

    if target_slug:
        exam_name = gulf_exams.get(target_slug, target_slug.upper())
        total = await generate_for_slug(target_slug, exam_name)
        print(f"\nDone: {total} questions saved for {target_slug}")
        return

    # --next: pick first slug under target
    for slug in gulf_slugs:
        if await _count_existing_db(slug) < TARGET_PER_EXAM:
            exam_name = gulf_exams[slug]
            total = await generate_for_slug(slug, exam_name)
            print(f"\nDone: {total} questions saved for {slug}")
            print(f"Run without --next to see updated DB counts per slug.")
            return

    print("All Gulf exam slugs at target in DB.")


if __name__ == "__main__":
    if not GROQ_KEYS:
        print("ERROR: No Groq keys found in environment")
        sys.exit(1)
    asyncio.run(main())
