"""Tests for teacher lesson authoring endpoints."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

# ── helpers ──────────────────────────────────────────────────────────────────

_LESSON_CONTENT = {
    "title": "Introduction to Beta-Blockers",
    "blocks": [
        {"type": "text", "content": {"text": "Beta-blockers reduce heart rate."}, "order": 0},
        {"type": "quiz", "content": {"question": "What is the MOA?", "options": {"A": "Block alpha", "B": "Block beta"}, "correct": "B", "explanation": "Correct."}, "order": 1},
    ],
    "estimated_minutes": 20,
    "learning_objectives": ["Understand MOA of beta-blockers"],
}


async def _register_teacher(client: AsyncClient, email: str = "teacher@test.com") -> str:
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Teacher1234!",
        "first_name": "Prof",
        "last_name": "Smith",
        "role": "teacher",
        "consent_terms": True,
        "consent_data_processing": True,
    })
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "Teacher1234!"})
    return resp.json().get("access_token", "")


async def _register_student(client: AsyncClient, email: str = "student@test.com") -> str:
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Student1234!",
        "first_name": "Alice",
        "last_name": "Jones",
        "role": "student",
        "consent_terms": True,
        "consent_data_processing": True,
    })
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "Student1234!"})
    return resp.json().get("access_token", "")


async def _create_module(client: AsyncClient, token: str) -> str:
    resp = await client.post(
        "/api/v1/lessons/modules",
        json={"title": "Cardiology Basics", "level_label": "intermediate"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def _create_lesson(client: AsyncClient, token: str, module_id: str) -> str:
    resp = await client.post(
        f"/api/v1/lessons/modules/{module_id}/lessons",
        json={
            "title": "Beta-Blockers",
            "content": _LESSON_CONTENT,
            "estimated_minutes": 20,
            "lesson_order": 0,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# ── Module tests ──────────────────────────────────────────────────────────────

class TestModuleCreate:
    async def test_teacher_can_create_module(self, client):
        token = await _register_teacher(client, "tc_mod1@test.com")
        resp = await client.post(
            "/api/v1/lessons/modules",
            json={"title": "Neuro Basics", "level_label": "beginner"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Neuro Basics"
        assert data["is_published"] is False   # starts unpublished
        assert data["author_id"] is not None

    async def test_student_cannot_create_module(self, client):
        token = await _register_student(client, "st_mod1@test.com")
        resp = await client.post(
            "/api/v1/lessons/modules",
            json={"title": "Hack module"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_create_module(self, client):
        resp = await client.post("/api/v1/lessons/modules", json={"title": "No auth"})
        assert resp.status_code == 401

    async def test_module_publish_requires_published_lesson(self, client):
        token = await _register_teacher(client, "tc_mod2@test.com")
        module_id = await _create_module(client, token)

        # No published lessons yet → should fail
        resp = await client.patch(
            f"/api/v1/lessons/modules/{module_id}/publish",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

    async def test_module_publish_succeeds_after_lesson_published(self, client):
        token = await _register_teacher(client, "tc_mod3@test.com")
        module_id = await _create_module(client, token)
        lesson_id = await _create_lesson(client, token, module_id)

        # Publish the lesson first
        await client.patch(
            f"/api/v1/lessons/{lesson_id}/publish",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Now publish module
        resp = await client.patch(
            f"/api/v1/lessons/modules/{module_id}/publish",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["is_published"] is True


# ── Lesson CRUD tests ─────────────────────────────────────────────────────────

class TestLessonCRUD:
    async def test_teacher_creates_lesson_as_draft(self, client):
        token = await _register_teacher(client, "tc_les1@test.com")
        module_id = await _create_module(client, token)
        lesson_id = await _create_lesson(client, token, module_id)

        resp = await client.get(
            f"/api/v1/lessons/{lesson_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "draft"
        assert data["title"] == "Beta-Blockers"

    async def test_student_cannot_see_draft(self, client):
        teacher_token = await _register_teacher(client, "tc_les2@test.com")
        student_token = await _register_student(client, "st_les2@test.com")

        module_id = await _create_module(client, teacher_token)
        lesson_id = await _create_lesson(client, teacher_token, module_id)

        resp = await client.get(
            f"/api/v1/lessons/{lesson_id}",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 403

    async def test_update_lesson_content(self, client):
        token = await _register_teacher(client, "tc_les3@test.com")
        module_id = await _create_module(client, token)
        lesson_id = await _create_lesson(client, token, module_id)

        updated_content = {**_LESSON_CONTENT, "title": "Updated Title"}
        resp = await client.patch(
            f"/api/v1/lessons/{lesson_id}",
            json={"title": "Updated Title", "content": updated_content},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated Title"

    async def test_archive_lesson(self, client):
        token = await _register_teacher(client, "tc_les4@test.com")
        module_id = await _create_module(client, token)
        lesson_id = await _create_lesson(client, token, module_id)

        resp = await client.delete(
            f"/api/v1/lessons/{lesson_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 204

        # Verify archived — teacher can still see it via direct GET (it's their lesson)
        resp2 = await client.get(
            f"/api/v1/lessons/{lesson_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp2.status_code == 200
        assert resp2.json()["status"] == "archived"

    async def test_cannot_edit_archived_lesson(self, client):
        token = await _register_teacher(client, "tc_les5@test.com")
        module_id = await _create_module(client, token)
        lesson_id = await _create_lesson(client, token, module_id)

        # Archive it
        await client.delete(
            f"/api/v1/lessons/{lesson_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        # Try to edit
        resp = await client.patch(
            f"/api/v1/lessons/{lesson_id}",
            json={"title": "Should fail"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400

    async def test_other_teacher_cannot_edit_lesson(self, client):
        teacher1 = await _register_teacher(client, "tc_les6a@test.com")
        teacher2 = await _register_teacher(client, "tc_les6b@test.com")

        module_id = await _create_module(client, teacher1)
        lesson_id = await _create_lesson(client, teacher1, module_id)

        resp = await client.patch(
            f"/api/v1/lessons/{lesson_id}",
            json={"title": "Stolen edit"},
            headers={"Authorization": f"Bearer {teacher2}"},
        )
        assert resp.status_code == 403

    async def test_list_lessons_hides_drafts_from_student(self, client):
        teacher_token = await _register_teacher(client, "tc_les7@test.com")
        student_token = await _register_student(client, "st_les7@test.com")

        module_id = await _create_module(client, teacher_token)
        await _create_lesson(client, teacher_token, module_id)  # draft

        resp = await client.get(
            f"/api/v1/lessons/modules/{module_id}/lessons",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 200
        assert resp.json() == []  # draft hidden from students


# ── Workflow tests ────────────────────────────────────────────────────────────

class TestLessonWorkflow:
    async def test_submit_for_review(self, client):
        token = await _register_teacher(client, "tc_wf1@test.com")
        module_id = await _create_module(client, token)
        lesson_id = await _create_lesson(client, token, module_id)

        resp = await client.patch(
            f"/api/v1/lessons/{lesson_id}/submit-review",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "review"

    async def test_publish_lesson(self, client):
        token = await _register_teacher(client, "tc_wf2@test.com")
        module_id = await _create_module(client, token)
        lesson_id = await _create_lesson(client, token, module_id)

        resp = await client.patch(
            f"/api/v1/lessons/{lesson_id}/publish",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "published"
        assert data["published_at"] is not None

    async def test_published_lesson_visible_to_student(self, client):
        teacher_token = await _register_teacher(client, "tc_wf3@test.com")
        student_token = await _register_student(client, "st_wf3@test.com")

        module_id = await _create_module(client, teacher_token)
        lesson_id = await _create_lesson(client, teacher_token, module_id)

        await client.patch(
            f"/api/v1/lessons/{lesson_id}/publish",
            headers={"Authorization": f"Bearer {teacher_token}"},
        )

        resp = await client.get(
            f"/api/v1/lessons/{lesson_id}",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 200

    async def test_unpublish_returns_to_draft(self, client):
        token = await _register_teacher(client, "tc_wf4@test.com")
        module_id = await _create_module(client, token)
        lesson_id = await _create_lesson(client, token, module_id)

        await client.patch(f"/api/v1/lessons/{lesson_id}/publish",
                           headers={"Authorization": f"Bearer {token}"})
        resp = await client.patch(f"/api/v1/lessons/{lesson_id}/unpublish",
                                  headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "draft"

    async def test_submit_review_from_non_draft_fails(self, client):
        token = await _register_teacher(client, "tc_wf5@test.com")
        module_id = await _create_module(client, token)
        lesson_id = await _create_lesson(client, token, module_id)

        # Publish directly (allowed from draft too)
        await client.patch(f"/api/v1/lessons/{lesson_id}/publish",
                           headers={"Authorization": f"Bearer {token}"})
        # Try submit-review on published lesson
        resp = await client.patch(f"/api/v1/lessons/{lesson_id}/submit-review",
                                  headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 400


# ── Preview tests ─────────────────────────────────────────────────────────────

class TestLessonPreview:
    async def test_author_can_preview_draft(self, client):
        token = await _register_teacher(client, "tc_pv1@test.com")
        module_id = await _create_module(client, token)
        lesson_id = await _create_lesson(client, token, module_id)

        resp = await client.get(
            f"/api/v1/lessons/{lesson_id}/preview",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    async def test_student_cannot_preview_draft(self, client):
        teacher_token = await _register_teacher(client, "tc_pv2@test.com")
        student_token = await _register_student(client, "st_pv2@test.com")

        module_id = await _create_module(client, teacher_token)
        lesson_id = await _create_lesson(client, teacher_token, module_id)

        resp = await client.get(
            f"/api/v1/lessons/{lesson_id}/preview",
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 403


# ── AI improve tests ──────────────────────────────────────────────────────────

class TestAIImprove:
    async def test_ai_improve_returns_suggestion(self, client):
        token = await _register_teacher(client, "tc_ai1@test.com")
        module_id = await _create_module(client, token)
        lesson_id = await _create_lesson(client, token, module_id)

        fake_response = MagicMock()
        fake_response.content = [MagicMock(text='{"title": "Improved", "blocks": [], "estimated_minutes": 20, "learning_objectives": ["Updated"]}')]

        with patch("app.api.v1.routes.lessons._claude") as mock_claude:
            mock_claude.messages.create = AsyncMock(return_value=fake_response)
            resp = await client.post(
                f"/api/v1/lessons/{lesson_id}/ai-improve",
                json={"task": "improve_clarity", "specialty": "Cardiology", "target_level": "intermediate"},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert "suggested" in data
        assert "original" in data
        assert data["task"] == "improve_clarity"

    async def test_student_cannot_ai_improve(self, client):
        teacher_token = await _register_teacher(client, "tc_ai2@test.com")
        student_token = await _register_student(client, "st_ai2@test.com")

        module_id = await _create_module(client, teacher_token)
        lesson_id = await _create_lesson(client, teacher_token, module_id)

        resp = await client.post(
            f"/api/v1/lessons/{lesson_id}/ai-improve",
            json={"task": "improve_clarity", "specialty": "Cardiology"},
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert resp.status_code == 403

    async def test_other_teacher_cannot_ai_improve(self, client):
        teacher1 = await _register_teacher(client, "tc_ai3a@test.com")
        teacher2 = await _register_teacher(client, "tc_ai3b@test.com")

        module_id = await _create_module(client, teacher1)
        lesson_id = await _create_lesson(client, teacher1, module_id)

        resp = await client.post(
            f"/api/v1/lessons/{lesson_id}/ai-improve",
            json={"task": "improve_clarity", "specialty": "Cardiology"},
            headers={"Authorization": f"Bearer {teacher2}"},
        )
        assert resp.status_code == 403
