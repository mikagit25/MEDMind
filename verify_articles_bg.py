#!/usr/bin/env python3
"""Background PubMed article verifier.

Verifies all published articles against PubMed indexed literature.
Sets verification_status = 'ai_verified' if ≥2 relevant papers found.

Runs inside backend container:
  docker cp verify_articles_bg.py medmind_backend:/app/
  docker exec -d medmind_backend python3 /app/verify_articles_bg.py
  docker exec medmind_backend tail -f /tmp/verify_articles.log
"""
import asyncio
import logging
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/tmp/verify_articles.log", mode="a"),
    ],
)
logger = logging.getLogger("verify_bg")


async def main():
    sys.path.insert(0, "/app")
    from app.core.database import AsyncSessionLocal
    from app.models.models import Article
    from app.services.pubmed_service import verify_article
    from sqlalchemy import select
    from datetime import datetime

    logger.info("=== PubMed Article Verifier Started ===")

    async with AsyncSessionLocal() as db:
        rows = (await db.execute(
            select(Article)
            .where(Article.is_published == True, Article.review_status == "published")
            .order_by(Article.published_at.desc())
        )).scalars().all()

    logger.info("Found %d published articles to verify", len(rows))

    verified = unverified = already = failed = 0

    for i, art in enumerate(rows, 1):
        # Skip expert-verified (manual, don't overwrite)
        if getattr(art, "verification_status", "unverified") == "expert_verified":
            already += 1
            continue
        # Skip if already ai_verified AND has sources AND verified recently
        if (
            getattr(art, "verification_status", "unverified") == "ai_verified"
            and getattr(art, "verified_sources", None)
            and getattr(art, "last_verified_at", None)
        ):
            already += 1
            continue

        logger.info("[%d/%d] Verifying: %s", i, len(rows), art.title[:60])

        existing_pmids = []
        if art.sources:
            for src in art.sources:
                if not isinstance(src, dict):
                    continue
                pmid = src.get("pmid")
                if pmid and str(pmid).strip().isdigit():
                    existing_pmids.append(str(pmid).strip())

        try:
            result = await verify_article(
                title=art.title,
                keywords=art.keywords or [],
                category=art.category,
                existing_pmids=existing_pmids,
            )

            # Open fresh session for each article to avoid stale state
            async with AsyncSessionLocal() as db:
                a = await db.get(Article, art.id)
                if a:
                    a.verification_status = result["status"]
                    a.verified_sources = result["verified_sources"] or []
                    a.last_verified_at = datetime.utcnow()
                    await db.commit()

            status = result["status"]
            count = result["pubmed_count"]
            if status == "ai_verified":
                verified += 1
                logger.info("  ✅ ai_verified — %d PubMed sources", count)
            else:
                unverified += 1
                logger.info("  ⚠️  unverified — %d sources found", count)

        except Exception as exc:
            failed += 1
            logger.error("  ❌ FAILED: %s: %s", type(exc).__name__, exc)

        # Rate limiting: NCBI allows 3 req/sec without key, 10/sec with key
        # Each verify_article makes ~2 API calls
        await asyncio.sleep(1.0)

    logger.info("=== DONE ===")
    logger.info("ai_verified: %d | unverified: %d | already_done: %d | failed: %d",
                verified, unverified, already, failed)
    logger.info("Total processed: %d/%d", verified + unverified + failed, len(rows))


if __name__ == "__main__":
    asyncio.run(main())
