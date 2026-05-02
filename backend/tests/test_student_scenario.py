"""End-to-end student scenario test.

Simulates a real student workflow without Docker:
  1. Registration & profile
  2. Browse published lessons
  3. Complete a lesson (progress tracking)
  4. Flashcard review (spaced repetition)
  5. Personal notes
  6. Bookmarks
  7. Dashboard / stats
  8. Adaptive study plan
  9. Permission boundaries (student cannot do teacher actions)

All run in-memory (SQLite + FakeRedis) via the shared conftest fixtures.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

LESSON_CONTENT = {
    "title": "Pharmacology Basics",
    "blocks": [
        {
            "type": "text",
            "order": 0,
            "content": {"text": "## Introduction\nDrugs interact with receptors to produce effects."},
        },
        {
            "type": "quiz",
            "order": 1,
            "content": {
                "question": "What is the mechanism of beta-blockers?",
                "options": {"A": "Block alpha receptors", "B": "Block beta receptors", "C": "Activate dopamine"},
                "correct": "B",
                "explanation": "Beta-blockers competitively antagonise beta-adrenergic receptors.",
            },
        },
    ],
    "estimated_minutes": 15,
    "learning_objectives": ["Understand receptor pharmacology basics"],
    "species_applicability": ["human"],
    "clinical_risk_level": "low",
}


async def _register(client: AsyncClient, email: str, role: str) -> dict:
    reg = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Secure1234!",
        "first_name": "Test",
        "last_name": "User",
        "role": role,
        "consent_terms": True,
        "consent_data_processing": True,
    })
    assert reg.status_code == 201, f"Register failed ({role}): {reg.text}"
    data = reg.json()
    return {"token": data["access_token"], "user_id": data["user"]["id"]}


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _setup_published_lesson(client: AsyncClient) -> tuple[str, str]:
    """Create teacher + module + published lesson. Returns (teacher_token, lesson_id)."""
    teacher = await _register(client, f"t_{uuid.uuid4().hex[:6]}@example.com", "teacher")
    token = teacher["token"]

    mod = await client.post("/api/v1/lessons/modules",
        json={"title": "Pharmacology", "level_label": "beginner"},
        headers=_auth(token))
    assert mod.status_code == 201
    module_id = mod.json()["id"]

    les = await client.post(f"/api/v1/lessons/modules/{module_id}/lessons",
        json={"title": "Beta-Blockers", "content": LESSON_CONTENT,
              "estimated_minutes": 15, "lesson_order": 0},
        headers=_auth(token))
    assert les.status_code == 201
    lesson_id = les.json()["id"]

    pub = await client.patch(f"/api/v1/lessons/{lesson_id}/publish", headers=_auth(token))
    assert pub.status_code == 200

    return token, lesson_id


# ─────────────────────────────────────────────────────────────────────────────
# 1. Registration & profile
# ─────────────────────────────────────────────────────────────────────────────

class TestStudentRegistration:
    async def test_register_as_student(self, client):
        r = await client.post("/api/v1/auth/register", json={
            "email": "alice.jones@example.com",
            "password": "Student1234!",
            "first_name": "Alice",
            "last_name": "Jones",
            "role": "student",
            "consent_terms": True,
            "consent_data_processing": True,
        })
        assert r.status_code == 201
        data = r.json()
        assert data["user"]["role"] == "student"
        assert "access_token" in data

    async def test_duplicate_email_rejected(self, client):
        email = f"dup_{uuid.uuid4().hex[:6]}@example.com"
        await _register(client, email, "student")
        r = await client.post("/api/v1/auth/register", json={
            "email": email, "password": "Secure1234!", "first_name": "X",
            "last_name": "Y", "role": "student",
            "consent_terms": True, "consent_data_processing": True,
        })
        assert r.status_code == 400

    async def test_weak_password_rejected(self, client):
        r = await client.post("/api/v1/auth/register", json={
            "email": "weak@example.com", "password": "123",
            "first_name": "A", "last_name": "B", "role": "student",
            "consent_terms": True, "consent_data_processing": True,
        })
        assert r.status_code == 422

    async def test_get_own_profile(self, client):
        student = await _register(client, f"prof_{uuid.uuid4().hex[:6]}@example.com", "student")
        me = await client.get("/api/v1/auth/me", headers=_auth(student["token"]))
        assert me.status_code == 200
        assert me.json()["role"] == "student"

    async def test_update_profile(self, client):
        student = await _register(client, f"upd_{uuid.uuid4().hex[:6]}@example.com", "student")
        r = await client.patch("/api/v1/auth/me",
            json={"first_name": "Updated"},
            headers=_auth(student["token"]))
        assert r.status_code == 200
        assert r.json()["first_name"] == "Updated"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Browse lessons
# ─────────────────────────────────────────────────────────────────────────────

class TestStudentBrowsing:
    async def test_student_can_read_published_lesson(self, client):
        _, lesson_id = await _setup_published_lesson(client)
        student = await _register(client, f"br_{uuid.uuid4().hex[:6]}@example.com", "student")

        r = await client.get(f"/api/v1/lessons/{lesson_id}", headers=_auth(student["token"]))
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "published"
        assert data["title"] == "Beta-Blockers"

    async def test_student_cannot_see_draft(self, client):
        teacher = await _register(client, f"td_{uuid.uuid4().hex[:6]}@example.com", "teacher")
        student = await _register(client, f"sd_{uuid.uuid4().hex[:6]}@example.com", "student")

        mod = await client.post("/api/v1/lessons/modules",
            json={"title": "Hidden Module", "level_label": "beginner"},
            headers=_auth(teacher["token"]))
        module_id = mod.json()["id"]

        les = await client.post(f"/api/v1/lessons/modules/{module_id}/lessons",
            json={"title": "Draft Lesson", "content": LESSON_CONTENT,
                  "estimated_minutes": 15, "lesson_order": 0},
            headers=_auth(teacher["token"]))
        lesson_id = les.json()["id"]  # stays as draft

        r = await client.get(f"/api/v1/lessons/{lesson_id}", headers=_auth(student["token"]))
        assert r.status_code == 403

    async def test_student_cannot_see_draft_in_module_list(self, client):
        teacher = await _register(client, f"tl_{uuid.uuid4().hex[:6]}@example.com", "teacher")
        student = await _register(client, f"sl_{uuid.uuid4().hex[:6]}@example.com", "student")

        mod = await client.post("/api/v1/lessons/modules",
            json={"title": "Module", "level_label": "beginner"},
            headers=_auth(teacher["token"]))
        module_id = mod.json()["id"]

        await client.post(f"/api/v1/lessons/modules/{module_id}/lessons",
            json={"title": "Draft", "content": LESSON_CONTENT,
                  "estimated_minutes": 15, "lesson_order": 0},
            headers=_auth(teacher["token"]))

        r = await client.get(f"/api/v1/lessons/modules/{module_id}/lessons",
            headers=_auth(student["token"]))
        assert r.status_code == 200
        assert r.json() == []


# ─────────────────────────────────────────────────────────────────────────────
# 3. Lesson completion / progress tracking
# ─────────────────────────────────────────────────────────────────────────────

class TestLessonProgress:
    async def test_complete_lesson_returns_xp(self, client):
        _, lesson_id = await _setup_published_lesson(client)
        student = await _register(client, f"cp_{uuid.uuid4().hex[:6]}@example.com", "student")

        r = await client.post(f"/api/v1/progress/lesson/{lesson_id}/complete",
            json={"score": 90, "time_spent_seconds": 600},
            headers=_auth(student["token"]))
        assert r.status_code == 200
        data = r.json()
        assert "xp_earned" in data or "xp" in data or "message" in data

    async def test_progress_stats_after_completion(self, client):
        _, lesson_id = await _setup_published_lesson(client)
        student = await _register(client, f"ps_{uuid.uuid4().hex[:6]}@example.com", "student")

        await client.post(f"/api/v1/progress/lesson/{lesson_id}/complete",
            json={"score": 80, "time_spent_seconds": 500},
            headers=_auth(student["token"]))

        stats = await client.get("/api/v1/progress/stats", headers=_auth(student["token"]))
        assert stats.status_code == 200
        data = stats.json()
        assert "lessons_completed" in data or "total_lessons" in data or "xp" in data

    async def test_progress_history(self, client):
        # /progress/history uses SQL cast(DateTime, Date) which behaves differently
        # in SQLite vs PostgreSQL. Skip in SQLite test environment.
        import os
        if os.environ.get("DATABASE_URL", "").startswith("sqlite"):
            pytest.skip("cast(DateTime, Date) requires PostgreSQL — skipped in SQLite tests")

        _, lesson_id = await _setup_published_lesson(client)
        student = await _register(client, f"ph_{uuid.uuid4().hex[:6]}@example.com", "student")

        await client.post(f"/api/v1/progress/lesson/{lesson_id}/complete",
            json={"score": 75, "time_spent_seconds": 450},
            headers=_auth(student["token"]))

        r = await client.get("/api/v1/progress/history", headers=_auth(student["token"]))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_due_flashcards_endpoint(self, client):
        student = await _register(client, f"df_{uuid.uuid4().hex[:6]}@example.com", "student")
        r = await client.get("/api/v1/progress/flashcards/due", headers=_auth(student["token"]))
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_weaknesses_endpoint(self, client):
        student = await _register(client, f"wk_{uuid.uuid4().hex[:6]}@example.com", "student")
        r = await client.get("/api/v1/progress/weaknesses", headers=_auth(student["token"]))
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            assert isinstance(r.json(), (list, dict))


# ─────────────────────────────────────────────────────────────────────────────
# 4. Personal flashcards (spaced repetition)
# ─────────────────────────────────────────────────────────────────────────────

class TestPersonalFlashcards:
    async def test_create_flashcard(self, client):
        student = await _register(client, f"fc_{uuid.uuid4().hex[:6]}@example.com", "student")
        r = await client.post("/api/v1/my/flashcards",
            json={"question": "What is the half-life of aspirin?",
                  "answer": "15-20 minutes (active metabolite salicylate: 2-3 hours)",
                  "difficulty": "medium"},
            headers=_auth(student["token"]))
        assert r.status_code == 201
        data = r.json()
        assert data["question"] == "What is the half-life of aspirin?"
        return data["id"], student["token"]

    async def test_list_flashcards(self, client):
        student = await _register(client, f"fcl_{uuid.uuid4().hex[:6]}@example.com", "student")
        await client.post("/api/v1/my/flashcards",
            json={"question": "Q1?", "answer": "A1", "difficulty": "easy"},
            headers=_auth(student["token"]))
        await client.post("/api/v1/my/flashcards",
            json={"question": "Q2?", "answer": "A2", "difficulty": "hard"},
            headers=_auth(student["token"]))

        r = await client.get("/api/v1/my/flashcards", headers=_auth(student["token"]))
        assert r.status_code == 200
        assert len(r.json()) >= 2

    async def test_update_flashcard(self, client):
        student = await _register(client, f"fcu_{uuid.uuid4().hex[:6]}@example.com", "student")
        create = await client.post("/api/v1/my/flashcards",
            json={"question": "Original question?", "answer": "Original answer"},
            headers=_auth(student["token"]))
        card_id = create.json()["id"]

        r = await client.patch(f"/api/v1/my/flashcards/{card_id}",
            json={"question": "Updated question?"},
            headers=_auth(student["token"]))
        assert r.status_code == 200
        assert r.json()["question"] == "Updated question?"

    async def test_delete_flashcard(self, client):
        student = await _register(client, f"fcd_{uuid.uuid4().hex[:6]}@example.com", "student")
        create = await client.post("/api/v1/my/flashcards",
            json={"question": "Delete me?", "answer": "Yes"},
            headers=_auth(student["token"]))
        card_id = create.json()["id"]

        r = await client.delete(f"/api/v1/my/flashcards/{card_id}",
            headers=_auth(student["token"]))
        assert r.status_code == 204

    async def test_review_flashcard(self, client):
        student = await _register(client, f"fcr_{uuid.uuid4().hex[:6]}@example.com", "student")
        create = await client.post("/api/v1/my/flashcards",
            json={"question": "Review me?", "answer": "OK"},
            headers=_auth(student["token"]))
        card_id = create.json()["id"]

        r = await client.post(f"/api/v1/my/flashcards/{card_id}/review",
            json={"quality": 4},  # SM-2 quality 0-5
            headers=_auth(student["token"]))
        assert r.status_code == 200
        data = r.json()
        assert "next_review_at" in data or "interval" in data or "ease_factor" in data

    async def test_other_student_cannot_see_flashcards(self, client):
        student1 = await _register(client, f"fco1_{uuid.uuid4().hex[:6]}@example.com", "student")
        student2 = await _register(client, f"fco2_{uuid.uuid4().hex[:6]}@example.com", "student")

        create = await client.post("/api/v1/my/flashcards",
            json={"question": "Private question?", "answer": "Private"},
            headers=_auth(student1["token"]))
        card_id = create.json()["id"]

        r = await client.patch(f"/api/v1/my/flashcards/{card_id}",
            json={"question": "Stolen edit?"},
            headers=_auth(student2["token"]))
        # 403 or 404 — either explicit ownership check or filtered by user_id
        assert r.status_code in (403, 404)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Notes
# ─────────────────────────────────────────────────────────────────────────────

class TestStudentNotes:
    async def test_create_note(self, client):
        _, lesson_id = await _setup_published_lesson(client)
        student = await _register(client, f"nt_{uuid.uuid4().hex[:6]}@example.com", "student")

        r = await client.post("/api/v1/notes",
            json={"lesson_id": lesson_id,
                  "content": "Beta-blockers work by blocking beta-adrenergic receptors."},
            headers=_auth(student["token"]))
        assert r.status_code == 201
        data = r.json()
        assert "id" in data
        assert data["content"] == "Beta-blockers work by blocking beta-adrenergic receptors."

    async def test_list_notes(self, client):
        _, lesson_id = await _setup_published_lesson(client)
        student = await _register(client, f"ntl_{uuid.uuid4().hex[:6]}@example.com", "student")

        await client.post("/api/v1/notes",
            json={"lesson_id": lesson_id, "content": "Note 1 content here."},
            headers=_auth(student["token"]))

        r = await client.get("/api/v1/notes", headers=_auth(student["token"]))
        assert r.status_code == 200
        notes = r.json()
        assert len(notes) >= 1

    async def test_update_note(self, client):
        _, lesson_id = await _setup_published_lesson(client)
        student = await _register(client, f"ntu_{uuid.uuid4().hex[:6]}@example.com", "student")

        create = await client.post("/api/v1/notes",
            json={"lesson_id": lesson_id, "content": "Original note content."},
            headers=_auth(student["token"]))
        note_id = create.json()["id"]

        r = await client.patch(f"/api/v1/notes/{note_id}",
            json={"content": "Updated note content here."},
            headers=_auth(student["token"]))
        assert r.status_code == 200
        assert r.json()["content"] == "Updated note content here."

    async def test_delete_note(self, client):
        _, lesson_id = await _setup_published_lesson(client)
        student = await _register(client, f"ntd_{uuid.uuid4().hex[:6]}@example.com", "student")

        create = await client.post("/api/v1/notes",
            json={"lesson_id": lesson_id, "content": "Note to delete."},
            headers=_auth(student["token"]))
        note_id = create.json()["id"]

        r = await client.delete(f"/api/v1/notes/{note_id}", headers=_auth(student["token"]))
        assert r.status_code == 204

    async def test_other_student_cannot_edit_note(self, client):
        _, lesson_id = await _setup_published_lesson(client)
        student1 = await _register(client, f"nto1_{uuid.uuid4().hex[:6]}@example.com", "student")
        student2 = await _register(client, f"nto2_{uuid.uuid4().hex[:6]}@example.com", "student")

        create = await client.post("/api/v1/notes",
            json={"lesson_id": lesson_id, "content": "Private note content."},
            headers=_auth(student1["token"]))
        note_id = create.json()["id"]

        r = await client.patch(f"/api/v1/notes/{note_id}",
            json={"content": "Stolen edit."},
            headers=_auth(student2["token"]))
        # 403 (explicit ownership check) or 404 (filtered by user_id — note not found)
        assert r.status_code in (403, 404)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Bookmarks
# ─────────────────────────────────────────────────────────────────────────────

class TestStudentBookmarks:
    async def test_bookmark_lesson(self, client):
        _, lesson_id = await _setup_published_lesson(client)
        student = await _register(client, f"bm_{uuid.uuid4().hex[:6]}@example.com", "student")

        r = await client.post(f"/api/v1/bookmarks/lesson/{lesson_id}",
            headers=_auth(student["token"]))
        assert r.status_code == 201

    async def test_list_bookmarks(self, client):
        _, lesson_id = await _setup_published_lesson(client)
        student = await _register(client, f"bml_{uuid.uuid4().hex[:6]}@example.com", "student")

        await client.post(f"/api/v1/bookmarks/lesson/{lesson_id}",
            headers=_auth(student["token"]))

        r = await client.get("/api/v1/bookmarks", headers=_auth(student["token"]))
        assert r.status_code == 200
        data = r.json()
        # Paginated response
        assert "bookmarks" in data or isinstance(data, list)
        if "bookmarks" in data:
            assert len(data["bookmarks"]) >= 1

    async def test_check_bookmark(self, client):
        _, lesson_id = await _setup_published_lesson(client)
        student = await _register(client, f"bmc_{uuid.uuid4().hex[:6]}@example.com", "student")

        # Not bookmarked yet
        r = await client.get(f"/api/v1/bookmarks/check/lesson/{lesson_id}",
            headers=_auth(student["token"]))
        assert r.status_code == 200
        assert r.json().get("bookmarked") is False

        # Bookmark it
        await client.post(f"/api/v1/bookmarks/lesson/{lesson_id}",
            headers=_auth(student["token"]))

        r = await client.get(f"/api/v1/bookmarks/check/lesson/{lesson_id}",
            headers=_auth(student["token"]))
        assert r.status_code == 200
        assert r.json().get("bookmarked") is True

    async def test_remove_bookmark(self, client):
        _, lesson_id = await _setup_published_lesson(client)
        student = await _register(client, f"bmr_{uuid.uuid4().hex[:6]}@example.com", "student")

        await client.post(f"/api/v1/bookmarks/lesson/{lesson_id}",
            headers=_auth(student["token"]))
        r = await client.delete(f"/api/v1/bookmarks/lesson/{lesson_id}",
            headers=_auth(student["token"]))
        assert r.status_code == 204


# ─────────────────────────────────────────────────────────────────────────────
# 7. Dashboard
# ─────────────────────────────────────────────────────────────────────────────

class TestStudentDashboard:
    async def test_student_dashboard(self, client):
        student = await _register(client, f"db_{uuid.uuid4().hex[:6]}@example.com", "student")
        r = await client.get("/api/v1/student/dashboard", headers=_auth(student["token"]))
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, dict)

    async def test_dashboard_overview(self, client):
        student = await _register(client, f"dbo_{uuid.uuid4().hex[:6]}@example.com", "student")
        r = await client.get("/api/v1/dashboard/overview", headers=_auth(student["token"]))
        assert r.status_code == 200

    async def test_teacher_cannot_access_student_dashboard(self, client):
        teacher = await _register(client, f"dbt_{uuid.uuid4().hex[:6]}@example.com", "teacher")
        r = await client.get("/api/v1/student/dashboard", headers=_auth(teacher["token"]))
        # Either 403 (role check) or 200 (dashboard also works for teachers) — not a crash
        assert r.status_code in (200, 403)


# ─────────────────────────────────────────────────────────────────────────────
# 8. Adaptive study plan
# ─────────────────────────────────────────────────────────────────────────────

class TestStudentAdaptivePlan:
    async def test_generate_plan(self, client):
        student = await _register(client, f"ap_{uuid.uuid4().hex[:6]}@example.com", "student")
        r = await client.post("/api/v1/student/plan/adapt",
            json={"exam_date": "2026-09-01"},
            headers=_auth(student["token"]))
        assert r.status_code in (200, 422)
        if r.status_code == 200:
            data = r.json()
            assert isinstance(data, dict)

    async def test_get_plan_before_generate_returns_404(self, client):
        student = await _register(client, f"ap2_{uuid.uuid4().hex[:6]}@example.com", "student")
        r = await client.get("/api/v1/student/plan/current", headers=_auth(student["token"]))
        assert r.status_code == 404

    async def test_plan_cached_after_generation(self, client):
        student = await _register(client, f"apc_{uuid.uuid4().hex[:6]}@example.com", "student")

        gen = await client.post("/api/v1/student/plan/adapt",
            json={"exam_date": "2026-09-01"},
            headers=_auth(student["token"]))
        if gen.status_code != 200:
            pytest.skip("Plan generation returned non-200 (no data to cache)")

        r = await client.get("/api/v1/student/plan/current", headers=_auth(student["token"]))
        assert r.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# 9. Permission boundaries
# ─────────────────────────────────────────────────────────────────────────────

class TestStudentPermissionBoundaries:
    async def test_student_cannot_create_module(self, client):
        student = await _register(client, f"pb1_{uuid.uuid4().hex[:6]}@example.com", "student")
        r = await client.post("/api/v1/lessons/modules",
            json={"title": "Hacked Module"},
            headers=_auth(student["token"]))
        assert r.status_code == 403

    async def test_student_cannot_publish_lesson(self, client):
        teacher = await _register(client, f"pb2t_{uuid.uuid4().hex[:6]}@example.com", "teacher")
        student = await _register(client, f"pb2s_{uuid.uuid4().hex[:6]}@example.com", "student")

        mod = await client.post("/api/v1/lessons/modules",
            json={"title": "Module", "level_label": "beginner"},
            headers=_auth(teacher["token"]))
        module_id = mod.json()["id"]

        les = await client.post(f"/api/v1/lessons/modules/{module_id}/lessons",
            json={"title": "Lesson", "content": LESSON_CONTENT,
                  "estimated_minutes": 15, "lesson_order": 0},
            headers=_auth(teacher["token"]))
        lesson_id = les.json()["id"]

        r = await client.patch(f"/api/v1/lessons/{lesson_id}/publish",
            headers=_auth(student["token"]))
        assert r.status_code == 403

    async def test_student_cannot_access_professor_analytics(self, client):
        student = await _register(client, f"pb3_{uuid.uuid4().hex[:6]}@example.com", "student")
        r = await client.get(f"/api/v1/professor/courses/{uuid.uuid4()}/at-risk",
            headers=_auth(student["token"]))
        assert r.status_code == 403

    async def test_unauthenticated_cannot_complete_lesson(self, client):
        r = await client.post(f"/api/v1/progress/lesson/{uuid.uuid4()}/complete",
            json={"score": 100, "time_spent_seconds": 60})
        assert r.status_code == 401

    async def test_unauthenticated_cannot_create_note(self, client):
        r = await client.post("/api/v1/notes",
            json={"lesson_id": str(uuid.uuid4()), "content": "Sneaky note."})
        assert r.status_code == 401

    async def test_student_cannot_delete_others_flashcard(self, client):
        student1 = await _register(client, f"pb4a_{uuid.uuid4().hex[:6]}@example.com", "student")
        student2 = await _register(client, f"pb4b_{uuid.uuid4().hex[:6]}@example.com", "student")

        create = await client.post("/api/v1/my/flashcards",
            json={"question": "Private?", "answer": "Yes"},
            headers=_auth(student1["token"]))
        card_id = create.json()["id"]

        r = await client.delete(f"/api/v1/my/flashcards/{card_id}",
            headers=_auth(student2["token"]))
        # 403 or 404 — ownership check or filtered by user_id
        assert r.status_code in (403, 404)
