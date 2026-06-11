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
from app.models.models import Lesson, Module, Drug, Specialty, PublicQuiz, SharedDeck
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
    description: Optional[str]
    lay_summary: Optional[str]       # first lesson's lay_summary
    lesson_count: int
    specialty: Optional[str]


class PublicTopicDetail(BaseModel):
    module_code: str
    slug: str
    title: str
    description: Optional[str]
    specialty: Optional[str]
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
    db: AsyncSession = Depends(get_db),
):
    """Aggregated glossary from all lessons with lay_glossary set.

    Returns deduplicated terms sorted A-Z.
    Cached for 1 hour. Rate limited 120 req/min per IP.
    """
    await check_public_rate_limit(request)

    cache_key = f"pub_glossary:{letter or '*'}:{search or ''}:{limit}"
    cached = await _cache_get(cache_key)
    if cached:
        return cached

    # Fetch all lessons with lay_glossary and their modules
    stmt = (
        select(Lesson.title, Lesson.lay_glossary, Module.code, Module.title)
        .join(Module, Lesson.module_id == Module.id)
        .where(Lesson.lay_glossary.isnot(None))
        .where(Lesson.status == "published")
    )
    result = await db.execute(stmt)
    rows = result.all()

    # Aggregate and deduplicate terms
    seen: dict[str, PublicGlossaryTerm] = {}
    for lesson_title, glossary, module_code, module_title in rows:
        if not isinstance(glossary, list):
            continue
        for entry in glossary:
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
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List modules that have at least one lesson with lay_summary."""
    await check_public_rate_limit(request)

    cache_key = f"pub_topics:{specialty or '*'}:{limit}"
    cached = await _cache_get(cache_key)
    if cached:
        return cached

    # Modules with lay_summary lessons
    stmt = (
        select(
            Module.code, Module.title, Module.description,
            Specialty.name.label("specialty_name"),
            func.count(Lesson.id).label("lesson_count"),
            func.max(Lesson.lay_summary).label("sample_summary"),
        )
        .join(Lesson, Lesson.module_id == Module.id)
        .outerjoin(Specialty, Module.specialty_id == Specialty.id)
        .where(Lesson.lay_summary.isnot(None))
        .where(Lesson.status == "published")
        .group_by(Module.code, Module.title, Module.description, Specialty.name)
        .order_by(Module.code)
        .limit(limit)
    )
    if specialty:
        stmt = stmt.where(Specialty.name.ilike(f"%{specialty}%"))

    result = await db.execute(stmt)
    rows = result.all()

    topics = [
        PublicTopic(
            module_code=row.code,
            slug=_slugify(row.code),
            title=row.title,
            description=row.description,
            lay_summary=row.sample_summary[:200] if row.sample_summary else None,
            lesson_count=row.lesson_count,
            specialty=row.specialty_name,
        ).model_dump()
        for row in rows
    ]

    await _cache_set(cache_key, topics)
    return topics


@router.get("/topics/{module_slug}")
async def get_public_topic(
    module_slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Single topic (module) detail with all lay_summary lessons."""
    await check_public_rate_limit(request)

    cache_key = f"pub_topic:{module_slug}"
    cached = await _cache_get(cache_key)
    if cached:
        return cached

    # Find module by slugified code
    stmt = (
        select(Module, Specialty.name.label("specialty_name"))
        .outerjoin(Specialty, Module.specialty_id == Specialty.id)
    )
    result = await db.execute(stmt)
    rows = result.all()

    module = None
    specialty_name = None
    for mod, spec in rows:
        if _slugify(mod.code) == module_slug:
            module = mod
            specialty_name = spec
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

    lesson_data = []
    total_terms = 0
    for l in lessons:
        if l.lay_summary or l.lay_glossary:
            glossary = l.lay_glossary or []
            total_terms += len(glossary) if isinstance(glossary, list) else 0
            lesson_data.append({
                "title": l.title,
                "lay_summary": l.lay_summary,
                "lay_glossary": [
                    {"term": t["term"], "slug": _slugify(t["term"]), "simple_definition": t["simple_definition"]}
                    for t in (glossary if isinstance(glossary, list) else [])
                    if isinstance(t, dict)
                ],
                "order": l.lesson_order,
            })

    if not lesson_data:
        raise HTTPException(status_code=404, detail="No public content available for this topic yet")

    response = PublicTopicDetail(
        module_code=module.code,
        slug=module_slug,
        title=module.title,
        description=module.description,
        specialty=specialty_name,
        lessons=lesson_data,
        total_glossary_terms=total_terms,
    ).model_dump()

    await _cache_set(cache_key, response)
    return response


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
