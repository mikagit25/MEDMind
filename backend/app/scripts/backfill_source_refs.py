"""Backfill source_refs (and optional verification) for existing MCQ questions.

All 1185 questions were generated before _mcq_db_writer added source tracing.
This script assigns source_refs based on module prefix, then (optionally) runs
the LLM verification pass on NURSE-* questions.

Usage:
  python -m app.scripts.backfill_source_refs              # source_refs only (fast)
  python -m app.scripts.backfill_source_refs --verify     # + LLM verify NURSE-*
  python -m app.scripts.backfill_source_refs --dry-run    # preview counts only
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select, update

from app.core.database import AsyncSessionLocal
from app.models.models import MCQQuestion, Module
from app.scripts._mcq_db_writer import (
    NCLEX_SOURCES,
    verify_batch,
)

# ── Source reference banks by module prefix ───────────────────────────────────

VET_SOURCES: list[dict] = [
    {
        "name": "Merck Veterinary Manual (11th ed.)",
        "url": "https://www.merckvetmanual.com",
        "type": "textbook",
    },
    {
        "name": "BSAVA Small Animal Formulary (10th ed.)",
        "url": "https://www.bsava.com/Resources/Veterinary-resources/Formulary",
        "type": "textbook",
    },
    {
        "name": "Ettinger & Feldman: Textbook of Veterinary Internal Medicine (8th ed.)",
        "url": "https://www.elsevier.com/books/textbook-of-veterinary-internal-medicine/ettinger/978-0-323-31211-0",
        "type": "textbook",
    },
]

MEDICAL_SOURCES: list[dict] = [
    {
        "name": "Harrison's Principles of Internal Medicine (21st ed.)",
        "url": "https://accessmedicine.mhmedical.com/book.aspx?bookid=3095",
        "type": "textbook",
    },
    {
        "name": "Robbins & Cotran Pathologic Basis of Disease (10th ed.)",
        "url": "https://www.elsevier.com/books/robbins-and-cotran-pathologic-basis-of-disease/kumar/978-0-323-53113-9",
        "type": "textbook",
    },
    {
        "name": "UpToDate — Evidence-Based Clinical Decision Support",
        "url": "https://www.uptodate.com",
        "type": "clinical_resource",
    },
    {
        "name": "WHO Clinical Practice Guidelines",
        "url": "https://www.who.int/publications/guidelines",
        "type": "guideline",
    },
]


def _source_refs_for(module_code: str) -> list[dict]:
    if module_code.startswith("NURSE"):
        return NCLEX_SOURCES
    if module_code.startswith("VET"):
        return VET_SOURCES
    return MEDICAL_SOURCES


# ── Main ──────────────────────────────────────────────────────────────────────

async def run(dry_run: bool = False, run_verify: bool = False) -> None:
    async with AsyncSessionLocal() as db:
        # Load all modules that have questions with NULL source_refs
        result = await db.execute(
            select(Module.id, Module.code).join(MCQQuestion, MCQQuestion.module_id == Module.id)
            .where(MCQQuestion.source_refs.is_(None))
            .distinct()
        )
        modules = result.fetchall()

    if not modules:
        print("✓ All questions already have source_refs.")
        if run_verify:
            # Skip source_refs step, go straight to verification
            pass
        else:
            return

    if modules and dry_run:
        print("\n[DRY RUN] Would update:")
        for module_id, code in modules:
            refs = _source_refs_for(code)
            ref_names = [r["name"][:50] for r in refs[:2]]
            print(f"  {code:<30} → {len(refs)} refs  (e.g. {ref_names[0][:40]})")
        return

    # ── Step 1: Bulk assign source_refs ──────────────────────────────────────

    total_updated = 0
    for module_id, code in modules:
        refs = _source_refs_for(code)
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                update(MCQQuestion)
                .where(MCQQuestion.module_id == module_id, MCQQuestion.source_refs.is_(None))
                .values(source_refs=refs)
                .returning(MCQQuestion.id)
            )
            count = len(result.fetchall())
            await db.commit()
        print(f"  {code:<30} → source_refs set on {count} questions")
        total_updated += count

    if total_updated:
        print(f"\n✓ source_refs backfilled: {total_updated} questions across {len(modules)} modules")

    # ── Step 2: Verification pass for NURSE-* (optional) ─────────────────────

    if not run_verify:
        print("\nVerification pass skipped (run with --verify to enable).")
        print("NURSE-* questions remain verification_status='pending' until verified.")
        return

    print("\n── Running LLM verification pass on NURSE-* questions ──────────────")

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(MCQQuestion)
            .join(Module, MCQQuestion.module_id == Module.id)
            .where(
                Module.code.like("NURSE-%"),
                MCQQuestion.verification_status == "pending",
            )
            .order_by(Module.code, MCQQuestion.id)
        )
        nurse_qs = result.scalars().all()

    if not nurse_qs:
        print("No pending NURSE-* questions to verify.")
        return

    print(f"Verifying {len(nurse_qs)} NURSE-* questions in batches of 10…")

    BATCH = 10
    verified = failed = 0

    for i in range(0, len(nurse_qs), BATCH):
        batch = nurse_qs[i:i + BATCH]
        batch_dicts = [
            {
                "question": q.question or "",
                "correct": q.correct or q.correct_answers,
                "explanation": q.explanation or "",
                "nclex_client_needs": q.nclex_client_needs or "",
            }
            for q in batch
        ]

        print(f"  Batch {i // BATCH + 1}/{(len(nurse_qs) + BATCH - 1) // BATCH} ({len(batch)} questions)…", end=" ", flush=True)
        reports = await verify_batch(batch_dicts)

        by_idx = {r.get("idx", -1): r for r in reports}

        async with AsyncSessionLocal() as db:
            for j, q_obj in enumerate(batch):
                report = by_idx.get(j, {})
                v_status = report.get("status", "pending")
                db_status = {
                    "pass": "ai_verified",
                    "warning": "ai_verified",
                    "fail": "flagged",
                    "pending": "pending",
                }.get(v_status, "pending")

                result = await db.execute(
                    update(MCQQuestion)
                    .where(MCQQuestion.id == q_obj.id)
                    .values(
                        verification_status=db_status,
                        verification_report=report if report else None,
                    )
                )
                if db_status != "pending":
                    verified += 1
                else:
                    failed += 1
            await db.commit()

        passes = sum(1 for r in reports if r.get("status") == "pass")
        warns  = sum(1 for r in reports if r.get("status") == "warning")
        flags  = sum(1 for r in reports if r.get("status") == "fail")
        print(f"pass={passes} warn={warns} flag={flags}")
        await asyncio.sleep(1)

    print(f"\n✓ Verification done — ai_verified: {verified} | still pending: {failed}")


def main() -> None:
    dry_run    = "--dry-run" in sys.argv
    run_verify = "--verify"  in sys.argv
    asyncio.run(run(dry_run=dry_run, run_verify=run_verify))


if __name__ == "__main__":
    main()
