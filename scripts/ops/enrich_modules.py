#!/usr/bin/env python3
"""
Module content enricher — uses dedicated GROQ_KEY_MODULE key.

For each lesson:
  - Expands section texts to clinical depth (3-5x)
  - Adds evidence-based references (major guidelines + landmark trials)
  - Enriches clinical_pearl and key_points
  - Adds 5 extra flashcards per module (total 10)

Usage:
  python3 scripts/ops/enrich_modules.py                  # all modules
  python3 scripts/ops/enrich_modules.py --module CARDIO-001
  python3 scripts/ops/enrich_modules.py --specialty CARDIO
  python3 scripts/ops/enrich_modules.py --dry-run       # show plan only
  python3 scripts/ops/enrich_modules.py --reset VET-017 # remove enrichment flag

Rate limits: Groq free tier ~30 RPM / 500-1000 RPD for llama-3.3-70b.
The script sleeps between calls and retries on 429.
"""

import argparse
import json
import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

MODULES_DIR = Path(__file__).parent.parent.parent / "Modules"
GROQ_KEY = os.environ.get("GROQ_KEY_MODULE", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"

# Delay between API calls (seconds).
# Groq free tier for llama-3.3-70b: ~6000 TPM input limit.
# Each lesson call ~2000 input tokens → max 3 calls/min → 22s between calls.
CALL_DELAY = 22.0
# Extra delay after rate-limit hit
RATE_LIMIT_SLEEP = 65


# ── Prompts ──────────────────────────────────────────────────────────────────

LESSON_SYSTEM_PROMPT = """You are a senior medical/veterinary educator creating authoritative, evidence-based educational content for healthcare professionals.

TASK: Enrich the provided lesson JSON with deeper clinical content. Return ONLY valid JSON — no markdown, no commentary.

Rules:
1. Keep all existing field names exactly as provided.
2. Expand each section "text" to 3-5x its current length with:
   - Detailed clinical mechanisms and pathophysiology
   - Diagnostic criteria with specific thresholds/values
   - Treatment protocols with specific doses where appropriate
   - Comparison of clinical approaches (e.g., when to choose A vs B)
3. Expand "clinical_pearl" with nuanced clinical wisdom.
4. Expand "key_points" to 6-8 concise, actionable points.
5. Add a "references" array (5-8 items) at the same level as "sections". Each reference:
   {
     "title": "Full guideline/paper title or study name",
     "authors": "Author Last Name et al. OR organization name (e.g. ESC, ACC/AHA, WSAVA)",
     "journal_or_source": "JACC / ESC / NEJM / Lancet / JVIM / Vet Rec / etc.",
     "year": 2022,
     "type": "guideline|rct|meta-analysis|review",
     "note": "Specific clinical relevance: e.g. 'Defines GRACE score thresholds for ACS risk'"
   }
   IMPORTANT — ONLY cite REAL, named guidelines and landmark trials that actually exist:
   Medical examples: "2023 ESC Guidelines for Acute Coronary Syndromes", "ACC/AHA 2022 Guideline for Heart Failure",
   "PARADIGM-HF (McMurray, NEJM 2014)", "RALES trial (Pitt, NEJM 1999)", "UKPDS-33 (NEJM 1998)",
   "ACCORD trial (NEJM 2008)", "4S trial (Lancet 1994)", "HOPE trial (NEJM 2000)",
   "ESC 2021 Guidelines on Cardiovascular Disease Prevention", "JNC 8 Guidelines (JAMA 2014)".
   Veterinary examples: "ACVIM Consensus Guidelines on CHF in Dogs and Cats (Boswood, JVIM 2019)",
   "WSAVA Nutrition Guidelines 2021", "ACVIM Consensus on CKD in Cats (Brown, JVIM 2016)",
   "RECOVER Guidelines for CPR in Veterinary Patients (Fletcher, JVIM 2012)".
   DO NOT fabricate DOIs or PMIDs. DO NOT invent study names.
6. Write all content in RUSSIAN (same language as the input).
7. Maintain scientific accuracy — no speculation.

Output format: the enriched lesson content object (same structure as input "content" object, with added "references" field)."""

FLASHCARD_SYSTEM_PROMPT = """You are a senior medical/veterinary educator creating high-yield flashcards for professional exam preparation.

TASK: Given a module's lessons content, generate 5 additional flashcards that are NOT already covered by the existing flashcards.

Focus on:
- Specific drug doses, diagnostic thresholds, key differentials
- Clinical decision points ("when to choose X vs Y")
- High-yield mnemonics
- Common exam traps / pitfalls

Return ONLY a JSON array of flashcard objects:
[
  {
    "id": "{{MODULE_ID}}-FC6",
    "category": "relevant category in Russian",
    "question": "Clear clinical question in Russian",
    "answer": "Concise but complete answer in Russian, with specific values where relevant",
    "difficulty": "easy|medium|hard"
  },
  ...
]
No markdown, no commentary."""


# ── Groq API ─────────────────────────────────────────────────────────────────

def call_groq(system: str, user: str, max_tokens: int = 4000, retries: int = 4) -> Optional[str]:
    headers = {
        "Authorization": f"Bearer {GROQ_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }

    for attempt in range(retries):
        try:
            with httpx.Client(timeout=90) as client:
                resp = client.post(GROQ_URL, json=payload, headers=headers)

            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()

            if resp.status_code == 429:
                log.warning(f"Rate limited — sleeping {RATE_LIMIT_SLEEP}s (attempt {attempt+1})")
                time.sleep(RATE_LIMIT_SLEEP)
                continue

            log.error(f"Groq error {resp.status_code}: {resp.text[:200]}")
            return None

        except Exception as e:
            log.error(f"Request error: {e}")
            if attempt < retries - 1:
                time.sleep(10 * (attempt + 1))
    return None


def parse_json_response(text: str) -> Optional[dict | list]:
    text = text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        # Try to find JSON object/array within text
        for start_char, end_char in [("{", "}"), ("[", "]")]:
            start = text.find(start_char)
            end = text.rfind(end_char)
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(text[start:end+1])
                except Exception:
                    pass
        log.error(f"JSON parse failed: {e}\nText: {text[:300]}")
        return None


# ── Enrichment logic ──────────────────────────────────────────────────────────

def enrich_lesson(module_id: str, lesson: dict) -> Optional[dict]:
    """Call Groq to enrich a single lesson's content."""
    content = lesson.get("content", {})
    user_msg = (
        f"Module: {module_id}\n"
        f"Lesson: {lesson['title']}\n\n"
        f"Current content to enrich:\n{json.dumps(content, ensure_ascii=False, indent=2)}"
    )

    raw = call_groq(LESSON_SYSTEM_PROMPT, user_msg, max_tokens=4096)
    if not raw:
        return None

    enriched = parse_json_response(raw)
    if not isinstance(enriched, dict):
        log.error(f"Expected dict from lesson enrichment, got {type(enriched)}")
        return None

    return enriched


def generate_extra_flashcards(module: dict) -> Optional[list]:
    """Generate 5 additional flashcards for a module."""
    module_id = module["meta"]["id"]
    existing_fc = module.get("flashcards", [])

    # Build a summary of lessons for context
    lessons_summary = []
    for lesson in module.get("lessons", []):
        c = lesson.get("content", {})
        lessons_summary.append({
            "title": lesson["title"],
            "key_points": c.get("key_points", []),
            "clinical_pearl": c.get("clinical_pearl", ""),
        })

    user_msg = (
        f"Module ID: {module_id}\n"
        f"Module title: {module['meta']['title']}\n\n"
        f"Existing flashcards (do NOT repeat these topics):\n"
        f"{json.dumps(existing_fc, ensure_ascii=False, indent=2)}\n\n"
        f"Lesson content summary:\n"
        f"{json.dumps(lessons_summary, ensure_ascii=False, indent=2)}\n\n"
        f"Generate 5 NEW flashcards (IDs: {module_id}-FC{len(existing_fc)+1} through {module_id}-FC{len(existing_fc)+5})."
    )

    raw = call_groq(
        FLASHCARD_SYSTEM_PROMPT.replace("{{MODULE_ID}}", module_id),
        user_msg,
        max_tokens=2000,
    )
    if not raw:
        return None

    result = parse_json_response(raw)
    if not isinstance(result, list):
        log.error(f"Expected list from flashcard generation, got {type(result)}")
        return None

    return result


def enrich_module(module_path: Path, dry_run: bool = False) -> bool:
    """Enrich a single module file. Returns True on success."""
    with open(module_path, encoding="utf-8") as f:
        module = json.load(f)

    module_id = module["meta"]["id"]

    # Skip already enriched
    if module["meta"].get("content_enriched"):
        log.info(f"⏭  {module_id} already enriched — skipping")
        return True

    log.info(f"🔄 Enriching {module_id}: {module['meta']['title']}")

    if dry_run:
        lessons_count = len(module.get("lessons", []))
        log.info(f"   [DRY RUN] Would enrich {lessons_count} lessons + flashcards")
        return True

    lessons = module.get("lessons", [])
    any_enriched = False

    for i, lesson in enumerate(lessons):
        log.info(f"   Lesson {i+1}/{len(lessons)}: {lesson['title']}")
        enriched_content = enrich_lesson(module_id, lesson)

        if enriched_content:
            lesson["content"] = enriched_content
            any_enriched = True
        else:
            log.warning(f"   ⚠  Failed to enrich lesson {i+1}, keeping original")

        time.sleep(CALL_DELAY)

    # Extra flashcards
    log.info(f"   Generating extra flashcards…")
    extra_fc = generate_extra_flashcards(module)
    if extra_fc:
        existing_ids = {fc["id"] for fc in module.get("flashcards", [])}
        new_fc = [fc for fc in extra_fc if fc.get("id") not in existing_ids]
        module.setdefault("flashcards", []).extend(new_fc)
        log.info(f"   ✅ Added {len(new_fc)} flashcards")
    else:
        log.warning(f"   ⚠  Flashcard generation failed")

    time.sleep(CALL_DELAY)

    if any_enriched or extra_fc:
        module["meta"]["content_enriched"] = True
        module["meta"]["enriched_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        module["meta"]["version"] = "2.0"

        with open(module_path, "w", encoding="utf-8") as f:
            json.dump(module, f, ensure_ascii=False, indent=2)

        log.info(f"   ✅ Saved {module_path.name}")
        return True

    log.warning(f"   ❌ No enrichment applied to {module_id}")
    return False


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Enrich MedMind module content via Groq")
    parser.add_argument("--module", help="Enrich specific module by ID (e.g. CARDIO-001)")
    parser.add_argument("--specialty", help="Enrich all modules of a specialty (e.g. CARDIO)")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without calling API")
    parser.add_argument("--reset", help="Remove enriched flag from module ID (re-run enrichment)")
    args = parser.parse_args()

    if not GROQ_KEY:
        log.error("GROQ_KEY_MODULE environment variable not set")
        sys.exit(1)

    # Handle --reset
    if args.reset:
        path = MODULES_DIR / f"module_{args.reset}.json"
        if not path.exists():
            log.error(f"Module file not found: {path}")
            sys.exit(1)
        with open(path, encoding="utf-8") as f:
            module = json.load(f)
        module["meta"].pop("content_enriched", None)
        module["meta"].pop("enriched_at", None)
        module["meta"]["version"] = "1.0"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(module, f, ensure_ascii=False, indent=2)
        log.info(f"Reset enrichment flag for {args.reset}")
        return

    # Collect modules to process
    all_files = sorted(MODULES_DIR.glob("module_*.json"))

    if args.module:
        target = f"module_{args.module}.json"
        files = [f for f in all_files if f.name == target]
        if not files:
            log.error(f"Module not found: {target}")
            sys.exit(1)
    elif args.specialty:
        prefix = f"module_{args.specialty}-"
        files = [f for f in all_files if f.name.startswith(prefix)]
        if not files:
            log.error(f"No modules found for specialty: {args.specialty}")
            sys.exit(1)
    else:
        # Exclude registry and -1 variant files
        files = [
            f for f in all_files
            if not f.name.endswith("-1.json")
        ]

    log.info(f"{'DRY RUN — ' if args.dry_run else ''}Processing {len(files)} module files")

    success = 0
    failed = 0
    skipped = 0

    for i, path in enumerate(files):
        try:
            with open(path, encoding="utf-8") as f:
                m = json.load(f)
            if m["meta"].get("content_enriched") and not args.dry_run:
                skipped += 1
                continue

            ok = enrich_module(path, dry_run=args.dry_run)
            if ok:
                success += 1
            else:
                failed += 1

        except KeyboardInterrupt:
            log.info(f"\nInterrupted at {path.name}. Progress saved.")
            break
        except Exception as e:
            log.error(f"Error processing {path.name}: {e}")
            failed += 1

        # Progress report every 10 modules
        if (i + 1) % 10 == 0:
            log.info(f"── Progress: {i+1}/{len(files)} | ✅{success} ❌{failed} ⏭{skipped}")

    log.info(f"\n{'='*50}")
    log.info(f"Done: ✅ {success} enriched | ⏭ {skipped} skipped | ❌ {failed} failed")
    log.info(f"After enriching, run: docker exec medmind_backend python -m app.scripts.import_modules")


if __name__ == "__main__":
    main()
