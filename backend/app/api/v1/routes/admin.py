"""Admin panel API — restricted to users with role='admin'."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
import json

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import func, select, update, desc, Integer, cast, text, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin, require_reviewer
from app.core.database import get_db
from app.core.encryption import decrypt_email
from app.models.models import (
    Article, ContentFeedback, Flashcard, Lesson, MCQQuestion, Module, Reviewer,
    Specialty, User, ClinicalCase,
    AuditLog, LessonTranslation, AIConversation, SUPPORTED_LOCALES, MedicalImage, Drug,
    StripeEvent, CreditTransaction, AuthorCreditAccount,
)

router = APIRouter(prefix="/admin", tags=["admin"])

_admin = Depends(require_admin())


# ── Schemas ───────────────────────────────────────────────────────────────────

class UserPatch(BaseModel):
    subscription_tier: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None
    is_verified_teacher: Optional[bool] = None
    is_trusted_author: Optional[bool] = None


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
    from datetime import timedelta
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    seven_days_ago = today_start - timedelta(days=7)
    thirty_days_ago = today_start - timedelta(days=30)

    # ── Basic counts ──────────────────────────────────────────────────────────
    total_users      = (await db.execute(select(func.count(User.id)))).scalar() or 0
    active_users     = (await db.execute(select(func.count(User.id)).where(User.is_active == True))).scalar() or 0
    total_modules    = (await db.execute(select(func.count(Module.id)))).scalar() or 0
    published_modules= (await db.execute(select(func.count(Module.id)).where(Module.is_published == True))).scalar() or 0
    total_flashcards = (await db.execute(select(func.count(Flashcard.id)))).scalar() or 0
    total_lessons    = (await db.execute(select(func.count(Lesson.id)))).scalar() or 0
    total_mcq        = (await db.execute(select(func.count(MCQQuestion.id)))).scalar() or 0
    total_cases      = (await db.execute(select(func.count(ClinicalCase.id)))).scalar() or 0
    total_articles   = (await db.execute(select(func.count(Article.id)))).scalar() or 0
    published_articles=(await db.execute(select(func.count(Article.id)).where(Article.is_published == True))).scalar() or 0
    pending_articles = (await db.execute(select(func.count(Article.id)).where(Article.review_status == "pending_review"))).scalar() or 0

    # ── User activity ─────────────────────────────────────────────────────────
    dau = (await db.execute(
        select(func.count(User.id)).where(User.last_active_date >= today_start)
    )).scalar() or 0

    wau = (await db.execute(
        select(func.count(User.id)).where(User.last_active_date >= seven_days_ago)
    )).scalar() or 0

    mau = (await db.execute(
        select(func.count(User.id)).where(User.last_active_date >= thirty_days_ago)
    )).scalar() or 0

    new_users_week = (await db.execute(
        select(func.count(User.id)).where(User.created_at >= seven_days_ago)
    )).scalar() or 0

    new_users_month = (await db.execute(
        select(func.count(User.id)).where(User.created_at >= thirty_days_ago)
    )).scalar() or 0

    # ── Users by tier ─────────────────────────────────────────────────────────
    tier_rows = await db.execute(
        select(User.subscription_tier, func.count(User.id)).group_by(User.subscription_tier)
    )
    tiers = {row[0]: row[1] for row in tier_rows}

    # ── AI usage stats (last 30 days) ─────────────────────────────────────────
    ai_rows = await db.execute(
        select(AIConversation.model_used, func.count(AIConversation.id), func.sum(AIConversation.total_tokens))
        .where(AIConversation.created_at >= thirty_days_ago)
        .group_by(AIConversation.model_used)
    )
    ai_by_model = {}
    total_tokens_30d = 0
    total_conversations_30d = 0
    for row in ai_rows:
        model = row[0] or "unknown"
        count = row[1] or 0
        tokens = row[2] or 0
        ai_by_model[model] = {"conversations": count, "tokens": tokens}
        total_tokens_30d += tokens
        total_conversations_30d += count

    # ── Recent audit log (last 24h most common actions) ───────────────────────
    audit_rows = await db.execute(
        select(AuditLog.action, func.count(AuditLog.id))
        .where(AuditLog.created_at >= now - timedelta(hours=24))
        .group_by(AuditLog.action)
        .order_by(func.count(AuditLog.id).desc())
        .limit(10)
    )
    recent_actions = {row[0]: row[1] for row in audit_rows}

    return {
        "users": {
            "total": total_users,
            "active": active_users,
            "dau": dau,
            "wau": wau,
            "mau": mau,
            "new_last_7_days": new_users_week,
            "new_last_30_days": new_users_month,
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
        "ai": {
            "conversations_30d": total_conversations_30d,
            "tokens_30d": total_tokens_30d,
            "by_model": ai_by_model,
        },
        "activity": {
            "top_actions_24h": recent_actions,
        },
    }


@router.get("/health")
async def get_system_health(
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    """System health: DB pool, Redis, Ollama."""
    import time
    from app.core.database import engine
    from app.core.config import settings

    result: dict = {"timestamp": datetime.utcnow().isoformat(), "services": {}}

    # DB pool stats
    pool = engine.pool
    result["services"]["database"] = {
        "status": "ok",
        "pool_size": pool.size(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "checked_in": pool.checkedin(),
    }

    # Quick DB ping
    try:
        t0 = time.monotonic()
        await db.execute(select(func.now()))
        result["services"]["database"]["latency_ms"] = round((time.monotonic() - t0) * 1000, 1)
    except Exception as e:
        result["services"]["database"]["status"] = "error"
        result["services"]["database"]["error"] = str(e)

    # Redis ping
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(settings.REDIS_URL, socket_connect_timeout=2)
        t0 = time.monotonic()
        await r.ping()
        await r.aclose()
        result["services"]["redis"] = {
            "status": "ok",
            "latency_ms": round((time.monotonic() - t0) * 1000, 1),
        }
    except Exception as e:
        result["services"]["redis"] = {"status": "error", "error": str(e)}

    # Ollama ping
    try:
        import httpx
        t0 = time.monotonic()
        async with httpx.AsyncClient(timeout=3) as client:
            resp = await client.get(f"{settings.OLLAMA_URL}/api/tags")
        models = [m["name"] for m in resp.json().get("models", [])]
        result["services"]["ollama"] = {
            "status": "ok",
            "latency_ms": round((time.monotonic() - t0) * 1000, 1),
            "models": models,
        }
    except Exception as e:
        result["services"]["ollama"] = {"status": "unavailable", "error": str(e)}

    return result


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


@router.get("/users/{user_id}")
async def get_user_detail(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    result = await db.execute(select(User).where(User.id == user_id))
    u = result.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    article_count = (await db.execute(select(func.count(Article.id)).where(Article.author_id == u.id))).scalar_one()
    return {
        "id": str(u.id),
        "email": decrypt_email(u.email),
        "first_name": u.first_name,
        "last_name": u.last_name,
        "role": u.role,
        "subscription_tier": u.subscription_tier,
        "subscription_expires": u.subscription_expires.isoformat() if u.subscription_expires else None,
        "stripe_customer_id": u.stripe_customer_id,
        "is_active": u.is_active,
        "is_verified_teacher": u.is_verified_teacher,
        "is_trusted_author": u.is_trusted_author,
        "xp": u.xp,
        "level": u.level,
        "streak_days": u.streak_days,
        "ai_requests_today": u.ai_requests_today,
        "ai_requests_reset_at": u.ai_requests_reset_at.isoformat() if u.ai_requests_reset_at else None,
        "articles_authored": article_count,
        "created_at": u.created_at.isoformat() if u.created_at else None,
        "last_login": u.last_login.isoformat() if hasattr(u, "last_login") and u.last_login else None,
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
    if data.is_verified_teacher is not None:
        target.is_verified_teacher = data.is_verified_teacher
    if data.is_trusted_author is not None:
        target.is_trusted_author = data.is_trusted_author

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
        "is_verified_teacher": target.is_verified_teacher,
        "is_trusted_author": target.is_trusted_author,
    }


# ── Teachers ─────────────────────────────────────────────────────────────────

@router.get("/teachers")
async def list_teachers(
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    """List all teachers with verification/trust status and article stats."""
    from sqlalchemy import func as _func
    from app.models.models import Article

    result = await db.execute(
        select(User).where(User.role.in_(["teacher", "doctor"])).order_by(User.created_at.desc())
    )
    teachers = result.scalars().all()

    # Get article counts per teacher
    teacher_ids = [t.id for t in teachers]
    art_stats: dict = {}
    if teacher_ids:
        art_rows = await db.execute(
            select(Article.author_id, Article.is_published, Article.review_status)
            .where(Article.author_id.in_(teacher_ids))
        )
        for row in art_rows:
            tid = str(row.author_id)
            s = art_stats.setdefault(tid, {"total": 0, "published": 0, "pending": 0})
            s["total"] += 1
            if row.is_published:
                s["published"] += 1
            if row.review_status == "pending_review":
                s["pending"] += 1

    return [
        {
            "id": str(t.id),
            "email": decrypt_email(t.email),
            "first_name": t.first_name,
            "last_name": t.last_name,
            "role": t.role,
            "is_active": t.is_active,
            "is_verified_teacher": t.is_verified_teacher,
            "is_trusted_author": t.is_trusted_author,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "articles": art_stats.get(str(t.id), {"total": 0, "published": 0, "pending": 0}),
        }
        for t in teachers
    ]


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


# ── Article bulk operations ───────────────────────────────────────────────────

VALID_VERIFICATION = {"unverified", "ai_reviewed", "expert_reviewed", "verified"}

@router.post("/articles/bulk-verify")
async def bulk_verify_articles(
    data: dict,
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    """Bulk set verification_status on articles. Body: {ids?: [...], category?: str, status: str, all?: bool}"""
    status = data.get("status", "ai_reviewed")
    if status not in VALID_VERIFICATION:
        raise HTTPException(status_code=400, detail=f"Invalid status. Valid: {VALID_VERIFICATION}")

    q = update(Article)
    ids = data.get("ids")
    category = data.get("category")
    apply_all = data.get("all", False)

    if ids:
        q = q.where(Article.id.in_(ids))
    elif category:
        q = q.where(Article.category == category)
    elif apply_all:
        pass  # update everything
    else:
        raise HTTPException(status_code=400, detail="Provide ids, category, or all=true")

    result = await db.execute(q.values(verification_status=status))
    await db.commit()
    return {"updated": result.rowcount, "verification_status": status}


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


# ── Article Pipeline (research → generate → translate → publish) ───────────────

class PipelineRequest(BaseModel):
    topic: str
    category: str
    model: str = "haiku"  # haiku | sonnet
    auto_publish: bool = True


class BatchPipelineRequest(BaseModel):
    topics: list[str]
    category: str
    model: str = "haiku"
    auto_publish: bool = True
    max_concurrent: int = 3


@router.post("/pipeline/generate")
async def pipeline_generate_article(
    req: PipelineRequest,
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    """Generate a single article via the open-source pipeline (research → AI → translate → publish)."""
    from app.services.article_pipeline import run_pipeline
    slug = await run_pipeline(
        topic=req.topic,
        category=req.category,
        db=db,
        model=req.model,
        auto_publish=req.auto_publish,
        skip_if_exists=False,
    )
    if not slug:
        raise HTTPException(500, "Pipeline failed — check logs")
    return {"slug": slug, "url": f"https://medmind.pro/articles/{slug}"}


@router.get("/analytics")
async def get_analytics(
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    """Content analytics: top articles, views by category, growth by day, generator stats."""
    from datetime import timedelta, timezone

    now = datetime.now(timezone.utc)
    day_30 = now - timedelta(days=30)
    day_7  = now - timedelta(days=7)

    # ── Top articles by views ─────────────────────────────────────────────────
    top_rows = (await db.execute(
        select(
            Article.slug, Article.title, Article.category,
            Article.view_count, Article.reading_time_minutes,
            Article.generated_by, Article.published_at,
        )
        .where(Article.is_published == True)
        .order_by(desc(Article.view_count))
        .limit(20)
    )).all()

    top_articles = [
        {
            "slug": r.slug,
            "title": r.title,
            "category": r.category,
            "views": r.view_count or 0,
            "reading_time": r.reading_time_minutes or 0,
            "generated_by": r.generated_by or "manual",
            "published_at": r.published_at.isoformat() if r.published_at else None,
        }
        for r in top_rows
    ]

    # ── Views by category ─────────────────────────────────────────────────────
    cat_rows = (await db.execute(
        select(Article.category, func.sum(Article.view_count).label("views"),
               func.count(Article.id).label("count"))
        .where(Article.is_published == True)
        .group_by(Article.category)
        .order_by(desc("views"))
    )).all()

    by_category = [
        {"category": r.category, "views": int(r.views or 0), "count": r.count}
        for r in cat_rows
    ]

    # ── Daily new articles (last 30 days) ─────────────────────────────────────
    daily_rows = (await db.execute(
        select(
            func.date_trunc("day", Article.published_at).label("day"),
            func.count(Article.id).label("count"),
        )
        .where(and_(Article.is_published == True, Article.published_at >= day_30))
        .group_by(text("day"))
        .order_by(text("day"))
    )).all()

    daily_growth = [
        {"date": r.day.strftime("%Y-%m-%d"), "count": r.count}
        for r in daily_rows if r.day
    ]

    # ── Generator breakdown ───────────────────────────────────────────────────
    gen_rows = (await db.execute(
        select(Article.generated_by, func.count(Article.id).label("count"))
        .where(Article.is_published == True)
        .group_by(Article.generated_by)
        .order_by(desc("count"))
    )).all()

    by_generator = [
        {"generator": r.generated_by or "manual", "count": r.count}
        for r in gen_rows
    ]

    # ── Verification status breakdown ─────────────────────────────────────────
    ver_rows = (await db.execute(
        select(Article.verification_status, func.count(Article.id).label("count"))
        .where(Article.is_published == True)
        .group_by(Article.verification_status)
    )).all()

    by_verification = [
        {"status": r.verification_status or "unverified", "count": r.count}
        for r in ver_rows
    ]

    # ── Total views ───────────────────────────────────────────────────────────
    total_views = (await db.execute(
        select(func.sum(Article.view_count)).where(Article.is_published == True)
    )).scalar() or 0

    published_total = (await db.execute(
        select(func.count(Article.id)).where(Article.is_published == True)
    )).scalar() or 0

    avg_views = round(total_views / published_total, 1) if published_total else 0

    # ── New last 7 / 30 days ─────────────────────────────────────────────────
    new_7 = (await db.execute(
        select(func.count(Article.id))
        .where(and_(Article.is_published == True, Article.published_at >= day_7))
    )).scalar() or 0

    new_30 = (await db.execute(
        select(func.count(Article.id))
        .where(and_(Article.is_published == True, Article.published_at >= day_30))
    )).scalar() or 0

    return {
        "summary": {
            "total_published": published_total,
            "total_views": int(total_views),
            "avg_views_per_article": avg_views,
            "new_last_7_days": new_7,
            "new_last_30_days": new_30,
        },
        "top_articles": top_articles,
        "by_category": by_category,
        "daily_growth": daily_growth,
        "by_generator": by_generator,
        "by_verification": by_verification,
    }


@router.post("/pipeline/batch")
async def pipeline_batch(
    req: BatchPipelineRequest,
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    """
    Queue a batch of topics for background generation.
    Returns immediately with a task count; generation runs in background.
    """
    import asyncio
    from app.services.article_pipeline import run_pipeline

    async def _generate_one(topic: str):
        try:
            async with __import__('app.core.database', fromlist=['AsyncSessionLocal']).AsyncSessionLocal() as session:
                slug = await run_pipeline(
                    topic=topic, category=req.category, db=session,
                    model=req.model, auto_publish=req.auto_publish,
                )
            return {"topic": topic, "slug": slug, "ok": True}
        except Exception as e:
            return {"topic": topic, "error": str(e), "ok": False}

    # Fire and forget — don't await the whole batch
    asyncio.create_task(asyncio.gather(*[_generate_one(t) for t in req.topics[:50]]))
    return {"queued": len(req.topics[:50]), "message": "Batch generation started in background"}


# ── Revenue / Credits ─────────────────────────────────────────────────────────

@router.get("/revenue")
async def admin_revenue(
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    from datetime import timedelta
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    prev_month_start = (month_start - timedelta(days=1)).replace(day=1)

    # Subscription breakdown
    tier_counts = (await db.execute(
        select(User.subscription_tier, func.count(User.id).label("n"))
        .group_by(User.subscription_tier)
    )).all()

    # Credit transactions summary
    credit_totals = (await db.execute(
        select(
            CreditTransaction.type,
            func.count(CreditTransaction.id).label("count"),
            func.sum(CreditTransaction.credits).label("credits"),
            func.coalesce(func.sum(CreditTransaction.usd_amount), 0).label("usd"),
        ).group_by(CreditTransaction.type)
    )).all()

    # This month revenue (purchases)
    month_rev = (await db.execute(
        select(func.coalesce(func.sum(CreditTransaction.usd_amount), 0))
        .where(CreditTransaction.type == "purchase")
        .where(CreditTransaction.created_at >= month_start)
    )).scalar_one()

    prev_month_rev = (await db.execute(
        select(func.coalesce(func.sum(CreditTransaction.usd_amount), 0))
        .where(CreditTransaction.type == "purchase")
        .where(CreditTransaction.created_at >= prev_month_start)
        .where(CreditTransaction.created_at < month_start)
    )).scalar_one()

    # Recent transactions
    recent_tx = (await db.execute(
        select(
            CreditTransaction.type, CreditTransaction.credits,
            CreditTransaction.usd_amount, CreditTransaction.description,
            CreditTransaction.created_at, User.email.label("user_email"),
        )
        .join(User, User.id == CreditTransaction.user_id, isouter=True)
        .order_by(desc(CreditTransaction.created_at))
        .limit(20)
    )).all()

    # Stripe events
    stripe_recent = (await db.execute(
        select(StripeEvent.event_type, StripeEvent.processed, StripeEvent.created_at)
        .order_by(desc(StripeEvent.created_at))
        .limit(10)
    )).all()

    return {
        "subscription_tiers": [{"tier": r.subscription_tier, "count": r.n} for r in tier_counts],
        "credit_summary": [
            {"type": r.type, "count": r.count, "credits": int(r.credits or 0), "usd": float(r.usd or 0)}
            for r in credit_totals
        ],
        "this_month_usd": float(month_rev or 0),
        "prev_month_usd": float(prev_month_rev or 0),
        "recent_transactions": [
            {
                "type": r.type, "credits": r.credits,
                "usd": float(r.usd_amount or 0) if r.usd_amount else None,
                "description": r.description or "",
                "user_email": decrypt_email(r.user_email) if r.user_email else "—",
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in recent_tx
        ],
        "stripe_events": [
            {"type": r.event_type, "processed": r.processed, "at": r.created_at.isoformat() if r.created_at else None}
            for r in stripe_recent
        ],
    }


# ── Admin Imaging ──────────────────────────────────────────────────────────────

@router.get("/imaging")
async def admin_list_imaging(
    page: int = Query(1, ge=1),
    per_page: int = Query(24, ge=1, le=100),
    modality: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    q = select(MedicalImage).order_by(desc(MedicalImage.created_at))
    if modality:
        q = q.where(MedicalImage.modality == modality)
    if search:
        term = f"%{search}%"
        q = q.where(MedicalImage.title.ilike(term))
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows = (await db.execute(q.offset((page - 1) * per_page).limit(per_page))).scalars().all()
    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "items": [
            {
                "id": str(r.id),
                "title": r.title or "",
                "modality": r.modality or "",
                "anatomy_region": r.anatomy_region or "",
                "file_path": r.file_path or "",
                "thumbnail_path": r.thumbnail_path or "",
                "view_count": r.view_count or 0,
                "is_active": r.is_active,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }


@router.get("/drugs")
async def admin_list_drugs(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    drug_class: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    q = select(Drug).order_by(Drug.name)
    if search:
        q = q.where(Drug.name.ilike(f"%{search}%"))
    if drug_class:
        q = q.where(Drug.drug_class == drug_class)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows = (await db.execute(q.offset((page - 1) * per_page).limit(per_page))).scalars().all()
    return {
        "total": total, "page": page, "per_page": per_page,
        "items": [
            {
                "id": str(d.id), "name": d.name, "generic_name": d.generic_name or "",
                "drug_class": d.drug_class or "", "is_high_yield": d.is_high_yield,
                "is_nti": d.is_nti, "is_veterinary": d.is_veterinary,
                "indications_count": len(d.indications or []),
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in rows
        ],
    }


@router.patch("/drugs/{drug_id}")
async def admin_patch_drug(
    drug_id: UUID,
    data: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    result = await db.execute(select(Drug).where(Drug.id == drug_id))
    drug = result.scalar_one_or_none()
    if not drug:
        raise HTTPException(status_code=404, detail="Drug not found")
    allowed = {"name", "generic_name", "drug_class", "mechanism", "black_box_warning",
               "is_high_yield", "is_nti", "is_veterinary", "image_url"}
    for k, v in data.items():
        if k in allowed:
            setattr(drug, k, v)
    await db.commit()
    return {"id": str(drug.id), "name": drug.name}


@router.delete("/drugs/{drug_id}", status_code=204)
async def admin_delete_drug(
    drug_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    result = await db.execute(select(Drug).where(Drug.id == drug_id))
    drug = result.scalar_one_or_none()
    if not drug:
        raise HTTPException(status_code=404, detail="Drug not found")
    await db.delete(drug)
    await db.commit()


@router.delete("/imaging/{image_id}", status_code=204)
async def admin_delete_imaging(
    image_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = _admin,
):
    result = await db.execute(select(MedicalImage).where(MedicalImage.id == image_id))
    img = result.scalar_one_or_none()
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")
    img.is_active = False
    await db.commit()


# ── Reviewer queue (accessible to admin + reviewer roles) ──────────────────────

_reviewer = Depends(require_reviewer())


class RequestChangesBody(BaseModel):
    comment: str


@router.get("/reviewer-queue")
async def list_reviewer_queue(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = _reviewer,
):
    """Articles that have passed automated verification but not yet been human-reviewed.
    Sorted by view_count desc (highest-traffic first), then by published_at desc.
    """
    q = (
        select(
            Article.id,
            Article.slug,
            Article.title,
            Article.category,
            Article.view_count,
            Article.published_at,
            Article.verification_status,
            Article.review_status,
            Article.reviewed_by,
            Article.last_verified_at,
        )
        .where(
            Article.is_published == True,
            Article.review_status == "published",
            Article.verification_status == "passed",
        )
        .order_by(desc(Article.view_count), desc(Article.published_at))
        .offset((page - 1) * limit)
        .limit(limit)
    )
    rows = (await db.execute(q)).all()
    total = await db.scalar(
        select(func.count(Article.id)).where(
            Article.is_published == True,
            Article.review_status == "published",
            Article.verification_status == "passed",
        )
    ) or 0

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": [
            {
                "id": str(r.id),
                "slug": r.slug,
                "title": r.title,
                "category": r.category,
                "view_count": r.view_count,
                "published_at": r.published_at.isoformat() if r.published_at else None,
                "verification_status": r.verification_status,
                "last_verified_at": r.last_verified_at.isoformat() if r.last_verified_at else None,
            }
            for r in rows
        ],
    }


@router.get("/reviewer-queue/{article_id}")
async def get_reviewer_queue_article(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = _reviewer,
):
    """Full article detail for reviewer: body, sources, verification_report."""
    article = (await db.execute(select(Article).where(Article.id == article_id))).scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    return {
        "id": str(article.id),
        "slug": article.slug,
        "title": article.title,
        "category": article.category,
        "excerpt": article.excerpt,
        "body": article.body or [],
        "sources": article.sources or [],
        "faq": article.faq or [],
        "verification_status": article.verification_status,
        "verification_report": article.verification_report,
        "last_verified_at": article.last_verified_at.isoformat() if article.last_verified_at else None,
        "reviewed_by": article.reviewed_by,
        "review_note": article.review_note,
        "view_count": article.view_count,
        "published_at": article.published_at.isoformat() if article.published_at else None,
    }


@router.post("/reviewer-queue/{article_id}/approve")
async def approve_article(
    article_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = _reviewer,
):
    """Approve article: sets verification_status='human_reviewed'.
    Links to the reviewer's Reviewer profile by matching user email/name.
    """
    article = (await db.execute(select(Article).where(Article.id == article_id))).scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    # Resolve reviewer display name — prefer linked Reviewer profile, fall back to user name
    reviewer_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email

    article.verification_status = "human_reviewed"
    article.reviewed_by = reviewer_name
    article.last_verified_at = datetime.utcnow()
    article.review_note = None  # clear any prior rejection note
    article.updated_at = datetime.utcnow()
    await db.commit()

    return {
        "id": str(article.id),
        "verification_status": "human_reviewed",
        "reviewed_by": reviewer_name,
        "last_verified_at": article.last_verified_at.isoformat(),
    }


@router.post("/reviewer-queue/{article_id}/request-changes")
async def request_changes(
    article_id: UUID,
    body: RequestChangesBody,
    db: AsyncSession = Depends(get_db),
    user: User = _reviewer,
):
    """Request changes: sets verification_status='failed', hides article from public.
    The public endpoint gate (V4 Phase 1) already excludes failed articles.
    """
    if not body.comment.strip():
        raise HTTPException(status_code=400, detail="Comment is required")

    article = (await db.execute(select(Article).where(Article.id == article_id))).scalar_one_or_none()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    article.verification_status = "failed"
    article.review_note = body.comment.strip()
    article.updated_at = datetime.utcnow()
    await db.commit()

    return {
        "id": str(article.id),
        "verification_status": "failed",
        "review_note": article.review_note,
    }


@router.get("/reviewer-queue/stats/summary")
async def reviewer_queue_summary(
    db: AsyncSession = Depends(get_db),
    user: User = _reviewer,
):
    """Dashboard stats for the reviewer: queue depth + unresolved feedback."""
    queue_count = await db.scalar(
        select(func.count(Article.id)).where(
            Article.is_published == True,
            Article.review_status == "published",
            Article.verification_status == "passed",
        )
    ) or 0

    feedback_count = await db.scalar(
        select(func.count(ContentFeedback.id)).where(
            ContentFeedback.resolved == False
        )
    ) or 0

    human_reviewed_count = await db.scalar(
        select(func.count(Article.id)).where(
            Article.verification_status == "human_reviewed"
        )
    ) or 0

    return {
        "queue_depth": queue_count,
        "unresolved_feedback": feedback_count,
        "human_reviewed_total": human_reviewed_count,
    }


@router.get("/feedback")
async def list_feedback(
    resolved: Optional[bool] = None,
    content_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User = _reviewer,
):
    """List user-submitted content feedback reports. Reviewer+ access."""
    q = select(ContentFeedback).order_by(ContentFeedback.created_at.desc())
    if resolved is not None:
        q = q.where(ContentFeedback.resolved == resolved)
    if content_type:
        q = q.where(ContentFeedback.content_type == content_type)
    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    rows = (await db.execute(q.offset(offset).limit(limit))).scalars().all()
    return {
        "total": total,
        "items": [
            {
                "id": r.id,
                "content_type": r.content_type,
                "content_id": r.content_id,
                "problem_type": r.problem_type,
                "comment": r.comment,
                "reporter_email": r.reporter_email,
                "resolved": r.resolved,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }


@router.patch("/feedback/{feedback_id}/resolve")
async def resolve_feedback(
    feedback_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = _reviewer,
):
    """Mark a feedback report as resolved."""
    item = await db.get(ContentFeedback, feedback_id)
    if not item:
        raise HTTPException(status_code=404, detail="Feedback not found")
    item.resolved = True
    await db.commit()
    return {"id": feedback_id, "resolved": True}
