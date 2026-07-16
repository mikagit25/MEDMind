"""Nursing dose-calculation trainer endpoints.

GET  /dose-calc/categories          — list available problem categories
GET  /dose-calc/problem/{category}  — get a single random problem (no answer)
POST /dose-calc/check               — submit numeric answer, get result + steps
GET  /dose-calc/series/{category}   — get a series of 5 problems (progressive)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from app.api.deps import get_current_user
from app.models.models import User
from app.services.dose_calc_generator import (
    CATEGORIES, Category, generate_problem, generate_series,
)

router = APIRouter(prefix="/dose-calc", tags=["dose-calc"])


class CheckRequest(BaseModel):
    category: str
    seed: int
    numeric_value: float


class CheckResponse(BaseModel):
    correct: bool
    expected: float
    tolerance: float
    unit: str
    steps: list[str]
    diff: float


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


@router.post("/check", response_model=CheckResponse)
async def check_answer(
    body: CheckRequest,
    _: User = Depends(get_current_user),
):
    if body.category not in CATEGORIES:
        raise HTTPException(400, f"Unknown category")
    prob = generate_problem(body.category, seed=body.seed)  # type: ignore[arg-type]
    expected = prob["numeric_answer"]
    tol = prob["numeric_tolerance"]
    diff = abs(body.numeric_value - expected)
    return CheckResponse(
        correct=diff <= tol,
        expected=expected,
        tolerance=tol,
        unit=prob["numeric_unit"],
        steps=prob["steps"],
        diff=round(diff, 4),
    )


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
