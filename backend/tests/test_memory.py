"""Tests for the long-term student memory system."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select

from app.models.models import StudentMemory, MemoryRelation
from app.services.memory_service import (
    _make_search_tokens,
    _parse_llm_json,
    _importance,
    format_memory_context,
    retrieve_relevant_memories,
    extract_and_save_memories,
)

pytestmark = pytest.mark.asyncio


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests — pure functions (no DB required)
# ─────────────────────────────────────────────────────────────────────────────

class TestSearchTokens:
    def test_basic(self):
        tokens = _make_search_tokens("Atrial fibrillation management guidelines")
        assert "atrial" in tokens
        assert "fibrillation" in tokens
        assert "management" in tokens

    def test_tags_included(self):
        tokens = _make_search_tokens("Beta blockers", ["cardiology", "arrhythmia"])
        assert "cardiology" in tokens
        assert "arrhythmia" in tokens

    def test_deduplication(self):
        tokens = _make_search_tokens("beta beta beta blockers")
        parts = tokens.split()
        assert parts.count("beta") == 1

    def test_short_words_filtered(self):
        tokens = _make_search_tokens("is a the beta blockers")
        assert "is" not in tokens
        assert "the" not in tokens

    def test_cyrillic(self):
        tokens = _make_search_tokens("Мерцательная аритмия")
        assert "мерцательная" in tokens


class TestParseLlmJson:
    def test_plain_array(self):
        result = _parse_llm_json('[{"type":"fact","content":"test"}]')
        assert len(result) == 1
        assert result[0]["type"] == "fact"

    def test_markdown_fenced(self):
        result = _parse_llm_json('```json\n[{"type":"fact","content":"ok"}]\n```')
        assert len(result) == 1

    def test_embedded_in_text(self):
        result = _parse_llm_json('Here are facts:\n[{"type":"fact","content":"embedded"}]')
        assert len(result) == 1

    def test_empty_array(self):
        assert _parse_llm_json("[]") == []

    def test_invalid_returns_empty(self):
        assert _parse_llm_json("not json at all") == []

    def test_object_instead_of_array(self):
        # LLM sometimes returns a dict — should return []
        assert _parse_llm_json('{"type":"fact"}') == []


class TestImportanceScore:
    def test_misconception_boosted(self):
        score = _importance({"type": "misconception", "competency_level": "intermediate", "confidence": 0.4})
        assert score > 0.7

    def test_case_experience_boosted(self):
        score = _importance({"type": "case_experience", "competency_level": "beginner", "confidence": 0.8})
        assert score > 0.6

    def test_advanced_boosted(self):
        score_adv = _importance({"type": "fact", "competency_level": "advanced", "confidence": 0.9})
        score_beg = _importance({"type": "fact", "competency_level": "beginner", "confidence": 0.9})
        assert score_adv > score_beg

    def test_low_confidence_penalised(self):
        score_high = _importance({"type": "fact", "competency_level": "beginner", "confidence": 0.9})
        score_low = _importance({"type": "fact", "competency_level": "beginner", "confidence": 0.3})
        assert score_high > score_low

    def test_clamped_to_1(self):
        score = _importance({"type": "misconception", "competency_level": "advanced", "confidence": 0.9})
        assert score <= 1.0


class TestFormatMemoryContext:
    def _make_mem(self, mtype: str, content: str, level: str = "intermediate") -> StudentMemory:
        m = MagicMock(spec=StudentMemory)
        m.memory_type = mtype
        m.content = content
        m.competency_level = level
        return m

    def test_empty_list_returns_empty_string(self):
        assert format_memory_context([]) == ""

    def test_contains_content(self):
        mems = [self._make_mem("fact", "Beta-blockers reduce HR")]
        ctx = format_memory_context(mems)
        assert "Beta-blockers reduce HR" in ctx

    def test_misconception_prefix(self):
        mems = [self._make_mem("misconception", "Student thought aspirin is safe in dengue")]
        ctx = format_memory_context(mems)
        assert "misconception" in ctx.lower() or "⚠️" in ctx

    def test_multiple_memories(self):
        mems = [
            self._make_mem("fact", "Fact one"),
            self._make_mem("case_experience", "Case two"),
        ]
        ctx = format_memory_context(mems)
        assert "Fact one" in ctx
        assert "Case two" in ctx

    def test_includes_instruction(self):
        mems = [self._make_mem("fact", "something")]
        ctx = format_memory_context(mems)
        assert "Prior Knowledge" in ctx or "prior" in ctx.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Integration tests — require DB session (from conftest)
# ─────────────────────────────────────────────────────────────────────────────

async def _register_and_login(client: AsyncClient, email: str = "memtest@example.com") -> str:
    """Helper: register user and return access token."""
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Memory1234!",
        "first_name": "Memory",
        "last_name": "Tester",
        "role": "student",
        "consent_terms": True,
        "consent_data_processing": True,
    })
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": "Memory1234!"})
    return resp.json().get("access_token", "")


class TestMemoryRetrieval:
    """Tests for retrieve_relevant_memories with real DB."""

    async def test_empty_returns_empty(self, db_session):
        result = await retrieve_relevant_memories(
            db=db_session,
            user_id=uuid.uuid4(),
            query="anything",
        )
        assert result == []

    async def test_deprecated_excluded(self, db_session):
        uid = uuid.uuid4()
        mem = StudentMemory(
            id=uuid.uuid4(),
            user_id=uid,
            memory_type="fact",
            content="Deprecated fact about aspirin",
            search_tokens="deprecated fact aspirin",
            confidence=0.9,
            deprecated=True,
            importance_score=0.8,
        )
        db_session.add(mem)
        await db_session.commit()

        result = await retrieve_relevant_memories(db=db_session, user_id=uid, query="aspirin")
        assert all(not m.deprecated for m in result)

    async def test_low_confidence_excluded(self, db_session):
        uid = uuid.uuid4()
        mem = StudentMemory(
            id=uuid.uuid4(),
            user_id=uid,
            memory_type="fact",
            content="Uncertain fact about digoxin",
            search_tokens="uncertain fact digoxin",
            confidence=0.3,  # below MIN_CONFIDENCE=0.6
            deprecated=False,
            importance_score=0.5,
        )
        db_session.add(mem)
        await db_session.commit()

        result = await retrieve_relevant_memories(db=db_session, user_id=uid, query="digoxin")
        assert len(result) == 0

    async def test_relevant_memory_returned(self, db_session):
        uid = uuid.uuid4()
        mem = StudentMemory(
            id=uuid.uuid4(),
            user_id=uid,
            memory_type="fact",
            content="Warfarin requires INR monitoring",
            search_tokens="warfarin requires inr monitoring anticoagulation",
            specialty="Cardiology",
            confidence=0.9,
            deprecated=False,
            importance_score=0.7,
        )
        db_session.add(mem)
        await db_session.commit()

        result = await retrieve_relevant_memories(
            db=db_session,
            user_id=uid,
            query="warfarin INR dosing",
            specialty="Cardiology",
        )
        assert any(m.content == "Warfarin requires INR monitoring" for m in result)

    async def test_access_count_incremented(self, db_session):
        uid = uuid.uuid4()
        mem = StudentMemory(
            id=uuid.uuid4(),
            user_id=uid,
            memory_type="fact",
            content="Metformin first-line for type 2 diabetes",
            search_tokens="metformin first line type diabetes",
            confidence=0.9,
            deprecated=False,
            importance_score=0.6,
        )
        db_session.add(mem)
        await db_session.commit()
        initial_count = mem.access_count

        await retrieve_relevant_memories(db=db_session, user_id=uid, query="metformin diabetes")
        await db_session.refresh(mem)
        assert mem.access_count == initial_count + 1


class TestExtractAndSave:
    """Tests for extract_and_save_memories with mocked Claude."""

    async def test_saves_extracted_facts(self, db_session):
        uid = uuid.uuid4()
        conv_id = uuid.uuid4()

        fake_response = MagicMock()
        fake_response.content = [MagicMock(text=json.dumps([
            {
                "type": "fact",
                "content": "Furosemide is a loop diuretic",
                "competency_level": "beginner",
                "confidence": 0.9,
                "species_context": "human",
                "tags": ["diuretics", "cardiology"],
            }
        ]))]

        with patch("app.services.memory_service._claude") as mock_claude:
            mock_claude.messages.create = AsyncMock(return_value=fake_response)
            memories = await extract_and_save_memories(
                db=db_session,
                user_id=uid,
                message="What is furosemide?",
                ai_reply="Furosemide is a loop diuretic used in heart failure.",
                specialty="Cardiology",
                conversation_id=conv_id,
            )

        assert len(memories) == 1
        assert "Furosemide" in memories[0].content
        assert memories[0].memory_type == "fact"
        assert memories[0].confidence == 0.9

        # Verify persisted
        saved = (await db_session.execute(
            select(StudentMemory).where(StudentMemory.user_id == uid)
        )).scalars().all()
        assert len(saved) == 1

    async def test_empty_llm_response_saves_nothing(self, db_session):
        uid = uuid.uuid4()
        fake_response = MagicMock()
        fake_response.content = [MagicMock(text="[]")]

        with patch("app.services.memory_service._claude") as mock_claude:
            mock_claude.messages.create = AsyncMock(return_value=fake_response)
            memories = await extract_and_save_memories(
                db=db_session,
                user_id=uid,
                message="Hello",
                ai_reply="Hello back",
                specialty="General",
                conversation_id=uuid.uuid4(),
            )

        assert memories == []

    async def test_claude_error_does_not_raise(self, db_session):
        uid = uuid.uuid4()
        with patch("app.services.memory_service._claude") as mock_claude:
            mock_claude.messages.create = AsyncMock(side_effect=Exception("API down"))
            # Should NOT raise
            memories = await extract_and_save_memories(
                db=db_session,
                user_id=uid,
                message="Question",
                ai_reply="Answer",
                specialty="Cardiology",
                conversation_id=uuid.uuid4(),
            )
        assert memories == []

    async def test_misconception_gets_high_importance(self, db_session):
        uid = uuid.uuid4()
        fake_response = MagicMock()
        fake_response.content = [MagicMock(text=json.dumps([
            {
                "type": "misconception",
                "content": "Student thought aspirin is safe in children with fever",
                "competency_level": "beginner",
                "confidence": 0.3,
                "species_context": "human",
                "tags": [],
            }
        ]))]

        with patch("app.services.memory_service._claude") as mock_claude:
            mock_claude.messages.create = AsyncMock(return_value=fake_response)
            memories = await extract_and_save_memories(
                db=db_session,
                user_id=uid,
                message="Aspirin ok for kids?",
                ai_reply="No, Reye's syndrome risk.",
                specialty="Pediatrics",
                conversation_id=uuid.uuid4(),
            )

        assert len(memories) == 1
        assert memories[0].memory_type == "misconception"
        assert memories[0].importance_score > 0.6


class TestMemoryAPI:
    """HTTP endpoint tests for /memory."""

    async def test_list_memories_empty(self, client):
        token = await _register_and_login(client, "memapi1@example.com")
        resp = await client.get("/api/v1/memory/", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_stats_empty(self, client):
        token = await _register_and_login(client, "memapi2@example.com")
        resp = await client.get("/api/v1/memory/stats", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["by_type"] == {}

    async def test_delete_nonexistent_returns_404(self, client):
        token = await _register_and_login(client, "memapi3@example.com")
        fake_id = str(uuid.uuid4())
        resp = await client.delete(
            f"/api/v1/memory/{fake_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    async def test_unauthenticated_returns_401(self, client):
        resp = await client.get("/api/v1/memory/")
        assert resp.status_code == 401

    async def test_verify_requires_professor_role(self, client):
        token = await _register_and_login(client, "memapi4@example.com")
        fake_id = str(uuid.uuid4())
        resp = await client.patch(
            f"/api/v1/memory/{fake_id}/verify",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403
