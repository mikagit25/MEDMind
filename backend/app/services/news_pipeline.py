"""Medical news pipeline.

Sources:
  1. PubMed — recent high-impact publications (NCBI API, free, no key required)
  2. WHO News RSS — official press releases
  3. medRxiv — preprints (clinical medicine)

Pipeline per article:
  fetch → deduplicate → AI summarise (Groq) → translate ×6 (Groq) → save

Translation target locales: ru, ar, es, de, fr, tr
"""
import hashlib
import json
import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.models import NewsArticle

logger = logging.getLogger(__name__)

LOCALES = ["ru", "ar", "es", "de", "fr", "tr"]
LOCALE_NAMES = {"ru": "Russian", "ar": "Arabic", "es": "Spanish",
                "de": "German", "fr": "French", "tr": "Turkish"}

# ── PubMed config ─────────────────────────────────────────────────────────────
# Top-tier journals with broad clinical relevance
PUBMED_JOURNALS = [
    "N Engl J Med", "Lancet", "JAMA", "BMJ", "Ann Intern Med",
    "Nat Med", "Circulation", "Eur Heart J", "JAMA Intern Med",
    "JAMA Cardiol", "Lancet Oncol", "J Clin Oncol",
]
PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

# PubMed MeSH→category mapping
MESH_CATEGORY: list[tuple[str, str]] = [
    ("cardiovascular", "cardiology"), ("heart", "cardiology"), ("cardiac", "cardiology"),
    ("oncology", "oncology"), ("cancer", "oncology"), ("tumor", "oncology"), ("tumour", "oncology"),
    ("neurol", "neurology"), ("stroke", "neurology"), ("brain", "neurology"),
    ("infectious", "infectious-disease"), ("virus", "infectious-disease"), ("bacteria", "infectious-disease"),
    ("COVID", "infectious-disease"), ("SARS", "infectious-disease"),
    ("diabet", "endocrinology"), ("metabol", "endocrinology"), ("thyroid", "endocrinology"),
    ("respirat", "pulmonology"), ("pulmonary", "pulmonology"), ("lung", "pulmonology"),
    ("renal", "nephrology"), ("kidney", "nephrology"),
    ("gastro", "gastroenterology"), ("liver", "gastroenterology"), ("hepat", "gastroenterology"),
    ("psychiatr", "psychiatry"), ("mental", "psychiatry"), ("depression", "psychiatry"),
    ("pediatr", "pediatrics"), ("children", "pediatrics"), ("neonatal", "pediatrics"),
    ("surgery", "surgery"), ("surgical", "surgery"),
    ("obstet", "obstetrics"), ("pregnan", "obstetrics"),
    ("vaccine", "public-health"), ("epidemiol", "public-health"),
]

WHO_RSS = "https://www.who.int/rss-feeds/news-english.xml"
MEDRXIV_API = "https://api.biorxiv.org/details/medrxiv"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _source_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()


def _slugify(text: str, suffix: str = "") -> str:
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_]+", "-", text.strip())[:60]
    if suffix:
        text = f"{text}-{suffix}"
    return text


def _infer_category(text: str) -> str:
    low = text.lower()
    for keyword, cat in MESH_CATEGORY:
        if keyword.lower() in low:
            return cat
    return "general-medicine"


def _parse_rss_date(date_str: str) -> Optional[datetime]:
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S GMT"):
        try:
            return datetime.strptime(date_str.strip(), fmt).replace(tzinfo=None)
        except ValueError:
            continue
    return None


# ── AI caller with key rotation + provider fallback ───────────────────────────

def _groq_keys() -> list[str]:
    """KEY_5 is dedicated to news pipeline. KEY_1/2 reserved for user AI tutor."""
    keys = []
    for attr in ("GROQ_API_KEY_5",):
        k = getattr(settings, attr, "")
        if k:
            keys.append(k)
    return keys

def _cerebras_keys() -> list[str]:
    keys = []
    for attr in ("CEREBRAS_API_KEY", "CEREBRAS_API_KEY_2", "CEREBRAS_API_KEY_3",
                 "CEREBRAS_API_KEY_4", "CEREBRAS_API_KEY_5"):
        k = getattr(settings, attr, "")
        if k:
            keys.append(k)
    return keys


async def _call_openai_compat(base_url: str, api_key: str, model: str,
                               system: str, user: str, max_tokens: int) -> str:
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }
    async with httpx.AsyncClient(timeout=40) as http:
        resp = await http.post(
            base_url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()


async def _groq(system: str, user: str, max_tokens: int = 1200) -> str:
    """Try all Groq keys in rotation, then fall back to Cerebras."""
    last_err: Exception | None = None

    for key in _groq_keys():
        try:
            return await _call_openai_compat(
                "https://api.groq.com/openai/v1/chat/completions",
                key, settings.GROQ_MODEL, system, user, max_tokens,
            )
        except Exception as e:
            last_err = e
            logger.debug("Groq key failed (%s): %s", key[:12], e)

    # Fallback: Cerebras (900 tok/s, very fast)
    for key in _cerebras_keys():
        try:
            return await _call_openai_compat(
                "https://api.cerebras.ai/v1/chat/completions",
                key, "gpt-oss-120b", system, user, max_tokens,
            )
        except Exception as e:
            last_err = e
            logger.debug("Cerebras key failed (%s): %s", key[:12], e)

    raise RuntimeError(f"All AI providers exhausted: {last_err}")


# ── Summarisation ─────────────────────────────────────────────────────────────

SUMMARISE_SYSTEM = """\
You are a medical science journalist writing for healthcare professionals (doctors, residents, nurses).

Given a title and abstract/description of a medical publication or news item, write a comprehensive \
summary (500-700 words) in clear, engaging English prose.

Structure (no headers, flowing paragraphs):
1. Lead paragraph: key finding in plain language, why it matters (2-3 sentences)
2. Background & context: disease burden, previous knowledge gap, why this study was needed (2-3 sentences)
3. Study design: type of study, population, setting, methodology in sufficient detail (3-4 sentences)
4. Key results: specific numbers, effect sizes, p-values, confidence intervals where available (3-4 sentences)
5. Secondary findings or subgroup analyses if mentioned (1-2 sentences)
6. Clinical significance: what this changes in practice, guideline implications (2-3 sentences)
7. Limitations and caveats (1-2 sentences)

DO NOT: copy-paste from the source, add disclaimers, mention "this article", use bullet points or headers.
Return ONLY the summary text — no title, no JSON, no markdown."""


async def _summarise(title: str, abstract: str, category: str) -> str:
    user = f"Category: {category}\n\nTitle: {title}\n\nAbstract/Description:\n{abstract}"
    try:
        return await _groq(SUMMARISE_SYSTEM, user, max_tokens=1100)
    except Exception as e:
        logger.warning("Groq summarisation failed: %s", e)
        return abstract[:800]  # fallback to truncated abstract


# ── Translation ───────────────────────────────────────────────────────────────

TRANSLATE_SYSTEM = """\
Professional medical translator. Translate the JSON from English to {lang_name}.
Use standard medical terminology for {lang_name}.
Keep proper nouns, drug names, and acronyms (e.g. PCR, COVID-19, RNA) unchanged.
Return ONLY valid JSON with the same keys. Do not truncate — complete the full translation."""


def _clean_json(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1] if len(parts) > 1 else raw
        if raw.startswith("json"):
            raw = raw[4:]
    return raw.strip()


# Max characters for the summary in a translation payload to stay within token budget.
# 1800 chars ≈ 450 words ≈ 600 tokens → leaves plenty of room in a 2000-token budget.
_SUMMARY_CHAR_LIMIT = 1800


async def _translate_news(title: str, summary: str, locale: str) -> dict:
    lang_name = LOCALE_NAMES.get(locale, locale)
    # Truncate summary to avoid token overrun (keeps the most clinically relevant part)
    short_summary = summary[:_SUMMARY_CHAR_LIMIT]
    payload = json.dumps({"title": title, "summary": short_summary}, ensure_ascii=False)
    system = TRANSLATE_SYSTEM.format(lang_name=lang_name)
    try:
        raw = await _groq(system, payload, max_tokens=2000)
        cleaned = _clean_json(raw)
        obj = json.loads(cleaned)
        if obj.get("title") and obj.get("summary"):
            return obj
        return {}
    except Exception as e:
        logger.warning("Translation to %s failed: %s", locale, e)
        return {}


# ── Fetchers ──────────────────────────────────────────────────────────────────

async def _fetch_pubmed(days_back: int = 7) -> list[dict]:
    """Fetch recent papers from top-tier journals via NCBI Entrez."""
    journal_filter = "[ta] OR ".join(f'"{j}"' for j in PUBMED_JOURNALS) + "[ta]"
    date_end = datetime.utcnow().strftime("%Y/%m/%d")
    date_start = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y/%m/%d")
    query = f"({journal_filter}) AND {date_start}:{date_end}[dp] AND hasabstract"

    params = {"db": "pubmed", "term": query, "retmax": 30, "retmode": "json",
              "sort": "pub+date", "usehistory": "n"}
    if getattr(settings, "PUBMED_API_KEY", ""):
        params["api_key"] = settings.PUBMED_API_KEY

    results: list[dict] = []
    try:
        async with httpx.AsyncClient(timeout=20) as http:
            search_resp = await http.get(f"{PUBMED_BASE}esearch.fcgi", params=params)
            search_resp.raise_for_status()
            ids = search_resp.json().get("esearchresult", {}).get("idlist", [])

        if not ids:
            return []

        # Fetch summaries
        fetch_params = {"db": "pubmed", "id": ",".join(ids), "retmode": "json",
                        "rettype": "abstract"}
        if getattr(settings, "PUBMED_API_KEY", ""):
            fetch_params["api_key"] = settings.PUBMED_API_KEY

        async with httpx.AsyncClient(timeout=30) as http:
            detail_resp = await http.get(f"{PUBMED_BASE}esummary.fcgi", params=fetch_params)
            detail_resp.raise_for_status()
            summaries = detail_resp.json().get("result", {})

        # Also fetch abstracts
        efetch_params = {"db": "pubmed", "id": ",".join(ids), "retmode": "xml",
                         "rettype": "abstract"}
        async with httpx.AsyncClient(timeout=30) as http:
            abstract_resp = await http.get(f"{PUBMED_BASE}efetch.fcgi", params=efetch_params)
            abstract_resp.raise_for_status()

        # Parse abstracts from XML
        abstracts: dict[str, str] = {}
        try:
            root = ET.fromstring(abstract_resp.text)
            for article_elem in root.findall(".//PubmedArticle"):
                pmid_elem = article_elem.find(".//PMID")
                pmid = pmid_elem.text if pmid_elem is not None else None
                abstract_parts = article_elem.findall(".//AbstractText")
                if pmid and abstract_parts:
                    abstracts[pmid] = " ".join(
                        (p.text or "") for p in abstract_parts if p.text
                    )
        except ET.ParseError:
            pass

        for pmid in ids:
            s = summaries.get(pmid, {})
            if not s or s.get("error"):
                continue
            title = s.get("title", "").rstrip(".")
            if not title:
                continue
            authors = s.get("authors", [])
            first_author = authors[0].get("name", "") if authors else ""
            pub_date_str = s.get("pubdate", "")
            journal = s.get("fulljournalname", s.get("source", "PubMed"))
            doi = next((sid["value"] for sid in s.get("articleids", [])
                        if sid.get("idtype") == "doi"), None)
            source_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

            try:
                pub_date = datetime.strptime(pub_date_str[:10], "%Y %b %d") if " " in pub_date_str else None
            except ValueError:
                pub_date = None

            results.append({
                "title": title,
                "abstract": abstracts.get(pmid, s.get("source", "")),
                "source_name": journal,
                "source_url": source_url,
                "source_doi": doi,
                "published_at": pub_date,
                "extra_text": f"{first_author} et al. — {journal}",
            })

    except Exception as e:
        logger.error("PubMed fetch failed: %s", e)

    return results


async def _fetch_who_rss() -> list[dict]:
    """Fetch WHO news RSS feed."""
    results: list[dict] = []
    try:
        async with httpx.AsyncClient(timeout=15) as http:
            resp = await http.get(WHO_RSS, headers={"User-Agent": "MedMind/1.0"})
            resp.raise_for_status()

        root = ET.fromstring(resp.text)
        for item in root.findall(".//item")[:20]:
            title = (item.findtext("title") or "").strip()
            desc = (item.findtext("description") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub_date = _parse_rss_date(item.findtext("pubDate") or "")

            if not title or not link:
                continue

            results.append({
                "title": title,
                "abstract": re.sub(r"<[^>]+>", "", desc)[:1000],
                "source_name": "WHO",
                "source_url": link,
                "source_doi": None,
                "published_at": pub_date,
                "extra_text": "World Health Organization",
            })
    except Exception as e:
        logger.error("WHO RSS fetch failed: %s", e)

    return results


async def _fetch_medrxiv(days_back: int = 7) -> list[dict]:
    """Fetch recent medRxiv preprints via public API."""
    results: list[dict] = []
    try:
        date_start = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        date_end = datetime.utcnow().strftime("%Y-%m-%d")
        url = f"{MEDRXIV_API}/{date_start}/{date_end}/0/json"

        async with httpx.AsyncClient(timeout=20) as http:
            resp = await http.get(url)
            resp.raise_for_status()
            data = resp.json()

        for paper in data.get("collection", [])[:25]:
            title = paper.get("title", "").strip()
            abstract = paper.get("abstract", "").strip()
            doi = paper.get("doi", "")
            if not title or not abstract or not doi:
                continue

            pub_date_str = paper.get("date", "")
            try:
                pub_date = datetime.strptime(pub_date_str, "%Y-%m-%d")
            except ValueError:
                pub_date = None

            results.append({
                "title": title,
                "abstract": abstract[:1500],
                "source_name": "medRxiv",
                "source_url": f"https://doi.org/{doi}",
                "source_doi": doi,
                "published_at": pub_date,
                "extra_text": "medRxiv preprint (not peer-reviewed)",
            })
    except Exception as e:
        logger.error("medRxiv fetch failed: %s", e)

    return results


# ── Main pipeline ─────────────────────────────────────────────────────────────

async def run_news_pipeline(days_back: int = 7) -> int:
    """Fetch, summarise, translate, and save new medical news. Returns count of new articles saved."""
    logger.info("News pipeline started (days_back=%d)", days_back)

    # 1. Fetch from all sources
    raw_items = []
    pubmed_items = await _fetch_pubmed(days_back)
    who_items = await _fetch_who_rss()
    medrxiv_items = await _fetch_medrxiv(days_back)
    raw_items = pubmed_items + who_items + medrxiv_items
    logger.info("Fetched %d raw items (PubMed=%d, WHO=%d, medRxiv=%d)",
                len(raw_items), len(pubmed_items), len(who_items), len(medrxiv_items))

    saved = 0
    async with AsyncSessionLocal() as db:
        for item in raw_items:
            try:
                saved += await _process_item(item, db)
            except Exception as e:
                logger.error("Failed to process item '%s': %s", item.get("title", "?")[:60], e)

    logger.info("News pipeline done — %d new articles saved", saved)
    return saved


async def _process_item(item: dict, db: AsyncSession) -> int:
    url = item["source_url"]
    h = _source_hash(url)

    # 2. Deduplicate
    existing = await db.execute(
        select(NewsArticle.id).where(NewsArticle.source_hash == h)
    )
    if existing.scalar_one_or_none():
        return 0

    title = item["title"]
    abstract = item.get("abstract", "")
    if not abstract or len(abstract) < 30:
        return 0  # skip items without content

    # 3. Infer category
    combined_text = f"{title} {abstract}"
    category = _infer_category(combined_text)

    # 4. AI summarise (English)
    summary = await _summarise(title, abstract, category)
    if not summary or len(summary) < 50:
        return 0

    # 5. Translate to all target locales (with small delay to avoid rate limits)
    import asyncio as _asyncio
    translations: dict[str, dict] = {}
    for locale in LOCALES:
        t = await _translate_news(title, summary, locale)
        if t.get("title") and t.get("summary"):
            translations[locale] = t
        await _asyncio.sleep(0.3)  # avoid rate limit bursts

    # 6. Build slug (unique)
    date_part = (item["published_at"] or datetime.utcnow()).strftime("%Y%m%d")
    base_slug = _slugify(title, date_part)
    slug = base_slug

    # Ensure slug uniqueness
    counter = 1
    while True:
        check = await db.execute(select(NewsArticle.id).where(NewsArticle.slug == slug))
        if not check.scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    # 7. Save
    news = NewsArticle(
        slug=slug,
        source_name=item["source_name"],
        source_url=url,
        source_doi=item.get("source_doi"),
        source_hash=h,
        title=title,
        summary=summary,
        category=category,
        tags=[],
        translations=translations,
        original_published_at=item.get("published_at"),
        fetched_at=datetime.utcnow(),
        translated_at=datetime.utcnow() if translations else None,
        is_published=True,
        verification_status="passed",
    )
    db.add(news)
    await db.commit()
    logger.info("Saved news: [%s] %s", category, title[:70])
    return 1
