"""Generate MCQ questions for specialty modules (CARDIO, PULM, DERM, etc.) from existing content.

Picks modules with content but < TARGET_QUESTIONS, generates up to TARGET_QUESTIONS per module,
saves to DB with verification and source_refs. Idempotent — skips modules already at target.

Usage:
  python -m app.scripts.generate_specialty_mcq          # next pending module
  python -m app.scripts.generate_specialty_mcq --all    # all pending modules sequentially
  python -m app.scripts.generate_specialty_mcq CARDIO-002  # specific module
  python -m app.scripts.generate_specialty_mcq --status    # show counts
  python -m app.scripts.generate_specialty_mcq --dry-run   # preview only
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
from sqlalchemy import func, select, text

from app.core.database import AsyncSessionLocal
from app.models.models import MCQQuestion, Module
from app.scripts._mcq_db_writer import save_questions_to_db

GROQ_KEYS = [k for k in [
    os.getenv("GROQ_KEY_MODULE_2", ""),
    os.getenv("GROQ_KEY_CASES", ""),
    os.getenv("GROQ_API_KEY_3", ""),
] if k]
_seen: set = set()
GROQ_KEYS = [k for k in GROQ_KEYS if not (k in _seen or _seen.add(k))]

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
TARGET_QUESTIONS = 80
MIN_THRESHOLD = 80  # generate for modules with fewer than this many questions
# Generate in batches of 20 per Groq call (fits within context + rate limits)
BATCH_SIZE = 20
# Delay between batches (seconds) to stay within ~6000 TPM Groq limit
INTER_BATCH_DELAY = 15

# Specialty→clinical guideline source map
SPECIALTY_SOURCES: dict[str, list[dict]] = {
    "CARDIO": [
        {"name": "ESC Guidelines on Acute Coronary Syndromes (2023)", "url": "https://www.escardio.org/Guidelines/Clinical-Practice-Guidelines/Acute-Coronary-Syndromes", "type": "guideline"},
        {"name": "ACC/AHA Heart Failure Guidelines (2022)", "url": "https://www.acc.org/guidelines", "type": "guideline"},
    ],
    "PULM": [
        {"name": "GOLD COPD Guidelines (2024)", "url": "https://goldcopd.org/2024-gold-report/", "type": "guideline"},
        {"name": "GINA Asthma Guidelines (2023)", "url": "https://ginasthma.org/gina-reports/", "type": "guideline"},
    ],
    "GASTRO": [
        {"name": "American College of Gastroenterology Clinical Guidelines", "url": "https://gi.org/practice/clinical-guidelines/", "type": "guideline"},
        {"name": "EASL Clinical Practice Guidelines on Liver Disease", "url": "https://easl.eu/publications/clinical-guidelines/", "type": "guideline"},
    ],
    "NEPH": [
        {"name": "KDIGO Clinical Practice Guideline for CKD (2024)", "url": "https://kdigo.org/guidelines/ckd-evaluation-and-management/", "type": "guideline"},
        {"name": "KDIGO AKI Clinical Practice Guideline", "url": "https://kdigo.org/guidelines/acute-kidney-injury/", "type": "guideline"},
    ],
    "ENDO": [
        {"name": "ADA Standards of Medical Care in Diabetes (2024)", "url": "https://diabetesjournals.org/care/issue/47/Supplement_1", "type": "guideline"},
        {"name": "Endocrine Society Clinical Practice Guidelines", "url": "https://www.endocrine.org/clinical-practice-guidelines", "type": "guideline"},
    ],
    "DERM": [
        {"name": "American Academy of Dermatology Clinical Guidelines", "url": "https://www.aad.org/member/clinical-quality/guidelines", "type": "guideline"},
        {"name": "BAD British Journal of Dermatology Guidelines", "url": "https://www.bad.org.uk/clinical-services/clinical-guidelines/", "type": "guideline"},
    ],
    "RHEUM": [
        {"name": "ACR Clinical Practice Guidelines (Rheumatology)", "url": "https://www.rheumatology.org/Practice-Quality/Clinical-Support/Clinical-Practice-Guidelines", "type": "guideline"},
        {"name": "EULAR Recommendations", "url": "https://www.eular.org/eular_recommendations_management.cfm", "type": "guideline"},
    ],
    "HEMA": [
        {"name": "ASH Clinical Practice Guidelines (Hematology)", "url": "https://www.hematology.org/education/clinicians/guidelines-and-quality-care", "type": "guideline"},
        {"name": "EHA Guidelines", "url": "https://ehaweb.org/education/guidelines-recommendations/", "type": "guideline"},
    ],
    "ONC": [
        {"name": "NCCN Clinical Practice Guidelines in Oncology", "url": "https://www.nccn.org/guidelines/category_1", "type": "guideline"},
        {"name": "ESMO Clinical Practice Guidelines", "url": "https://www.esmo.org/guidelines", "type": "guideline"},
    ],
    "NEURO": [
        {"name": "AHA/ASA Stroke Guidelines (2021)", "url": "https://www.ahajournals.org/doi/10.1161/STR.0000000000000375", "type": "guideline"},
        {"name": "European Stroke Organisation Guidelines", "url": "https://eso-stroke.org/eso-guidelines/", "type": "guideline"},
    ],
    "EMERG": [
        {"name": "ERC Resuscitation Guidelines (2021)", "url": "https://www.erc.edu/guidelines", "type": "guideline"},
        {"name": "ACEP Clinical Policies", "url": "https://www.acep.org/clinical-and-practice-management/acep-clinical-policies/", "type": "guideline"},
    ],
    "ICU": [
        {"name": "ESICM Critical Care Guidelines", "url": "https://www.esicm.org/education/clinical-guidelines/", "type": "guideline"},
        {"name": "Society of Critical Care Medicine Guidelines", "url": "https://www.sccm.org/clinical-resources/guidelines", "type": "guideline"},
    ],
    "INFECT": [
        {"name": "IDSA Infectious Disease Practice Guidelines", "url": "https://www.idsociety.org/practice-guideline/practice-guidelines/", "type": "guideline"},
        {"name": "WHO Antimicrobial Resistance Action Plan", "url": "https://www.who.int/publications/i/item/9789241509763", "type": "guideline"},
    ],
    "PHARM": [
        {"name": "BNF British National Formulary", "url": "https://bnf.nice.org.uk/", "type": "textbook"},
        {"name": "Katzung Basic & Clinical Pharmacology (15th ed.)", "url": "https://accesspharmacy.mhmedical.com/book.aspx?bookid=2988", "type": "textbook"},
    ],
    "PSYCH": [
        {"name": "APA DSM-5-TR Diagnostic and Statistical Manual", "url": "https://www.psychiatry.org/psychiatrists/practice/dsm", "type": "textbook"},
        {"name": "NICE Mental Health Guidelines", "url": "https://www.nice.org.uk/guidance/conditions-and-diseases/mental-health-and-behavioural-conditions", "type": "guideline"},
    ],
    "ORTHO": [
        {"name": "AAOS Clinical Practice Guidelines (Orthopaedics)", "url": "https://www.aaos.org/quality/clinical-quality-programs/clinical-practice-guidelines/", "type": "guideline"},
        {"name": "BOA British Orthopaedic Association Guidelines", "url": "https://www.boa.ac.uk/resources/standards-of-care.html", "type": "guideline"},
    ],
    "UROL": [
        {"name": "EAU Guidelines on Urological Diseases (2024)", "url": "https://uroweb.org/guidelines/", "type": "guideline"},
        {"name": "AUA American Urological Association Guidelines", "url": "https://www.auanet.org/guidelines-and-quality/guidelines", "type": "guideline"},
    ],
    "NEPH_UROL": [
        {"name": "KDIGO CKD Guidelines", "url": "https://kdigo.org/guidelines/ckd-evaluation-and-management/", "type": "guideline"},
    ],
    "SURG": [
        {"name": "ACS NSQIP Surgical Outcomes Guidelines", "url": "https://www.facs.org/quality-programs/data-and-registries/acs-nsqip/", "type": "guideline"},
    ],
}

GENERIC_SOURCES = [
    {"name": "Harrison's Principles of Internal Medicine (21st ed.)", "url": "https://accessmedicine.mhmedical.com/book.aspx?bookid=3095", "type": "textbook"},
    {"name": "UpToDate Clinical Decision Support", "url": "https://www.uptodate.com/", "type": "guideline"},
]


def get_sources_for_module(code: str) -> list[dict]:
    prefix = code.split("-")[0].split("_")[0]
    return SPECIALTY_SOURCES.get(prefix, []) + GENERIC_SOURCES


MCQ_PROMPT = """\
You are an expert medical educator writing board-style exam questions.
Generate {count} clinical MCQ questions based on the following module content.

Module: {title}
Specialty: {specialty}

Content summary:
{content_text}

Rules:
- Each question must have exactly 4 options (A, B, C, D)
- Only ONE option is correct
- Use realistic clinical scenarios (patient presentation, lab results, vitals)
- Explanation must justify the correct answer AND briefly explain why each distractor is wrong
- Difficulty: {easy} easy, {medium} medium, {hard} hard
- Questions must be based ONLY on the provided content

Return ONLY a valid JSON array:
[
  {{
    "question": "A 54-year-old patient presents with...",
    "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
    "correct": "B",
    "explanation": "B is correct because... A is incorrect because...",
    "rationales": {{
      "A": {{"text": "Clinical reasoning for A.", "why": "incorrect"}},
      "B": {{"text": "Clinical reasoning for B.", "why": "correct"}},
      "C": {{"text": "Clinical reasoning for C.", "why": "incorrect"}},
      "D": {{"text": "Clinical reasoning for D.", "why": "incorrect"}}
    }},
    "key_takeaway": "One-sentence core principle tested.",
    "test_taking_tip": "One-sentence tip for eliminating distractors.",
    "difficulty": "medium",
    "tags": ["tag1", "tag2"]
  }}
]"""


def _extract_text(content: dict | list | str | None, max_chars: int = 4000) -> str:
    if not content:
        return ""
    if isinstance(content, str):
        return content[:max_chars]
    if isinstance(content, list):
        return " ".join(_extract_text(item, max_chars) for item in content)[:max_chars]
    if isinstance(content, dict):
        parts = []
        for key in ["intro", "sections", "key_points", "clinical_pearl", "text", "content", "body"]:
            v = content.get(key)
            if v:
                parts.append(_extract_text(v, max_chars // 3))
        return " ".join(parts)[:max_chars]
    return str(content)[:max_chars]


def _extract_module_text(content: dict | None) -> str:
    if not content:
        return ""
    lessons = content.get("lessons", [])
    texts = []
    for lesson in lessons[:4]:  # max 4 lessons
        lesson_content = lesson.get("content", {}) or lesson.get("body", "")
        texts.append(f"=== {lesson.get('title', 'Lesson')} ===\n{_extract_text(lesson_content, 800)}")
    return "\n\n".join(texts)[:4000]


_reset_at: dict[str, float] = {k: 0.0 for k in GROQ_KEYS}


async def _groq_call(prompt: str, max_tokens: int = 6000) -> str | None:
    while True:
        if not GROQ_KEYS:
            return None
        key = min(GROQ_KEYS, key=lambda k: _reset_at[k])
        wait = _reset_at[key] - time.time()
        if wait > 120:
            print(f"  ⚠ All Groq keys limited — exiting")
            return None
        if wait > 0:
            print(f"  Waiting {wait:.0f}s for Groq key…")
            await asyncio.sleep(wait + 1)
        try:
            async with httpx.AsyncClient(timeout=60) as c:
                resp = await c.post(
                    GROQ_URL,
                    headers={"Authorization": f"Bearer {key}"},
                    json={"model": GROQ_MODEL,
                          "messages": [{"role": "user", "content": prompt}],
                          "max_tokens": max_tokens, "temperature": 0.7},
                )
            if resp.status_code == 429:
                try:
                    wait_s = float(re.search(r"in ([\d.]+)s", resp.json()["error"]["message"]).group(1))
                except Exception:
                    wait_s = 60.0
                _reset_at[key] = time.time() + wait_s
                print(f"  Rate limited {wait_s:.0f}s")
                continue
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"  Groq error: {e}")
            await asyncio.sleep(3)
            return None


def _parse_questions(raw: str) -> list[dict]:
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        return []
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return []


async def get_pending_modules(db) -> list[tuple[str, str, str, str]]:
    result = await db.execute(text("""
        SELECT m.id::text, m.code, m.title, m.content::text
        FROM modules m
        LEFT JOIN (
            SELECT module_id, COUNT(*) as cnt
            FROM mcq_questions GROUP BY module_id
        ) q ON q.module_id = m.id
        WHERE m.is_published = TRUE
          AND m.content IS NOT NULL
          AND m.content::text NOT IN ('null', '{}', '[]', '')
          AND m.code NOT LIKE 'NURSE%'
          AND m.code NOT LIKE 'VET%'
          AND m.code NOT LIKE 'PET%'
          AND m.code NOT LIKE 'GULF%'
          AND COALESCE(q.cnt, 0) < :threshold
        ORDER BY COALESCE(q.cnt, 0) ASC, m.code
    """), {"threshold": MIN_THRESHOLD})
    return result.fetchall()


async def _current_question_count(module_id: str) -> int:
    """How many questions this module already has."""
    from sqlalchemy import text as _text
    import uuid as _uuid
    async with AsyncSessionLocal() as db:
        r = await db.execute(_text(
            "SELECT COUNT(*) FROM mcq_questions WHERE module_id = :mid"
        ), {"mid": _uuid.UUID(module_id)})
        return r.scalar() or 0


async def generate_for_module(module_id: str, code: str, title: str, content_json: str,
                               dry_run: bool = False) -> tuple[int, int]:
    try:
        content = json.loads(content_json) if isinstance(content_json, str) else content_json
    except Exception:
        content = {}

    content_text = _extract_module_text(content)
    if not content_text.strip():
        print(f"  [{code}] No extractable content — skipping")
        return 0, 0

    existing = await _current_question_count(module_id)
    needed = max(0, TARGET_QUESTIONS - existing)
    if needed == 0:
        print(f"  [{code}] Already has {existing} questions — skipping")
        return 0, 0

    specialty = code.split("-")[0]
    import uuid
    mod_uuid = uuid.UUID(module_id)
    source_refs = get_sources_for_module(code)

    total_saved = total_skipped = 0
    batch_num = 0

    while needed > 0:
        batch_count = min(BATCH_SIZE, needed)
        batch_num += 1
        prompt = MCQ_PROMPT.format(
            count=batch_count,
            title=title,
            specialty=specialty,
            content_text=content_text,
            easy=max(1, batch_count // 4),
            medium=max(1, batch_count // 2),
            hard=max(1, batch_count // 4),
        )

        print(f"  [{code}] Batch {batch_num}: generating {batch_count} questions (need {needed} more)…")
        raw = await _groq_call(prompt)
        if raw is None:
            print(f"  [{code}] Groq keys exhausted — stopping (saved {total_saved} so far)")
            break

        questions = _parse_questions(raw)
        print(f"  [{code}] Batch {batch_num}: parsed {len(questions)} questions")

        if dry_run:
            for q in questions[:2]:
                print(f"    Q: {q.get('question', '')[:80]}")
            total_saved += len(questions)
            needed -= batch_count
            continue

        if not questions:
            print(f"  [{code}] Empty batch — stopping")
            break

        saved, skipped = await save_questions_to_db(questions, mod_uuid, source_refs)
        total_saved += saved
        total_skipped += skipped
        needed -= saved + skipped  # count what was attempted
        print(f"  [{code}] Batch {batch_num}: saved {saved} | skipped {skipped} | remaining target: {needed}")

        if needed > 0:
            await asyncio.sleep(INTER_BATCH_DELAY)

    print(f"  [{code}] Done — total saved: {total_saved} | skipped: {total_skipped}")
    return total_saved, total_skipped


async def main_async(
    module_code: str | None = None,
    dry_run: bool = False,
    show_status: bool = False,
    run_all: bool = False,
) -> None:
    if not GROQ_KEYS:
        print("ERROR: No Groq generation keys configured (GROQ_KEY_MODULE_2, GROQ_KEY_CASES, GROQ_API_KEY_3)")
        sys.exit(1)

    async with AsyncSessionLocal() as db:
        pending = await get_pending_modules(db)

    if show_status:
        print(f"Modules with < {MIN_THRESHOLD} questions: {len(pending)}")
        for mid, code, title, _ in pending[:20]:
            print(f"  {code:<20} {title[:50]}")
        if len(pending) > 20:
            print(f"  ... and {len(pending) - 20} more")
        return

    if module_code:
        row = next((r for r in pending if r[1] == module_code), None)
        if not row:
            async with AsyncSessionLocal() as db:
                r = await db.execute(select(Module).where(Module.code == module_code))
                m = r.scalar_one_or_none()
            if not m:
                print(f"Module {module_code!r} not found")
                sys.exit(1)
            import json as _json
            content_str = _json.dumps(m.content) if m.content else "{}"
            saved, skipped = await generate_for_module(str(m.id), m.code, m.title, content_str, dry_run)
        else:
            mid, code, title, content_json = row
            saved, skipped = await generate_for_module(mid, code, title, content_json, dry_run)
        print(f"\nDone — saved: {saved} | skipped: {skipped}")

    elif run_all:
        if not pending:
            print("No modules pending — all have enough questions")
            return
        print(f"Processing ALL {len(pending)} pending modules sequentially…")
        grand_saved = grand_skipped = 0
        for i, (mid, code, title, content_json) in enumerate(pending, 1):
            print(f"\n[{i}/{len(pending)}] {code} — {title}")
            saved, skipped = await generate_for_module(mid, code, title, content_json, dry_run)
            grand_saved += saved
            grand_skipped += skipped
            # Brief pause between modules to avoid burst rate-limiting
            if i < len(pending):
                await asyncio.sleep(5)
        print(f"\n=== ALL DONE — total saved: {grand_saved} | skipped: {grand_skipped} ===")

    else:
        if not pending:
            print("No modules pending — all have enough questions")
            return
        mid, code, title, content_json = pending[0]
        print(f"Processing next pending module: {code} — {title}")
        saved, skipped = await generate_for_module(mid, code, title, content_json, dry_run)
        print(f"\nDone — saved: {saved} | skipped: {skipped}")


def main() -> None:
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    show_status = "--status" in args
    run_all = "--all" in args
    args = [a for a in args if not a.startswith("--")]
    module_code = args[0].upper() if args else None
    asyncio.run(main_async(module_code, dry_run, show_status, run_all))


if __name__ == "__main__":
    main()
