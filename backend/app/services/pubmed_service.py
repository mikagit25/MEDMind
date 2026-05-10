"""PubMed search integration with Redis caching + article verification."""
import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.core.redis_client import get_redis

logger = logging.getLogger(__name__)

PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"


def _cache_key(query: str) -> str:
    return "pubmed:" + hashlib.sha256(query.lower().encode()).hexdigest()


async def search_pubmed(query: str, max_results: int = 5) -> List[dict]:
    """Search PubMed and return article list. Results are cached 7 days."""
    redis = await get_redis()
    cache_key = _cache_key(query)

    cached = await redis.get(cache_key)
    if cached:
        return json.loads(cached)

    # Build search term (sanitize)
    search_term = query.replace("[", "").replace("]", "")[:120]
    params = {
        "db": "pubmed",
        "term": search_term,
        "retmax": max_results,
        "retmode": "json",
        "sort": "relevance",
    }
    if settings.PUBMED_API_KEY:
        params["api_key"] = settings.PUBMED_API_KEY

    articles = []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Step 1: get PMIDs
            r1 = await client.get(PUBMED_BASE + "esearch.fcgi", params=params)
            r1.raise_for_status()
            d1 = r1.json()
            ids = d1.get("esearchresult", {}).get("idlist", [])

            if not ids:
                return []

            # Step 2: get article summaries
            sum_params = {
                "db": "pubmed",
                "id": ",".join(ids),
                "retmode": "json",
            }
            if settings.PUBMED_API_KEY:
                sum_params["api_key"] = settings.PUBMED_API_KEY

            r2 = await client.get(PUBMED_BASE + "esummary.fcgi", params=sum_params)
            r2.raise_for_status()
            d2 = r2.json()

            for pmid in ids:
                art = d2.get("result", {}).get(pmid)
                if art and isinstance(art, dict):
                    authors = art.get("authors", [])
                    author_str = (
                        ", ".join(a["name"] for a in authors[:2])
                        + (" et al." if len(authors) > 2 else "")
                        if authors else "Unknown"
                    )
                    articles.append({
                        "pmid": pmid,
                        "title": art.get("title", "No title"),
                        "authors": author_str,
                        "journal": art.get("source", ""),
                        "year": (art.get("pubdate", "") or "")[:4],
                        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    })

        # Cache results
        await redis.setex(cache_key, settings.PUBMED_CACHE_TTL, json.dumps(articles))

    except Exception as e:
        logger.warning(f"PubMed search failed for '{query}': {e}")

    return articles


def build_pubmed_context(articles: List[dict]) -> str:
    """Format articles as context string for AI prompt."""
    if not articles:
        return ""
    lines = []
    for i, a in enumerate(articles, 1):
        lines.append(f'{i}. "{a["title"]}" — {a["authors"]} ({a["year"]})')
    return "\n".join(lines)


# ── Article verification ───────────────────────────────────────────────────────

_MIN_PAPERS_FOR_VERIFIED = 2


async def verify_article(
    title: str,
    keywords: Optional[List[str]] = None,
    category: Optional[str] = None,
    existing_pmids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Cross-reference article topic with PubMed.

    Returns dict with:
      status: 'ai_verified' | 'unverified'
      verified_sources: [{pmid, title, authors, journal, year, url}]
      pubmed_count: int
    """
    # Build query from title + top keywords
    query_parts = [title[:80]]
    if keywords:
        query_parts.extend(kw for kw in keywords[:2] if kw.lower() not in title.lower())

    query = " ".join(query_parts)
    pubmed_results = await search_pubmed(query, max_results=5)

    # Also validate existing LLM-cited PMIDs
    existing_found: List[dict] = []
    if existing_pmids:
        valid_ids = [str(p).strip() for p in existing_pmids if str(p).strip().isdigit()]
        if valid_ids:
            # Cross-check via esummary directly
            try:
                params: Dict[str, Any] = {
                    "db": "pubmed", "id": ",".join(valid_ids[:3]), "retmode": "json",
                }
                if settings.PUBMED_API_KEY:
                    params["api_key"] = settings.PUBMED_API_KEY
                async with httpx.AsyncClient(timeout=10.0) as client:
                    r = await client.get(PUBMED_BASE + "esummary.fcgi", params=params)
                    r.raise_for_status()
                    d = r.json()
                    for pid in valid_ids[:3]:
                        doc = d.get("result", {}).get(pid, {})
                        if doc and not doc.get("error"):
                            authors_list = doc.get("authors", [])
                            author_str = (
                                ", ".join(a["name"] for a in authors_list[:2])
                                + (" et al." if len(authors_list) > 2 else "")
                                if authors_list else "Unknown"
                            )
                            existing_found.append({
                                "pmid": pid,
                                "title": doc.get("title", "").rstrip("."),
                                "authors": author_str,
                                "journal": doc.get("source", ""),
                                "year": (doc.get("pubdate", "") or "")[:4],
                                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pid}/",
                            })
            except Exception as exc:
                logger.warning("PMID validation failed: %s", exc)

    # Merge: validated LLM PMIDs first, then PubMed search results (deduplicated)
    seen: set[str] = set()
    merged: List[dict] = []
    for src in existing_found + pubmed_results:
        pmid = src.get("pmid", "")
        if pmid and pmid not in seen:
            seen.add(pmid)
            merged.append(src)
        if len(merged) >= 5:
            break

    status = "ai_verified" if len(merged) >= _MIN_PAPERS_FOR_VERIFIED else "unverified"

    return {
        "status": status,
        "verified_sources": merged,
        "pubmed_count": len(merged),
    }


async def verify_article_orm(article_id, db) -> str:
    """Verify article against PubMed and persist result. Returns new status."""
    from app.models.models import Article
    from sqlalchemy import select

    art = (await db.execute(select(Article).where(Article.id == article_id))).scalar_one_or_none()
    if not art:
        return "not_found"

    existing_pmids = []
    if art.sources:
        for src in art.sources:
            pmid = src.get("pmid")
            if pmid and str(pmid).strip().isdigit():
                existing_pmids.append(str(pmid).strip())

    result = await verify_article(
        title=art.title,
        keywords=art.keywords or [],
        category=art.category,
        existing_pmids=existing_pmids,
    )

    art.verification_status = result["status"]
    art.verified_sources = result["verified_sources"] or []
    art.last_verified_at = datetime.utcnow()
    await db.commit()

    logger.info(
        "Verified %s [%.40s]: %d PubMed sources → %s",
        art.slug, art.title, result["pubmed_count"], result["status"],
    )
    return result["status"]
