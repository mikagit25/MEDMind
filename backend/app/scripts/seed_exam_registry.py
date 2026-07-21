"""Seed ExamDefinition records from exam_registry.py into the database.

Idempotent — skips entries that already exist, updates if data changed.

Run:
    docker exec medmind_backend python3 -m app.scripts.seed_exam_registry
"""
import asyncio
import logging
from datetime import datetime

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.data.exam_registry import ALL_EXAMS
from app.models.models import ExamDefinition

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


async def run() -> None:
    async with AsyncSessionLocal() as db:
        created = updated = skipped = 0
        for data in ALL_EXAMS:
            existing = await db.get(ExamDefinition, data["slug"])
            if existing is None:
                exam = ExamDefinition(
                    slug=data["slug"],
                    name=data["name"],
                    country=data["country"],
                    regulatory_body=data["regulatory_body"],
                    question_count=data["question_count"],
                    duration_min=data["duration_min"],
                    pass_threshold=data["pass_threshold"],
                    passing_score_label=data.get("passing_score_label", f"{data['pass_threshold']}%"),
                    blueprint_source=data["blueprint_source"],
                    blueprint_verified_at=data.get("blueprint_verified_at"),
                    status=data.get("status", "draft"),
                    locale=data.get("locale", "en"),
                    family=data.get("family", "gulf"),
                    options_per_question=data.get("options_per_question", 4),
                    categories=data.get("categories"),
                    exam_date_fixed=data.get("exam_date_fixed"),
                    disclaimer=data.get("disclaimer"),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(exam)
                created += 1
                log.info("  + created: %s", data["slug"])
            else:
                # Update mutable fields (not slug)
                changed = False
                for field in ("name", "country", "regulatory_body", "question_count",
                              "duration_min", "pass_threshold", "passing_score_label",
                              "blueprint_source", "blueprint_verified_at", "status",
                              "categories", "disclaimer"):
                    new_val = data.get(field)
                    if getattr(existing, field) != new_val:
                        setattr(existing, field, new_val)
                        changed = True
                if changed:
                    existing.updated_at = datetime.utcnow()
                    updated += 1
                    log.info("  ~ updated: %s", data["slug"])
                else:
                    skipped += 1

        await db.commit()
        log.info("\nDone — created: %d | updated: %d | skipped: %d", created, updated, skipped)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
