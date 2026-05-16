"""
Article generation pipeline:
  1. Gather research context from open sources (PMC, Wikipedia, MedlinePlus)
  2. Generate original article via Claude using that context
  3. Translate to 6 languages
  4. Publish + notify search engines

Usage:
    from app.services.article_pipeline import run_pipeline
    await run_pipeline("Atrial Fibrillation", "cardiology", db_session)
"""
import asyncio
import logging
import re
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

log = logging.getLogger(__name__)

LOCALES = ["ru", "de", "fr", "es", "tr", "ar"]


def _slugify(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:200]


async def _generate_with_context(
    topic: str,
    category: str,
    research_context: str,
    model: str = "haiku",
) -> dict:
    """
    Call Claude with research context to produce a fully original article.
    The context provides facts; Claude writes original prose — no copying.
    """
    from app.core.config import settings
    import anthropic

    SCHEMA_HINTS = {
        "cardiology": "MedicalCondition",
        "neurology": "MedicalCondition",
        "pharmacology": "Drug",
        "surgery": "MedicalProcedure",
        "pediatrics": "MedicalCondition",
        "internal-medicine": "MedicalCondition",
        "ob-gyn": "MedicalCondition",
        "veterinary": "MedicalCondition",
        "dermatology": "MedicalCondition",
        "oncology": "MedicalCondition",
        "psychiatry": "MedicalCondition",
        "emergency": "MedicalCondition",
        "infectious": "MedicalCondition",
        "anatomy": "MedicalWebPage",
    }
    schema_type = SCHEMA_HINTS.get(category.lower(), "MedicalWebPage")

    system_prompt = f"""You are a senior medical writer producing evidence-based educational content.
You are given research context from open-access sources (PMC, Wikipedia, MedlinePlus).
Your task: write a COMPLETELY ORIGINAL article that covers this topic comprehensively.
Do NOT copy sentences from the research context. Use the facts and findings, but express them in your own words.
Your article must be at least 1000 words of original content.

Schema type: {schema_type}
Category: {category}

Return ONLY valid JSON (no markdown code fences):
{{
  "title": "Clinical and descriptive title (60-80 chars)",
  "excerpt": "2-3 sentence summary (150-200 chars)",
  "og_title": "SEO title (50-60 chars)",
  "og_description": "SEO description (120-150 chars)",
  "subcategory": "specific subcategory or null",
  "reading_time_minutes": <integer>,
  "keywords": ["kw1", "kw2", "kw3", "kw4", "kw5", "kw6"],
  "body": [
    {{"type": "h2", "content": "Heading text"}},
    {{"type": "p",  "content": "Paragraph text (4-6 sentences)"}},
    {{"type": "ul", "items": ["Point 1", "Point 2", "Point 3"]}},
    ... (8-12 blocks total for thorough coverage)
  ],
  "faq": [
    {{"question": "Q1?", "answer": "A1 (2-3 sentences)"}},
    {{"question": "Q2?", "answer": "A2 (2-3 sentences)"}},
    {{"question": "Q3?", "answer": "A3 (2-3 sentences)"}}
  ],
  "sources": [
    {{"title": "Source title", "url": "https://...", "pmid": "optional"}},
    ...
  ]
}}"""

    user_msg = (
        f"Topic: {topic}\nCategory: {category}\n\n"
        f"{research_context}\n\n"
        "Now write an original, comprehensive medical article about this topic. "
        "Use the research above as factual basis but write entirely in your own words."
    )

    model_id = "claude-haiku-4-5-20251001" if model == "haiku" else "claude-sonnet-4-6"
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=60)
    msg = await client.messages.create(
        model=model_id,
        max_tokens=4000,
        messages=[{"role": "user", "content": user_msg}],
        system=system_prompt,
    )
    raw = msg.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    import json
    try:
        return json.loads(raw)
    except Exception:
        # Attempt to extract JSON object
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            return json.loads(m.group())
        raise


def _gtranslate(text: str, locale: str) -> str:
    """Google Translate free API. Returns translated text or original on error."""
    import urllib.request, urllib.parse, json as _json
    if not text or not text.strip():
        return text
    try:
        url = (
            "https://translate.googleapis.com/translate_a/single"
            "?client=gtx&sl=en&tl=" + locale
            + "&dt=t&q=" + urllib.parse.quote(text[:4500])
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = _json.loads(resp.read())
        return "".join(part[0] for part in data[0] if part[0])
    except Exception:
        return text


def _translate_blocks(blocks: list, locale: str) -> list:
    """Translate all article body blocks using Google Translate."""
    import time
    result = []
    for block in blocks:
        btype = block.get("type", "")
        nb = dict(block)
        if btype in ("h2", "h3", "p", "callout"):
            if block.get("content"):
                nb["content"] = _gtranslate(block["content"], locale)
                time.sleep(0.25)
        elif btype == "ul":
            items = block.get("items", [])
            nb["items"] = [_gtranslate(it, locale) for it in items]
            time.sleep(0.1 * len(items))
        elif btype == "table":
            nb["headers"] = [_gtranslate(h, locale) for h in block.get("headers", [])]
            nb["rows"]    = [[_gtranslate(c, locale) for c in row] for row in block.get("rows", [])]
            time.sleep(0.3)
        result.append(nb)
    return result


async def _translate_article(
    title: str,
    excerpt: str,
    body_blocks: list,
    teaching_points: list,
    locale: str,
) -> dict:
    """Translate article to locale using Google Translate (free, no API quota)."""
    import asyncio
    loop = asyncio.get_event_loop()

    tr_title   = await loop.run_in_executor(None, _gtranslate, title,   locale)
    tr_excerpt = await loop.run_in_executor(None, _gtranslate, excerpt, locale)
    tr_body    = await loop.run_in_executor(None, _translate_blocks, body_blocks, locale)

    return {"title": tr_title, "excerpt": tr_excerpt, "body": tr_body}


async def run_pipeline(
    topic: str,
    category: str,
    db: AsyncSession,
    model: str = "haiku",
    auto_publish: bool = True,
    skip_if_exists: bool = True,
) -> Optional[str]:
    """
    Full pipeline: research → generate → translate → publish.
    Returns the article slug on success, None if skipped or failed.
    """
    from app.models.models import Article
    from app.services.open_content_scraper import gather_research_context
    from app.services.indexing_service import notify_article_published

    # Check for existing article on this topic
    slug_candidate = _slugify(topic)
    if skip_if_exists:
        existing = (await db.execute(
            select(Article).where(Article.slug.like(f"{slug_candidate[:50]}%"))
        )).scalar_one_or_none()
        if existing:
            log.info("Article already exists for topic '%s' — skipping", topic)
            return None

    log.info("Pipeline start: '%s' (%s)", topic, category)

    # Step 1: gather research context
    context = await gather_research_context(topic, max_pubmed=3)
    log.info("Research context gathered: %d chars", len(context))

    # Step 2: generate original article
    try:
        article_data = await _generate_with_context(topic, category, context, model)
    except Exception as e:
        log.error("Article generation failed for '%s': %s", topic, e)
        return None

    title    = article_data.get("title", topic)
    excerpt  = article_data.get("excerpt", "")
    body     = article_data.get("body", [])
    faq      = article_data.get("faq", [])
    sources  = article_data.get("sources", [])
    keywords = article_data.get("keywords", [])

    # Unique slug
    base_slug = _slugify(title) or slug_candidate
    slug = base_slug
    suffix = 1
    while (await db.execute(select(Article).where(Article.slug == slug))).scalar_one_or_none():
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    # Step 3: save article
    article = Article(
        slug=slug,
        title=title,
        excerpt=excerpt,
        body=body,
        category=category.lower(),
        subcategory=article_data.get("subcategory"),
        keywords=keywords,
        reading_time_minutes=article_data.get("reading_time_minutes", 6),
        schema_type=article_data.get("schema_type", "MedicalWebPage"),
        og_title=article_data.get("og_title", title[:60]),
        og_description=article_data.get("og_description", excerpt[:150]),
        faq=faq,
        sources=sources,
        is_published=auto_publish,
        published_at=datetime.utcnow() if auto_publish else None,
        review_status="published",
        generated_by="pipeline-claude",
    )
    db.add(article)
    await db.commit()
    await db.refresh(article)
    log.info("Article saved: %s", slug)

    # Step 4: translate concurrently
    from app.models.models import ArticleTranslation
    try:
        translations = await asyncio.gather(*[
            _translate_article(title, excerpt, body, keywords, loc)
            for loc in LOCALES
        ], return_exceptions=True)

        for loc, tr in zip(LOCALES, translations):
            if isinstance(tr, dict) and tr.get("title"):
                db.add(ArticleTranslation(
                    article_id=article.id,
                    locale=loc,
                    title=tr.get("title", title),
                    excerpt=tr.get("excerpt", excerpt),
                    body=tr.get("body", body),  # full translated body from Google Translate
                    status="done",
                ))
        await db.commit()
        log.info("Translations saved for %d locales", len(LOCALES))
    except Exception as e:
        log.warning("Translation step failed for '%s': %s", slug, e)

    # Step 5: notify search engines
    if auto_publish:
        asyncio.create_task(notify_article_published(slug))

    return slug
