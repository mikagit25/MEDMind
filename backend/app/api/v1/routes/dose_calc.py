"""Nursing dose-calculation trainer endpoints.

GET  /dose-calc/categories          — list available problem categories
GET  /dose-calc/problem/{category}  — get a single random problem (no answer)
POST /dose-calc/check               — submit numeric answer, get result + steps + updated stats
GET  /dose-calc/stats               — per-category + overall aggregate stats for current user
GET  /dose-calc/series/{category}   — get a series of 5 problems (progressive)
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import DoseCalcStat, User
from app.services.dose_calc_generator import (
    CATEGORIES, Category, generate_problem, generate_series,
)

router = APIRouter(prefix="/dose-calc", tags=["dose-calc"])


class CheckRequest(BaseModel):
    category: str
    seed: int
    numeric_value: float


@router.get("/categories")
async def list_categories(_: User = Depends(get_current_user)):
    labels = {
        "weight_dose": "Weight-based dosing",
        "infusion_rate": "Infusion rate",
        "dilution": "Dilution & concentration",
        "unit_convert": "Unit conversion",
        "pediatric_dose": "Paediatric dosing",
    }
    return [{"id": c, "label": labels.get(c, c)} for c in CATEGORIES]


@router.get("/problem/{category}")
async def get_problem(
    category: str,
    seed: Optional[int] = Query(None),
    _: User = Depends(get_current_user),
):
    if category not in CATEGORIES:
        raise HTTPException(400, f"Unknown category. Valid: {CATEGORIES}")
    import random as _random
    effective_seed = seed if seed is not None else _random.randint(0, 999999)
    prob = generate_problem(category, seed=effective_seed)  # type: ignore[arg-type]
    return {
        "category": prob["category"],
        "question": prob["question"],
        "numeric_unit": prob["numeric_unit"],
        "seed": effective_seed,
    }


@router.post("/check")
async def check_answer(
    body: CheckRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.category not in CATEGORIES:
        raise HTTPException(400, "Unknown category")

    prob = generate_problem(body.category, seed=body.seed)  # type: ignore[arg-type]
    expected = prob["numeric_answer"]
    tol = prob["numeric_tolerance"]
    diff = abs(body.numeric_value - expected)
    is_correct = diff <= tol
    now = datetime.utcnow()

    # Upsert stats for the specific category and _overall
    for cat_key in [body.category, "_overall"]:
        row = await db.get(DoseCalcStat, (user.id, cat_key))
        if row is None:
            row = DoseCalcStat(
                user_id=user.id,
                category=cat_key,
                total_attempts=0,
                total_correct=0,
                current_streak=0,
                best_streak=0,
            )
            db.add(row)
        row.total_attempts += 1
        if is_correct:
            row.total_correct += 1
            row.current_streak += 1
            row.best_streak = max(row.best_streak, row.current_streak)
        else:
            row.current_streak = 0
        row.last_attempted_at = now

    await db.commit()

    overall = await db.get(DoseCalcStat, (user.id, "_overall"))
    cat_stat = await db.get(DoseCalcStat, (user.id, body.category))

    return {
        "correct": is_correct,
        "expected": expected,
        "tolerance": tol,
        "unit": prob["numeric_unit"],
        "steps": prob["steps"],
        "diff": round(diff, 4),
        "overall_streak": overall.current_streak if overall else 0,
        "overall_total": overall.total_attempts if overall else 0,
        "overall_correct": overall.total_correct if overall else 0,
        "cat_total": cat_stat.total_attempts if cat_stat else 0,
        "cat_correct": cat_stat.total_correct if cat_stat else 0,
    }


@router.get("/stats")
async def get_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DoseCalcStat).where(DoseCalcStat.user_id == user.id)
    )
    rows = result.scalars().all()
    stats: dict[str, dict] = {}
    for row in rows:
        stats[row.category] = {
            "total": row.total_attempts,
            "correct": row.total_correct,
            "pct": round(row.total_correct / row.total_attempts * 100) if row.total_attempts else 0,
            "streak": row.current_streak,
            "best_streak": row.best_streak,
        }
    return stats


@router.get("/series/{category}")
async def get_series(
    category: str,
    seed: Optional[int] = Query(None),
    count: int = Query(5, ge=1, le=10),
    _: User = Depends(get_current_user),
):
    if category not in CATEGORIES:
        raise HTTPException(400, f"Unknown category. Valid: {CATEGORIES}")
    import random as _random
    base_seed = seed if seed is not None else _random.randint(0, 999999)
    problems = generate_series(category, count=count, seed=base_seed)  # type: ignore[arg-type]
    return {
        "category": category,
        "base_seed": base_seed,
        "count": len(problems),
        "problems": [
            {
                "seed": base_seed + i * 37,
                "question": p["question"],
                "numeric_unit": p["numeric_unit"],
            }
            for i, p in enumerate(problems)
        ],
    }
