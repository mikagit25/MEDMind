"""Clinical calculator results — save and retrieve calculator history.

Public endpoints (no auth):
  GET  /calculators          — list all available calculators (metadata)

Authenticated endpoints:
  POST /calculators/{slug}/save-result   — save a calculator result for the current user
  GET  /calculators/history              — list the current user's saved results (newest first)
  DELETE /calculators/history/{id}       — delete a saved result
"""
from __future__ import annotations

import uuid as _uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.models import User, CalculatorResult

router = APIRouter(tags=["calculators"])

# ── Static calculator catalog ─────────────────────────────────────────────────

CALC_CATALOG = [
    # Cardiology
    {"slug": "cha2ds2-vasc",   "name": "CHA₂DS₂-VASc",          "category": "Cardiology",    "icon": "💓"},
    {"slug": "has-bled",       "name": "HAS-BLED",                "category": "Cardiology",    "icon": "🩸"},
    {"slug": "wells-dvt",      "name": "Wells Criteria (DVT)",    "category": "Cardiology",    "icon": "🦵"},
    {"slug": "wells-pe",       "name": "Wells Criteria (PE)",     "category": "Pulmonology",   "icon": "🫁"},
    {"slug": "heart-score",    "name": "HEART Score",             "category": "Cardiology",    "icon": "🏥"},
    {"slug": "target-heart-rate", "name": "Target Heart Rate",   "category": "Cardiology",    "icon": "💓"},
    # Nephrology / Biochemistry
    {"slug": "egfr-ckd-epi",   "name": "eGFR (CKD-EPI 2021)",    "category": "Nephrology",    "icon": "🫘"},
    {"slug": "cockcroft-gault","name": "Cockcroft-Gault CrCl",   "category": "Nephrology",    "icon": "💊"},
    {"slug": "aki",            "name": "AKI Staging (KDIGO)",     "category": "Critical Care", "icon": "🚨"},
    {"slug": "corrected-calcium","name": "Corrected Calcium",     "category": "Biochemistry",  "icon": "🧪"},
    {"slug": "anion-gap",      "name": "Anion Gap",               "category": "Biochemistry",  "icon": "⚗️"},
    # Hepatology
    {"slug": "meld",           "name": "MELD / MELD-Na",          "category": "Hepatology",    "icon": "🫀"},
    {"slug": "child-pugh",     "name": "Child-Pugh Score",        "category": "Hepatology",    "icon": "🫀"},
    # Critical Care / Neurology
    {"slug": "sofa",           "name": "SOFA Score",              "category": "Critical Care", "icon": "🏥"},
    {"slug": "qsofa",          "name": "qSOFA",                   "category": "Critical Care", "icon": "⚠️"},
    {"slug": "curb-65",        "name": "CURB-65",                 "category": "Pulmonology",   "icon": "🫁"},
    {"slug": "gcs",            "name": "Glasgow Coma Scale",      "category": "Neurology",     "icon": "🧠"},
    {"slug": "abcd2",          "name": "ABCD² Score",             "category": "Neurology",     "icon": "🧠"},
    # General
    {"slug": "bmi",            "name": "BMI Calculator",          "category": "General",       "icon": "⚖️"},
    {"slug": "ideal-body-weight","name": "Ideal Body Weight",     "category": "General",       "icon": "⚖️"},
    {"slug": "daily-calories", "name": "Daily Calorie Needs",     "category": "General",       "icon": "🍎"},
    {"slug": "pregnancy-due-date","name": "Pregnancy Due Date",   "category": "Obstetrics",    "icon": "🤰"},
    {"slug": "framingham-risk","name": "Framingham Risk Score",  "category": "Cardiology",    "icon": "🫀"},
    {"slug": "ottawa-ankle",  "name": "Ottawa Ankle Rules",      "category": "Emergency",     "icon": "🦶"},
    {"slug": "ottawa-knee",   "name": "Ottawa Knee Rules",       "category": "Emergency",     "icon": "🦵"},
]

VALID_SLUGS = {c["slug"] for c in CALC_CATALOG}


# ── Schemas ───────────────────────────────────────────────────────────────────

class SaveResultRequest(BaseModel):
    inputs: dict
    score: Optional[str] = None
    risk_level: Optional[str] = None
    note: Optional[str] = None


class SavedResultOut(BaseModel):
    id: str
    slug: str
    inputs: dict
    score: Optional[str]
    risk_level: Optional[str]
    note: Optional[str]
    created_at: datetime

    @classmethod
    def from_orm(cls, r: CalculatorResult) -> "SavedResultOut":
        return cls(
            id=str(r.id),
            slug=r.slug,
            inputs=r.inputs,
            score=r.score,
            risk_level=r.risk_level,
            note=r.note,
            created_at=r.created_at,
        )


# ── Public: catalog ───────────────────────────────────────────────────────────

@router.get("/calculators", response_model=List[dict])
async def list_calculators():
    """Return the full list of available clinical calculators."""
    return CALC_CATALOG


# ── Authenticated: save result ────────────────────────────────────────────────

@router.post("/calculators/{slug}/save-result", response_model=SavedResultOut, status_code=201)
async def save_result(
    slug: str,
    body: SaveResultRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Save a calculator result to the current user's history."""
    if slug not in VALID_SLUGS:
        raise HTTPException(status_code=404, detail=f"Calculator '{slug}' not found.")
    record = CalculatorResult(
        id=_uuid.uuid4(),
        user_id=user.id,
        slug=slug,
        inputs=body.inputs,
        score=body.score,
        risk_level=body.risk_level,
        note=body.note,
        created_at=datetime.utcnow(),
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return SavedResultOut.from_orm(record)


# ── Authenticated: history ────────────────────────────────────────────────────

@router.get("/calculators/history", response_model=List[SavedResultOut])
async def get_history(
    slug: Optional[str] = Query(None, description="Filter by calculator slug"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Return the authenticated user's saved calculator results, newest first."""
    q = select(CalculatorResult).where(CalculatorResult.user_id == user.id)
    if slug:
        q = q.where(CalculatorResult.slug == slug)
    q = q.order_by(CalculatorResult.created_at.desc()).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return [SavedResultOut.from_orm(r) for r in rows]


# ── Authenticated: delete ─────────────────────────────────────────────────────

@router.delete("/calculators/history/{result_id}", status_code=204)
async def delete_result(
    result_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Delete a saved calculator result."""
    try:
        rid = _uuid.UUID(result_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid UUID")
    result = await db.execute(
        select(CalculatorResult).where(
            CalculatorResult.id == rid,
            CalculatorResult.user_id == user.id,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Result not found.")
    await db.delete(record)
    await db.commit()
