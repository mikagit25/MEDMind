"""V7 Phase 3 — Post-exam outcome survey endpoints.

User-facing: check pending survey, submit result, unsubscribe.
Admin: readiness validation report, blueprint calibration report.
"""
from __future__ import annotations

import datetime as _dt
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_admin
from app.core.database import get_db
from app.models.models import ExamOutcome, User

router = APIRouter(prefix="/api/v1", tags=["exam-outcomes"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class SurveySubmitBody(BaseModel):
    # Step 1
    result: str = Field(..., pattern="^(passed|failed|postponed|no_answer)$")
    self_reported_score: Optional[str] = None
    # Step 2 — optional topic feedback (no verbatim questions per NDA)
    harder_topics: Optional[List[str]] = None
    weaker_topics: Optional[List[str]] = None
    feedback_note: Optional[str] = Field(None, max_length=1000)
    # Step 3
    nps_score: Optional[int] = Field(None, ge=0, le=10)


# ── User endpoints ────────────────────────────────────────────────────────────

@router.get("/exam-outcomes/pending")
async def get_pending_survey(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Return the oldest pending survey for the current user, or null."""
    today = _dt.datetime.utcnow().date()
    # Look for an outcome where exam_date has passed and survey not yet filled
    outcome = (await db.execute(
        select(ExamOutcome).where(
            ExamOutcome.user_id == user.id,
            ExamOutcome.reported_at.is_(None),
            ExamOutcome.unsubscribed_from_survey == False,  # noqa: E712
            ExamOutcome.exam_date <= str(today),
        ).order_by(ExamOutcome.exam_date)
    )).scalars().first()

    if not outcome:
        return {"pending": False}

    return {
        "pending": True,
        "outcome_id": str(outcome.id),
        "exam_slug": outcome.exam_slug,
        "exam_date": str(outcome.exam_date),
        "readiness_at_exam": outcome.readiness_at_exam,
    }


@router.post("/exam-outcomes/{outcome_id}/submit")
async def submit_survey(
    outcome_id: UUID,
    body: SurveySubmitBody,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Submit the post-exam survey. NDA disclaimer must be accepted on the frontend."""
    outcome = (await db.execute(
        select(ExamOutcome).where(
            ExamOutcome.id == outcome_id,
            ExamOutcome.user_id == user.id,
        )
    )).scalar_one_or_none()

    if not outcome:
        raise HTTPException(404, "Outcome not found")
    if outcome.reported_at is not None:
        raise HTTPException(409, "Survey already submitted")

    outcome.result = body.result
    outcome.self_reported_score = body.self_reported_score
    outcome.harder_topics = body.harder_topics
    outcome.weaker_topics = body.weaker_topics
    outcome.feedback_note = body.feedback_note
    outcome.nps_score = body.nps_score
    outcome.reported_at = _dt.datetime.utcnow()
    db.add(outcome)
    await db.commit()
    return {"ok": True, "outcome_id": str(outcome_id)}


@router.post("/exam-outcomes/{outcome_id}/unsubscribe")
async def unsubscribe_survey(
    outcome_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Opt out of further survey reminders for this exam outcome."""
    outcome = (await db.execute(
        select(ExamOutcome).where(
            ExamOutcome.id == outcome_id,
            ExamOutcome.user_id == user.id,
        )
    )).scalar_one_or_none()

    if not outcome:
        raise HTTPException(404, "Outcome not found")

    outcome.unsubscribed_from_survey = True
    db.add(outcome)
    await db.commit()
    return {"ok": True}


# ── Admin endpoints ───────────────────────────────────────────────────────────

@router.get("/admin/readiness-validation")
async def readiness_validation_report(
    exam_slug: Optional[str] = Query(None),
    admin: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Readiness score vs pass rate table.

    Buckets: 0–50, 50–60, 60–70, 70–80, 80+.
    Only users who submitted a result (passed|failed) are included.
    Shows 'insufficient_data' warning when n < 20 in a bucket.
    Note: correlation claims not suitable for marketing when total outcomes < 100.
    """
    q = select(ExamOutcome).where(
        ExamOutcome.reported_at.is_not(None),
        ExamOutcome.result.in_(["passed", "failed"]),
        ExamOutcome.readiness_at_exam.is_not(None),
    )
    if exam_slug:
        q = q.where(ExamOutcome.exam_slug == exam_slug)

    outcomes = (await db.execute(q)).scalars().all()

    BUCKETS = [
        ("0–50", 0, 50),
        ("50–60", 50, 60),
        ("60–70", 60, 70),
        ("70–80", 70, 80),
        ("80+", 80, 101),
    ]
    MIN_N_BUCKET = 20
    MIN_N_MARKETING = 100

    table = []
    for label, lo, hi in BUCKETS:
        bucket_outcomes = [
            o for o in outcomes
            if o.readiness_at_exam is not None
            and lo <= o.readiness_at_exam < hi
        ]
        n = len(bucket_outcomes)
        passed = sum(1 for o in bucket_outcomes if o.result == "passed")
        table.append({
            "readiness_range": label,
            "n": n,
            "passed": passed,
            "pass_rate": round(passed / n * 100, 1) if n > 0 else None,
            "insufficient_data": n < MIN_N_BUCKET,
        })

    total = len(outcomes)
    return {
        "exam_slug": exam_slug,
        "total_outcomes": total,
        "marketing_correlation_safe": total >= MIN_N_MARKETING,
        "note": (
            "Correlation claims should not be used in marketing until total_outcomes >= 100."
            if total < MIN_N_MARKETING else None
        ),
        "table": table,
    }


@router.get("/admin/blueprint-calibration")
async def blueprint_calibration_report(
    exam_slug: Optional[str] = Query(None),
    admin: User = Depends(require_admin()),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Aggregate of topics users reported as harder/weaker than expected.

    Output is advisory only — official blueprint weights take precedence.
    Use to identify where to strengthen the question bank and study modules.
    """
    q = select(ExamOutcome).where(
        ExamOutcome.reported_at.is_not(None),
    )
    if exam_slug:
        q = q.where(ExamOutcome.exam_slug == exam_slug)

    outcomes = (await db.execute(q)).scalars().all()

    harder: Dict[str, int] = {}
    weaker: Dict[str, int] = {}
    for o in outcomes:
        for topic in (o.harder_topics or []):
            harder[topic] = harder.get(topic, 0) + 1
        for topic in (o.weaker_topics or []):
            weaker[topic] = weaker.get(topic, 0) + 1

    def _sorted(d: Dict[str, int]) -> List[Dict]:
        return sorted(
            [{"topic": k, "count": v} for k, v in d.items()],
            key=lambda x: -x["count"],
        )

    return {
        "exam_slug": exam_slug,
        "total_responses": len(outcomes),
        "harder_than_expected": _sorted(harder),
        "weaker_preparation": _sorted(weaker),
        "advisory_note": (
            "These are self-reported perceptions, not objective difficulty metrics. "
            "Official blueprint weights take precedence. "
            "Use to identify gaps in question bank coverage and study module depth."
        ),
    }
