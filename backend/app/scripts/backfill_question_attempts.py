"""V7: Backfill question_attempts from historical exam_sessions.per_question.

For each completed ExamSession, reads per_question JSONB and inserts
QuestionAttempt rows. Marks is_first_attempt correctly based on
which attempt came first chronologically.

Usage:
    docker exec medmind_backend python -m app.scripts.backfill_question_attempts
    docker exec medmind_backend python -m app.scripts.backfill_question_attempts --dry-run
    docker exec medmind_backend python -m app.scripts.backfill_question_attempts --since 2026-01-01
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import uuid
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


async def run(dry_run: bool, since: str | None):
    import os
    db_url = os.environ.get("DATABASE_URL", "postgresql+asyncpg://medmind:medmind_secret@localhost:5432/medmind")
    engine = create_async_engine(db_url, echo=False)
    factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    from app.models.models import ExamSession, QuestionAttempt

    async with factory() as db:
        q = select(ExamSession).where(
            ExamSession.status == "completed",
            ExamSession.per_question.isnot(None),
        )
        if since:
            q = q.where(ExamSession.created_at >= datetime.fromisoformat(since))
        q = q.order_by(ExamSession.created_at.asc())

        sessions = (await db.execute(q)).scalars().all()
        log.info("Found %d completed sessions to backfill", len(sessions))

        # Track first-attempt per (user_id, question_id) across sessions (chronological order)
        seen: set[tuple] = set()
        inserted = 0
        skipped = 0

        for sess in sessions:
            pq_list = sess.per_question or []
            q_ids = sess.question_ids or []
            mode_id = sess.mode_id or ""
            session_type = "mock" if "mock" in mode_id else ("exam" if sess.cat_enabled else "practice")

            for pq in pq_list:
                idx = pq.get("index", 0)
                is_correct = pq.get("correct")
                if is_correct is None:
                    continue  # skipped question

                # Get question_id from per_question (V7 added this) or from question_ids list
                qid = pq.get("question_id")
                if not qid and idx < len(q_ids):
                    qid = q_ids[idx]
                if not qid:
                    continue

                key = (str(sess.user_id), str(qid))
                is_first = key not in seen
                seen.add(key)

                if dry_run:
                    inserted += 1
                    continue

                # Check if already exists in DB (idempotent)
                existing = (await db.execute(
                    select(QuestionAttempt.id).where(
                        QuestionAttempt.question_id == uuid.UUID(qid),
                        QuestionAttempt.session_id == sess.id,
                    ).limit(1)
                )).scalar_one_or_none()
                if existing:
                    skipped += 1
                    continue

                db.add(QuestionAttempt(
                    question_id=uuid.UUID(qid),
                    user_id=sess.user_id,
                    exam_slug=None,
                    selected=pq.get("selected"),
                    is_correct=bool(is_correct),
                    time_seconds=pq.get("time_seconds"),
                    session_id=sess.id,
                    session_type=session_type,
                    is_first_attempt=is_first,
                    created_at=sess.ends_at or sess.created_at,
                ))
                inserted += 1

        if not dry_run:
            await db.commit()

        log.info("Backfill done: inserted=%d skipped=%d (dry_run=%s)", inserted, skipped, dry_run)

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--since", help="ISO date filter e.g. 2026-01-01")
    args = parser.parse_args()
    asyncio.run(run(args.dry_run, args.since))
