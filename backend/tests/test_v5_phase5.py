"""V5 Phase 5 — Spaced Repetition System (SRS) tests.

Coverage:
- POST /srs/enqueue: auth required, 404 on unknown lesson, success, idempotent
- GET  /srs/queue: empty for fresh user, populated after enqueue (forces next_review to past)
- POST /srs/review/{id}: SM-2 update, 404 on wrong item, quality validates 0-5
- GET  /srs/stats: total/due counts
- DELETE /srs/items/{id}: removes item, 404 for other users item
- SRS preference: disabled preference skips enqueue
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Article, Lesson, LessonSrsItem, Module, User

pytestmark = pytest.mark.anyio


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _reg(client: AsyncClient, email: str, role: str = "student") -> tuple[str, str]:
    r = await client.post("/api/v1/auth/register", json={
        "email": email, "password": "Str0ng!Pass99",
        "first_name": "SRS", "last_name": "Tester",
        "role": role,
        "consent_terms": True, "consent_data_processing": True,
    })
    assert r.status_code == 201, r.text
    body = r.json()
    return body["access_token"], body["user"]["id"]


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _make_lesson(db: AsyncSession) -> str:
    """Create a published module + lesson; return lesson_id as str."""
    mod = Module(
        title=f"SRS Module {uuid.uuid4().hex[:4]}",
        code=f"SRS-{uuid.uuid4().hex[:4]}",
        is_published=True,
        is_fundamental=True,
    )
    db.add(mod)
    await db.flush()

    lesson = Lesson(
        module_id=mod.id,
        title="SRS Test Lesson",
        lesson_order=1,
        content={"blocks": [{"type": "p", "text": "Test content for SRS review."}]},
    )
    db.add(lesson)
    await db.commit()
    await db.refresh(lesson)
    return str(lesson.id)


async def _make_article(db: AsyncSession) -> str:
    """Create an article; return its id as str."""
    article = Article(
        title="SRS Test Article",
        slug=f"srs-test-{uuid.uuid4().hex[:6]}",
        body=[{"type": "p", "content": "Article body for SRS testing."}],
        excerpt="Short excerpt.",
        category="general",
    )
    db.add(article)
    await db.commit()
    await db.refresh(article)
    return str(article.id)


async def _force_due(db: AsyncSession, item_id: str):
    """Move next_review_at to the past so the item shows up in the queue."""
    from sqlalchemy import select
    item = (await db.execute(
        select(LessonSrsItem).where(LessonSrsItem.id == uuid.UUID(item_id))
    )).scalar_one()
    item.next_review_at = datetime.utcnow() - timedelta(hours=1)
    await db.commit()


# ── Tests: enqueue ────────────────────────────────────────────────────────────

async def test_enqueue_requires_auth(client: AsyncClient):
    r = await client.post("/api/v1/srs/enqueue", json={
        "entity_type": "lesson",
        "entity_id": str(uuid.uuid4()),
    })
    assert r.status_code == 401


async def test_enqueue_invalid_entity_type(client: AsyncClient, db_session: AsyncSession):
    token, _ = await _reg(client, "srs_bad_type@test.com")
    r = await client.post("/api/v1/srs/enqueue", json={
        "entity_type": "quiz",
        "entity_id": str(uuid.uuid4()),
    }, headers=_h(token))
    assert r.status_code == 422


async def test_enqueue_lesson_not_found(client: AsyncClient, db_session: AsyncSession):
    token, _ = await _reg(client, "srs_404@test.com")
    r = await client.post("/api/v1/srs/enqueue", json={
        "entity_type": "lesson",
        "entity_id": str(uuid.uuid4()),
    }, headers=_h(token))
    assert r.status_code == 404


async def test_enqueue_lesson_success(client: AsyncClient, db_session: AsyncSession):
    lesson_id = await _make_lesson(db_session)
    token, _ = await _reg(client, "srs_ok@test.com")
    r = await client.post("/api/v1/srs/enqueue", json={
        "entity_type": "lesson",
        "entity_id": lesson_id,
    }, headers=_h(token))
    assert r.status_code == 201
    body = r.json()
    assert body["enrolled"] is True
    assert body["already_enrolled"] is False
    assert "item_id" in body
    assert "next_review_at" in body


async def test_enqueue_idempotent(client: AsyncClient, db_session: AsyncSession):
    lesson_id = await _make_lesson(db_session)
    token, _ = await _reg(client, "srs_idem@test.com")
    payload = {"entity_type": "lesson", "entity_id": lesson_id}

    r1 = await client.post("/api/v1/srs/enqueue", json=payload, headers=_h(token))
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/srs/enqueue", json=payload, headers=_h(token))
    assert r2.status_code == 201
    assert r2.json()["already_enrolled"] is True


async def test_enqueue_article(client: AsyncClient, db_session: AsyncSession):
    article_id = await _make_article(db_session)
    token, _ = await _reg(client, "srs_article@test.com")
    r = await client.post("/api/v1/srs/enqueue", json={
        "entity_type": "article",
        "entity_id": article_id,
    }, headers=_h(token))
    assert r.status_code == 201
    assert r.json()["enrolled"] is True


async def test_enqueue_srs_disabled_preference(client: AsyncClient, db_session: AsyncSession):
    """User with srs_enabled=False should get enrolled=False."""
    lesson_id = await _make_lesson(db_session)
    token, uid = await _reg(client, "srs_disabled@test.com")

    # Set preference
    from sqlalchemy import select
    user = (await db_session.execute(
        select(User).where(User.id == uuid.UUID(uid))
    )).scalar_one()
    user.preferences = {"srs_enabled": False}
    await db_session.commit()

    r = await client.post("/api/v1/srs/enqueue", json={
        "entity_type": "lesson",
        "entity_id": lesson_id,
    }, headers=_h(token))
    assert r.status_code == 201
    assert r.json()["enrolled"] is False
    assert r.json()["reason"] == "srs_disabled"


# ── Tests: queue ──────────────────────────────────────────────────────────────

async def test_queue_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/srs/queue")
    assert r.status_code == 401


async def test_queue_empty_for_new_user(client: AsyncClient, db_session: AsyncSession):
    token, _ = await _reg(client, "srs_empty@test.com")
    r = await client.get("/api/v1/srs/queue", headers=_h(token))
    assert r.status_code == 200
    assert r.json()["items"] == []
    assert r.json()["total"] == 0


async def test_queue_returns_due_item(client: AsyncClient, db_session: AsyncSession):
    lesson_id = await _make_lesson(db_session)
    token, _ = await _reg(client, "srs_queue@test.com")

    # Enqueue
    r = await client.post("/api/v1/srs/enqueue", json={
        "entity_type": "lesson", "entity_id": lesson_id,
    }, headers=_h(token))
    item_id = r.json()["item_id"]

    # Force it to be due now
    await _force_due(db_session, item_id)

    r2 = await client.get("/api/v1/srs/queue", headers=_h(token))
    assert r2.status_code == 200
    body = r2.json()
    assert body["total"] == 1
    assert body["items"][0]["item_id"] == item_id
    assert body["items"][0]["entity_type"] == "lesson"
    assert "title" in body["items"][0]
    assert isinstance(body["items"][0]["questions"], list)


async def test_queue_not_due_yet_hidden(client: AsyncClient, db_session: AsyncSession):
    lesson_id = await _make_lesson(db_session)
    token, _ = await _reg(client, "srs_future@test.com")
    await client.post("/api/v1/srs/enqueue", json={
        "entity_type": "lesson", "entity_id": lesson_id,
    }, headers=_h(token))

    # Don't force due — next_review is 1 day from now
    r = await client.get("/api/v1/srs/queue", headers=_h(token))
    assert r.json()["total"] == 0


# ── Tests: review ─────────────────────────────────────────────────────────────

async def test_review_requires_auth(client: AsyncClient):
    r = await client.post(f"/api/v1/srs/review/{uuid.uuid4()}", json={"quality": 4})
    assert r.status_code == 401


async def test_review_404_wrong_user(client: AsyncClient, db_session: AsyncSession):
    lesson_id = await _make_lesson(db_session)
    tok_a, _ = await _reg(client, "srs_rev_a@test.com")
    tok_b, _ = await _reg(client, "srs_rev_b@test.com")

    r = await client.post("/api/v1/srs/enqueue", json={
        "entity_type": "lesson", "entity_id": lesson_id,
    }, headers=_h(tok_a))
    item_id = r.json()["item_id"]

    # User B tries to review User A's item
    r2 = await client.post(f"/api/v1/srs/review/{item_id}", json={"quality": 4}, headers=_h(tok_b))
    assert r2.status_code == 404


async def test_review_sm2_update(client: AsyncClient, db_session: AsyncSession):
    lesson_id = await _make_lesson(db_session)
    token, _ = await _reg(client, "srs_sm2@test.com")

    r = await client.post("/api/v1/srs/enqueue", json={
        "entity_type": "lesson", "entity_id": lesson_id,
    }, headers=_h(token))
    item_id = r.json()["item_id"]

    # Perfect recall (quality=5)
    r2 = await client.post(f"/api/v1/srs/review/{item_id}", json={"quality": 5}, headers=_h(token))
    assert r2.status_code == 200
    body = r2.json()
    assert body["item_id"] == item_id
    assert body["interval_days"] == 6   # first review: 1→6 on quality≥3
    assert body["review_count"] == 1
    assert "next_review_at" in body
    assert float(body["ease_factor"]) > 2.5   # improved from perfect recall


async def test_review_bad_recall_resets_interval(client: AsyncClient, db_session: AsyncSession):
    lesson_id = await _make_lesson(db_session)
    token, _ = await _reg(client, "srs_bad_recall@test.com")

    r = await client.post("/api/v1/srs/enqueue", json={
        "entity_type": "lesson", "entity_id": lesson_id,
    }, headers=_h(token))
    item_id = r.json()["item_id"]

    r2 = await client.post(f"/api/v1/srs/review/{item_id}", json={"quality": 1}, headers=_h(token))
    assert r2.status_code == 200
    assert r2.json()["interval_days"] == 1   # reset on quality < 3


# ── Tests: stats ──────────────────────────────────────────────────────────────

async def test_stats_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/srs/stats")
    assert r.status_code == 401


async def test_stats_shape(client: AsyncClient, db_session: AsyncSession):
    token, _ = await _reg(client, "srs_stats@test.com")
    r = await client.get("/api/v1/srs/stats", headers=_h(token))
    assert r.status_code == 200
    body = r.json()
    assert "total_enrolled" in body
    assert "due_today" in body
    assert body["total_enrolled"] == 0
    assert body["due_today"] == 0


async def test_stats_counts_after_enqueue(client: AsyncClient, db_session: AsyncSession):
    lesson_id = await _make_lesson(db_session)
    token, _ = await _reg(client, "srs_stats2@test.com")

    r_enq = await client.post("/api/v1/srs/enqueue", json={
        "entity_type": "lesson", "entity_id": lesson_id,
    }, headers=_h(token))
    item_id = r_enq.json()["item_id"]
    await _force_due(db_session, item_id)

    r = await client.get("/api/v1/srs/stats", headers=_h(token))
    body = r.json()
    assert body["total_enrolled"] == 1
    assert body["due_today"] == 1


# ── Tests: delete ─────────────────────────────────────────────────────────────

async def test_delete_requires_auth(client: AsyncClient):
    r = await client.delete(f"/api/v1/srs/items/{uuid.uuid4()}")
    assert r.status_code == 401


async def test_delete_removes_item(client: AsyncClient, db_session: AsyncSession):
    lesson_id = await _make_lesson(db_session)
    token, _ = await _reg(client, "srs_del@test.com")

    r = await client.post("/api/v1/srs/enqueue", json={
        "entity_type": "lesson", "entity_id": lesson_id,
    }, headers=_h(token))
    item_id = r.json()["item_id"]

    r_del = await client.delete(f"/api/v1/srs/items/{item_id}", headers=_h(token))
    assert r_del.status_code == 204

    r_stats = await client.get("/api/v1/srs/stats", headers=_h(token))
    assert r_stats.json()["total_enrolled"] == 0


async def test_delete_other_users_item_404(client: AsyncClient, db_session: AsyncSession):
    lesson_id = await _make_lesson(db_session)
    tok_a, _ = await _reg(client, "srs_del_a@test.com")
    tok_b, _ = await _reg(client, "srs_del_b@test.com")

    r = await client.post("/api/v1/srs/enqueue", json={
        "entity_type": "lesson", "entity_id": lesson_id,
    }, headers=_h(tok_a))
    item_id = r.json()["item_id"]

    r_del = await client.delete(f"/api/v1/srs/items/{item_id}", headers=_h(tok_b))
    assert r_del.status_code == 404


# ── Tests: dashboard integration ──────────────────────────────────────────────

async def test_dashboard_includes_srs_due(client: AsyncClient, db_session: AsyncSession):
    """Dashboard stats should expose srs_due field after Phase 5 update."""
    lesson_id = await _make_lesson(db_session)
    token, _ = await _reg(client, "srs_dash@test.com")

    r_enq = await client.post("/api/v1/srs/enqueue", json={
        "entity_type": "lesson", "entity_id": lesson_id,
    }, headers=_h(token))
    item_id = r_enq.json()["item_id"]
    await _force_due(db_session, item_id)

    r = await client.get("/api/v1/dashboard/overview", headers=_h(token))
    assert r.status_code == 200
    body = r.json()
    assert "srs_due" in body["stats"]
    assert body["stats"]["srs_due"] >= 1
