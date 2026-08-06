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
    QuestionReview, QuestionStats, User, Reviewer,
    JurisdictionRule,
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


# ── L5: Jurisdiction reviewer queue ───────────────────────────────────────────

GULF_SLUGS = {"snle", "dha", "haad", "doh", "qchp", "omsb", "nhra", "moh_kw"}
EXAM_TO_JURISDICTION = {
    "snle": "sa", "dha": "ae_dubai", "haad": "ae_abudhabi", "doh": "ae_abudhabi",
    "qchp": "qa", "omsb": "om", "nhra": "bh", "moh_kw": "kw",
}


class JurisdictionReviewBody(BaseModel):
    """L5.3 — Extended rubric for jurisdiction-sensitive question review."""
    locally_correct: str = Field(..., pattern=r"^(yes|no|uncertain)$")
    scope_ok: str = Field(..., pattern=r"^(yes|no)$")
    culturally_appropriate: str = Field(..., pattern=r"^(yes|needs_edit)$")
    local_note: Optional[str] = None
    jurisdiction_slug: str   # must match one the reviewer is authorized for


@router.get("/queue/jurisdiction")
async def jurisdiction_queue(
    jurisdiction: Optional[str] = Query(None, description="Filter by jurisdiction slug, e.g. 'sa'"),
    limit: int = Query(20, ge=1, le=100),
    reviewer: User = Depends(require_reviewer()),
    db: AsyncSession = Depends(get_db),
):
    """L5.2 — Jurisdiction-sensitive questions awaiting local reviewer confirmation.

    Returns questions that are:
    - jurisdiction_sensitive=True
    - jurisdiction_verified_for is NULL (quarantined)
    - tagged to a Gulf exam matching the reviewer's authorized jurisdictions

    Only returns questions the reviewer is authorized to review (by their
    jurisdictions field on the Reviewer record, if exists).
    """
    # Find reviewer record for jurisdiction authorization
    reviewer_record = (await db.execute(
        select(Reviewer).where(Reviewer.slug == reviewer.email.split("@")[0])
    )).scalar_one_or_none()

    authorized_jurisdictions: list[str] = []
    if reviewer_record and reviewer_record.jurisdictions:
        authorized_jurisdictions = reviewer_record.jurisdictions
    elif jurisdiction:
        authorized_jurisdictions = [jurisdiction]
    # Admins see all
    if reviewer.role == "admin":
        if jurisdiction:
            authorized_jurisdictions = [jurisdiction]
        else:
            authorized_jurisdictions = list(EXAM_TO_JURISDICTION.values())

    if not authorized_jurisdictions:
        return {"questions": [], "total": 0, "note": "No jurisdiction authorization found — contact admin"}

    # Determine which exam slugs match authorized jurisdictions
    authorized_exams = [
        slug for slug, jur in EXAM_TO_JURISDICTION.items()
        if jur in authorized_jurisdictions
    ]

    # Query quarantined Gulf questions
    from sqlalchemy import or_, literal as sa_literal
    import json as _json
    from sqlalchemy.dialects.postgresql import JSONB as _JSONB

    q_stmt = (
        select(MCQQuestion)
        .where(
            MCQQuestion.status == "active",
            MCQQuestion.jurisdiction_sensitive == True,
            MCQQuestion.jurisdiction_verified_for.is_(None),
        )
        .order_by(MCQQuestion.created_at.asc())
        .limit(limit)
    )

    # Filter to questions tagged with authorized exam slugs
    all_quarantined = (await db.execute(q_stmt)).scalars().all()
    result = []
    for q in all_quarantined:
        q_exams = set(q.exam_slugs or [])
        if q_exams & set(authorized_exams):
            # Which jurisdictions apply?
            applicable = [EXAM_TO_JURISDICTION[s] for s in q_exams & set(authorized_exams)]
            result.append({
                "id": str(q.id),
                "question": q.question,
                "options": q.options,
                "correct": q.correct,
                "explanation": q.explanation,
                "rationales": q.rationales,
                "key_takeaway": q.key_takeaway,
                "nclex_client_needs": q.nclex_client_needs,
                "exam_slugs": q.exam_slugs,
                "applicable_jurisdictions": list(set(applicable)),
                "jurisdiction_audit_notes": q.jurisdiction_audit_notes,
                "origin": q.origin,
            })

    return {
        "questions": result,
        "total": len(result),
        "authorized_jurisdictions": authorized_jurisdictions,
    }


@router.post("/submit-jurisdiction/{question_id}")
async def submit_jurisdiction_review(
    question_id: uuid.UUID,
    body: JurisdictionReviewBody,
    reviewer: User = Depends(require_reviewer()),
    db: AsyncSession = Depends(get_db),
):
    """L5.4 — Submit local reviewer judgment for a jurisdiction-sensitive question.

    - locally_correct=yes + scope_ok=yes → exits quarantine for this jurisdiction
    - locally_correct=no OR scope_ok=no → question retired + regeneration queued
    - local_note → creates draft JurisdictionRule (needs_human) for human source confirmation
    - L5.6: verified_for updated on question
    """
    q = await db.get(MCQQuestion, question_id)
    if not q:
        raise HTTPException(404, "Question not found")

    # Authorization check: reviewer must cover this jurisdiction
    reviewer_record = (await db.execute(
        select(Reviewer).where(Reviewer.slug == reviewer.email.split("@")[0])
    )).scalar_one_or_none()

    authorized = False
    if reviewer.role == "admin":
        authorized = True
    elif reviewer_record and reviewer_record.jurisdictions:
        authorized = body.jurisdiction_slug in reviewer_record.jurisdictions

    if not authorized:
        raise HTTPException(
            403,
            f"Reviewer not authorized for jurisdiction '{body.jurisdiction_slug}'"
        )

    # Verify question is tagged to an exam in this jurisdiction
    exam_for_jur = [s for s, j in EXAM_TO_JURISDICTION.items() if j == body.jurisdiction_slug]
    q_exams = set(q.exam_slugs or [])
    if not (q_exams & set(exam_for_jur)):
        raise HTTPException(
            400,
            f"Question is not tagged to any exam in jurisdiction '{body.jurisdiction_slug}'"
        )

    # Record the rubric
    review = QuestionReview(
        question_id=question_id,
        reviewer_user_id=reviewer.id,
        # Standard rubric — set neutral values for jurisdiction-only review
        realism=3, clinical_accuracy=3, key_correct=3,
        rationale_quality=3, distractors_plausible=3,
        language_clarity=3, category_correct=3,
        decision="approve" if (body.locally_correct == "yes" and body.scope_ok == "yes") else "reject",
        comment=body.local_note,
        locally_correct=body.locally_correct,
        scope_ok=body.scope_ok,
        culturally_appropriate=body.culturally_appropriate,
        local_note=body.local_note,
        jurisdiction_slug=body.jurisdiction_slug,
    )
    db.add(review)

    action_taken = ""

    if body.locally_correct == "yes" and body.scope_ok == "yes":
        # L5.4: exit quarantine for this jurisdiction
        existing_verified = list(q.jurisdiction_verified_for or [])
        if body.jurisdiction_slug not in existing_verified:
            existing_verified.append(body.jurisdiction_slug)
        q.jurisdiction_verified_for = existing_verified
        action_taken = "released_from_quarantine"
    else:
        # locally_correct=no or scope_ok=no → retire + regenerate
        q.status = "retired"
        q.verification_status = "flagged"
        action_taken = "retired"
        exam_slug = (q.exam_slugs or ["snle"])[0]
        db.add(GenerationQueue(
            exam_slug=exam_slug,
            nclex_category=q.nclex_client_needs or "nursing_fundamentals",
            question_type=q.question_type or "mcq",
            target_difficulty=q.difficulty or "medium",
            count_requested=1,
            status="pending",
            created_at=datetime.utcnow(),
        ))

    # L5.5: local_note creates draft JurisdictionRule
    if body.local_note:
        # Map jurisdiction to domain based on audit notes (rough heuristic)
        audit_domains = []
        if q.jurisdiction_audit_notes:
            import json as _json2
            try:
                audit_domains = _json2.loads(q.jurisdiction_audit_notes)
            except Exception:
                pass
        domain = audit_domains[0] if audit_domains else "scope_of_practice"

        # Check if rule already exists
        existing_rule = (await db.execute(
            select(JurisdictionRule).where(
                JurisdictionRule.profile_slug == body.jurisdiction_slug,
                JurisdictionRule.domain == domain,
                JurisdictionRule.rule_key == f"reviewer_note_{str(question_id)[:8]}",
            )
        )).scalar_one_or_none()

        if not existing_rule:
            db.add(JurisdictionRule(
                profile_slug=body.jurisdiction_slug,
                domain=domain,
                rule_key=f"reviewer_note_{str(question_id)[:8]}",
                statement=body.local_note,
                source_title="Local reviewer note",
                source_url=None,
                source_type="regulator",
                status="needs_human",  # needs source confirmation before verified
                verified_by="human_reviewer",
                divergence_from_us=(body.locally_correct != "yes"),
            ))

    await db.commit()

    return {
        "ok": True,
        "question_id": str(question_id),
        "jurisdiction_slug": body.jurisdiction_slug,
        "locally_correct": body.locally_correct,
        "scope_ok": body.scope_ok,
        "action_taken": action_taken,
        "local_note_rule_created": bool(body.local_note),
    }
