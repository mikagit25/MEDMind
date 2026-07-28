"""Retroactively enrich articles without PubMed sources.

Searches PubMed by article title/keywords, saves top 2-3 real citations
to article.sources and sets verification_status = 'pending' so the
verification cron can pick them up.

Usage:
    python -m app.scripts.enrich_article_sources           # all without sources
    python -m app.scripts.enrich_article_sources --max 100 # limit per run
    python -m app.scripts.enrich_article_sources --dry-run # preview only

Rate limits:
  PubMed without API key: 3 req/sec → sleep 0.4s between articles
  Set PUBMED_API_KEY in .env for 10 req/sec.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from typing import Any

import httpx
from sqlalchemy import select

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from app.core.database import AsyncSessionLocal
from app.models.models import Article

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

PUBMED_API_KEY = os.getenv("PUBMED_API_KEY", "")
ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
_DELAY = 0.12 if PUBMED_API_KEY else 0.40


async def _pubmed_search(query: str, max_results: int = 3) -> list[dict[str, Any]]:
    """Search PubMed and return list of {pmid, title, url}."""
    clean = query.replace("[", "").replace("]", "")[:120]
    params: dict[str, Any] = {
        "db": "pubmed", "term": clean,
        "retmax": max_results, "retmode": "json", "sort": "relevance",
    }
    if PUBMED_API_KEY:
        params["api_key"] = PUBMED_API_KEY

    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r1 = await c.get(ESEARCH, params=params)
            r1.raise_for_status()
            ids = r1.json().get("esearchresult", {}).get("idlist", [])
            if not ids:
                return []

            time.sleep(_DELAY)
            sum_params: dict[str, Any] = {"db": "pubmed", "id": ",".join(ids), "retmode": "json"}
            if PUBMED_API_KEY:
                sum_params["api_key"] = PUBMED_API_KEY
            r2 = await c.get(ESUMMARY, params=sum_params)
            r2.raise_for_status()
            uids = r2.json().get("result", {}).get("uids", [])
            result_data = r2.json().get("result", {})

            sources = []
            for uid in uids:
                item = result_data.get(uid, {})
                title = item.get("title", "")
                if not title:
                    continue
                sources.append({
                    "pmid": uid,
                    "title": title,
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{uid}/",
                    "authors": ", ".join(
                        a.get("name", "") for a in item.get("authors", [])[:3]
                    ),
                    "year": item.get("pubdate", "")[:4],
                    "journal": item.get("source", ""),
                })
            return sources
    except Exception as exc:
        log.warning("PubMed search failed for '%s': %s", query[:50], exc)
        return []


def _build_query(article: Article) -> str:
    """Build PubMed search query from article title + keywords."""
    title_words = (article.title or "")[:80]
    kw = " ".join((article.keywords or [])[:3])
    return f"{title_words} {kw}".strip()


async def run(max_articles: int = 30, dry_run: bool = False) -> int:
    """Main enrichment loop. Returns number of articles enriched."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Article)
            .where(
                Article.is_published == True,
                Article.sources.is_(None)
                | (Article.sources == "[]")
                | (Article.sources.cast(str) == "null"),
            )
            .order_by(Article.created_at.asc())
            .limit(max_articles)
        )
        articles = result.scalars().all()

    if not articles:
        log.info("No articles without sources — nothing to do")
        return 0

    log.info("Found %d articles to enrich", len(articles))
    enriched = 0

    for article in articles:
        query = _build_query(article)
        sources = await _pubmed_search(query)

        if not sources:
            log.debug("No PubMed results for: %s", article.title[:60])
            time.sleep(_DELAY)
            continue

        if dry_run:
            log.info("[DRY] %s → %d sources", article.slug[:50], len(sources))
            continue

        async with AsyncSessionLocal() as db:
            a = await db.get(Article, article.id)
            if not a:
                continue
            a.sources = sources
            # Mark pending so verification cron picks it up
            if a.verification_status in ("passed", "unverified"):
                a.verification_status = "pending"
            await db.commit()

        log.info("Enriched: %s → %d sources", article.slug[:60], len(sources))
        enriched += 1
        time.sleep(_DELAY)

    log.info("Done: enriched %d/%d articles", enriched, len(articles))
    return enriched


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(max_articles=args.max, dry_run=args.dry_run))
