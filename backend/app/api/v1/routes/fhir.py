"""
HL7 FHIR R4 API — Medical learning record export.

Standard: HL7 FHIR R4 (https://hl7.org/fhir/R4/)
Base URL: /api/v1/fhir/

Exports MedMind learning data as interoperable FHIR resources:
  - Practitioner        : learner profile
  - Observation         : quiz scores, XP, streak
  - CarePlan            : adaptive study plan
  - Procedure           : completed lessons (learning activities)
  - DiagnosticReport    : CPD/CME summary
  - Bundle              : all of the above

Medical schools and hospitals can use this to:
  - Import CME/CPD records into their HR systems
  - Verify competency attainment
  - Track learner progress across institutions
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.encryption import decrypt_email
from app.models.models import (
    User, UserProgress, LessonCompletion, Module, Lesson,
)

router = APIRouter(prefix="/fhir", tags=["FHIR R4"])

FHIR_BASE = "https://medmind.pro/api/v1/fhir"
FHIR_VERSION = "4.0.1"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fhir_date(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _practitioner(user: User, email: str) -> Dict[str, Any]:
    """FHIR R4 Practitioner resource representing the learner."""
    name: List[Dict] = []
    if user.first_name or user.last_name:
        name = [{
            "use": "official",
            "family": user.last_name or "",
            "given": [user.first_name] if user.first_name else [],
        }]

    qualifier = []
    if user.profile_data and isinstance(user.profile_data, dict):
        specialty = user.profile_data.get("specialty")
        if specialty:
            qualifier.append({
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "display": specialty,
                }]
            })

    return {
        "resourceType": "Practitioner",
        "id": str(user.id),
        "meta": {
            "versionId": "1",
            "lastUpdated": _fhir_date(user.updated_at) or _now_iso(),
            "profile": ["http://hl7.org/fhir/StructureDefinition/Practitioner"],
            "source": FHIR_BASE,
        },
        "identifier": [{
            "system": f"{FHIR_BASE}/practitioners",
            "value": str(user.id),
        }],
        "active": user.is_active,
        "name": name,
        "telecom": [{
            "system": "email",
            "value": email,
            "use": "work",
        }] if email else [],
        "qualification": qualifier,
        "extension": [
            {
                "url": f"{FHIR_BASE}/StructureDefinition/learner-xp",
                "valueInteger": user.xp or 0,
            },
            {
                "url": f"{FHIR_BASE}/StructureDefinition/learner-level",
                "valueInteger": user.level or 1,
            },
            {
                "url": f"{FHIR_BASE}/StructureDefinition/learner-streak-days",
                "valueInteger": user.streak_days or 0,
            },
            {
                "url": f"{FHIR_BASE}/StructureDefinition/subscription-tier",
                "valueString": user.subscription_tier or "free",
            },
        ],
    }


def _observation_xp(user: User) -> Dict[str, Any]:
    """FHIR Observation: total XP earned (engagement metric)."""
    return {
        "resourceType": "Observation",
        "id": f"{user.id}-xp",
        "meta": {"profile": ["http://hl7.org/fhir/StructureDefinition/Observation"]},
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                "code": "activity",
                "display": "Activity",
            }]
        }],
        "code": {
            "coding": [{
                "system": f"{FHIR_BASE}/CodeSystem/learning-metrics",
                "code": "xp-total",
                "display": "Total Experience Points",
            }],
            "text": "Learning XP",
        },
        "subject": {"reference": f"Practitioner/{user.id}"},
        "effectiveDateTime": _fhir_date(user.last_active_date) or _now_iso(),
        "valueInteger": user.xp or 0,
        "component": [
            {
                "code": {"coding": [{"system": f"{FHIR_BASE}/CodeSystem/learning-metrics", "code": "level"}]},
                "valueInteger": user.level or 1,
            },
            {
                "code": {"coding": [{"system": f"{FHIR_BASE}/CodeSystem/learning-metrics", "code": "streak-days"}]},
                "valueInteger": user.streak_days or 0,
            },
        ],
    }


def _procedure_from_completion(
    completion: LessonCompletion,
    lesson: Optional[Lesson],
    user: User,
) -> Dict[str, Any]:
    """FHIR Procedure: a completed learning activity (lesson)."""
    lesson_title = lesson.title if lesson else f"Lesson {completion.lesson_id}"
    specialty = lesson.specialty if lesson and hasattr(lesson, "specialty") else None

    coding = [{
        "system": "http://snomed.info/sct",
        "code": "410155008",
        "display": "Continuing medical education activity",
    }]
    if specialty:
        coding.append({
            "system": f"{FHIR_BASE}/CodeSystem/specialties",
            "code": specialty.lower().replace(" ", "-"),
            "display": specialty,
        })

    resource: Dict[str, Any] = {
        "resourceType": "Procedure",
        "id": str(completion.id),
        "meta": {"profile": ["http://hl7.org/fhir/StructureDefinition/Procedure"]},
        "status": "completed",
        "code": {
            "coding": coding,
            "text": lesson_title,
        },
        "subject": {"reference": f"Practitioner/{user.id}"},
        "performedDateTime": _fhir_date(completion.completed_at) or _now_iso(),
        "extension": [
            {
                "url": f"{FHIR_BASE}/StructureDefinition/lesson-id",
                "valueString": str(completion.lesson_id),
            },
            {
                "url": f"{FHIR_BASE}/StructureDefinition/time-spent-minutes",
                "valueDecimal": round((completion.time_spent_seconds or 0) / 60, 1),
            },
        ],
    }

    if completion.quiz_score is not None:
        resource["outcome"] = {
            "coding": [{
                "system": f"{FHIR_BASE}/CodeSystem/quiz-outcome",
                "code": "quiz-completed",
                "display": f"Quiz score: {float(completion.quiz_score):.0f}%",
            }]
        }
        resource["extension"].append({
            "url": f"{FHIR_BASE}/StructureDefinition/quiz-score",
            "valueDecimal": float(completion.quiz_score),
        })

    return resource


def _care_plan(user: User, progress_list: List[UserProgress], modules: Dict[str, Module]) -> Dict[str, Any]:
    """FHIR CarePlan: adaptive study plan activities."""
    activities = []
    for prog in progress_list:
        mod = modules.get(str(prog.module_id))
        if not mod:
            continue
        activities.append({
            "detail": {
                "status": "completed" if float(prog.completion_percent or 0) >= 100 else "in-progress",
                "code": {
                    "coding": [{
                        "system": f"{FHIR_BASE}/CodeSystem/learning-modules",
                        "code": str(prog.module_id),
                        "display": mod.title,
                    }]
                },
                "description": f"{float(prog.completion_percent or 0):.0f}% complete",
                "extension": [
                    {
                        "url": f"{FHIR_BASE}/StructureDefinition/mcq-score",
                        "valueDecimal": float(prog.mcq_score or 0),
                    },
                    {
                        "url": f"{FHIR_BASE}/StructureDefinition/flashcards-mastered",
                        "valueInteger": len(prog.flashcards_mastered or []),
                    },
                ],
            }
        })

    return {
        "resourceType": "CarePlan",
        "id": f"{user.id}-studyplan",
        "meta": {"profile": ["http://hl7.org/fhir/StructureDefinition/CarePlan"]},
        "status": "active",
        "intent": "plan",
        "title": "Medical Learning Plan",
        "description": "Adaptive study plan generated by MedMind AI",
        "subject": {"reference": f"Practitioner/{user.id}"},
        "period": {
            "start": _fhir_date(user.created_at),
        },
        "activity": activities,
    }


def _diagnostic_report(user: User, completions: List[LessonCompletion]) -> Dict[str, Any]:
    """FHIR DiagnosticReport: CPD/CME summary."""
    total_minutes = sum((c.time_spent_seconds or 0) for c in completions) // 60
    avg_quiz = None
    scored = [float(c.quiz_score) for c in completions if c.quiz_score is not None]
    if scored:
        avg_quiz = round(sum(scored) / len(scored), 1)

    presented: List[Dict] = [
        {
            "coding": [{
                "system": f"{FHIR_BASE}/CodeSystem/cme-metrics",
                "code": "lessons-completed",
                "display": f"Lessons completed: {len(completions)}",
            }]
        },
        {
            "coding": [{
                "system": f"{FHIR_BASE}/CodeSystem/cme-metrics",
                "code": "total-cme-minutes",
                "display": f"Total CME time: {total_minutes} minutes ({total_minutes//60}h {total_minutes%60}m)",
            }]
        },
    ]
    if avg_quiz is not None:
        presented.append({
            "coding": [{
                "system": f"{FHIR_BASE}/CodeSystem/cme-metrics",
                "code": "avg-quiz-score",
                "display": f"Average quiz score: {avg_quiz}%",
            }]
        })

    return {
        "resourceType": "DiagnosticReport",
        "id": f"{user.id}-cpd",
        "meta": {"profile": ["http://hl7.org/fhir/StructureDefinition/DiagnosticReport"]},
        "status": "final",
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                "code": "EDU",
                "display": "Education",
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "73709-0",
                "display": "Continuing Medical Education credit",
            }],
            "text": "CPD/CME Summary Report",
        },
        "subject": {"reference": f"Practitioner/{user.id}"},
        "effectivePeriod": {
            "start": _fhir_date(user.created_at),
            "end": _now_iso(),
        },
        "issued": _now_iso(),
        "conclusion": (
            f"Learner completed {len(completions)} lessons totalling {total_minutes} minutes "
            f"of CME activity on MedMind AI platform."
            + (f" Average quiz score: {avg_quiz}%." if avg_quiz else "")
        ),
        "presentedForm": [],
        "extension": [
            {
                "url": f"{FHIR_BASE}/StructureDefinition/total-xp",
                "valueInteger": user.xp or 0,
            },
            {
                "url": f"{FHIR_BASE}/StructureDefinition/learner-level",
                "valueInteger": user.level or 1,
            },
            {
                "url": f"{FHIR_BASE}/StructureDefinition/cme-minutes",
                "valueInteger": total_minutes,
            },
            {
                "url": f"{FHIR_BASE}/StructureDefinition/lessons-completed",
                "valueInteger": len(completions),
            },
        ],
        "result": [{"display": item["coding"][0]["display"]} for item in presented],
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get(
    "/metadata",
    summary="FHIR CapabilityStatement",
    response_class=JSONResponse,
)
async def fhir_capability():
    """FHIR R4 CapabilityStatement — describes supported resources."""
    return {
        "resourceType": "CapabilityStatement",
        "id": "medmind-fhir-capability",
        "status": "active",
        "date": _now_iso(),
        "publisher": "MedMind AI",
        "kind": "instance",
        "fhirVersion": FHIR_VERSION,
        "format": ["json"],
        "description": (
            "MedMind AI FHIR R4 endpoint exports medical learner records. "
            "Enables interoperability with medical schools, hospitals, and "
            "CME tracking systems."
        ),
        "rest": [{
            "mode": "server",
            "resource": [
                {"type": "Practitioner", "interaction": [{"code": "read"}]},
                {"type": "Observation", "interaction": [{"code": "read"}]},
                {"type": "Procedure", "interaction": [{"code": "search-type"}]},
                {"type": "CarePlan", "interaction": [{"code": "read"}]},
                {"type": "DiagnosticReport", "interaction": [{"code": "read"}]},
                {"type": "Bundle", "interaction": [{"code": "read"}]},
            ],
        }],
    }


@router.get(
    "/Practitioner/me",
    summary="Current user as FHIR Practitioner",
    response_class=JSONResponse,
)
async def get_practitioner_me(
    current_user: User = Depends(get_current_user),
):
    """Returns the authenticated user as a FHIR R4 Practitioner resource."""
    try:
        email = decrypt_email(current_user.email)
    except Exception:
        email = ""
    return _practitioner(current_user, email)


@router.get(
    "/Bundle/me",
    summary="Full learning record as FHIR Bundle",
    response_class=JSONResponse,
)
async def get_bundle_me(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns the authenticated user's complete learning record as a FHIR R4
    Transaction Bundle containing:
      - Practitioner (user profile)
      - Observation  (XP, level, streak)
      - Procedure[]  (each completed lesson)
      - CarePlan     (module progress)
      - DiagnosticReport (CPD/CME summary)
    """
    try:
        email = decrypt_email(current_user.email)
    except Exception:
        email = ""

    # Load completions with lesson details
    compl_result = await db.execute(
        select(LessonCompletion, Lesson)
        .outerjoin(Lesson, Lesson.id == LessonCompletion.lesson_id)
        .where(LessonCompletion.user_id == current_user.id)
        .order_by(LessonCompletion.completed_at.desc())
        .limit(500)
    )
    rows = compl_result.all()
    completions = [r[0] for r in rows]
    lessons_map = {str(r[0].lesson_id): r[1] for r in rows}

    # Load module progress
    prog_result = await db.execute(
        select(UserProgress, Module)
        .outerjoin(Module, Module.id == UserProgress.module_id)
        .where(UserProgress.user_id == current_user.id)
    )
    prog_rows = prog_result.all()
    progress_list = [r[0] for r in prog_rows]
    modules_map = {str(r[1].id): r[1] for r in prog_rows if r[1]}

    # Build resources
    practitioner = _practitioner(current_user, email)
    obs_xp = _observation_xp(current_user)
    procedures = [
        _procedure_from_completion(c, lessons_map.get(str(c.lesson_id)), current_user)
        for c in completions
    ]
    care_plan = _care_plan(current_user, progress_list, modules_map)
    report = _diagnostic_report(current_user, completions)

    entries = [
        {"fullUrl": f"{FHIR_BASE}/Practitioner/{current_user.id}", "resource": practitioner},
        {"fullUrl": f"{FHIR_BASE}/Observation/{current_user.id}-xp", "resource": obs_xp},
        {"fullUrl": f"{FHIR_BASE}/CarePlan/{current_user.id}-studyplan", "resource": care_plan},
        {"fullUrl": f"{FHIR_BASE}/DiagnosticReport/{current_user.id}-cpd", "resource": report},
    ] + [
        {"fullUrl": f"{FHIR_BASE}/Procedure/{p['id']}", "resource": p}
        for p in procedures
    ]

    return {
        "resourceType": "Bundle",
        "id": f"{current_user.id}-record",
        "meta": {
            "lastUpdated": _now_iso(),
            "profile": ["http://hl7.org/fhir/StructureDefinition/Bundle"],
        },
        "type": "collection",
        "timestamp": _now_iso(),
        "total": len(entries),
        "link": [{
            "relation": "self",
            "url": f"{FHIR_BASE}/Bundle/me",
        }],
        "entry": entries,
    }


@router.get(
    "/DiagnosticReport/me",
    summary="CPD/CME DiagnosticReport",
    response_class=JSONResponse,
)
async def get_diagnostic_report_me(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns CPD/CME summary as a FHIR DiagnosticReport."""
    compl_result = await db.execute(
        select(LessonCompletion)
        .where(LessonCompletion.user_id == current_user.id)
    )
    completions = compl_result.scalars().all()
    return _diagnostic_report(current_user, list(completions))
