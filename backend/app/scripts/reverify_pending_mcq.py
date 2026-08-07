"""Re-verify MCQQuestion rows stuck in 'pending' verification_status.

Uses the same verify_batch() pipeline as the generation script.
Safe to run multiple times (idempotent — skips already-verified questions).

Usage:
    python -m app.scripts.reverify_pending_mcq            # all pending
    python -m app.scripts.reverify_pending_mcq --max 50   # limit per run
"""
from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.models import MCQQuestion
from app.scripts._mcq_db_writer import verify_batch


async def run(max_questions: int | None = None) -> None:
    async with AsyncSessionLocal() as db:
        q = select(MCQQuestion).where(
            MCQQuestion.verification_status == "pending",
            MCQQuestion.status == "active",
        )
        if max_questions:
            q = q.limit(max_questions)
        result = await db.execute(q)
        questions = result.scalars().all()

    if not questions:
        print("No pending questions found.")
        return

    print(f"Found {len(questions)} pending questions — running verification...")

    BATCH = 10
    total_verified = 0
    total_flagged = 0

    for i in range(0, len(questions), BATCH):
        batch = questions[i : i + BATCH]
        q_dicts = [
            {
                "idx": j,
                "question": q.question or "",
                "correct": q.correct,
                "explanation": q.explanation or "",
                "nclex_client_needs": q.nclex_client_needs or "",
            }
            for j, q in enumerate(batch)
        ]

        print(f"  Batch {i // BATCH + 1}: verifying {len(batch)} questions...")
        reports = await verify_batch(q_dicts)
        report_by_idx = {r.get("idx", -1): r for r in reports}

        async with AsyncSessionLocal() as db:
            for j, mcq in enumerate(batch):
                report = report_by_idx.get(j, {})
                v = report.get("status", "pending")
                new_status = {
                    "pass": "ai_verified",
                    "warning": "ai_verified",
                    "fail": "flagged",
                    "pending": "pending",
                }.get(v, "pending")

                # Fetch fresh instance in this session
                result = await db.execute(
                    select(MCQQuestion).where(MCQQuestion.id == mcq.id)
                )
                fresh = result.scalar_one_or_none()
                if fresh:
                    fresh.verification_status = new_status
                    fresh.verification_report = report if report else None
                    if new_status == "ai_verified":
                        total_verified += 1
                    elif new_status == "flagged":
                        total_flagged += 1

            await db.commit()

        print(
            f"    ✓ batch done — verified so far: {total_verified} | flagged: {total_flagged}"
        )
        await asyncio.sleep(3)

    print(
        f"\nDone — ai_verified: {total_verified} | flagged: {total_flagged} "
        f"| still pending: {len(questions) - total_verified - total_flagged}"
    )


def main() -> None:
    max_q = None
    if "--max" in sys.argv:
        idx = sys.argv.index("--max")
        if idx + 1 < len(sys.argv):
            max_q = int(sys.argv[idx + 1])
    asyncio.run(run(max_questions=max_q))


if __name__ == "__main__":
    main()
