"""PubMed search integration with Redis caching."""
import hashlib
import json
import logging
from typing import List, Optional

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
