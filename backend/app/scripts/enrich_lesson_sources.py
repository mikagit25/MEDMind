"""Enrich published lessons with structured PubMed sources.

Each lesson's content JSONB contains a 'references' key — an array of plain-text
citation strings like:
  "NICE. Intravenous fluid therapy in adults in hospital (CG174). NICE, 2013"
  "Adrogue HJ & Madias NE. Hyponatraemia. NEJM 2000;342:1581-1589"

This script:
  1. Fetches lessons that have text references but no structured sources yet.
  2. For each text reference, searches PubMed and saves the best matching result.
  3. Populates lesson.sources with [{pmid, title, url, authors, year, journal}].
  4. Sets verification_status = 'pending' so the verify cron picks it up.

Usage:
    python -m app.scripts.enrich_lesson_sources           # default 20 per run
    python -m app.scripts.enrich_lesson_sources --max 50
    python -m app.scripts.enrich_lesson_sources --dry-run
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from typing import Any

import httpx
from sqlalchemy import select, cast

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
from app.core.database import AsyncSessionLocal
from app.models.models import Lesson

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

PUBMED_API_KEY = os.getenv("PUBMED_API_KEY", "")
ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
_DELAY = 0.12 if PUBMED_API_KEY else 0.40


async def _pubmed_search(query: str) -> dict[str, Any] | None:
    """Search PubMed for a single reference string. Returns first match or None."""
    clean = query.replace("[", "").replace("]", "")[:120]
    params: dict[str, Any] = {
        "db": "pubmed", "term": clean,
        "retmax": 1, "retmode": "json", "sort": "relevance",
    }
    if PUBMED_API_KEY:
        params["api_key"] = PUBMED_API_KEY

    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r1 = await c.get(ESEARCH, params=params)
            r1.raise_for_status()
            ids = r1.json().get("esearchresult", {}).get("idlist", [])
            if not ids:
                return None

            await asyncio.sleep(_DELAY)
            sum_params: dict[str, Any] = {"db": "pubmed", "id": ids[0], "retmode": "json"}
            if PUBMED_API_KEY:
                sum_params["api_key"] = PUBMED_API_KEY
            r2 = await c.get(ESUMMARY, params=sum_params)
            r2.raise_for_status()
            result_data = r2.json().get("result", {})
            item = result_data.get(ids[0], {})
            title = item.get("title", "")
            if not title:
                return None
            return {
                "pmid": ids[0],
                "title": title,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{ids[0]}/",
                "authors": ", ".join(
                    a.get("name", "") for a in item.get("authors", [])[:3]
                ),
                "year": item.get("pubdate", "")[:4],
                "journal": item.get("source", ""),
            }
    except Exception as exc:
        log.warning("PubMed search failed for '%s': %s", query[:60], exc)
        return None


def _lesson_text_references(lesson: Lesson) -> list[str]:
    """Extract plain-text reference strings from lesson.content['references']."""
    content = lesson.content
    if not isinstance(content, dict):
        return []
    refs = content.get("references", [])
    if not isinstance(refs, list):
        return []
    return [r for r in refs if isinstance(r, str) and r.strip()]


async def run(max_lessons: int = 20, dry_run: bool = False) -> int:
    """Main enrichment loop. Returns number of lessons enriched."""
    from sqlalchemy.dialects.postgresql import JSONB as _JSONB

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Lesson)
            .where(
                Lesson.status == "published",
                # No structured sources yet (over-fetch, filter for refs in Python)
                Lesson.sources.is_(None)
                | (Lesson.sources == cast("[]", _JSONB))
                | (Lesson.sources == cast("null", _JSONB)),
            )
            .order_by(Lesson.created_at.asc())
            .limit(500)
        )
        all_without_sources = result.scalars().all()

    # Only lessons that actually have non-empty text references
    lessons = [l for l in all_without_sources if _lesson_text_references(l)][:max_lessons]

    if not lessons:
        log.info("No lessons without sources — nothing to do")
        return 0

    log.info("Found %d lessons to enrich", len(lessons))
    enriched = 0

    for lesson in lessons:
        text_refs = _lesson_text_references(lesson)
        sources: list[dict] = []

        for ref_text in text_refs[:5]:  # cap at 5 refs per lesson to limit API calls
            result = await _pubmed_search(ref_text)
            await asyncio.sleep(_DELAY)
            if result:
                sources.append(result)

        if not sources:
            log.debug("No PubMed matches for lesson: %s", (lesson.title or "")[:60])
            continue

        if dry_run:
            log.info("[DRY] %s → %d sources", (lesson.title or "")[:60], len(sources))
            continue

        async with AsyncSessionLocal() as db:
            l = await db.get(Lesson, lesson.id)
            if not l:
                continue
            l.sources = sources
            if l.verification_status in ("passed", "unverified"):
                l.verification_status = "pending"
            await db.commit()

        log.info("Enriched: %s → %d sources", (lesson.title or "")[:60], len(sources))
        enriched += 1

    log.info("Done: enriched %d/%d lessons", enriched, len(lessons))
    return enriched


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(max_lessons=args.max, dry_run=args.dry_run))
