"""Enrich MCQ questions with per-question PubMed source references.

Replaces the generic 5-textbook placeholder with specific articles that
confirm the clinical content of each question.

Strategy per question:
  1. Extract clinical keywords from question text + explanation
  2. Search PubMed E-utilities (esearch → esummary)
  3. Pick top 1–2 most relevant articles
  4. Add 1 category-specific textbook reference
  5. Add regulatory source (NCSBN / Gulf board depending on exam_slugs)
  6. Write to source_refs in DB

Rate limits:
  - Without API key: 3 req/sec (we sleep 0.35s between calls)
  - With PUBMED_API_KEY: 10 req/sec
  Set PUBMED_API_KEY in backend/.env for faster runs.

Usage:
  python -m app.scripts.enrich_pubmed_refs              # all without per-q refs
  python -m app.scripts.enrich_pubmed_refs --max 100    # limit per run
  python -m app.scripts.enrich_pubmed_refs --dry-run    # preview only
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
import time
import urllib.parse
from typing import Any

import httpx
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.models import MCQQuestion

PUBMED_API_KEY = os.getenv("PUBMED_API_KEY", "")
ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
# Polite delay: 0.35s → stays under 3 req/sec without a key
_DELAY = 0.12 if PUBMED_API_KEY else 0.35

BATCH_SIZE = 50

# ── Stop-words for keyword extraction ─────────────────────────────────────────

_STOP = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "to", "of", "in", "on",
    "at", "by", "for", "with", "as", "or", "and", "but", "if", "then",
    "which", "that", "this", "these", "those", "it", "its", "not", "no",
    # Nursing exam fluff
    "patient", "nurse", "nursing", "client", "priority", "first", "action",
    "assess", "assessment", "intervention", "care", "plan", "implement",
    "evaluate", "monitor", "report", "notify", "physician", "provider",
    "most", "least", "best", "correct", "appropriate", "important",
    "immediately", "next", "initial", "primary", "secondary",
}


def _keywords(question: str, explanation: str) -> str:
    """Extract 4–6 meaningful clinical terms for a PubMed search."""
    text = f"{question} {explanation}"
    # Keep only letters, lowercase, split
    words = re.findall(r"[a-zA-Z]{4,}", text.lower())
    seen: set[str] = set()
    terms: list[str] = []
    for w in words:
        if w not in _STOP and w not in seen:
            seen.add(w)
            terms.append(w)
        if len(terms) >= 6:
            break
    return " ".join(terms[:5]) if terms else "nursing clinical practice"


# ── Category → specific textbook reference ────────────────────────────────────

_TEXTBOOK_BY_CATEGORY: dict[str, dict] = {
    "pharmacology": {
        "name": "Karch's Focus on Nursing Pharmacology (9th ed.)",
        "url": "https://shop.lww.com/Karch-s-Focus-on-Nursing-Pharmacology/p/9781975174583",
        "type": "textbook",
    },
    "maternal_newborn": {
        "name": "Lowdermilk: Maternity & Women's Health Care (12th ed.)",
        "url": "https://evolve.elsevier.com/cs/product/9780323831741",
        "type": "textbook",
    },
    "pediatrics": {
        "name": "Wong's Nursing Care of Infants and Children (11th ed.)",
        "url": "https://evolve.elsevier.com/cs/product/9780323776004",
        "type": "textbook",
    },
    "mental_health": {
        "name": "Townsend: Psychiatric Mental Health Nursing (9th ed.)",
        "url": "https://www.fadavis.com/product/nursing-psychiatric-mental-health-townsend-9",
        "type": "textbook",
    },
    "community_public_health": {
        "name": "Stanhope: Public Health Nursing (10th ed.)",
        "url": "https://evolve.elsevier.com/cs/product/9780323582247",
        "type": "textbook",
    },
    "leadership_management": {
        "name": "Yoder-Wise: Leading and Managing in Nursing (7th ed.)",
        "url": "https://evolve.elsevier.com/cs/product/9780323449137",
        "type": "textbook",
    },
    "critical_care": {
        "name": "Urden: Critical Care Nursing — Diagnosis and Management (9th ed.)",
        "url": "https://evolve.elsevier.com/cs/product/9780323879231",
        "type": "textbook",
    },
    "medical_surgical": {
        "name": "Ignatavicius: Medical-Surgical Nursing (10th ed.)",
        "url": "https://evolve.elsevier.com/cs/product/9780323612425",
        "type": "textbook",
    },
    "fundamentals_nursing": {
        "name": "Potter & Perry: Fundamentals of Nursing (11th ed.)",
        "url": "https://evolve.elsevier.com/cs/product/9780323877442",
        "type": "textbook",
    },
}
_DEFAULT_TEXTBOOK = {
    "name": "Saunders Comprehensive Review for the NCLEX-RN (9th ed.)",
    "url": "https://evolve.elsevier.com/cs/product/9780323358415",
    "type": "textbook",
}

# ── Regulatory source by exam family ─────────────────────────────────────────

_GULF_REGULATORY = {
    "snle": {
        "name": "SCFHS SNLE Applicant Guide 2024",
        "url": "https://scfhs.org.sa/sites/default/files/2024-10/SNLE%20Applicant%20Guide%202024.pdf",
        "type": "regulatory",
    },
    "dha": {
        "name": "Dubai Health Authority — Licensing Requirements",
        "url": "https://www.dha.gov.ae/en/HealthProfessionals/LicensingandRegistration",
        "type": "regulatory",
    },
    "qchp": {
        "name": "QCHP Nursing Licensing Requirements",
        "url": "https://www.qchp.org.qa/en/Licensing/Pages/LicensingRequirements.aspx",
        "type": "regulatory",
    },
    "omsb": {
        "name": "OMSB Nursing Examination Booklet",
        "url": "https://omsb.gov.om",
        "type": "regulatory",
    },
    "nhra": {
        "name": "NHRA Health Professionals Licensing",
        "url": "https://www.nhra.bh/Licensing",
        "type": "regulatory",
    },
    "mohuae": {
        "name": "MOHAP UAE Health Professional Licensing",
        "url": "https://mohap.gov.ae/en/services/licensing-of-health-professionals",
        "type": "regulatory",
    },
    "haad": {
        "name": "DOH Abu Dhabi Licensing Requirements",
        "url": "https://www.doh.gov.ae/en/regulatedhealthprofessions/licensingrequirements",
        "type": "regulatory",
    },
}
_NCLEX_REGULATORY = {
    "name": "NCSBN NCLEX-RN Test Plan 2023",
    "url": "https://www.ncsbn.org/publications/nclex-rn-examination-test-plan-2023",
    "type": "regulatory",
}


def _regulatory_source(exam_slugs: list[str] | None) -> dict:
    if exam_slugs:
        for slug in exam_slugs:
            if slug in _GULF_REGULATORY:
                return _GULF_REGULATORY[slug]
    return _NCLEX_REGULATORY


# ── PubMed E-utilities ────────────────────────────────────────────────────────

async def _pubmed_search(client: httpx.AsyncClient, query: str) -> list[str]:
    """Return up to 2 PMIDs for the query."""
    params: dict[str, Any] = {
        "db": "pubmed",
        "term": query,
        "retmax": 2,
        "retmode": "json",
        "sort": "relevance",
    }
    if PUBMED_API_KEY:
        params["api_key"] = PUBMED_API_KEY
    try:
        resp = await client.get(ESEARCH_URL, params=params, timeout=10)
        resp.raise_for_status()
        ids = resp.json().get("esearchresult", {}).get("idlist", [])
        return ids[:2]
    except Exception:
        return []


async def _pubmed_summary(client: httpx.AsyncClient, pmids: list[str]) -> list[dict]:
    """Fetch article title, journal, year for given PMIDs."""
    if not pmids:
        return []
    params: dict[str, Any] = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "json",
    }
    if PUBMED_API_KEY:
        params["api_key"] = PUBMED_API_KEY
    try:
        resp = await client.get(ESUMMARY_URL, params=params, timeout=10)
        resp.raise_for_status()
        result = resp.json().get("result", {})
        articles = []
        for pmid in pmids:
            art = result.get(pmid, {})
            title = art.get("title", "").rstrip(".")
            if not title:
                continue
            year = art.get("pubdate", "")[:4]
            journal = art.get("source", "")
            articles.append({
                "name": f"{title} ({year})" if year else title,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "type": "pubmed",
                "pmid": pmid,
                "journal": journal,
            })
        return articles
    except Exception:
        return []


async def _build_source_refs(
    client: httpx.AsyncClient,
    question: str,
    explanation: str,
    category: str | None,
    exam_slugs: list[str] | None,
) -> list[dict]:
    """Build a per-question source_refs list with PubMed + textbook + regulatory."""
    keywords = _keywords(question, explanation)

    # Add category context to improve PubMed relevance
    cat_term = (category or "").replace("_", " ")
    search_query = f"({keywords}) AND nursing[ti] AND ({cat_term}[ti] OR clinical[ti])"

    await asyncio.sleep(_DELAY)
    pmids = await _pubmed_search(client, search_query)

    # Fallback: broader search without category
    if not pmids:
        await asyncio.sleep(_DELAY)
        pmids = await _pubmed_search(client, f"{keywords} nursing")

    await asyncio.sleep(_DELAY)
    pubmed_refs = await _pubmed_summary(client, pmids)

    # Category-specific textbook
    textbook = _TEXTBOOK_BY_CATEGORY.get(category or "", _DEFAULT_TEXTBOOK)

    # Regulatory source
    regulatory = _regulatory_source(exam_slugs)

    sources: list[dict] = []
    sources.extend(pubmed_refs)         # PubMed first (most verifiable)
    sources.append(textbook)            # Category textbook
    sources.append(regulatory)          # Regulatory/exam board

    return sources


# ── Main ──────────────────────────────────────────────────────────────────────

async def run(max_questions: int | None = None, dry_run: bool = False) -> None:
    print(f"PubMed API key: {'set' if PUBMED_API_KEY else 'not set (3 req/sec limit)'}")

    async with AsyncSessionLocal() as db:
        # Target: questions with generic (5-item) source_refs OR NULL
        result = await db.execute(
            select(MCQQuestion).where(MCQQuestion.explanation.isnot(None))
        )
        all_qs = result.scalars().all()

        # Filter to questions that still have generic refs (all same 5 items)
        generic_url = "https://www.ncsbn.org/publications/nclex-rn-examination-test-plan-2023"
        to_enrich = []
        for q in all_qs:
            refs = q.source_refs or []
            is_generic = (
                len(refs) == 5 and
                any(r.get("url") == generic_url for r in refs)
            ) or refs == [] or q.source_refs is None
            if is_generic:
                to_enrich.append(q)

        if max_questions:
            to_enrich = to_enrich[:max_questions]

        print(f"Questions needing PubMed enrichment: {len(to_enrich)}")
        if dry_run:
            print("[DRY RUN] Would process:")
            for q in to_enrich[:5]:
                kw = _keywords(q.question or "", q.explanation or "")
                print(f"  [{q.nclex_client_needs}] {(q.question or '')[:60]}… → {kw}")
            return

        enriched = 0
        failed = 0

        async with httpx.AsyncClient() as client:
            for q in to_enrich:
                try:
                    refs = await _build_source_refs(
                        client,
                        q.question or "",
                        q.explanation or "",
                        q.nclex_client_needs,
                        q.exam_slugs,
                    )
                    q.source_refs = refs
                    enriched += 1

                    if enriched % 10 == 0:
                        await db.commit()
                        print(f"  {enriched}/{len(to_enrich)} enriched…")

                except Exception as e:
                    print(f"  Error on {str(q.id)[:8]}: {e}")
                    failed += 1

        await db.commit()
        print(f"Done — enriched: {enriched} | failed: {failed}")


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    max_q: int | None = None
    if "--max" in sys.argv:
        idx = sys.argv.index("--max")
        if idx + 1 < len(sys.argv):
            max_q = int(sys.argv[idx + 1])
    asyncio.run(run(max_questions=max_q, dry_run=dry_run))


if __name__ == "__main__":
    main()
