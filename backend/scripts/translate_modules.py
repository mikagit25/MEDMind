#!/usr/bin/env python3
"""
Process pending ModuleTranslation and LessonTranslation records.

Runs after module generation and import to fill the translation queue.
Rate-limited by Claude/Ollama availability — designed to be run daily by cron.

Usage:
    python3 /opt/medmind/backend/scripts/translate_modules.py
    python3 /opt/medmind/backend/scripts/translate_modules.py --limit 50
    python3 /opt/medmind/backend/scripts/translate_modules.py --locale ru --limit 20
    python3 /opt/medmind/backend/scripts/translate_modules.py --status
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models.models import ModuleTranslation, LessonTranslation, SUPPORTED_LOCALES

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def show_status() -> None:
    async with AsyncSessionLocal() as db:
        # Module translations
        for status in ("pending", "translating", "done", "failed"):
            r = await db.execute(
                select(func.count()).where(ModuleTranslation.status == status)
            )
            print(f"  ModuleTranslation [{status:12s}]: {r.scalar()}")

        print()
        for status in ("pending", "translating", "done", "failed"):
            r = await db.execute(
                select(func.count()).where(LessonTranslation.status == status)
            )
            print(f"  LessonTranslation [{status:12s}]: {r.scalar()}")


async def process_module_translations(locale_filter: str | None, limit: int) -> int:
    from app.services.translation_service import _translate_module_one

    async with AsyncSessionLocal() as db:
        stmt = (
            select(ModuleTranslation)
            .where(ModuleTranslation.status == "pending")
            .order_by(ModuleTranslation.locale)
            .limit(limit)
        )
        if locale_filter:
            stmt = stmt.where(ModuleTranslation.locale == locale_filter)
        result = await db.execute(stmt)
        pending = result.scalars().all()

    processed = 0
    for mt in pending:
        async with AsyncSessionLocal() as db:
            from app.models.models import Module
            module = await db.get(Module, mt.module_id)
            if not module:
                continue
            logger.info(f"  Translating module {module.code} → {mt.locale}")
            await _translate_module_one(module, mt.locale, db)
            processed += 1

    return processed


async def process_lesson_translations(locale_filter: str | None, limit: int) -> int:
    from app.services.translation_service import _translate_lesson_one

    async with AsyncSessionLocal() as db:
        stmt = (
            select(LessonTranslation)
            .where(LessonTranslation.status == "pending")
            .order_by(LessonTranslation.locale)
            .limit(limit)
        )
        if locale_filter:
            stmt = stmt.where(LessonTranslation.locale == locale_filter)
        result = await db.execute(stmt)
        pending = result.scalars().all()

    processed = 0
    for lt in pending:
        async with AsyncSessionLocal() as db:
            from app.models.models import Lesson
            lesson = await db.get(Lesson, lt.lesson_id)
            if not lesson:
                continue
            logger.info(f"  Translating lesson {lesson.lesson_code or lesson.id} → {lt.locale}")
            await _translate_lesson_one(lesson, lt.locale, db)
            processed += 1

    return processed


async def main() -> None:
    parser = argparse.ArgumentParser(description="Process pending module/lesson translations")
    parser.add_argument("--status", action="store_true", help="Show translation queue status and exit")
    parser.add_argument("--locale", default=None, help="Only process this locale, e.g. 'ru'")
    parser.add_argument("--limit", type=int, default=100, help="Max records to process per run (default: 100)")
    parser.add_argument("--modules-only", action="store_true", help="Skip lesson translations")
    parser.add_argument("--lessons-only", action="store_true", help="Skip module translations")
    args = parser.parse_args()

    if args.status:
        print("\n=== Translation Queue Status ===")
        await show_status()
        print()
        return

    logger.info("=== Starting translation processing ===")
    logger.info(f"Locale filter: {args.locale or 'all'} | Limit: {args.limit}")

    total = 0

    if not args.lessons_only:
        n = await process_module_translations(args.locale, args.limit)
        logger.info(f"Module translations processed: {n}")
        total += n

    if not args.modules_only:
        n = await process_lesson_translations(args.locale, args.limit)
        logger.info(f"Lesson translations processed: {n}")
        total += n

    logger.info(f"=== Done. Total processed: {total} ===")


if __name__ == "__main__":
    asyncio.run(main())
