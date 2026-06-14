"""Backfill translations for news articles that are missing them.

Usage:
    python -m app.scripts.translate_missing_news          # all missing
    python -m app.scripts.translate_missing_news --locale ru   # only one locale
    python -m app.scripts.translate_missing_news --limit 50    # cap count
"""
import asyncio
import argparse
import logging

from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified

from app.core.database import AsyncSessionLocal
from app.models.models import NewsArticle
from app.services.news_pipeline import _translate_news, LOCALES

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def backfill(only_locale: str | None = None, limit: int = 500) -> None:
    target_locales = [only_locale] if only_locale else LOCALES

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(NewsArticle)
            .where(NewsArticle.is_published == True)
            .order_by(NewsArticle.fetched_at.desc())
            .limit(limit * 4)  # fetch extra, filter below
        )
        articles = result.scalars().all()

        # Filter to those missing at least one target locale
        to_process = [
            a for a in articles
            if any(loc not in (a.translations or {}) for loc in target_locales)
        ][:limit]

        logger.info("Found %d articles needing translations", len(to_process))

        updated = 0
        for i, article in enumerate(to_process):
            translations = dict(article.translations or {})
            missing = [loc for loc in target_locales if loc not in translations]
            if not missing:
                continue

            logger.info("[%d/%d] %s — translating %s", i + 1, len(to_process),
                        article.title[:60], missing)

            changed = False
            for locale in missing:
                t = await _translate_news(article.title, article.summary, locale)
                if t.get("title") and t.get("summary"):
                    translations[locale] = t
                    changed = True
                    logger.info("  ✓ %s", locale)
                else:
                    logger.warning("  ✗ %s failed", locale)
                await asyncio.sleep(2.0)  # respect Groq rate limits

            if changed:
                article.translations = translations
                flag_modified(article, "translations")
                updated += 1

            # Commit in batches of 10
            if updated > 0 and updated % 10 == 0:
                await db.commit()
                logger.info("Committed batch (%d updated so far)", updated)

        await db.commit()
        logger.info("Done — %d articles updated", updated)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--locale", default=None, help="Only backfill this locale")
    parser.add_argument("--limit", type=int, default=200, help="Max articles to process")
    args = parser.parse_args()
    asyncio.run(backfill(args.locale, args.limit))


if __name__ == "__main__":
    main()
