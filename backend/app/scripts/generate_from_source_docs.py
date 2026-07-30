"""Bank-Scale B2 — Generate MCQ questions from ingested source corpus.

Pipeline per question:
  1. Fetch SourceDocuments for the target NCLEX category
  2. Build prompt with source excerpts (attribution/facts-only rules enforced)
  3. Call Groq (content pipeline keys KEY_3/KEY_4)
  4. Parse JSON response
  5. Claim-check: verify key claims against source text (reject if contradicted)
  6. Dedup: skip if question text hash already exists in target module
  7. Save via _mcq_db_writer.save_questions_to_db()
  8. Print run report

Usage:
  python -m app.scripts.generate_from_source_docs \\
      --category pharmacological \\
      --type mcq \\
      --difficulty medium \\
      --count 10

  python -m app.scripts.generate_from_source_docs \\
      --categories pharmacological safe_effective_care physiological_adaptation \\
      --count 5
"""
from __future__ import annotations

import argparse
import asyncio
import itertools
import json
import logging
import os
import re
import time
import uuid
from datetime import datetime

import httpx
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.models import MCQQuestion, Module, SourceDocument
from app.scripts._mcq_db_writer import (
    _question_hash,
    save_questions_to_db,
    NCLEX_SOURCES,
)
from app.services.question_claim_check import verify_question_against_source

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

# ── Groq config (content pipeline keys only) ──────────────────────────────────

def _dedup(lst):
    seen: set = set()
    return [k for k in lst if k and k not in seen and not seen.add(k)]  # type: ignore

GROQ_KEYS = _dedup([
    os.getenv("GROQ_API_KEY_3", ""),
    os.getenv("GROQ_API_KEY_4", ""),
    os.getenv("GROQ_KEY_MODULE_2", ""),
    os.getenv("GROQ_KEY_CASES", ""),
])
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"
_key_reset: dict[str, float] = {k: 0.0 for k in GROQ_KEYS}
_cycle = itertools.cycle(GROQ_KEYS) if GROQ_KEYS else None

GENERATION_PROMPT_VERSION = "b2-v1"

# ── Prompt ────────────────────────────────────────────────────────────────────

_SYSTEM = """You are an expert NCLEX nursing educator writing original exam questions.
IMPORTANT RULES:
1. Write COMPLETELY ORIGINAL questions — do not copy or paraphrase any existing question bank.
2. Use the provided source documents as your factual basis only.
3. For sources marked FACTS_ONLY: formulate entirely in your own words, do not reproduce source text.
4. For sources marked TEXT_REUSE_OK: you may paraphrase with attribution in the explanation.
5. Each question must have a realistic clinical scenario, 4 options (A-D), and one correct answer.
6. Include per-option rationales (why each option is correct or incorrect).
Return ONLY a JSON array."""

def _build_prompt(
    category: str,
    question_type: str,
    difficulty: str,
    docs: list[dict],
    count: int,
) -> str:
    doc_blocks = []
    for i, doc in enumerate(docs[:6]):
        reuse = "TEXT_REUSE_OK" if doc.get("text_reuse_allowed") else "FACTS_ONLY"
        excerpt = doc["full_text"][:1200]
        doc_blocks.append(
            f"--- Source {i+1} [{reuse}] ({doc['source_slug']}): {doc['title'][:80]} ---\n{excerpt}"
        )
    sources_text = "\n\n".join(doc_blocks)

    q_type_instruction = {
        "mcq": "standard single-best-answer MCQ",
        "sata": "Select All That Apply (SATA) — multiple correct answers, list in correct_answers as array",
        "calculation": "dose/IV calculation — include numeric_answer and numeric_unit",
        "ordered": "drag-and-drop ordering — provide correct_order array of option keys",
    }.get(question_type, "standard single-best-answer MCQ")

    return f"""{_SYSTEM}

NCLEX Category: {category}
Question type: {q_type_instruction}
Difficulty: {difficulty}
Generate: {count} questions

Source documents (use as factual basis):
{sources_text}

Return a JSON array of {count} question objects, each with:
{{
  "question": "Clinical scenario question stem",
  "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
  "correct": "A",
  "correct_answers": null,
  "correct_order": null,
  "numeric_answer": null,
  "numeric_unit": null,
  "explanation": "Detailed explanation citing source facts",
  "rationales": {{"A": {{"text": "...", "why": "correct"}}, "B": {{"text": "...", "why": "incorrect"}}, ...}},
  "key_takeaway": "One-sentence memory hook",
  "test_taking_tip": "Strategy tip",
  "difficulty": "{difficulty}",
  "nclex_client_needs": "{category}",
  "question_type": "{question_type}",
  "tags": ["tag1", "tag2"],
  "source_doc_titles": ["Source title used"]
}}

Return ONLY the JSON array. No markdown, no extra text."""


# ── Groq caller ───────────────────────────────────────────────────────────────

async def _groq_generate(prompt: str) -> str | None:
    if not _cycle:
        logger.warning("No Groq content keys configured — cannot generate")
        return None
    for _ in range(len(GROQ_KEYS) * 3):
        key = next(_cycle)
        wait = _key_reset.get(key, 0) - time.time()
        if wait > 120:
            continue
        if wait > 0:
            await asyncio.sleep(wait + 1)
        try:
            async with httpx.AsyncClient(timeout=90) as c:
                r = await c.post(
                    GROQ_URL,
                    headers={"Authorization": f"Bearer {key}"},
                    json={
                        "model": GROQ_MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 4000,
                        "temperature": 0.7,
                    },
                )
            if r.status_code == 429:
                m = re.search(r"in ([\d.]+)s", r.text)
                _key_reset[key] = time.time() + (float(m.group(1)) if m else 60)
                continue
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.debug("Groq error: %s", e)
            await asyncio.sleep(2)
    return None


# ── Parse JSON from LLM response ──────────────────────────────────────────────

def parse_questions(raw: str) -> list[dict]:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"```[a-z]*\n?", "", raw).strip().rstrip("`").strip()
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    if not m:
        return []
    try:
        questions = json.loads(m.group())
        return questions if isinstance(questions, list) else []
    except Exception as e:
        logger.warning("JSON parse failed: %s", e)
        return []


# ── Category → module resolver ────────────────────────────────────────────────

# Map each NCLEX category to the best existing NURSE-* module code
_CATEGORY_TO_MODULE: dict[str, str] = {
    "pharmacological": "NURSE-002",
    "safe_effective_care": "NURSE-004",
    "physiological_adaptation": "NURSE-005",
    "reduction_risk": "NURSE-007",
    "health_promotion": "NURSE-009",
    "psychosocial": "NURSE-010",
    "basic_care": "NURSE-001",
}


async def resolve_module_id(category: str) -> uuid.UUID:
    """Return module_id for category; create a B2 module if no match exists."""
    from app.models.models import Module as _Mod
    code = _CATEGORY_TO_MODULE.get(category, f"B2-{category.upper()[:20]}")
    async with AsyncSessionLocal() as db:
        row = (await db.execute(
            select(_Mod.id).where(_Mod.code == code)
        )).scalar_one_or_none()
        if row:
            return row
        # Create a placeholder module for B2-generated questions
        slug_title = category.replace("_", " ").title()
        mod = _Mod(
            code=code,
            title=f"NCLEX: {slug_title} (Source-Generated)",
            title_en=f"NCLEX: {slug_title} (Source-Generated)",
            description=f"Questions generated from open-source documents for NCLEX category: {category}",
            level=3,
            level_label="Advanced",
            is_nursing=True,
            is_published=False,  # not public until reviewed
        )
        db.add(mod)
        await db.commit()
        await db.refresh(mod)
        return mod.id


# ── Dedup check ───────────────────────────────────────────────────────────────

async def get_existing_hashes(module_id: uuid.UUID) -> set[str]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(MCQQuestion.question).where(MCQQuestion.module_id == module_id)
        )
        return {_question_hash(row[0]) for row in result.fetchall() if row[0]}


# ── Fetch source docs ─────────────────────────────────────────────────────────

async def fetch_docs_for_category(category: str) -> list[dict]:
    """Return SourceDocument rows for a category as plain dicts (with text_reuse_allowed)."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(SourceDocument, "content_sources.text_reuse_allowed")
            .join(
                "content_sources",  # type: ignore[arg-type]
                SourceDocument.source_slug == "content_sources.slug",
                isouter=False,
            )
            .where(SourceDocument.nclex_category == category)
            .order_by(SourceDocument.downloaded_at.desc())
            .limit(10)
        )
        rows = result.fetchall()

    if not rows:
        return []
    # rows = (SourceDocument, text_reuse_allowed)
    docs = []
    for sd, reuse in rows:
        docs.append({
            "source_slug": sd.source_slug,
            "title": sd.title,
            "url": sd.url,
            "full_text": sd.full_text,
            "text_reuse_allowed": bool(reuse),
        })
    return docs


async def fetch_docs_simple(category: str) -> list[dict]:
    """Fetch SourceDocuments for category using explicit join query."""
    from sqlalchemy.orm import aliased
    from app.models.models import ContentSource

    async with AsyncSessionLocal() as db:
        stmt = (
            select(SourceDocument, ContentSource.text_reuse_allowed)
            .join(ContentSource, SourceDocument.source_slug == ContentSource.slug)
            .where(SourceDocument.nclex_category == category)
            .order_by(SourceDocument.downloaded_at.desc())
            .limit(10)
        )
        result = await db.execute(stmt)
        rows = result.fetchall()

    docs = []
    for sd, reuse in rows:
        docs.append({
            "source_slug": sd.source_slug,
            "title": sd.title,
            "url": sd.url,
            "full_text": sd.full_text,
            "text_reuse_allowed": bool(reuse),
        })
    return docs


# ── Source refs builder ───────────────────────────────────────────────────────

def build_source_refs(docs: list[dict], question: dict) -> list[dict]:
    """Build source_refs list linking question to specific source documents used."""
    used_titles = set(question.get("source_doc_titles") or [])
    refs = []
    for doc in docs:
        if not used_titles or doc["title"] in used_titles or not used_titles:
            refs.append({
                "source_slug": doc["source_slug"],
                "name": doc["title"],
                "url": doc.get("url", ""),
                "text_reuse_allowed": doc.get("text_reuse_allowed", False),
            })
    # Also include standard NCLEX refs
    refs += NCLEX_SOURCES[:2]
    return refs[:5]


# ── Main generation function ──────────────────────────────────────────────────

async def generate_for_category(
    category: str,
    question_type: str = "mcq",
    difficulty: str = "medium",
    count: int = 5,
    module_id: uuid.UUID | None = None,
    run_claim_check: bool = True,
) -> dict:
    """Generate questions for one category. Returns run report dict."""
    report = {
        "category": category,
        "question_type": question_type,
        "difficulty": difficulty,
        "requested": count,
        "generated_raw": 0,
        "claim_failed": 0,
        "duplicate": 0,
        "saved": 0,
        "errors": [],
    }

    # 1. Fetch source documents
    docs = await fetch_docs_simple(category)
    if not docs:
        report["errors"].append(f"No source documents for category {category!r} — run ingest first")
        logger.warning("No docs for %s — skipping", category)
        return report

    logger.info("[%s] %d source docs available", category, len(docs))

    # 2. Build prompt and call Groq
    prompt = _build_prompt(category, question_type, difficulty, docs, count)
    raw = await _groq_generate(prompt)
    if not raw:
        report["errors"].append("Groq generation failed (no keys or all rate-limited)")
        return report

    # 3. Parse
    questions = parse_questions(raw)
    report["generated_raw"] = len(questions)
    if not questions:
        report["errors"].append("Could not parse JSON from LLM response")
        return report

    logger.info("[%s] parsed %d questions", category, len(questions))

    # 4. Resolve target module
    if module_id is None:
        module_id = await resolve_module_id(category)

    # 5. Existing hashes for dedup
    existing_hashes = await get_existing_hashes(module_id)

    # 6. Filter: claim check + dedup
    accepted: list[dict] = []
    # Merge all source texts for claim checking
    combined_source_text = " ".join(d["full_text"][:2000] for d in docs[:3])

    for q in questions:
        q_text = (q.get("question") or "").strip()
        if not q_text:
            continue

        # Dedup
        if _question_hash(q_text) in existing_hashes:
            report["duplicate"] += 1
            logger.debug("Duplicate skipped: %s…", q_text[:60])
            continue

        # Claim check (only when Groq keys available and run_claim_check=True)
        if run_claim_check and combined_source_text:
            explanation = q.get("explanation") or ""
            check = await verify_question_against_source(q_text, explanation, combined_source_text)
            if not check["passed"]:
                report["claim_failed"] += 1
                logger.info("Claim check REJECTED: %s", check.get("rejected_reason"))
                continue

        # Tag with prompt version and source refs
        q["generation_prompt_version"] = GENERATION_PROMPT_VERSION
        accepted.append(q)
        existing_hashes.add(_question_hash(q_text))

    if not accepted:
        logger.info("[%s] no questions passed filters", category)
        return report

    # 7. Build source_refs and save
    source_refs = build_source_refs(docs, accepted[0])
    saved, skipped = await save_questions_to_db(
        accepted,
        module_id,
        source_refs,
        run_verification=True,
        print_fn=lambda msg: logger.info(msg),
    )
    report["saved"] = saved
    report["duplicate"] += skipped
    logger.info("[%s] saved=%d  claim_failed=%d  dup=%d",
                category, saved, report["claim_failed"], report["duplicate"])
    return report


# ── CLI entry point ───────────────────────────────────────────────────────────

async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", help="Single NCLEX category")
    parser.add_argument("--categories", nargs="+", help="Multiple categories")
    parser.add_argument("--type", dest="qtype", default="mcq",
                        choices=["mcq", "sata", "ordered", "calculation"])
    parser.add_argument("--difficulty", default="medium",
                        choices=["easy", "medium", "hard"])
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--no-claim-check", action="store_true")
    args = parser.parse_args()

    cats = args.categories or ([args.category] if args.category else [
        "pharmacological", "safe_effective_care", "physiological_adaptation"
    ])

    reports = []
    for cat in cats:
        r = await generate_for_category(
            category=cat,
            question_type=args.qtype,
            difficulty=args.difficulty,
            count=args.count,
            run_claim_check=not args.no_claim_check,
        )
        reports.append(r)

    # Print report
    print("\n=== Generation Report ===")
    total_saved = total_failed = total_dup = 0
    for r in reports:
        print(
            f"  {r['category']:30} "
            f"raw={r['generated_raw']:3}  "
            f"claim_failed={r['claim_failed']:2}  "
            f"dup={r['duplicate']:2}  "
            f"saved={r['saved']:3}"
        )
        if r["errors"]:
            for e in r["errors"]:
                print(f"    ERROR: {e}")
        total_saved += r["saved"]
        total_failed += r["claim_failed"]
        total_dup += r["duplicate"]
    print(f"\n  TOTAL  saved={total_saved}  claim_failed={total_failed}  duplicates={total_dup}")


if __name__ == "__main__":
    asyncio.run(main())
