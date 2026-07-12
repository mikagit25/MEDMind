"""Point-of-Care /practice routes (V5 Phase 3).

All endpoints require authentication. Drugs + interactions respect
existing specialist-only rules (existing drug endpoints handle this).
Algorithms, lab values — any authenticated user.
"""
import json
import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.cache import get_cached, set_cached
from app.models.models import ClinicalAlgorithm, Drug, Module, User

log = logging.getLogger(__name__)
router = APIRouter(prefix="/practice", tags=["practice"])

_DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"
_LAB_FILE = _DATA_DIR / "lab_reference_values.json"


# ── Lab Reference Values ──────────────────────────────────────────────────────

@router.get("/lab-values")
async def get_lab_values(
    species: str = Query("human", description="human | dog | cat"),
    _user: User = Depends(get_current_user),
):
    """Return reference lab value tables. Cached in memory (file rarely changes)."""
    cache_key = f"lab_values:{species}"
    cached = await get_cached(cache_key)
    if cached:
        return cached

    try:
        with open(_LAB_FILE, "r", encoding="utf-8") as f:
            all_data = json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Lab values data file not found")

    if species == "human":
        result = {"species": "human", "panels": all_data.get("human", {})}
    elif species in ("dog", "cat"):
        vet_data = all_data.get("veterinary", {}).get(species, {})
        result = {"species": species, "panels": vet_data}
    else:
        raise HTTPException(status_code=422, detail=f"Unknown species: {species}. Use: human, dog, cat")

    await set_cached(cache_key, result, ttl=3600 * 6)  # 6h cache
    return result


# ── Clinical Algorithms ───────────────────────────────────────────────────────

@router.get("/algorithms")
async def list_algorithms(
    specialty: Optional[str] = Query(None),
    vet_only: bool = Query(False),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all clinical algorithms (title + slug + specialty). ~10 items, cacheable."""
    cache_key = f"algo_list:{specialty}:{vet_only}"
    cached = await get_cached(cache_key)
    if cached:
        return cached

    stmt = (
        select(
            ClinicalAlgorithm.id,
            ClinicalAlgorithm.slug,
            ClinicalAlgorithm.title,
            ClinicalAlgorithm.specialty,
            ClinicalAlgorithm.description,
            ClinicalAlgorithm.tags,
            ClinicalAlgorithm.is_veterinary,
        )
        .where(ClinicalAlgorithm.verification_status == "passed")
    )
    if vet_only:
        stmt = stmt.where(ClinicalAlgorithm.is_veterinary == True)
    if specialty:
        stmt = stmt.where(ClinicalAlgorithm.specialty == specialty)
    stmt = stmt.order_by(ClinicalAlgorithm.title)

    rows = (await db.execute(stmt)).all()
    result = [
        {
            "id": str(r.id),
            "slug": r.slug,
            "title": r.title,
            "specialty": r.specialty,
            "description": r.description or "",
            "tags": [t.strip() for t in (r.tags or "").split(",") if t.strip()],
            "is_veterinary": r.is_veterinary,
        }
        for r in rows
    ]
    await set_cached(cache_key, result, ttl=3600)
    return result


@router.get("/algorithms/{slug}")
async def get_algorithm(
    slug: str,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Full algorithm with steps."""
    cache_key = f"algo_detail:{slug}"
    cached = await get_cached(cache_key)
    if cached:
        return cached

    algo = (
        await db.execute(
            select(ClinicalAlgorithm).where(ClinicalAlgorithm.slug == slug)
        )
    ).scalar_one_or_none()

    if not algo:
        raise HTTPException(status_code=404, detail="Algorithm not found")

    result = {
        "id": str(algo.id),
        "slug": algo.slug,
        "title": algo.title,
        "specialty": algo.specialty,
        "description": algo.description or "",
        "steps": algo.steps,
        "tags": [t.strip() for t in (algo.tags or "").split(",") if t.strip()],
        "source": algo.source or "",
        "is_veterinary": algo.is_veterinary,
        "verification_status": algo.verification_status,
    }
    await set_cached(cache_key, result, ttl=3600)
    return result


# ── Practice Search ───────────────────────────────────────────────────────────

@router.get("/search")
async def practice_search(
    q: str = Query(..., min_length=2, max_length=100),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Unified point-of-care search.

    Priority order: drugs → algorithms → modules.
    Returns up to 5 results per category (15 total).
    """
    term = f"%{q.lower()}%"

    # 1. Drugs (name or generic_name match)
    drug_rows = (await db.execute(
        select(Drug.id, Drug.name, Drug.generic_name, Drug.drug_class)
        .where(
            or_(
                func.lower(Drug.name).like(term),
                func.lower(Drug.generic_name).like(term),
            )
        )
        .limit(5)
    )).all()
    drugs = [
        {"type": "drug", "id": str(r.id), "title": r.name,
         "subtitle": r.generic_name or "", "href": f"/drugs/{r.id}"}
        for r in drug_rows
    ]

    # 2. Algorithms
    algo_rows = (await db.execute(
        select(ClinicalAlgorithm.slug, ClinicalAlgorithm.title, ClinicalAlgorithm.specialty)
        .where(
            or_(
                func.lower(ClinicalAlgorithm.title).like(term),
                func.lower(ClinicalAlgorithm.tags).like(term),
            )
        )
        .where(ClinicalAlgorithm.verification_status == "passed")
        .limit(5)
    )).all()
    algorithms = [
        {"type": "algorithm", "id": r.slug, "title": r.title,
         "subtitle": r.specialty or "Algorithm", "href": f"/practice/algorithms/{r.slug}"}
        for r in algo_rows
    ]

    # 3. Modules (educational content — lowest priority)
    mod_rows = (await db.execute(
        select(Module.id, Module.title, Module.code)
        .where(
            or_(
                func.lower(Module.title).like(term),
                func.lower(Module.code).like(term),
            )
        )
        .where(Module.is_published == True)
        .limit(5)
    )).all()
    modules = [
        {"type": "module", "id": str(r.id), "title": r.title,
         "subtitle": r.code, "href": f"/modules/{r.id}"}
        for r in mod_rows
    ]

    return {
        "query": q,
        "results": drugs + algorithms + modules,
        "counts": {"drugs": len(drugs), "algorithms": len(algorithms), "modules": len(modules)},
    }
