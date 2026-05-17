"""Public articles API — SEO medical content.

Public endpoints (no auth required):
  GET /articles                   — paginated list
  GET /articles/{slug}            — single article
  GET /articles/category/{cat}    — articles by category
  GET /articles/sitemap-data      — all published slugs for sitemap generation
  GET /articles/categories        — categories with article counts

Teacher endpoints (require role=teacher|admin):
  GET  /articles/my               — list own articles (all statuses)
  POST /articles/my               — create draft article
  GET  /articles/my/{id}          — get own article (any status)
  PATCH /articles/my/{id}         — update own draft
  POST   /articles/my/{id}/submit   — submit draft for admin review
  POST   /articles/my/{id}/withdraw — withdraw from review back to draft
  DELETE /articles/my/{id}          — delete own draft or rejected article
  POST   /articles/my/{id}/upload-image — upload image, returns URL

Admin endpoints (require role=admin):
  GET  /articles/admin/list       — all articles with filters
  GET  /articles/admin/pending    — articles pending review
  POST /articles/generate         — generate article via Claude
  POST /articles                  — create article manually
  PATCH /articles/{id}            — update any article
  PATCH /articles/{id}/publish    — publish / unpublish
  PATCH /articles/{id}/approve    — approve teacher article
  PATCH /articles/{id}/reject     — reject teacher article with note
  DELETE /articles/{id}           — delete article
"""
from __future__ import annotations

import logging
import mimetypes
import re as _re
import uuid as _uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

logger = logging.getLogger(__name__)

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select, desc, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin, require_author, require_teacher
from app.core.config import settings
from app.core.database import get_db
from app.models.models import Article, ArticleTranslation, AuthorCreditAccount, CreditTransaction, LLMPricing, Module, User

router = APIRouter(prefix="/articles", tags=["articles"])

_admin = Depends(require_admin())
_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/svg+xml", "image/webp", "image/gif"}


# ── Schemas ────────────────────────────────────────────────────────────────────

class ArticleCreateRequest(BaseModel):
    title: str
    slug: str
    excerpt: str
    body: List[Dict[str, Any]]
    category: str
    subcategory: Optional[str] = None
    keywords: Optional[List[str]] = None
    reading_time_minutes: int = 5
    schema_type: str = "MedicalWebPage"
    faq: Optional[List[Dict[str, str]]] = None
    sources: Optional[List[Dict[str, str]]] = None
    related_module_code: Optional[str] = None
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    auto_publish: bool = False
    # Authorship
    author_display_name: Optional[str] = None
    author_bio: Optional[str] = None


class ArticleGenerateRequest(BaseModel):
    topic: str
    category: str
    schema_type: str = "MedicalCondition"
    language: str = "en"
    auto_publish: bool = False
    model: str = "haiku"


class ArticleAIGenerateRequest(BaseModel):
    topic: str
    category: str
    model: str = "claude-haiku"  # 'ollama', 'claude-haiku', 'claude-sonnet'
    specialty: Optional[str] = None
    author_display_name: Optional[str] = None
    author_bio: Optional[str] = None


class ArticlePatch(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    excerpt: Optional[str] = None
    body: Optional[List[Dict[str, Any]]] = None
    category: Optional[str] = None
    subcategory: Optional[str] = None
    keywords: Optional[List[str]] = None
    reading_time_minutes: Optional[int] = None
    schema_type: Optional[str] = None
    faq: Optional[List[Dict[str, str]]] = None
    sources: Optional[List[Dict[str, str]]] = None
    related_module_code: Optional[str] = None
    og_title: Optional[str] = None
    og_description: Optional[str] = None
    author_display_name: Optional[str] = None
    author_bio: Optional[str] = None


# ── Public helpers ─────────────────────────────────────────────────────────────

def _author_info(article: Article) -> dict:
    """Resolve author display info."""
    if article.author_id is None:
        return {"name": "MedMind AI Editorial", "bio": None, "is_ai": True}
    display = article.author_display_name
    if not display and article.author:
        fn = article.author.first_name or ""
        ln = article.author.last_name or ""
        display = f"{fn} {ln}".strip() or article.author.email
    return {
        "name": display or "MedMind AI Editorial",
        "bio": article.author_bio,
        "is_ai": False,
    }


def _list_item(a: Article) -> dict:
    return {
        "id": str(a.id),
        "slug": a.slug,
        "title": a.title,
        "excerpt": a.excerpt,
        "category": a.category,
        "subcategory": a.subcategory,
        "keywords": a.keywords or [],
        "reading_time_minutes": a.reading_time_minutes,
        "schema_type": a.schema_type,
        "published_at": a.published_at.isoformat() if a.published_at else None,
        "author": _author_info(a),
    }


def _og_image_url(slug: str) -> str | None:
    """Return OG image URL if the file exists on disk."""
    from pathlib import Path as _Path
    p = _Path(f"/app/data/media/og/{slug}.jpg")
    if p.exists():
        return f"https://medmind.pro/media/og/{slug}.jpg"
    return None


def _detail(a: Article) -> dict:
    return {
        **_list_item(a),
        "body": a.body or [],
        "faq": a.faq or [],
        "sources": a.sources or [],
        "related_module_code": a.related_module_code,
        "og_title": a.og_title,
        "og_description": a.og_description,
        "og_image": _og_image_url(a.slug),
        "generated_by": a.generated_by,
        "review_status": a.review_status,
        "review_note": a.review_note,
        # Verification
        "verification_status": getattr(a, "verification_status", "unverified"),
        "verified_sources": getattr(a, "verified_sources", None) or [],
        "last_verified_at": getattr(a, "last_verified_at", None).isoformat() if getattr(a, "last_verified_at", None) else None,
    }


async def _get_article_or_404(article_id: UUID, db: AsyncSession) -> Article:
    a = (await db.execute(select(Article).where(Article.id == article_id))).scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Article not found")
    return a


# ── Public endpoints ───────────────────────────────────────────────────────────

@router.get("")
async def list_articles(
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    locale: Optional[str] = Query(None, description="Return translated titles/excerpts: ru|ar|tr|de|fr|es"),
    db: AsyncSession = Depends(get_db),
):
    q = select(Article).where(Article.is_published == True, Article.review_status == "published")
    if category:
        q = q.where(Article.category == category)
    if search:
        from sqlalchemy import or_
        like = f"%{search.lower()}%"
        q = q.where(or_(Article.title.ilike(like), Article.excerpt.ilike(like)))

    count_q = select(func.count(Article.id)).where(Article.is_published == True, Article.review_status == "published")
    if category:
        count_q = count_q.where(Article.category == category)
    total = (await db.execute(count_q)).scalar() or 0

    q = q.order_by(desc(Article.published_at)).offset((page - 1) * limit).limit(limit)
    rows = (await db.execute(q)).scalars().all()

    items = [_list_item(a) for a in rows]

    # Overlay translated title/excerpt when locale requested and translation available
    if locale and locale != "en" and rows:
        article_ids = [a.id for a in rows]
        tr_rows = (await db.execute(
            select(ArticleTranslation)
            .where(
                ArticleTranslation.article_id.in_(article_ids),
                ArticleTranslation.locale == locale,
                ArticleTranslation.status == "done",
            )
        )).scalars().all()
        tr_map = {str(tr.article_id): tr for tr in tr_rows}
        for item in items:
            tr = tr_map.get(item["id"])
            if tr:
                item["title"] = tr.title
                item["excerpt"] = tr.excerpt

    return {"total": total, "page": page, "limit": limit, "articles": items}


@router.get("/sitemap-data")
async def sitemap_data(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Article.id, Article.slug, Article.updated_at, Article.category)
        .where(Article.is_published == True, Article.review_status == "published")
        .order_by(desc(Article.published_at))
    )).all()

    # Fetch completed translation locales for all articles in one query
    article_ids = [r.id for r in rows]
    trans_rows = (await db.execute(
        select(ArticleTranslation.article_id, ArticleTranslation.locale)
        .where(ArticleTranslation.article_id.in_(article_ids), ArticleTranslation.status == "done")
    )).all() if article_ids else []

    # Group locales by article_id
    locales_by_id: Dict[str, List[str]] = {}
    for tr in trans_rows:
        locales_by_id.setdefault(str(tr.article_id), []).append(tr.locale)

    return [
        {
            "slug": r.slug,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            "category": r.category,
            "locales": locales_by_id.get(str(r.id), []),
        }
        for r in rows
    ]


@router.get("/categories")
async def list_categories(db: AsyncSession = Depends(get_db)):
    rows = await db.execute(
        select(Article.category, func.count(Article.id).label("count"))
        .where(Article.is_published == True, Article.review_status == "published")
        .group_by(Article.category)
        .order_by(desc("count"))
    )
    return [{"category": r.category, "count": r.count} for r in rows.all()]


@router.get("/link-map")
async def article_link_map(db: AsyncSession = Depends(get_db)):
    """Return a flat list of {term, slug} for all published articles.

    Used by the frontend to auto-link medical terms in article body text.
    Includes article titles (primary) and individual keywords (secondary).
    Sorted by term length descending so longer/more specific terms match first.
    Cached for 1 hour via ISR on the consuming page.
    """
    rows = (await db.execute(
        select(Article.slug, Article.title, Article.keywords)
        .where(Article.is_published == True, Article.review_status == "published")
    )).all()

    entries: List[Dict[str, str]] = []
    seen_terms: set = set()

    for r in rows:
        # Title → primary link
        term = r.title.strip()
        if term and term.lower() not in seen_terms:
            entries.append({"term": term, "slug": r.slug})
            seen_terms.add(term.lower())
        # Keywords → secondary links (only if not already mapped)
        for kw in (r.keywords or []):
            kw = kw.strip()
            if len(kw) >= 4 and kw.lower() not in seen_terms:
                entries.append({"term": kw, "slug": r.slug})
                seen_terms.add(kw.lower())

    # Sort longest terms first to prevent partial-match shadowing
    entries.sort(key=lambda e: len(e["term"]), reverse=True)
    return entries


@router.get("/module-by-code/{code}")
async def module_by_code(code: str, db: AsyncSession = Depends(get_db)):
    """Public endpoint: resolve a module code to its id + title.

    Used by article pages to build a direct /modules/{id} link instead of the
    generic /register CTA, improving internal navigation for logged-in users.
    Returns 404 if the module does not exist or is not published.
    """
    mod = (await db.execute(
        select(Module.id, Module.title)
        .where(Module.code == code, Module.is_published == True)
    )).first()
    if not mod:
        raise HTTPException(status_code=404, detail="Module not found")
    return {"id": str(mod.id), "title": mod.title, "code": code}


@router.get("/category/{category}")
async def articles_by_category(
    category: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    locale: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    q = select(Article).where(Article.is_published == True, Article.review_status == "published", Article.category == category)
    total = (await db.execute(
        select(func.count(Article.id)).where(Article.is_published == True, Article.review_status == "published", Article.category == category)
    )).scalar() or 0
    q = q.order_by(desc(Article.published_at)).offset((page - 1) * limit).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    items = [_list_item(a) for a in rows]

    if locale and locale != "en" and rows:
        article_ids = [a.id for a in rows]
        tr_rows = (await db.execute(
            select(ArticleTranslation)
            .where(
                ArticleTranslation.article_id.in_(article_ids),
                ArticleTranslation.locale == locale,
                ArticleTranslation.status == "done",
            )
        )).scalars().all()
        tr_map = {str(tr.article_id): tr for tr in tr_rows}
        for item in items:
            tr = tr_map.get(item["id"])
            if tr:
                item["title"] = tr.title
                item["excerpt"] = tr.excerpt

    return {"category": category, "total": total, "page": page, "limit": limit, "articles": items}


@router.get("/{slug}/related")
async def article_related(
    slug: str,
    limit: int = Query(4, ge=1, le=8),
    locale: Optional[str] = Query(None, description="Return translated titles/excerpts"),
    db: AsyncSession = Depends(get_db),
):
    """Return related published articles from the same category (excluding self)."""
    article = (await db.execute(
        select(Article).where(Article.slug == slug, Article.is_published == True, Article.review_status == "published")
    )).scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    rows = (await db.execute(
        select(Article)
        .where(
            Article.is_published == True,
            Article.review_status == "published",
            Article.category == article.category,
            Article.id != article.id,
        )
        .order_by(desc(Article.published_at))
        .limit(limit)
    )).scalars().all()

    items = [_list_item(a) for a in rows]

    # Overlay translated title/excerpt when locale requested
    if locale and locale != "en" and rows:
        article_ids = [a.id for a in rows]
        tr_rows = (await db.execute(
            select(ArticleTranslation)
            .where(
                ArticleTranslation.article_id.in_(article_ids),
                ArticleTranslation.locale == locale,
                ArticleTranslation.status == "done",
            )
        )).scalars().all()
        tr_map = {str(tr.article_id): tr for tr in tr_rows}
        for item in items:
            tr = tr_map.get(item["id"])
            if tr:
                item["title"] = tr.title
                item["excerpt"] = tr.excerpt

    return items


@router.get("/{slug}/nav")
async def article_nav(
    slug: str,
    locale: Optional[str] = Query(None, description="Return translated titles"),
    db: AsyncSession = Depends(get_db),
):
    """Return prev/next article in the same category (by published_at)."""
    article = (await db.execute(
        select(Article).where(Article.slug == slug, Article.is_published == True, Article.review_status == "published")
    )).scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    pub = article.published_at

    prev_art = (await db.execute(
        select(Article)
        .where(
            Article.is_published == True,
            Article.review_status == "published",
            Article.category == article.category,
            Article.id != article.id,
            Article.published_at < pub,
        )
        .order_by(desc(Article.published_at))
        .limit(1)
    )).scalar_one_or_none()

    next_art = (await db.execute(
        select(Article)
        .where(
            Article.is_published == True,
            Article.review_status == "published",
            Article.category == article.category,
            Article.id != article.id,
            Article.published_at > pub,
        )
        .order_by(Article.published_at)
        .limit(1)
    )).scalar_one_or_none()

    result = {
        "prev": {"slug": prev_art.slug, "title": prev_art.title} if prev_art else None,
        "next": {"slug": next_art.slug, "title": next_art.title} if next_art else None,
    }

    # Overlay translated titles
    if locale and locale != "en":
        for key, art in [("prev", prev_art), ("next", next_art)]:
            if art:
                tr = (await db.execute(
                    select(ArticleTranslation)
                    .where(
                        ArticleTranslation.article_id == art.id,
                        ArticleTranslation.locale == locale,
                        ArticleTranslation.status == "done",
                    )
                )).scalar_one_or_none()
                if tr:
                    result[key]["title"] = tr.title

    return result


@router.get("/{slug}/available-locales")
async def article_available_locales(slug: str, db: AsyncSession = Depends(get_db)):
    """Return list of locales with completed translations for this article."""
    article = (await db.execute(
        select(Article).where(Article.slug == slug, Article.is_published == True, Article.review_status == "published")
    )).scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    rows = (await db.execute(
        select(ArticleTranslation.locale)
        .where(ArticleTranslation.article_id == article.id, ArticleTranslation.status == "done")
    )).scalars().all()
    return {"slug": slug, "locales": list(rows)}


@router.get("/{slug}/quiz")
async def article_quiz(slug: str, db: AsyncSession = Depends(get_db)):
    """
    Generate 5 USMLE-style MCQ questions for an article.
    Results are cached in Redis for 24 h so Claude is called at most once per article.
    No authentication required — public endpoint.
    """
    from app.core.cache import get_cached, set_cached
    import json as _json

    cache_key = f"article_quiz:{slug}"
    cached = await get_cached(cache_key)
    if cached:
        return cached

    article = (await db.execute(
        select(Article).where(Article.slug == slug, Article.is_published == True)
    )).scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Build plain-text summary from body blocks (limit for token budget)
    blocks = article.body or []
    lines: list[str] = [f"Title: {article.title}", f"Summary: {article.excerpt}"]
    for block in blocks:
        btype = block.get("type", "")
        if btype == "h2":
            lines.append(f"\n## {block.get('content','')}")
        elif btype == "p":
            lines.append(block.get("content", "")[:600])
        elif btype == "ul":
            for item in (block.get("items") or [])[:4]:
                lines.append(f"- {item}")
        if len("\n".join(lines)) > 4000:
            break
    article_text = "\n".join(lines)[:4500]

    prompt = f"""You are a medical educator writing USMLE-style multiple-choice questions.

Based on the article below, generate exactly 5 high-quality MCQ questions.
Rules:
- Each question must have 4 options labeled A, B, C, D
- Exactly one option is correct
- Questions should test clinical reasoning, not just memorization
- Mix difficulty: 2 easy, 2 medium, 1 hard
- Explanation must be 1-2 sentences citing the key concept from the article

Respond with ONLY valid JSON, no other text:
{{
  "questions": [
    {{
      "question": "Clinical scenario or direct question...",
      "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
      "correct": "A",
      "explanation": "A is correct because...",
      "difficulty": "easy"
    }}
  ]
}}

ARTICLE:
{article_text}"""

    questions = None

    # Try Claude first
    try:
        import anthropic as _anthropic
        from app.core.config import settings as _s
        if _s.ANTHROPIC_API_KEY:
            client = _anthropic.AsyncAnthropic(api_key=_s.ANTHROPIC_API_KEY)
            msg = await client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = _json.loads(raw)
            questions = data.get("questions", [])[:5]
    except Exception as e:
        if "credit" in str(e).lower() or "balance" in str(e).lower() or "402" in str(e):
            logger.info("Claude API balance depleted, falling back to Ollama for quiz: %s", slug)
        else:
            logger.warning("Claude quiz failed for %s: %s", slug, e)

    # Ollama fallback — use 1.7b for faster response (quiz needs ~500 tokens, not 2000)
    if not questions:
        try:
            import httpx as _httpx
            ollama_resp = await _httpx.AsyncClient(timeout=180).post(
                "http://172.20.0.1:11434/api/chat",
                json={
                    "model":   "qwen3:1.7b",
                    "messages": [{"role": "user", "content": prompt}],
                    "stream":  False,
                    "options": {"temperature": 0.3, "num_predict": 1500, "num_ctx": 4096},
                    "think":   False,
                },
            )
            raw = ollama_resp.json().get("message", {}).get("content", "").strip()
            raw = _re.sub(r"^```(?:json)?\s*", "", raw)
            raw = _re.sub(r"\s*```$", "", raw)
            m = _re.search(r"\{.*\}", raw, _re.DOTALL)
            if m:
                data = _json.loads(m.group())
                questions = data.get("questions", [])[:5]
        except Exception as e2:
            logger.error("Ollama quiz fallback failed for %s: %s", slug, e2)

    if not questions:
        raise HTTPException(status_code=503, detail="Quiz generation temporarily unavailable")

    result = {"slug": slug, "title": article.title, "questions": questions}
    await set_cached(cache_key, result, ttl=86400)  # cache 24 h
    return result


# NOTE: /my and /admin routes MUST be defined before /{slug} so FastAPI
# matches them before the wildcard slug pattern (first-match wins).

@router.get("/my")
async def my_articles_early(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_author),
):
    """List articles authored by the current teacher (early registration before /{slug})."""
    rows = (await db.execute(
        select(Article).where(Article.author_id == user.id)
        .order_by(desc(Article.created_at))
    )).scalars().all()
    return [_detail(a) | {"is_published": a.is_published} for a in rows]


@router.get("/my/stats")
async def my_article_stats_early(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_author),
):
    """Author stats (early registration before /{slug})."""
    rows = (await db.execute(
        select(Article).where(Article.author_id == user.id)
        .order_by(desc(Article.created_at))
    )).scalars().all()
    total_views = sum(a.view_count for a in rows)
    published = [a for a in rows if a.is_published and a.review_status == "published"]
    _RPM_LOCAL = 2.00
    article_stats = []
    for a in rows:
        rev = (a.view_count / 1000) * _RPM_LOCAL * (a.revenue_share_pct / 100)
        article_stats.append({
            "id": str(a.id), "slug": a.slug, "title": a.title,
            "views": a.view_count, "revenue_share_pct": a.revenue_share_pct,
            "estimated_revenue_usd": round(rev, 2),
            "review_status": a.review_status, "is_published": a.is_published,
            "published_at": a.published_at.isoformat() if a.published_at else None,
        })
    return {
        "total_views": total_views, "total_articles": len(rows),
        "published_articles": len(published),
        "estimated_revenue_usd": round(sum(s["estimated_revenue_usd"] for s in article_stats), 2),
        "revenue_per_1000_views": _RPM_LOCAL, "revenue_share_pct": 40,
        "articles": article_stats,
    }


@router.get("/admin/list")
async def admin_list_articles_early(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    published: Optional[bool] = Query(None),
    category: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    """Admin: list articles (early registration before /{slug})."""
    q = select(Article)
    if published is not None:
        q = q.where(Article.is_published == published)
    if category:
        q = q.where(Article.category == category)
    if review_status:
        q = q.where(Article.review_status == review_status)
    total = (await db.execute(select(func.count(Article.id)))).scalar() or 0
    q = q.order_by(desc(Article.created_at)).offset((page - 1) * limit).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return {"total": total, "page": page, "articles": [_detail(a) | {"is_published": a.is_published} for a in rows]}


@router.get("/admin/pending")
async def admin_pending_articles_early(
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    """Admin: articles awaiting review (early registration before /{slug})."""
    rows = (await db.execute(
        select(Article).where(Article.review_status == "pending_review")
        .order_by(Article.submitted_at)
    )).scalars().all()
    return [_detail(a) | {"is_published": a.is_published, "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None} for a in rows]


@router.get("/{slug}")
async def get_article(
    slug: str,
    locale: Optional[str] = Query(None, description="Return translated version: ru|ar|tr|de|fr|es"),
    db: AsyncSession = Depends(get_db),
):
    article = (await db.execute(
        select(Article).where(Article.slug == slug, Article.is_published == True, Article.review_status == "published")
    )).scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    detail = _detail(article)

    # Serve translated version if requested and available
    if locale and locale != "en":
        tr = (await db.execute(
            select(ArticleTranslation).where(
                ArticleTranslation.article_id == article.id,
                ArticleTranslation.locale == locale,
                ArticleTranslation.status == "done",
            )
        )).scalar_one_or_none()
        if tr:
            detail = {
                **detail,
                "title": tr.title,
                "excerpt": tr.excerpt,
                "body": tr.body or [],
                "faq": tr.faq or detail["faq"],
                "locale": locale,
                "is_translated": True,
            }

    return detail


# ── Author Program endpoints ───────────────────────────────────────────────────

@router.post("/{slug}/view", status_code=204)
async def track_article_view(slug: str, db: AsyncSession = Depends(get_db)):
    """Public — increment view_count atomically. Returns 204 No Content."""
    await db.execute(
        update(Article).where(Article.slug == slug).values(view_count=Article.view_count + 1)
    )
    await db.commit()
    return Response(status_code=204)


_RPM = 2.00  # revenue per 1,000 views in USD


@router.get("/my/stats")
async def my_article_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_author),
):
    """Author stats: views + estimated earnings per article."""
    rows = (await db.execute(
        select(Article).where(Article.author_id == user.id)
        .order_by(desc(Article.created_at))
    )).scalars().all()

    total_views = sum(a.view_count for a in rows)
    published = [a for a in rows if a.is_published and a.review_status == "published"]

    article_stats = []
    for a in rows:
        rev = (a.view_count / 1000) * _RPM * (a.revenue_share_pct / 100)
        article_stats.append({
            "id": str(a.id),
            "slug": a.slug,
            "title": a.title,
            "views": a.view_count,
            "revenue_share_pct": a.revenue_share_pct,
            "estimated_revenue_usd": round(rev, 2),
            "review_status": a.review_status,
            "is_published": a.is_published,
            "published_at": a.published_at.isoformat() if a.published_at else None,
        })

    total_rev = sum(s["estimated_revenue_usd"] for s in article_stats)

    return {
        "total_views": total_views,
        "total_articles": len(rows),
        "published_articles": len(published),
        "estimated_revenue_usd": round(total_rev, 2),
        "revenue_per_1000_views": _RPM,
        "revenue_share_pct": 40,
        "articles": article_stats,
    }


@router.post("/my/generate-ai", status_code=201)
async def generate_article_ai(
    req: ArticleAIGenerateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_author),
):
    """Generate an article using AI — costs credits based on model selected.

    Returns immediately with a placeholder draft (generated_by='ai-generating').
    Background task fills in the real content — poll /my/{id} until
    generated_by changes to 'ai-{model}' (done) or 'ai-failed' (error).
    """
    import asyncio
    import re as _re

    # Check pricing
    pricing = await db.get(LLMPricing, req.model)
    if not pricing or not pricing.is_active:
        raise HTTPException(status_code=400, detail=f"Model '{req.model}' is not available")

    # Check / create credit account
    acc = await db.get(AuthorCreditAccount, user.id)
    if not acc:
        acc = AuthorCreditAccount(user_id=user.id, balance=10, total_purchased=0, total_spent=0)
        db.add(acc)
        db.add(CreditTransaction(
            user_id=user.id, type="bonus", credits=10,
            description="Welcome bonus — 10 free credits",
        ))
        await db.flush()

    # Ollama is free (0 credits) — always allowed
    if pricing.credits_per_article > 0 and acc.balance < pricing.credits_per_article:
        raise HTTPException(
            status_code=402,
            detail={
                "message": "Insufficient credits",
                "required": pricing.credits_per_article,
                "balance": acc.balance,
                "free_alternative": "Use Ollama for free — select 'Ollama' in the model picker",
                "buy_url": "/teacher/credits",
            },
        )

    # Deduct credits immediately
    acc.balance -= pricing.credits_per_article
    acc.total_spent += pricing.credits_per_article

    # Create placeholder article — returned instantly
    base_slug = _re.sub(r"[^a-z0-9]+", "-", req.topic.lower()).strip("-")[:60]
    slug = f"{base_slug}-{_uuid.uuid4().hex[:6]}"
    display = req.author_display_name
    if not display:
        fn = user.first_name or ""
        ln = user.last_name or ""
        display = f"{fn} {ln}".strip() or user.email

    article = Article(
        slug=slug,
        title=f"Generating: {req.topic[:80]}…",
        excerpt="AI is writing this article — check back in a few minutes.",
        body=[],
        category=req.category,
        author_id=user.id,
        author_display_name=display,
        author_bio=req.author_bio,
        is_published=False,
        review_status="draft",
        generated_by="ai-generating",
        revenue_share_pct=40,
    )
    db.add(article)

    db.add(CreditTransaction(
        user_id=user.id,
        type="spend",
        credits=pricing.credits_per_article,
        usd_amount=float(pricing.credits_per_article) * 0.01,
        actual_cost_usd=float(pricing.actual_cost_usd),
        model=req.model,
        description=f"AI generation: {req.topic[:60]}",
    ))

    await db.commit()
    await db.refresh(article)

    # Capture IDs for background task
    article_id = article.id
    user_id = user.id
    topic, category, model, specialty = req.topic, req.category, req.model, req.specialty
    credits_spent = pricing.credits_per_article

    async def _generate_background() -> None:
        from app.core.database import AsyncSessionLocal
        from app.services.article_generator import generate_article_content
        async with AsyncSessionLocal() as bg_db:
            art = await bg_db.get(Article, article_id)
            if not art:
                return
            try:
                content = await generate_article_content(
                    topic=topic, category=category, model=model, specialty=specialty,
                )
                art.title = content.get("title", topic)
                art.excerpt = content.get("excerpt", content.get("og_description", ""))
                art.body = content.get("body", [])
                art.keywords = content.get("keywords", [])
                art.reading_time_minutes = content.get("reading_time_minutes", 8)
                art.faq = content.get("faq", [])
                art.sources = content.get("sources", [])
                art.og_title = content.get("og_title")
                art.og_description = content.get("og_description")
                art.generated_by = f"ai-{model}"
                art.updated_at = datetime.utcnow()
                await bg_db.commit()
            except Exception as exc:
                logger.error(
                    "AI article generation failed [article=%s topic=%r model=%s]: %s: %s",
                    article_id, topic, model, type(exc).__name__, exc,
                )
                # Refund on failure
                try:
                    bg_acc = await bg_db.get(AuthorCreditAccount, user_id)
                    if bg_acc:
                        bg_acc.balance += credits_spent
                        bg_acc.total_spent -= credits_spent
                    art.title = f"Generation failed: {topic[:60]}"
                    art.excerpt = f"Credits refunded. Error: {type(exc).__name__}: {str(exc)[:200]}"
                    art.generated_by = "ai-failed"
                    art.updated_at = datetime.utcnow()
                    await bg_db.commit()
                except Exception as inner:
                    logger.error("Failed to persist generation failure state: %s", inner)

    asyncio.create_task(_generate_background())

    return {
        **_detail(article),
        "is_published": False,
        "generating": True,
        "message": f"Article generation started. Using {pricing.credits_per_article} credits. Refresh in 1-3 minutes.",
    }


# ── Teacher / Author endpoints ─────────────────────────────────────────────────

@router.get("/my")
async def my_articles(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_author),
):
    """List articles authored by the current teacher."""
    rows = (await db.execute(
        select(Article).where(Article.author_id == user.id)
        .order_by(desc(Article.created_at))
    )).scalars().all()
    return [_detail(a) | {"is_published": a.is_published} for a in rows]


@router.post("/my")
async def create_my_article(
    req: ArticleCreateRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_author),
):
    """Teacher creates a draft article."""
    existing = (await db.execute(select(Article).where(Article.slug == req.slug))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail=f"Slug '{req.slug}' already exists")

    display = req.author_display_name
    if not display:
        fn = user.first_name or ""
        ln = user.last_name or ""
        display = f"{fn} {ln}".strip() or user.email

    article = Article(
        **req.model_dump(exclude={"auto_publish", "author_display_name", "author_bio"}),
        author_id=user.id,
        author_display_name=display,
        author_bio=req.author_bio,
        is_published=False,
        review_status="draft",
        generated_by="teacher",
    )
    db.add(article)
    await db.commit()
    await db.refresh(article)
    return _detail(article) | {"is_published": article.is_published}


@router.get("/my/{article_id}")
async def get_my_article(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_author),
):
    article = await _get_article_or_404(article_id, db)
    if str(article.author_id) != str(user.id) and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your article")
    return _detail(article) | {"is_published": article.is_published}


@router.patch("/my/{article_id}")
async def update_my_article(
    article_id: UUID,
    data: ArticlePatch,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_author),
):
    article = await _get_article_or_404(article_id, db)
    if str(article.author_id) != str(user.id) and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your article")
    if article.review_status == "pending_review":
        raise HTTPException(status_code=400, detail="Cannot edit while pending review. Withdraw first.")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(article, field, value)
    # If editing a rejected article, reset to draft
    if article.review_status == "rejected":
        article.review_status = "draft"
        article.review_note = None

    await db.commit()
    await db.refresh(article)
    return _detail(article) | {"is_published": article.is_published}


@router.post("/my/{article_id}/submit")
async def submit_for_review(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_author),
):
    """Submit a draft article for admin review."""
    article = await _get_article_or_404(article_id, db)
    if str(article.author_id) != str(user.id) and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your article")
    if article.review_status not in ("draft", "rejected"):
        raise HTTPException(status_code=400, detail=f"Cannot submit: current status is '{article.review_status}'")
    if article.generated_by == "ai-generating":
        raise HTTPException(status_code=400, detail="Article is still being generated. Wait for generation to complete.")
    if article.generated_by == "ai-failed":
        raise HTTPException(status_code=400, detail="Article generation failed. Delete it and try again.")
    if not article.body:
        raise HTTPException(status_code=400, detail="Article has no content. Add body sections before submitting.")

    article.review_status = "pending_review"
    article.submitted_at = datetime.utcnow()
    article.review_note = None
    await db.commit()
    return {"id": str(article.id), "review_status": article.review_status}


@router.post("/my/{article_id}/withdraw")
async def withdraw_review(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_author),
):
    """Withdraw article from review back to draft."""
    article = await _get_article_or_404(article_id, db)
    if str(article.author_id) != str(user.id) and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your article")
    if article.review_status != "pending_review":
        raise HTTPException(status_code=400, detail="Article is not pending review")
    article.review_status = "draft"
    await db.commit()
    return {"id": str(article.id), "review_status": article.review_status}


@router.delete("/my/{article_id}")
async def delete_my_article(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_author),
):
    """Teacher deletes own draft or rejected article."""
    article = await _get_article_or_404(article_id, db)
    if str(article.author_id) != str(user.id) and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your article")
    if article.review_status not in ("draft", "rejected"):
        raise HTTPException(status_code=400, detail=f"Cannot delete: status is '{article.review_status}'. Withdraw first if pending review.")
    await db.delete(article)
    await db.commit()
    return {"deleted": str(article_id)}


@router.post("/my/{article_id}/upload-image")
async def upload_article_image(
    article_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_author),
):
    """Upload an image for use in an article body block. Returns the public URL."""
    article = await _get_article_or_404(article_id, db)
    if str(article.author_id) != str(user.id) and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your article")

    content_type = file.content_type or ""
    if content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(400, f"File type '{content_type}' not allowed. Accepted: JPEG, PNG, SVG, WebP, GIF.")

    max_bytes = settings.MEDIA_MAX_IMAGE_MB * 1024 * 1024
    data = await file.read()
    if len(data) > max_bytes:
        raise HTTPException(400, f"File exceeds {settings.MEDIA_MAX_IMAGE_MB} MB limit.")

    ext = mimetypes.guess_extension(content_type) or ".bin"
    if ext == ".jpe":
        ext = ".jpg"
    filename = f"{_uuid.uuid4().hex}{ext}"

    dest_dir = Path(settings.MEDIA_ROOT) / "articles" / str(article_id)
    dest_dir.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(dest_dir / filename, "wb") as f:
        await f.write(data)

    url = f"{settings.MEDIA_URL}/articles/{article_id}/{filename}"
    return {"url": url, "filename": filename, "size": len(data), "content_type": content_type}


# ── Admin endpoints ────────────────────────────────────────────────────────────

@router.get("/admin/list")
async def admin_list_articles(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    published: Optional[bool] = Query(None),
    category: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    q = select(Article)
    if published is not None:
        q = q.where(Article.is_published == published)
    if category:
        q = q.where(Article.category == category)
    if review_status:
        q = q.where(Article.review_status == review_status)
    total = (await db.execute(select(func.count(Article.id)))).scalar() or 0
    q = q.order_by(desc(Article.created_at)).offset((page - 1) * limit).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return {
        "total": total,
        "page": page,
        "articles": [_detail(a) | {"is_published": a.is_published} for a in rows],
    }


@router.get("/admin/pending")
async def admin_pending_articles(
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    """Articles awaiting admin review."""
    rows = (await db.execute(
        select(Article).where(Article.review_status == "pending_review")
        .order_by(Article.submitted_at)
    )).scalars().all()
    return [_detail(a) | {"is_published": a.is_published, "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None} for a in rows]


@router.get("/admin/{article_id}")
async def admin_get_article(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    """Admin: fetch any article by ID regardless of published/review status."""
    article = await _get_article_or_404(article_id, db)
    return _detail(article) | {"is_published": article.is_published}


@router.patch("/{article_id}/approve")
async def approve_article(
    article_id: UUID,
    auto_publish: bool = True,
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    """Approve a pending teacher article (optionally publish immediately)."""
    article = await _get_article_or_404(article_id, db)
    article.review_status = "published"
    article.review_note = None
    if auto_publish:
        article.is_published = True
        article.published_at = article.published_at or datetime.utcnow()
    await db.commit()

    # Trigger background translation into all supported locales
    from app.services.translation_service import schedule_article_translations
    await schedule_article_translations(article.id, db)

    # Notify search engines and AI crawlers
    if auto_publish:
        import asyncio
        from app.services.indexing_service import notify_article_published
        asyncio.create_task(notify_article_published(article.slug))

    return {"id": str(article.id), "review_status": article.review_status, "is_published": article.is_published}


@router.patch("/{article_id}/reject")
async def reject_article(
    article_id: UUID,
    note: str = "",
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    """Reject a pending article and return it to the teacher with a note."""
    article = await _get_article_or_404(article_id, db)
    article.review_status = "rejected"
    article.review_note = note
    article.is_published = False
    await db.commit()
    return {"id": str(article.id), "review_status": article.review_status, "review_note": article.review_note}


@router.post("/{article_id}/verify")
async def verify_article_pubmed(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    """Trigger PubMed verification for an article (admin only).
    Sets verification_status = 'ai_verified' if ≥2 relevant papers found.
    """
    from app.services.pubmed_service import verify_article_orm
    status = await verify_article_orm(article_id, db)
    if status == "not_found":
        raise HTTPException(status_code=404, detail="Article not found")
    article = await _get_article_or_404(article_id, db)
    return {
        "id": str(article_id),
        "verification_status": status,
        "verified_sources": article.verified_sources or [],
        "last_verified_at": article.last_verified_at.isoformat() if article.last_verified_at else None,
    }


@router.patch("/{article_id}/expert-verify")
async def expert_verify_article(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = _admin,
):
    """Mark article as expert-verified by admin physician (manual review).
    Highest trust level — shown with green badge on article page.
    """
    article = await _get_article_or_404(article_id, db)
    article.verification_status = "expert_verified"
    article.last_verified_at = datetime.utcnow()
    await db.commit()
    return {"id": str(article_id), "verification_status": "expert_verified"}


@router.post("/generate")
async def generate_article(
    req: ArticleGenerateRequest,
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    """Generate a medical article via Claude AI and save as draft (or publish)."""
    from app.services.article_generator import generate_medical_article

    result = await generate_medical_article(
        topic=req.topic, category=req.category,
        schema_type=req.schema_type, language=req.language, model=req.model,
    )

    existing = (await db.execute(select(Article).where(Article.slug == result["slug"]))).scalar_one_or_none()
    if existing:
        result["slug"] = result["slug"] + f"-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    article = Article(
        slug=result["slug"], title=result["title"], excerpt=result["excerpt"],
        body=result["body"], category=req.category, subcategory=result.get("subcategory"),
        keywords=result.get("keywords", []), reading_time_minutes=result.get("reading_time_minutes", 5),
        schema_type=req.schema_type, faq=result.get("faq"), sources=result.get("sources"),
        related_module_code=result.get("related_module_code"),
        og_title=result.get("og_title"), og_description=result.get("og_description"),
        is_published=req.auto_publish,
        published_at=datetime.utcnow() if req.auto_publish else None,
        generated_by=f"claude-{req.model}",
        review_status="published",  # AI articles skip review
    )
    db.add(article)
    await db.commit()
    await db.refresh(article)

    if req.auto_publish:
        from app.services.translation_service import schedule_article_translations
        await schedule_article_translations(article.id, db)
        import asyncio
        from app.services.indexing_service import notify_article_published
        asyncio.create_task(notify_article_published(article.slug))

    return _detail(article) | {"is_published": article.is_published}


@router.post("")
async def create_article(
    req: ArticleCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = _admin,
):
    existing = (await db.execute(select(Article).where(Article.slug == req.slug))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail=f"Slug '{req.slug}' already exists")

    article = Article(
        **req.model_dump(exclude={"auto_publish"}),
        is_published=req.auto_publish,
        published_at=datetime.utcnow() if req.auto_publish else None,
        generated_by="manual",
        review_status="published",
    )
    db.add(article)
    await db.commit()
    await db.refresh(article)

    if req.auto_publish:
        from app.services.translation_service import schedule_article_translations
        await schedule_article_translations(article.id, db)
        import asyncio
        from app.services.indexing_service import notify_article_published
        asyncio.create_task(notify_article_published(article.slug))

    return _detail(article) | {"is_published": article.is_published}


@router.patch("/{article_id}")
async def update_article(
    article_id: UUID,
    data: ArticlePatch,
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    article = await _get_article_or_404(article_id, db)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(article, field, value)
    await db.commit()
    await db.refresh(article)
    return _detail(article) | {"is_published": article.is_published}


@router.patch("/{article_id}/publish")
async def toggle_publish(
    article_id: UUID,
    publish: bool = True,
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    article = await _get_article_or_404(article_id, db)
    article.is_published = publish
    article.published_at = datetime.utcnow() if publish and not article.published_at else article.published_at
    await db.commit()

    if publish:
        from app.services.translation_service import schedule_article_translations
        await schedule_article_translations(article.id, db)
        # Notify search engines and AI crawlers asynchronously
        import asyncio
        from app.services.indexing_service import notify_article_published
        asyncio.create_task(notify_article_published(article.slug))

    return {"id": str(article.id), "slug": article.slug, "is_published": article.is_published}


@router.delete("/{article_id}")
async def delete_article(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    article = await _get_article_or_404(article_id, db)
    await db.delete(article)
    await db.commit()
    return {"deleted": str(article_id)}
