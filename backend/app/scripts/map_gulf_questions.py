"""G1.2 — Tag existing MCQQuestions with Gulf exam slugs.

Maps NCLEX-tagged questions to Gulf exams based on category overlap.
All Gulf Prometric exams share the same blueprint categories, so any
NCLEX question whose nclex_client_needs maps to a Gulf category gets
tagged with ALL 7 Gulf exam slugs.

Run:
    docker exec medmind_backend python3 -m app.scripts.map_gulf_questions
"""
import asyncio
import logging

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.data.exam_registry import GULF_EXAMS, NCLEX_TO_GULF_CATEGORY_MAP
from app.models.models import MCQQuestion

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

GULF_SLUGS = [e["slug"] for e in GULF_EXAMS]


async def run() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(MCQQuestion).where(MCQQuestion.nclex_client_needs.isnot(None))
        )
        questions = result.scalars().all()
        log.info("Found %d NCLEX-tagged questions to process", len(questions))

        tagged = 0
        already = 0
        for q in questions:
            # Check if category maps to Gulf blueprint
            cat = (q.nclex_client_needs or "").lower().strip()
            if cat not in NCLEX_TO_GULF_CATEGORY_MAP:
                continue

            existing = set(q.exam_slugs or [])
            new_slugs = existing | set(GULF_SLUGS)
            if new_slugs == existing:
                already += 1
                continue

            q.exam_slugs = sorted(new_slugs)
            tagged += 1

        await db.commit()
        log.info("Done — tagged: %d new | %d already tagged | %d skipped (no NCLEX cat)",
                 tagged, already, len(questions) - tagged - already)
        log.info("Gulf slugs applied: %s", GULF_SLUGS)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
