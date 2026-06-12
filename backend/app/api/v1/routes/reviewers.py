"""Public reviewer profile endpoints — V4 Phase 3."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import Article, Reviewer

router = APIRouter(prefix="/reviewers", tags=["public"])


def _reviewer_out(r: Reviewer) -> dict:
    return {
        "slug": r.slug,
        "name": r.name,
        "credentials": r.credentials,
        "bio": r.bio,
        "institution": r.institution,
        "avatar_url": r.avatar_url,
        "specialties": r.specialties or [],
        "linkedin_url": r.linkedin_url,
    }


@router.get("")
async def list_reviewers(db: AsyncSession = Depends(get_db)):
    """List active reviewers."""
    rows = (await db.execute(
        select(Reviewer).where(Reviewer.is_active == True).order_by(Reviewer.name)
    )).scalars().all()
    return [_reviewer_out(r) for r in rows]


@router.get("/{slug}")
async def get_reviewer(slug: str, db: AsyncSession = Depends(get_db)):
    """Get a single reviewer profile with their reviewed articles."""
    reviewer = (await db.execute(
        select(Reviewer).where(Reviewer.slug == slug, Reviewer.is_active == True)
    )).scalar_one_or_none()
    if not reviewer:
        raise HTTPException(status_code=404, detail="Reviewer not found")

    # Fetch articles reviewed by this person (by display name match)
    reviewed_articles = (await db.execute(
        select(Article.slug, Article.title, Article.category, Article.published_at)
        .where(
            Article.reviewed_by == reviewer.name,
            Article.is_published == True,
            Article.review_status == "published",
        )
        .order_by(Article.published_at.desc())
        .limit(20)
    )).all()

    return {
        **_reviewer_out(reviewer),
        "reviewed_articles": [
            {
                "slug": a.slug,
                "title": a.title,
                "category": a.category,
                "published_at": a.published_at.isoformat() if a.published_at else None,
            }
            for a in reviewed_articles
        ],
    }
