"""Text-to-Speech endpoint — Edge TTS streaming audio.

GET  /tts/voices           List available voices
POST /tts/speak            Stream MP3 audio for given text + locale
POST /tts/article/{id}     Stream full article as audio (extracts body text)
"""
import logging
import re
import unicodedata
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

# Male voice alternatives
LOCALE_VOICES_MALE: dict[str, str] = {
    "en": "en-US-GuyNeural",
    "ru": "ru-RU-DmitryNeural",
    "de": "de-DE-ConradNeural",
    "fr": "fr-FR-HenriNeural",
    "es": "es-ES-AlvaroNeural",
    "ar": "ar-SA-HamedNeural",
    "tr": "tr-TR-AhmetNeural",
}

MAX_CHARS = 8_000  # Edge TTS practical limit per request


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
    # Strip markdown remnants
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)
    text = re.sub(r"`[^`]+`", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:MAX_CHARS]


async def _stream_tts(text: str, voice: str, rate: str = "+0%") -> AsyncGenerator[bytes, None]:
    """Stream Edge TTS MP3 chunks."""
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]
    except ImportError:
        raise HTTPException(status_code=503, detail="TTS service unavailable — edge-tts not installed")
    except Exception as e:
        logger.error("Edge TTS error: %s", e)
        raise HTTPException(status_code=502, detail=f"TTS generation failed: {e}")


@router.get("/voices")
async def list_voices(user: User = Depends(get_current_user)):
    """Return available voices grouped by language."""
    voices = []
    for locale, female_voice in LOCALE_VOICES.items():
        male_voice = LOCALE_VOICES_MALE.get(locale)
        voices.append({
            "locale": locale,
            "female": female_voice,
            "male": male_voice,
        })
    return {"voices": voices}


@router.post("/speak")
async def speak(
    req: SpeakRequest,
    user: User = Depends(get_current_user),
):
    """Stream MP3 audio for arbitrary text."""
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
    user: User = Depends(get_current_user),
):
    """Stream article body as MP3 audio. Uses translated body if available."""
    # Try translated version first
    lang = locale[:2].lower()
    text = None

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

    if not text:
        art_result = await db.execute(select(Article).where(Article.id == article_id))
        article = art_result.scalar_one_or_none()
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")
        text = _blocks_to_text(article.body or [])

    if not text:
        raise HTTPException(status_code=422, detail="Article has no readable content")

    voice = _voice_for(locale, gender)
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
