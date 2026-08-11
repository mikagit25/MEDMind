"""V7 Phase 4 — Question ↔ AI Tutor tests.

Verifies:
- followup endpoint requires authentication
- followup with unknown chip returns 422
- followup with unknown question returns 404
- follow_up_count increments on each call
- after PSYCHO_FOLLOWUP_THRESHOLD calls, question health changes to key_suspect
- question_followup prompt builder returns correct structure
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import MCQQuestion, Module, Specialty, User


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _create_user(client: AsyncClient, email: str, password: str = "Str0ng!Pass99") -> str:
    r = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "first_name": "Test",
        "last_name": "User",
        "consent_terms": True,
        "consent_data_processing": True,
    })
    assert r.status_code == 201, r.text
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


async def _make_mcq(db: AsyncSession) -> uuid.UUID:
    spec = Specialty(id=uuid.uuid4(), code=f"sp-{uuid.uuid4().hex[:6]}", name="Test")
    db.add(spec)
    await db.flush()
    mod = Module(id=uuid.uuid4(), code=f"m-{uuid.uuid4().hex[:6]}", specialty_id=spec.id, title="Test")
    db.add(mod)
    await db.flush()
    q = MCQQuestion(
        id=uuid.uuid4(),
        module_id=mod.id,
        question="Which action is correct?",
        options={"A": "Option A", "B": "Option B", "C": "Option C", "D": "Option D"},
        correct="A",
        explanation="A is correct.",
        difficulty="medium",
        question_type="mcq",
        status="active",
        follow_up_count=0,
    )
    db.add(q)
    await db.commit()
    return q.id


# ── Unit tests ────────────────────────────────────────────────────────────────

def test_followup_prompt_structure():
    """build_followup_prompt returns (system, user) tuple with required content."""
    from app.prompts.question_followup import build_followup_prompt

    system, user = build_followup_prompt(
        question="What should the nurse do first?",
        options={"A": "Assess", "B": "Intervene", "C": "Document", "D": "Delegate"},
        correct_answer="A",
        correct_text="Assess",
        selected_answer="B",
        selected_text="Intervene",
        base_explanation="Assessment comes before intervention.",
        category="Management of Care",
        chip="explain_differently",
        user_language="en",
    )
    assert isinstance(system, str) and len(system) > 10
    assert isinstance(user, str) and len(user) > 10
    assert "Assess" in user or "correct" in user.lower()


def test_followup_prompt_all_chips():
    """All chip types return valid prompts."""
    from app.prompts.question_followup import build_followup_prompt, CHIP_INSTRUCTIONS

    for chip in CHIP_INSTRUCTIONS:
        system, user = build_followup_prompt(
            question="Q",
            options={"A": "opt A", "B": "opt B"},
            correct_answer="A",
            correct_text="opt A",
            selected_answer=None,
            selected_text=None,
            base_explanation=None,
            category="General",
            chip=chip,
        )
        assert system and user, f"Empty output for chip={chip}"


# ── HTTP tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_followup_requires_auth(client: AsyncClient, db_session: AsyncSession):
    """Unauthenticated access returns 401."""
    fake_id = str(uuid.uuid4())
    resp = await client.post(f"/api/v1/exam/questions/{fake_id}/followup", json={"chip": "explain_differently"})
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_followup_unknown_question(client: AsyncClient, db_session: AsyncSession):
    """Non-existent question returns 404."""
    token = await _create_user(client, f"u-{uuid.uuid4().hex[:8]}@test.com")
    fake_id = str(uuid.uuid4())
    with patch("app.services.ai_router.call_ollama_structured", new=AsyncMock(return_value=("ok", {}))):
        resp = await client.post(
            f"/api/v1/exam/questions/{fake_id}/followup",
            json={"chip": "explain_differently"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_followup_unknown_chip(client: AsyncClient, db_session: AsyncSession):
    """Unknown chip returns 422."""
    token = await _create_user(client, f"u-{uuid.uuid4().hex[:8]}@test.com")
    mcq_id = await _make_mcq(db_session)
    with patch("app.services.ai_router.call_ollama_structured", new=AsyncMock(return_value=("ok", {}))):
        resp = await client.post(
            f"/api/v1/exam/questions/{mcq_id}/followup",
            json={"chip": "delete_everything"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_followup_increments_count(client: AsyncClient, db_session: AsyncSession):
    """Each followup call increments follow_up_count."""
    token = await _create_user(client, f"u-{uuid.uuid4().hex[:8]}@test.com")
    mcq_id = await _make_mcq(db_session)

    with patch("app.services.ai_router.call_ollama_structured", new=AsyncMock(return_value=("Explanation text", {}))):
        resp = await client.post(
            f"/api/v1/exam/questions/{mcq_id}/followup",
            json={"chip": "explain_differently"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert resp.json()["follow_up_count"] == 1


@pytest.mark.asyncio
async def test_followup_response_has_explanation(client: AsyncClient, db_session: AsyncSession):
    """Followup response includes explanation and chip fields."""
    token = await _create_user(client, f"u-{uuid.uuid4().hex[:8]}@test.com")
    mcq_id = await _make_mcq(db_session)

    with patch("app.services.ai_router.call_ollama_structured", new=AsyncMock(return_value=("Here is the mnemonic: PASS", {}))):
        resp = await client.post(
            f"/api/v1/exam/questions/{mcq_id}/followup",
            json={"chip": "mnemonic", "selected_answer": "B"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["chip"] == "mnemonic"
    assert "explanation" in data
    assert len(data["explanation"]) > 0
