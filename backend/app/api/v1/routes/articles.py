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

import mimetypes
import uuid as _uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

import aiofiles
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin, require_teacher
from app.core.config import settings
from app.core.database import get_db
from app.models.models import Article, ArticleTranslation, Module, User

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


def _detail(a: Article) -> dict:
    return {
        **_list_item(a),
        "body": a.body or [],
        "faq": a.faq or [],
        "sources": a.sources or [],
        "related_module_code": a.related_module_code,
        "og_title": a.og_title,
        "og_description": a.og_description,
        "generated_by": a.generated_by,
        "review_status": a.review_status,
        "review_note": a.review_note,
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
    return {"total": total, "page": page, "limit": limit, "articles": [_list_item(a) for a in rows]}


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
    db: AsyncSession = Depends(get_db),
):
    q = select(Article).where(Article.is_published == True, Article.review_status == "published", Article.category == category)
    total = (await db.execute(
        select(func.count(Article.id)).where(Article.is_published == True, Article.review_status == "published", Article.category == category)
    )).scalar() or 0
    q = q.order_by(desc(Article.published_at)).offset((page - 1) * limit).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return {"category": category, "total": total, "page": page, "limit": limit, "articles": [_list_item(a) for a in rows]}


@router.get("/{slug}/related")
async def article_related(
    slug: str,
    limit: int = Query(4, ge=1, le=8),
    db: AsyncSession = Depends(get_db),
):
    """Return related published articles from the same category (excluding self)."""
    article = (await db.execute(
        select(Article).where(Article.slug == slug, Article.is_published == True, Article.review_status == "published")
    )).scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Primary: same category, ordered by recency
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

    return [_list_item(a) for a in rows]


@router.get("/{slug}/nav")
async def article_nav(slug: str, db: AsyncSession = Depends(get_db)):
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

    return {
        "prev": {"slug": prev_art.slug, "title": prev_art.title} if prev_art else None,
        "next": {"slug": next_art.slug, "title": next_art.title} if next_art else None,
    }


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


# ── Teacher endpoints ──────────────────────────────────────────────────────────

@router.get("/my")
async def my_articles(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_teacher),
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
    user: User = Depends(require_teacher),
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
    user: User = Depends(require_teacher),
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
    user: User = Depends(require_teacher),
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
    user: User = Depends(require_teacher),
):
    """Submit a draft article for admin review."""
    article = await _get_article_or_404(article_id, db)
    if str(article.author_id) != str(user.id) and user.role != "admin":
        raise HTTPException(status_code=403, detail="Not your article")
    if article.review_status not in ("draft", "rejected"):
        raise HTTPException(status_code=400, detail=f"Cannot submit: current status is '{article.review_status}'")

    article.review_status = "pending_review"
    article.submitted_at = datetime.utcnow()
    article.review_note = None
    await db.commit()
    return {"id": str(article.id), "review_status": article.review_status}


@router.post("/my/{article_id}/withdraw")
async def withdraw_review(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_teacher),
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
    user: User = Depends(require_teacher),
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
    user: User = Depends(require_teacher),
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

@router.get("/admin/{article_id}")
async def admin_get_article(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    """Admin: fetch any article by ID regardless of published/review status."""
    article = await _get_article_or_404(article_id, db)
    return _detail(article) | {"is_published": article.is_published}


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
