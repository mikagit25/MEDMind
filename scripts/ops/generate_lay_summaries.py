#!/usr/bin/env python3
"""
Generate lay_summary and lay_glossary for all module lessons.

lay_summary: 150-250 word plain-language explanation (8th-grade reading level)
             written for patients / general public. No medical jargon.
lay_glossary: 4-8 key medical terms from the lesson with simple definitions.

These power the public /learn section (no login required).

Uses GROQ_KEY_MODULE — dedicated for content generation.

Usage:
  python3 scripts/ops/generate_lay_summaries.py              # all modules
  python3 scripts/ops/generate_lay_summaries.py --module CARDIO-001
  python3 scripts/ops/generate_lay_summaries.py --specialty VET
  python3 scripts/ops/generate_lay_summaries.py --reset CARDIO-001
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

CALL_DELAY = 22.0       # seconds between calls (6000 TPM limit)
RATE_LIMIT_SLEEP = 70   # sleep after 429


LAY_SYSTEM_PROMPT = """You are a medical writer specializing in patient education. Your job is to explain complex medical content in plain language that a 14-year-old can understand.

TASK: Given a medical/veterinary lesson, produce TWO outputs in a JSON object:

{
  "lay_summary": "...",
  "lay_glossary": [...]
}

Rules for lay_summary:
- 150–250 words maximum
- 8th-grade reading level (no medical jargon without explanation)
- Active voice, short sentences
- Explain WHY this matters to the reader personally
- Do NOT just list facts — tell a story or explain a concept
- Do NOT use the words "administer", "pathophysiology", "etiology", "aforementioned"
- End with one practical takeaway
- Language: RUSSIAN (same as the input)

Rules for lay_glossary:
- Pick 4–8 key medical terms used in the lesson
- Each term: {"term": "...", "simple_definition": "one sentence in plain Russian"}
- Simple definitions should use everyday analogies where possible
- No definitions longer than 30 words
- Language: RUSSIAN

Output: ONLY the JSON object above. No markdown, no commentary."""


def call_groq(system: str, user: str, max_tokens: int = 1500, retries: int = 4) -> Optional[str]:
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
        "temperature": 0.4,
    }

    for attempt in range(retries):
        try:
            with httpx.Client(timeout=60) as client:
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
                time.sleep(10)
    return None


def parse_json(text: str) -> Optional[dict]:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except Exception:
                pass
        return None


def generate_lesson_lay(module_id: str, lesson: dict) -> Optional[dict]:
    content = lesson.get("content", {})
    # Build a compact lesson summary for the prompt
    sections_text = "\n".join(
        f"### {s['heading']}\n{s['text']}"
        for s in content.get("sections", [])
    )
    user_msg = (
        f"Module: {module_id}\n"
        f"Lesson title: {lesson['title']}\n\n"
        f"Intro: {content.get('intro', '')}\n\n"
        f"{sections_text}\n\n"
        f"Clinical pearl: {content.get('clinical_pearl', '')}\n"
        f"Key points: {', '.join(content.get('key_points', []))}"
    )

    raw = call_groq(LAY_SYSTEM_PROMPT, user_msg, max_tokens=1200)
    if not raw:
        return None

    result = parse_json(raw)
    if not isinstance(result, dict):
        log.error(f"Expected dict, got {type(result)}: {raw[:200]}")
        return None

    if "lay_summary" not in result or "lay_glossary" not in result:
        log.error(f"Missing required fields: {list(result.keys())}")
        return None

    return result


def process_module(module_path: Path, dry_run: bool = False) -> bool:
    with open(module_path, encoding="utf-8") as f:
        module = json.load(f)

    module_id = module["meta"]["id"]

    # Check if all lessons already have lay content
    lessons = module.get("lessons", [])
    already_done = all(
        l.get("lay_summary") or l.get("content", {}).get("lay_summary")
        for l in lessons
    )
    if already_done:
        log.info(f"⏭  {module_id} — all lessons have lay content, skipping")
        return True

    log.info(f"🌿 Generating lay summaries for {module_id}: {module['meta']['title']}")

    if dry_run:
        log.info(f"   [DRY RUN] Would process {len(lessons)} lessons")
        return True

    changed = False
    for i, lesson in enumerate(lessons):
        # Skip lessons that already have lay_summary
        if lesson.get("lay_summary"):
            log.info(f"   Lesson {i+1}/{len(lessons)}: already has lay_summary, skipping")
            continue

        log.info(f"   Lesson {i+1}/{len(lessons)}: {lesson['title']}")
        result = generate_lesson_lay(module_id, lesson)

        if result:
            lesson["lay_summary"] = result["lay_summary"]
            lesson["lay_glossary"] = result.get("lay_glossary", [])
            changed = True
            log.info(f"   ✅ lay_summary: {len(result['lay_summary'])} chars, {len(result.get('lay_glossary',[]))} terms")
        else:
            log.warning(f"   ⚠  Failed for lesson {i+1}")

        time.sleep(CALL_DELAY)

    if changed:
        with open(module_path, "w", encoding="utf-8") as f:
            json.dump(module, f, ensure_ascii=False, indent=2)
        log.info(f"   ✅ Saved {module_path.name}")

    return changed


def main():
    parser = argparse.ArgumentParser(description="Generate lay summaries for public /learn section")
    parser.add_argument("--module", help="Single module ID (e.g. CARDIO-001)")
    parser.add_argument("--specialty", help="Specialty prefix (e.g. VET, CARDIO)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reset", help="Remove lay content from module ID so it regenerates")
    args = parser.parse_args()

    if not GROQ_KEY:
        log.error("GROQ_KEY_MODULE environment variable not set")
        sys.exit(1)

    if args.reset:
        path = MODULES_DIR / f"module_{args.reset}.json"
        if not path.exists():
            log.error(f"Not found: {path}")
            sys.exit(1)
        with open(path, encoding="utf-8") as f:
            module = json.load(f)
        for lesson in module.get("lessons", []):
            lesson.pop("lay_summary", None)
            lesson.pop("lay_glossary", None)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(module, f, ensure_ascii=False, indent=2)
        log.info(f"Reset lay content for {args.reset}")
        return

    all_files = sorted(MODULES_DIR.glob("module_*.json"))

    if args.module:
        files = [f for f in all_files if f.name == f"module_{args.module}.json"]
        if not files:
            log.error(f"Module not found: {args.module}")
            sys.exit(1)
    elif args.specialty:
        prefix = f"module_{args.specialty}-"
        files = [f for f in all_files if f.name.startswith(prefix)]
        if not files:
            log.error(f"No modules for specialty: {args.specialty}")
            sys.exit(1)
    else:
        files = [f for f in all_files if not f.name.endswith("-1.json")]

    log.info(f"{'DRY RUN — ' if args.dry_run else ''}Processing {len(files)} modules")

    success = skipped = failed = 0

    for i, path in enumerate(files):
        try:
            with open(path, encoding="utf-8") as f:
                m = json.load(f)

            lessons = m.get("lessons", [])
            all_done = all(l.get("lay_summary") for l in lessons)
            if all_done and not args.dry_run:
                skipped += 1
                continue

            ok = process_module(path, dry_run=args.dry_run)
            if ok:
                success += 1
            else:
                failed += 1

        except KeyboardInterrupt:
            log.info(f"Interrupted at {path.name}. Progress saved.")
            break
        except Exception as e:
            log.error(f"Error on {path.name}: {e}")
            failed += 1

        if (i + 1) % 10 == 0:
            log.info(f"── Progress: {i+1}/{len(files)} | ✅{success} ⏭{skipped} ❌{failed}")

    log.info(f"\n{'='*50}")
    log.info(f"Done: ✅{success} generated | ⏭{skipped} skipped | ❌{failed} failed")
    log.info("Re-import to DB: docker exec medmind_backend python -m app.scripts.import_modules")


if __name__ == "__main__":
    main()
