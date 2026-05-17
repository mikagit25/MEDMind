"""Text-to-Speech endpoint — Edge TTS streaming audio.

GET  /tts/voices           List available voices
POST /tts/speak            Stream MP3 audio for given text + locale
GET  /tts/article/{id}     Stream full article as audio (no auth required)
"""
import logging
import re
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.models import Article, ArticleTranslation, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tts", tags=["tts"])

# Best neural voice per locale — female (clearer for medical terminology)
LOCALE_VOICES: dict[str, str] = {
    "en": "en-US-AriaNeural",
    "ru": "ru-RU-SvetlanaNeural",
    "de": "de-DE-KatjaNeural",
    "fr": "fr-FR-DeniseNeural",
    "es": "es-ES-ElviraNeural",
    "ar": "ar-SA-ZariyahNeural",
    "tr": "tr-TR-EmelNeural",
}

LOCALE_VOICES_MALE: dict[str, str] = {
    "en": "en-US-GuyNeural",
    "ru": "ru-RU-DmitryNeural",
    "de": "de-DE-ConradNeural",
    "fr": "fr-FR-HenriNeural",
    "es": "es-ES-AlvaroNeural",
    "ar": "ar-SA-HamedNeural",
    "tr": "tr-TR-AhmetNeural",
}

MAX_CHARS = 6_000   # ~6-8 min of speech; beyond that UX suffers anyway


class SpeakRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_CHARS)
    locale: str = Field("en", min_length=2, max_length=5)
    gender: str = Field("female", pattern="^(female|male)$")
    rate: str = Field("+0%", description="Speed adjustment: -20% to +20%")


def _voice_for(locale: str, gender: str) -> str:
    lang = locale[:2].lower()
    if gender == "male":
        return LOCALE_VOICES_MALE.get(lang, LOCALE_VOICES_MALE["en"])
    return LOCALE_VOICES.get(lang, LOCALE_VOICES["en"])


def _blocks_to_text(blocks: list) -> str:
    """Convert article body blocks to plain text for TTS."""
    parts = []
    for block in blocks:
        t = block.get("type", "")
        if t in ("h2", "h3", "h4"):
            parts.append(block.get("content", "") + ". ")
        elif t in ("p", "callout"):
            parts.append(block.get("content", "") + " ")
        elif t in ("ul", "ol"):
            for item in block.get("items", []):
                parts.append(item + ". ")
    text = " ".join(parts)
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    text = re.sub(r"`[^`]+`", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:MAX_CHARS]


def _check_edge_tts():
    """Raise 503 early (before streaming starts) if edge_tts not available."""
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="TTS service unavailable. Please try again later."
        )


async def _stream_tts(text: str, voice: str, rate: str = "+0%") -> AsyncGenerator[bytes, None]:
    """Stream Edge TTS MP3 chunks. Call _check_edge_tts() before this."""
    import edge_tts
    try:
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]
    except Exception as e:
        logger.error("Edge TTS stream error: %s", e)
        # Can't raise HTTPException here — headers already sent
        # Just stop the stream; client shows "error" state


@router.get("/voices")
async def list_voices():
    """Return available voices grouped by language. Public endpoint."""
    return {"voices": [
        {"locale": loc, "female": female, "male": LOCALE_VOICES_MALE.get(loc)}
        for loc, female in LOCALE_VOICES.items()
    ]}


@router.post("/speak")
async def speak(
    req: SpeakRequest,
    user: User = Depends(get_current_user),
):
    """Stream MP3 audio for arbitrary text. Requires auth."""
    _check_edge_tts()
    voice = _voice_for(req.locale, req.gender)
    return StreamingResponse(
        _stream_tts(req.text, voice, req.rate),
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": "inline; filename=speech.mp3",
            "Cache-Control": "no-cache",
            "X-Voice": voice,
        },
    )


@router.get("/article/{article_id}")
async def speak_article(
    article_id: str,
    locale: str = Query("en", min_length=2, max_length=5),
    gender: str = Query("female", pattern="^(female|male)$"),
    rate: str = Query("+0%"),
    db: AsyncSession = Depends(get_db),
):
    """
    Stream article body as MP3. Public — no auth required.
    Uses translated body if available for the requested locale.
    """
    # Check TTS availability BEFORE starting stream (prevents 502)
    _check_edge_tts()

    lang = locale[:2].lower()
    text = None

    # Try translated body first
    if lang != "en":
        tr_result = await db.execute(
            select(ArticleTranslation).where(
                ArticleTranslation.article_id == article_id,
                ArticleTranslation.locale == lang,
            )
        )
        tr = tr_result.scalar_one_or_none()
        if tr and tr.body:
            text = _blocks_to_text(tr.body)

    # Fallback to English body
    if not text:
        art_result = await db.execute(select(Article).where(Article.id == article_id))
        article = art_result.scalar_one_or_none()
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        text = _blocks_to_text(article.body or [])

    if not text:
        raise HTTPException(status_code=422, detail="Article has no readable content")

    voice = _voice_for(locale, gender)
    logger.info("TTS: article=%s locale=%s voice=%s chars=%d", article_id, locale, voice, len(text))

    return StreamingResponse(
        _stream_tts(text, voice, rate),
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": "inline; filename=article.mp3",
            "Cache-Control": "public, max-age=3600",
            "X-Voice": voice,
            "X-Text-Length": str(len(text)),
        },
    )
