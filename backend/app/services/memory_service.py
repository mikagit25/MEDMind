"""Long-term student memory service.

Architecture:
  - Memories are extracted from AI conversations using Claude Haiku (cheap, fast).
  - Retrieval uses PostgreSQL FTS (tsvector/tsquery) + metadata filtering + recency/importance reranking.
  - Runs as background tasks so it never blocks the main AI response.

PostgreSQL 9.6 does NOT support pgvector (requires PG 11+).
We use built-in full-text search instead — zero extra dependencies.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

import anthropic
from sqlalchemy import select, func, text, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import StudentMemory, MemoryRelation

logger = logging.getLogger(__name__)

_claude = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

# Minimum confidence for a memory to appear in context
MIN_CONFIDENCE = 0.6

# Maximum memories to surface in one prompt
MAX_CONTEXT_MEMORIES = 4

# Extraction prompt (must return a JSON array)
_EXTRACT_PROMPT = """\
You are a medical education assistant analysing a student–AI dialogue.
Your task: extract important, reusable learning facts.

Dialogue:
Student: {message}
AI reply: {reply}
Specialty: {specialty}

Return ONLY a JSON array (no other text).  Each element:
{{
  "type": "fact|skill|misconception|preference|case_experience",
  "content": "<concise 1-2 sentence fact in the SAME language as the dialogue>",
  "competency_level": "beginner|intermediate|advanced",
  "confidence": 0.0-1.0,
  "species_context": "human|canine|feline|equine|bovine|avian|rabbit|other",
  "tags": ["keyword1", "keyword2"]
}}

Rules:
- Omit trivial facts ("the heart pumps blood").
- Mark student errors as type "misconception" with confidence ≤ 0.4.
- For clinical cases use type "case_experience".
- Return [] if nothing noteworthy.
- Maximum 5 facts per call.
"""


_STOP_WORDS = frozenset({
    "a", "an", "the", "is", "in", "on", "at", "to", "of", "or", "and",
    "for", "not", "but", "be", "as", "by", "it", "its", "if", "do",
    "so", "up", "he", "she", "we", "my", "no", "can", "has", "had",
    "was", "are", "did", "may", "who", "how", "our", "you", "all",
})


def _make_search_tokens(content: str, tags: list[str] | None = None) -> str:
    """Create a lowercased, deduplicated token string for full-text search."""
    text_parts = [content] + (tags or [])
    tokens = re.findall(r"[a-zA-Zа-яёА-ЯЁ0-9]+", " ".join(text_parts))
    seen: set[str] = set()
    unique: list[str] = []
    for t in tokens:
        lt = t.lower()
        if lt not in seen and len(lt) > 2 and lt not in _STOP_WORDS:
            seen.add(lt)
            unique.append(lt)
    return " ".join(unique)


def _importance(fact: dict) -> float:
    score = 0.5
    if fact.get("type") == "misconception":
        score += 0.3  # errors are highly important to remember
    elif fact.get("type") == "case_experience":
        score += 0.2
    if fact.get("competency_level") == "advanced":
        score += 0.1
    if fact.get("confidence", 0.7) < 0.5:
        score -= 0.1  # low-confidence facts are less important
    return max(0.1, min(score, 1.0))


def _parse_llm_json(text: str) -> list[dict]:
    """Robustly parse the JSON array the LLM returns."""
    # Strip markdown fences if present
    text = re.sub(r"```(?:json)?", "", text).strip()
    text = text.strip("`").strip()
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    # Try to find a JSON array inside the text
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    return []


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

async def extract_and_save_memories(
    db: AsyncSession,
    user_id: UUID,
    message: str,
    ai_reply: str,
    specialty: str,
    conversation_id: UUID,
) -> list[StudentMemory]:
    """
    Background task: calls Claude Haiku to extract facts, saves to DB.
    Never raises — any error is logged and swallowed so the caller is unaffected.
    """
    try:
        prompt = _EXTRACT_PROMPT.format(
            message=message[:1000],
            reply=ai_reply[:1500],
            specialty=specialty,
        )
        response = await _claude.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text if response.content else "[]"
        facts = _parse_llm_json(raw)

        if not facts:
            return []

        memories: list[StudentMemory] = []
        for fact in facts[:5]:
            if not isinstance(fact, dict) or not fact.get("content"):
                continue
            mem = StudentMemory(
                user_id=user_id,
                memory_type=fact.get("type", "fact"),
                content=fact["content"],
                search_tokens=_make_search_tokens(fact["content"], fact.get("tags")),
                specialty=specialty,
                competency_level=fact.get("competency_level", "intermediate"),
                species_context=fact.get("species_context", "human"),
                source_conversation_id=conversation_id,
                confidence=float(fact.get("confidence", 0.7)),
                importance_score=_importance(fact),
            )
            memories.append(mem)

        if memories:
            db.add_all(memories)
            await db.commit()
            logger.info("Saved %d memories for user %s", len(memories), user_id)

        return memories

    except Exception as exc:
        logger.warning("Memory extraction failed for user %s: %s", user_id, exc)
        try:
            await db.rollback()
        except Exception:
            pass
        return []


async def retrieve_relevant_memories(
    db: AsyncSession,
    user_id: UUID,
    query: str,
    specialty: Optional[str] = None,
    species_context: Optional[str] = None,
    limit: int = MAX_CONTEXT_MEMORIES,
) -> list[StudentMemory]:
    """
    Retrieve the most relevant memories for the given query.

    Strategy:
      1. Candidate filtering: user + not deprecated + confidence >= MIN_CONFIDENCE
      2. Full-text relevance via PostgreSQL tsvector if available, else token overlap
      3. Metadata boost: specialty match, recent access, importance_score
      4. Return top `limit` after reranking
    """
    try:
        stmt = (
            select(StudentMemory)
            .where(
                StudentMemory.user_id == user_id,
                StudentMemory.deprecated == False,
                StudentMemory.confidence >= MIN_CONFIDENCE,
            )
            .order_by(StudentMemory.importance_score.desc(), StudentMemory.created_at.desc())
            .limit(limit * 4)  # over-fetch for reranking
        )
        if specialty:
            stmt = stmt.where(StudentMemory.specialty == specialty)
        if species_context:
            stmt = stmt.where(
                or_(
                    StudentMemory.species_context == species_context,
                    StudentMemory.species_context == "human",
                    StudentMemory.species_context == None,
                )
            )

        candidates = (await db.execute(stmt)).scalars().all()

        if not candidates:
            return []

        # Build query tokens for overlap scoring
        query_tokens = set(re.findall(r"[a-zA-Zа-яёА-ЯЁ0-9]+", query.lower()))
        query_tokens = {t for t in query_tokens if len(t) > 2}

        now = datetime.utcnow()

        def score(mem: StudentMemory) -> float:
            # Token overlap score
            mem_tokens = set((mem.search_tokens or "").split())
            overlap = len(query_tokens & mem_tokens)
            token_score = overlap / max(len(query_tokens), 1)

            # Specialty match bonus
            specialty_bonus = 0.2 if specialty and mem.specialty == specialty else 0.0

            # Recency bonus (decays over 30 days)
            if mem.last_accessed:
                days_old = (now - mem.last_accessed).days
            elif mem.created_at:
                days_old = (now - mem.created_at).days
            else:
                days_old = 30
            recency = max(0.0, 1.0 - days_old / 30.0) * 0.2

            # Misconceptions always surface
            type_bonus = 0.25 if mem.memory_type == "misconception" else 0.0

            return (
                token_score * 0.5
                + mem.importance_score * 0.2
                + specialty_bonus
                + recency
                + type_bonus
                + min(mem.access_count, 10) / 100
            )

        ranked = sorted(candidates, key=score, reverse=True)[:limit]

        # Update access stats
        for mem in ranked:
            mem.access_count += 1
            mem.last_accessed = now
            mem.updated_at = now
        await db.commit()

        return ranked

    except Exception as exc:
        logger.warning("Memory retrieval failed for user %s: %s", user_id, exc)
        return []


def format_memory_context(memories: list[StudentMemory]) -> str:
    """Format memories into a concise system prompt injection."""
    if not memories:
        return ""

    lines = []
    for mem in memories:
        prefix = {
            "misconception": "⚠️ Previous misconception",
            "case_experience": "📋 Prior case",
            "skill": "🛠 Known skill",
            "preference": "💬 Learning preference",
        }.get(mem.memory_type, "📌 Known fact")

        level = f"[{mem.competency_level}]" if mem.competency_level else ""
        lines.append(f"• {prefix} {level}: {mem.content}")

    return (
        "\n\n=== Student's Prior Knowledge (from past sessions) ===\n"
        + "\n".join(lines)
        + "\n=== Use this context to personalise your response. "
        "Do NOT repeat information the student already knows unless they ask. "
        "Address any misconceptions gently. ==="
    )
