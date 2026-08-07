"""Shared MCQ DB writer with verification and source tracing.

Used by generate_nclex_questions.py and generate_gulf_questions.py.

Pipeline per batch:
  1. verify_batch()  — second LLM call fact-checks correctness and clinical accuracy
  2. save_to_db()    — idempotent upsert: skip exact duplicates by question text hash
  3. Sources are embedded as source_refs JSONB on each MCQQuestion row

Verification model: same Groq pool as the enrich script (KEY_1/2/6 tutor + content).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.models import MCQQuestion, Module

log = logging.getLogger(__name__)

# ── Official source reference banks ──────────────────────────────────────────

NCLEX_SOURCES: list[dict] = [
    {
        "name": "NCSBN NCLEX-RN Test Plan 2023",
        "url": "https://www.ncsbn.org/publications/nclex-rn-examination-test-plan-2023",
        "type": "regulatory",
    },
    {
        "name": "Saunders Comprehensive Review for the NCLEX-RN (Silvestri)",
        "url": "https://evolve.elsevier.com/cs/product/9780323358415",
        "type": "textbook",
    },
    {
        "name": "Lippincott Manual of Nursing Practice (10th ed.)",
        "url": "https://shop.lww.com/Lippincott-Manual-of-Nursing-Practice/p/9781496306081",
        "type": "textbook",
    },
    {
        "name": "Potter & Perry's Fundamentals of Nursing (10th ed.)",
        "url": "https://evolve.elsevier.com/cs/product/9780323749114",
        "type": "textbook",
    },
    {
        "name": "Ignatavicius: Medical-Surgical Nursing (10th ed.)",
        "url": "https://evolve.elsevier.com/cs/product/9780323612425",
        "type": "textbook",
    },
]

# Gulf-specific references keyed by exam slug
GULF_SOURCES: dict[str, list[dict]] = {
    "_common": [
        {
            "name": "WHO Clinical Nursing Standards",
            "url": "https://www.who.int/health-topics/nursing",
            "type": "guideline",
        },
        {
            "name": "ICN Code of Ethics for Nurses (2021)",
            "url": "https://www.icn.ch/system/files/2021-10/ICN_Code-of-Ethics_EN_Web_0.pdf",
            "type": "guideline",
        },
    ],
    "snle": [
        {"name": "SCHS SNLE Examination Blueprint",
         "url": "https://www.scfhs.org.sa/en/Examinations/Pages/NLE.aspx", "type": "regulatory"},
    ],
    "dha": [
        {"name": "DHA Healthcare Professionals Examination",
         "url": "https://www.dha.gov.ae/en/HealthRegulation/Pages/examination.aspx", "type": "regulatory"},
    ],
    "qchp": [
        {"name": "QCHP Examination & Licensing Guidelines",
         "url": "https://www.qchp.org.qa/en/HealthcareRegistration/Pages/ExamAndLicense.aspx", "type": "regulatory"},
    ],
    "omsb": [
        {"name": "OMSB Licensing Examinations",
         "url": "https://www.omsb.org/licensing-examination/", "type": "regulatory"},
    ],
    "nhra": [
        {"name": "NHRA Health Professionals Classification",
         "url": "https://www.nhra.bh/health-professionals", "type": "regulatory"},
    ],
    "mohuae": [
        {"name": "MOH UAE Health Professional Licensing",
         "url": "https://www.mohap.gov.ae/en/services/Pages/226.aspx", "type": "regulatory"},
    ],
    "haad": [
        {"name": "DOH Abu Dhabi Health Professional Licensing",
         "url": "https://www.doh.gov.ae/en/regulation/healthcareprofessionals", "type": "regulatory"},
    ],
}


def get_gulf_sources(exam_slug: str) -> list[dict]:
    slug_refs = GULF_SOURCES.get(exam_slug, [])
    return GULF_SOURCES["_common"] + slug_refs


# ── Groq verification client ──────────────────────────────────────────────────

def _dedup(keys: list[str]) -> list[str]:
    seen: set[str] = set()
    return [k for k in keys if k and not (k in seen or seen.add(k))]  # type: ignore


VERIFY_GROQ_KEYS = _dedup([
    os.getenv("GROQ_API_KEY", ""),
    os.getenv("GROQ_API_KEY_2", ""),
    os.getenv("GROQ_API_KEY_6", ""),
    os.getenv("GROQ_API_KEY_3", ""),
    os.getenv("GROQ_KEY_MODULE_2", ""),
    os.getenv("GROQ_KEY_CASES", ""),
])
GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

_reset_at: dict[str, float] = {k: 0.0 for k in VERIFY_GROQ_KEYS}


async def _groq_call(prompt: str, max_tokens: int = 2000) -> str | None:
    if not VERIFY_GROQ_KEYS:
        return None
    for _ in range(len(VERIFY_GROQ_KEYS) * 3):
        key = min(VERIFY_GROQ_KEYS, key=lambda k: _reset_at[k])
        wait = _reset_at[key] - time.time()
        if wait > 60:
            log.warning("All verify keys limited >60s — skipping verification")
            return None
        if wait > 0:
            await asyncio.sleep(wait + 1)
        try:
            async with httpx.AsyncClient(timeout=45) as c:
                resp = await c.post(
                    GROQ_URL,
                    headers={"Authorization": f"Bearer {key}"},
                    json={"model": GROQ_MODEL,
                          "messages": [{"role": "user", "content": prompt}],
                          "max_tokens": max_tokens, "temperature": 0.1},
                )
            if resp.status_code == 429:
                try:
                    wait = float(re.search(r"in ([\d.]+)s",
                                 resp.json()["error"]["message"]).group(1))  # type: ignore
                except Exception:
                    wait = 60.0
                _reset_at[key] = time.time() + wait
                continue
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            log.debug("Verify Groq error: %s", e)
            await asyncio.sleep(2)
    return None


# ── Verification ─────────────────────────────────────────────────────────────

VERIFY_PROMPT = """You are a senior NCLEX nursing educator and clinical accuracy reviewer.

Review the following nursing exam questions and verify:
1. The marked correct answer is clinically accurate and defensible
2. Distractors are plausible (not obviously silly)
3. Clinical scenario is realistic
4. The explanation correctly justifies the answer
5. No patient safety misinformation

For each question return a JSON object with:
- "idx": the question's array index (0-based)
- "status": "pass" | "warning" | "fail"
- "confidence": 0.0–1.0 (your certainty in the marked correct answer)
- "correct_answer_valid": true | false
- "issues": [] or list of specific problems found
- "suggested_correction": null or a brief correction if the answer is wrong

Questions to review:
{questions_json}

Return ONLY a JSON array of {n} review objects. No markdown, no extra text."""


async def verify_batch(questions: list[dict]) -> list[dict]:
    """Run a second-LLM verification pass on a batch of generated questions.

    Returns list of verification report dicts (one per question, matched by idx).
    Falls back to [{"idx": i, "status": "pending", ...}] if verification fails.
    """
    if not questions:
        return []

    # Compact representation for the verifier (no options → too long)
    compact = [
        {
            "idx": i,
            "question": q.get("question", "")[:200],
            "correct": q.get("correct") or q.get("correct_answers"),
            "explanation": (q.get("explanation") or "")[:300],
            "nclex_category": q.get("nclex_client_needs", ""),
        }
        for i, q in enumerate(questions)
    ]

    prompt = VERIFY_PROMPT.format(
        questions_json=json.dumps(compact, ensure_ascii=False, indent=2),
        n=len(questions),
    )

    raw = await _groq_call(prompt, max_tokens=len(questions) * 200 + 500)
    if not raw:
        return [{"idx": i, "status": "pending", "confidence": None,
                 "correct_answer_valid": None, "issues": [], "suggested_correction": None}
                for i in range(len(questions))]

    # Parse
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        return [{"idx": i, "status": "pending", "confidence": None,
                 "correct_answer_valid": None, "issues": [], "suggested_correction": None}
                for i in range(len(questions))]
    try:
        reports = json.loads(match.group())
        # index by idx for easy lookup
        return reports if isinstance(reports, list) else []
    except Exception:
        return []


# ── Dedup hash ────────────────────────────────────────────────────────────────

def _question_hash(question_text: str) -> str:
    """SHA-1 of the first 200 chars — fast near-duplicate detection."""
    return hashlib.sha1(question_text[:200].encode()).hexdigest()


# ── Main save function ────────────────────────────────────────────────────────

async def save_questions_to_db(
    questions: list[dict],
    module_id: uuid.UUID,
    source_refs: list[dict],
    *,
    run_verification: bool = True,
    print_fn=print,
) -> tuple[int, int]:
    """Save a list of generated questions directly to DB.

    Runs verification pass first (if run_verification=True).
    Skips exact duplicates (by first-200-chars hash within same module).

    Returns (saved_count, skipped_count).
    """
    if not questions:
        return 0, 0

    # Verification pass
    verify_reports: dict[int, dict] = {}
    if run_verification and VERIFY_GROQ_KEYS:
        print_fn(f"    → Verifying {len(questions)} questions…")
        reports = await verify_batch(questions)
        for r in reports:
            verify_reports[r.get("idx", -1)] = r
        fails = sum(1 for r in reports if r.get("status") == "fail")
        if fails:
            print_fn(f"    ⚠ {fails} questions flagged by verifier")

    saved = skipped = 0

    async with AsyncSessionLocal() as db:
        # Fetch existing question texts for this module (dedup)
        existing_result = await db.execute(
            select(MCQQuestion.question).where(MCQQuestion.module_id == module_id)
        )
        existing_hashes = {
            _question_hash(row[0]) for row in existing_result.fetchall() if row[0]
        }

        for i, q in enumerate(questions):
            q_text = q.get("question", "").strip()
            if not q_text:
                skipped += 1
                continue

            if _question_hash(q_text) in existing_hashes:
                skipped += 1
                continue

            report = verify_reports.get(i, {})
            v_status = report.get("status", "pending")
            # Map verifier status to our enum
            db_status = {
                "pass": "ai_verified",
                "warning": "ai_verified",   # warning but not wrong — still usable
                "fail": "flagged",
                "pending": "pending",
            }.get(v_status, "pending")

            qtype = q.get("question_type", "mcq")
            options = q.get("options") or {}
            if not options:
                skipped += 1
                continue

            mcq = MCQQuestion(
                module_id=module_id,
                question=q_text,
                options=options,
                correct=q.get("correct") or "A",
                explanation=q.get("explanation") or "",
                difficulty=q.get("difficulty", "medium"),
                tags=q.get("tags") or [],
                question_type=qtype,
                correct_answers=q.get("correct_answers"),
                correct_order=q.get("correct_order"),
                numeric_answer=float(q["numeric_answer"]) if q.get("numeric_answer") is not None else None,
                numeric_tolerance=float(q.get("numeric_tolerance") or 0.5),
                numeric_unit=q.get("numeric_unit"),
                partial_scoring=bool(q.get("partial_scoring", False)),
                nclex_client_needs=q.get("nclex_client_needs"),
                cjmm_skill=q.get("cjmm_skill"),
                ngn_type=q.get("ngn_type"),
                bowtie_data=q.get("bowtie_data"),
                matrix_data=q.get("matrix_data"),
                rationales=q.get("rationales") or None,
                key_takeaway=q.get("key_takeaway") or None,
                test_taking_tip=q.get("test_taking_tip") or None,
                exam_slugs=q.get("exam_slugs") or None,
                origin=q.get("origin") or None,
                jurisdiction_sensitive=bool(q.get("jurisdiction_sensitive", False)),
                jurisdiction_verified_for=q.get("jurisdiction_verified_for") or None,
                # Traceability
                source_refs=source_refs,
                verification_status=db_status,
                verification_report=report if report else None,
            )
            db.add(mcq)
            existing_hashes.add(_question_hash(q_text))
            saved += 1

        await db.commit()

    return saved, skipped


# ── Gulf module resolver ──────────────────────────────────────────────────────

async def get_or_create_gulf_module(exam_slug: str, exam_name: str) -> uuid.UUID:
    """Return module_id for a Gulf exam, creating the module row if needed."""
    module_code = f"GULF-{exam_slug.upper()}"
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Module).where(Module.code == module_code)
        )
        module = result.scalar_one_or_none()
        if module:
            return module.id

        # Get or create the nursing specialty (id for specialty_id FK)
        # Use module without specialty_id if not found
        new_module = Module(
            code=module_code,
            title=f"{exam_name} — Gulf Prometric Question Bank",
            title_en=f"{exam_name} — Gulf Prometric Question Bank",
            description=(
                f"Practice questions for the {exam_name} licensing examination. "
                f"Content follows the Prometric format with 4-option MCQ clinical scenarios."
            ),
            level=3,
            level_label="Advanced",
            is_fundamental=False,
            is_nursing=True,
            is_published=True,
        )
        db.add(new_module)
        await db.commit()
        await db.refresh(new_module)
        log.info("Created Gulf module: %s (%s)", module_code, new_module.id)
        return new_module.id


async def get_nclex_module_id(module_code: str) -> uuid.UUID | None:
    """Return module_id for a NURSE-* module code."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Module.id).where(Module.code == module_code)
        )
        row = result.scalar_one_or_none()
        return row
