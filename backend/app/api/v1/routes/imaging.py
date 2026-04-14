"""
Medical Imaging Library router.

Endpoints
─────────
GET  /imaging                    browse with filters (modality, region, specialty)
GET  /imaging/modalities         list distinct modalities with counts
GET  /imaging/regions            list distinct anatomy regions with counts
GET  /imaging/search?q=          full-text search
GET  /imaging/{id}               image detail + increment view_count
GET  /imaging/openi?q=...        proxy to NIH OpenI API (avoids CORS)

Anatomy Viewers:
GET  /imaging/anatomy/viewers              list all active viewers
GET  /imaging/anatomy/viewers?system=...   filter by organ_system
"""

from typing import List, Optional
from uuid import UUID
import httpx

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import MedicalImage, AnatomyViewer

router = APIRouter(prefix="/imaging", tags=["imaging"])

OPENI_BASE = "https://openi.nlm.nih.gov/api/search"


# ── Schemas ────────────────────────────────────────────────────────────────

class ImageOut(BaseModel):
    id: str
    title: str
    description: Optional[str]
    modality: str
    anatomy_region: Optional[str]
    specialty: Optional[str]
    image_url: str
    thumbnail_url: Optional[str]
    source_name: str
    source_url: Optional[str]
    license: Optional[str]
    attribution: Optional[str]
    tags: list
    view_count: int

    @classmethod
    def from_orm(cls, img: MedicalImage) -> "ImageOut":
        return cls(
            id=str(img.id),
            title=img.title,
            description=img.description,
            modality=img.modality,
            anatomy_region=img.anatomy_region,
            specialty=img.specialty,
            image_url=img.image_url,
            thumbnail_url=img.thumbnail_url,
            source_name=img.source_name,
            source_url=img.source_url,
            license=img.license,
            attribution=img.attribution,
            tags=img.tags or [],
            view_count=img.view_count or 0,
        )


class ViewerOut(BaseModel):
    id: str
    title: str
    description: Optional[str]
    organ_system: Optional[str]
    anatomy_region: Optional[str]
    embed_type: str
    embed_id: str
    embed_url: Optional[str]
    thumbnail_url: Optional[str]
    source_name: Optional[str]
    source_url: Optional[str]
    license: Optional[str]
    attribution: Optional[str]

    @classmethod
    def from_orm(cls, v: AnatomyViewer) -> "ViewerOut":
        return cls(
            id=str(v.id),
            title=v.title,
            description=v.description,
            organ_system=v.organ_system,
            anatomy_region=v.anatomy_region,
            embed_type=v.embed_type or "sketchfab",
            embed_id=v.embed_id,
            embed_url=v.embed_url,
            thumbnail_url=v.thumbnail_url,
            source_name=v.source_name,
            source_url=v.source_url,
            license=v.license,
            attribution=v.attribution,
        )


# ── Image library endpoints ────────────────────────────────────────────────

@router.get("", response_model=List[ImageOut])
async def browse_images(
    modality: Optional[str] = Query(None),
    region: Optional[str] = Query(None),
    specialty: Optional[str] = Query(None),
    limit: int = Query(40, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Browse library with optional filters."""
    q = select(MedicalImage).where(MedicalImage.is_active == True)
    if modality:
        q = q.where(MedicalImage.modality == modality)
    if region:
        q = q.where(MedicalImage.anatomy_region == region)
    if specialty:
        q = q.where(MedicalImage.specialty == specialty)
    q = q.order_by(MedicalImage.view_count.desc(), MedicalImage.created_at.desc())
    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    return [ImageOut.from_orm(img) for img in result.scalars().all()]


@router.get("/modalities")
async def list_modalities(db: AsyncSession = Depends(get_db)):
    """Return distinct modalities with image counts."""
    result = await db.execute(
        select(MedicalImage.modality, func.count().label("count"))
        .where(MedicalImage.is_active == True)
        .group_by(MedicalImage.modality)
        .order_by(func.count().desc())
    )
    return [{"modality": row[0], "count": row[1]} for row in result.fetchall()]


@router.get("/regions")
async def list_regions(
    modality: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Return distinct anatomy regions with image counts."""
    q = (
        select(MedicalImage.anatomy_region, func.count().label("count"))
        .where(MedicalImage.is_active == True, MedicalImage.anatomy_region.isnot(None))
    )
    if modality:
        q = q.where(MedicalImage.modality == modality)
    q = q.group_by(MedicalImage.anatomy_region).order_by(func.count().desc())
    result = await db.execute(q)
    return [{"region": row[0], "count": row[1]} for row in result.fetchall()]


@router.get("/search", response_model=List[ImageOut])
async def search_images(
    q: str = Query(..., min_length=2),
    modality: Optional[str] = Query(None),
    limit: int = Query(30, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Full-text search across title, description, tags."""
    term = f"%{q.lower()}%"
    query = (
        select(MedicalImage)
        .where(
            MedicalImage.is_active == True,
            or_(
                func.lower(MedicalImage.title).like(term),
                func.lower(MedicalImage.description).like(term),
                func.lower(MedicalImage.anatomy_region).like(term),
            ),
        )
    )
    if modality:
        query = query.where(MedicalImage.modality == modality)
    query = query.order_by(MedicalImage.view_count.desc()).limit(limit)
    result = await db.execute(query)
    return [ImageOut.from_orm(img) for img in result.scalars().all()]


@router.get("/openi")
async def proxy_openi(
    q: str = Query(..., min_length=2),
    m: int = Query(1, ge=1),        # start index
    n: int = Query(10, le=30),       # count
):
    """
    Proxy to NIH OpenI API — avoids browser CORS issues.
    Returns raw OpenI JSON enriched with display-ready fields.
    """
    params = {"q": q, "m": m, "n": n, "it": "x,ct,mri"}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(OPENI_BASE, params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="NIH OpenI API unavailable")

    items = []
    for entry in data.get("list", []):
        uid = entry.get("uid", "")
        img_url = f"https://openi.nlm.nih.gov/imgs/512/{uid}.png" if uid else None
        if not img_url:
            continue
        items.append({
            "uid": uid,
            "title": entry.get("title", "Untitled"),
            "caption": entry.get("caption", ""),
            "image_url": img_url,
            "thumbnail_url": f"https://openi.nlm.nih.gov/imgs/128/{uid}.png",
            "source_url": f"https://openi.nlm.nih.gov/detailedresult?img={uid}",
            "source_name": "NIH OpenI",
            "license": "Public Domain",
            "attribution": "National Library of Medicine — NIH OpenI",
            "modality": _guess_modality(entry),
        })
    return {"total": data.get("total", 0), "list": items}


def _guess_modality(entry: dict) -> str:
    img_type = (entry.get("image_type") or "").lower()
    if "xray" in img_type or "radiograph" in img_type:
        return "xray"
    if "ct" in img_type or "computed" in img_type:
        return "ct"
    if "mri" in img_type or "magnetic" in img_type:
        return "mri"
    if "ultrasound" in img_type or "us" == img_type:
        return "ultrasound"
    return "other"


@router.get("/{image_id}", response_model=ImageOut)
async def get_image(image_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get image detail and increment view count."""
    result = await db.execute(
        select(MedicalImage).where(MedicalImage.id == image_id, MedicalImage.is_active == True)
    )
    img = result.scalar_one_or_none()
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    img.view_count = (img.view_count or 0) + 1
    await db.commit()
    await db.refresh(img)
    return ImageOut.from_orm(img)


# ── Anatomy viewers ────────────────────────────────────────────────────────

@router.get("/anatomy/viewers", response_model=List[ViewerOut])
async def list_viewers(
    system: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List 3D anatomy viewers, optionally filtered by organ system."""
    q = select(AnatomyViewer).where(AnatomyViewer.is_active == True)
    if system:
        q = q.where(AnatomyViewer.organ_system == system)
    q = q.order_by(AnatomyViewer.sort_order)
    result = await db.execute(q)
    return [ViewerOut.from_orm(v) for v in result.scalars().all()]
