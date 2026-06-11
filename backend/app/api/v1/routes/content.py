"""Content routes — specialties, modules, lessons, flashcards, MCQ, cases."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.core.database import get_db
from app.models.models import Specialty, Module, Lesson, Flashcard, MCQQuestion, ClinicalCase, User, Drug, Article, UserProgress
from app.schemas.schemas import (
    SpecialtyOut, ModuleOut, ModuleDetail, LessonOut, LessonDetail,
    LessonLayView, FlashcardOut, MCQQuestionOut, ClinicalCaseOut, ClinicalCaseDetail, DrugOut
)
from app.api.deps import get_current_user, get_current_user_optional
from app.core.cache import get_cached, set_cached

router = APIRouter(tags=["content"])

# Tiers that can access all specialties (not just BASE-*)
PAID_TIERS = {"student", "pro", "clinic", "lifetime"}
VET_TIERS = {"pro", "clinic", "lifetime"}


# ============================================================
# SPECIALTIES
# ============================================================
@router.get("/specialties", response_model=List[SpecialtyOut])
async def list_specialties(
    vet: bool = False,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    cache_key = f"specialties:vet={vet}"
    if cached := await get_cached(cache_key):
        return cached

    stmt = select(Specialty).where(Specialty.is_active == True)
    if vet:
        stmt = stmt.where(Specialty.is_veterinary == True)
    else:
        stmt = stmt.where(Specialty.is_veterinary == False)
    result = await db.execute(stmt.order_by(Specialty.name))
    specialties = result.scalars().all()

    # Attach module counts
    count_result = await db.execute(
        select(Module.specialty_id, func.count(Module.id).label("cnt"))
        .where(Module.is_published == True)
        .group_by(Module.specialty_id)
    )
    module_counts = {row.specialty_id: row.cnt for row in count_result.all()}

    out = []
    for spec in specialties:
        d = SpecialtyOut.model_validate(spec)
        d.module_count = module_counts.get(spec.id, 0)
        out.append(d)
    await set_cached(cache_key, [o.model_dump() for o in out], ttl=600)
    return out


@router.get("/specialties/{specialty_id}/modules", response_model=List[ModuleOut])
async def list_specialty_modules(
    specialty_id: UUID,
    language: Optional[str] = Query(None, description="Filter by content language"),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    cache_key = f"specialty_modules:{specialty_id}:{language or 'all'}"
    if cached := await get_cached(cache_key):
        return cached

    stmt = (
        select(Module)
        .where(Module.specialty_id == specialty_id, Module.is_published == True)
        .order_by(Module.module_order)
    )
    if language:
        stmt = stmt.where(Module.language == language)
    result = await db.execute(stmt)
    modules = result.scalars().all()
    if not modules:
        return []

    module_ids = [m.id for m in modules]

    # Batch-count lessons, flashcards, MCQs
    lesson_counts_result = await db.execute(
        select(Lesson.module_id, func.count(Lesson.id).label("cnt"))
        .where(Lesson.module_id.in_(module_ids))
        .group_by(Lesson.module_id)
    )
    lesson_counts = {row.module_id: row.cnt for row in lesson_counts_result.all()}

    fc_counts_result = await db.execute(
        select(Flashcard.module_id, func.count(Flashcard.id).label("cnt"))
        .where(Flashcard.module_id.in_(module_ids))
        .group_by(Flashcard.module_id)
    )
    fc_counts = {row.module_id: row.cnt for row in fc_counts_result.all()}

    mcq_counts_result = await db.execute(
        select(MCQQuestion.module_id, func.count(MCQQuestion.id).label("cnt"))
        .where(MCQQuestion.module_id.in_(module_ids))
        .group_by(MCQQuestion.module_id)
    )
    mcq_counts = {row.module_id: row.cnt for row in mcq_counts_result.all()}

    out = []
    for mod in modules:
        d = ModuleOut.model_validate(mod)
        d.lesson_count = lesson_counts.get(mod.id, 0)
        d.flashcard_count = fc_counts.get(mod.id, 0)
        d.mcq_count = mcq_counts.get(mod.id, 0)
        out.append(d)
    await set_cached(cache_key, [o.model_dump() for o in out], ttl=300)
    return out


# ============================================================
# MODULES — public list (all published, for student browse page)
# ============================================================
@router.get("/modules", response_model=List[ModuleOut])
async def list_all_modules(
    search: Optional[str] = Query(None),
    specialty_code: Optional[str] = Query(None),
    vet: bool = Query(False),
    language: Optional[str] = Query(None, description="Filter by content language (e.g. 'en', 'ru')"),
    limit: int = Query(200, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Return all published modules. Used by the student browse page."""
    stmt = (
        select(Module)
        .where(Module.is_published == True, Module.is_veterinary == vet)
        .order_by(Module.is_fundamental.desc(), Module.module_order)
        .limit(limit)
    )
    if search:
        stmt = stmt.where(or_(
            Module.title.ilike(f"%{search}%"),
            Module.description.ilike(f"%{search}%"),
        ))
    if specialty_code:
        stmt = stmt.join(Specialty, Specialty.id == Module.specialty_id).where(
            Specialty.code == specialty_code
        )
    if language:
        stmt = stmt.where(Module.language == language)

    modules = (await db.execute(stmt)).scalars().all()
    if not modules:
        return []

    module_ids = [m.id for m in modules]

    # Batch counts
    lesson_counts = {r.module_id: r.cnt for r in (await db.execute(
        select(Lesson.module_id, func.count(Lesson.id).label("cnt"))
        .where(Lesson.module_id.in_(module_ids)).group_by(Lesson.module_id)
    )).all()}
    fc_counts = {r.module_id: r.cnt for r in (await db.execute(
        select(Flashcard.module_id, func.count(Flashcard.id).label("cnt"))
        .where(Flashcard.module_id.in_(module_ids)).group_by(Flashcard.module_id)
    )).all()}
    mcq_counts = {r.module_id: r.cnt for r in (await db.execute(
        select(MCQQuestion.module_id, func.count(MCQQuestion.id).label("cnt"))
        .where(MCQQuestion.module_id.in_(module_ids)).group_by(MCQQuestion.module_id)
    )).all()}

    # Specialty names
    spec_ids = list({m.specialty_id for m in modules if m.specialty_id})
    spec_map: dict = {}
    if spec_ids:
        spec_rows = (await db.execute(
            select(Specialty.id, Specialty.name).where(Specialty.id.in_(spec_ids))
        )).all()
        spec_map = {r.id: r.name for r in spec_rows}

    out = []
    for mod in modules:
        d = ModuleOut.model_validate(mod)
        d.lesson_count = lesson_counts.get(mod.id, 0)
        d.flashcard_count = fc_counts.get(mod.id, 0)
        d.mcq_count = mcq_counts.get(mod.id, 0)
        d.specialty_name = spec_map.get(mod.specialty_id, "")
        out.append(d)
    return out


@router.get("/modules/{module_id}", response_model=ModuleDetail)
async def get_module(
    module_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    cache_key = f"module:{module_id}"
    if cached := await get_cached(cache_key):
        return cached

    result = await db.execute(select(Module).where(Module.id == module_id, Module.is_published == True))
    module = result.scalar_one_or_none()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    # Access control: free users can only access BASE-* modules
    if user and user.subscription_tier not in PAID_TIERS:
        if not module.is_fundamental:
            raise HTTPException(
                status_code=403,
                detail="Upgrade to Student plan to access specialty modules"
            )
    await set_cached(cache_key, ModuleDetail.model_validate(module).model_dump(), ttl=300)
    return module


# ============================================================
# LESSONS
# ============================================================
@router.get("/modules/{module_id}/lessons", response_model=List[LessonOut])
async def list_module_lessons(
    module_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    result = await db.execute(
        select(Lesson)
        .where(Lesson.module_id == module_id)
        .order_by(Lesson.lesson_order)
    )
    return result.scalars().all()


@router.get("/lessons/{lesson_id}")
async def get_lesson(
    lesson_id: UUID,
    view: Optional[str] = Query(None, description="Pass 'lay' for plain-language summary"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Lesson).where(Lesson.id == lesson_id))
    lesson = result.scalar_one_or_none()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Access control
    mod_result = await db.execute(select(Module).where(Module.id == lesson.module_id))
    module = mod_result.scalar_one_or_none()
    if module and not module.is_fundamental and user.subscription_tier not in PAID_TIERS:
        raise HTTPException(status_code=403, detail="Upgrade to access specialty content")

    # ?view=lay — return simplified version for non-specialists
    if view == "lay":
        return LessonLayView.model_validate(lesson)

    return LessonDetail.model_validate(lesson)


# ============================================================
# FLASHCARDS
# ============================================================
@router.get("/modules/{module_id}/flashcards", response_model=List[FlashcardOut])
async def list_flashcards(
    module_id: UUID,
    due_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Flashcard).where(Flashcard.module_id == module_id)

    if due_only:
        from datetime import datetime
        from app.models.models import FlashcardReview
        # Return flashcards that are due for review (or never reviewed)
        subq = (
            select(FlashcardReview.flashcard_id)
            .where(
                FlashcardReview.user_id == user.id,
                FlashcardReview.next_review_at > datetime.utcnow(),
            )
        )
        stmt = stmt.where(~Flashcard.id.in_(subq))

    result = await db.execute(stmt)
    return result.scalars().all()


# ============================================================
# MCQ QUESTIONS
# ============================================================
@router.get("/modules/{module_id}/mcq", response_model=List[MCQQuestionOut])
async def list_mcq(
    module_id: UUID,
    limit: int = Query(10, le=50),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(MCQQuestion)
        .where(MCQQuestion.module_id == module_id)
        .limit(limit)
    )
    return result.scalars().all()


# ============================================================
# CLINICAL CASES
# ============================================================

def _apply_case_translation(case, tr) -> dict:
    """Merge a ClinicalCase ORM row with a translation row into a dict."""
    d = {
        "id": str(case.id),
        "module_id": str(case.module_id),
        "title": tr.title if tr and tr.title else case.title,
        "specialty": case.specialty,
        "presentation": tr.presentation if tr and tr.presentation else case.presentation,
        "vitals": case.vitals,
        "diagnosis": case.diagnosis,
        "differential_diagnosis": case.differential_diagnosis,
        "management": (tr.management if tr and tr.management else case.management) or [],
        "teaching_points": (tr.teaching_points if tr and tr.teaching_points else case.teaching_points) or [],
        "difficulty": case.difficulty or "medium",
        "steps": case.steps,
        "initial_step_id": case.initial_step_id,
        "ideal_path": case.ideal_path,
        "max_score": case.max_score or 100,
        "content": case.content,
    }
    return d


@router.get("/cases")
async def list_all_cases(
    locale: str = Query("en", max_length=5),
    specialty: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    search: Optional[str] = Query(None, max_length=100),
    limit: int = Query(100, le=300),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return all clinical cases, optionally filtered, with locale translations."""
    from sqlalchemy import text as sql_text
    from sqlalchemy.orm import aliased

    stmt = select(ClinicalCase)
    if specialty:
        stmt = stmt.where(ClinicalCase.specialty.ilike(f"%{specialty}%"))
    if difficulty:
        stmt = stmt.where(ClinicalCase.difficulty == difficulty)
    if search:
        stmt = stmt.where(ClinicalCase.title.ilike(f"%{search}%"))
    stmt = stmt.order_by(ClinicalCase.difficulty, ClinicalCase.title).limit(limit).offset(offset)

    result = await db.execute(stmt)
    cases = result.scalars().all()

    if not cases:
        return []

    # Fetch translations for all cases in one query
    case_ids = [c.id for c in cases]
    if locale != "en":
        tr_result = await db.execute(
            sql_text(
                "SELECT case_id, title, presentation, teaching_points, management "
                "FROM clinical_case_translations "
                "WHERE case_id = ANY(:ids) AND locale = :locale"
            ).bindparams(ids=case_ids, locale=locale)
        )
        tr_map = {str(row.case_id): row for row in tr_result}
    else:
        tr_map = {}

    return [_apply_case_translation(c, tr_map.get(str(c.id))) for c in cases]


@router.get("/modules/{module_id}/cases")
async def list_cases(
    module_id: UUID,
    locale: str = Query("en", max_length=5),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from sqlalchemy import text as sql_text

    result = await db.execute(
        select(ClinicalCase).where(ClinicalCase.module_id == module_id)
    )
    cases = result.scalars().all()

    if not cases or locale == "en":
        return [_apply_case_translation(c, None) for c in cases]

    case_ids = [c.id for c in cases]
    tr_result = await db.execute(
        sql_text(
            "SELECT case_id, title, presentation, teaching_points, management "
            "FROM clinical_case_translations WHERE case_id = ANY(:ids) AND locale = :locale"
        ).bindparams(ids=case_ids, locale=locale)
    )
    tr_map = {str(row.case_id): row for row in tr_result}
    return [_apply_case_translation(c, tr_map.get(str(c.id))) for c in cases]


@router.get("/cases/{case_id}")
async def get_case(
    case_id: UUID,
    locale: str = Query("en", max_length=5),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from sqlalchemy import text as sql_text

    result = await db.execute(select(ClinicalCase).where(ClinicalCase.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    tr = None
    if locale != "en":
        tr_result = await db.execute(
            sql_text(
                "SELECT case_id, title, presentation, teaching_points, management "
                "FROM clinical_case_translations WHERE case_id = :cid AND locale = :locale"
            ).bindparams(cid=case_id, locale=locale)
        )
        tr = tr_result.first()

    return _apply_case_translation(case, tr)


# ============================================================
# DRUGS
# ============================================================
@router.get("/drugs/sitemap-data")
async def drugs_sitemap_data(db: AsyncSession = Depends(get_db)):
    """Public endpoint for sitemap generation — returns all drug IDs and available langs."""
    result = await db.execute(
        select(Drug.id, Drug.translations).order_by(Drug.name)
    )
    rows = result.all()
    return [
        {
            "id": str(r[0]),
            "available_langs": list((r[1] or {}).keys()),
        }
        for r in rows
    ]


@router.get("/drugs/browse")
async def browse_drugs(
    page: int = Query(1, ge=1),
    limit: int = Query(24, ge=1, le=100),
    drug_class: Optional[str] = Query(None),
    vet: Optional[bool] = Query(None),
    high_yield: Optional[bool] = Query(None),
    lang: str = Query("en", max_length=5),
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user_optional),
):
    """Browse all drugs with pagination and optional filters."""
    from sqlalchemy import func
    q = select(Drug)
    if drug_class:
        q = q.where(Drug.drug_class.ilike(f"%{drug_class}%"))
    if vet is not None:
        q = q.where(Drug.is_veterinary == vet)
    if high_yield is not None:
        q = q.where(Drug.is_high_yield == high_yield)

    total_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(total_q)).scalar_one()

    drugs_q = q.order_by(Drug.name).offset((page - 1) * limit).limit(limit)
    drugs = (await db.execute(drugs_q)).scalars().all()

    return {
        "items": [_drug_to_dict(d, lang) for d in drugs],
        "total": total,
        "page": page,
        "pages": max(1, (total + limit - 1) // limit),
        "limit": limit,
    }


@router.get("/drugs/classes")
async def get_drug_classes(
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user_optional),
):
    """Return distinct drug classes with counts."""
    from sqlalchemy import func
    result = await db.execute(
        select(Drug.drug_class, func.count(Drug.id).label("count"))
        .where(Drug.drug_class.isnot(None))
        .group_by(Drug.drug_class)
        .order_by(func.count(Drug.id).desc())
        .limit(30)
    )
    return [{"drug_class": r[0], "count": r[1]} for r in result.all()]


def _drug_to_dict(d: Drug, lang: str = "en") -> dict:
    """Return drug dict with optional locale overlay from translations."""
    tr = {}
    if lang and lang != "en" and d.translations:
        tr = (d.translations or {}).get(lang, {})
    return {
        "id": str(d.id),
        "name": d.name,                          # drug names stay in English always
        "generic_name": d.generic_name,
        "drug_class": tr.get("drug_class") or d.drug_class,
        "mechanism": tr.get("mechanism") or d.mechanism,
        "indications": tr.get("indications") or d.indications or [],
        "contraindications": tr.get("contraindications") or d.contraindications or [],
        "dosing": d.dosing or {},                # dosing stays English (medical standard)
        "adverse_effects": tr.get("adverse_effects") or d.adverse_effects or {},
        "interactions": d.interactions or [],
        "monitoring": d.monitoring or [],
        "black_box_warning": tr.get("black_box_warning") or d.black_box_warning,
        "is_high_yield": d.is_high_yield,
        "is_nti": d.is_nti,
        "is_veterinary": d.is_veterinary,
        "image_url": d.image_url,
        "available_langs": list((d.translations or {}).keys()),
    }


@router.get("/drugs")
async def search_drugs(
    q: str = Query(None, min_length=1, max_length=100),
    lang: str = Query("en", max_length=5),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from sqlalchemy import or_
    if not q:
        result = await db.execute(select(Drug).order_by(Drug.name).limit(24))
        return [_drug_to_dict(d, lang) for d in result.scalars().all()]
    result = await db.execute(
        select(Drug).where(
            or_(
                Drug.name.ilike(f"%{q}%"),
                Drug.generic_name.ilike(f"%{q}%"),
                Drug.drug_class.ilike(f"%{q}%"),
            )
        ).limit(20)
    )
    return [_drug_to_dict(d, lang) for d in result.scalars().all()]


@router.get("/drugs/{drug_id}")
async def get_drug_detail(
    drug_id: UUID,
    lang: str = Query("en", max_length=5),
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user_optional),
):
    """Return full drug detail with optional locale translation."""
    result = await db.execute(select(Drug).where(Drug.id == drug_id))
    drug = result.scalar_one_or_none()
    if not drug:
        raise HTTPException(status_code=404, detail="Drug not found")
    return _drug_to_dict(drug, lang)


@router.get("/drugs/{drug_id}/alternatives")
async def get_drug_alternatives(
    drug_id: UUID,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user_optional),
):
    """Return same-class drugs as alternatives/analogues."""
    result = await db.execute(select(Drug).where(Drug.id == drug_id))
    drug = result.scalar_one_or_none()
    if not drug:
        raise HTTPException(status_code=404, detail="Drug not found")

    alternatives = []
    if drug.drug_class:
        alts_result = await db.execute(
            select(Drug).where(
                Drug.drug_class == drug.drug_class,
                Drug.id != drug_id,
            ).limit(8)
        )
        same_class = alts_result.scalars().all()
        for alt in same_class:
            alternatives.append({
                "id": str(alt.id),
                "name": alt.name,
                "generic_name": alt.generic_name,
                "drug_class": alt.drug_class,
                "is_high_yield": alt.is_high_yield,
                "reason": "Same drug class",
            })

    # Also search by first word of class (broader match) if few results
    if len(alternatives) < 3 and drug.drug_class:
        first_word = drug.drug_class.split()[0]
        if first_word and len(first_word) > 3:
            broad_result = await db.execute(
                select(Drug).where(
                    Drug.drug_class.ilike(f"%{first_word}%"),
                    Drug.id != drug_id,
                    Drug.id.notin_([UUID(a["id"]) for a in alternatives]),
                ).limit(5)
            )
            for alt in broad_result.scalars().all():
                alternatives.append({
                    "id": str(alt.id),
                    "name": alt.name,
                    "generic_name": alt.generic_name,
                    "drug_class": alt.drug_class,
                    "is_high_yield": alt.is_high_yield,
                    "reason": f"Related class ({alt.drug_class})",
                })

    return {"drug_id": str(drug_id), "drug_name": drug.name, "alternatives": alternatives}


class InteractionCheckRequest(BaseModel):
    drug_ids: list[UUID]


@router.post("/drugs/check-interactions")
async def check_drug_interactions(
    data: InteractionCheckRequest,
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user_optional),
):
    """Check pairwise interactions for a list of drug IDs."""
    from app.services.drug_service import check_interactions
    if len(data.drug_ids) < 2:
        raise HTTPException(status_code=422, detail="At least 2 drug IDs required")
    interactions = await check_interactions(db, data.drug_ids)
    return {"interactions": interactions, "pairs_checked": len(data.drug_ids) * (len(data.drug_ids) - 1) // 2}


class DoseCalculateRequest(BaseModel):
    drug_name: str
    weight_kg: float
    dose_per_kg: float
    unit: str = "mg"
    age_years: float | None = None
    renal_gfr: float | None = None
    max_dose: float | None = None


@router.post("/drugs/calculate-dose")
async def calculate_drug_dose(
    data: DoseCalculateRequest,
    user = Depends(get_current_user_optional),
):
    """Calculate weight-based dose with renal adjustment."""
    from app.services.drug_service import calculate_dose
    return calculate_dose(
        drug_name=data.drug_name,
        weight_kg=data.weight_kg,
        age_years=data.age_years,
        renal_gfr=data.renal_gfr,
        dose_per_kg=data.dose_per_kg,
        unit=data.unit,
        max_dose=data.max_dose,
    )


# Species dose scaling factors vs human adult (approximate)
_SPECIES_FACTORS: dict[str, float] = {
    "canine": 1.0,
    "feline": 0.6,
    "equine": 10.0,
    "bovine": 12.0,
    "porcine": 1.2,
    "avian": 0.05,
    "exotic": 0.3,
}

class DosingResult(BaseModel):
    drug_name: str
    species: str
    human_dosing: dict
    species_dosing: dict
    note: str


@router.get("/drugs/dosing", response_model=DosingResult)
async def get_species_dosing(
    drug: str = Query(..., min_length=1, max_length=100, description="Drug name to look up"),
    species: str = Query(..., description="Target species (canine|feline|equine|bovine|porcine|avian|exotic)"),
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user_optional),
):
    """Return species-adjusted dosing for veterinary users (or any authenticated user in test mode)."""

    species = species.lower()
    if species not in _SPECIES_FACTORS:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown species '{species}'. Allowed: {', '.join(_SPECIES_FACTORS)}",
        )

    from sqlalchemy import or_
    result = await db.execute(
        select(Drug).where(
            or_(Drug.name.ilike(f"%{drug}%"), Drug.generic_name.ilike(f"%{drug}%"))
        ).limit(1)
    )
    db_drug = result.scalar_one_or_none()
    if not db_drug:
        raise HTTPException(status_code=404, detail=f"Drug '{drug}' not found")

    human_dosing: dict = db_drug.dosing or {}
    factor = _SPECIES_FACTORS[species]

    # Apply scaling factor to numeric dosing values where present
    species_dosing: dict = {}
    for route, info in human_dosing.items():
        if isinstance(info, dict) and "dose" in info:
            try:
                import re
                # Extract numeric part from strings like "5-10 mg/kg"
                raw = str(info["dose"])
                nums = re.findall(r"\d+(?:\.\d+)?", raw)
                if nums:
                    scaled_nums = [f"{float(n) * factor:.2f}" for n in nums]
                    # Replace originals with scaled values
                    scaled_dose = raw
                    for orig, scaled in zip(nums, scaled_nums):
                        scaled_dose = scaled_dose.replace(orig, scaled, 1)
                    species_dosing[route] = {**info, "dose": scaled_dose}
                else:
                    species_dosing[route] = info
            except Exception:
                species_dosing[route] = info
        else:
            species_dosing[route] = info

    return DosingResult(
        drug_name=db_drug.name,
        species=species,
        human_dosing=human_dosing,
        species_dosing=species_dosing,
        note=f"Doses scaled by factor ×{factor} for {species}. Always verify with a licensed veterinarian.",
    )


# ============================================================
# FULL-TEXT SEARCH
# ============================================================
class SearchResult(ModuleOut):
    match_type: str = "module"


class ArticleSearchItem(BaseModel):
    id: str
    slug: str
    title: str
    excerpt: str
    category: str

    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    modules: List[ModuleOut]
    lessons: List[LessonOut]
    articles: List[ArticleSearchItem]
    total: int


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=2, max_length=200),
    limit: int = Query(10, le=50),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Full-text search across modules, lessons, and articles."""
    # Search modules by title and description
    mod_stmt = (
        select(Module)
        .where(
            Module.is_published == True,
            or_(
                Module.title.ilike(f"%{q}%"),
                Module.description.ilike(f"%{q}%"),
            ),
        )
        .limit(limit)
    )
    # Apply access control for free users
    if not user or user.subscription_tier not in PAID_TIERS:
        mod_stmt = mod_stmt.where(Module.is_fundamental == True)

    mod_result = await db.execute(mod_stmt)
    modules = mod_result.scalars().all()

    # Search lessons by title
    lesson_stmt = (
        select(Lesson)
        .where(Lesson.title.ilike(f"%{q}%"))
        .limit(limit)
    )
    lesson_result = await db.execute(lesson_stmt)
    lessons = lesson_result.scalars().all()

    # Search published articles by title and excerpt (public, no auth needed)
    art_stmt = (
        select(Article)
        .where(
            Article.is_published == True,
            Article.review_status == "published",
            or_(
                Article.title.ilike(f"%{q}%"),
                Article.excerpt.ilike(f"%{q}%"),
            ),
        )
        .limit(limit)
    )
    art_result = await db.execute(art_stmt)
    articles = art_result.scalars().all()

    return SearchResponse(
        modules=modules,
        lessons=lessons,
        articles=[ArticleSearchItem(
            id=str(a.id),
            slug=a.slug,
            title=a.title,
            excerpt=a.excerpt,
            category=a.category,
        ) for a in articles],
        total=len(modules) + len(lessons) + len(articles),
    )


# ============================================================
# PUBMED SEARCH
# ============================================================
@router.get("/search/pubmed")
async def search_pubmed(
    q: str = Query(..., min_length=2, max_length=300),
    limit: int = Query(10, le=20),
    user = Depends(get_current_user_optional),
):
    """Search PubMed via NCBI E-utilities API."""
    from app.services.pubmed_service import PubMedService
    service = PubMedService()
    results = await service.search_articles(q, max_results=limit)
    return results


# ============================================================
# RECOMMENDATIONS
# ============================================================
@router.get("/recommendations")
async def get_recommendations(
    limit: int = Query(5, le=20),
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user_optional),
):
    """
    Hybrid recommendations:
    1. Collaborative filtering — modules popular among users with similar progress
    2. Content-based — not-yet-started modules ordered by curriculum order
    Merges both lists, deduplicates, respects tier and vet-mode.
    """
    from sqlalchemy import text as sql_text

    started_result = await db.execute(
        select(UserProgress.module_id).where(UserProgress.user_id == user.id)
    )
    started_ids = {row[0] for row in started_result.all()}
    is_free = user.subscription_tier == "free"
    prefs = user.preferences or {}
    vet_mode = bool(prefs.get("vet_mode"))

    # ── 1. Collaborative filtering ─────────────────────────────────────────────
    # "Users who studied the same modules also studied these" — ranked by popularity
    collab_ids: list = []
    if started_ids:
        try:
            collab_rows = await db.execute(sql_text("""
                WITH similar_users AS (
                    SELECT DISTINCT user_id
                    FROM user_progress
                    WHERE module_id = ANY(:started)
                      AND user_id != :uid
                    GROUP BY user_id
                    HAVING COUNT(*) >= LEAST(3, :min_overlap)
                )
                SELECT up.module_id, COUNT(*) AS cnt
                FROM user_progress up
                JOIN similar_users su ON su.user_id = up.user_id
                JOIN modules m ON m.id = up.module_id
                WHERE up.module_id != ALL(:started)
                  AND m.is_published = TRUE
                  AND (:free_only = FALSE OR m.is_fundamental = TRUE)
                GROUP BY up.module_id
                ORDER BY cnt DESC
                LIMIT :lim
            """).bindparams(
                started=list(started_ids),
                uid=user.id,
                min_overlap=max(1, len(started_ids) // 3),
                free_only=is_free,
                lim=limit,
            ))
            collab_ids = [row[0] for row in collab_rows]
        except Exception:
            pass  # Fallback to content-based if query fails

    # ── 2. Content-based (curriculum order, not yet started) ───────────────────
    cb_stmt = (
        select(Module)
        .where(
            Module.is_published == True,
            Module.id.not_in(started_ids) if started_ids else True,
            Module.id.not_in(collab_ids) if collab_ids else True,
        )
        .order_by(Module.module_order)
        .limit(limit)
    )
    if is_free:
        cb_stmt = cb_stmt.where(Module.is_fundamental == True)
    if vet_mode:
        cb_stmt = cb_stmt.join(Specialty, Module.specialty_id == Specialty.id).where(
            Specialty.is_veterinary == True
        )
    cb_result = await db.execute(cb_stmt)
    cb_modules = cb_result.scalars().all()

    # ── 3. Fetch collab modules and merge ──────────────────────────────────────
    final_modules = list(cb_modules)
    if collab_ids:
        collab_result = await db.execute(
            select(Module).where(Module.id.in_(collab_ids))
        )
        collab_modules = collab_result.scalars().all()
        # Prepend collaborative results (higher priority)
        final_modules = collab_modules + final_modules

    final_modules = final_modules[:limit]
    return {
        "modules": final_modules,
        "total": len(final_modules),
        "collaborative_count": len(collab_ids),
        "vet_filtered": vet_mode,
    }


@router.get("/recommendations/daily")
async def get_daily_plan(
    db: AsyncSession = Depends(get_db),
    user = Depends(get_current_user_optional),
):
    """Return today's learning plan based on due flashcards and incomplete modules."""
    from app.models.models import FlashcardReview as FR
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Count due flashcards
    due_result = await db.execute(
        select(func.count()).where(
            FR.user_id == user.id,
            FR.next_review_at <= now,
        )
    )
    due_count = due_result.scalar() or 0

    # In-progress modules
    from app.models.models import UserProgress as UP
    in_progress_result = await db.execute(
        select(Module)
        .join(UP, Module.id == UP.module_id)
        .where(
            UP.user_id == user.id,
            UP.completion_percent < 100,
            UP.completion_percent > 0,
        )
        .limit(3)
    )
    in_progress = in_progress_result.scalars().all()

    goal_minutes = (user.preferences or {}).get("daily_goal_minutes", 20)

    return {
        "date": now.date().isoformat(),
        "goal_minutes": goal_minutes,
        "due_flashcards": due_count,
        "in_progress_modules": in_progress,
        "streak_days": user.streak_days,
        "xp_today": 0,  # Would need a daily XP tracker table
    }
