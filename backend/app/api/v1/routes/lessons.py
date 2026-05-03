"""Teacher lesson authoring endpoints.

Endpoints
─────────
Modules (teacher-authored):
  POST   /lessons/modules                    Create new module (teacher/admin)
  PATCH  /lessons/modules/{module_id}        Update module metadata
  DELETE /lessons/modules/{module_id}        Soft-delete module (unpublish)

Lessons CRUD:
  POST   /lessons/modules/{module_id}/lessons       Create lesson (draft)
  GET    /lessons/modules/{module_id}/lessons        List lessons in module
  GET    /lessons/{lesson_id}                        Get lesson detail
  PATCH  /lessons/{lesson_id}                        Update lesson content/metadata
  DELETE /lessons/{lesson_id}                        Archive lesson

Workflow:
  PATCH  /lessons/{lesson_id}/submit-review          Move draft → review
  PATCH  /lessons/{lesson_id}/publish                Publish (author or admin)
  PATCH  /lessons/{lesson_id}/archive                Archive
  GET    /lessons/{lesson_id}/preview                Preview (author sees drafts)

AI assist:
  POST   /lessons/{lesson_id}/ai-improve             AI suggestions for lesson content
"""
import json
import mimetypes
import uuid as _uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal, Optional
from uuid import UUID

import aiofiles
import anthropic
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.audit import audit
from app.core.cache import invalidate
from app.core.config import settings
from app.core.database import get_db
from app.models.models import Flashcard, Lesson, LessonCompletion, LessonVersion, MCQQuestion, Module, Specialty, User, UserProgress
from app.services.content_sanitizer import sanitize_for_llm_context

router = APIRouter(prefix="/lessons", tags=["lessons"])

_claude = anthropic.AsyncAnthropic(
    api_key=settings.ANTHROPIC_API_KEY,
    timeout=30.0,
    max_retries=2,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers / guards
# ─────────────────────────────────────────────────────────────────────────────

def _require_teacher(user: User) -> None:
    if user.role not in ("teacher", "admin"):
        raise HTTPException(403, "Teacher or admin role required")


async def _get_module_or_404(module_id: UUID, db: AsyncSession) -> Module:
    mod = await db.get(Module, module_id)
    if not mod:
        raise HTTPException(404, "Module not found")
    return mod


async def _get_lesson_or_404(lesson_id: UUID, db: AsyncSession) -> Lesson:
    lesson = await db.get(Lesson, lesson_id)
    if not lesson:
        raise HTTPException(404, "Lesson not found")
    return lesson


def _same_uuid(a, b) -> bool:
    """Compare two UUID-like values safely.

    Handles: uuid.UUID objects, 32-char hex strings (SQLite stores without dashes),
    standard hyphenated strings, and 16-byte blobs.
    """
    if a is None or b is None:
        return False

    def _normalise(v) -> _uuid.UUID:
        if isinstance(v, _uuid.UUID):
            return v
        if isinstance(v, bytes) and len(v) == 16:
            return _uuid.UUID(bytes=v)
        s = str(v).strip().replace("-", "").lower()
        return _uuid.UUID(s)  # accepts 32-char hex

    try:
        return _normalise(a) == _normalise(b)
    except (ValueError, AttributeError):
        return False


def _require_module_owner(mod: Module, user: User) -> None:
    """Only the module author or an admin may modify it."""
    if user.role == "admin":
        return
    if mod.author_id is None or not _same_uuid(mod.author_id, user.id):
        raise HTTPException(403, "Not the module author")


def _require_lesson_owner(lesson: Lesson, user: User) -> None:
    """Only the lesson author or an admin may modify it."""
    if user.role == "admin":
        return
    if lesson.author_id is None or not _same_uuid(lesson.author_id, user.id):
        raise HTTPException(403, "Not the lesson author")


# ─────────────────────────────────────────────────────────────────────────────
# Content schema — Pydantic validation for lesson blocks
# ─────────────────────────────────────────────────────────────────────────────

_VALID_SPECIES = frozenset({
    "human", "canine", "feline", "equine", "bovine",
    "porcine", "ovine", "avian", "exotic",
})

_VALID_RISK_LEVELS = frozenset({"low", "medium", "high"})


class GuidelineSource(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    year: Optional[int] = Field(default=None, ge=2000, le=2030)
    url: Optional[str] = None


class LessonBlock(BaseModel):
    """One content block inside a lesson.

    ``show_if`` / ``hide_if`` support adaptive display on the frontend:
    e.g. ``{"user_level": "intermediate+"}`` or ``{"species_context": "feline"}``
    """
    type: Literal["text", "image", "video", "quiz", "case", "flashcard", "table", "dosage_table", "anatomy_3d"]
    content: dict
    order: int = Field(ge=0)
    # Optional accessibility & species metadata
    alt_text: Optional[str] = None          # required for image blocks (accessibility)
    species_context: Optional[list[str]] = None  # limits block visibility by species
    clinical_warning: Optional[str] = None  # inline clinical safety warning
    # Adaptive display conditions (evaluated by frontend)
    show_if: Optional[dict] = None
    hide_if: Optional[dict] = None

    model_config = {"extra": "allow"}


class LessonContent(BaseModel):
    """Validated lesson content structure stored as JSONB.

    Supported block types:
    - **text** — rich Markdown body
    - **quiz** — MCQ with options A-E, correct answer, explanation
    - **case** — clinical case (presentation, diagnosis, management)
    - **image** — medical image (url or image_id, alt_text required)
    - **dosage_table** — species-specific dosing table
    - **anatomy_3d** — 3D anatomy viewer embed

    Medical/vet fields:
    - ``species_applicability`` — list of species this lesson covers
    - ``clinical_risk_level`` — low | medium | high
    - ``guideline_sources`` — authoritative sources (name, year, url)
    """
    title: str = Field(min_length=2, max_length=300)
    blocks: list[LessonBlock] = Field(default_factory=list)
    estimated_minutes: int = Field(default=20, ge=5, le=180)
    learning_objectives: list[str] = Field(default_factory=list)

    # Medical / veterinary metadata
    species_applicability: list[str] = Field(default_factory=lambda: ["human"])
    clinical_risk_level: str = Field(default="low")
    guideline_sources: list[GuidelineSource] = Field(default_factory=list)
    cross_species_comparative: bool = False  # flag for lessons mixing human+vet content

    model_config = {"extra": "allow"}

    @field_validator("species_applicability")
    @classmethod
    def validate_species(cls, v: list[str]) -> list[str]:
        invalid = set(v) - _VALID_SPECIES
        if invalid:
            raise ValueError(f"Unknown species: {invalid}. Valid: {sorted(_VALID_SPECIES)}")
        return v

    @field_validator("clinical_risk_level")
    @classmethod
    def validate_risk(cls, v: str) -> str:
        if v not in _VALID_RISK_LEVELS:
            raise ValueError(f"clinical_risk_level must be one of {sorted(_VALID_RISK_LEVELS)}")
        return v


# ─────────────────────────────────────────────────────────────────────────────
# Pydantic schemas
# ─────────────────────────────────────────────────────────────────────────────

class ModuleCreate(BaseModel):
    title: str = Field(min_length=2, max_length=300)
    description: Optional[str] = None
    specialty_code: Optional[str] = None   # e.g. "cardiology"
    level_label: Optional[str] = "intermediate"
    is_veterinary: bool = False


class ModuleUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    level_label: Optional[str] = None
    is_veterinary: Optional[bool] = None


class ModuleOut(BaseModel):
    id: UUID
    code: str
    title: str
    description: Optional[str]
    level_label: Optional[str]
    is_published: bool
    is_veterinary: bool
    author_id: Optional[UUID]
    created_at: datetime

    model_config = {"from_attributes": True}


class LessonCreate(BaseModel):
    title: str = Field(min_length=2, max_length=300)
    content: LessonContent
    estimated_minutes: int = Field(default=20, ge=5, le=180)
    lesson_order: int = Field(default=0, ge=0)
    # Medical/vet metadata (also embedded in content, mirrored here for DB columns)
    species_applicability: list[str] = Field(default_factory=lambda: ["human"])
    clinical_risk_level: str = Field(default="low")
    requires_clinical_supervision: bool = False
    guideline_version: Optional[str] = None
    cross_species_warning: Optional[str] = None


class LessonUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=300)
    content: Optional[LessonContent] = None
    estimated_minutes: Optional[int] = Field(default=None, ge=5, le=180)
    lesson_order: Optional[int] = Field(default=None, ge=0)
    review_notes: Optional[str] = None
    expected_version: Optional[int] = None   # if set, enforces optimistic locking
    # Medical/vet metadata
    species_applicability: Optional[list[str]] = None
    clinical_risk_level: Optional[str] = None
    requires_clinical_supervision: Optional[bool] = None
    guideline_version: Optional[str] = None
    cross_species_warning: Optional[str] = None
    last_expert_review: Optional[datetime] = None
    next_review_due: Optional[datetime] = None


class LessonOut(BaseModel):
    id: UUID
    module_id: UUID
    title: str
    lesson_order: int
    estimated_minutes: int
    status: str
    author_id: Optional[UUID]
    published_at: Optional[datetime]
    review_notes: Optional[str]
    content: dict
    created_at: datetime
    updated_at: datetime
    row_version: int = 0
    # Medical/vet fields
    species_applicability: list[str] = Field(default_factory=lambda: ["human"])
    clinical_risk_level: str = "low"
    requires_clinical_supervision: bool = False
    guideline_version: Optional[str] = None
    last_expert_review: Optional[datetime] = None
    next_review_due: Optional[datetime] = None
    cross_species_warning: Optional[str] = None
    # Preview token (returned only to author/admin)
    preview_token: Optional[str] = None
    preview_expires_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class LessonTranslationOut(BaseModel):
    lesson_id: UUID
    locale: str
    title: str
    content_json: dict
    status: str
    reviewed: bool
    translated_at: Optional[datetime]
    error_message: Optional[str]

    model_config = {"from_attributes": True}


class TranslationStatusOut(BaseModel):
    """Summary of all translations for a lesson."""
    lesson_id: UUID
    translations: list[dict]  # [{locale, status, reviewed, translated_at}]


class AIImproveRequest(BaseModel):
    task: Literal[
        "improve_clarity",
        "add_quiz",
        "simplify_language",
        "add_clinical_case",
        "check_accuracy",
    ]
    specialty: str
    target_level: Literal["beginner", "intermediate", "advanced"] = "intermediate"


class AIGenerateRequest(BaseModel):
    """Request body for generating a lesson from scratch with AI."""
    title: str = Field(min_length=2, max_length=300)
    specialty: str
    key_concepts: list[str] = Field(default_factory=list, max_length=10)
    target_level: Literal["beginner", "intermediate", "advanced"] = "intermediate"
    estimated_minutes: int = Field(default=20, ge=5, le=90)
    include_quiz: bool = True
    include_clinical_case: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# Module endpoints (teacher-authored modules)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/my-modules", response_model=list[ModuleOut])
async def list_my_modules(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all modules authored by the current teacher."""
    _require_teacher(user)
    result = await db.execute(
        select(Module).where(Module.author_id == user.id).order_by(Module.created_at.desc())
    )
    return result.scalars().all()


@router.post("/modules", response_model=ModuleOut, status_code=201)
async def create_module(
    body: ModuleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new teacher-authored module."""
    _require_teacher(user)

    # Resolve specialty
    specialty_id = None
    if body.specialty_code:
        result = await db.execute(
            select(Specialty).where(Specialty.code == body.specialty_code)
        )
        spec = result.scalar_one_or_none()
        if spec:
            specialty_id = spec.id

    # Generate a unique module code
    import uuid as _uuid
    code = f"TCHR-{user.id.hex[:6].upper()}-{_uuid.uuid4().hex[:6].upper()}"

    mod = Module(
        code=code,
        title=body.title,
        description=body.description,
        specialty_id=specialty_id,
        level_label=body.level_label or "intermediate",
        is_veterinary=body.is_veterinary,
        is_published=False,  # starts unpublished
        author_id=user.id,
    )
    db.add(mod)
    await db.commit()
    await db.refresh(mod)
    await audit(db, "module_created", user_id=user.id, resource_id=mod.id)
    return mod


@router.patch("/modules/{module_id}", response_model=ModuleOut)
async def update_module(
    module_id: UUID,
    body: ModuleUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _require_teacher(user)
    mod = await _get_module_or_404(module_id, db)
    _require_module_owner(mod, user)

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(mod, field, value)
    mod.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(mod)
    return mod


@router.patch("/modules/{module_id}/publish", response_model=ModuleOut)
async def publish_module(
    module_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Make a teacher-authored module visible to students."""
    _require_teacher(user)
    mod = await _get_module_or_404(module_id, db)
    _require_module_owner(mod, user)

    # Check module has at least one published lesson
    result = await db.execute(
        select(Lesson).where(
            Lesson.module_id == module_id,
            Lesson.status == "published",
        ).limit(1)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(400, "Module must have at least one published lesson before publishing")

    mod.is_published = True
    mod.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(mod)
    await audit(db, "module_published", user_id=user.id, resource_id=mod.id)
    await invalidate(f"specialty_modules:{mod.specialty_id}*")
    await invalidate("specialties*")

    # Trigger background translation of module metadata
    from app.services.translation_service import schedule_module_translations
    await schedule_module_translations(mod.id, db)

    return mod


@router.delete("/modules/{module_id}", status_code=204)
async def delete_module(
    module_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Soft-delete: unpublish teacher module."""
    _require_teacher(user)
    mod = await _get_module_or_404(module_id, db)
    _require_module_owner(mod, user)

    mod.is_published = False
    mod.updated_at = datetime.utcnow()
    await db.commit()
    await audit(db, "module_unpublished", user_id=user.id, resource_id=mod.id)


# ─────────────────────────────────────────────────────────────────────────────
# Lesson CRUD
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/modules/{module_id}/lessons", response_model=LessonOut, status_code=201)
async def create_lesson(
    module_id: UUID,
    body: LessonCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Create a new lesson in a module (starts as draft)."""
    _require_teacher(user)
    mod = await _get_module_or_404(module_id, db)
    _require_module_owner(mod, user)

    lesson = Lesson(
        module_id=module_id,
        title=body.title,
        content=body.content.model_dump(),
        estimated_minutes=body.estimated_minutes,
        lesson_order=body.lesson_order,
        author_id=user.id,
        status="draft",
        species_applicability=body.species_applicability,
        clinical_risk_level=body.clinical_risk_level,
        requires_clinical_supervision=body.requires_clinical_supervision,
        guideline_version=body.guideline_version,
        cross_species_warning=body.cross_species_warning,
    )
    db.add(lesson)
    await db.commit()
    await db.refresh(lesson)
    await audit(db, "lesson_created", user_id=user.id, resource_id=lesson.id)
    return lesson


@router.get("/modules/{module_id}/lessons", response_model=list[LessonOut])
async def list_lessons(
    module_id: UUID,
    include_drafts: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List lessons in a module. Teachers see drafts of own modules."""
    mod = await _get_module_or_404(module_id, db)

    stmt = select(Lesson).where(Lesson.module_id == module_id)

    # Students only see published lessons
    is_owner = user.role == "admin" or (
        mod.author_id is not None and _same_uuid(mod.author_id, user.id)
    )
    if not is_owner or not include_drafts:
        stmt = stmt.where(Lesson.status == "published")

    stmt = stmt.order_by(Lesson.lesson_order)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{lesson_id}", response_model=LessonOut)
async def get_lesson(
    lesson_id: UUID,
    locale: Optional[str] = Query(None, description="Return translated content (e.g. 'ru', 'de')"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get lesson detail. Drafts visible only to author/admin.
    Pass ?locale=ru to get translated title and content blocks.
    Falls back to English if translation is not ready.
    """
    from app.models.models import LessonTranslation
    lesson = await _get_lesson_or_404(lesson_id, db)

    if lesson.status != "published":
        is_owner = user.role == "admin" or (
            lesson.author_id is not None and _same_uuid(lesson.author_id, user.id)
        )
        if not is_owner:
            raise HTTPException(403, "This lesson is not yet published")

    # Apply translation if requested and available
    if locale and locale != "en":
        tr = await db.get(LessonTranslation, (lesson_id, locale))
        if tr and tr.status == "done" and tr.content_json:
            # Return a synthetic object with translated content
            lesson.title = tr.title
            lesson.content = tr.content_json

    return lesson


@router.patch("/{lesson_id}", response_model=LessonOut)
async def update_lesson(
    lesson_id: UUID,
    body: LessonUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Update lesson content or metadata. Only allowed in draft/review status."""
    _require_teacher(user)
    lesson = await _get_lesson_or_404(lesson_id, db)
    _require_lesson_owner(lesson, user)

    # Optimistic locking: reject if client's version is stale
    if body.expected_version is not None and lesson.row_version != body.expected_version:
        raise HTTPException(
            status_code=409,
            detail=f"Lesson was modified by another user. Current version: {lesson.row_version}. Reload and try again.",
        )

    if lesson.status == "archived":
        raise HTTPException(400, "Cannot edit an archived lesson")

    # Save current state as a version snapshot before applying changes
    max_ver_result = await db.execute(
        select(func.max(LessonVersion.version_number)).where(LessonVersion.lesson_id == lesson_id)
    )
    next_ver = (max_ver_result.scalar() or 0) + 1
    db.add(LessonVersion(
        lesson_id=lesson_id,
        version_number=next_ver,
        title=lesson.title,
        content=lesson.content,
        saved_by=user.id,
    ))

    data = body.model_dump(exclude_none=True)
    # Remove schema-only fields that don't map to model columns
    data.pop("expected_version", None)
    content_changed = False
    if "content" in data:
        # content is a LessonContent object — convert to dict for JSONB
        data["content"] = body.content.model_dump()
        content_changed = True
    for field, value in data.items():
        setattr(lesson, field, value)
    lesson.row_version = (lesson.row_version or 0) + 1
    lesson.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(lesson)
    await invalidate(f"module:{lesson.module_id}*")

    # Re-embed in background when content changes (keeps vector search accurate)
    if content_changed and lesson.content:
        import asyncio
        from app.services.embedding_service import reembed_lesson as _reembed
        asyncio.create_task(_reembed(lesson.id, lesson.content))

    return lesson


@router.delete("/{lesson_id}", status_code=204)
async def archive_lesson(
    lesson_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Archive (soft-delete) a lesson."""
    _require_teacher(user)
    lesson = await _get_lesson_or_404(lesson_id, db)
    _require_lesson_owner(lesson, user)

    lesson.status = "archived"
    lesson.updated_at = datetime.utcnow()
    await db.commit()
    await audit(db, "lesson_archived", user_id=user.id, resource_id=lesson_id)


# ─────────────────────────────────────────────────────────────────────────────
# Workflow transitions
# ─────────────────────────────────────────────────────────────────────────────

@router.patch("/{lesson_id}/submit-review", response_model=LessonOut)
async def submit_for_review(
    lesson_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Move lesson from draft → review (author submits for approval)."""
    _require_teacher(user)
    lesson = await _get_lesson_or_404(lesson_id, db)
    _require_lesson_owner(lesson, user)

    if lesson.status != "draft":
        raise HTTPException(400, f"Lesson is '{lesson.status}', expected 'draft'")

    lesson.status = "review"
    lesson.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(lesson)
    await audit(db, "lesson_submitted_review", user_id=user.id, resource_id=lesson_id)
    return lesson


@router.patch("/{lesson_id}/publish", response_model=LessonOut)
async def publish_lesson(
    lesson_id: UUID,
    force: bool = Query(False, description="Admin-only: skip validation checks"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Publish a lesson (from draft/review status). Author or admin only.

    Runs MedVet validation before publishing — returns HTTP 422 with a list
    of errors if the lesson fails safety/quality checks. Admins may pass
    ``?force=true`` to bypass validation (emergency fix scenarios).
    """
    _require_teacher(user)
    lesson = await _get_lesson_or_404(lesson_id, db)
    _require_lesson_owner(lesson, user)

    if lesson.status not in ("review", "draft"):
        raise HTTPException(400, f"Cannot publish lesson with status '{lesson.status}'")

    # Run publication validator (skip if admin passes force=true)
    if not (force and user.role == "admin"):
        from app.services.lesson_validator import validate_for_publication
        # Resolve specialty code from module
        module = await _get_module_or_404(lesson.module_id, db)
        specialty_code = ""
        if module.specialty_id:
            from app.models.models import Specialty
            spec = await db.get(Specialty, module.specialty_id)
            specialty_code = spec.code if spec else ""

        errors = await validate_for_publication(lesson, specialty_code)
        if errors:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Lesson failed publication checks. Fix the issues below before publishing.",
                    "errors": errors,
                    "hint": "Admin can use ?force=true to override.",
                },
            )

    lesson.status = "published"
    lesson.published_at = datetime.utcnow()
    lesson.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(lesson)
    await audit(db, "lesson_published", user_id=user.id, resource_id=lesson_id)
    await invalidate(f"module:{lesson.module_id}*")
    await invalidate("specialty_modules:*")

    # Trigger background translation into all supported locales
    from app.services.translation_service import schedule_lesson_translations
    await schedule_lesson_translations(lesson.id, db)

    return lesson


@router.patch("/{lesson_id}/unpublish", response_model=LessonOut)
async def unpublish_lesson(
    lesson_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Move lesson back to draft for editing."""
    _require_teacher(user)
    lesson = await _get_lesson_or_404(lesson_id, db)
    _require_lesson_owner(lesson, user)

    if lesson.status != "published":
        raise HTTPException(400, "Only published lessons can be unpublished")

    lesson.status = "draft"
    lesson.published_at = None
    lesson.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(lesson)
    return lesson


# ─────────────────────────────────────────────────────────────────────────────
# Preview
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{lesson_id}/preview", response_model=LessonOut)
async def preview_lesson(
    lesson_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Preview endpoint — author/admin can preview any status, students only published."""
    lesson = await _get_lesson_or_404(lesson_id, db)

    is_owner = user.role == "admin" or (
        lesson.author_id is not None and _same_uuid(lesson.author_id, user.id)
    )
    if not is_owner and lesson.status != "published":
        raise HTTPException(403, "Lesson not yet published")

    return lesson


# ─────────────────────────────────────────────────────────────────────────────
# Preview token — shareable links for draft lessons
# ─────────────────────────────────────────────────────────────────────────────

class PreviewLinkResponse(BaseModel):
    preview_token: str
    preview_url: str
    expires_at: datetime


@router.post("/{lesson_id}/preview-link", response_model=PreviewLinkResponse)
async def create_preview_link(
    lesson_id: UUID,
    expires_hours: int = Query(24, ge=1, le=168, description="Link validity in hours (1–168)"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate a time-limited shareable preview link for a draft lesson.

    The link can be shared with colleagues or reviewers without requiring them
    to log in.  Only the lesson author or an admin may generate preview links.
    """
    _require_teacher(user)
    lesson = await _get_lesson_or_404(lesson_id, db)

    is_owner = user.role == "admin" or (
        lesson.author_id is not None and _same_uuid(lesson.author_id, user.id)
    )
    if not is_owner:
        raise HTTPException(403, "Only the lesson author can create preview links")

    import secrets
    token = secrets.token_hex(32)  # 64-char hex
    expires_at = datetime.utcnow() + timedelta(hours=expires_hours)

    lesson.preview_token = token
    lesson.preview_expires_at = expires_at
    await db.commit()

    return PreviewLinkResponse(
        preview_token=token,
        preview_url=f"/api/v1/lessons/preview/{token}",
        expires_at=expires_at,
    )


@router.get("/preview/{token}", response_model=LessonOut)
async def view_preview_by_token(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Public preview endpoint accessed via a time-limited token.

    No authentication required — designed for external reviewers.
    Token is single-use per generation (teacher can regenerate to revoke).
    """
    lesson = (await db.execute(
        select(Lesson).where(Lesson.preview_token == token)
    )).scalar_one_or_none()

    if not lesson:
        raise HTTPException(404, "Preview link not found or expired")

    if lesson.preview_expires_at and lesson.preview_expires_at < datetime.utcnow():
        raise HTTPException(410, "Preview link has expired. Ask the author to generate a new one.")

    return lesson


# ─────────────────────────────────────────────────────────────────────────────
# AI-assisted lesson improvement
# ─────────────────────────────────────────────────────────────────────────────

_AI_IMPROVE_PROMPTS = {
    "improve_clarity": (
        "Rewrite the lesson content to be clearer and more concise. "
        "Use active voice, shorter sentences, and plain medical language at {level} level."
    ),
    "add_quiz": (
        "Add 3 multiple-choice quiz blocks (type='quiz') to the lesson content. "
        "Each quiz block should have: question, options (A-E), correct answer, explanation. "
        "Questions must be relevant to the existing content and appropriate for {level} level."
    ),
    "simplify_language": (
        "Simplify the language for {level} medical students. "
        "Replace jargon with plain explanations. Keep clinical accuracy."
    ),
    "add_clinical_case": (
        "Add one realistic clinical case block (type='case') that illustrates the main concept. "
        "The case should match {specialty} specialty and {level} student level. "
        "Format: patient presentation → questions → teaching points."
    ),
    "check_accuracy": (
        "Review the lesson content for medical accuracy. "
        "Identify any outdated information, incorrect statements, or missing safety warnings. "
        "Return the corrected content with a 'review_notes' field listing changes made."
    ),
}


@router.post("/{lesson_id}/ai-improve")
async def ai_improve_lesson(
    lesson_id: UUID,
    body: AIImproveRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get AI suggestions to improve lesson content. Returns suggested diff."""
    _require_teacher(user)
    lesson = await _get_lesson_or_404(lesson_id, db)
    _require_lesson_owner(lesson, user)

    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(503, "AI service not configured")

    task_instruction = _AI_IMPROVE_PROMPTS[body.task].format(
        level=body.target_level,
        specialty=body.specialty,
    )

    prompt = (
        f"You are a medical education expert helping a teacher improve a lesson.\n\n"
        f"Task: {task_instruction}\n\n"
        f"Specialty: {body.specialty}\n"
        f"Target student level: {body.target_level}\n\n"
        f"Current lesson content:\n"
        f"{sanitize_for_llm_context(lesson.content)}\n\n"
        f"Return ONLY the improved lesson content as valid JSON in the same structure. "
        f"Do not add explanations outside the JSON. "
        f"If you add a 'review_notes' key, put your comments there."
    )

    try:
        response = await _claude.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        raw = response.content[0].text if response.content else "{}"

        # Strip markdown fences
        import re
        raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
        try:
            suggested = json.loads(raw)
        except json.JSONDecodeError:
            # Try to find JSON object
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            suggested = json.loads(m.group()) if m else {}

        if not isinstance(suggested, dict):
            raise HTTPException(502, "AI returned unexpected format")

        # Extract review notes if present
        review_notes = suggested.pop("review_notes", None)

        return {
            "lesson_id": str(lesson_id),
            "task": body.task,
            "original": lesson.content,
            "suggested": suggested,
            "review_notes": review_notes,
            "model": "claude-haiku-4-5-20251001",
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, f"AI service error: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# Media upload for lesson images
# ─────────────────────────────────────────────────────────────────────────────

_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/svg+xml", "image/webp"}

@router.post("/{lesson_id}/upload-media")
async def upload_lesson_media(
    lesson_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Upload an image for a lesson block. Returns public URL."""
    _require_teacher(user)
    lesson = await _get_lesson_or_404(lesson_id, db)
    _require_lesson_owner(lesson, user)

    content_type = file.content_type or ""
    if content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(400, f"File type '{content_type}' not allowed. Accepted: JPEG, PNG, SVG, WebP.")

    max_bytes = settings.MEDIA_MAX_IMAGE_MB * 1024 * 1024
    data = await file.read()
    if len(data) > max_bytes:
        raise HTTPException(400, f"File exceeds {settings.MEDIA_MAX_IMAGE_MB} MB limit.")

    ext = mimetypes.guess_extension(content_type) or ".bin"
    # .jpe is the default extension for jpeg in some systems — normalise
    if ext == ".jpe":
        ext = ".jpg"
    filename = f"{_uuid.uuid4().hex}{ext}"

    dest_dir = Path(settings.MEDIA_ROOT) / "lessons" / str(lesson_id)
    dest_dir.mkdir(parents=True, exist_ok=True)

    async with aiofiles.open(dest_dir / filename, "wb") as f:
        await f.write(data)

    url = f"{settings.MEDIA_URL}/lessons/{lesson_id}/{filename}"
    await audit(db, "media_uploaded", user_id=user.id, resource_id=lesson_id)
    return {"url": url, "filename": filename, "size": len(data), "content_type": content_type}


# ─────────────────────────────────────────────────────────────────────────────
# AI lesson generation from scratch
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# Lesson completion (student records finishing a lesson)
# ─────────────────────────────────────────────────────────────────────────────

class LessonCompleteRequest(BaseModel):
    time_spent_seconds: int = Field(default=0, ge=0)
    quiz_score: Optional[float] = Field(default=None, ge=0, le=100)
    quiz_attempts: int = Field(default=0, ge=0)


@router.post("/{lesson_id}/complete", status_code=201)
async def complete_lesson(
    lesson_id: UUID,
    body: LessonCompleteRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Record that a student has completed this lesson. Idempotent — updates if already recorded."""
    lesson = await _get_lesson_or_404(lesson_id, db)
    if lesson.status != "published":
        raise HTTPException(400, "Can only complete published lessons")

    existing = await db.execute(
        select(LessonCompletion).where(
            LessonCompletion.lesson_id == lesson_id,
            LessonCompletion.user_id == user.id,
        )
    )
    completion = existing.scalar_one_or_none()

    if completion:
        # Update with better score or more time
        if body.quiz_score is not None and (completion.quiz_score is None or body.quiz_score > float(completion.quiz_score)):
            completion.quiz_score = body.quiz_score
        completion.quiz_attempts = (completion.quiz_attempts or 0) + body.quiz_attempts
        completion.time_spent_seconds = (completion.time_spent_seconds or 0) + body.time_spent_seconds
    else:
        completion = LessonCompletion(
            lesson_id=lesson_id,
            user_id=user.id,
            time_spent_seconds=body.time_spent_seconds,
            quiz_score=body.quiz_score,
            quiz_attempts=body.quiz_attempts,
        )
        db.add(completion)

    await db.commit()
    return {"lesson_id": str(lesson_id), "status": "completed"}


# ─────────────────────────────────────────────────────────────────────────────
# Teacher analytics — per-lesson and per-module stats
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{lesson_id}/analytics")
async def lesson_analytics(
    lesson_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Analytics for a single lesson: completions, avg time, quiz scores."""
    _require_teacher(user)
    lesson = await _get_lesson_or_404(lesson_id, db)
    _require_lesson_owner(lesson, user)

    result = await db.execute(
        select(
            func.count(LessonCompletion.id).label("total_completions"),
            func.avg(LessonCompletion.time_spent_seconds).label("avg_time_seconds"),
            func.avg(LessonCompletion.quiz_score).label("avg_quiz_score"),
            func.min(LessonCompletion.completed_at).label("first_completion"),
            func.max(LessonCompletion.completed_at).label("last_completion"),
        ).where(LessonCompletion.lesson_id == lesson_id)
    )
    row = result.one()

    # Recent completions (last 20)
    recent_result = await db.execute(
        select(LessonCompletion).where(LessonCompletion.lesson_id == lesson_id)
        .order_by(LessonCompletion.completed_at.desc()).limit(20)
    )
    recent = recent_result.scalars().all()

    return {
        "lesson_id": str(lesson_id),
        "title": lesson.title,
        "status": lesson.status,
        "total_completions": row.total_completions or 0,
        "avg_time_seconds": round(float(row.avg_time_seconds), 1) if row.avg_time_seconds else None,
        "avg_quiz_score": round(float(row.avg_quiz_score), 1) if row.avg_quiz_score else None,
        "first_completion": row.first_completion.isoformat() if row.first_completion else None,
        "last_completion": row.last_completion.isoformat() if row.last_completion else None,
        "recent_completions": [
            {
                "user_id": str(c.user_id),
                "time_spent_seconds": c.time_spent_seconds,
                "quiz_score": float(c.quiz_score) if c.quiz_score is not None else None,
                "quiz_attempts": c.quiz_attempts,
                "completed_at": c.completed_at.isoformat() if c.completed_at else None,
            }
            for c in recent
        ],
    }


@router.get("/modules/{module_id}/analytics")
async def get_module_analytics(
    module_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Per-lesson engagement analytics for a module.
    Returns completion rates, avg time spent, student count, drop-off points.
    Teacher sees only their own modules; admins see all.
    """
    _require_teacher(user)

    # Verify ownership
    mod_result = await db.execute(select(Module).where(Module.id == module_id))
    mod = mod_result.scalar_one_or_none()
    if not mod:
        raise HTTPException(404, "Module not found")
    if user.role != "admin" and str(mod.author_id) != str(user.id):
        raise HTTPException(403, "Not your module")

    # All lessons in this module
    lessons_result = await db.execute(
        select(Lesson)
        .where(Lesson.module_id == module_id)
        .order_by(Lesson.lesson_order)
    )
    lessons = lessons_result.scalars().all()

    # UserProgress rows for this module
    prog_result = await db.execute(
        select(UserProgress).where(UserProgress.module_id == module_id)
    )
    progressions = prog_result.scalars().all()

    total_students = len(progressions)

    lesson_stats = []
    for lesson in lessons:
        lesson_id_str = str(lesson.id)

        # Count how many students completed this lesson
        completions = sum(
            1 for p in progressions
            if lesson.id in (p.lessons_completed or [])
        )

        completion_rate = round(completions / total_students * 100, 1) if total_students > 0 else 0.0

        lesson_stats.append({
            "lesson_id": lesson_id_str,
            "title": lesson.title,
            "lesson_order": lesson.lesson_order,
            "status": lesson.status,
            "completions": completions,
            "completion_rate": completion_rate,
            "estimated_minutes": lesson.estimated_minutes,
        })

    # Drop-off point: first lesson with completion_rate < 60% of previous
    drop_off_lesson_id = None
    for i in range(1, len(lesson_stats)):
        prev = lesson_stats[i - 1]["completion_rate"]
        curr = lesson_stats[i]["completion_rate"]
        if prev > 0 and curr < prev * 0.6:  # >40% drop
            drop_off_lesson_id = lesson_stats[i]["lesson_id"]
            break

    return {
        "module_id": str(module_id),
        "module_title": mod.title,
        "total_students": total_students,
        "lessons": lesson_stats,
        "drop_off_lesson_id": drop_off_lesson_id,
        "avg_completion_rate": round(
            sum(s["completion_rate"] for s in lesson_stats) / len(lesson_stats), 1
        ) if lesson_stats else 0.0,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Lesson version history
# ─────────────────────────────────────────────────────────────────────────────

class VersionOut(BaseModel):
    id: UUID
    lesson_id: UUID
    version_number: int
    title: str
    saved_at: datetime
    note: Optional[str]
    model_config = {"from_attributes": True}


@router.get("/{lesson_id}/versions", response_model=list[VersionOut])
async def list_versions(
    lesson_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List saved versions of a lesson (newest first)."""
    _require_teacher(user)
    lesson = await _get_lesson_or_404(lesson_id, db)
    _require_lesson_owner(lesson, user)

    result = await db.execute(
        select(LessonVersion)
        .where(LessonVersion.lesson_id == lesson_id)
        .order_by(LessonVersion.version_number.desc())
        .limit(50)
    )
    return result.scalars().all()


@router.get("/{lesson_id}/versions/{version_number}")
async def get_version(
    lesson_id: UUID,
    version_number: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get the full content of a specific version."""
    _require_teacher(user)
    lesson = await _get_lesson_or_404(lesson_id, db)
    _require_lesson_owner(lesson, user)

    result = await db.execute(
        select(LessonVersion).where(
            LessonVersion.lesson_id == lesson_id,
            LessonVersion.version_number == version_number,
        )
    )
    ver = result.scalar_one_or_none()
    if not ver:
        raise HTTPException(404, "Version not found")
    return {"version_number": ver.version_number, "title": ver.title, "content": ver.content,
            "saved_at": ver.saved_at.isoformat(), "note": ver.note}


@router.post("/{lesson_id}/versions/{version_number}/restore", response_model=LessonOut)
async def restore_version(
    lesson_id: UUID,
    version_number: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Restore a previous version as the current lesson content (saves current as a new version first)."""
    _require_teacher(user)
    lesson = await _get_lesson_or_404(lesson_id, db)
    _require_lesson_owner(lesson, user)

    if lesson.status == "archived":
        raise HTTPException(400, "Cannot restore version of an archived lesson")

    result = await db.execute(
        select(LessonVersion).where(
            LessonVersion.lesson_id == lesson_id,
            LessonVersion.version_number == version_number,
        )
    )
    ver = result.scalar_one_or_none()
    if not ver:
        raise HTTPException(404, "Version not found")

    # Save current as a new version before restoring
    max_ver_result = await db.execute(
        select(func.max(LessonVersion.version_number)).where(LessonVersion.lesson_id == lesson_id)
    )
    next_ver = (max_ver_result.scalar() or 0) + 1
    snapshot = LessonVersion(
        lesson_id=lesson_id,
        version_number=next_ver,
        title=lesson.title,
        content=lesson.content,
        saved_by=user.id,
        note=f"Auto-saved before restoring v{version_number}",
    )
    db.add(snapshot)

    lesson.title = ver.title
    lesson.content = ver.content
    lesson.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(lesson)
    await audit(db, "lesson_version_restored", user_id=user.id, resource_id=lesson_id)
    return lesson


@router.post("/generate", response_model=LessonOut, status_code=201)
async def generate_lesson(
    module_id_q: UUID = Query(..., alias="module_id"),
    body: AIGenerateRequest = ...,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Generate a complete lesson from scratch using AI and save it as a draft."""
    _require_teacher(user)
    mod = await _get_module_or_404(module_id_q, db)
    _require_module_owner(mod, user)

    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(503, "AI service not configured")

    concepts_str = ", ".join(body.key_concepts) if body.key_concepts else body.title

    optional_blocks = ""
    if body.include_quiz:
        optional_blocks += (
            "\n- 2–3 quiz blocks (type='quiz') with question, options (A-D), correct, explanation"
        )
    if body.include_clinical_case:
        optional_blocks += (
            "\n- 1 clinical case block (type='case') with patient presentation, questions, teaching_points"
        )

    prompt = (
        f"You are a medical education expert. Generate a complete, evidence-based lesson.\n\n"
        f"Title: {body.title}\n"
        f"Specialty: {body.specialty}\n"
        f"Key concepts to cover: {concepts_str}\n"
        f"Target student level: {body.target_level}\n"
        f"Estimated duration: {body.estimated_minutes} minutes\n\n"
        f"Return ONLY valid JSON with this exact structure:\n"
        f'{{\n'
        f'  "title": "{body.title}",\n'
        f'  "learning_objectives": ["...", "..."],\n'
        f'  "estimated_minutes": {body.estimated_minutes},\n'
        f'  "blocks": [\n'
        f'    {{"type": "text", "order": 0, "content": {{"text": "..."}}}},\n'
        f'    {{"type": "text", "order": 1, "content": {{"heading": "...", "text": "..."}}}}'
        f"{optional_blocks}\n"
        f"  ]\n"
        f"}}\n\n"
        f"Requirements:\n"
        f"- Minimum 4 text blocks covering introduction, pathophysiology/mechanism, clinical relevance, management\n"
        f"- Content must be accurate and based on current clinical guidelines\n"
        f"- Language appropriate for {body.target_level} level\n"
        f"- Return ONLY the JSON, no markdown, no extra text"
    )

    import re
    try:
        response = await _claude.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=6000,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        raw = response.content[0].text if response.content else "{}"
        raw = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
        try:
            content_data = json.loads(raw)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            content_data = json.loads(m.group()) if m else {}

        if not isinstance(content_data, dict) or "blocks" not in content_data:
            raise HTTPException(502, "AI returned unexpected format")

        # Count existing lessons for order
        result = await db.execute(
            select(Lesson).where(Lesson.module_id == module_id_q).order_by(Lesson.lesson_order.desc()).limit(1)
        )
        last = result.scalar_one_or_none()
        next_order = (last.lesson_order + 1) if last else 0

        lesson = Lesson(
            module_id=module_id_q,
            title=content_data.get("title", body.title),
            content=content_data,
            estimated_minutes=content_data.get("estimated_minutes", body.estimated_minutes),
            lesson_order=next_order,
            author_id=user.id,
            status="draft",
        )
        db.add(lesson)
        await db.commit()
        await db.refresh(lesson)
        await audit(db, "lesson_ai_generated", user_id=user.id, resource_id=lesson.id)
        return lesson

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, f"AI generation error: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# Course export / import (JSON portable format)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/modules/{module_id}/export")
async def export_module(
    module_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Export a complete module (metadata + all lessons + flashcards + MCQs) as JSON.
    Suitable for backup or importing into another MedMind instance.
    """
    _require_teacher(user)

    mod_result = await db.execute(select(Module).where(Module.id == module_id))
    mod = mod_result.scalar_one_or_none()
    if not mod:
        raise HTTPException(404, "Module not found")
    if user.role != "admin" and str(mod.author_id) != str(user.id):
        raise HTTPException(403, "Not your module")

    lessons_result = await db.execute(
        select(Lesson).where(Lesson.module_id == module_id).order_by(Lesson.lesson_order)
    )
    lessons = lessons_result.scalars().all()

    fc_result = await db.execute(
        select(Flashcard).where(Flashcard.module_id == module_id)
    )
    flashcards = fc_result.scalars().all()

    mcq_result = await db.execute(
        select(MCQQuestion).where(MCQQuestion.module_id == module_id)
    )
    mcqs = mcq_result.scalars().all()

    payload = {
        "format": "medmind_course_v1",
        "exported_at": datetime.utcnow().isoformat(),
        "module": {
            "code": mod.code,
            "title": mod.title,
            "description": mod.description,
            "difficulty": mod.difficulty,
            "estimated_hours": mod.estimated_hours,
            "is_fundamental": mod.is_fundamental,
        },
        "lessons": [
            {
                "title": l.title,
                "lesson_order": l.lesson_order,
                "estimated_minutes": l.estimated_minutes,
                "content": l.content,
            }
            for l in lessons if l.status != "archived"
        ],
        "flashcards": [
            {
                "question": f.question,
                "answer": f.answer,
                "difficulty": f.difficulty,
                "tags": f.tags or [],
            }
            for f in flashcards
        ],
        "mcq_questions": [
            {
                "question": q.question,
                "options": q.options,
                "correct": q.correct,
                "explanation": q.explanation,
                "difficulty": q.difficulty,
            }
            for q in mcqs
        ],
    }

    from fastapi.responses import JSONResponse
    filename = f"medmind_{mod.code or str(module_id)[:8]}_{datetime.utcnow().strftime('%Y%m%d')}.json"
    return JSONResponse(
        content=payload,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/modules/import")
async def import_module(
    specialty_id: UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Import a module from a previously exported JSON payload.
    Creates a new module in draft status owned by the current teacher.
    """
    _require_teacher(user)

    if body.get("format") != "medmind_course_v1":
        raise HTTPException(400, "Invalid format. Expected medmind_course_v1")

    mod_data = body.get("module", {})
    if not mod_data.get("title"):
        raise HTTPException(400, "Module title is required")

    # Create module
    import uuid as _uuid_mod
    new_mod = Module(
        id=_uuid_mod.uuid4(),
        specialty_id=specialty_id,
        author_id=user.id,
        code=mod_data.get("code", f"IMPORT-{_uuid_mod.uuid4().hex[:6].upper()}"),
        title=mod_data["title"],
        description=mod_data.get("description", ""),
        difficulty=mod_data.get("difficulty", "intermediate"),
        estimated_hours=mod_data.get("estimated_hours", 1),
        is_fundamental=mod_data.get("is_fundamental", False),
        is_published=False,
    )
    db.add(new_mod)
    await db.flush()

    # Import lessons
    lesson_count = 0
    for l_data in body.get("lessons", []):
        if not l_data.get("title") or not l_data.get("content"):
            continue
        db.add(Lesson(
            module_id=new_mod.id,
            author_id=user.id,
            title=l_data["title"],
            lesson_order=l_data.get("lesson_order", lesson_count),
            estimated_minutes=l_data.get("estimated_minutes", 20),
            content=l_data["content"],
            status="draft",
        ))
        lesson_count += 1

    # Import flashcards
    fc_count = 0
    for f_data in body.get("flashcards", []):
        if not f_data.get("question") or not f_data.get("answer"):
            continue
        db.add(Flashcard(
            module_id=new_mod.id,
            question=f_data["question"],
            answer=f_data["answer"],
            difficulty=f_data.get("difficulty", "medium"),
            tags=f_data.get("tags", []),
        ))
        fc_count += 1

    # Import MCQs
    mcq_count = 0
    for q_data in body.get("mcq_questions", []):
        if not q_data.get("question") or not q_data.get("options") or not q_data.get("correct"):
            continue
        db.add(MCQQuestion(
            module_id=new_mod.id,
            question=q_data["question"],
            options=q_data["options"],
            correct=q_data["correct"],
            explanation=q_data.get("explanation", ""),
            difficulty=q_data.get("difficulty", "medium"),
        ))
        mcq_count += 1

    await db.commit()

    return {
        "module_id": str(new_mod.id),
        "title": new_mod.title,
        "lessons_imported": lesson_count,
        "flashcards_imported": fc_count,
        "mcqs_imported": mcq_count,
        "status": "draft",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Translation management endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{lesson_id}/translations", response_model=TranslationStatusOut)
async def get_translation_status(
    lesson_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get translation status for all locales of a lesson.
    Available to lesson author and admins.
    """
    from app.models.models import LessonTranslation
    lesson = await _get_lesson_or_404(lesson_id, db)
    _require_lesson_owner(lesson, user)

    result = await db.execute(
        select(LessonTranslation).where(LessonTranslation.lesson_id == lesson_id)
    )
    translations = result.scalars().all()

    return {
        "lesson_id": lesson_id,
        "translations": [
            {
                "locale": tr.locale,
                "status": tr.status,
                "reviewed": tr.reviewed,
                "translated_at": tr.translated_at.isoformat() if tr.translated_at else None,
                "error_message": tr.error_message,
            }
            for tr in translations
        ],
    }


@router.post("/{lesson_id}/translations/{locale}/retranslate", status_code=202)
async def retranslate(
    lesson_id: UUID,
    locale: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Force re-translation of a specific locale. Author or admin only."""
    from app.models.models import LessonTranslation, SUPPORTED_LOCALES
    from app.services.translation_service import retranslate_lesson

    _require_teacher(user)
    lesson = await _get_lesson_or_404(lesson_id, db)
    _require_lesson_owner(lesson, user)

    if locale not in SUPPORTED_LOCALES:
        raise HTTPException(400, f"Locale '{locale}' not supported. Supported: {SUPPORTED_LOCALES}")

    # Kick off background retranslation
    import asyncio
    asyncio.create_task(retranslate_lesson(lesson_id, locale, db))

    return {"message": f"Retranslation scheduled for locale '{locale}'", "lesson_id": str(lesson_id)}


@router.patch("/{lesson_id}/translations/{locale}", response_model=LessonTranslationOut)
async def update_translation(
    lesson_id: UUID,
    locale: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Manually edit translation (teacher review). Marks as 'reviewed'.
    Body: {title?: str, content_json?: list}
    """
    from app.models.models import LessonTranslation, SUPPORTED_LOCALES

    _require_teacher(user)
    lesson = await _get_lesson_or_404(lesson_id, db)
    _require_lesson_owner(lesson, user)

    if locale not in SUPPORTED_LOCALES:
        raise HTTPException(400, f"Locale '{locale}' not supported.")

    tr = await db.get(LessonTranslation, (lesson_id, locale))
    if not tr:
        raise HTTPException(404, "Translation not found. Publish the lesson first.")

    if "title" in body and body["title"]:
        tr.title = body["title"]
    if "content_json" in body and body["content_json"]:
        tr.content_json = body["content_json"]

    tr.reviewed = True
    tr.reviewed_by = user.id
    tr.reviewed_at = datetime.utcnow()
    tr.status = "reviewed"
    tr.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(tr)
    return tr


@router.get("/{lesson_id}/translations/{locale}", response_model=LessonTranslationOut)
async def get_translation(
    lesson_id: UUID,
    locale: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get the translation content for a specific locale."""
    from app.models.models import LessonTranslation
    lesson = await _get_lesson_or_404(lesson_id, db)

    tr = await db.get(LessonTranslation, (lesson_id, locale))
    if not tr:
        raise HTTPException(404, f"No translation found for locale '{locale}'")
    return tr
