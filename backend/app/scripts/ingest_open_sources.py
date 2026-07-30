"""Bank-Scale B2 — Ingest open-license content into source_documents table.

Sources used (all verified in B1):
  - MedlinePlus Health Topics (public domain US gov) — via NLM WS API
  - CDC          (public domain US gov)              — via CDC Content Syndication API
  - StatPearls   (CC BY-NC-ND 4.0, facts only)      — via NCBI E-utilities

Rate limits respected:
  - NCBI E-utilities: 3 req/s without API key, 10/s with NCBI_API_KEY
  - CDC/MedlinePlus: polite 1 req/s

Usage:
  python -m app.scripts.ingest_open_sources                        # all categories
  python -m app.scripts.ingest_open_sources pharmacological        # single category
  python -m app.scripts.ingest_open_sources --dry-run              # print without saving
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

import httpx
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.models import ContentSource, SourceDocument

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

# ── Category → search terms mapping ───────────────────────────────────────────

CATEGORY_TOPICS: dict[str, list[str]] = {
    "pharmacological": [
        "medication safety nursing",
        "drug adverse effects nursing",
        "high alert medications",
        "pharmacokinetics nursing",
    ],
    "safe_effective_care": [
        "infection control nursing",
        "patient safety nursing",
        "hand hygiene healthcare",
        "surgical asepsis",
    ],
    "physiological_adaptation": [
        "heart failure nursing care",
        "acute respiratory failure nursing",
        "sepsis nursing",
        "diabetic ketoacidosis nursing",
    ],
    "reduction_risk": [
        "fall prevention hospital",
        "pressure injury prevention nursing",
        "laboratory values nurses",
        "deep vein thrombosis prevention",
    ],
    "health_promotion": [
        "health screening nursing",
        "immunization schedule adults",
        "prenatal care nursing",
        "health education patient",
    ],
    "psychosocial": [
        "therapeutic communication nursing",
        "mental health nursing",
        "anxiety disorder nursing care",
        "substance use disorder nursing",
    ],
    "basic_care": [
        "wound care nursing",
        "nutrition nursing care",
        "urinary catheter care",
        "mobility nursing rehabilitation",
    ],
}

# ── Helpers ────────────────────────────────────────────────────────────────────

_UA = "MedMindBot/2.0 (medmind.pro; content-ingestion; contact@medmind.pro)"
NCBI_API_KEY = os.getenv("NCBI_API_KEY", "")
NCBI_RATE = 10.0 if NCBI_API_KEY else 3.0   # req/s
_ncbi_last = 0.0


async def _ncbi_throttle() -> None:
    global _ncbi_last
    gap = 1.0 / NCBI_RATE
    wait = _ncbi_last + gap - time.monotonic()
    if wait > 0:
        await asyncio.sleep(wait)
    _ncbi_last = time.monotonic()


def _hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode()).hexdigest()


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&[a-z]+;", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _word_count(text: str) -> int:
    return len(text.split())


# ── MedlinePlus fetcher ────────────────────────────────────────────────────────

async def fetch_medlineplus(term: str, category: str, client: httpx.AsyncClient) -> list[dict]:
    """Fetch health topic summaries from MedlinePlus WS API.

    Public domain (US gov) — text_reuse_allowed=True.
    API docs: https://wsearch.nlm.nih.gov/ws/query
    """
    url = "https://wsearch.nlm.nih.gov/ws/query"
    params = {"db": "healthTopics", "term": term, "retmax": "4"}
    try:
        r = await client.get(url, params=params, timeout=20,
                             headers={"User-Agent": _UA})
        r.raise_for_status()
    except Exception as e:
        logger.warning("MedlinePlus fetch error for %r: %s", term, e)
        return []

    # Response is XML — parse with regex (no xml lib required)
    docs = []
    for doc_block in re.findall(r"<document[^>]*>(.*?)</document>", r.text, re.S):
        title_m = re.search(r'<content name="title"[^>]*>(.*?)</content>', doc_block, re.S)
        url_m = re.search(r'<content name="FullSummary"[^>]*>(.*?)</content>', doc_block, re.S)
        full_m = re.search(r'<content name="FullSummary"[^>]*>(.*?)</content>', doc_block, re.S)
        doc_url_m = re.search(r'url="([^"]+)"', doc_block)

        title = _strip_html(title_m.group(1)) if title_m else term
        full_text = _strip_html(full_m.group(1)) if full_m else ""
        if not full_text or len(full_text) < 100:
            continue

        docs.append({
            "source_slug": "medlineplus_topics",
            "nclex_category": category,
            "title": title[:490],
            "url": doc_url_m.group(1) if doc_url_m else "https://medlineplus.gov/",
            "section": term,
            "full_text": full_text,
        })
    await asyncio.sleep(1.0)   # polite 1 req/s
    return docs


# ── CDC Content Syndication fetcher ───────────────────────────────────────────

async def fetch_cdc(term: str, category: str, client: httpx.AsyncClient) -> list[dict]:
    """Fetch CDC content via Content Syndication API.

    Public domain (US gov) — text_reuse_allowed=True.
    API: https://tools.cdc.gov/api/v2/resources/media.json
    """
    url = "https://tools.cdc.gov/api/v2/resources/media.json"
    params = {"topic": term, "max": "3", "sort": "datePublished", "order": "desc"}
    try:
        r = await client.get(url, params=params, timeout=20,
                             headers={"User-Agent": _UA, "Accept": "application/json"})
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        logger.warning("CDC fetch error for %r: %s", term, e)
        return []

    docs = []
    for item in (data.get("results") or [])[:3]:
        title = item.get("name", term)[:490]
        description = item.get("description", "")
        content_url = item.get("sourceUrl", "https://www.cdc.gov/")
        if not description or len(description) < 80:
            continue
        docs.append({
            "source_slug": "cdc",
            "nclex_category": category,
            "title": title,
            "url": content_url,
            "section": term,
            "full_text": description,
        })
    await asyncio.sleep(1.0)
    return docs


# ── NCBI / StatPearls fetcher ─────────────────────────────────────────────────

async def fetch_statpearls(term: str, category: str, client: httpx.AsyncClient) -> list[dict]:
    """Fetch StatPearls abstracts from NCBI Bookshelf via E-utilities.

    CC BY-NC-ND 4.0 → text_reuse_allowed=False → facts-only, no text reproduction.
    Stored as factual context for the generator; generator prompt forbids text copying.
    """
    # Step 1: search
    await _ncbi_throttle()
    search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    search_params: dict[str, str] = {
        "db": "books", "term": f"StatPearls[book] AND {term}",
        "retmax": "3", "retmode": "json",
    }
    if NCBI_API_KEY:
        search_params["api_key"] = NCBI_API_KEY

    try:
        r = await client.get(search_url, params=search_params, timeout=20,
                             headers={"User-Agent": _UA})
        r.raise_for_status()
        ids = r.json().get("esearchresult", {}).get("idlist", [])
    except Exception as e:
        logger.warning("NCBI search error for %r: %s", term, e)
        return []

    docs = []
    for uid in ids[:3]:
        # Step 2: fetch abstract
        await _ncbi_throttle()
        fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        fetch_params: dict[str, str] = {
            "db": "books", "id": uid,
            "rettype": "abstract", "retmode": "text",
        }
        if NCBI_API_KEY:
            fetch_params["api_key"] = NCBI_API_KEY
        try:
            r2 = await client.get(fetch_url, params=fetch_params, timeout=20,
                                  headers={"User-Agent": _UA})
            r2.raise_for_status()
            text = r2.text.strip()
        except Exception as e:
            logger.warning("NCBI fetch error for uid %s: %s", uid, e)
            continue

        if not text or len(text) < 100:
            continue

        docs.append({
            "source_slug": "statpearls",
            "nclex_category": category,
            "title": f"StatPearls: {term} (NCBI UID {uid})"[:490],
            "url": f"https://www.ncbi.nlm.nih.gov/books/{uid}/",
            "section": term,
            "full_text": text[:8000],   # cap at 8k chars
        })

    return docs


# ── Save to DB ────────────────────────────────────────────────────────────────

async def save_documents(docs: list[dict], db=None) -> tuple[int, int]:
    """Save documents to source_documents, skip duplicates by hash.

    Accepts an optional db session (for tests). Creates its own session if not provided.
    Returns (inserted, skipped).
    """
    async def _run(session) -> tuple[int, int]:
        inserted = skipped = 0
        for doc in docs:
            text = doc["full_text"]
            h = _hash(text)
            existing = await session.execute(
                select(SourceDocument).where(SourceDocument.text_hash == h)
            )
            if existing.scalar_one_or_none():
                skipped += 1
                continue
            session.add(SourceDocument(
                source_slug=doc["source_slug"],
                nclex_category=doc.get("nclex_category"),
                title=doc["title"],
                url=doc.get("url"),
                section=doc.get("section"),
                full_text=text,
                text_hash=h,
                word_count=_word_count(text),
                doc_metadata=doc.get("doc_metadata"),
                downloaded_at=datetime.utcnow(),
            ))
            inserted += 1
        await session.commit()
        return inserted, skipped

    if db is not None:
        return await _run(db)
    async with AsyncSessionLocal() as session:
        return await _run(session)


# ── Main ──────────────────────────────────────────────────────────────────────

async def run(categories: list[str] | None = None, dry_run: bool = False) -> dict:
    """Run ingestion for given categories (all if None). Returns report dict."""
    target_cats = categories or list(CATEGORY_TOPICS.keys())
    report: dict[str, dict] = {}

    async with AsyncSessionLocal() as db:
        async with httpx.AsyncClient() as client:
            for cat in target_cats:
                terms = CATEGORY_TOPICS.get(cat, [])
                cat_docs: list[dict] = []

                for term in terms:
                    logger.info("[%s] fetching MedlinePlus: %r", cat, term)
                    cat_docs += await fetch_medlineplus(term, cat, client)

                    logger.info("[%s] fetching CDC: %r", cat, term)
                    cat_docs += await fetch_cdc(term, cat, client)

                    logger.info("[%s] fetching StatPearls: %r", cat, term)
                    cat_docs += await fetch_statpearls(term, cat, client)

                logger.info("[%s] fetched %d candidate docs", cat, len(cat_docs))

                if dry_run:
                    report[cat] = {"fetched": len(cat_docs), "inserted": 0, "skipped": 0, "dry_run": True}
                    continue

                inserted, skipped = await save_documents(cat_docs, db)
                report[cat] = {"fetched": len(cat_docs), "inserted": inserted, "skipped": skipped}
                logger.info("[%s] saved %d new docs, skipped %d duplicates", cat, inserted, skipped)

    return report


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry_run = "--dry-run" in sys.argv
    cats = args if args else None
    result = asyncio.run(run(cats, dry_run=dry_run))
    print("\n=== Ingest Report ===")
    total_ins = total_skip = 0
    for cat, stats in result.items():
        print(f"  {cat:30} fetched={stats['fetched']:3}  inserted={stats['inserted']:3}  skipped={stats['skipped']:3}")
        total_ins += stats["inserted"]
        total_skip += stats["skipped"]
    print(f"\n  TOTAL  inserted={total_ins}  skipped={total_skip}")
