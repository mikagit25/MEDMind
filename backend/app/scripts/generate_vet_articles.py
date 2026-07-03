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

GROQ_API_URL  = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL    = settings.GROQ_MODEL or "llama-3.3-70b-versatile"
TOPICS_FILE   = Path(__file__).parent / "vet_article_topics.json"


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

async def save_article(session: AsyncSession, data: dict, topic: dict) -> bool:
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

        async with AsyncSessionLocal() as session:
            ok = await save_article(session, data, topic)

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
