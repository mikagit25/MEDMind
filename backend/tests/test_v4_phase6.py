"""V4 Phase 6 — Reviewer workspace tests.

Tests:
  1. Unauthenticated access to reviewer-queue returns 401
  2. Student role cannot access reviewer-queue (403)
  3. Reviewer role can list reviewer-queue
  4. Admin role can list reviewer-queue
  5. Reviewer-queue list sorted by view_count descending
  6. Reviewer-queue detail returns body/sources/verification_report
  7. Reviewer-queue detail returns 404 for unknown article
  8. Approve sets verification_status=human_reviewed
  9. Approve sets reviewed_by to the approver's name
 10. Request-changes sets verification_status=failed + review_note
 11. Request-changes without comment returns 400
 12. Stats summary returns correct counts
 13. Weekly reviewer digest function (email dev-mode log)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Article, ContentFeedback, User


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _create_user(client: AsyncClient, email: str, password: str = "Str0ng!Pass99") -> str:
    r = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "first_name": "Test",
        "last_name": "Reviewer",
        "consent_terms": True,
        "consent_data_processing": True,
    })
    assert r.status_code == 201, r.text
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


async def _set_role(db: AsyncSession, client: AsyncClient, token: str, role: str) -> None:
    """Set user role by user ID (fetched via /me) — avoids encrypted-email lookup issues."""
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    user_id = uuid.UUID(me.json()["id"])
    await db.execute(update(User).where(User.id == user_id).values(role=role))
    await db.commit()


def _make_article(db: AsyncSession, **kwargs) -> Article:
    defaults = dict(
        id=uuid.uuid4(),
        slug=f"article-{uuid.uuid4().hex[:8]}",
        title="Test Article",
        excerpt="Test excerpt for reviewer queue.",
        body=[{"type": "p", "content": "Test body paragraph."}],
        category="cardiology",
        verification_status="passed",
        is_published=True,
        review_status="published",
        view_count=100,
    )
    defaults.update(kwargs)
    a = Article(**defaults)
    db.add(a)
    return a


# ── Auth guard tests ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reviewer_queue_unauthenticated(client: AsyncClient):
    """No token → 401."""
    r = await client.get("/api/v1/admin/reviewer-queue")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_reviewer_queue_student_forbidden(client: AsyncClient, db_session: AsyncSession):
    """Student role → 403."""
    token = await _create_user(client, "student_rq@test.medmind")
    r = await client.get("/api/v1/admin/reviewer-queue", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


# ── Access control — reviewer and admin can access ─────────────────────────────

@pytest.mark.asyncio
async def test_reviewer_role_can_list_queue(client: AsyncClient, db_session: AsyncSession):
    """User with role='reviewer' can access the reviewer queue."""
    email = "reviewer_rq@test.medmind"
    token = await _create_user(client, email)
    await _set_role(db_session, client, token, "reviewer")

    r = await client.get("/api/v1/admin/reviewer-queue", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert "items" in r.json()


@pytest.mark.asyncio
async def test_admin_role_can_list_queue(client: AsyncClient, db_session: AsyncSession):
    """Admin can access reviewer queue."""
    email = "admin_rq@test.medmind"
    token = await _create_user(client, email)
    await _set_role(db_session, client, token, "admin")

    r = await client.get("/api/v1/admin/reviewer-queue", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


# ── Queue list — content and ordering ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_reviewer_queue_sorted_by_view_count(client: AsyncClient, db_session: AsyncSession):
    """Queue is sorted by view_count descending (highest traffic first)."""
    _make_article(db_session, title="Low Traffic", slug="low-traffic", view_count=10)
    _make_article(db_session, title="High Traffic", slug="high-traffic", view_count=9999)
    _make_article(db_session, title="Mid Traffic", slug="mid-traffic", view_count=500)
    await db_session.commit()

    email = "reviewer_sort@test.medmind"
    token = await _create_user(client, email)
    await _set_role(db_session, client, token, "reviewer")

    r = await client.get("/api/v1/admin/reviewer-queue", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    items = r.json()["items"]
    slugs = [i["slug"] for i in items]
    assert slugs.index("high-traffic") < slugs.index("mid-traffic")
    assert slugs.index("mid-traffic") < slugs.index("low-traffic")


@pytest.mark.asyncio
async def test_reviewer_queue_excludes_non_passed(client: AsyncClient, db_session: AsyncSession):
    """Only articles with verification_status='passed' appear in the queue."""
    _make_article(db_session, slug="passed-art", verification_status="passed")
    _make_article(db_session, slug="human-reviewed-art", verification_status="human_reviewed")
    _make_article(db_session, slug="failed-art", verification_status="failed")
    await db_session.commit()

    email = "reviewer_excl@test.medmind"
    token = await _create_user(client, email)
    await _set_role(db_session, client, token, "reviewer")

    r = await client.get("/api/v1/admin/reviewer-queue", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    slugs = [i["slug"] for i in r.json()["items"]]
    assert "passed-art" in slugs
    assert "human-reviewed-art" not in slugs
    assert "failed-art" not in slugs


# ── Article detail ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reviewer_queue_detail_not_found(client: AsyncClient, db_session: AsyncSession):
    """Unknown article UUID → 404."""
    email = "reviewer_det404@test.medmind"
    token = await _create_user(client, email)
    await _set_role(db_session, client, token, "reviewer")

    fake_id = uuid.uuid4()
    r = await client.get(
        f"/api/v1/admin/reviewer-queue/{fake_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_reviewer_queue_detail_fields(client: AsyncClient, db_session: AsyncSession):
    """Article detail response contains body, sources, verification_report, review_note."""
    article = _make_article(
        db_session,
        slug="detail-test",
        sources=[{"title": "PubMed Ref", "url": "https://pubmed.ncbi.nlm.nih.gov/1234"}],
        faq=[{"question": "Q?", "answer": "A."}],
    )
    await db_session.commit()

    email = "reviewer_fields@test.medmind"
    token = await _create_user(client, email)
    await _set_role(db_session, client, token, "reviewer")

    r = await client.get(
        f"/api/v1/admin/reviewer-queue/{article.id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "body" in data
    assert "sources" in data
    assert "faq" in data
    assert "verification_report" in data
    assert "review_note" in data
    assert data["slug"] == "detail-test"


# ── Approve ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_approve_sets_human_reviewed(client: AsyncClient, db_session: AsyncSession):
    """Approving an article sets verification_status='human_reviewed'."""
    article = _make_article(db_session, slug="approve-me")
    await db_session.commit()

    email = "reviewer_approve@test.medmind"
    token = await _create_user(client, email)
    await _set_role(db_session, client, token, "reviewer")

    r = await client.post(
        f"/api/v1/admin/reviewer-queue/{article.id}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["verification_status"] == "human_reviewed"
    assert data["reviewed_by"]
    assert data["last_verified_at"]


@pytest.mark.asyncio
async def test_approve_sets_reviewed_by_name(client: AsyncClient, db_session: AsyncSession):
    """Approving sets reviewed_by to the reviewer's full name."""
    article = _make_article(db_session, slug="approve-name")
    await db_session.commit()

    email = "dr_approver@test.medmind"
    token = await _create_user(client, email)
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    user_id = uuid.UUID(me.json()["id"])
    await db_session.execute(
        update(User).where(User.id == user_id).values(
            role="reviewer", first_name="Jane", last_name="Smith"
        )
    )
    await db_session.commit()

    r = await client.post(
        f"/api/v1/admin/reviewer-queue/{article.id}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["reviewed_by"] == "Jane Smith"


# ── Request changes ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_request_changes_sets_failed(client: AsyncClient, db_session: AsyncSession):
    """Request-changes sets verification_status='failed' and stores the note."""
    article = _make_article(db_session, slug="needs-changes")
    await db_session.commit()

    email = "reviewer_rc@test.medmind"
    token = await _create_user(client, email)
    await _set_role(db_session, client, token, "reviewer")

    r = await client.post(
        f"/api/v1/admin/reviewer-queue/{article.id}/request-changes",
        headers={"Authorization": f"Bearer {token}"},
        json={"comment": "Missing dosage references in section 2."},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["verification_status"] == "failed"
    assert "Missing dosage" in data["review_note"]


@pytest.mark.asyncio
async def test_request_changes_empty_comment_400(client: AsyncClient, db_session: AsyncSession):
    """Request-changes with empty comment returns 400."""
    article = _make_article(db_session, slug="empty-comment")
    await db_session.commit()

    email = "reviewer_400@test.medmind"
    token = await _create_user(client, email)
    await _set_role(db_session, client, token, "reviewer")

    r = await client.post(
        f"/api/v1/admin/reviewer-queue/{article.id}/request-changes",
        headers={"Authorization": f"Bearer {token}"},
        json={"comment": "   "},
    )
    assert r.status_code == 400


# ── Stats summary ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reviewer_stats_summary(client: AsyncClient, db_session: AsyncSession):
    """Stats summary returns queue_depth, unresolved_feedback, human_reviewed_total."""
    # Create 2 passed articles (queue)
    _make_article(db_session, slug="stat-q1", verification_status="passed")
    _make_article(db_session, slug="stat-q2", verification_status="passed")
    # Create 1 human_reviewed (not in queue)
    _make_article(db_session, slug="stat-hr1", verification_status="human_reviewed")
    # Create unresolved feedback
    db_session.add(ContentFeedback(
        content_type="article",
        content_id="stat-q1",
        problem_type="factual_error",
        comment="Factual error in section 1",
        resolved=False,
    ))
    await db_session.commit()

    email = "reviewer_stats@test.medmind"
    token = await _create_user(client, email)
    await _set_role(db_session, client, token, "reviewer")

    r = await client.get(
        "/api/v1/admin/reviewer-queue/stats/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["queue_depth"] >= 2
    assert data["unresolved_feedback"] >= 1
    assert data["human_reviewed_total"] >= 1
    assert "queue_depth" in data
    assert "unresolved_feedback" in data
    assert "human_reviewed_total" in data


# ── Email digest function ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reviewer_digest_dev_mode_logs(caplog):
    """send_reviewer_digest logs in dev mode (no SMTP configured)."""
    import logging
    from app.services.email_service import send_reviewer_digest

    with caplog.at_level(logging.INFO, logger="app.services.email_service"):
        await send_reviewer_digest(
            to_email="reviewer@example.com",
            reviewer_name="Dr. Test",
            queue_count=5,
            feedback_count=2,
        )

    # In dev mode (no SMTP), it should log the digest summary
    assert any("reviewer@example.com" in r.message or "queue" in r.message.lower() for r in caplog.records)
