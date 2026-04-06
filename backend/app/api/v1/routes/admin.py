"""Admin panel API — restricted to users with role='admin'."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.models import (
    Flashcard, Lesson, MCQQuestion, Module, Specialty, User, ClinicalCase,
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
                "email": u.email,
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

    await db.commit()
    await db.refresh(target)
    return {
        "id": str(target.id),
        "email": target.email,
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
