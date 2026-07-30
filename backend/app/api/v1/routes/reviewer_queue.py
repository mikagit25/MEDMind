"""Bank-Scale B4 — Reviewer workplace endpoints.

Requires role='reviewer' or 'admin' (enforced by require_reviewer dependency).
Endpoints:
  GET  /reviewer/queue          — next question to review (prioritized)
  POST /reviewer/submit/{id}    — submit rubric assessment + decision
  GET  /reviewer/stats          — reviewer's own review counts
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_reviewer
from app.core.database import get_db
from app.models.models import (
    ContentAuditLog, GenerationQueue, MCQQuestion, Module,
    QuestionReview, QuestionStats, User,
)

router = APIRouter(prefix="/reviewer", tags=["reviewer"])

_RUBRIC_FIELDS = [
    "realism", "clinical_accuracy", "key_correct",
    "rationale_quality", "distractors_plausible",
    "language_clarity", "category_correct",
]


# ── Schemas ───────────────────────────────────────────────────────────────────

class ReviewSubmitBody(BaseModel):
    realism:               int = Field(..., ge=1, le=5)
    clinical_accuracy:     int = Field(..., ge=1, le=5)
    key_correct:           int = Field(..., ge=1, le=5)
    rationale_quality:     int = Field(..., ge=1, le=5)
    distractors_plausible: int = Field(..., ge=1, le=5)
    language_clarity:      int = Field(..., ge=1, le=5)
    category_correct:      int = Field(..., ge=1, le=5)
    comment:               Optional[str] = None
    decision:              str = Field(..., pattern=r"^(approve|approve_with_edits|reject)$")
    edits:                 Optional[dict] = None      # applied when approve_with_edits
    reject_reason:         Optional[str] = None       # required when decision=reject


def _question_out(q: MCQQuestion) -> dict[str, Any]:
    return {
        "id": str(q.id),
        "question": q.question,
        "options": q.options,
        "correct": q.correct,
        "explanation": q.explanation,
        "rationales": q.rationales,
        "key_takeaway": q.key_takeaway,
        "difficulty": q.difficulty,
        "question_type": q.question_type,
        "nclex_client_needs": q.nclex_client_needs,
        "exam_slugs": q.exam_slugs or [],
        "source_refs": q.source_refs or [],
        "verification_status": q.verification_status,
        "is_flagged": q.is_flagged,
        "flag_reason": q.flag_reason,
        "status": q.status,
        "created_at": q.created_at.isoformat() if q.created_at else None,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _next_priority_question(db: AsyncSession, exclude_ids: list[uuid.UUID] | None = None) -> MCQQuestion | None:
    """Return highest-priority question for review.

    Priority order (B4.2):
    1. user-flagged questions
    2. health != ok (from QuestionStats)
    3. pending + recently generated (B2 pipeline)
    4. high follow-up count (user confusion proxy)
    """
    base = select(MCQQuestion).where(
        MCQQuestion.status == "active",
        MCQQuestion.verification_status != "human_reviewed",
    )
    if exclude_ids:
        base = base.where(MCQQuestion.id.notin_(exclude_ids))

    # 1. User-flagged
    q = (await db.execute(
        base.where(MCQQuestion.is_flagged == True).limit(1)
    )).scalar_one_or_none()
    if q:
        return q

    # 2. health != ok (join QuestionStats)
    q = (await db.execute(
        base.join(QuestionStats, QuestionStats.question_id == MCQQuestion.id, isouter=True)
        .where(QuestionStats.health != "ok", QuestionStats.health.isnot(None))
        .limit(1)
    )).scalar_one_or_none()
    if q:
        return q

    # 3. Pending verification (newly generated)
    q = (await db.execute(
        base.where(MCQQuestion.verification_status == "pending")
        .order_by(MCQQuestion.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()
    if q:
        return q

    # 4. High follow-up count
    q = (await db.execute(
        base.order_by(MCQQuestion.follow_up_count.desc()).limit(1)
    )).scalar_one_or_none()
    return q


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/queue")
async def reviewer_queue(
    skip_ids: str = Query("", description="Comma-separated question IDs to skip"),
    reviewer: User = Depends(require_reviewer()),
    db: AsyncSession = Depends(get_db),
):
    """Return the next question to review, prioritized by urgency."""
    exclude: list[uuid.UUID] = []
    for sid in (skip_ids.split(",") if skip_ids else []):
        try:
            exclude.append(uuid.UUID(sid.strip()))
        except ValueError:
            pass

    q = await _next_priority_question(db, exclude_ids=exclude or None)
    if not q:
        return {"question": None, "message": "Queue empty — no pending questions."}

    # How many reviews has this reviewer done?
    review_count = (await db.execute(
        select(func.count()).where(QuestionReview.reviewer_user_id == reviewer.id)
    )).scalar_one()

    return {
        "question": _question_out(q),
        "reviewer_review_count": review_count,
    }


@router.post("/submit/{question_id}")
async def reviewer_submit(
    question_id: uuid.UUID,
    body: ReviewSubmitBody,
    reviewer: User = Depends(require_reviewer()),
    db: AsyncSession = Depends(get_db),
):
    """Submit a rubric assessment and decision for a question.

    Decision effects:
    - approve            → verification_status='human_reviewed'
    - approve_with_edits → apply edits + human_reviewed + audit log
    - reject             → status='retired' + GenerationQueue entry
    """
    q = await db.get(MCQQuestion, question_id)
    if not q:
        raise HTTPException(404, "Question not found")
    if q.status == "retired":
        raise HTTPException(409, "Question already retired")

    if body.decision == "reject" and not body.reject_reason:
        raise HTTPException(422, "reject_reason required when decision=reject")

    # Persist review record
    review = QuestionReview(
        question_id=question_id,
        reviewer_user_id=reviewer.id,
        realism=body.realism,
        clinical_accuracy=body.clinical_accuracy,
        key_correct=body.key_correct,
        rationale_quality=body.rationale_quality,
        distractors_plausible=body.distractors_plausible,
        language_clarity=body.language_clarity,
        category_correct=body.category_correct,
        comment=body.comment,
        decision=body.decision,
        edits=body.edits,
        reject_reason=body.reject_reason,
        created_at=datetime.utcnow(),
    )
    db.add(review)

    before: dict = {"verification_status": q.verification_status, "status": q.status}
    after: dict = {}

    if body.decision in ("approve", "approve_with_edits"):
        q.verification_status = "human_reviewed"
        after["verification_status"] = "human_reviewed"

        if body.decision == "approve_with_edits" and body.edits:
            for field, value in body.edits.items():
                if hasattr(q, field) and field not in ("id", "module_id", "created_at"):
                    setattr(q, field, value)
            after["edits_applied"] = list(body.edits.keys())

        db.add(ContentAuditLog(
            question_id=question_id,
            admin_id=reviewer.id,
            action="approve" if body.decision == "approve" else "approve_with_edits",
            before=before,
            after=after,
            note=body.comment,
        ))

    elif body.decision == "reject":
        q.status = "retired"
        q.verification_status = "flagged"
        after["status"] = "retired"

        # Queue regeneration (B3.2)
        db.add(GenerationQueue(
            exam_slug=(q.exam_slugs or ["nclex_rn"])[0],
            nclex_category=q.nclex_client_needs or "pharmacological",
            question_type=q.question_type or "mcq",
            target_difficulty=q.difficulty or "medium",
            count_requested=1,
            status="pending",
            created_at=datetime.utcnow(),
        ))

        db.add(ContentAuditLog(
            question_id=question_id,
            admin_id=reviewer.id,
            action="retire",
            before=before,
            after=after,
            note=f"Rejected by reviewer: {body.reject_reason}. {body.comment or ''}",
        ))

    await db.commit()
    return {"ok": True, "decision": body.decision, "question_id": str(question_id)}


@router.get("/stats")
async def reviewer_stats(
    reviewer: User = Depends(require_reviewer()),
    db: AsyncSession = Depends(get_db),
):
    """Return reviewer's own review statistics."""
    total = (await db.execute(
        select(func.count()).where(QuestionReview.reviewer_user_id == reviewer.id)
    )).scalar_one()

    by_decision = (await db.execute(
        select(QuestionReview.decision, func.count().label("cnt"))
        .where(QuestionReview.reviewer_user_id == reviewer.id)
        .group_by(QuestionReview.decision)
    )).all()

    avg_scores = (await db.execute(
        select(
            func.avg(QuestionReview.realism).label("avg_realism"),
            func.avg(QuestionReview.clinical_accuracy).label("avg_clinical_accuracy"),
            func.avg(QuestionReview.key_correct).label("avg_key_correct"),
            func.avg(QuestionReview.rationale_quality).label("avg_rationale_quality"),
            func.avg(QuestionReview.language_clarity).label("avg_language_clarity"),
        ).where(QuestionReview.reviewer_user_id == reviewer.id)
    )).one()

    return {
        "reviewer_id": str(reviewer.id),
        "total_reviews": total,
        "by_decision": {r.decision: r.cnt for r in by_decision},
        "avg_scores": {
            "realism":           round(avg_scores.avg_realism or 0, 2),
            "clinical_accuracy": round(avg_scores.avg_clinical_accuracy or 0, 2),
            "key_correct":       round(avg_scores.avg_key_correct or 0, 2),
            "rationale_quality": round(avg_scores.avg_rationale_quality or 0, 2),
            "language_clarity":  round(avg_scores.avg_language_clarity or 0, 2),
        },
    }
