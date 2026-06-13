"""Phase 16: Save AI Response as Flashcard — backend tests.

The feature adds a save-as-flashcard button to the AI tutor frontend.
Backend: POST /my/flashcards already existed; tests confirm it works
correctly for this use case (AI-generated Q&A content, long answer text).
"""
import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str) -> str:
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Str0ng!Pass99",
        "first_name": "Phase16",
        "last_name": "Tester",
        "consent_terms": True,
        "consent_data_processing": True,
    })
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": "Str0ng!Pass99"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Auth guard ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_flashcard_requires_auth(client: AsyncClient):
    """POST /my/flashcards returns 401 without JWT."""
    resp = await client.post(
        "/api/v1/my/flashcards",
        json={"question": "What is the mechanism of metformin?", "answer": "It reduces hepatic glucose output.", "difficulty": "medium"},
    )
    assert resp.status_code == 401


# ── Happy path: save AI response as flashcard ─────────────────────────────────

@pytest.mark.asyncio
async def test_save_ai_response_as_flashcard(client: AsyncClient):
    """Authenticated user can save an AI Q&A pair as a personal flashcard."""
    token = await _register_and_login(client, "phase16_save@test.medmind")
    resp = await client.post(
        "/api/v1/my/flashcards",
        json={
            "question": "Explain the pathophysiology of heart failure with reduced ejection fraction",
            "answer": "HFrEF results from impaired systolic function — the left ventricle cannot contract effectively, reducing stroke volume and cardiac output. Neurohormonal activation (RAAS, sympathetic) initially compensates but leads to maladaptive remodeling over time.",
            "difficulty": "hard",
        },
        headers=_h(token),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "id" in data
    assert data["question"] == "Explain the pathophysiology of heart failure with reduced ejection fraction"
    assert data["difficulty"] == "hard"


@pytest.mark.asyncio
async def test_save_flashcard_with_tags(client: AsyncClient):
    """Flashcard created with tags returns those tags."""
    token = await _register_and_login(client, "phase16_tags@test.medmind")
    resp = await client.post(
        "/api/v1/my/flashcards",
        json={
            "question": "What is the first-line treatment for type 2 diabetes?",
            "answer": "Metformin, combined with lifestyle modification.",
            "difficulty": "easy",
            "tags": ["endocrinology", "diabetes", "pharmacology"],
        },
        headers=_h(token),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert set(data["tags"]) == {"endocrinology", "diabetes", "pharmacology"}


@pytest.mark.asyncio
async def test_save_flashcard_appears_in_list(client: AsyncClient):
    """Saved flashcard appears in GET /my/flashcards list."""
    token = await _register_and_login(client, "phase16_list@test.medmind")
    question = "What are the signs of meningitis?"
    await client.post(
        "/api/v1/my/flashcards",
        json={"question": question, "answer": "Neck stiffness, photophobia, fever, headache, Kernig/Brudzinski signs.", "difficulty": "medium"},
        headers=_h(token),
    )
    list_resp = await client.get("/api/v1/my/flashcards", headers=_h(token))
    assert list_resp.status_code == 200
    cards = list_resp.json()["items"]
    assert any(c["question"] == question for c in cards)


@pytest.mark.asyncio
async def test_save_flashcard_invalid_difficulty_rejected(client: AsyncClient):
    """Flashcard with invalid difficulty value returns 422."""
    token = await _register_and_login(client, "phase16_diff@test.medmind")
    resp = await client.post(
        "/api/v1/my/flashcards",
        json={"question": "Q?", "answer": "A.", "difficulty": "super_hard"},
        headers=_h(token),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_save_flashcard_too_short_question_rejected(client: AsyncClient):
    """Question shorter than 3 chars is rejected."""
    token = await _register_and_login(client, "phase16_short@test.medmind")
    resp = await client.post(
        "/api/v1/my/flashcards",
        json={"question": "Q", "answer": "Answer here.", "difficulty": "easy"},
        headers=_h(token),
    )
    assert resp.status_code == 422
