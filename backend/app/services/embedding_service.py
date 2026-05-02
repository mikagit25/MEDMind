"""Embedding generation service.

Uses Google Gemini text-embedding-004 (free via aistudio.google.com).
Falls back gracefully when GEMINI_API_KEY is not set — embeddings are
treated as optional: missing embeddings just mean vector search won't
return that lesson until re-indexed.

Usage:
    from app.services.embedding_service import generate_embedding, reembed_lesson
"""
import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

GEMINI_EMBED_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "text-embedding-004:embedContent"
)
EMBED_TASK_TYPE = "RETRIEVAL_DOCUMENT"
EMBED_DIMENSIONS = 768  # text-embedding-004 native dimension


async def generate_embedding(text: str) -> Optional[list[float]]:
    """Return a 768-dim embedding vector or None if unavailable.

    Truncates input to 3000 chars (model limit is ~2048 tokens).
    Silently returns None on any error so callers don't need to handle failures.
    """
    if not settings.GEMINI_API_KEY:
        logger.debug("GEMINI_API_KEY not set — skipping embedding generation")
        return None

    text = text.strip()[:3000]
    if not text:
        return None

    payload = {
        "model": "models/text-embedding-004",
        "content": {"parts": [{"text": text}]},
        "taskType": EMBED_TASK_TYPE,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as http:
            resp = await http.post(
                GEMINI_EMBED_URL,
                params={"key": settings.GEMINI_API_KEY},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["embedding"]["values"]
    except Exception as exc:
        logger.warning("Embedding generation failed (non-fatal): %s", exc)
        return None


async def reembed_lesson(lesson_id, content: dict) -> None:
    """Background task: generate a new embedding for a lesson and save it.

    Imports DB models inline to avoid circular imports when called from lessons.py.
    Must be called inside its own AsyncSession (not the request-scoped one).
    """
    from app.core.database import AsyncSessionLocal
    from app.models.models import Lesson
    from app.services.content_sanitizer import extract_text_from_content
    from sqlalchemy import select

    text = extract_text_from_content(content)
    if not text:
        return

    vector = await generate_embedding(text)
    if vector is None:
        return

    try:
        async with AsyncSessionLocal() as db:
            lesson = (
                await db.execute(select(Lesson).where(Lesson.id == lesson_id))
            ).scalar_one_or_none()
            if lesson:
                lesson.embedding = vector
                await db.commit()
                logger.info("Re-embedded lesson %s (%d dims)", lesson_id, len(vector))
    except Exception as exc:
        logger.warning("Failed to save re-embedded lesson %s: %s", lesson_id, exc)
