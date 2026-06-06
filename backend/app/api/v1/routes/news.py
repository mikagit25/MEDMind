"""Medical news API.

Public:
  GET  /news                       — paginated list (published only)
  GET  /news/categories            — category counts
  GET  /news/sitemap-data          — slugs for sitemap
  GET  /news/{slug}                — single article
  GET  /news/{slug}/related-articles — articles same category

Teacher:
  GET  /news/my                    — own news (all statuses)
  POST /news/my                    — create draft
  PATCH /news/my/{id}              — update own draft
  POST  /news/my/{id}/submit       — submit for review
  POST  /news/my/{id}/withdraw     — withdraw to draft
  DELETE /news/my/{id}             — delete own draft/rejected
  POST  /news/generate-summary     — AI summarise from URL/abstract

Admin:
  GET  /news/admin/list            — all news with filters
  PATCH /news/admin/{id}/approve   — publish
  PATCH /news/admin/{id}/reject    — reject with note
  DELETE /news/admin/{id}          — hard delete
  POST  /news/admin/run-pipeline   — trigger auto-fetch
"""
import logging
import re
from datetime import datetime
from typing import Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, HttpUrl
from sqlalchemy import func, select, desc, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db, require_admin, require_teacher
from app.core.config import settings
from app.models.models import Article, ArticleTranslation, NewsArticle, User
from app.services.news_pipeline import run_news_pipeline, _slugify, _source_hash

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/news", tags=["news"])

SUPPORTED_LOCALES = ["en", "ru", "ar", "es", "de", "fr", "tr"]
_teacher = Depends(require_teacher)
_admin   = Depends(require_admin())

# News categories → MedMind article categories (may differ in naming/granularity)
_NEWS_TO_ARTICLE_CATS: dict[str, list[str]] = {
    "cardiology":         ["cardiology", "cardiology-advanced"],
    "oncology":           ["oncology", "hematology"],
    "neurology":          ["neurology"],
    "infectious-disease": ["infectious-diseases", "infectious-specific", "microbiology"],
    "endocrinology":      ["endocrinology"],
    "pulmonology":        ["pulmonology"],
    "nephrology":         ["nephrology"],
    "gastroenterology":   ["gastroenterology"],
    "psychiatry":         ["psychiatry", "mental-health"],
    "pediatrics":         ["pediatrics"],
    "surgery":            ["surgery", "surgery-procedures"],
    "obstetrics":         ["womens-health"],
    "general-medicine":   ["internal-medicine", "diseases", "clinical-syndromes"],
    "public-health":      ["public-health", "internal-medicine"],
}


# ── Schemas ───────────────────────────────────────────────────────────────────

class NewsListItem(BaseModel):
    id: str
    slug: str
    source_name: str
    source_url: str
    title: str
    summary_excerpt: str
    category: str
    review_status: str
    original_published_at: Optional[str] = None
    fetched_at: str
    author_display_name: Optional[str] = None


class NewsDetail(BaseModel):
    id: str
    slug: str
    source_name: str
    source_url: str
    source_doi: Optional[str] = None
    title: str
    summary: str
    category: str
    tags: Optional[list[str]] = None
    review_status: str
    original_published_at: Optional[str] = None
    fetched_at: str
    author_display_name: Optional[str] = None
    review_note: Optional[str] = None


class NewsCreate(BaseModel):
    source_url: str
    source_doi: Optional[str] = None
    source_name: str = "Teacher"
    title: str
    summary: str
    category: str
    tags: Optional[list[str]] = None
    original_published_at: Optional[str] = None


class NewsUpdate(BaseModel):
    source_url: Optional[str] = None
    title: Optional[str] = None
    summary: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[list[str]] = None
    source_name: Optional[str] = None
    original_published_at: Optional[str] = None


class GenerateSummaryRequest(BaseModel):
    source_url: str
    title: Optional[str] = None
    abstract: Optional[str] = None


class GenerateSummaryResponse(BaseModel):
    title: str
    summary: str
    category: str


class AdminRejectRequest(BaseModel):
    note: str


class NewsSitemapEntry(BaseModel):
    slug: str
    fetched_at: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


def _loc_title(news: NewsArticle, locale: str) -> str:
    if locale == "en":
        return news.title
    return (news.translations or {}).get(locale, {}).get("title") or news.title


def _loc_summary(news: NewsArticle, locale: str) -> str:
    if locale == "en":
        return news.summary
    return (news.translations or {}).get(locale, {}).get("summary") or news.summary


def _to_list_item(news: NewsArticle, locale: str) -> NewsListItem:
    summary = _loc_summary(news, locale)
    return NewsListItem(
        id=str(news.id),
        slug=news.slug,
        source_name=news.source_name,
        source_url=news.source_url,
        title=_loc_title(news, locale),
        summary_excerpt=summary[:280] + ("…" if len(summary) > 280 else ""),
        category=news.category,
        review_status=news.review_status,
        original_published_at=_fmt(news.original_published_at),
        fetched_at=_fmt(news.fetched_at) or "",
        author_display_name=news.author_display_name,
    )


def _to_detail(news: NewsArticle, locale: str) -> NewsDetail:
    return NewsDetail(
        id=str(news.id),
        slug=news.slug,
        source_name=news.source_name,
        source_url=news.source_url,
        source_doi=news.source_doi,
        title=_loc_title(news, locale),
        summary=_loc_summary(news, locale),
        category=news.category,
        tags=news.tags,
        review_status=news.review_status,
        original_published_at=_fmt(news.original_published_at),
        fetched_at=_fmt(news.fetched_at) or "",
        author_display_name=news.author_display_name,
        review_note=news.review_note,
    )


async def _make_unique_slug(base: str, db: AsyncSession) -> str:
    slug = base
    counter = 1
    while True:
        exists = await db.execute(select(NewsArticle.id).where(NewsArticle.slug == slug))
        if not exists.scalar_one_or_none():
            return slug
        slug = f"{base}-{counter}"
        counter += 1


# ── Public endpoints ──────────────────────────────────────────────────────────

@router.get("", response_model=list[NewsListItem])
async def list_news(
    locale: str = Query("en"),
    category: Optional[str] = Query(None),
    limit: int = Query(24, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    locale = locale if locale in SUPPORTED_LOCALES else "en"
    q = (
        select(NewsArticle)
        .where(NewsArticle.is_published == True, NewsArticle.review_status == "published")
    )
    if category:
        q = q.where(NewsArticle.category == category)
    q = q.order_by(desc(NewsArticle.fetched_at)).limit(limit).offset(offset)
    result = await db.execute(q)
    return [_to_list_item(n, locale) for n in result.scalars().all()]


@router.get("/categories")
async def list_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(NewsArticle.category, func.count(NewsArticle.id).label("count"))
        .where(NewsArticle.is_published == True, NewsArticle.review_status == "published")
        .group_by(NewsArticle.category)
        .order_by(desc("count"))
    )
    return [{"category": row.category, "count": row.count} for row in result]


@router.get("/sitemap-data", response_model=list[NewsSitemapEntry])
async def sitemap_data(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(NewsArticle.slug, NewsArticle.fetched_at)
        .where(NewsArticle.is_published == True, NewsArticle.review_status == "published")
        .order_by(desc(NewsArticle.fetched_at))
    )
    return [NewsSitemapEntry(slug=r.slug, fetched_at=_fmt(r.fetched_at) or "") for r in result]


@router.get("/{slug}/related-articles")
async def related_articles(slug: str, locale: str = Query("en"),
                            db: AsyncSession = Depends(get_db)):
    """Return up to 5 published articles in the same category as this news item."""
    news_result = await db.execute(
        select(NewsArticle.category).where(
            NewsArticle.slug == slug, NewsArticle.is_published == True
        )
    )
    row = news_result.first()
    if not row:
        return []
    news_category = row.category

    from app.models.models import Article, ArticleTranslation
    from sqlalchemy import func
    locale = locale if locale in SUPPORTED_LOCALES else "en"

    # Map news category to one or more article categories
    article_cats = _NEWS_TO_ARTICLE_CATS.get(news_category, [news_category])

    # Sort by created_at (always set) so new articles surface first
    q = (
        select(Article)
        .where(Article.category.in_(article_cats), Article.is_published == True)
        .order_by(desc(Article.created_at))
        .limit(5)
    )
    articles_result = await db.execute(q)
    articles = articles_result.scalars().all()

    out = []
    for a in articles:
        title, excerpt = a.title, a.excerpt
        if locale != "en":
            tr = await db.execute(
                select(ArticleTranslation)
                .where(ArticleTranslation.article_id == a.id,
                       ArticleTranslation.locale == locale,
                       ArticleTranslation.status == "done")
            )
            t = tr.scalar_one_or_none()
            if t:
                title = t.title
                excerpt = t.excerpt
        out.append({"slug": a.slug, "title": title, "excerpt": excerpt[:200],
                    "category": a.category})
    return out


@router.get("/{slug}", response_model=NewsDetail)
async def get_news_article(slug: str, locale: str = Query("en"),
                            db: AsyncSession = Depends(get_db)):
    locale = locale if locale in SUPPORTED_LOCALES else "en"
    result = await db.execute(
        select(NewsArticle).where(
            NewsArticle.slug == slug,
            NewsArticle.is_published == True,
            NewsArticle.review_status == "published",
        )
    )
    news = result.scalar_one_or_none()
    if not news:
        raise HTTPException(status_code=404, detail="News article not found")
    return _to_detail(news, locale)


# ── AI generate-summary ───────────────────────────────────────────────────────

@router.post("/generate-summary", response_model=GenerateSummaryResponse)
async def generate_summary(req: GenerateSummaryRequest, user: User = _teacher):
    """Teacher-only: AI-generate title+summary from source URL + optional abstract."""
    from app.services.news_pipeline import _summarise, _infer_category

    title = req.title or ""
    abstract = req.abstract or ""

    # Try to fetch page title if not provided
    if not title or not abstract:
        try:
            async with httpx.AsyncClient(timeout=10) as http:
                resp = await http.get(str(req.source_url),
                                      headers={"User-Agent": "MedMind/1.0"}, follow_redirects=True)
                html = resp.text[:8000]
            if not title:
                m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.I)
                if m:
                    title = re.sub(r"\s*[|\-–—].*$", "", m.group(1)).strip()[:200]
            if not abstract:
                # Try meta description
                m = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']+)', html, re.I)
                if m:
                    abstract = m.group(1)[:1000]
        except Exception:
            pass

    if not title and not abstract:
        raise HTTPException(status_code=422, detail="Could not extract content from URL. Please provide title and abstract manually.")

    category = _infer_category(f"{title} {abstract}")
    summary = await _summarise(title or "Medical Research", abstract or title, category)

    return GenerateSummaryResponse(title=title or "Medical Research", summary=summary, category=category)


# ── Teacher endpoints ─────────────────────────────────────────────────────────

@router.get("/my", response_model=list[NewsListItem])
async def my_news(user: User = _teacher, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(NewsArticle)
        .where(NewsArticle.author_id == user.id)
        .order_by(desc(NewsArticle.fetched_at))
    )
    return [_to_list_item(n, "en") for n in result.scalars().all()]


@router.post("/my", response_model=NewsDetail, status_code=201)
async def create_news(req: NewsCreate, user: User = _teacher,
                      db: AsyncSession = Depends(get_db)):
    h = _source_hash(req.source_url)
    existing = await db.execute(select(NewsArticle.id).where(NewsArticle.source_hash == h))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="A news item with this source URL already exists.")

    date_suffix = datetime.utcnow().strftime("%Y%m%d")
    base_slug = _slugify(req.title, date_suffix)
    slug = await _make_unique_slug(base_slug, db)

    pub_date = None
    if req.original_published_at:
        try:
            pub_date = datetime.fromisoformat(req.original_published_at)
        except ValueError:
            pass

    news = NewsArticle(
        slug=slug,
        source_name=req.source_name,
        source_url=req.source_url,
        source_doi=req.source_doi,
        source_hash=h,
        title=req.title,
        summary=req.summary,
        category=req.category,
        tags=req.tags or [],
        translations={},
        original_published_at=pub_date,
        fetched_at=datetime.utcnow(),
        is_published=False,
        review_status="draft",
        author_id=user.id,
        author_display_name=user.full_name or user.email,
    )
    db.add(news)
    await db.commit()
    await db.refresh(news)
    return _to_detail(news, "en")


@router.patch("/my/{news_id}", response_model=NewsDetail)
async def update_my_news(news_id: UUID, req: NewsUpdate, user: User = _teacher,
                         db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(NewsArticle).where(NewsArticle.id == news_id, NewsArticle.author_id == user.id)
    )
    news = result.scalar_one_or_none()
    if not news:
        raise HTTPException(status_code=404, detail="Not found")
    if news.review_status not in ("draft", "rejected"):
        raise HTTPException(status_code=400, detail="Can only edit draft or rejected news")

    for field, value in req.model_dump(exclude_none=True).items():
        setattr(news, field, value)
    await db.commit()
    await db.refresh(news)
    return _to_detail(news, "en")


@router.post("/my/{news_id}/submit")
async def submit_news(news_id: UUID, user: User = _teacher,
                      db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(NewsArticle).where(NewsArticle.id == news_id, NewsArticle.author_id == user.id)
    )
    news = result.scalar_one_or_none()
    if not news:
        raise HTTPException(status_code=404, detail="Not found")
    if news.review_status != "draft":
        raise HTTPException(status_code=400, detail="Only draft news can be submitted")
    news.review_status = "submitted"
    await db.commit()
    return {"status": "submitted"}


@router.post("/my/{news_id}/withdraw")
async def withdraw_news(news_id: UUID, user: User = _teacher,
                        db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(NewsArticle).where(NewsArticle.id == news_id, NewsArticle.author_id == user.id)
    )
    news = result.scalar_one_or_none()
    if not news:
        raise HTTPException(status_code=404, detail="Not found")
    if news.review_status != "submitted":
        raise HTTPException(status_code=400, detail="Only submitted news can be withdrawn")
    news.review_status = "draft"
    await db.commit()
    return {"status": "draft"}


@router.delete("/my/{news_id}", status_code=204)
async def delete_my_news(news_id: UUID, user: User = _teacher,
                         db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(NewsArticle).where(NewsArticle.id == news_id, NewsArticle.author_id == user.id)
    )
    news = result.scalar_one_or_none()
    if not news:
        raise HTTPException(status_code=404, detail="Not found")
    if news.review_status == "published":
        raise HTTPException(status_code=400, detail="Cannot delete published news — ask admin")
    await db.delete(news)
    await db.commit()


# ── Admin endpoints ───────────────────────────────────────────────────────────

@router.get("/admin/list")
async def admin_list(
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    _a=_admin, db: AsyncSession = Depends(get_db),
):
    q = select(NewsArticle)
    if status:
        q = q.where(NewsArticle.review_status == status)
    q = q.order_by(desc(NewsArticle.fetched_at)).limit(limit).offset(offset)
    result = await db.execute(q)
    return [_to_list_item(n, "en") for n in result.scalars().all()]


@router.patch("/admin/{news_id}/approve")
async def admin_approve(news_id: UUID, _a=_admin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NewsArticle).where(NewsArticle.id == news_id))
    news = result.scalar_one_or_none()
    if not news:
        raise HTTPException(status_code=404, detail="Not found")
    news.review_status = "published"
    news.is_published = True
    news.review_note = None
    await db.commit()
    return {"status": "published"}


@router.patch("/admin/{news_id}/reject")
async def admin_reject(news_id: UUID, req: AdminRejectRequest,
                       _a=_admin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NewsArticle).where(NewsArticle.id == news_id))
    news = result.scalar_one_or_none()
    if not news:
        raise HTTPException(status_code=404, detail="Not found")
    news.review_status = "rejected"
    news.is_published = False
    news.review_note = req.note
    await db.commit()
    return {"status": "rejected"}


@router.delete("/admin/{news_id}", status_code=204)
async def admin_delete(news_id: UUID, _a=_admin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NewsArticle).where(NewsArticle.id == news_id))
    news = result.scalar_one_or_none()
    if not news:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(news)
    await db.commit()


@router.post("/admin/run-pipeline")
async def trigger_pipeline(
    background_tasks: BackgroundTasks,
    days_back: int = Query(7, ge=1, le=30),
    _a=_admin,
):
    background_tasks.add_task(run_news_pipeline, days_back)
    return {"status": "pipeline started", "days_back": days_back}
