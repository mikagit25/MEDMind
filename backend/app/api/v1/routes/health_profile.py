"""Health Hub API — persistent health profiles + metrics for users."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.models import HealthProfile, HealthMetric, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/health-profile", tags=["health-profile"])

# ---------------------------------------------------------------------------
# Chronic disease configuration
# ---------------------------------------------------------------------------
CHRONIC_DISEASES: dict[str, dict] = {
    "diabetes_t2": {
        "label": {"en": "Type 2 Diabetes", "ru": "Сахарный диабет 2 типа"},
        "icon": "🩸",
        "metrics": ["glucose", "hba1c", "weight"],
        "targets": {
            "glucose": {"min": 3.9, "max": 7.2, "unit": "mmol/L", "label": "Fasting glucose"},
            "hba1c":  {"min": None, "max": 7.0,  "unit": "%",       "label": "HbA1c"},
        },
        "article_tags": ["diabetes", "blood-sugar", "insulin"],
        "calculators": ["bmi", "hba1c-average"],
        "advice_key": "diabetes",
    },
    "hypertension": {
        "label": {"en": "Hypertension", "ru": "Артериальная гипертензия"},
        "icon": "❤️",
        "metrics": ["bp", "pulse", "weight"],
        "targets": {
            "bp": {"systolic_max": 130, "diastolic_max": 80, "unit": "mmHg", "label": "Blood pressure"},
        },
        "article_tags": ["hypertension", "blood-pressure", "cardiovascular"],
        "calculators": ["cha2ds2-vasc", "framingham"],
        "advice_key": "hypertension",
    },
    "hypothyroidism": {
        "label": {"en": "Hypothyroidism", "ru": "Гипотиреоз"},
        "icon": "🦋",
        "metrics": ["weight", "pulse"],
        "targets": {},
        "article_tags": ["thyroid", "hypothyroidism", "tsh"],
        "calculators": ["bmi"],
        "advice_key": "hypothyroidism",
    },
    "asthma": {
        "label": {"en": "Asthma", "ru": "Бронхиальная астма"},
        "icon": "🌬️",
        "metrics": ["spo2", "pulse"],
        "targets": {
            "spo2": {"min": 95, "max": 100, "unit": "%", "label": "SpO₂"},
        },
        "article_tags": ["asthma", "bronchial", "inhaler"],
        "calculators": ["peak-flow"],
        "advice_key": "asthma",
    },
    "ckd": {
        "label": {"en": "Chronic Kidney Disease", "ru": "Хроническая болезнь почек"},
        "icon": "🫘",
        "metrics": ["bp", "weight"],
        "targets": {
            "bp": {"systolic_max": 125, "diastolic_max": 75, "unit": "mmHg", "label": "Blood pressure"},
        },
        "article_tags": ["kidney", "ckd", "renal"],
        "calculators": ["egfr", "ckd-epi"],
        "advice_key": "ckd",
    },
    "heart_failure": {
        "label": {"en": "Heart Failure", "ru": "Сердечная недостаточность"},
        "icon": "💔",
        "metrics": ["weight", "bp", "pulse", "spo2"],
        "targets": {
            "spo2": {"min": 94, "max": 100, "unit": "%", "label": "SpO₂"},
        },
        "article_tags": ["heart-failure", "cardiac", "ejection-fraction"],
        "calculators": ["nyha", "cha2ds2-vasc"],
        "advice_key": "heart_failure",
    },
    "copd": {
        "label": {"en": "COPD", "ru": "ХОБЛ"},
        "icon": "🫁",
        "metrics": ["spo2", "pulse"],
        "targets": {
            "spo2": {"min": 88, "max": 92, "unit": "%", "label": "SpO₂ target"},
        },
        "article_tags": ["copd", "emphysema", "bronchitis"],
        "calculators": ["copd-assessment", "bode-index"],
        "advice_key": "copd",
    },
    "obesity": {
        "label": {"en": "Obesity", "ru": "Ожирение"},
        "icon": "⚖️",
        "metrics": ["weight"],
        "targets": {},
        "article_tags": ["obesity", "weight-loss", "bmi"],
        "calculators": ["bmi", "waist-hip-ratio"],
        "advice_key": "obesity",
    },
    "atrial_fibrillation": {
        "label": {"en": "Atrial Fibrillation", "ru": "Фибрилляция предсердий"},
        "icon": "〰️",
        "metrics": ["pulse", "bp"],
        "targets": {
            "pulse": {"min": 60, "max": 100, "unit": "bpm", "label": "Resting HR"},
        },
        "article_tags": ["afib", "arrhythmia", "anticoagulation"],
        "calculators": ["cha2ds2-vasc", "has-bled"],
        "advice_key": "afib",
    },
    "depression": {
        "label": {"en": "Depression / Anxiety", "ru": "Депрессия / Тревога"},
        "icon": "🧠",
        "metrics": [],
        "targets": {},
        "article_tags": ["depression", "anxiety", "mental-health"],
        "calculators": ["phq9", "gad7"],
        "advice_key": "depression",
    },
}

ALL_DISEASES_LIST = [
    {"key": k, "label": v["label"], "icon": v["icon"]}
    for k, v in CHRONIC_DISEASES.items()
]

TRACKER_UNITS = {
    "glucose":     "mmol/L",
    "hba1c":       "%",
    "bp":          "mmHg",
    "pulse":       "bpm",
    "weight":      "kg",
    "temp":        "°C",
    "spo2":        "%",
    "cholesterol": "mmol/L",
}

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
class HealthProfileIn(BaseModel):
    birth_year:  int | None = None
    sex:         str | None = None
    conditions:  list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    allergies:   list[str] = Field(default_factory=list)
    telegram_chat_id: str | None = None


class MetricIn(BaseModel):
    metric:      str
    value:       str
    note:        str | None = None
    recorded_at: datetime | None = None
    source:      str = "web"


class HealthProfileOut(BaseModel):
    birth_year:       int | None
    sex:              str | None
    conditions:       list[str]
    medications:      list[str]
    allergies:        list[str]
    health_log:       list[dict]
    checkin_log:      list[dict]
    trackers:         dict[str, list[dict]]
    telegram_chat_id: str | None
    disease_configs:  list[dict]
    updated_at:       datetime | None
    created_at:       datetime | None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _get_or_create_profile(user_id: str, db: AsyncSession) -> HealthProfile:
    result = await db.execute(
        select(HealthProfile).where(HealthProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        profile = HealthProfile(
            user_id=user_id,
            conditions=[],
            medications=[],
            allergies=[],
            health_log=[],
            checkin_log=[],
            trackers={},
        )
        db.add(profile)
        await db.flush()
    return profile


def _disease_configs_for_conditions(conditions: list[str]) -> list[dict]:
    """Return chronic disease configs matching user's conditions."""
    out = []
    for cond in conditions:
        key = cond.lower().replace(" ", "_").replace("-", "_")
        if key in CHRONIC_DISEASES:
            out.append({"key": key, **CHRONIC_DISEASES[key]})
    return out


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.get("/", response_model=HealthProfileOut)
async def get_health_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_or_create_profile(str(current_user.id), db)
    await db.commit()
    return HealthProfileOut(
        birth_year=profile.birth_year,
        sex=profile.sex,
        conditions=profile.conditions or [],
        medications=profile.medications or [],
        allergies=profile.allergies or [],
        health_log=profile.health_log or [],
        checkin_log=profile.checkin_log or [],
        trackers=profile.trackers or {},
        telegram_chat_id=profile.telegram_chat_id,
        disease_configs=_disease_configs_for_conditions(profile.conditions or []),
        updated_at=profile.updated_at,
        created_at=profile.created_at,
    )


@router.put("/", response_model=HealthProfileOut)
async def update_health_profile(
    data: HealthProfileIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_or_create_profile(str(current_user.id), db)
    if data.birth_year is not None:
        profile.birth_year = data.birth_year
    if data.sex is not None:
        profile.sex = data.sex
    profile.conditions  = data.conditions
    profile.medications = data.medications
    profile.allergies   = data.allergies
    if data.telegram_chat_id is not None:
        profile.telegram_chat_id = data.telegram_chat_id
    profile.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(profile)
    return HealthProfileOut(
        birth_year=profile.birth_year,
        sex=profile.sex,
        conditions=profile.conditions or [],
        medications=profile.medications or [],
        allergies=profile.allergies or [],
        health_log=profile.health_log or [],
        checkin_log=profile.checkin_log or [],
        trackers=profile.trackers or {},
        telegram_chat_id=profile.telegram_chat_id,
        disease_configs=_disease_configs_for_conditions(profile.conditions or []),
        updated_at=profile.updated_at,
        created_at=profile.created_at,
    )


@router.post("/metrics", status_code=201)
async def add_metric(
    data: MetricIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    unit = TRACKER_UNITS.get(data.metric, "")
    metric_row = HealthMetric(
        user_id=str(current_user.id),
        metric=data.metric,
        value=data.value,
        unit=unit,
        note=data.note,
        source=data.source,
        recorded_at=data.recorded_at or datetime.utcnow(),
    )
    db.add(metric_row)

    # Also update trackers in profile
    profile = await _get_or_create_profile(str(current_user.id), db)
    trackers = dict(profile.trackers or {})
    entry = {"date": (data.recorded_at or datetime.utcnow()).strftime("%Y-%m-%d"), "value": data.value}
    history = trackers.get(data.metric, [])
    history.append(entry)
    trackers[data.metric] = history[-100:]  # keep last 100
    profile.trackers = trackers
    profile.updated_at = datetime.utcnow()

    await db.commit()
    return {"ok": True, "metric": data.metric, "value": data.value, "unit": unit}


@router.get("/metrics/{metric}")
async def get_metric_history(
    metric: str,
    days: int = Query(default=30, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.utcnow() - timedelta(days=days)
    result = await db.execute(
        select(HealthMetric)
        .where(
            HealthMetric.user_id == str(current_user.id),
            HealthMetric.metric == metric,
            HealthMetric.recorded_at >= since,
        )
        .order_by(desc(HealthMetric.recorded_at))
    )
    rows = result.scalars().all()
    return {
        "metric": metric,
        "unit": TRACKER_UNITS.get(metric, ""),
        "history": [
            {"date": r.recorded_at.strftime("%Y-%m-%d"), "value": r.value, "note": r.note}
            for r in rows
        ],
    }


@router.get("/diseases")
async def list_diseases():
    """Return full list of supported chronic conditions."""
    return ALL_DISEASES_LIST


@router.delete("/")
async def delete_health_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(HealthProfile).where(HealthProfile.user_id == str(current_user.id))
    )
    profile = result.scalar_one_or_none()
    if profile:
        await db.delete(profile)
        await db.commit()
    return {"ok": True}
