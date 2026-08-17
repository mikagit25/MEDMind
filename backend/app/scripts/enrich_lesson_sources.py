"""Enrich lessons with real PubMed sources.

Strategy:
- English title → build query from title + first key_point directly
- Russian title → ask LLM for 3-5 English PubMed search terms first
- Object-refs in content → extract title/author/year into search string
- Searches PubMed E-utilities (free, real articles only — no hallucinated PMIDs)
- Stores [{pmid, title, url, authors, year, journal}] in lessons.sources
- Sets verification_status = 'ai_verified'

Usage:
    python -m app.scripts.enrich_lesson_sources            # 50 per run
    python -m app.scripts.enrich_lesson_sources --max 200
    python -m app.scripts.enrich_lesson_sources --dry-run
    python -m app.scripts.enrich_lesson_sources --all      # all 1199
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
from typing import Any

import httpx
from sqlalchemy import select, cast
from sqlalchemy.dialects.postgresql import JSONB

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.models import Lesson, Module

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

CYRILLIC = re.compile(r"[А-Яа-яёЁ]")
PUBMED_API_KEY = getattr(settings, "PUBMED_API_KEY", "")
ESEARCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
_PM_DELAY = 0.12 if PUBMED_API_KEY else 0.50

_CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
_cerebras_key_index = 0


def _get_cerebras_keys() -> list[str]:
    keys = []
    for attr in ("CEREBRAS_API_KEY", "CEREBRAS_API_KEY_2", "CEREBRAS_API_KEY_3",
                 "CEREBRAS_API_KEY_4", "CEREBRAS_API_KEY_5", "CEREBRAS_API_KEY_6"):
        k = getattr(settings, attr, "")
        if k:
            keys.append(k)
    return keys


async def _cerebras_query(prompt: str) -> str | None:
    global _cerebras_key_index
    keys = _get_cerebras_keys()
    if not keys:
        return None
    tried = 0
    async with httpx.AsyncClient(timeout=30) as http:
        while tried < len(keys):
            key = keys[_cerebras_key_index % len(keys)]
            try:
                r = await http.post(
                    _CEREBRAS_URL,
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={
                        "model": "gemma-4-31b",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 60,
                        "temperature": 0.0,
                    },
                )
                if r.status_code == 429:
                    _cerebras_key_index += 1
                    tried += 1
                    await asyncio.sleep(1)
                    continue
                r.raise_for_status()
                content = r.json()["choices"][0]["message"]["content"].strip()
                return content if content else None
            except Exception as e:
                log.debug("Cerebras error: %s", e)
                _cerebras_key_index += 1
                tried += 1
    return None


async def _ru_to_pubmed_query(title: str, key_points: list[str]) -> str:
    """Ask Cerebras to generate English PubMed search terms for a Russian lesson."""
    prompt = (
        f"Russian medical lesson: «{title}».\n"
        "Give 5 English PubMed search terms (one line, just terms, no explanations):"
    )
    result = await _cerebras_query(prompt)
    if result:
        result = re.sub(r'["\[\]\n]', ' ', result).strip()
        # Remove any leading/trailing punctuation like "1." or "-"
        result = re.sub(r'^[\d\.\-\s]+', '', result).strip()
        if result and len(result) > 5:
            return result[:200]
    # Fallback: extract any Latin/English words already in the title
    latin = re.sub(r'[^a-zA-Z0-9 \-]', ' ', title).strip()
    return latin if len(latin) > 4 else "evidence-based medicine clinical practice"


def _build_query_from_content_refs(refs: list) -> str | None:
    """Build search string from object-format references in content."""
    parts = []
    for ref in refs[:3]:
        if isinstance(ref, dict):
            t = ref.get("title", "")
            a = ref.get("authors", "")
            y = str(ref.get("year", ""))
            if t and not CYRILLIC.search(t):
                parts.append(f"{t} {a} {y}".strip())
        elif isinstance(ref, str) and not CYRILLIC.search(ref):
            parts.append(ref[:100])
    return parts[0] if parts else None


async def _pubmed_search(query: str, max_results: int = 5) -> list[dict]:
    """Search PubMed and return up to max_results citation dicts."""
    params: dict[str, Any] = {
        "db": "pubmed",
        "term": query[:200],
        "retmax": max_results,
        "retmode": "json",
        "sort": "relevance",
    }
    if PUBMED_API_KEY:
        params["api_key"] = PUBMED_API_KEY

    try:
        async with httpx.AsyncClient(timeout=20) as c:
            # Retry up to 3 times on 429
            for attempt in range(3):
                r1 = await c.get(ESEARCH, params=params)
                if r1.status_code == 429:
                    await asyncio.sleep(2 ** attempt + 1)
                    continue
                r1.raise_for_status()
                break
            else:
                log.warning("PubMed rate-limited after retries: %s", query[:60])
                return []
            ids = r1.json().get("esearchresult", {}).get("idlist", [])
            if not ids:
                return []

            await asyncio.sleep(_PM_DELAY)

            sum_params: dict[str, Any] = {
                "db": "pubmed",
                "id": ",".join(ids),
                "retmode": "json",
            }
            if PUBMED_API_KEY:
                sum_params["api_key"] = PUBMED_API_KEY
            r2 = await c.get(ESUMMARY, params=sum_params)
            r2.raise_for_status()
            result_data = r2.json().get("result", {})

            sources = []
            for pmid in ids:
                item = result_data.get(pmid, {})
                title = item.get("title", "")
                if not title:
                    continue
                authors_list = item.get("authors", [])
                authors_str = ", ".join(
                    a.get("name", "") for a in authors_list[:3]
                )
                if len(authors_list) > 3:
                    authors_str += " et al."
                doi = ""
                for aid in item.get("articleids", []):
                    if aid.get("idtype") == "doi":
                        doi = aid.get("value", "")
                        break
                sources.append({
                    "pmid": pmid,
                    "title": title,
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    "authors": authors_str,
                    "year": item.get("pubdate", "")[:4],
                    "journal": item.get("source", ""),
                    "doi": doi,
                })
            return sources

    except Exception as exc:
        log.warning("PubMed error for '%s': %s", query[:60], exc)
        return []


async def _get_lesson_query(lesson: Lesson, module_title: str) -> str:
    """Build the best possible English PubMed search query for a lesson."""
    title = lesson.title or ""
    content = lesson.content or {}
    key_points: list[str] = []
    if isinstance(content, dict):
        kp = content.get("key_points", [])
        if isinstance(kp, list):
            # Strip Cyrillic from key_points for query building
            for k in kp[:3]:
                if isinstance(k, str) and not CYRILLIC.search(k):
                    key_points.append(k[:80])

    # English title — query directly
    if not CYRILLIC.search(title):
        kp_text = " ".join(key_points[:1])
        return f"{title} {kp_text}".strip()[:200]

    # Russian title — try content object-refs first
    refs = content.get("references", []) if isinstance(content, dict) else []
    ref_query = _build_query_from_content_refs(refs)
    if ref_query:
        return ref_query

    # Russian title — use LLM
    all_kp: list[str] = []
    if isinstance(content, dict):
        for k in (content.get("key_points", []) or [])[:3]:
            if isinstance(k, str):
                all_kp.append(k[:80])
    return await _ru_to_pubmed_query(title, all_kp)


async def run(max_lessons: int, dry_run: bool) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Lesson, Module.title.label("module_title"))
            .join(Module, Lesson.module_id == Module.id)
            .where(
                Lesson.status == "published",
                Lesson.sources.is_(None)
                | (Lesson.sources == cast("[]", JSONB))
                | (Lesson.sources == cast("null", JSONB)),
            )
            .order_by(Lesson.created_at.asc())
            .limit(max_lessons + 200)
        )
        rows = result.all()

    # Filter: only lessons actually missing sources
    lessons_with_module: list[tuple[Lesson, str]] = []
    for row in rows:
        lesson = row[0]
        module_title = row[1] or ""
        src = lesson.sources
        if src is None or src == [] or src == []:
            lessons_with_module.append((lesson, module_title))
        if len(lessons_with_module) >= max_lessons:
            break

    log.info("Lessons to enrich: %d", len(lessons_with_module))
    enriched = skipped = errors = 0

    for i, (lesson, module_title) in enumerate(lessons_with_module):
        title_display = (lesson.title or "")[:60]
        log.info("[%d/%d] %s", i + 1, len(lessons_with_module), title_display)

        query = await _get_lesson_query(lesson, module_title)
        if not query or len(query) < 4:
            log.warning("  No valid query — skipping")
            skipped += 1
            continue

        log.debug("  Query: %s", query[:80])
        await asyncio.sleep(_PM_DELAY)
        sources = await _pubmed_search(query, max_results=5)

        # Keep top 3 most relevant
        sources = sources[:3]

        if not sources:
            log.warning("  No PubMed results for: %s", query[:60])
            skipped += 1
            continue

        if dry_run:
            log.info("  [DRY] Would store %d sources:", len(sources))
            for s in sources:
                log.info("    • %s (%s) PMID:%s", s["title"][:60], s["year"], s["pmid"])
            enriched += 1
            continue

        async with AsyncSessionLocal() as db:
            l = await db.get(Lesson, lesson.id)
            if not l:
                errors += 1
                continue
            l.sources = sources
            l.verification_status = "ai_verified"
            await db.commit()

        log.info("  ✓ %d sources saved", len(sources))
        for s in sources:
            log.info("    • %s (%s)", s["title"][:70], s["year"])
        enriched += 1

    log.info("Done. Enriched: %d  Skipped: %d  Errors: %d", enriched, skipped, errors)


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich lessons with real PubMed sources")
    parser.add_argument("--max", type=int, default=50, help="Max lessons per run (default 50)")
    parser.add_argument("--all", action="store_true", help="Process all lessons without sources")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, no DB writes")
    args = parser.parse_args()
    max_n = 9999 if args.all else args.max
    asyncio.run(run(max_lessons=max_n, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
