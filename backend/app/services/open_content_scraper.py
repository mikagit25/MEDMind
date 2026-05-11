"""
Open content scraper — fetches research context from legal open-access sources.

Sources:
  - PubMed Central (PMC) Open Access via NCBI E-utilities (proper API, no scraping)
  - Wikipedia Medical (CC BY-SA) via Wikipedia REST API
  - MedlinePlus (US National Library of Medicine, public domain) via REST API
  - WHO (CC BY-NC-SA) via public topic pages

This module does NOT copy content — it fetches summaries/abstracts to use
as research context when generating original articles via Claude.
"""
import asyncio
import logging
from typing import Optional

import httpx

log = logging.getLogger(__name__)

NCBI_BASE  = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
WIKI_BASE  = "https://en.wikipedia.org/api/rest_v1/page"
MPLUS_BASE = "https://connect.medlineplus.gov/application"

HEADERS = {"User-Agent": "MedMind-AI/1.0 (educational; contact@medmind.pro)"}


# ── PubMed Central (NCBI E-utilities) ─────────────────────────────────────────

async def fetch_pubmed_abstracts(topic: str, max_results: int = 5) -> list[dict]:
    """
    Search PMC Open Access and return abstracts.
    These are licensed CC BY — safe to use as research context.
    """
    async with httpx.AsyncClient(headers=HEADERS, timeout=20) as client:
        # Step 1: search for PMC IDs
        search = await client.get(
            f"{NCBI_BASE}/esearch.fcgi",
            params={
                "db": "pmc",
                "term": f"{topic}[Title/Abstract] AND open+access[Filter]",
                "retmax": max_results,
                "retmode": "json",
                "sort": "relevance",
            },
        )
        if search.status_code != 200:
            return []
        ids = search.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []

        # Step 2: fetch abstracts for found IDs
        fetch = await client.get(
            f"{NCBI_BASE}/efetch.fcgi",
            params={
                "db": "pmc",
                "id": ",".join(ids),
                "rettype": "abstract",
                "retmode": "text",
            },
        )
        if fetch.status_code != 200:
            return []

        raw = fetch.text.strip()
        # Split into individual abstracts
        chunks = [c.strip() for c in raw.split("\n\n\n") if len(c.strip()) > 100]
        return [{"source": "PMC Open Access", "pmcid": pmcid, "text": chunk}
                for pmcid, chunk in zip(ids, chunks[:max_results])]


# ── Wikipedia Medical (CC BY-SA) ───────────────────────────────────────────────

async def fetch_wikipedia_summary(topic: str) -> Optional[dict]:
    """
    Fetch Wikipedia article summary via REST API.
    Wikipedia content is CC BY-SA — safe to use as research context with attribution.
    """
    # Try exact title first, then search
    search_term = topic.replace(" ", "_").title()
    async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
        # Try direct lookup
        r = await client.get(f"{WIKI_BASE}/summary/{search_term}")
        if r.status_code == 200:
            data = r.json()
            return {
                "source": "Wikipedia (CC BY-SA)",
                "title": data.get("title", ""),
                "extract": data.get("extract", ""),
                "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
            }

        # Fallback: Wikipedia search API
        r2 = await client.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": topic + " medical",
                "srlimit": 3,
                "format": "json",
            },
        )
        if r2.status_code == 200:
            results = r2.json().get("query", {}).get("search", [])
            for result in results:
                title = result["title"].replace(" ", "_")
                r3 = await client.get(f"{WIKI_BASE}/summary/{title}")
                if r3.status_code == 200:
                    data = r3.json()
                    extract = data.get("extract", "")
                    if len(extract) > 200:
                        return {
                            "source": "Wikipedia (CC BY-SA)",
                            "title": data.get("title", ""),
                            "extract": extract,
                            "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                        }
    return None


# ── MedlinePlus (US National Library of Medicine — Public Domain) ──────────────

async def fetch_medlineplus(topic: str) -> Optional[dict]:
    """
    Fetch MedlinePlus health topic summary. Public domain (US government content).
    """
    async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
        r = await client.get(
            f"{MPLUS_BASE}",
            params={
                "mainSearchCriteria.v.cs": "2.16.840.1.113883.6.177",
                "mainSearchCriteria.v.dn": topic,
                "informationRecipient": "PROV",
                "knowledgeResponseType": "application/json",
            },
        )
        if r.status_code == 200:
            data = r.json()
            entries = data.get("feed", {}).get("entry", [])
            if entries:
                entry = entries[0]
                summary = entry.get("summary", {}).get("_value", "") if isinstance(entry.get("summary"), dict) else ""
                return {
                    "source": "MedlinePlus (Public Domain)",
                    "title": entry.get("title", {}).get("_value", topic) if isinstance(entry.get("title"), dict) else topic,
                    "summary": summary[:2000] if summary else "",
                }
    return None


# ── Aggregate research context ─────────────────────────────────────────────────

async def gather_research_context(topic: str, max_pubmed: int = 3) -> str:
    """
    Gather research context from multiple open sources concurrently.
    Returns a structured text block for use as Claude's research input.
    """
    results = await asyncio.gather(
        fetch_pubmed_abstracts(topic, max_results=max_pubmed),
        fetch_wikipedia_summary(topic),
        fetch_medlineplus(topic),
        return_exceptions=True,
    )

    pubmed_abstracts, wiki_summary, mplus = results
    sections: list[str] = [f"## Research context for: {topic}\n"]

    # Wikipedia summary
    if isinstance(wiki_summary, dict) and wiki_summary.get("extract"):
        sections.append(
            f"### Wikipedia ({wiki_summary['source']})\n"
            f"**{wiki_summary['title']}**\n{wiki_summary['extract'][:1500]}\n"
            f"Source: {wiki_summary.get('url', '')}\n"
        )

    # MedlinePlus
    if isinstance(mplus, dict) and mplus.get("summary"):
        sections.append(
            f"### MedlinePlus ({mplus['source']})\n{mplus['summary']}\n"
        )

    # PubMed abstracts
    if isinstance(pubmed_abstracts, list):
        for i, ab in enumerate(pubmed_abstracts[:max_pubmed], 1):
            sections.append(
                f"### PubMed Abstract {i} (PMC {ab.get('pmcid', '')}, {ab['source']})\n"
                f"{ab['text'][:800]}\n"
            )

    if len(sections) == 1:
        return ""  # No data found

    return "\n".join(sections)
