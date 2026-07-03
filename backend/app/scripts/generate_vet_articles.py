"""
Generate SEO-optimised veterinary articles from a curated topic seed list.

Reads vet_article_topics.json, skips already-published slugs, generates
detailed articles via Groq, and saves them as published Article records.

Uses GROQ_KEY_VET_ARTICLES (KEY_5) with KEY_3/4/6 as fallbacks.

Article format:
  - 1,500–2,500 words (body as JSONB blocks)
  - h2 blocks, paragraph blocks, callout blocks, table blocks
  - 5 FAQ Q&A pairs for FAQ schema
  - SEO-optimised title, excerpt (meta description), keywords
  - category = "veterinary", is_published = True

Usage:
  python -m app.scripts.generate_vet_articles                         # 5 articles/run
  python -m app.scripts.generate_vet_articles --limit 8               # 8 this run
  python -m app.scripts.generate_vet_articles --topic-slug dog-kidney  # one topic
  python -m app.scripts.generate_vet_articles --dry-run               # no saves/API
  python -m app.scripts.generate_vet_articles --force                 # overwrite existing
"""

import argparse
import asyncio
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
from app.models.models import Article

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

GROQ_API_URL    = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL      = settings.GROQ_MODEL or "llama-3.3-70b-versatile"
TOPICS_FILE     = Path(__file__).parent / "vet_article_topics.json"
WP_UA           = "MedMindAI/1.0 (https://medmind.pro; 33mikalai@gmail.com)"
TOGETHER_URL    = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL  = "black-forest-labs/FLUX.1-schnell"
MEDIA_ARTICLES  = Path("/app/data/media/articles")
MEDIA_URL_BASE  = "/media/articles"
IMAGE_STYLE     = (
    "professional veterinary medicine illustration, clean clinical photography style, "
    "soft natural lighting, no text, no labels, no watermarks, "
    "high quality, warm earthy tones, 16:9 format"
)

# Vet-specific stop words to clean up Wikipedia search queries
_VET_STOP = {
    "symptoms", "treatment", "diagnosis", "management", "guide", "complete",
    "veterinary", "emergency", "and", "the", "for", "in", "with", "how",
    "causes", "types", "options", "overview", "prevention", "care", "home",
}


# ─── Wikipedia cover image fetch ─────────────────────────────────────────────

def _wp_api(params: dict) -> dict:
    base = "https://en.wikipedia.org/w/api.php"
    url  = base + "?" + urllib.parse.urlencode({"format": "json", **params})
    req  = urllib.request.Request(url, headers={"User-Agent": WP_UA})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def _wp_thumbnail(query: str, min_width: int = 300) -> str | None:
    try:
        data  = _wp_api({"action": "query", "titles": query,
                          "prop": "pageimages", "pithumbsize": 1200, "pilicense": "any"})
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            thumb = page.get("thumbnail", {})
            src, w = thumb.get("source", ""), thumb.get("width", 0)
            if src and w >= min_width:
                return src
    except Exception:
        pass
    return None


def fetch_vet_cover_image(title: str) -> str | None:
    """Try to fetch a relevant image from Wikipedia for a vet article title."""
    clean = re.sub(r"[,:;()\[\]]", " ", title).replace("-", " ").strip()
    words = [w for w in clean.split()
             if w.lower().rstrip(".,;:") not in _VET_STOP and len(w) > 2]

    # Strategy 1: first 2 meaningful words (most specific)
    if len(words) >= 2:
        url = _wp_thumbnail(" ".join(words[:2]))
        if url:
            return url
        time.sleep(0.2)

    # Strategy 2: single first word (condition/species name)
    if words and len(words[0]) >= 4:
        url = _wp_thumbnail(words[0])
        if url:
            return url

    return None


# ─── Together.ai image generation (fallback) ─────────────────────────────────

def _build_image_prompt(title: str, species: list[str]) -> str:
    """Build a neutral, visually appealing prompt for a vet article."""
    species_str = " and ".join(species[:2]) if species else "dog and cat"
    # Extract the main subject (first 2-3 words of title, cleaned)
    clean = re.sub(r"[,:;()\[\]]", " ", title).strip()
    words = [w for w in clean.split() if w.lower() not in _VET_STOP and len(w) > 3]
    subject = " ".join(words[:3]) if words else "veterinary medicine"
    return f"{subject}, {species_str}, {IMAGE_STYLE}"


def generate_together_image(slug: str, title: str, species: list[str]) -> str | None:
    """
    Generate a cover image via Together.ai FLUX.1-schnell.
    Saves to /app/data/media/articles/{slug}.jpg
    Returns the media URL or None on failure.
    """
    key = settings.TOGETHER_API_KEY
    if not key:
        log.debug("TOGETHER_API_KEY not set, skipping AI image generation")
        return None

    prompt = _build_image_prompt(title, species)
    log.info("  Generating AI image via Together.ai: %s", prompt[:80])

    try:
        import base64
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
            log.warning("  Together.ai error %s: %s", r.status_code, r.text[:120])
            return None

        item = r.json()["data"][0]
        raw: bytes | None = None

        b64 = item.get("b64_json")
        if b64:
            raw = base64.b64decode(b64)
        else:
            img_url = item.get("url")
            if img_url:
                img_r = httpx.get(img_url, timeout=30)
                if img_r.status_code == 200:
                    raw = img_r.content

        if not raw:
            log.warning("  Together.ai: no image data in response")
            return None

        MEDIA_ARTICLES.mkdir(parents=True, exist_ok=True)
        out = MEDIA_ARTICLES / f"{slug}.jpg"
        out.write_bytes(raw)
        media_url = f"{MEDIA_URL_BASE}/{slug}.jpg"
        log.info("  AI image saved: %s (%d KB)", media_url, len(raw) // 1024)
        return media_url

    except Exception as e:
        log.warning("  Together.ai generation failed: %s", e)
        return None


# ─── Key pool ────────────────────────────────────────────────────────────────

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


async def _call_groq(prompt: str, system: str, keys: list[str], max_tokens: int = 4096) -> str | None:
    for i, key in enumerate(keys):
        try:
            async with httpx.AsyncClient(timeout=120) as c:
                r = await c.post(
                    GROQ_API_URL,
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={
                        "model": GROQ_MODEL,
                        "max_tokens": max_tokens,
                        "temperature": 0.5,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user",   "content": prompt},
                        ],
                    },
                )
            if r.status_code == 429:
                log.warning("Key %d rate-limited, trying next", i + 1)
                continue
            if r.status_code != 200:
                log.warning("Key %d error %s: %s", i + 1, r.status_code, r.text[:200])
                continue
            return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            log.warning("Key %d exception: %s", i + 1, e)
    return None


def _extract_json(raw: str) -> dict | None:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as e:
        log.warning("JSON parse failed: %s", e)
        return None


# ─── Prompts ─────────────────────────────────────────────────────────────────

SYSTEM_ARTICLE = """You are a veterinary content writer and SEO specialist (DVM + 10 years clinical experience).
Write detailed, accurate, helpful veterinary articles for pet owners and veterinary professionals.
Rules:
- All clinical information must be accurate (Merck Vet Manual / WSAVA / BSAVA standards)
- Tone: clear, professional, empathetic — works for both vets and informed pet owners
- Include specific values (doses, lab reference ranges, prognosis data) where relevant
- Structure content with clear H2 sections for SEO
- Return ONLY valid JSON, no markdown fences"""


def _article_prompt(topic: dict) -> str:
    title    = topic["title_en"]
    slug     = topic["slug"]
    species  = ", ".join(topic.get("species", ["dog", "cat"]))
    keywords = ", ".join(topic.get("keywords", []))

    return f"""Write a comprehensive veterinary article:

Title: "{title}"
Target species: {species}
SEO keywords to naturally include: {keywords}

Return JSON:
{{
  "title": "{title}",
  "slug": "{slug}",
  "excerpt": "150-160 character SEO meta description summarising the article",
  "reading_time_minutes": 8,
  "keywords": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
  "body": [
    {{
      "type": "h2",
      "content": "Introduction / Overview"
    }},
    {{
      "type": "p",
      "content": "Opening paragraph: why this topic matters, how common it is, what this article covers. 150+ words."
    }},
    {{
      "type": "h2",
      "content": "Causes and Risk Factors"
    }},
    {{
      "type": "p",
      "content": "200+ words on aetiology, breeds at risk, age/sex predispositions, environmental factors."
    }},
    {{
      "type": "h2",
      "content": "Symptoms and Clinical Signs"
    }},
    {{
      "type": "p",
      "content": "200+ words describing early vs late signs, red flags requiring emergency care."
    }},
    {{
      "type": "callout",
      "variant": "warning",
      "content": "⚠️ Emergency signs that require immediate veterinary attention: [list specific red-flag symptoms]"
    }},
    {{
      "type": "h2",
      "content": "Diagnosis"
    }},
    {{
      "type": "p",
      "content": "200+ words: what your vet will examine, which tests are done (blood tests, imaging, specific assays), what results mean."
    }},
    {{
      "type": "h2",
      "content": "Treatment Options"
    }},
    {{
      "type": "p",
      "content": "300+ words: step-by-step treatment approach, medication names (with purpose explained in plain language), dietary changes, surgery if applicable. Include typical treatment duration and what to expect."
    }},
    {{
      "type": "table",
      "headers": ["Treatment", "Purpose", "Notes"],
      "rows": [
        ["Drug/approach 1", "What it does", "Side effects / monitoring"],
        ["Drug/approach 2", "What it does", "Side effects / monitoring"],
        ["Drug/approach 3", "What it does", "Side effects / monitoring"]
      ]
    }},
    {{
      "type": "h2",
      "content": "Home Care and Monitoring"
    }},
    {{
      "type": "p",
      "content": "150+ words on what owners can do at home, diet, exercise restrictions, how to monitor response to treatment, when to call the vet."
    }},
    {{
      "type": "h2",
      "content": "Prognosis and Prevention"
    }},
    {{
      "type": "p",
      "content": "150+ words: realistic prognosis with survival statistics if available, long-term management, prevention strategies."
    }}
  ],
  "faq": [
    {{
      "question": "Specific owner question about this condition",
      "answer": "Detailed 80-120 word answer with practical information"
    }},
    {{
      "question": "Question about costs or how long treatment takes",
      "answer": "..."
    }},
    {{
      "question": "Question about home remedies or diet",
      "answer": "..."
    }},
    {{
      "question": "Question about prognosis / will my pet recover",
      "answer": "..."
    }},
    {{
      "question": "Question about prevention or reducing risk",
      "answer": "..."
    }}
  ],
  "sources": [
    {{"title": "Merck Veterinary Manual: [topic]", "url": "https://www.merckvetmanual.com/", "pmid": null}},
    {{"title": "WSAVA Global Nutrition Guidelines", "url": "https://wsava.org/", "pmid": null}}
  ]
}}

Write ALL content in English. Be thorough — this article should be the best resource on the topic."""


# ─── Save to DB ───────────────────────────────────────────────────────────────

async def save_article(session: AsyncSession, data: dict, topic: dict,
                       cover_image: str | None = None) -> bool:
    article = Article(
        slug=data.get("slug") or topic["slug"],
        title=data.get("title") or topic["title_en"],
        excerpt=data.get("excerpt", "")[:500],
        body=data.get("body", []),
        category="veterinary",
        subcategory=", ".join(topic.get("species", [])),
        keywords=data.get("keywords", topic.get("keywords", [])),
        reading_time_minutes=data.get("reading_time_minutes", 8),
        schema_type="MedicalWebPage",
        faq=data.get("faq", []),
        sources=data.get("sources", []),
        cover_image=cover_image,
        is_published=True,
        published_at=datetime.utcnow(),
        generated_by="groq-llama-3.3-70b",
        review_status="published",
        verification_status="pending",
    )
    session.add(article)
    await session.commit()
    return True


# ─── Main ─────────────────────────────────────────────────────────────────────

async def main(args: argparse.Namespace) -> None:
    if not TOPICS_FILE.exists():
        log.error("Topics file not found: %s", TOPICS_FILE)
        sys.exit(1)

    topics = json.loads(TOPICS_FILE.read_text())
    keys   = _get_keys()
    log.info("Loaded %d topics. Keys: %d. Limit this run: %d", len(topics), len(keys), args.limit)

    # Filter to single topic if requested
    if args.topic_slug:
        topics = [t for t in topics if t["slug"] == args.topic_slug]
        if not topics:
            log.error("Topic slug not found: %s", args.topic_slug)
            sys.exit(1)

    # Get already-published slugs
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Article.slug).where(Article.category == "veterinary")
        )
        existing_slugs = {row[0] for row in result.all()}

    log.info("Existing vet article slugs: %d", len(existing_slugs))

    generated = 0
    for topic in topics:
        if generated >= args.limit:
            break

        slug = topic["slug"]
        if slug in existing_slugs and not args.force:
            log.info("Skip (exists): %s", slug)
            continue

        log.info("[%d/%d] Generating: %s", generated + 1, args.limit, topic["title_en"])

        if args.dry_run:
            log.info("[DRY RUN] would generate: %s", slug)
            generated += 1
            continue

        raw = await _call_groq(_article_prompt(topic), SYSTEM_ARTICLE, keys, max_tokens=4096)
        if not raw:
            log.error("No response for %s", slug)
            await asyncio.sleep(10)
            continue

        data = _extract_json(raw)
        if not data:
            log.error("Could not parse JSON for %s", slug)
            continue

        # Cover image: Wikipedia first → Together.ai fallback
        cover_image: str | None = None
        article_title  = data.get("title") or topic["title_en"]
        article_species = topic.get("species", ["dog", "cat"])
        try:
            cover_image = fetch_vet_cover_image(article_title)
            if cover_image:
                log.info("  cover_image (Wikipedia): %s", cover_image[:80])
        except Exception as e:
            log.warning("  Wikipedia image fetch failed: %s", e)

        if not cover_image:
            cover_image = generate_together_image(slug, article_title, article_species)
            if not cover_image:
                log.info("  cover_image: none (will show placeholder)")

        async with AsyncSessionLocal() as session:
            ok = await save_article(session, data, topic, cover_image=cover_image)

        if ok:
            log.info("Saved: %s ✓", slug)
            generated += 1
            existing_slugs.add(slug)

        await asyncio.sleep(4)

    log.info("Done. Articles generated this run: %d", generated)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate SEO vet articles from topic seed list")
    parser.add_argument("--limit",      type=int, default=5,  help="Max articles this run (default 5)")
    parser.add_argument("--topic-slug", type=str,             help="Generate only this topic slug")
    parser.add_argument("--dry-run",    action="store_true",  help="Preview without API calls or saves")
    parser.add_argument("--force",      action="store_true",  help="Overwrite existing articles")
    args = parser.parse_args()
    asyncio.run(main(args))
