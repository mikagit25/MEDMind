"""Phase 10: AI MCQ generation from lesson tests."""
import pytest
import uuid as _uuid
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str, role: str = "teacher") -> str:
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Str0ng!Pass99",
        "first_name": "Quiz",
        "last_name": "Tester",
        "role": role,
        "consent_terms": True,
        "consent_data_processing": True,
    })
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": "Str0ng!Pass99"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


LESSON_CONTENT = {
    "title": "Cardiac Tamponade",
    "blocks": [
        {"type": "text", "order": 0, "content": {
            "text": (
                "Cardiac tamponade is a life-threatening emergency where fluid accumulates in the "
                "pericardial space, compressing the heart and reducing cardiac output. "
                "Beck's triad: hypotension, muffled heart sounds, JVD. "
                "Electrical alternans on ECG is classic. Treatment: pericardiocentesis."
            )
        }},
    ],
    "estimated_minutes": 15,
    "species_applicability": ["human"],
    "clinical_risk_level": "high",
}

FAKE_QUESTIONS_JSON = """{
  "questions": [
    {
      "question": "Which mechanism best describes cardiac tamponade?",
      "options": {
        "A": "Increased preload",
        "B": "Pericardial fluid compressing the heart",
        "C": "Ventricular hypertrophy",
        "D": "Aortic valve stenosis"
      },
      "correct": "B",
      "explanation": "Cardiac tamponade occurs when fluid accumulates in the pericardial space, compressing the heart chambers."
    },
    {
      "question": "What is the first-line investigation for suspected cardiac tamponade?",
      "options": {"A": "CT chest", "B": "Echocardiography", "C": "ECG only", "D": "Chest X-ray"},
      "correct": "B",
      "explanation": "Echocardiography is the gold standard for cardiac tamponade."
    },
    {
      "question": "Beck's triad includes hypotension, muffled heart sounds, and?",
      "options": {"A": "Hypertension", "B": "JVD", "C": "Pulmonary oedema", "D": "Bradycardia"},
      "correct": "B",
      "explanation": "Beck's triad: hypotension, muffled heart sounds, and jugular venous distension."
    },
    {
      "question": "Pericardiocentesis is indicated when?",
      "options": {"A": "Pericarditis only", "B": "Haemodynamically significant tamponade", "C": "Stable effusion", "D": "Viral pericarditis"},
      "correct": "B",
      "explanation": "Pericardiocentesis is performed when tamponade causes haemodynamic compromise."
    },
    {
      "question": "Electrical alternans on ECG is characteristic of?",
      "options": {"A": "Myocardial infarction", "B": "Cardiac tamponade", "C": "Aortic dissection", "D": "Pulmonary embolism"},
      "correct": "B",
      "explanation": "Electrical alternans is a classic ECG finding in cardiac tamponade."
    }
  ]
}"""


async def _make_lesson(client: AsyncClient, token: str) -> str:
    """Create module + lesson as teacher, return published lesson_id."""
    mod = await client.post(
        "/api/v1/lessons/modules",
        json={"title": "MCQ Test Module", "level_label": "intermediate"},
        headers=_h(token),
    )
    assert mod.status_code == 201, f"Module creation failed: {mod.text}"
    module_id = mod.json()["id"]

    les = await client.post(
        f"/api/v1/lessons/modules/{module_id}/lessons",
        json={
            "title": "Cardiac Tamponade",
            "content": LESSON_CONTENT,
            "estimated_minutes": 15,
            "lesson_order": 0,
            "clinical_risk_level": "high",
            "species_applicability": ["human"],
        },
        headers=_h(token),
    )
    assert les.status_code == 201, f"Lesson creation failed: {les.text}"
    lesson_id = les.json()["id"]

    # Publish so students can access it
    await client.patch(f"/api/v1/lessons/{lesson_id}/publish", headers=_h(token))
    return lesson_id


# ── 401 without auth ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_quiz_requires_auth(client: AsyncClient):
    """Endpoint returns 401 without JWT."""
    fake_id = str(_uuid.uuid4())
    resp = await client.post(f"/api/v1/ai/lessons/{fake_id}/generate-quiz")
    assert resp.status_code == 401


# ── 404 for unknown lesson ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_quiz_unknown_lesson(client: AsyncClient):
    """Returns 404 for a lesson that doesn't exist."""
    token = await _register_and_login(client, "quiz_404@test.medmind")
    fake_id = str(_uuid.uuid4())
    with patch("app.services.ai_router.call_ollama_structured", new=AsyncMock(return_value=(FAKE_QUESTIONS_JSON, "claude-haiku-4-5-20251001"))):
        resp = await client.post(f"/api/v1/ai/lessons/{fake_id}/generate-quiz", headers=_h(token))
    assert resp.status_code == 404


# ── Happy path ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_quiz_returns_questions(client: AsyncClient):
    """Authenticated request with valid lesson returns 5 questions."""
    token = await _register_and_login(client, "quiz_happy@test.medmind")
    lesson_id = await _make_lesson(client, token)

    with patch("app.services.ai_router.call_ollama_structured", new=AsyncMock(return_value=(FAKE_QUESTIONS_JSON, "claude-haiku-4-5-20251001"))):
        resp = await client.post(
            f"/api/v1/ai/lessons/{lesson_id}/generate-quiz",
            headers=_h(token),
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["lesson_id"] == lesson_id
    assert len(data["questions"]) == 5


@pytest.mark.asyncio
async def test_generate_quiz_question_structure(client: AsyncClient):
    """Each question has question, options (A-D), correct, explanation fields."""
    token = await _register_and_login(client, "quiz_struct@test.medmind")
    lesson_id = await _make_lesson(client, token)

    with patch("app.services.ai_router.call_ollama_structured", new=AsyncMock(return_value=(FAKE_QUESTIONS_JSON, "claude-haiku-4-5-20251001"))):
        resp = await client.post(
            f"/api/v1/ai/lessons/{lesson_id}/generate-quiz",
            headers=_h(token),
        )

    assert resp.status_code == 200
    for q in resp.json()["questions"]:
        assert "question" in q
        assert "options" in q
        assert "correct" in q
        assert "explanation" in q
        assert q["correct"] in q["options"]
        assert len(q["options"]) >= 2


@pytest.mark.asyncio
async def test_generate_quiz_difficulty_param(client: AsyncClient):
    """Difficulty parameter is accepted (easy/medium/hard)."""
    token = await _register_and_login(client, "quiz_diff@test.medmind")
    lesson_id = await _make_lesson(client, token)

    for diff in ("easy", "medium", "hard"):
        with patch("app.services.ai_router.call_ollama_structured", new=AsyncMock(return_value=(FAKE_QUESTIONS_JSON, "claude-haiku-4-5-20251001"))):
            resp = await client.post(
                f"/api/v1/ai/lessons/{lesson_id}/generate-quiz?difficulty={diff}",
                headers=_h(token),
            )
        assert resp.status_code == 200, f"Failed for difficulty={diff}: {resp.text}"


@pytest.mark.asyncio
async def test_generate_quiz_invalid_uuid(client: AsyncClient):
    """Invalid lesson UUID returns 422."""
    token = await _register_and_login(client, "quiz_uuid@test.medmind")
    resp = await client.post("/api/v1/ai/lessons/not-a-uuid/generate-quiz", headers=_h(token))
    assert resp.status_code == 422
