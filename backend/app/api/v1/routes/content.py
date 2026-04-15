"""Content routes — specialties, modules, lessons, flashcards, MCQ, cases."""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app.core.database import get_db
from app.models.models import Specialty, Module, Lesson, Flashcard, MCQQuestion, ClinicalCase, User, Drug
from app.schemas.schemas import (
    SpecialtyOut, ModuleOut, ModuleDetail, LessonOut, LessonDetail,
    FlashcardOut, MCQQuestionOut, ClinicalCaseOut, ClinicalCaseDetail, DrugOut
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
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    cache_key = f"specialty_modules:{specialty_id}"
    if cached := await get_cached(cache_key):
        return cached

    stmt = (
        select(Module)
        .where(Module.specialty_id == specialty_id, Module.is_published == True)
        .order_by(Module.module_order)
    )
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
# MODULES
# ============================================================
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


@router.get("/lessons/{lesson_id}", response_model=LessonDetail)
async def get_lesson(
    lesson_id: UUID,
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

    return lesson


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
@router.get("/modules/{module_id}/cases", response_model=List[ClinicalCaseOut])
async def list_cases(
    module_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(ClinicalCase).where(ClinicalCase.module_id == module_id)
    )
    return result.scalars().all()


@router.get("/cases/{case_id}", response_model=ClinicalCaseDetail)
async def get_case(
    case_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(ClinicalCase).where(ClinicalCase.id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


# ============================================================
# DRUGS
# ============================================================
@router.get("/drugs", response_model=List[DrugOut])
async def search_drugs(
    q: str = Query(..., min_length=1, max_length=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.subscription_tier not in ["pro", "clinic", "lifetime"]:
        raise HTTPException(
            status_code=403,
            detail="Drug database requires Pro subscription or higher",
        )
    from sqlalchemy import or_, cast, String
    result = await db.execute(
        select(Drug).where(
            or_(
                Drug.name.ilike(f"%{q}%"),
                Drug.generic_name.ilike(f"%{q}%"),
                Drug.drug_class.ilike(f"%{q}%"),
            )
        ).limit(20)
    )
    return result.scalars().all()


class InteractionCheckRequest(BaseModel):
    drug_ids: list[UUID]


@router.post("/drugs/check-interactions")
async def check_drug_interactions(
    data: InteractionCheckRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
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
    user: User = Depends(get_current_user),
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
    user: User = Depends(get_current_user),
):
    """Return species-adjusted dosing for veterinary users."""
    if not (user.preferences or {}).get("vet_mode"):
        raise HTTPException(status_code=403, detail="Veterinary mode is not enabled for this account")

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


class SearchResponse(BaseModel):
    modules: List[ModuleOut]
    lessons: List[LessonOut]
    total: int


@router.get("/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=2, max_length=200),
    limit: int = Query(10, le=50),
    db: AsyncSession = Depends(get_db),
    user: Optional[User] = Depends(get_current_user_optional),
):
    """Full-text search across modules and lessons."""
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

    return SearchResponse(
        modules=modules,
        lessons=lessons,
        total=len(modules) + len(lessons),
    )


# ============================================================
# PUBMED SEARCH
# ============================================================
@router.get("/search/pubmed")
async def search_pubmed(
    q: str = Query(..., min_length=2, max_length=300),
    limit: int = Query(10, le=20),
    user: User = Depends(get_current_user),
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
    user: User = Depends(get_current_user),
):
    """Recommend next modules based on user progress."""
    from sqlalchemy import not_
    # Modules user has started
    started_ids_result = await db.execute(
        select(Module.id).where(
            Module.id.in_(
                select(Module.id).join(
                    __import__("app.models.models", fromlist=["UserProgress"]).UserProgress,
                    Module.id == __import__("app.models.models", fromlist=["UserProgress"]).UserProgress.module_id,
                ).where(
                    __import__("app.models.models", fromlist=["UserProgress"]).UserProgress.user_id == user.id
                )
            )
        )
    )

    # Simpler approach — get modules not yet started
    from app.models.models import UserProgress as UP
    started_result = await db.execute(
        select(UP.module_id).where(UP.user_id == user.id)
    )
    started_ids = {row[0] for row in started_result.all()}

    # Pick published, accessible modules not yet started
    stmt = (
        select(Module)
        .where(
            Module.is_published == True,
            Module.id.not_in(started_ids) if started_ids else True,
        )
        .order_by(Module.module_order)
        .limit(limit)
    )

    # Free users see only fundamentals
    if user.subscription_tier == "free":
        stmt = stmt.where(Module.is_fundamental == True)

    result = await db.execute(stmt)
    modules = result.scalars().all()
    return {"modules": modules, "total": len(modules)}


@router.get("/recommendations/daily")
async def get_daily_plan(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
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
