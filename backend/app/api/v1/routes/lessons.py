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
import uuid as _uuid
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

import anthropic
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.audit import audit
from app.core.config import settings
from app.core.database import get_db
from app.models.models import Lesson, Module, Specialty, User

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

class LessonBlock(BaseModel):
    """One content block inside a lesson."""
    type: Literal["text", "image", "video", "quiz", "case", "flashcard", "table"]
    content: dict
    order: int = Field(ge=0)

    model_config = {"extra": "allow"}


class LessonContent(BaseModel):
    """Validated lesson content structure stored as JSONB."""
    title: str = Field(min_length=2, max_length=300)
    blocks: list[LessonBlock] = Field(default_factory=list)
    estimated_minutes: int = Field(default=20, ge=5, le=180)
    learning_objectives: list[str] = Field(default_factory=list)

    model_config = {"extra": "allow"}


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


class LessonUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=2, max_length=300)
    content: Optional[LessonContent] = None
    estimated_minutes: Optional[int] = Field(default=None, ge=5, le=180)
    lesson_order: Optional[int] = Field(default=None, ge=0)
    review_notes: Optional[str] = None


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

    model_config = {"from_attributes": True}


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
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get lesson detail. Drafts visible only to author/admin."""
    lesson = await _get_lesson_or_404(lesson_id, db)

    if lesson.status != "published":
        # Only author or admin can see non-published lessons
        is_owner = user.role == "admin" or (
            lesson.author_id is not None and _same_uuid(lesson.author_id, user.id)
        )
        if not is_owner:
            raise HTTPException(403, "This lesson is not yet published")

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

    if lesson.status == "archived":
        raise HTTPException(400, "Cannot edit an archived lesson")

    data = body.model_dump(exclude_none=True)
    if "content" in data:
        # content is a LessonContent object — convert to dict for JSONB
        data["content"] = body.content.model_dump()
    for field, value in data.items():
        setattr(lesson, field, value)
    lesson.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(lesson)
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
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Publish a lesson (from review status). Author or admin only."""
    _require_teacher(user)
    lesson = await _get_lesson_or_404(lesson_id, db)
    _require_lesson_owner(lesson, user)

    if lesson.status not in ("review", "draft"):
        raise HTTPException(400, f"Cannot publish lesson with status '{lesson.status}'")

    lesson.status = "published"
    lesson.published_at = datetime.utcnow()
    lesson.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(lesson)
    await audit(db, "lesson_published", user_id=user.id, resource_id=lesson_id)
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
        f"Current lesson content (JSON):\n"
        f"{json.dumps(lesson.content, ensure_ascii=False, indent=2)}\n\n"
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
# AI lesson generation from scratch
# ─────────────────────────────────────────────────────────────────────────────

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
