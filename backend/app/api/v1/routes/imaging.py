"""
Medical Imaging Library router.

Endpoints
─────────
POST /imaging/upload             upload image (teacher/admin) — JPEG/PNG/WebP/DICOM
GET  /imaging                    browse with filters (modality, region, specialty)
GET  /imaging/modalities         list distinct modalities with counts
GET  /imaging/regions            list distinct anatomy regions with counts
GET  /imaging/search?q=          full-text search
GET  /imaging/{id}               image detail + increment view_count
DELETE /imaging/{id}             soft-delete (uploader or admin only)
GET  /imaging/openi?q=...        proxy to NIH OpenI API (avoids CORS)

Anatomy Viewers:
GET  /imaging/anatomy/viewers              list all active viewers
GET  /imaging/anatomy/viewers?system=...   filter by organ_system

Annotations (per image):
GET    /imaging/{id}/annotations            list annotations
POST   /imaging/{id}/annotations            create annotation
PATCH  /imaging/{id}/annotations/{ann_id}   update annotation
DELETE /imaging/{id}/annotations/{ann_id}   delete annotation
"""

import base64
import io
import mimetypes
import uuid as _uuid
from typing import Any, Dict, List, Optional
from uuid import UUID

import anthropic
import httpx
from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, UploadFile
from PIL import Image as PILImage
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.models.models import ImageAnnotation, MedicalImage, AnatomyViewer, User
from app.services.storage_service import storage

router = APIRouter(prefix="/imaging", tags=["imaging"])
_claude = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=45.0)

OPENI_BASE = "https://openi.nlm.nih.gov/api/search"

_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_ALLOWED_DICOM_EXTS = {".dcm", ".dicom"}


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


class AnnotationIn(BaseModel):
    annotation_type: str  # arrow | rectangle | circle | text | polygon
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    x2: Optional[float] = None
    y2: Optional[float] = None
    points: Optional[List[Dict[str, float]]] = None
    label: Optional[str] = None
    color: str = "#FF0000"
    stroke_width: int = 2
    font_size: int = 14
    opacity: float = 1.0


class AnnotationOut(AnnotationIn):
    id: str
    image_id: str
    created_by: Optional[str]


# ── Upload ─────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=Dict[str, Any], status_code=201)
async def upload_medical_image(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    modality: Optional[str] = Form("anatomy"),
    anatomy_region: Optional[str] = Form(None),
    specialty: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload a medical image (JPEG/PNG/WebP or DICOM).

    - Teachers and admins only.
    - DICOM files are automatically converted to PNG.
    - A 300×300 thumbnail is generated and saved alongside the original.
    - File is saved via `storage_service` (local or S3 depending on USE_S3).
    """
    if user.role not in ("teacher", "admin"):
        raise HTTPException(403, "Teachers and admins only")

    from app.core.config import settings

    content = await file.read()
    max_bytes = settings.MEDIA_MAX_IMAGE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(400, f"File too large (max {settings.MEDIA_MAX_IMAGE_MB} MB)")

    filename_lower = (file.filename or "").lower()
    is_dicom = any(filename_lower.endswith(ext) for ext in _ALLOWED_DICOM_EXTS)

    if is_dicom:
        # Convert DICOM → PNG
        from app.services.dicom_service import dicom_to_png, extract_dicom_metadata
        png_bytes = await dicom_to_png(content)
        if png_bytes is None:
            raise HTTPException(
                422,
                "DICOM conversion failed. Install pydicom+numpy on the server or upload PNG/JPEG directly.",
            )
        image_bytes = png_bytes
        content_type = "image/png"
        ext = ".png"
        dicom_meta = extract_dicom_metadata(content)
        if not modality:
            modality = dicom_meta.get("modality", "ct").lower()
        if not anatomy_region:
            anatomy_region = dicom_meta.get("body_part", "").lower() or None
    else:
        if file.content_type not in _ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                400,
                f"Unsupported file type '{file.content_type}'. Allowed: JPEG, PNG, WebP, GIF, DICOM.",
            )
        image_bytes = content
        content_type = file.content_type
        ext = mimetypes.guess_extension(content_type) or ".jpg"
        if ext == ".jpe":
            ext = ".jpg"

    uid = _uuid.uuid4().hex
    rel_path = f"medical_images/{uid}{ext}"
    thumb_path = f"medical_images/thumb_{uid}{ext}"

    # Generate thumbnail (300×300, keeps aspect ratio)
    try:
        with PILImage.open(io.BytesIO(image_bytes)) as img:
            img.thumbnail((300, 300))
            thumb_buf = io.BytesIO()
            fmt = "JPEG" if ext in (".jpg", ".jpeg") else "PNG"
            img.save(thumb_buf, format=fmt)
            thumb_bytes = thumb_buf.getvalue()
    except Exception:
        thumb_bytes = image_bytes  # fallback: use original

    image_url = await storage.save(image_bytes, rel_path, content_type)
    thumbnail_url = await storage.save(thumb_bytes, thumb_path, content_type)

    med_image = MedicalImage(
        title=title or file.filename or "Uploaded image",
        description=description,
        modality=modality or "anatomy",
        anatomy_region=anatomy_region,
        specialty=specialty,
        image_url=image_url,
        thumbnail_url=thumbnail_url,
        source_name="MEDMind Upload",
        license="All Rights Reserved",
        attribution=f"Uploaded by {user.email}",
        uploaded_by=user.id,
        is_user_upload=True,
    )
    db.add(med_image)
    await db.commit()
    await db.refresh(med_image)

    return {
        "id": str(med_image.id),
        "url": image_url,
        "thumbnail_url": thumbnail_url,
        "title": med_image.title,
        "modality": med_image.modality,
    }


@router.delete("/{image_id}", status_code=204)
async def delete_image(
    image_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Soft-delete an image (uploader or admin only)."""
    img = (await db.execute(
        select(MedicalImage).where(MedicalImage.id == image_id)
    )).scalar_one_or_none()
    if not img:
        raise HTTPException(404, "Image not found")

    is_owner = user.role == "admin" or (
        img.uploaded_by is not None and str(img.uploaded_by) == str(user.id)
    )
    if not is_owner:
        raise HTTPException(403, "Only the uploader or admin can delete this image")

    img.is_active = False
    await db.commit()


# ── Annotation CRUD ────────────────────────────────────────────────────────

@router.get("/{image_id}/annotations", response_model=List[AnnotationOut])
async def list_annotations(
    image_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return all annotations for a medical image."""
    rows = (await db.execute(
        select(ImageAnnotation)
        .where(ImageAnnotation.image_id == image_id)
        .order_by(ImageAnnotation.created_at)
    )).scalars().all()
    return [
        AnnotationOut(
            id=str(a.id),
            image_id=str(a.image_id),
            annotation_type=a.annotation_type,
            x=a.x, y=a.y, width=a.width, height=a.height,
            x2=a.x2, y2=a.y2, points=a.points,
            label=a.label, color=a.color or "#FF0000",
            stroke_width=a.stroke_width or 2,
            font_size=a.font_size or 14,
            opacity=a.opacity if a.opacity is not None else 1.0,
            created_by=str(a.created_by) if a.created_by else None,
        )
        for a in rows
    ]


@router.post("/{image_id}/annotations", response_model=AnnotationOut, status_code=201)
async def create_annotation(
    image_id: UUID,
    data: AnnotationIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Add an annotation overlay to a medical image (teachers/admins only)."""
    if user.role not in ("teacher", "admin"):
        raise HTTPException(403, "Teachers and admins only")

    img = (await db.execute(
        select(MedicalImage).where(MedicalImage.id == image_id, MedicalImage.is_active == True)
    )).scalar_one_or_none()
    if not img:
        raise HTTPException(404, "Image not found")

    ann = ImageAnnotation(
        image_id=image_id,
        created_by=user.id,
        **data.model_dump(),
    )
    db.add(ann)
    await db.commit()
    await db.refresh(ann)
    return AnnotationOut(
        id=str(ann.id), image_id=str(ann.image_id),
        annotation_type=ann.annotation_type,
        x=ann.x, y=ann.y, width=ann.width, height=ann.height,
        x2=ann.x2, y2=ann.y2, points=ann.points,
        label=ann.label, color=ann.color or "#FF0000",
        stroke_width=ann.stroke_width or 2, font_size=ann.font_size or 14,
        opacity=ann.opacity if ann.opacity is not None else 1.0,
        created_by=str(ann.created_by) if ann.created_by else None,
    )


@router.patch("/{image_id}/annotations/{ann_id}", response_model=AnnotationOut)
async def update_annotation(
    image_id: UUID,
    ann_id: UUID,
    data: AnnotationIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update an existing annotation (creator or admin only)."""
    ann = (await db.execute(
        select(ImageAnnotation).where(
            ImageAnnotation.id == ann_id,
            ImageAnnotation.image_id == image_id,
        )
    )).scalar_one_or_none()
    if not ann:
        raise HTTPException(404, "Annotation not found")

    is_owner = user.role == "admin" or (
        ann.created_by is not None and str(ann.created_by) == str(user.id)
    )
    if not is_owner:
        raise HTTPException(403, "Only the annotation creator or admin can edit this")

    for field, val in data.model_dump(exclude_none=True).items():
        setattr(ann, field, val)
    await db.commit()
    await db.refresh(ann)
    return AnnotationOut(
        id=str(ann.id), image_id=str(ann.image_id),
        annotation_type=ann.annotation_type,
        x=ann.x, y=ann.y, width=ann.width, height=ann.height,
        x2=ann.x2, y2=ann.y2, points=ann.points,
        label=ann.label, color=ann.color or "#FF0000",
        stroke_width=ann.stroke_width or 2, font_size=ann.font_size or 14,
        opacity=ann.opacity if ann.opacity is not None else 1.0,
        created_by=str(ann.created_by) if ann.created_by else None,
    )


@router.delete("/{image_id}/annotations/{ann_id}", status_code=204)
async def delete_annotation(
    image_id: UUID,
    ann_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete an annotation (creator or admin only)."""
    ann = (await db.execute(
        select(ImageAnnotation).where(
            ImageAnnotation.id == ann_id,
            ImageAnnotation.image_id == image_id,
        )
    )).scalar_one_or_none()
    if not ann:
        raise HTTPException(404, "Annotation not found")

    is_owner = user.role == "admin" or (
        ann.created_by is not None and str(ann.created_by) == str(user.id)
    )
    if not is_owner:
        raise HTTPException(403, "Only the annotation creator or admin can delete this")

    await db.delete(ann)
    await db.commit()


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


# ── AI Image Analysis ──────────────────────────────────────────────────────

# Modality-specific analysis prompts
_MODALITY_PROMPTS: dict[str, str] = {
    "xray": (
        "You are a radiologist reviewing this chest/skeletal X-ray for medical education.\n"
        "Provide: 1) Key findings (describe what you see — density, position, size, shape), "
        "2) Interpretation (most likely diagnosis/diagnoses), "
        "3) Differential diagnoses (3 alternatives with brief reasoning), "
        "4) Clinical correlation (what history/symptoms would fit), "
        "5) Teaching points (2–3 key learning messages for medical students).\n"
        "Be precise, educational, and use proper radiological terminology."
    ),
    "ct": (
        "You are a radiologist reviewing this CT scan for medical education.\n"
        "Describe: 1) Imaging plane and contrast phase (if visible), "
        "2) Key findings (attenuation, size, location, enhancement pattern), "
        "3) Interpretation with confidence, "
        "4) Differential diagnoses (3 options with reasoning), "
        "5) Teaching points for medical students."
    ),
    "mri": (
        "You are a radiologist reviewing this MRI for medical education.\n"
        "Describe: 1) Sequence (T1/T2/FLAIR/DWI if identifiable), "
        "2) Signal characteristics and key findings, "
        "3) Most likely diagnosis, "
        "4) Differential diagnoses, "
        "5) Clinical significance and teaching points."
    ),
    "ultrasound": (
        "You are a sonographer/radiologist reviewing this ultrasound image for medical education.\n"
        "Describe: 1) Organ/region imaged, 2) Echogenicity and key findings, "
        "3) Measurements if visible, 4) Interpretation, "
        "5) Teaching points about ultrasound technique and diagnosis."
    ),
    "ecg": (
        "You are a cardiologist reviewing this ECG/EKG for medical education.\n"
        "Systematically analyse: 1) Rate and rhythm, 2) P waves, PR interval, "
        "3) QRS morphology and duration, 4) ST changes, T waves, QTc, "
        "5) Overall interpretation, 6) Clinical significance and treatment implications, "
        "7) Key teaching points for students."
    ),
    "histology": (
        "You are a pathologist reviewing this histology/microscopy slide for medical education.\n"
        "Describe: 1) Stain type (H&E/PAS/Masson's if identifiable), "
        "2) Tissue architecture and cell types, 3) Abnormal findings, "
        "4) Diagnosis, 5) Teaching points about the pathological process."
    ),
}

_DEFAULT_PROMPT = (
    "You are a medical educator reviewing this medical image.\n"
    "Provide: 1) Key findings and what is shown, "
    "2) Interpretation/diagnosis if applicable, "
    "3) Differential considerations, "
    "4) Clinical correlation, "
    "5) Teaching points for medical students.\n"
    "Be educational, precise, and use appropriate medical terminology."
)


async def _fetch_image_as_base64(url: str) -> tuple[str, str]:
    """
    Fetch an image from a URL or local path and return (base64_data, media_type).
    Handles both external URLs and local /media/ paths.
    """
    if url.startswith("/media/"):
        # Local file — read from filesystem
        import os
        local_path = os.path.join(settings.MEDIA_ROOT, url.removeprefix("/media/").lstrip("/"))
        if not os.path.exists(local_path):
            raise HTTPException(404, "Image file not found locally")
        with open(local_path, "rb") as f:
            data = f.read()
        mt, _ = mimetypes.guess_type(local_path)
        return base64.standard_b64encode(data).decode(), mt or "image/jpeg"

    # External URL
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        resp = await client.get(url)
        if resp.status_code != 200:
            raise HTTPException(502, f"Could not fetch image from URL (status {resp.status_code})")
        mt = resp.headers.get("content-type", "image/jpeg").split(";")[0]
        return base64.standard_b64encode(resp.content).decode(), mt


@router.post("/analyze")
async def analyze_image(
    image_url: str = Body(..., embed=True),
    modality: str = Body("", embed=True),
    question: str = Body("", embed=True),
    image_id: Optional[str] = Body(None, embed=True),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    AI-powered medical image analysis using Claude Vision.
    Returns structured findings, interpretation, differential, and teaching points.
    """
    # If image_id provided, resolve URL from DB
    if image_id and not image_url:
        try:
            uid = UUID(image_id)
            res = await db.execute(select(MedicalImage).where(MedicalImage.id == uid))
            img_row = res.scalar_one_or_none()
            if img_row:
                image_url = img_row.image_url
                if not modality:
                    modality = img_row.modality or ""
        except Exception:
            pass

    if not image_url:
        raise HTTPException(400, "image_url or image_id is required")

    # Build system + user prompt
    mod_key = modality.lower() if modality else ""
    # Map common aliases
    if mod_key in ("echocardiogram", "echo"):
        mod_key = "ultrasound"
    system_prompt = _MODALITY_PROMPTS.get(mod_key, _DEFAULT_PROMPT)

    user_text = (
        question.strip()
        or f"Please analyse this {modality or 'medical'} image for educational purposes."
    )

    try:
        img_b64, media_type = await _fetch_image_as_base64(image_url)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(502, f"Failed to retrieve image: {e}")

    # Validate media type
    if media_type not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
        media_type = "image/jpeg"  # safe fallback

    try:
        response = await _claude.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=900,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": img_b64,
                            },
                        },
                        {"type": "text", "text": user_text},
                    ],
                }
            ],
        )
        analysis_text = response.content[0].text if response.content else "No analysis generated."
    except anthropic.BadRequestError as e:
        raise HTTPException(422, f"Image could not be processed by AI: {e}")
    except Exception as e:
        raise HTTPException(502, f"AI analysis failed: {e}")

    return {
        "analysis": analysis_text,
        "modality": modality or "general",
        "image_url": image_url,
        "model": "claude-sonnet-4-6",
    }


# ── Image Suggestion ───────────────────────────────────────────────────────

@router.get("/suggest", response_model=List[ImageOut])
async def suggest_images(
    topic: str = Query(..., min_length=2),
    modality: Optional[str] = Query(None),
    limit: int = Query(4, le=10),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Suggest medical images relevant to a lesson topic.
    Searches the local library first; falls back to NIH OpenI results.
    """
    term = f"%{topic.lower()}%"
    q = (
        select(MedicalImage)
        .where(
            MedicalImage.is_active == True,
            or_(
                func.lower(MedicalImage.title).like(term),
                func.lower(MedicalImage.description).like(term),
                func.lower(MedicalImage.anatomy_region).like(term),
                func.lower(MedicalImage.specialty).like(term),
            ),
        )
        .order_by(MedicalImage.view_count.desc())
        .limit(limit)
    )
    if modality:
        q = q.where(MedicalImage.modality == modality)

    result = await db.execute(q)
    images = result.scalars().all()

    if images:
        return [ImageOut.from_orm(img) for img in images]

    # Fallback: proxy NIH OpenI
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                OPENI_BASE,
                params={"query": topic, "m": 1, "n": limit, "it": "x,ct,mri,us"},
            )
            if resp.status_code == 200:
                data = resp.json()
                openi_images = data.get("list", [])
                out = []
                for img in openi_images[:limit]:
                    img_url = img.get("largeImgUrl") or img.get("imgUrl") or ""
                    if not img_url:
                        continue
                    out.append(ImageOut(
                        id=img.get("uid", ""),
                        title=img.get("title") or topic,
                        description=img.get("abstract", "")[:300] if img.get("abstract") else None,
                        modality=modality or "xray",
                        anatomy_region=None,
                        specialty=None,
                        image_url=img_url,
                        thumbnail_url=img.get("imgThumbUrl"),
                        source_name="NIH OpenI",
                        source_url=img.get("articleURL"),
                        license="Public Domain",
                        attribution="National Library of Medicine — OpenI",
                        tags=[],
                        is_active=True,
                        view_count=0,
                    ))
                return out
    except Exception:
        pass

    return []
