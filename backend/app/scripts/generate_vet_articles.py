"""
Generate SEO-optimised veterinary articles from a curated topic seed list.

Quality pipeline:
  1. PubMed grounding  — fetch 6-8 recent papers via NCBI E-utilities (stdlib urllib)
  2. LLM generation    — Groq llama-3.3-70b with VET_ARTICLE_PROMPT (4500+ words)
  3. Cover image       — Pexels stock photo (primary) → Together.ai FLUX (fallback)
  4. DB save           — body as JSONB blocks; PMIDs in sources + verified_sources

Uses GROQ_KEY_VET_ARTICLES (KEY_5) with KEY_3/4/6 as fallbacks.

Usage:
  python -m app.scripts.generate_vet_articles                       # 5 articles/run
  python -m app.scripts.generate_vet_articles --limit 8
  python -m app.scripts.generate_vet_articles --topic-slug dog-kidney-disease-symptoms-treatment
  python -m app.scripts.generate_vet_articles --dry-run
  python -m app.scripts.generate_vet_articles --force
"""

import argparse
import asyncio
import base64
import json
import logging
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.models import Article, ArticleTranslation
from app.services.article_pipeline import (
    _translate_article,
    LOCALES,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

GROQ_API_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL     = settings.GROQ_MODEL or "llama-3.3-70b-versatile"
TOPICS_FILE    = Path(__file__).parent / "vet_article_topics.json"
TOGETHER_URL   = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL = "black-forest-labs/FLUX.1-schnell"
MEDIA_ARTICLES = Path("/app/data/media/articles")
MEDIA_URL_BASE = "/media/articles"
NCBI_BASE      = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
APP_UA         = "MedMindAI/1.0 (https://medmind.pro; 33mikalai@gmail.com)"
# Pexels curated queries per species — ordered by visual appeal, rotate via article slug hash
SPECIES_PEXELS_QUERIES: dict[str, list[str]] = {
    "dog":     ["golden retriever dog outdoors", "labrador dog portrait", "dog nature sunny", "german shepherd dog"],
    "cat":     ["cat portrait natural light", "tabby cat indoor", "domestic cat window", "fluffy cat close-up"],
    "horse":   ["horse green field", "horse portrait sunset", "bay horse outdoors", "horse countryside"],
    "cattle":  ["dairy cow farm field", "cattle farm countryside", "cow pasture green"],
    "rabbit":  ["rabbit pet portrait", "bunny rabbit close-up", "white rabbit nature"],
    "bird":    ["parrot colorful portrait", "cockatiel pet bird", "macaw tropical bird"],
    "reptile": ["bearded dragon lizard", "gecko reptile portrait", "iguana green closeup"],
}

# Species → photorealistic AI image prompt (no medical/clinical context)
SPECIES_AI_PROMPTS: dict[str, str] = {
    "dog":     (
        "golden retriever dog sitting in a sunlit park, shallow depth of field, "
        "DSLR photography, natural warm light, soft bokeh background, "
        "high resolution, 16:9 format, no text"
    ),
    "cat":     (
        "beautiful tabby cat sitting by a window with natural light, "
        "close-up portrait, DSLR photography, soft bokeh, "
        "warm indoor atmosphere, high resolution, 16:9 format, no text"
    ),
    "horse":   (
        "majestic bay horse in a green field at golden hour, "
        "wide landscape, DSLR photography, natural sunlight, "
        "high resolution, 16:9 format, no text"
    ),
    "cattle":  (
        "dairy cow on green farm pasture, natural morning light, "
        "countryside photography, wide shot, "
        "high resolution, 16:9 format, no text"
    ),
    "rabbit":  (
        "white domestic rabbit on soft grass, natural daylight, "
        "close-up portrait, shallow depth of field, "
        "high resolution, 16:9 format, no text"
    ),
    "bird":    (
        "colorful parrot perched on a branch, vibrant feathers, "
        "natural light, wildlife photography, "
        "high resolution, 16:9 format, no text"
    ),
    "reptile": (
        "bearded dragon lizard on a rock, natural lighting, "
        "close-up macro photography, vivid colours, "
        "high resolution, 16:9 format, no text"
    ),
}

# ─── PubMed grounding ────────────────────────────────────────────────────────

def _ncbi_get(endpoint: str, params: dict) -> dict:
    """GET request to NCBI E-utilities (stdlib only — works inside Docker)."""
    url = f"{NCBI_BASE}/{endpoint}?" + urllib.parse.urlencode(
        {"retmode": "json", **params}
    )
    req = urllib.request.Request(url, headers={"User-Agent": APP_UA})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def fetch_pubmed_refs(query: str, n: int = 6) -> list[dict]:
    """
    Fetch n recent PubMed papers relevant to the given veterinary topic.
    Returns list of {pmid, title, authors, journal, year, url}.
    Rate-limited to 3 req/sec without NCBI API key.
    """
    try:
        # Step 1: search
        search = _ncbi_get("esearch.fcgi", {
            "db": "pubmed", "term": query, "retmax": n,
            "sort": "relevance", "field": "tiab",
        })
        ids = search.get("esearchresult", {}).get("idlist", [])
        if not ids:
            return []

        time.sleep(0.4)  # respect 3 req/sec limit

        # Step 2: fetch summaries
        summary = _ncbi_get("esummary.fcgi", {
            "db": "pubmed", "id": ",".join(ids),
        })
        results = []
        for pmid in ids:
            doc = summary.get("result", {}).get(pmid, {})
            if not doc or "title" not in doc:
                continue

            authors_list = doc.get("authors", [])
            first_auth   = authors_list[0].get("name", "") if authors_list else ""
            et_al        = " et al." if len(authors_list) > 1 else ""
            year         = doc.get("pubdate", "")[:4]
            journal      = doc.get("fulljournalname") or doc.get("source", "")

            results.append({
                "pmid":    pmid,
                "title":   doc.get("title", "").rstrip("."),
                "authors": f"{first_auth}{et_al}",
                "journal": journal,
                "year":    year,
                "url":     f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            })

        log.info("  PubMed: found %d/%d refs for query '%s'", len(results), n, query[:60])
        return results

    except Exception as e:
        log.warning("  PubMed fetch failed: %s", e)
        return []


# ─── Pexels cover image ───────────────────────────────────────────────────────

def _pexels_fetch(query: str, key: str) -> str | None:
    """Single Pexels API call — returns large2x URL or None."""
    url = (
        "https://api.pexels.com/v1/search?"
        + urllib.parse.urlencode({"query": query, "per_page": 5, "orientation": "landscape"})
    )
    req = urllib.request.Request(url, headers={"Authorization": key, "User-Agent": APP_UA})
    with urllib.request.urlopen(req, timeout=12) as r:
        data = json.loads(r.read())
    photos = data.get("photos", [])
    if photos:
        return photos[0]["src"].get("large2x") or photos[0]["src"].get("original")
    return None


def fetch_pexels_image(species: list[str], slug: str) -> str | None:
    """
    Search Pexels using curated species-specific queries.
    Uses slug hash to rotate query variants for visual variety across articles.
    Returns the large2x URL or None.
    """
    key = settings.PEXELS_API_KEY
    if not key:
        return None

    sp      = species[0] if species else "dog"
    queries = SPECIES_PEXELS_QUERIES.get(sp, [f"{sp} animal portrait"])
    # Rotate query based on slug so different articles get different photos
    idx   = hash(slug) % len(queries)
    order = queries[idx:] + queries[:idx]  # start at rotated position

    try:
        for query in order:
            result = _pexels_fetch(query, key)
            if result:
                log.info("  Pexels ('%s'): %s", query, result[:80])
                return result
            time.sleep(0.3)
    except Exception as e:
        log.warning("  Pexels failed: %s", e)

    return None


# ─── Together.ai image generation (fallback) ─────────────────────────────────

def generate_together_image(slug: str, title: str, species: list[str]) -> str | None:
    """
    Generate a photorealistic animal photo via Together.ai FLUX.1-schnell.
    Uses species-specific portrait prompts — no clinical/3D style.
    Saves to /app/data/media/articles/{slug}.jpg
    """
    key = settings.TOGETHER_API_KEY
    if not key:
        return None

    sp     = species[0] if species else "dog"
    prompt = SPECIES_AI_PROMPTS.get(sp, f"{sp} animal portrait, natural light, DSLR photography, 16:9, no text")
    log.info("  Together.ai prompt: %s", prompt[:100])

    try:
        r = httpx.post(
            TOGETHER_URL,
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model":  TOGETHER_MODEL,
                "prompt": prompt,
                "width":  1280,
                "height": 720,
                "steps":  4,
                "n":      1,
            },
            timeout=90,
        )
        if r.status_code != 200:
            log.warning("  Together.ai %s: %s", r.status_code, r.text[:120])
            return None

        item   = r.json()["data"][0]
        b64    = item.get("b64_json")
        raw: bytes | None = base64.b64decode(b64) if b64 else None

        if not raw:
            img_url = item.get("url", "")
            if img_url:
                img_r = httpx.get(img_url, timeout=30)
                if img_r.status_code == 200:
                    raw = img_r.content

        if not raw:
            return None

        MEDIA_ARTICLES.mkdir(parents=True, exist_ok=True)
        out      = MEDIA_ARTICLES / f"{slug}.jpg"
        out.write_bytes(raw)
        media_url = f"{MEDIA_URL_BASE}/{slug}.jpg"
        log.info("  AI image saved: %s (%d KB)", media_url, len(raw) // 1024)
        return media_url

    except Exception as e:
        log.warning("  Together.ai failed: %s", e)
        return None


# ─── Groq key pool ───────────────────────────────────────────────────────────

def _get_keys() -> list[str]:
    candidates = [
        settings.GROQ_KEY_VET_ARTICLES,
        settings.GROQ_API_KEY_3,
        settings.GROQ_API_KEY_4,
        settings.GROQ_API_KEY_6,
    ]
    keys = [k.strip() for k in candidates if k and k.strip()]
    if not keys:
        log.error("No Groq keys. Set GROQ_KEY_VET_ARTICLES in .env")
        sys.exit(1)
    return keys


async def _call_groq(prompt: str, system: str, keys: list[str],
                     max_tokens: int = 8000) -> str | None:
    for i, key in enumerate(keys):
        try:
            async with httpx.AsyncClient(timeout=180) as c:
                r = await c.post(
                    GROQ_API_URL,
                    headers={"Authorization": f"Bearer {key}",
                             "Content-Type": "application/json"},
                    json={
                        "model":       GROQ_MODEL,
                        "max_tokens":  max_tokens,
                        "temperature": 0.4,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user",   "content": prompt},
                        ],
                    },
                )
            if r.status_code == 429:
                log.warning("Key %d rate-limited, trying next", i + 1)
                await asyncio.sleep(5)
                continue
            if r.status_code != 200:
                log.warning("Key %d error %s: %s", i + 1, r.status_code, r.text[:200])
                continue
            return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            log.warning("Key %d exception: %s", i + 1, e)
    return None


def _sanitize_json_strings(s: str) -> str:
    """Escape raw control characters (0x00-0x1f) that appear inside JSON string values."""
    result: list[str] = []
    in_str  = False
    escaped = False
    for ch in s:
        if escaped:
            result.append(ch)
            escaped = False
        elif ch == "\\":
            result.append(ch)
            escaped = True
        elif ch == '"':
            result.append(ch)
            in_str = not in_str
        elif in_str and ord(ch) < 0x20:
            # Replace bare control char with JSON escape
            _MAP = {"\n": "\\n", "\t": "\\t", "\r": "\\r"}
            result.append(_MAP.get(ch, f"\\u{ord(ch):04x}"))
        else:
            result.append(ch)
    return "".join(result)


def _find_json_object(text: str) -> str | None:
    """
    Extract the outermost JSON object from text using bracket-depth tracking.
    Handles strings (with escape sequences) correctly so embedded } don't confuse it.
    """
    start = text.find("{")
    if start == -1:
        return None
    depth, in_str, escaped = 0, False, False
    for i, ch in enumerate(text[start:], start):
        if escaped:
            escaped = False
            continue
        if ch == "\\" and in_str:
            escaped = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    # Truncated — return from start to end of text
    return text[start:]


def _extract_json(raw: str) -> dict | None:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$",          "", raw)

    fragment = _find_json_object(raw)
    if not fragment:
        return None

    for attempt in [fragment, _sanitize_json_strings(fragment)]:
        try:
            return json.loads(attempt)
        except json.JSONDecodeError:
            pass

    # Truncated JSON — try adding missing closing brackets
    sanitised = _sanitize_json_strings(fragment)
    for suffix in ['"]}}}', '"]}}', '"]}', ']}}', ']}', '}']:
        try:
            return json.loads(sanitised + suffix)
        except Exception:
            pass

    log.warning("JSON parse failed for fragment (%d chars)", len(fragment))
    return None


# ─── Prompt ──────────────────────────────────────────────────────────────────

VET_SYSTEM = """\
You are a senior veterinarian, board-certified clinical specialist, and evidence-based \
medical educator writing authoritative veterinary references comparable to the Merck \
Veterinary Manual, WSAVA guidelines, and BSAVA Manuals.
Audience: veterinary students, general practitioners, and informed pet owners.
Rules:
- All clinical information must meet WSAVA/BSAVA/ACVIM/AAFP/Merck Vet Manual standards
- Every drug: generic name, exact dose in mg/kg, route, frequency, duration
- Every statistic: specific percentage or absolute number — never vague ranges
- Every guideline: name the organisation (WSAVA, BSAVA, ACVIM, AAFP, Merck)
- Species-specific differences clearly noted throughout
- Return ONLY valid JSON — no markdown fences, no text outside the JSON object"""


def _build_prompt(topic: dict, pubmed_refs: list[dict]) -> str:
    title   = topic["title_en"]
    slug    = topic["slug"]
    species = ", ".join(topic.get("species", ["dog", "cat"]))
    kws     = ", ".join(topic.get("keywords", []))

    refs_block = ""
    if pubmed_refs:
        refs_block = "\n\nPUBMED GROUNDING (cite as [PMID: XXXXXX] where relevant):\n"
        for r in pubmed_refs:
            refs_block += f"- PMID {r['pmid']}: {r['title']} ({r['journal']}, {r['year']})\n"

    pmids_json = json.dumps([r["pmid"] for r in pubmed_refs]) if pubmed_refs else "[]"

    return f"""Write a comprehensive, evidence-based veterinary article.

Title: "{title}"
Species: {species}
Keywords: {kws}{refs_block}

RULES — every section must have:
- Exact drug doses (mg/kg, route, frequency, duration)
- Specific lab reference ranges (species-specific)
- Named guidelines (WSAVA, BSAVA, ACVIM, AAFP, Merck Vet Manual)
- Incidence/prevalence numbers (not "common" or "rare")
- PMIDs from grounding evidence where directly applicable

Return valid JSON:
{{
  "title": "{title}",
  "slug": "{slug}",
  "excerpt": "155-char SEO meta description with the key clinical takeaway",
  "reading_time_minutes": 10,
  "keywords": ["kw1","kw2","kw3","kw4","kw5"],
  "body": [
    {{"type":"h2","content":"Key Points"}},
    {{"type":"p","content":"10 bullet points (• prefix), each with a specific value or dose. 200+ words."}},
    {{"type":"h2","content":"Overview and Epidemiology"}},
    {{"type":"p","content":"Definition, prevalence (specific %), breed/age/sex predispositions, economic impact. 300+ words."}},
    {{"type":"h2","content":"Pathophysiology"}},
    {{"type":"p","content":"Cellular/molecular mechanisms, organ pathology, biomarkers, species differences. 300+ words."}},
    {{"type":"h2","content":"Clinical Signs and Presentation"}},
    {{"type":"p","content":"Early and late signs with prevalence %, physical exam findings, red flags. 250+ words."}},
    {{"type":"callout","variant":"warning","content":"⚠️ EMERGENCY: [5-7 specific red-flag signs requiring immediate care]"}},
    {{"type":"h2","content":"Diagnosis"}},
    {{"type":"p","content":"Diagnostic algorithm, tests with reference ranges, imaging findings, staging systems. 300+ words."}},
    {{"type":"table","headers":["Test","Measures","Reference Range","Significance"],"rows":[["test1","...","...","..."],["test2","...","...","..."],["test3","...","...","..."]]}},
    {{"type":"h2","content":"Treatment and Management"}},
    {{"type":"h3","content":"Acute Stabilisation"}},
    {{"type":"p","content":"Emergency interventions, fluid rates (mL/kg/hr), immediate drugs with doses. 150+ words."}},
    {{"type":"h3","content":"First-Line Pharmacotherapy"}},
    {{"type":"p","content":"First-choice drugs: generic name, exact dose mg/kg, route, frequency, duration, monitoring. Named guideline. 250+ words."}},
    {{"type":"table","headers":["Drug","Dose & Route","Frequency","Duration","Monitoring"],"rows":[["drug1","Xmg/kg PO","SID","long-term","labs q3mo"],["drug2","...","...","...","..."]]}},
    {{"type":"h3","content":"Nutrition and Supportive Care"}},
    {{"type":"p","content":"Dietary targets (protein g/kg/day, phosphorus mg/day), named therapeutic diets, supplements with doses. 200+ words."}},
    {{"type":"h2","content":"Prognosis and Complications"}},
    {{"type":"p","content":"Median survival by stage, 1-yr survival %, complication rates, referral criteria. 200+ words."}},
    {{"type":"h2","content":"Recent Advances (2020–2025)"}},
    {{"type":"p","content":"New approvals, updated guidelines, emerging therapies with evidence status. Cite PMIDs. 150+ words."}},
    {{"type":"h2","content":"Owner Guidance"}},
    {{"type":"p","content":"Home monitoring checklist, medication tips, warning signs, follow-up schedule. 150+ words."}},
    {{"type":"callout","variant":"info","content":"ℹ️ CLINICAL PEARLS:\\n• [8 high-yield facts, each with specific value or classic association]"}}
  ],
  "faq": [
    {{"question":"How is this condition diagnosed?","answer":"80-word answer with specific tests and values"}},
    {{"question":"What is the prognosis?","answer":"80-word answer with survival data"}},
    {{"question":"What treatments are available?","answer":"80-word answer with drug names and doses"}},
    {{"question":"Can this be managed at home?","answer":"80-word practical answer"}},
    {{"question":"How can I prevent this condition?","answer":"80-word actionable answer"}}
  ],
  "pmids": {pmids_json}
}}

Replace ALL placeholder text with real, detailed veterinary content. Total body: 2500+ words."""


# ─── Save to DB ───────────────────────────────────────────────────────────────

async def save_article(
    session: AsyncSession,
    data: dict,
    topic: dict,
    pubmed_refs: list[dict],
    cover_image: str | None = None,
) -> bool:
    # Build sources from PubMed refs + any LLM-added extras
    pubmed_sources = [
        {
            "title":   r["title"],
            "url":     r["url"],
            "pmid":    r["pmid"],
            "authors": r["authors"],
            "journal": r["journal"],
            "year":    r["year"],
        }
        for r in pubmed_refs
    ]
    verified: list[dict] = pubmed_sources  # only real PubMed refs get verified status
    pmid_set = {str(r["pmid"]) for r in pubmed_refs}
    for s in data.get("sources", []):
        if s.get("pmid") and str(s["pmid"]) not in pmid_set:
            pubmed_sources.append(s)

    title   = data.get("title") or topic["title_en"]
    excerpt = data.get("excerpt", "")[:500]
    body    = data.get("body", [])
    faq     = data.get("faq", [])
    kws     = data.get("keywords", topic.get("keywords", []))

    article = Article(
        slug=data.get("slug") or topic["slug"],
        title=title,
        excerpt=excerpt,
        body=body,
        category="veterinary",
        subcategory=", ".join(topic.get("species", [])),
        keywords=kws,
        reading_time_minutes=data.get("reading_time_minutes", 10),
        schema_type="MedicalWebPage",
        faq=faq,
        sources=pubmed_sources,
        verified_sources=verified if verified else None,
        cover_image=cover_image,
        is_published=True,
        published_at=datetime.utcnow(),
        generated_by="groq-llama-3.3-70b",
        review_status="published",
        verification_status="pending",
    )
    session.add(article)
    await session.commit()
    await session.refresh(article)

    # Translate to all project locales concurrently
    log.info("  Translating to %d locales: %s", len(LOCALES), LOCALES)
    try:
        translations = await asyncio.gather(*[
            _translate_article(title, excerpt, body, kws, loc)
            for loc in LOCALES
        ], return_exceptions=True)

        for loc, tr in zip(LOCALES, translations):
            if isinstance(tr, dict) and tr.get("title"):
                qa_checked_at = None
                raw_ts = tr.get("qa_checked_at")
                if raw_ts:
                    try:
                        from datetime import datetime as _dt
                        qa_checked_at = _dt.fromisoformat(raw_ts)
                    except Exception:
                        pass
                session.add(ArticleTranslation(
                    article_id=article.id,
                    locale=loc,
                    title=tr.get("title", title),
                    excerpt=tr.get("excerpt", excerpt),
                    body=tr.get("body", body),
                    status="done",
                    translation_verification_status=tr.get("qa_status", "pending"),
                    translation_qa_report=tr.get("qa_report"),
                    translation_qa_checked_at=qa_checked_at,
                ))
            else:
                log.warning("  Translation failed for locale %s: %s", loc, tr)

        await session.commit()
        log.info("  Translations saved for %d locales", len(LOCALES))
    except Exception as e:
        log.warning("  Translation step failed (article still saved): %s", e)

    return True


# ─── Main ─────────────────────────────────────────────────────────────────────

async def main(args: argparse.Namespace) -> None:
    if not TOPICS_FILE.exists():
        log.error("Topics file not found: %s", TOPICS_FILE)
        sys.exit(1)

    topics = json.loads(TOPICS_FILE.read_text())
    keys   = _get_keys()
    log.info("Loaded %d topics. Groq keys: %d. Limit this run: %d",
             len(topics), len(keys), args.limit)

    if args.topic_slug:
        topics = [t for t in topics if t["slug"] == args.topic_slug]
        if not topics:
            log.error("Topic slug not found: %s", args.topic_slug)
            sys.exit(1)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Article.slug).where(Article.category == "veterinary")
        )
        existing_slugs = {row[0] for row in result.all()}

    log.info("Existing vet articles in DB: %d", len(existing_slugs))

    generated = 0
    for topic in topics:
        if generated >= args.limit:
            break

        slug = topic["slug"]
        if slug in existing_slugs and not args.force:
            log.info("Skip (exists): %s", slug)
            continue

        log.info("[%d/%d] Starting: %s", generated + 1, args.limit, topic["title_en"])

        if args.dry_run:
            log.info("[DRY RUN] would generate: %s", slug)
            generated += 1
            continue

        # 1. PubMed grounding
        species_str = " ".join(topic.get("species", ["dog", "cat"]))
        keywords    = " ".join(topic.get("keywords", [])[:3])
        pubmed_refs = fetch_pubmed_refs(
            f"{species_str} {keywords}", n=7
        )
        time.sleep(0.5)  # be polite to NCBI

        # 2. LLM generation (up to 3 attempts on bad JSON)
        prompt = _build_prompt(topic, pubmed_refs)
        data: dict | None = None
        for attempt in range(3):
            raw = await _call_groq(prompt, VET_SYSTEM, keys, max_tokens=8000)
            if not raw:
                log.warning("No LLM response on attempt %d for %s", attempt + 1, slug)
                await asyncio.sleep(15)
                continue
            data = _extract_json(raw)
            if data:
                break
            log.warning("JSON parse failed on attempt %d for %s — retrying", attempt + 1, slug)
            await asyncio.sleep(10)
        if not data:
            log.error("Could not parse JSON after 3 attempts for %s", slug)
            continue

        log.info("  Body blocks: %d | FAQ: %d | PMIDs: %s",
                 len(data.get("body", [])),
                 len(data.get("faq",  [])),
                 data.get("pmids", pubmed_refs and [r["pmid"] for r in pubmed_refs]))

        # 3. Cover image: Pexels → Together.ai → None
        cover_image:     str | None = None
        article_species: list[str]  = topic.get("species", ["dog", "cat"])
        article_title:   str        = data.get("title") or topic["title_en"]

        cover_image = fetch_pexels_image(article_species, slug)
        if not cover_image:
            log.info("  Pexels: no image found, trying Together.ai")
            cover_image = generate_together_image(slug, article_title, article_species)
        if not cover_image:
            log.info("  cover_image: none (placeholder will show)")

        # 4. Save to DB (delete first if --force)
        async with AsyncSessionLocal() as session:
            if args.force and slug in existing_slugs:
                from sqlalchemy import delete as sqdelete
                await session.execute(sqdelete(Article).where(Article.slug == slug))
                await session.commit()
            ok = await save_article(session, data, topic, pubmed_refs, cover_image=cover_image)

        if ok:
            log.info("Saved: %s ✓  (cover: %s)", slug,
                     cover_image[:60] if cover_image else "none")
            generated += 1
            existing_slugs.add(slug)

        # Polite delay between articles
        await asyncio.sleep(5)

    log.info("Done. Articles generated this run: %d / %d", generated, args.limit)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate SEO vet articles — PubMed-grounded, Pexels images"
    )
    parser.add_argument("--limit",      type=int, default=5,
                        help="Max articles this run (default 5)")
    parser.add_argument("--topic-slug", type=str,
                        help="Generate only this specific topic slug")
    parser.add_argument("--dry-run",    action="store_true",
                        help="Preview without API calls or DB writes")
    parser.add_argument("--force",      action="store_true",
                        help="Overwrite already-published articles")
    args = parser.parse_args()
    asyncio.run(main(args))
