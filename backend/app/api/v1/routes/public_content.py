"""Public read-only content endpoints — no authentication required.

All endpoints:
- No auth required
- Redis cache TTL 1 hour
- IP rate limiting: 120 req/min per IP
- Never expose dosing, prescription, or user-specific data
"""
import re
import hashlib
import logging
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis_client import get_redis
from app.models.models import Article, Lesson, Module, Drug, Flashcard, Specialty, PublicQuiz, SharedDeck, ModuleTranslation, LessonTranslation, ContentSource
from fastapi import Depends

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/public", tags=["public"])

CACHE_TTL = 3600        # 1 hour
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX = 120    # requests per window per IP


# ── Rate limiting ─────────────────────────────────────────────────────────────

async def check_public_rate_limit(request: Request) -> None:
    """IP-based rate limit for public endpoints. 120 req/min."""
    client_ip = (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or request.client.host
        or "unknown"
    )
    redis = await get_redis()
    key = f"pub_rl:{hashlib.md5(client_ip.encode()).hexdigest()}"
    count = await redis.incr(key)
    if count == 1:
        await redis.expire(key, RATE_LIMIT_WINDOW)
    if count > RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please wait a minute.",
            headers={"Retry-After": str(RATE_LIMIT_WINDOW)},
        )


# ── Cache helpers ─────────────────────────────────────────────────────────────

async def _cache_get(key: str) -> Any | None:
    import json
    redis = await get_redis()
    raw = await redis.get(key)
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            return None
    return None


async def _cache_set(key: str, value: Any, ttl: int = CACHE_TTL) -> None:
    import json
    redis = await get_redis()
    await redis.setex(key, ttl, json.dumps(value, default=str))


def _slugify(text: str) -> str:
    """Convert text to URL-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


# ── Schemas ───────────────────────────────────────────────────────────────────

class ContentSourceOut(BaseModel):
    slug: str
    title: str
    publisher: str
    url: str
    license: str
    license_url: str | None
    text_reuse_allowed: bool
    attribution_template: str | None
    source_type: str
    verified_at: str | None
    notes: str | None


class PublicGlossaryTerm(BaseModel):
    term: str
    simple_definition: str
    slug: str
    lesson_title: str
    module_code: str
    module_title: str


class PublicGlossaryList(BaseModel):
    terms: list[PublicGlossaryTerm]
    total: int


class PublicTopic(BaseModel):
    module_code: str
    slug: str
    title: str
    title_en: Optional[str] = None
    description: Optional[str]
    lay_summary: Optional[str]       # first lesson's lay_summary
    lesson_count: int
    specialty: Optional[str]
    specialty_en: Optional[str] = None


class PublicTopicDetail(BaseModel):
    module_code: str
    slug: str
    title: str
    title_en: Optional[str] = None
    description: Optional[str]
    specialty: Optional[str]
    specialty_en: Optional[str] = None
    lessons: list[dict]              # [{title, lay_summary, lay_glossary, order}]
    total_glossary_terms: int
    disclaimer: str = (
        "This content is for educational purposes only and does not replace "
        "professional medical advice. Always consult a qualified healthcare provider."
    )


class PublicDrug(BaseModel):
    id: str
    slug: str
    name: str
    generic_name: Optional[str]
    drug_class: Optional[str]
    mechanism: Optional[str]
    indications: Optional[list[str]]
    contraindications: Optional[list[str]]
    black_box_warning: Optional[str]
    is_high_yield: bool
    is_nti: bool
    image_url: Optional[str]
    # NOTE: dosing, adverse_effects intentionally EXCLUDED from public endpoint
    disclaimer: str = (
        "This is educational information only. Dosing and prescription decisions "
        "must be made by a licensed healthcare provider. Do not self-medicate."
    )


# ── /public/glossary ──────────────────────────────────────────────────────────

@router.get("/glossary", response_model=PublicGlossaryList)
async def get_public_glossary(
    request: Request,
    letter: Optional[str] = Query(None, min_length=1, max_length=1, description="Filter by first letter"),
    search: Optional[str] = Query(None, max_length=100),
    limit: int = Query(100, ge=1, le=500),
    locale: str = Query("en", max_length=5, description="Locale for translated glossary terms"),
    db: AsyncSession = Depends(get_db),
):
    """Aggregated glossary from all lessons with lay_glossary set.

    Returns deduplicated terms sorted A-Z.
    For non-English locales, prefers translated lay_glossary from lesson_translations.
    Cached for 1 hour. Rate limited 120 req/min per IP.
    """
    await check_public_rate_limit(request)

    cache_key = f"pub_glossary:{locale}:{letter or '*'}:{search or ''}:{limit}"
    cached = await _cache_get(cache_key)
    if cached:
        return cached

    # Fetch all published lessons with lay_glossary and their modules
    stmt = (
        select(Lesson.id, Lesson.title, Lesson.lay_glossary, Module.code, Module.title)
        .join(Module, Lesson.module_id == Module.id)
        .where(Lesson.lay_glossary.isnot(None))
        .where(Lesson.status == "published")
    )
    result = await db.execute(stmt)
    rows = result.all()

    # For non-English locales: fetch translated glossary from lesson_translations
    translation_glossary: dict[str, list] = {}
    if locale != "en":
        lesson_ids = [row.id for row in rows]
        if lesson_ids:
            tr_result = await db.execute(
                select(LessonTranslation.lesson_id, LessonTranslation.lay_glossary)
                .where(
                    LessonTranslation.lesson_id.in_(lesson_ids),
                    LessonTranslation.locale == locale,
                    LessonTranslation.lay_glossary.isnot(None),
                )
            )
            for tr_lesson_id, tr_glossary in tr_result.all():
                if isinstance(tr_glossary, list) and tr_glossary:
                    translation_glossary[str(tr_lesson_id)] = tr_glossary

    # Aggregate and deduplicate terms
    seen: dict[str, PublicGlossaryTerm] = {}
    for lesson_id, lesson_title, glossary, module_code, module_title in rows:
        # Use translated glossary if available for this locale
        effective_glossary = translation_glossary.get(str(lesson_id), glossary)
        if not isinstance(effective_glossary, list):
            continue
        for entry in effective_glossary:
            if not isinstance(entry, dict):
                continue
            term = entry.get("term", "").strip()
            definition = entry.get("simple_definition", "").strip()
            if not term or not definition:
                continue

            # Apply filters
            if letter and not term.lower().startswith(letter.lower()):
                continue
            if search and search.lower() not in term.lower() and search.lower() not in definition.lower():
                continue

            slug = _slugify(term)
            if slug not in seen:
                seen[slug] = PublicGlossaryTerm(
                    term=term,
                    simple_definition=definition,
                    slug=slug,
                    lesson_title=lesson_title,
                    module_code=module_code,
                    module_title=module_title,
                )

    terms = sorted(seen.values(), key=lambda t: t.term.lower())[:limit]
    response = PublicGlossaryList(terms=[t.model_dump() for t in terms], total=len(terms))

    await _cache_set(cache_key, response.model_dump())
    return response


@router.get("/glossary/{term_slug}")
async def get_glossary_term(
    term_slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Single glossary term detail page."""
    await check_public_rate_limit(request)

    cache_key = f"pub_glossary_term:{term_slug}"
    cached = await _cache_get(cache_key)
    if cached:
        return cached

    stmt = (
        select(Lesson.id, Lesson.title, Lesson.lay_glossary, Lesson.lay_summary,
               Module.code, Module.title)
        .join(Module, Lesson.module_id == Module.id)
        .where(Lesson.lay_glossary.isnot(None))
        .where(Lesson.status == "published")
    )
    result = await db.execute(stmt)
    rows = result.all()

    match = None
    related_terms: list[dict] = []

    for lesson_id, lesson_title, glossary, lay_summary, module_code, module_title in rows:
        if not isinstance(glossary, list):
            continue
        for entry in glossary:
            if not isinstance(entry, dict):
                continue
            term = entry.get("term", "").strip()
            if _slugify(term) == term_slug:
                match = {
                    "term": term,
                    "simple_definition": entry.get("simple_definition", ""),
                    "slug": term_slug,
                    "lesson_title": lesson_title,
                    "lesson_id": str(lesson_id),
                    "module_code": module_code,
                    "module_title": module_title,
                    "module_slug": _slugify(module_code),
                    "lay_summary_excerpt": (lay_summary or "")[:300] if lay_summary else None,
                }
            else:
                related_terms.append({
                    "term": term,
                    "slug": _slugify(term),
                    "lesson_title": lesson_title,
                    "module_code": module_code,
                })

    if not match:
        raise HTTPException(status_code=404, detail="Term not found")

    # Deduplicate related, limit to 8
    seen_slugs = {term_slug}
    unique_related = []
    for t in related_terms:
        if t["slug"] not in seen_slugs and t["module_code"] == match["module_code"]:
            seen_slugs.add(t["slug"])
            unique_related.append(t)
            if len(unique_related) >= 8:
                break

    response = {
        **match,
        "related_terms": unique_related,
        "disclaimer": (
            "This definition is for educational purposes only. "
            "Always consult a qualified healthcare provider for medical advice."
        ),
    }
    await _cache_set(cache_key, response)
    return response


# ── /public/topics ────────────────────────────────────────────────────────────

@router.get("/topics", response_model=list[PublicTopic])
async def list_public_topics(
    request: Request,
    specialty: Optional[str] = Query(None),
    locale: str = Query("en", max_length=5, description="Locale for translated titles, e.g. 'ru'"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List modules that have at least one lesson with lay_summary."""
    await check_public_rate_limit(request)

    cache_key = f"pub_topics:{specialty or '*'}:{locale}:{limit}"
    cached = await _cache_get(cache_key)
    if cached:
        return cached

    # All published modules — lay_summary optional (falls back to description)
    stmt = (
        select(
            Module.id, Module.code, Module.title, Module.title_en, Module.description,
            Specialty.name.label("specialty_name"),
            Specialty.name_en.label("specialty_name_en"),
            func.count(Lesson.id).label("lesson_count"),
            func.max(Lesson.lay_summary).label("sample_summary"),
        )
        .join(Lesson, Lesson.module_id == Module.id)
        .outerjoin(Specialty, Module.specialty_id == Specialty.id)
        .where(Lesson.status == "published")
        .group_by(Module.id, Module.code, Module.title, Module.title_en, Module.description, Specialty.name, Specialty.name_en)
        .order_by(Specialty.name.nullslast(), Module.code)
        .limit(limit)
    )
    if specialty:
        stmt = stmt.where(Specialty.name.ilike(f"%{specialty}%"))

    result = await db.execute(stmt)
    rows = result.all()

    # Bulk-fetch translations for non-English locale
    translation_map: dict = {}
    if locale != "en":
        module_ids = [row.id for row in rows]
        if module_ids:
            tr_result = await db.execute(
                select(ModuleTranslation).where(
                    ModuleTranslation.module_id.in_(module_ids),
                    ModuleTranslation.locale == locale,
                    ModuleTranslation.status == "done",
                )
            )
            for tr in tr_result.scalars().all():
                translation_map[tr.module_id] = tr

    topics = []
    for row in rows:
        tr = translation_map.get(row.id)
        tr_title = tr.title if tr and tr.title else None
        # For RU: modules.title is Russian — prefer it as fallback over English title_en
        if locale == "ru":
            title = tr_title or row.title or row.title_en
        else:
            title = tr_title or row.title_en or row.title
        description = (tr.description if tr and tr.description else None) or row.description
        topics.append(PublicTopic(
            module_code=row.code,
            slug=_slugify(row.code),
            title=title,
            title_en=row.title_en,
            description=description,
            lay_summary=(row.sample_summary[:200] if row.sample_summary else None) or description,
            lesson_count=row.lesson_count,
            specialty=row.specialty_name,
            specialty_en=row.specialty_name_en,
        ).model_dump())

    await _cache_set(cache_key, topics, ttl=3600)
    return topics


@router.get("/topics/{module_slug}")
async def get_public_topic(
    module_slug: str,
    request: Request,
    locale: str = Query("en", max_length=5, description="Locale for translated content, e.g. 'ru'"),
    db: AsyncSession = Depends(get_db),
):
    """Single topic (module) detail with all lay_summary lessons."""
    await check_public_rate_limit(request)

    cache_key = f"pub_topic:{module_slug}:{locale}"
    cached = await _cache_get(cache_key)
    if cached:
        return cached

    # Find module by slugified code
    stmt = (
        select(Module, Specialty.name.label("specialty_name"), Specialty.name_en.label("specialty_name_en"))
        .outerjoin(Specialty, Module.specialty_id == Specialty.id)
    )
    result = await db.execute(stmt)
    rows = result.all()

    module = None
    specialty_name = None
    specialty_name_en = None
    for mod, spec, spec_en in rows:
        if _slugify(mod.code) == module_slug:
            module = mod
            specialty_name = spec
            specialty_name_en = spec_en
            break

    if not module:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Fetch lessons with lay content
    lessons_stmt = (
        select(Lesson)
        .where(Lesson.module_id == module.id)
        .where(Lesson.status == "published")
        .order_by(Lesson.lesson_order)
    )
    lessons_result = await db.execute(lessons_stmt)
    lessons = lessons_result.scalars().all()

    # Fetch lesson translations in bulk for non-English locales
    lesson_translation_map: dict = {}
    if locale != "en" and lessons:
        lesson_ids = [l.id for l in lessons]
        lt_result = await db.execute(
            select(LessonTranslation).where(
                LessonTranslation.lesson_id.in_(lesson_ids),
                LessonTranslation.locale == locale,
                LessonTranslation.status == "done",
            )
        )
        for lt in lt_result.scalars().all():
            lesson_translation_map[lt.lesson_id] = lt

    # Overlay translated module title/description
    module_title = module.title_en or module.title
    module_description = module.description
    if locale != "en":
        mt = await db.get(ModuleTranslation, (module.id, locale))
        if mt and mt.status == "done":
            if mt.title:
                module_title = mt.title
            if mt.description:
                module_description = mt.description

    lesson_data = []
    total_terms = 0
    for l in lessons:
        lt = lesson_translation_map.get(l.id)
        lesson_title = (lt.title if lt and lt.title else None) or l.title

        # Use translated content_json if available, else fall back to English content
        english_content = l.content or {}
        translated_content = None
        if lt and lt.content_json and isinstance(lt.content_json, dict):
            translated_content = lt.content_json

        active_content = translated_content or english_content

        intro = active_content.get("intro") or l.lay_summary or ""
        sections = active_content.get("sections") or []
        key_points = active_content.get("key_points") or []
        # Normalize sections: ensure each has title and text
        sections_clean = [
            {"title": s.get("title") or "", "text": s.get("text") or ""}
            for s in sections
            if isinstance(s, dict) and s.get("text")
        ]

        glossary = l.lay_glossary or []
        total_terms += len(glossary) if isinstance(glossary, list) else 0
        lesson_data.append({
            "title": lesson_title,
            "lesson_code": l.lesson_code or "",
            "lesson_slug": _slugify(l.lesson_code or l.title or str(l.id)),
            "estimated_minutes": l.estimated_minutes,
            "intro": intro,
            "sections": sections_clean,
            "key_points": [kp for kp in key_points if isinstance(kp, str)],
            "lay_summary": intro[:300] if intro else None,
            "lay_glossary": [
                {"term": t["term"], "slug": _slugify(t["term"]), "simple_definition": t["simple_definition"]}
                for t in (glossary if isinstance(glossary, list) else [])
                if isinstance(t, dict)
            ],
            "order": l.lesson_order,
        })

    if not lesson_data:
        raise HTTPException(status_code=404, detail="Topic not found")

    response = PublicTopicDetail(
        module_code=module.code,
        slug=module_slug,
        title=module_title,
        title_en=module.title_en,
        description=module_description,
        specialty=specialty_name,
        specialty_en=specialty_name_en,
        lessons=lesson_data,
        total_glossary_terms=total_terms,
    ).model_dump()

    await _cache_set(cache_key, response, ttl=3600)
    return response


@router.get("/topics/{module_slug}/lessons/{lesson_slug}")
async def get_public_lesson(
    module_slug: str,
    lesson_slug: str,
    request: Request,
    locale: str = Query("en", max_length=5),
    db: AsyncSession = Depends(get_db),
):
    """Single lesson detail page — full content, no auth required."""
    await check_public_rate_limit(request)

    cache_key = f"pub_lesson:{module_slug}:{lesson_slug}:{locale}"
    cached = await _cache_get(cache_key)
    if cached:
        return cached

    # Find module
    stmt = (
        select(Module, Specialty.name.label("spec"), Specialty.name_en.label("spec_en"))
        .outerjoin(Specialty, Module.specialty_id == Specialty.id)
    )
    result = await db.execute(stmt)
    module = None
    specialty_name = None
    for mod, spec, spec_en in result.all():
        if _slugify(mod.code) == module_slug:
            module = mod
            specialty_name = spec
            break

    if not module:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Find lesson by slug (lesson_code slugified)
    lessons_result = await db.execute(
        select(Lesson)
        .where(Lesson.module_id == module.id, Lesson.status == "published")
        .order_by(Lesson.lesson_order)
    )
    lessons = lessons_result.scalars().all()

    lesson = None
    for l in lessons:
        if _slugify(l.lesson_code or l.title or str(l.id)) == lesson_slug:
            lesson = l
            break

    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Translation
    lt = None
    if locale != "en":
        lt_result = await db.execute(
            select(LessonTranslation).where(
                LessonTranslation.lesson_id == lesson.id,
                LessonTranslation.locale == locale,
                LessonTranslation.status == "done",
            )
        )
        lt = lt_result.scalar_one_or_none()

    # Module translation
    module_title = module.title_en or module.title
    if locale != "en":
        mt = await db.get(ModuleTranslation, (module.id, locale))
        if mt and mt.status == "done" and mt.title:
            module_title = mt.title

    english_content = lesson.content or {}
    translated_content = lt.content_json if (lt and lt.content_json and isinstance(lt.content_json, dict)) else None
    active = translated_content or english_content

    lesson_title = (lt.title if lt and lt.title else None) or lesson.title
    intro = active.get("intro") or lesson.lay_summary or ""
    sections = [
        {"title": s.get("title") or "", "text": s.get("text") or ""}
        for s in (active.get("sections") or [])
        if isinstance(s, dict) and s.get("text")
    ]
    key_points = [kp for kp in (active.get("key_points") or []) if isinstance(kp, str)]

    glossary = lesson.lay_glossary or []
    lesson_index = next((i for i, l in enumerate(lessons) if l.id == lesson.id), 0)
    prev_lesson = lessons[lesson_index - 1] if lesson_index > 0 else None
    next_lesson = lessons[lesson_index + 1] if lesson_index < len(lessons) - 1 else None

    response = {
        "module_code": module.code,
        "module_slug": module_slug,
        "module_title": module_title,
        "specialty": specialty_name,
        "lesson_code": lesson.lesson_code or "",
        "lesson_slug": lesson_slug,
        "title": lesson_title,
        "estimated_minutes": lesson.estimated_minutes,
        "intro": intro,
        "sections": sections,
        "key_points": key_points,
        "lay_glossary": [
            {"term": t["term"], "slug": _slugify(t["term"]), "simple_definition": t["simple_definition"]}
            for t in (glossary if isinstance(glossary, list) else [])
            if isinstance(t, dict)
        ],
        "prev_lesson": {
            "title": prev_lesson.title,
            "slug": _slugify(prev_lesson.lesson_code or prev_lesson.title or str(prev_lesson.id)),
        } if prev_lesson else None,
        "next_lesson": {
            "title": next_lesson.title,
            "slug": _slugify(next_lesson.lesson_code or next_lesson.title or str(next_lesson.id)),
        } if next_lesson else None,
        "total_lessons": len(lessons),
        "lesson_number": lesson_index + 1,
        "disclaimer": (
            "This content is for educational purposes only and does not replace "
            "professional medical advice. Always consult a qualified healthcare provider."
        ),
    }

    await _cache_set(cache_key, response, ttl=3600)
    return response


@router.get("/sitemap/lessons")
async def get_lessons_sitemap_data(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Returns all (module_slug, lesson_slug) pairs for sitemap generation."""
    await check_public_rate_limit(request)

    cache_key = "pub_sitemap_lessons"
    cached = await _cache_get(cache_key)
    if cached:
        return cached

    result = await db.execute(
        select(Module.code, Lesson.lesson_code, Lesson.title)
        .join(Lesson, Lesson.module_id == Module.id)
        .where(Lesson.status == "published")
        .order_by(Module.code, Lesson.lesson_order)
    )
    rows = result.all()

    data = [
        {
            "module_slug": _slugify(module_code),
            "lesson_slug": _slugify(lesson_code or lesson_title or ""),
        }
        for module_code, lesson_code, lesson_title in rows
        if lesson_code or lesson_title
    ]

    await _cache_set(cache_key, data, ttl=86400)
    return data


# ── /public/drugs ─────────────────────────────────────────────────────────────

@router.get("/drugs", response_model=list[dict])
async def list_public_drugs(
    request: Request,
    search: Optional[str] = Query(None, max_length=100),
    drug_class: Optional[str] = Query(None, max_length=100),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List drugs for public index — WITHOUT dosing data."""
    await check_public_rate_limit(request)

    cache_key = f"pub_drugs:{search or ''}:{drug_class or ''}:{limit}"
    cached = await _cache_get(cache_key)
    if cached:
        return cached

    stmt = select(
        Drug.id, Drug.name, Drug.generic_name, Drug.drug_class,
        Drug.mechanism, Drug.indications, Drug.is_high_yield,
        Drug.is_nti, Drug.image_url,
    )
    if search:
        stmt = stmt.where(
            or_(
                Drug.name.ilike(f"%{search}%"),
                Drug.generic_name.ilike(f"%{search}%"),
            )
        )
    if drug_class:
        stmt = stmt.where(Drug.drug_class.ilike(f"%{drug_class}%"))
    stmt = stmt.order_by(Drug.name).limit(limit)

    result = await db.execute(stmt)
    rows = result.all()

    drugs = [
        {
            "id": str(r.id),
            "slug": _slugify(r.name),
            "name": r.name,
            "generic_name": r.generic_name,
            "drug_class": r.drug_class,
            "mechanism": r.mechanism,
            "indications": r.indications or [],
            "is_high_yield": r.is_high_yield,
            "is_nti": r.is_nti,
            "image_url": r.image_url,
        }
        for r in rows
    ]

    await _cache_set(cache_key, drugs)
    return drugs


@router.get("/drugs/{drug_slug}")
async def get_public_drug(
    drug_slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Public drug page — educational info only, NO dosing data.

    Slug is derived from drug name: 'Amoxicillin' → 'amoxicillin'
    Falls back to UUID lookup if slug not found.
    """
    await check_public_rate_limit(request)

    cache_key = f"pub_drug:{drug_slug}"
    cached = await _cache_get(cache_key)
    if cached:
        return cached

    # Try UUID lookup first
    drug = None
    try:
        uid = UUID(drug_slug)
        result = await db.execute(select(Drug).where(Drug.id == uid))
        drug = result.scalar_one_or_none()
    except (ValueError, AttributeError):
        pass

    # Fall back to name-based slug lookup (scan and match)
    if not drug:
        result = await db.execute(select(Drug).order_by(Drug.name))
        all_drugs = result.scalars().all()
        for d in all_drugs:
            if _slugify(d.name) == drug_slug:
                drug = d
                break

    if not drug:
        raise HTTPException(status_code=404, detail="Drug not found")

    response = {
        "id": str(drug.id),
        "slug": _slugify(drug.name),
        "name": drug.name,
        "generic_name": drug.generic_name,
        "drug_class": drug.drug_class,
        "mechanism": drug.mechanism,
        "indications": drug.indications or [],
        "contraindications": drug.contraindications or [],
        "black_box_warning": drug.black_box_warning,
        "is_high_yield": bool(drug.is_high_yield),
        "is_nti": bool(drug.is_nti),
        "image_url": drug.image_url,
        # INTENTIONALLY excluded: dosing, adverse_effects
        "disclaimer": (
            "This is educational information only. Dosing and treatment decisions "
            "must be made by a licensed healthcare provider. Do not self-medicate."
        ),
    }

    await _cache_set(cache_key, response)
    return response


# ── /public/quiz ──────────────────────────────────────────────────────────────

@router.get("/quiz")
async def list_public_quizzes(
    request: Request,
    category: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List active public quizzes."""
    await check_public_rate_limit(request)

    cache_key = f"pub_quiz_list:{category or '*'}"
    cached = await _cache_get(cache_key)
    if cached:
        return cached

    stmt = select(
        PublicQuiz.slug, PublicQuiz.title, PublicQuiz.description,
        PublicQuiz.category, PublicQuiz.play_count,
    ).where(PublicQuiz.is_active.is_(True)).order_by(PublicQuiz.created_at)

    if category:
        stmt = stmt.where(PublicQuiz.category == category)

    result = await db.execute(stmt)
    rows = result.all()

    quizzes = [
        {
            "slug": r.slug,
            "title": r.title,
            "description": r.description,
            "category": r.category,
            "play_count": r.play_count,
        }
        for r in rows
    ]

    await _cache_set(cache_key, quizzes, ttl=300)
    return quizzes


@router.get("/quiz/{slug}")
async def get_public_quiz(
    slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Quiz detail — questions WITHOUT correct answers (stripped for client)."""
    await check_public_rate_limit(request)

    cache_key = f"pub_quiz:{slug}"
    cached = await _cache_get(cache_key)
    if cached:
        return cached

    result = await db.execute(
        select(PublicQuiz).where(PublicQuiz.slug == slug).where(PublicQuiz.is_active.is_(True))
    )
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    public_questions = [
        {
            "question": q.get("question", ""),
            "options": q.get("options", {}),
        }
        for q in (quiz.questions or [])
    ]

    response = {
        "slug": quiz.slug,
        "title": quiz.title,
        "description": quiz.description,
        "category": quiz.category,
        "question_count": len(public_questions),
        "questions": public_questions,
        "play_count": quiz.play_count,
    }

    await _cache_set(cache_key, response, ttl=300)
    return response


@router.post("/quiz/{slug}/submit")
async def submit_quiz_result(
    slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Submit anonymous quiz result — returns answers + score + percentile.

    Body: {"answers": {"0": "A", "1": "C", ...}}
    """
    await check_public_rate_limit(request)

    body = await request.json()
    user_answers: dict[str, str] = body.get("answers", {})

    result = await db.execute(
        select(PublicQuiz).where(PublicQuiz.slug == slug).where(PublicQuiz.is_active.is_(True))
    )
    quiz = result.scalar_one_or_none()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    questions = quiz.questions or []
    correct_count = 0
    results_list = []
    for i, q in enumerate(questions):
        user_ans = user_answers.get(str(i), "").upper()
        correct_ans = q.get("correct", "").upper()
        is_correct = user_ans == correct_ans
        if is_correct:
            correct_count += 1
        results_list.append({
            "question": q.get("question", ""),
            "options": q.get("options", {}),
            "user_answer": user_ans,
            "correct_answer": correct_ans,
            "is_correct": is_correct,
            "explanation": q.get("explanation", ""),
        })

    total_q = len(questions)
    score_pct = round(correct_count / total_q * 100) if total_q else 0

    # Aggregate stats in Redis
    redis = await get_redis()
    stats_key = f"pub_quiz_stats:{slug}"
    pipe = redis.pipeline()
    pipe.hincrby(stats_key, "total_plays", 1)
    pipe.hincrby(stats_key, f"score_{correct_count}", 1)
    await pipe.execute()

    # Increment DB play_count
    try:
        await db.execute(
            PublicQuiz.__table__.update()
            .where(PublicQuiz.slug == slug)
            .values(play_count=PublicQuiz.play_count + 1)
        )
        await db.commit()
    except Exception:
        pass

    # Calculate percentile
    stats = await redis.hgetall(stats_key)
    total_plays = int(stats.get(b"total_plays", stats.get("total_plays", 1)))
    scored_lte = sum(
        int(v) for k, v in stats.items()
        if (k if isinstance(k, str) else k.decode()).startswith("score_")
        and int((k if isinstance(k, str) else k.decode())[6:]) <= correct_count
    )
    percentile = round(scored_lte / total_plays * 100) if total_plays else 50

    return {
        "score": correct_count,
        "total": total_q,
        "score_pct": score_pct,
        "percentile": percentile,
        "results": results_list,
        "total_plays": total_plays,
    }


# ── /public/decks ─────────────────────────────────────────────────────────────

@router.get("/decks/{token}")
async def get_shared_deck(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """View a shared flashcard deck by token — no authentication required."""
    await check_public_rate_limit(request)

    result = await db.execute(
        select(SharedDeck).where(SharedDeck.token == token).where(SharedDeck.is_active.is_(True))
    )
    deck = result.scalar_one_or_none()
    if not deck:
        raise HTTPException(status_code=404, detail="Deck not found or link has been deactivated")

    try:
        await db.execute(
            SharedDeck.__table__.update()
            .where(SharedDeck.token == token)
            .values(view_count=SharedDeck.view_count + 1)
        )
        await db.commit()
    except Exception:
        pass

    return {
        "token": deck.token,
        "name": deck.name,
        "description": deck.description,
        "card_count": len(deck.cards) if deck.cards else 0,
        "cards": [
            {
                "question": c.get("question", ""),
                "answer": c.get("answer", ""),
                "difficulty": c.get("difficulty", "medium"),
            }
            for c in (deck.cards or [])
        ],
        "view_count": deck.view_count,
        "created_at": deck.created_at.isoformat() if deck.created_at else None,
    }


# ── Pet owner modules (PET-*) ─────────────────────────────────────────────────

PET_DISCLAIMER = (
    "⚠️ This content is for educational purposes only and does not constitute "
    "veterinary medical advice. If your pet is unwell, contact a veterinarian immediately."
)


@router.get("/pets")
async def list_public_pets(
    request: Request,
    _: None = Depends(check_public_rate_limit),
    db: AsyncSession = Depends(get_db),
):
    """List all public PET-* modules with lesson summaries."""
    cache_key = "pub_pets_list"
    cached = await _cache_get(cache_key)
    if cached:
        return cached

    result = await db.execute(
        select(Module).where(
            Module.code.like("PET-%"),
            Module.is_published == True,
        ).order_by(Module.module_order)
    )
    modules = result.scalars().all()

    items = []
    for mod in modules:
        lessons_result = await db.execute(
            select(Lesson).where(Lesson.module_id == mod.id).order_by(Lesson.lesson_order)
        )
        lessons = lessons_result.scalars().all()

        slug = _slugify(mod.title_en or mod.title)
        items.append({
            "module_code": mod.code,
            "slug": slug,
            "title": mod.title_en or mod.title,
            "description": (mod.content or {}).get("meta", {}).get("description", ""),
            "lesson_count": len(lessons),
            "lessons": [
                {
                    "slug": _slugify(l.title),
                    "title": l.title,
                    "lay_summary_preview": (l.lay_summary or "")[:200] + "…" if l.lay_summary else None,
                }
                for l in lessons
            ],
        })

    response = {"modules": items, "disclaimer": PET_DISCLAIMER}
    await _cache_set(cache_key, response)
    return response


@router.get("/pets/{module_slug}")
async def get_public_pet_module(
    module_slug: str,
    request: Request,
    _: None = Depends(check_public_rate_limit),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific PET module's public content."""
    cache_key = f"pub_pet:{module_slug}"
    cached = await _cache_get(cache_key)
    if cached:
        return cached

    # Fetch all PET modules and find by slug
    result = await db.execute(
        select(Module).where(
            Module.code.like("PET-%"),
            Module.is_published == True,
        )
    )
    modules = result.scalars().all()

    module = None
    for mod in modules:
        if _slugify(mod.title_en or mod.title) == module_slug or mod.code.lower() == module_slug.lower():
            module = mod
            break

    if not module:
        raise HTTPException(status_code=404, detail="Pet module not found")

    lessons_result = await db.execute(
        select(Lesson).where(Lesson.module_id == module.id).order_by(Lesson.lesson_order)
    )
    lessons = lessons_result.scalars().all()

    # Aggregate all glossary terms, deduplicated by term
    glossary: dict[str, str] = {}
    for lesson in lessons:
        for entry in (lesson.lay_glossary or []):
            term = entry.get("term", "")
            if term and term not in glossary:
                glossary[term] = entry.get("simple_definition", "")

    response = {
        "module_code": module.code,
        "slug": module_slug,
        "title": module.title_en or module.title,
        "lessons": [
            {
                "slug": _slugify(l.title),
                "title": l.title,
                "lay_summary": l.lay_summary,
                "lay_glossary": l.lay_glossary or [],
                "key_points": (l.content or {}).get("key_points", []) if isinstance(l.content, dict) else [],
            }
            for l in lessons
        ],
        "glossary": [{"term": k, "simple_definition": v} for k, v in glossary.items()],
        "disclaimer": PET_DISCLAIMER,
    }
    await _cache_set(cache_key, response)
    return response


# ── /public/stats ─────────────────────────────────────────────────────────────

@router.get("/stats")
async def get_public_stats(
    _: None = Depends(check_public_rate_limit),
    db: AsyncSession = Depends(get_db),
):
    """Platform counters for the landing page."""
    cache_key = "pub_stats"
    cached = await _cache_get(cache_key)
    if cached:
        return cached

    article_count = await db.scalar(
        select(func.count(Article.id)).where(
            Article.is_published == True,
            Article.review_status == "published",
            Article.verification_status.in_(["passed", "human_reviewed"]),
        )
    ) or 0
    module_count = await db.scalar(
        select(func.count(Module.id)).where(Module.is_published == True)
    ) or 0
    drug_count = await db.scalar(select(func.count(Drug.id))) or 0
    flashcard_count = await db.scalar(select(func.count(Flashcard.id))) or 0

    result = {
        "articles": article_count,
        "modules": module_count,
        "drugs": drug_count,
        "flashcards": flashcard_count,
        "languages": 7,
    }
    await _cache_set(cache_key, result, ttl=21600)  # 6h
    return result


# ── /public/content-sources ───────────────────────────────────────────────────

@router.get("/content-sources", response_model=list[ContentSourceOut])
async def list_content_sources(
    source_type: str | None = None,
    _: None = Depends(check_public_rate_limit),
    db: AsyncSession = Depends(get_db),
):
    """List all verified content sources used by MedMind.

    Public endpoint — no auth required.
    Supports optional ?source_type= filter.
    """
    cache_key = f"pub_content_sources:{source_type or 'all'}"
    cached = await _cache_get(cache_key)
    if cached:
        return cached

    stmt = select(ContentSource).order_by(
        ContentSource.source_type, ContentSource.title
    )
    if source_type:
        stmt = stmt.where(ContentSource.source_type == source_type)

    rows = (await db.execute(stmt)).scalars().all()
    result = [
        {
            "slug": r.slug,
            "title": r.title,
            "publisher": r.publisher,
            "url": r.url,
            "license": r.license,
            "license_url": r.license_url,
            "text_reuse_allowed": r.text_reuse_allowed,
            "attribution_template": r.attribution_template,
            "source_type": r.source_type,
            "verified_at": r.verified_at,
            "notes": r.notes,
        }
        for r in rows
    ]
    await _cache_set(cache_key, result, ttl=CACHE_TTL)
    return result


# ── B5: Anonymous Free Practice ───────────────────────────────────────────────

@router.get("/practice/free")
async def free_practice_questions(
    request: Request,
    category: Optional[str] = Query(None, description="NCLEX category filter"),
    limit: int = Query(5, ge=1, le=20, description="Questions per batch (max 20)"),
    db=Depends(get_db),
):
    """Serve up to N practice questions per day to anonymous users.

    Daily limit enforced by IP (hashed — IP never stored raw).
    Returns:
        {
            "questions": [...],
            "used": int,
            "limit": int,
            "remaining": int,
            "paywall": bool,  # True when limit exhausted
        }
    """
    from datetime import date as _date
    from app.core.freemium import check_anon_limit, increment_anon_usage, FREEMIUM_CONFIG
    from app.models.models import MCQQuestion
    import random

    client_ip = (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    today = str(_date.today())
    status = await check_anon_limit(client_ip, today)

    if not status["allowed"]:
        return {
            "questions": [],
            "used": status["used"],
            "limit": status["limit"],
            "remaining": 0,
            "paywall": True,
            "paywall_message": (
                f"You've used your {status['limit']} free questions for today. "
                "Register for free to save progress, or upgrade to practice without limits."
            ),
        }

    remaining = status["remaining"]
    serve_count = min(limit, remaining)

    stmt = (
        select(
            MCQQuestion.id,
            MCQQuestion.question,
            MCQQuestion.options,
            MCQQuestion.correct,
            MCQQuestion.explanation,
            MCQQuestion.rationales,
            MCQQuestion.difficulty,
            MCQQuestion.question_type,
            MCQQuestion.nclex_client_needs,
        )
        .where(
            MCQQuestion.status == "active",
            MCQQuestion.is_flagged.is_(False),
        )
    )
    if category:
        stmt = stmt.where(MCQQuestion.nclex_client_needs == category)

    stmt = stmt.order_by(func.random()).limit(serve_count * 3)
    rows = (await db.execute(stmt)).all()

    selected = rows[:serve_count]
    for _ in selected:
        await increment_anon_usage(client_ip, today)

    new_status = await check_anon_limit(client_ip, today)

    return {
        "questions": [
            {
                "id": str(r.id),
                "question": r.question,
                "options": r.options,
                "correct": r.correct,
                "explanation": r.explanation,
                "rationales": r.rationales,
                "difficulty": r.difficulty,
                "question_type": r.question_type,
                "nclex_category": r.nclex_client_needs,
            }
            for r in selected
        ],
        "used": new_status["used"],
        "limit": new_status["limit"],
        "remaining": new_status["remaining"],
        "paywall": not new_status["allowed"],
    }


@router.get("/practice/free/status")
async def free_practice_status(request: Request):
    """Return the anonymous user's current daily question usage status."""
    from datetime import date as _date
    from app.core.freemium import check_anon_limit

    client_ip = (
        request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    today = str(_date.today())
    status = await check_anon_limit(client_ip, today)
    return status


@router.get("/freemium/config")
async def freemium_config():
    """Return the freemium feature configuration (public — shown in paywall UI)."""
    from app.core.freemium import FREEMIUM_CONFIG
    return {
        "anon_daily_questions": FREEMIUM_CONFIG["anon_daily_questions"],
        "anon_features": FREEMIUM_CONFIG["anon_features"],
        "free_registered_features": FREEMIUM_CONFIG["free_registered_features"],
        "paid_features": FREEMIUM_CONFIG["paid_features"],
    }
