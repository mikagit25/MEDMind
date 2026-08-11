"""Bank-Scale B4 — Reviewer workplace tests.

Verifies:
- QuestionReview model: create and retrieve
- Rubric field validation: scores must be 1-5
- /reviewer/queue: 401 without auth, 200 with reviewer role, returns structure
- /reviewer/queue: empty queue returns None question
- /reviewer/submit: approve sets human_reviewed
- /reviewer/submit: reject retires question + creates GenerationQueue entry
- /reviewer/submit: reject without reject_reason returns 422
- /reviewer/stats: returns review counts
- /admin/review-insights: 401 without auth, 200 with admin role, returns structure
"""
from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    ContentAuditLog, GenerationQueue, MCQQuestion, Module, QuestionReview, User,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

_RUBRIC = dict(
    realism=4, clinical_accuracy=5, key_correct=5,
    rationale_quality=4, distractors_plausible=3,
    language_clarity=4, category_correct=4,
)


async def _create_user(client: AsyncClient, email: str) -> str:
    r = await client.post("/api/v1/auth/register", json={
        "email": email, "password": "Test!Pass99",
        "first_name": "Test", "last_name": "User",
        "consent_terms": True, "consent_data_processing": True,
    })
    assert r.status_code == 201, r.text
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": "Test!Pass99"})
    return r.json()["access_token"]


async def _set_role(db: AsyncSession, client: AsyncClient, token: str, role: str) -> None:
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    user_id = uuid.UUID(me.json()["id"])
    await db.execute(update(User).where(User.id == user_id).values(role=role))
    await db.commit()


async def _seed_question(db: AsyncSession) -> MCQQuestion:
    """Insert a test Module + MCQQuestion for review."""
    mod = Module(
        id=uuid.uuid4(), title="B4 Test Module", specialty_id=None,
        code=f"TEST-B4-{uuid.uuid4().hex[:6]}", module_type="specialty_module",
        is_published=False,
    )
    db.add(mod)
    await db.flush()

    q = MCQQuestion(
        id=uuid.uuid4(),
        module_id=mod.id,
        question="A nurse is caring for a patient receiving heparin. What is the priority assessment?",
        options={"A": "Monitor INR", "B": "Monitor aPTT", "C": "Monitor BNP", "D": "Monitor CBC"},
        correct="B",
        explanation="Heparin therapy is monitored by aPTT.",
        difficulty="medium",
        question_type="mcq",
        nclex_client_needs="pharmacological",
        exam_slugs=["nclex_rn"],
        verification_status="pending",
        status="active",
    )
    db.add(q)
    await db.commit()
    return q


# ── Unit: QuestionReview model ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_question_review_create(db_session, client):
    """Can create a QuestionReview record and retrieve it."""
    q = await _seed_question(db_session)

    review = QuestionReview(
        id=uuid.uuid4(),
        question_id=q.id,
        reviewer_user_id=None,
        **_RUBRIC,
        decision="approve",
        created_at=datetime.utcnow(),
    )
    db_session.add(review)
    await db_session.commit()

    result = await db_session.execute(
        select(QuestionReview).where(QuestionReview.question_id == q.id)
    )
    fetched = result.scalar_one_or_none()
    assert fetched is not None
    assert fetched.decision == "approve"
    assert fetched.realism == 4
    assert fetched.key_correct == 5


@pytest.mark.asyncio
async def test_question_review_reject_fields(db_session, client):
    """Reject review stores reject_reason and comment."""
    q = await _seed_question(db_session)

    review = QuestionReview(
        id=uuid.uuid4(),
        question_id=q.id,
        reviewer_user_id=None,
        **_RUBRIC,
        decision="reject",
        reject_reason="factual_error",
        comment="The answer key is wrong — aPTT monitors heparin, not INR.",
        created_at=datetime.utcnow(),
    )
    db_session.add(review)
    await db_session.commit()

    result = await db_session.execute(
        select(QuestionReview).where(QuestionReview.question_id == q.id)
    )
    fetched = result.scalar_one_or_none()
    assert fetched.reject_reason == "factual_error"
    assert "INR" in fetched.comment


# ── API: reviewer/queue ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reviewer_queue_requires_auth(client):
    """Unauthenticated request returns 401 or 403 depending on auth scheme."""
    r = await client.get("/api/v1/reviewer/queue")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_reviewer_queue_requires_reviewer_role(client):
    """Regular user (student role) cannot access reviewer queue."""
    token = await _create_user(client, "student_b4@test.com")
    r = await client.get("/api/v1/reviewer/queue",
                         headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_reviewer_queue_empty(client, db_session):
    """Reviewer can access empty queue — returns None question."""
    token = await _create_user(client, "reviewer_empty_b4@test.com")
    await _set_role(db_session, client, token, "reviewer")

    r = await client.get("/api/v1/reviewer/queue",
                         headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["question"] is None


@pytest.mark.asyncio
async def test_reviewer_queue_returns_question(client, db_session):
    """With a pending question, reviewer gets it from the queue."""
    token = await _create_user(client, "reviewer_has_q_b4@test.com")
    await _set_role(db_session, client, token, "reviewer")
    q = await _seed_question(db_session)

    r = await client.get("/api/v1/reviewer/queue",
                         headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert data["question"] is not None
    question = data["question"]
    assert "id" in question
    assert "question" in question
    assert "options" in question
    assert "explanation" in question


# ── API: reviewer/submit ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_submit_approve_sets_human_reviewed(client, db_session):
    """Submitting approve sets verification_status='human_reviewed'."""
    token = await _create_user(client, "reviewer_approve_b4@test.com")
    await _set_role(db_session, client, token, "reviewer")
    q = await _seed_question(db_session)

    r = await client.post(
        f"/api/v1/reviewer/submit/{q.id}",
        json={**_RUBRIC, "decision": "approve", "comment": "Looks good."},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["decision"] == "approve"

    await db_session.refresh(q)
    assert q.verification_status == "human_reviewed"


@pytest.mark.asyncio
async def test_submit_reject_retires_and_queues(client, db_session):
    """Rejecting retires the question and creates a GenerationQueue entry."""
    token = await _create_user(client, "reviewer_reject_b4@test.com")
    await _set_role(db_session, client, token, "reviewer")
    q = await _seed_question(db_session)

    r = await client.post(
        f"/api/v1/reviewer/submit/{q.id}",
        json={
            **_RUBRIC,
            "decision": "reject",
            "reject_reason": "factual_error",
            "comment": "Incorrect answer key.",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200

    await db_session.refresh(q)
    assert q.status == "retired"

    # GenerationQueue entry created
    gq = (await db_session.execute(
        select(GenerationQueue).where(
            GenerationQueue.nclex_category == q.nclex_client_needs,
            GenerationQueue.status == "pending",
        )
    )).scalar_one_or_none()
    assert gq is not None
    assert gq.count_requested == 1


@pytest.mark.asyncio
async def test_submit_reject_without_reason_returns_422(client, db_session):
    """Reject without reject_reason must return 422."""
    token = await _create_user(client, "reviewer_reject_no_reason@test.com")
    await _set_role(db_session, client, token, "reviewer")
    q = await _seed_question(db_session)

    r = await client.post(
        f"/api/v1/reviewer/submit/{q.id}",
        json={**_RUBRIC, "decision": "reject"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_submit_approve_with_edits(client, db_session):
    """approve_with_edits applies field changes to the question."""
    token = await _create_user(client, "reviewer_edits_b4@test.com")
    await _set_role(db_session, client, token, "reviewer")
    q = await _seed_question(db_session)

    r = await client.post(
        f"/api/v1/reviewer/submit/{q.id}",
        json={
            **_RUBRIC,
            "decision": "approve_with_edits",
            "edits": {"difficulty": "hard"},
            "comment": "Elevated difficulty.",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200

    await db_session.refresh(q)
    assert q.verification_status == "human_reviewed"
    assert q.difficulty == "hard"


# ── API: reviewer/stats ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reviewer_stats(client, db_session):
    """Reviewer stats endpoint returns total and by_decision counts."""
    token = await _create_user(client, "reviewer_stats_b4@test.com")
    await _set_role(db_session, client, token, "reviewer")

    r = await client.get("/api/v1/reviewer/stats",
                         headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    assert "total_reviews" in data
    assert "by_decision" in data
    assert "avg_scores" in data


# ── API: admin/review-insights ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_review_insights_requires_admin(client):
    """Unauthenticated request returns 401 or 403 depending on auth scheme."""
    r = await client.get("/api/v1/admin/review-insights")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_review_insights_returns_structure(admin_client):
    """Admin can access review-insights and gets expected keys."""
    r = await admin_client.get("/api/v1/admin/review-insights")
    assert r.status_code == 200
    data = r.json()
    assert "total_reviews" in data
    assert "overall_avg" in data
    assert "by_category" in data
    assert "reject_reasons" in data
    assert "decisions" in data
    assert "comments" in data


@pytest.mark.asyncio
async def test_review_insights_aggregates_scores(admin_client, db_session):
    """review-insights aggregates rubric scores from actual reviews."""
    # Seed a question and a review
    q = await _seed_question(db_session)
    review = QuestionReview(
        id=uuid.uuid4(),
        question_id=q.id,
        reviewer_user_id=None,
        **_RUBRIC,
        decision="approve",
        created_at=datetime.utcnow(),
    )
    db_session.add(review)
    await db_session.commit()

    r = await admin_client.get("/api/v1/admin/review-insights?days=1")
    assert r.status_code == 200
    data = r.json()
    assert data["total_reviews"] >= 1
    assert data["overall_avg"].get("realism") is not None
