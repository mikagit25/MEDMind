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


def _gemini_keys() -> list[str]:
    keys = []
    for attr in ("GEMINI_API_KEY", "GEMINI_API_KEY_2", "GEMINI_API_KEY_3",
                 "GEMINI_API_KEY_4", "GEMINI_API_KEY_5"):
        val = getattr(settings, attr, "")
        if val:
            keys.append(val)
    return keys


async def generate_embedding(text: str) -> Optional[list[float]]:
    """Return a 768-dim embedding vector or None if unavailable.

    Tries all configured Gemini keys in sequence; skips 429 rate-limited keys.
    Truncates input to 3000 chars (model limit is ~2048 tokens).
    Silently returns None on any error so callers don't need to handle failures.
    """
    keys = _gemini_keys()
    if not keys:
        logger.debug("No GEMINI_API_KEY configured — skipping embedding generation")
        return None

    text = text.strip()[:3000]
    if not text:
        return None

    payload = {
        "model": "models/text-embedding-004",
        "content": {"parts": [{"text": text}]},
        "taskType": EMBED_TASK_TYPE,
    }
    async with httpx.AsyncClient(timeout=15) as http:
        for key in keys:
            try:
                resp = await http.post(
                    GEMINI_EMBED_URL,
                    params={"key": key},
                    json=payload,
                )
                if resp.status_code == 429:
                    continue
                resp.raise_for_status()
                data = resp.json()
                return data["embedding"]["values"]
            except Exception as exc:
                logger.warning("Embedding key failed (non-fatal): %s", exc)
                continue
    logger.warning("All Gemini keys exhausted for embedding — skipping")
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
