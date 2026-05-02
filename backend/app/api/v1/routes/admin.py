"""Admin panel API — restricted to users with role='admin'."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
import json

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import func, select, update, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.core.encryption import decrypt_email
from app.models.models import (
    Article, Flashcard, Lesson, MCQQuestion, Module, Specialty, User, ClinicalCase,
    AuditLog, LessonTranslation, SUPPORTED_LOCALES,
)

router = APIRouter(prefix="/admin", tags=["admin"])

_admin = Depends(require_admin())


# ── Schemas ───────────────────────────────────────────────────────────────────

class UserPatch(BaseModel):
    subscription_tier: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None


class ModulePatch(BaseModel):
    is_published: Optional[bool] = None
    is_fundamental: Optional[bool] = None
    title: Optional[str] = None


# ── Platform stats ─────────────────────────────────────────────────────────

@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    active_users = (await db.execute(select(func.count(User.id)).where(User.is_active == True))).scalar() or 0
    total_modules = (await db.execute(select(func.count(Module.id)))).scalar() or 0
    published_modules = (await db.execute(select(func.count(Module.id)).where(Module.is_published == True))).scalar() or 0
    total_flashcards = (await db.execute(select(func.count(Flashcard.id)))).scalar() or 0
    total_lessons = (await db.execute(select(func.count(Lesson.id)))).scalar() or 0
    total_mcq = (await db.execute(select(func.count(MCQQuestion.id)))).scalar() or 0
    total_cases = (await db.execute(select(func.count(ClinicalCase.id)))).scalar() or 0
    total_articles = (await db.execute(select(func.count(Article.id)))).scalar() or 0
    published_articles = (await db.execute(select(func.count(Article.id)).where(Article.is_published == True))).scalar() or 0
    pending_articles = (await db.execute(select(func.count(Article.id)).where(Article.review_status == "pending_review"))).scalar() or 0

    # Users by subscription tier
    tier_rows = await db.execute(
        select(User.subscription_tier, func.count(User.id))
        .group_by(User.subscription_tier)
    )
    tiers = {row[0]: row[1] for row in tier_rows}

    # New users last 7 days
    seven_days_ago = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    from datetime import timedelta
    seven_days_ago = seven_days_ago - timedelta(days=7)
    new_users_week = (
        await db.execute(
            select(func.count(User.id)).where(User.created_at >= seven_days_ago)
        )
    ).scalar() or 0

    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "new_last_7_days": new_users_week,
            "by_tier": tiers,
        },
        "content": {
            "modules_total": total_modules,
            "modules_published": published_modules,
            "lessons": total_lessons,
            "flashcards": total_flashcards,
            "mcq": total_mcq,
            "cases": total_cases,
        },
        "articles": {
            "total": total_articles,
            "published": published_articles,
            "pending_review": pending_articles,
        },
    }


# ── Users ─────────────────────────────────────────────────────────────────────

@router.get("/users")
async def list_users(
    search: Optional[str] = Query(None),
    tier: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    q = select(User)
    if search:
        like = f"%{search.lower()}%"
        from sqlalchemy import or_
        q = q.where(or_(User.email.ilike(like), User.first_name.ilike(like), User.last_name.ilike(like)))
    if tier:
        q = q.where(User.subscription_tier == tier)
    q = q.order_by(User.created_at.desc()).offset((page - 1) * limit).limit(limit)
    rows = (await db.execute(q)).scalars().all()

    total_q = select(func.count(User.id))
    if search:
        like = f"%{search.lower()}%"
        from sqlalchemy import or_
        total_q = total_q.where(or_(User.email.ilike(like), User.first_name.ilike(like), User.last_name.ilike(like)))
    if tier:
        total_q = total_q.where(User.subscription_tier == tier)
    total = (await db.execute(total_q)).scalar() or 0

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "users": [
            {
                "id": str(u.id),
                "email": decrypt_email(u.email),
                "first_name": u.first_name,
                "last_name": u.last_name,
                "role": u.role,
                "subscription_tier": u.subscription_tier,
                "is_active": u.is_active,
                "xp": u.xp,
                "level": u.level,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in rows
        ],
    }


@router.patch("/users/{user_id}")
async def patch_user(
    user_id: UUID,
    data: UserPatch,
    db: AsyncSession = Depends(get_db),
    admin: User = _admin,
):
    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if str(target.id) == str(admin.id):
        raise HTTPException(status_code=400, detail="Cannot modify your own account")

    VALID_TIERS = {"free", "student", "pro", "clinic", "lifetime"}
    VALID_ROLES = {"student", "teacher", "doctor", "admin"}

    if data.subscription_tier is not None:
        if data.subscription_tier not in VALID_TIERS:
            raise HTTPException(status_code=400, detail=f"Invalid tier. Valid: {VALID_TIERS}")
        target.subscription_tier = data.subscription_tier
    if data.is_active is not None:
        target.is_active = data.is_active
    if data.role is not None:
        if data.role not in VALID_ROLES:
            raise HTTPException(status_code=400, detail=f"Invalid role. Valid: {VALID_ROLES}")
        target.role = data.role

    db.add(AuditLog(
        user_id=admin.id,
        action="admin_user_patch",
        resource_type="user",
        resource_id=target.id,
    ))
    await db.commit()
    await db.refresh(target)
    return {
        "id": str(target.id),
        "email": decrypt_email(target.email),
        "role": target.role,
        "subscription_tier": target.subscription_tier,
        "is_active": target.is_active,
    }


# ── Modules ───────────────────────────────────────────────────────────────────

@router.get("/modules")
async def list_modules_admin(
    search: Optional[str] = Query(None),
    specialty: Optional[str] = Query(None),
    published: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    q = select(Module, Specialty.name.label("specialty_name")).join(
        Specialty, Specialty.id == Module.specialty_id, isouter=True
    )
    if search:
        like = f"%{search.lower()}%"
        q = q.where(Module.title.ilike(like))
    if specialty:
        q = q.where(Specialty.code == specialty)
    if published is not None:
        q = q.where(Module.is_published == published)
    q = q.order_by(Module.code).offset((page - 1) * limit).limit(limit)

    rows = (await db.execute(q)).all()
    module_ids = [row[0].id for row in rows]

    # Batch count queries — 4 queries total regardless of module count
    lesson_counts: dict = {}
    flash_counts: dict = {}
    mcq_counts: dict = {}
    case_counts: dict = {}
    if module_ids:
        for counts_dict, model, col in [
            (lesson_counts, Lesson, Lesson.module_id),
            (flash_counts, Flashcard, Flashcard.module_id),
            (mcq_counts, MCQQuestion, MCQQuestion.module_id),
            (case_counts, ClinicalCase, ClinicalCase.module_id),
        ]:
            result = await db.execute(
                select(col, func.count().label("cnt"))
                .where(col.in_(module_ids))
                .group_by(col)
            )
            for r in result.all():
                counts_dict[r[0]] = r[1]

    modules_out = []
    for row in rows:
        mod = row[0]
        spec_name = row[1]
        modules_out.append(
            {
                "id": str(mod.id),
                "code": mod.code,
                "title": mod.title,
                "specialty": spec_name,
                "level": mod.level,
                "is_published": mod.is_published,
                "is_fundamental": mod.is_fundamental,
                "is_veterinary": mod.is_veterinary,
                "lessons": lesson_counts.get(mod.id, 0),
                "flashcards": flash_counts.get(mod.id, 0),
                "mcq": mcq_counts.get(mod.id, 0),
                "cases": case_counts.get(mod.id, 0),
                "created_at": mod.created_at.isoformat() if mod.created_at else None,
            }
        )

    return {"total": len(modules_out), "modules": modules_out}


@router.patch("/modules/{module_id}")
async def patch_module(
    module_id: UUID,
    data: ModulePatch,
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    result = await db.execute(select(Module).where(Module.id == module_id))
    mod = result.scalar_one_or_none()
    if not mod:
        raise HTTPException(status_code=404, detail="Module not found")

    if data.is_published is not None:
        mod.is_published = data.is_published
    if data.is_fundamental is not None:
        mod.is_fundamental = data.is_fundamental
    if data.title is not None and data.title.strip():
        mod.title = data.title.strip()

    await db.commit()
    await db.refresh(mod)
    return {"id": str(mod.id), "code": mod.code, "title": mod.title, "is_published": mod.is_published, "is_fundamental": mod.is_fundamental}


# ── Bulk publish/unpublish ────────────────────────────────────────────────────

@router.post("/modules/bulk-publish")
async def bulk_publish(
    data: dict,
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    """Bulk publish or unpublish modules. Body: {ids: [...], publish: bool}"""
    ids = data.get("ids", [])
    publish = bool(data.get("publish", True))
    if not ids:
        raise HTTPException(status_code=400, detail="No module IDs given")
    await db.execute(
        update(Module).where(Module.id.in_(ids)).values(is_published=publish)
    )
    await db.commit()
    return {"updated": len(ids), "is_published": publish}


# ── Generate module via Claude API ────────────────────────────────────────────

class GenerateModuleRequest(BaseModel):
    specialty: str
    topic: str
    level: int = 2  # 1-5
    auto_publish: bool = False


@router.post("/modules/generate")
async def generate_module(
    req: GenerateModuleRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = _admin,
):
    """Generate a new module via Claude API and optionally publish it."""
    import anthropic
    from app.core.config import settings
    from app.prompts.content_prompts import generate_full_module

    level_labels = {1: "beginner", 2: "intermediate", 3: "advanced", 4: "expert", 5: "master"}
    level_str = level_labels.get(req.level, "intermediate")

    prompt = generate_full_module(req.specialty, req.topic, level_str)

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Claude API error: {str(e)}")

    # Extract JSON from response
    import re
    json_match = re.search(r'\{.*\}', raw, re.DOTALL)
    if not json_match:
        raise HTTPException(status_code=422, detail="Claude did not return valid JSON")

    try:
        module_data = json.loads(json_match.group())
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"JSON parse error: {str(e)}")

    meta = module_data.get("meta", {})
    code = meta.get("id", f"GEN-{req.specialty[:4].upper()}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")

    # Check code uniqueness
    existing = (await db.execute(select(Module).where(Module.code == code))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail=f"Module with code {code} already exists")

    # Find or create specialty
    spec_result = await db.execute(
        select(Specialty).where(Specialty.name.ilike(f"%{req.specialty}%"))
    )
    specialty = spec_result.scalar_one_or_none()
    if not specialty:
        specialty = Specialty(
            code=req.specialty[:20].lower().replace(" ", "_"),
            name=req.specialty,
            name_en=req.specialty,
        )
        db.add(specialty)
        await db.flush()

    mod = Module(
        code=code,
        specialty_id=specialty.id,
        title=meta.get("title", req.topic),
        level=req.level,
        duration_hours=meta.get("duration_hours", 1.0),
        is_fundamental=False,
        is_published=req.auto_publish,
        content=module_data,
    )
    db.add(mod)
    await db.flush()

    # Import lessons, flashcards, mcq, cases
    for i, lesson_data in enumerate(module_data.get("lessons", []), 1):
        lesson = Lesson(
            module_id=mod.id,
            title=lesson_data.get("title", f"Lesson {i}"),
            order=lesson_data.get("order", i),
            content=lesson_data,
            estimated_minutes=int(lesson_data.get("duration_minutes", 20)),
        )
        db.add(lesson)

    for fc_data in module_data.get("flashcards", []):
        fc = Flashcard(
            module_id=mod.id,
            question=fc_data.get("question", ""),
            answer=fc_data.get("answer", ""),
            difficulty=fc_data.get("difficulty", "medium"),
            category=fc_data.get("category", ""),
        )
        db.add(fc)

    for mcq_data in module_data.get("mcq_questions", []):
        mcq = MCQQuestion(
            module_id=mod.id,
            question=mcq_data.get("question", ""),
            options=mcq_data.get("options", {}),
            correct_answer=mcq_data.get("correct", "A"),
            explanation=mcq_data.get("explanation", ""),
            difficulty=mcq_data.get("difficulty", "medium"),
        )
        db.add(mcq)

    for case_data in module_data.get("clinical_cases", []):
        case = ClinicalCase(
            module_id=mod.id,
            title=case_data.get("title", "Clinical Case"),
            presentation=case_data.get("presentation", ""),
            diagnosis=case_data.get("diagnosis", ""),
            management=case_data.get("management", []),
            teaching_points=case_data.get("teaching_points", []),
        )
        db.add(case)

    # Audit log
    log = AuditLog(
        user_id=admin.id,
        action="module_generated",
        resource_type="module",
        resource_id=mod.id,
    )
    db.add(log)

    await db.commit()
    return {
        "id": str(mod.id),
        "code": mod.code,
        "title": mod.title,
        "is_published": mod.is_published,
        "lessons": len(module_data.get("lessons", [])),
        "flashcards": len(module_data.get("flashcards", [])),
        "mcq": len(module_data.get("mcq_questions", [])),
        "cases": len(module_data.get("clinical_cases", [])),
    }


# ── Import module from JSON file ───────────────────────────────────────────────

@router.post("/modules/import")
async def import_module_json(
    file: UploadFile = File(...),
    auto_publish: bool = False,
    db: AsyncSession = Depends(get_db),
    admin: User = _admin,
):
    """Upload a module_*.json file and import it into the database."""
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .json files are accepted")

    content = await file.read()
    try:
        module_data = json.loads(content)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {str(e)}")

    meta = module_data.get("meta", {})
    code = meta.get("id")
    if not code:
        raise HTTPException(status_code=422, detail="JSON must have meta.id field")

    existing = (await db.execute(select(Module).where(Module.code == code))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail=f"Module {code} already exists. Use PATCH to update.")

    specialty_name = meta.get("specialty", "General")
    spec_result = await db.execute(
        select(Specialty).where(Specialty.name.ilike(f"%{specialty_name}%"))
    )
    specialty = spec_result.scalar_one_or_none()
    if not specialty:
        # Map common names
        SPECIALTY_MAP = {
            "Cardiology": "cardiology", "Therapy": "therapy",
            "Neurology": "neurology", "Surgery": "surgery",
            "Pediatrics": "pediatrics", "Obstetrics": "obstetrics",
            "Veterinary": "veterinary", "Psychiatry": "psychiatry",
            "Anesthesiology": "anesthesiology", "Oncology": "oncology",
            "Dermatology": "dermatology",
        }
        code_key = SPECIALTY_MAP.get(specialty_name, specialty_name[:20].lower().replace(" ", "_"))
        specialty = Specialty(
            code=code_key,
            name=specialty_name,
            name_en=specialty_name,
        )
        db.add(specialty)
        await db.flush()

    mod = Module(
        code=code,
        specialty_id=specialty.id,
        title=meta.get("title", code),
        level=int(meta.get("level", 2)),
        duration_hours=float(meta.get("duration_hours", 1.0)),
        is_fundamental=code.startswith("BASE-"),
        is_veterinary=specialty_name.lower() == "veterinary" or code.startswith("VET-"),
        is_published=auto_publish,
        content=module_data,
    )
    db.add(mod)
    await db.flush()

    lesson_ids = {}
    for i, lesson_data in enumerate(module_data.get("lessons", []), 1):
        lesson = Lesson(
            module_id=mod.id,
            title=lesson_data.get("title", f"Lesson {i}"),
            order=lesson_data.get("order", i),
            content=lesson_data,
            estimated_minutes=int(lesson_data.get("duration_minutes", 20)),
        )
        db.add(lesson)
        await db.flush()
        lesson_ids[lesson_data.get("id", f"L{i:03d}")] = lesson.id

    for fc_data in module_data.get("flashcards", []):
        db.add(Flashcard(
            module_id=mod.id,
            question=fc_data.get("question", ""),
            answer=fc_data.get("answer", ""),
            difficulty=fc_data.get("difficulty", "medium"),
            category=fc_data.get("category", ""),
        ))

    for mcq_data in module_data.get("mcq_questions", []):
        db.add(MCQQuestion(
            module_id=mod.id,
            question=mcq_data.get("question", ""),
            options=mcq_data.get("options", {}),
            correct_answer=mcq_data.get("correct", "A"),
            explanation=mcq_data.get("explanation", ""),
            difficulty=mcq_data.get("difficulty", "medium"),
        ))

    for case_data in module_data.get("clinical_cases", []):
        db.add(ClinicalCase(
            module_id=mod.id,
            title=case_data.get("title", "Clinical Case"),
            presentation=case_data.get("presentation", ""),
            diagnosis=case_data.get("diagnosis", ""),
            management=case_data.get("management", []),
            teaching_points=case_data.get("teaching_points", []),
        ))

    db.add(AuditLog(
        user_id=admin.id,
        action="module_imported",
        resource_type="module",
        resource_id=mod.id,
    ))

    await db.commit()
    return {
        "id": str(mod.id),
        "code": mod.code,
        "title": mod.title,
        "is_published": mod.is_published,
        "lessons": len(module_data.get("lessons", [])),
        "flashcards": len(module_data.get("flashcards", [])),
        "mcq": len(module_data.get("mcq_questions", [])),
        "cases": len(module_data.get("clinical_cases", [])),
    }


# ── Audit logs ─────────────────────────────────────────────────────────────────

@router.get("/audit-logs")
async def get_audit_logs(
    user_id: Optional[UUID] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    """List audit log entries with filters."""
    q = select(AuditLog).order_by(desc(AuditLog.created_at))

    if user_id:
        q = q.where(AuditLog.user_id == user_id)
    if action:
        q = q.where(AuditLog.action.ilike(f"%{action}%"))
    if resource_type:
        q = q.where(AuditLog.resource_type == resource_type)
    if date_from:
        try:
            q = q.where(AuditLog.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            q = q.where(AuditLog.created_at <= datetime.fromisoformat(date_to))
        except ValueError:
            pass

    total = (await db.execute(
        select(func.count(AuditLog.id)).where(
            *(
                ([AuditLog.user_id == user_id] if user_id else [])
                + ([AuditLog.action.ilike(f"%{action}%")] if action else [])
                + ([AuditLog.resource_type == resource_type] if resource_type else [])
            )
        )
    )).scalar() or 0

    q = q.offset((page - 1) * limit).limit(limit)
    rows = (await db.execute(q)).scalars().all()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "logs": [
            {
                "id": str(r.id),
                "user_id": str(r.user_id) if r.user_id else None,
                "action": r.action,
                "resource_type": r.resource_type,
                "resource_id": str(r.resource_id) if r.resource_id else None,
                "ip_address": r.ip_address,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }


# ── Feature Flags ────────────────────────────────────────────────────────────
@router.get("/feature-flags", tags=["admin"])
async def get_feature_flags(
    _: User = _admin,
):
    """List all feature flags with current values."""
    from app.core.feature_flags import list_flags
    return await list_flags()


@router.patch("/feature-flags/{flag}", tags=["admin"])
async def set_feature_flag(
    flag: str,
    enabled: bool,
    rollout: int = 100,
    _: User = _admin,
):
    """Enable/disable a feature flag, optionally with % rollout."""
    from app.core.feature_flags import set_flag, DEFAULTS
    if flag not in DEFAULTS:
        raise HTTPException(status_code=404, detail=f"Unknown flag: {flag}")
    await set_flag(flag, enabled, rollout)
    return {"flag": flag, "enabled": enabled, "rollout": rollout}


# ── Translation stats ──────────────────────────────────────────────────────────

@router.get("/translations/stats")
async def get_translation_stats(
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    """Per-locale translation coverage: total published lessons vs translated."""
    total_published = (
        await db.execute(select(func.count(Lesson.id)).where(Lesson.status == "published"))
    ).scalar() or 0

    # Per-locale counts grouped by status
    rows = await db.execute(
        select(
            LessonTranslation.locale,
            LessonTranslation.status,
            func.count().label("cnt"),
        ).group_by(LessonTranslation.locale, LessonTranslation.status)
    )

    # Build a dict: {locale: {status: count}}
    per_locale: Dict[str, Dict[str, int]] = {loc: {} for loc in SUPPORTED_LOCALES}
    for row in rows.all():
        if row.locale in per_locale:
            per_locale[row.locale][row.status] = row.cnt

    # Recent failures (last 20)
    failed_rows = await db.execute(
        select(LessonTranslation, Lesson.title.label("lesson_title"))
        .join(Lesson, Lesson.id == LessonTranslation.lesson_id)
        .where(LessonTranslation.status == "failed")
        .order_by(LessonTranslation.updated_at.desc())
        .limit(20)
    )
    failed = [
        {
            "lesson_id": str(r.LessonTranslation.lesson_id),
            "lesson_title": r.lesson_title,
            "locale": r.LessonTranslation.locale,
            "error": r.LessonTranslation.error_message,
        }
        for r in failed_rows.all()
    ]

    locales_out = []
    for locale in SUPPORTED_LOCALES:
        stats = per_locale.get(locale, {})
        done = stats.get("done", 0) + stats.get("reviewed", 0)
        locales_out.append({
            "locale": locale,
            "done": done,
            "pending": stats.get("pending", 0),
            "translating": stats.get("translating", 0),
            "failed": stats.get("failed", 0),
            "coverage_pct": round(done / total_published * 100, 1) if total_published else 0,
        })

    return {
        "total_published_lessons": total_published,
        "locales": locales_out,
        "recent_failures": failed,
    }


@router.post("/translations/retranslate-failed")
async def retranslate_all_failed(
    locale: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    """Re-queue all failed translations (optionally filtered by locale)."""
    import asyncio

    q = select(LessonTranslation.lesson_id).where(LessonTranslation.status == "failed").distinct()
    if locale:
        q = q.where(LessonTranslation.locale == locale)
    lesson_ids = (await db.execute(q)).scalars().all()

    if not lesson_ids:
        return {"queued": 0}

    # Reset status to pending
    from sqlalchemy import update as sa_update
    update_q = sa_update(LessonTranslation).where(LessonTranslation.status == "failed")
    if locale:
        update_q = update_q.where(LessonTranslation.locale == locale)
    await db.execute(update_q.values(status="pending", error_message=None))
    await db.commit()

    # Fire background tasks — use internal worker directly (opens its own DB session)
    from app.services.translation_service import _translate_lesson_all_locales
    for lesson_id in lesson_ids:
        asyncio.create_task(_translate_lesson_all_locales(lesson_id))

    return {"queued": len(lesson_ids)}


# ── System health ─────────────────────────────────────────────────────────────

@router.get("/system/health")
async def system_health(
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    """Check health of all connected services."""
    import httpx
    from app.core.config import settings
    from app.core.redis_client import get_redis

    result: Dict[str, Any] = {}

    # Database
    try:
        await db.execute(select(func.count(User.id)))
        result["database"] = "ok"
    except Exception as e:
        result["database"] = f"error: {str(e)[:80]}"

    # Redis
    try:
        redis = await get_redis()
        await redis.ping()
        info = await redis.info("memory")
        result["redis"] = {
            "status": "ok",
            "used_memory": info.get("used_memory_human", "?"),
        }
    except Exception as e:
        result["redis"] = {"status": f"error: {str(e)[:80]}"}

    # Ollama
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(f"{settings.OLLAMA_URL}/api/tags")
            if r.status_code == 200:
                models = [m["name"] for m in r.json().get("models", [])]
                result["ollama"] = {
                    "status": "ok",
                    "url": settings.OLLAMA_URL,
                    "model": settings.OLLAMA_MODEL,
                    "loaded_models": models,
                    "model_available": settings.OLLAMA_MODEL in models,
                }
            else:
                result["ollama"] = {"status": f"http {r.status_code}"}
    except Exception as e:
        result["ollama"] = {"status": f"unreachable: {str(e)[:80]}"}

    # Anthropic
    result["anthropic"] = "configured" if settings.ANTHROPIC_API_KEY else "not configured"
    result["gemini"] = "configured" if settings.GEMINI_API_KEY else "not configured"
    result["groq"] = "configured" if settings.GROQ_API_KEY else "not configured"

    # Stripe
    result["stripe"] = "configured" if settings.STRIPE_SECRET_KEY else "not configured"

    # SMTP
    result["smtp"] = "configured" if settings.SMTP_USER else "not configured"

    return result
