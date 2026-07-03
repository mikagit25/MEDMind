"""
Enrich existing veterinary modules: expand from 3 → 10 detailed lessons per module.

Each generated lesson uses the block-based LessonContentSchema format:
  - text blocks  (intro, pathophysiology, clinical signs, diagnosis, treatment, monitoring)
  - dosage_table blocks  (species-specific drug dosing with dose/route/warning)
  - quiz blocks  (MCQ with immediate feedback)
  - flashcard blocks  (inline Q&A cards)

Additionally saves Flashcard and MCQQuestion rows to their own tables for the
spaced-repetition and quiz systems.

Uses GROQ_KEY_VET_MODULES (KEY_6) with KEY_3/4/5 as fallbacks.

Usage:
  python -m app.scripts.enrich_vet_modules                        # all vet modules
  python -m app.scripts.enrich_vet_modules --module-code VET-001  # single module
  python -m app.scripts.enrich_vet_modules --max-per-run 5        # cap lessons/run
  python -m app.scripts.enrich_vet_modules --target-count 10      # lessons/module goal
  python -m app.scripts.enrich_vet_modules --dry-run              # preview, no saves
"""

import argparse
import asyncio
import json
import logging
import re
import sys
import time
import uuid
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.models import Flashcard, Lesson, MCQQuestion, Module

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = settings.GROQ_MODEL or "llama-3.3-70b-versatile"


# ─── Key pool ────────────────────────────────────────────────────────────────

def _get_keys() -> list[str]:
    candidates = [
        settings.GROQ_KEY_VET_MODULES,
        settings.GROQ_API_KEY_3,
        settings.GROQ_API_KEY_4,
        settings.GROQ_API_KEY_5,
    ]
    keys = [k.strip() for k in candidates if k and k.strip()]
    if not keys:
        log.error("No Groq keys available. Set GROQ_KEY_VET_MODULES in .env")
        sys.exit(1)
    return keys


async def _call_groq(prompt: str, system: str, keys: list[str], max_tokens: int = 4096) -> str | None:
    for i, key in enumerate(keys):
        try:
            async with httpx.AsyncClient(timeout=120) as c:
                r = await c.post(
                    GROQ_API_URL,
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={
                        "model": GROQ_MODEL,
                        "max_tokens": max_tokens,
                        "temperature": 0.4,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user",   "content": prompt},
                        ],
                    },
                )
            if r.status_code == 429:
                log.warning("Key %d rate-limited, trying next", i + 1)
                continue
            if r.status_code != 200:
                log.warning("Key %d error %s: %s", i + 1, r.status_code, r.text[:200])
                continue
            return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            log.warning("Key %d exception: %s", i + 1, e)
    return None


# ─── JSON parsing ─────────────────────────────────────────────────────────────

def _extract_json(raw: str) -> dict | None:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as e:
        log.warning("JSON parse failed: %s", e)
        return None


# ─── Prompts ──────────────────────────────────────────────────────────────────

SYSTEM_PLAN = """You are a senior veterinary educator with expertise in curriculum design.
Your task is to create detailed lesson plans for veterinary education modules.
Return only valid JSON, no markdown fences, no extra text."""

SYSTEM_LESSON = """You are a senior veterinary clinician and educator (DVM, PhD).
Generate comprehensive, clinically accurate veterinary education content.
Rules:
- All drug doses must be species-specific and evidence-based (WSAVA/BSAVA/Merck Vet Manual)
- Use SI units: mg/kg, mmol/L, µmol/L, IU/L
- Mark off-label uses explicitly
- quiz and flashcard questions must be clinically relevant and exam-quality
- Return ONLY valid JSON — no markdown fences, no preamble text"""


def _plan_prompt(module_title: str, existing_titles: list[str], target: int) -> str:
    existing_str = "\n".join(f"  {i+1}. {t}" for i, t in enumerate(existing_titles))
    needed = target - len(existing_titles)
    return f"""Module: "{module_title}"

Existing lessons already in the database:
{existing_str}

Generate a lesson plan for {needed} NEW lessons that:
1. Complement (do not duplicate) the existing lessons
2. Progress logically in complexity
3. Cover the most clinically important and commonly examined topics in this specialty

Return JSON:
{{
  "lesson_plan": [
    {{"order": {len(existing_titles)+1}, "title": "...", "topic_focus": "..."}},
    ...
  ]
}}"""


def _lesson_prompt(module_title: str, lesson_title: str, lesson_order: int,
                   species_list: list[str]) -> str:
    species_str = ", ".join(species_list) if species_list else "canine, feline"
    return f"""Generate a complete veterinary education lesson for this module:

Module: "{module_title}"
Lesson #{lesson_order}: "{lesson_title}"
Target species: {species_str}

Return JSON with this exact structure:
{{
  "title": "{lesson_title}",
  "estimated_minutes": 30,
  "learning_objectives": ["obj1 (max 8)", "obj2", "obj3"],
  "species_applicability": {json.dumps(species_list)},
  "clinical_risk_level": "medium",
  "guideline_sources": [{{"name": "Merck Veterinary Manual", "year": 2025}}],
  "blocks": [
    {{
      "type": "text",
      "order": 0,
      "content": "## Introduction\\n\\n[200+ words: clinical importance, prevalence, overview]"
    }},
    {{
      "type": "text",
      "order": 1,
      "content": "## Aetiology and Pathophysiology\\n\\n[300+ words: causes, mechanisms, breed predispositions]"
    }},
    {{
      "type": "text",
      "order": 2,
      "content": "## Clinical Signs\\n\\n[250+ words: history, physical exam findings, severity staging]"
    }},
    {{
      "type": "text",
      "order": 3,
      "content": "## Diagnosis\\n\\n[300+ words: haematology, biochemistry, imaging, specific tests, differential diagnosis]"
    }},
    {{
      "type": "dosage_table",
      "order": 4,
      "drug_name": "Primary drug name",
      "unit": "mg/kg",
      "rows": [
        {{"species": "canine", "dose": "X", "unit": "mg/kg", "route": "PO/IV/SC", "frequency": "SID/BID/TID", "warning": "if any"}},
        {{"species": "feline", "dose": "X", "unit": "mg/kg", "route": "PO/IV/SC", "frequency": "SID/BID"}}
      ]
    }},
    {{
      "type": "text",
      "order": 5,
      "content": "## Treatment Protocol\\n\\n[400+ words: stepwise management, first-line vs second-line, monitoring parameters, treatment targets]"
    }},
    {{
      "type": "dosage_table",
      "order": 6,
      "drug_name": "Second key drug (if applicable)",
      "unit": "mg/kg",
      "rows": [
        {{"species": "canine", "dose": "X", "unit": "mg/kg", "route": "PO", "frequency": "BID"}}
      ]
    }},
    {{
      "type": "text",
      "order": 7,
      "content": "## Monitoring and Prognosis\\n\\n[200+ words: follow-up schedule, response criteria, complications, quality of life]"
    }},
    {{
      "type": "quiz",
      "order": 8,
      "question": "Clinically realistic MCQ question about a key concept in this lesson",
      "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
      "correct": "A",
      "explanation": "Detailed explanation of why A is correct and why others are wrong (100+ words)",
      "difficulty": "medium"
    }},
    {{
      "type": "quiz",
      "order": 9,
      "question": "Second MCQ — about dosing or diagnosis",
      "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
      "correct": "B",
      "explanation": "...",
      "difficulty": "hard"
    }},
    {{
      "type": "flashcard",
      "order": 10,
      "question": "Key fact question 1",
      "answer": "Concise, memorable answer with specific values/doses",
      "difficulty": "medium"
    }},
    {{
      "type": "flashcard",
      "order": 11,
      "question": "Key fact question 2",
      "answer": "...",
      "difficulty": "medium"
    }},
    {{
      "type": "flashcard",
      "order": 12,
      "question": "Key fact question 3 (about a specific dose or diagnostic value)",
      "answer": "...",
      "difficulty": "hard"
    }}
  ],
  "flashcards": [
    {{"question": "...", "answer": "...", "difficulty": "medium"}},
    {{"question": "...", "answer": "...", "difficulty": "medium"}},
    {{"question": "...", "answer": "...", "difficulty": "hard"}},
    {{"question": "...", "answer": "...", "difficulty": "hard"}},
    {{"question": "...", "answer": "...", "difficulty": "easy"}},
    {{"question": "...", "answer": "...", "difficulty": "medium"}},
    {{"question": "...", "answer": "...", "difficulty": "hard"}},
    {{"question": "...", "answer": "...", "difficulty": "medium"}}
  ],
  "mcq_questions": [
    {{
      "question": "...",
      "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
      "correct": "C",
      "explanation": "...",
      "difficulty": "medium"
    }},
    {{
      "question": "...",
      "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
      "correct": "A",
      "explanation": "...",
      "difficulty": "hard"
    }},
    {{
      "question": "...",
      "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
      "correct": "D",
      "explanation": "...",
      "difficulty": "medium"
    }}
  ]
}}

Write ALL content in English. Be specific: include real drug names, real doses, real diagnostic values."""


# ─── Species mapping ──────────────────────────────────────────────────────────

MODULE_SPECIES: dict[str, list[str]] = {
    "VET-001": ["canine", "feline"],
    "VET-002": ["equine", "bovine", "ovine"],
    "VET-003": ["canine", "feline", "equine", "bovine"],
    "VET-004": ["canine", "feline"],
    "VET-005": ["canine", "feline"],
    "VET-006": ["canine", "feline"],
    "VET-007": ["canine", "feline"],
    "VET-008": ["canine", "feline"],
    "VET-009": ["avian", "exotic"],
    "VET-010": ["canine", "feline"],
    "VET-011": ["canine", "feline"],
    "VET-012": ["canine", "feline", "bovine", "equine"],
    "VET-013": ["canine", "feline", "bovine", "avian"],
    "VET-014": ["canine", "feline"],
    "VET-015": ["canine", "feline", "exotic"],
    "VET-016": ["canine", "feline"],
    "VET-017": ["canine", "feline", "equine"],
    "VET-018": ["canine", "feline"],
    "VET-019": ["canine", "feline"],
    "VET-020": ["canine", "feline", "exotic"],
    "VET-021": ["canine", "feline"],
}


# ─── Lesson content builder ───────────────────────────────────────────────────

def _build_lesson_content(data: dict) -> dict:
    """Convert LLM output into the LessonContentSchema-compatible JSONB structure."""
    blocks = []
    for i, block in enumerate(data.get("blocks", [])):
        b = dict(block)
        # Ensure every block has an id and order
        b.setdefault("id", uuid.uuid4().hex)
        b.setdefault("order", i)
        # Dosage table: ensure rows have required keys
        if b.get("type") == "dosage_table":
            cleaned_rows = []
            for row in b.get("rows", []):
                if "species" in row and "dose" in row and "route" in row:
                    cleaned_rows.append(row)
            b["rows"] = cleaned_rows
            if not cleaned_rows:
                continue  # skip empty dosage tables
        blocks.append(b)

    return {
        "title": data.get("title", ""),
        "estimated_minutes": data.get("estimated_minutes", 25),
        "learning_objectives": data.get("learning_objectives", [])[:10],
        "species_applicability": data.get("species_applicability", ["canine", "feline"]),
        "clinical_risk_level": data.get("clinical_risk_level", "medium"),
        "guideline_sources": data.get("guideline_sources", []),
        "blocks": blocks,
    }


# ─── Core logic ───────────────────────────────────────────────────────────────

async def enrich_module(
    session: AsyncSession,
    module: Module,
    keys: list[str],
    target_count: int,
    dry_run: bool,
) -> int:
    """Enrich one module. Returns number of lessons actually generated."""
    code = module.code
    title_en = module.title_en or module.title
    species = MODULE_SPECIES.get(code, ["canine", "feline"])

    # Existing lessons
    result = await session.execute(
        select(Lesson).where(Lesson.module_id == module.id).order_by(Lesson.lesson_order)
    )
    existing = result.scalars().all()
    existing_count = len(existing)

    if existing_count >= target_count:
        log.info("%s: already has %d lessons, skipping", code, existing_count)
        return 0

    existing_titles = [l.title for l in existing]
    log.info("%s: %d/%d lessons — need %d more", code, existing_count, target_count,
             target_count - existing_count)

    # ── Step 1: get or generate lesson plan ───────────────────────────────────
    mod_content = module.content or {}
    plan: list[dict] = mod_content.get("vet_lesson_plan", [])

    # Filter plan to only new lessons (not already in existing_titles)
    existing_titles_lower = {t.lower() for t in existing_titles}
    plan = [p for p in plan if p.get("title", "").lower() not in existing_titles_lower]

    if not plan:
        log.info("%s: generating lesson plan", code)
        raw = await _call_groq(
            _plan_prompt(title_en, existing_titles, target_count),
            SYSTEM_PLAN,
            keys,
            max_tokens=1500,
        )
        if not raw:
            log.error("%s: failed to get lesson plan", code)
            return 0
        parsed = _extract_json(raw)
        if not parsed or "lesson_plan" not in parsed:
            log.error("%s: could not parse lesson plan", code)
            return 0
        plan = parsed["lesson_plan"]
        log.info("%s: plan has %d new lessons", code, len(plan))

        if not dry_run:
            new_content = dict(mod_content)
            new_content["vet_lesson_plan"] = plan
            await session.execute(
                update(Module)
                .where(Module.id == module.id)
                .values(content=new_content, updated_at=datetime.utcnow())
            )
            await session.commit()

    # ── Step 2: generate each lesson from plan ────────────────────────────────
    generated = 0
    next_order = existing_count + 1

    for plan_item in plan:
        lesson_title = plan_item.get("title", "")
        if not lesson_title:
            continue

        log.info("%s: generating lesson %d: %s", code, next_order, lesson_title)

        if dry_run:
            log.info("[DRY RUN] would generate: %s", lesson_title)
            next_order += 1
            generated += 1
            continue

        raw = await _call_groq(
            _lesson_prompt(title_en, lesson_title, next_order, species),
            SYSTEM_LESSON,
            keys,
            max_tokens=4096,
        )
        if not raw:
            log.error("%s: no response for lesson %d", code, next_order)
            time.sleep(10)
            continue

        data = _extract_json(raw)
        if not data:
            log.error("%s: could not parse lesson %d", code, next_order)
            continue

        content = _build_lesson_content(data)

        lesson = Lesson(
            module_id=module.id,
            lesson_code=f"{code}-L{next_order}",
            title=data.get("title", lesson_title),
            lesson_order=next_order,
            content=content,
            estimated_minutes=content.get("estimated_minutes", 25),
            species_applicability=content.get("species_applicability", species),
            clinical_risk_level=content.get("clinical_risk_level", "medium"),
            status="published",
            published_at=datetime.utcnow(),
            guideline_version="WSAVA/BSAVA/Merck 2025",
        )
        session.add(lesson)

        # Save standalone flashcards
        for fc in data.get("flashcards", []):
            q, a = fc.get("question", ""), fc.get("answer", "")
            if q and a:
                session.add(Flashcard(
                    module_id=module.id,
                    question=q,
                    answer=a,
                    difficulty=fc.get("difficulty", "medium"),
                    category=title_en,
                    tags=[code, "veterinary"],
                ))

        # Save standalone MCQ questions
        for mcq in data.get("mcq_questions", []):
            q = mcq.get("question", "")
            opts = mcq.get("options", {})
            correct = mcq.get("correct", "")
            if q and opts and correct and correct in opts:
                session.add(MCQQuestion(
                    module_id=module.id,
                    question=q,
                    options=opts,
                    correct=correct,
                    explanation=mcq.get("explanation", ""),
                    difficulty=mcq.get("difficulty", "medium"),
                    tags=[code, "veterinary"],
                ))

        await session.commit()
        log.info("%s: saved lesson %d ✓", code, next_order)
        next_order += 1
        generated += 1

        # Respect rate limits
        await asyncio.sleep(3)

    return generated


async def main(args: argparse.Namespace) -> None:
    keys = _get_keys()
    log.info("Using %d Groq key(s). Target: %d lessons/module. Max this run: %d",
             len(keys), args.target_count, args.max_per_run)

    async with AsyncSessionLocal() as session:
        q = select(Module).where(Module.is_veterinary == True)
        if args.module_code:
            q = q.where(Module.code == args.module_code)
        q = q.order_by(Module.module_order)
        result = await session.execute(q)
        modules = result.scalars().all()

    if not modules:
        log.error("No veterinary modules found")
        return

    log.info("Found %d vet module(s)", len(modules))
    total_generated = 0

    for module in modules:
        if total_generated >= args.max_per_run:
            log.info("Reached max-per-run limit (%d), stopping", args.max_per_run)
            break
        remaining = args.max_per_run - total_generated
        async with AsyncSessionLocal() as session:
            n = await enrich_module(session, module, keys, args.target_count, args.dry_run)
        total_generated += n
        log.info("Module %s: generated %d lessons (total this run: %d)",
                 module.code, n, total_generated)

    log.info("Done. Total lessons generated: %d", total_generated)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enrich veterinary education modules")
    parser.add_argument("--module-code", help="Process only this module (e.g. VET-001)")
    parser.add_argument("--max-per-run",  type=int, default=5,
                        help="Max lessons to generate in this run (default 5)")
    parser.add_argument("--target-count", type=int, default=10,
                        help="Target lesson count per module (default 10)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without saving or calling the API")
    args = parser.parse_args()
    asyncio.run(main(args))
