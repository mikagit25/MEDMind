"""
Translation cron — rotates ALL available AI provider keys within rate limits.

Providers supported (content pipeline keys only):
  - Groq        : KEY_3, KEY_4, KEY_5, KEY_MODULE, KEY_MODULE_2, KEY_VET_ARTICLES, KEY_VET_MODULES
  - Gemini      : KEY_2..KEY_5 (KEY_1 reserved for user AI)
  - Cerebras    : KEY_2..KEY_5 (KEY_1 reserved for user AI)
  - SambaNova   : KEY_2, KEY_3, SAMBANOVA_API_KEY_NEW_1, SAMBANOVA_API_KEY_NEW_2
  - Anthropic   : only if ANTHROPIC_API_KEY set (credits may be depleted)
  - OpenRouter  : OPENROUTER_API_KEY (free-tier Qwen model)

Run:
    docker exec medmind_backend python3 /app/scripts/translate_cron.py [--batch N]

Cron (every 30 min in the container):
    */30 * * * * docker exec medmind_backend python3 /app/scripts/translate_cron.py >> /var/log/translate_cron.log 2>&1
"""

import asyncio
import json
import logging
import os
import sys
import time
import argparse
import re
from datetime import datetime
from itertools import cycle
from typing import Optional

import httpx
from sqlalchemy import select, and_, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# ── bootstrap path ────────────────────────────────────────────────────────────
sys.path.insert(0, "/app")
from app.core.config import settings
from app.models.models import LessonTranslation, Lesson, SUPPORTED_LOCALES

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("translate_cron")

# ── Rate-limit budgets per run (conservative — stay well within free tier) ────
# Groq free: 14400 req/day, 30 TPM per key → ~1-2 lessons per minute per key
# Gemini free: 60 req/min, 1000 req/day per key
# Cerebras free: ~60 req/min
# SambaNova free: ~60 req/min
# Each lesson translation = ~1 request per locale (we batch content)
BATCH_DEFAULT = 6   # lessons per cron run (across all providers)

# ── Provider pool ─────────────────────────────────────────────────────────────
def _build_provider_pool() -> list[dict]:
    """Build a list of provider configs from environment. Only includes non-empty keys."""
    pool = []

    def add_groq(key_val: str, label: str):
        if key_val:
            pool.append({
                "name": f"Groq/{label}",
                "type": "groq",
                "api_key": key_val,
                "model": settings.GROQ_MODEL or "llama-3.3-70b-versatile",
                "rpm_limit": 30,   # conservative — free tier is 30 RPM
                "last_used": 0.0,
            })

    def add_gemini(key_val: str, label: str):
        if key_val:
            pool.append({
                "name": f"Gemini/{label}",
                "type": "gemini",
                "api_key": key_val,
                "model": settings.GEMINI_MODEL or "gemini-2.0-flash",
                "rpm_limit": 15,   # free tier: 15 RPM
                "last_used": 0.0,
            })

    def add_cerebras(key_val: str, label: str):
        if key_val:
            pool.append({
                "name": f"Cerebras/{label}",
                "type": "cerebras",
                "api_key": key_val,
                "model": settings.CEREBRAS_MODEL or "gemma-4-31b",
                "rpm_limit": 30,
                "last_used": 0.0,
            })

    def add_sambanova(key_val: str, label: str):
        if key_val:
            pool.append({
                "name": f"SambaNova/{label}",
                "type": "sambanova",
                "api_key": key_val,
                "model": settings.SAMBANOVA_MODEL or "Meta-Llama-3.1-70B-Instruct",
                "rpm_limit": 30,
                "last_used": 0.0,
            })

    # Groq — content pipeline keys (NOT user AI keys KEY_1/KEY_2/KEY_6)
    add_groq(settings.GROQ_API_KEY_3, "KEY_3")
    add_groq(settings.GROQ_API_KEY_4, "KEY_4")
    add_groq(settings.GROQ_API_KEY_5, "KEY_5")
    add_groq(settings.GROQ_KEY_MODULE, "MODULE")
    add_groq(settings.GROQ_KEY_MODULE_2, "MODULE_2")
    add_groq(settings.GROQ_KEY_VET_ARTICLES, "VET_ARTICLES")
    add_groq(settings.GROQ_KEY_VET_MODULES, "VET_MODULES")

    # Gemini — use KEY_2..KEY_5 for content pipeline (KEY_1 may be shared)
    add_gemini(getattr(settings, "GEMINI_API_KEY_2", ""), "KEY_2")
    add_gemini(getattr(settings, "GEMINI_API_KEY_3", ""), "KEY_3")
    add_gemini(getattr(settings, "GEMINI_API_KEY_4", ""), "KEY_4")
    add_gemini(getattr(settings, "GEMINI_API_KEY_5", ""), "KEY_5")

    # Cerebras — KEY_2..KEY_5 for content pipeline
    add_cerebras(getattr(settings, "CEREBRAS_API_KEY_2", ""), "KEY_2")
    add_cerebras(getattr(settings, "CEREBRAS_API_KEY_3", ""), "KEY_3")
    add_cerebras(getattr(settings, "CEREBRAS_API_KEY_4", ""), "KEY_4")
    add_cerebras(getattr(settings, "CEREBRAS_API_KEY_5", ""), "KEY_5")

    # SambaNova — KEY_2, KEY_3, NEW_1, NEW_2
    add_sambanova(getattr(settings, "SAMBANOVA_API_KEY_2", ""), "KEY_2")
    add_sambanova(getattr(settings, "SAMBANOVA_API_KEY_3", ""), "KEY_3")
    add_sambanova(getattr(settings, "SAMBANOVA_API_KEY_NEW_1", ""), "NEW_1")
    add_sambanova(getattr(settings, "SAMBANOVA_API_KEY_NEW_2", ""), "NEW_2")

    # OpenRouter — free-tier fallback
    if getattr(settings, "OPENROUTER_API_KEY", ""):
        pool.append({
            "name": "OpenRouter/KEY_1",
            "type": "openrouter",
            "api_key": settings.OPENROUTER_API_KEY,
            "model": getattr(settings, "OPENROUTER_MODEL", "qwen/qwen3-8b"),
            "rpm_limit": 10,  # very conservative for free tier
            "last_used": 0.0,
        })

    # Anthropic — add last (may be depleted)
    if settings.ANTHROPIC_API_KEY:
        pool.append({
            "name": "Anthropic/Haiku",
            "type": "anthropic",
            "api_key": settings.ANTHROPIC_API_KEY,
            "model": "claude-haiku-4-5-20251001",
            "rpm_limit": 60,
            "last_used": 0.0,
        })

    return pool


# ── Medical translation prompt ────────────────────────────────────────────────
LANG_NAMES = {
    "ru": "Russian",
    "ar": "Arabic",
    "tr": "Turkish",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
}

MEDICAL_HINTS = {
    "ru": "Use standard Russian medical terminology. Keep drug names in Latin. Formal medical register.",
    "ar": "Use Modern Standard Arabic (MSA). Keep drug names in Latin. RTL language.",
    "tr": "Use official Turkish medical terminology (TTD). Keep drug names unchanged. Formal register.",
    "de": "Use standard German medical terminology. Keep drug names in Latin/English. Formal register.",
    "fr": "Use standard French medical terminology. Keep drug names in Latin/English. Formal register.",
    "es": "Use standard Spanish medical terminology (Spain/LatAm). Keep drug names in Latin. Formal register.",
}


def build_system_prompt(locale: str) -> str:
    lang = LANG_NAMES.get(locale, locale)
    hint = MEDICAL_HINTS.get(locale, "")
    return (
        f"You are a professional medical translator. Translate the following JSON content from English to {lang}. "
        f"Rules: {hint} "
        "Output ONLY the translated JSON with the same structure and keys as the input. "
        "Do not add commentary, markdown fences, or explanations. "
        "Keep numerical values, drug dosages, lab values, and proper names unchanged. "
        "Preserve all JSON keys exactly as-is (translate values only). "
        "If a value is a number or URL, do not translate it."
    )


def extract_translatable(lesson: Lesson) -> dict:
    """Extract only text fields that need translation from a lesson."""
    content = lesson.content or {}
    result = {
        "title": lesson.title or "",
        "lay_summary": lesson.lay_summary or "",
        "intro": content.get("intro", ""),
        "clinical_pearl": content.get("clinical_pearl", ""),
        "key_points": content.get("key_points", []),
        "sections": [
            {"title": s.get("title", ""), "body": s.get("body", "")}
            for s in content.get("sections", [])
        ],
    }
    return result


# ── API call implementations ─────────────────────────────────────────────────
async def _call_groq(provider: dict, system: str, user: str) -> str:
    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {provider['api_key']}", "Content-Type": "application/json"},
            json={
                "model": provider["model"],
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "temperature": 0.1,
                "max_tokens": 3000,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def _call_gemini(provider: dict, system: str, user: str) -> str:
    model = provider["model"]
    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={provider['api_key']}",
            json={
                "contents": [{"role": "user", "parts": [{"text": f"{system}\n\n{user}"}]}],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 3000},
            },
        )
        resp.raise_for_status()
        return resp.json()["candidates"][0]["content"]["parts"][0]["text"]


async def _call_cerebras(provider: dict, system: str, user: str) -> str:
    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(
            "https://api.cerebras.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {provider['api_key']}", "Content-Type": "application/json"},
            json={
                "model": provider["model"],
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "temperature": 0.1,
                "max_tokens": 3000,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def _call_sambanova(provider: dict, system: str, user: str) -> str:
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            "https://api.sambanova.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {provider['api_key']}", "Content-Type": "application/json"},
            json={
                "model": provider["model"],
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "temperature": 0.1,
                "max_tokens": 3000,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def _call_openrouter(provider: dict, system: str, user: str) -> str:
    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {provider['api_key']}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://medmind.ai",
            },
            json={
                "model": provider["model"],
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "temperature": 0.1,
                "max_tokens": 3000,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def _call_anthropic(provider: dict, system: str, user: str) -> str:
    import anthropic
    client = anthropic.AsyncAnthropic(api_key=provider["api_key"], timeout=90)
    msg = await client.messages.create(
        model=provider["model"],
        max_tokens=3000,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return msg.content[0].text


DISPATCH = {
    "groq": _call_groq,
    "gemini": _call_gemini,
    "cerebras": _call_cerebras,
    "sambanova": _call_sambanova,
    "openrouter": _call_openrouter,
    "anthropic": _call_anthropic,
}


async def call_provider(provider: dict, system: str, user: str) -> str:
    """Call provider with rate-limit enforcement (minimum gap between calls)."""
    min_gap = 60.0 / provider["rpm_limit"]
    elapsed = time.time() - provider["last_used"]
    if elapsed < min_gap:
        await asyncio.sleep(min_gap - elapsed)
    result = await DISPATCH[provider["type"]](provider, system, user)
    provider["last_used"] = time.time()
    return result


def parse_json_response(raw: str) -> dict:
    """Extract JSON from model response, handling markdown fences."""
    raw = raw.strip()
    # Remove markdown fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)
    # Find first { or [
    for i, ch in enumerate(raw):
        if ch in ("{", "["):
            try:
                return json.loads(raw[i:])
            except json.JSONDecodeError:
                break
    raise ValueError(f"No valid JSON found in response: {raw[:200]}")


# ── DB helpers ────────────────────────────────────────────────────────────────
async def get_pending_translations(session: AsyncSession, batch: int) -> list[tuple]:
    """Return (lesson_id, locale) pairs that are still pending."""
    result = await session.execute(
        text("""
            SELECT lt.lesson_id, lt.locale
            FROM lesson_translations lt
            WHERE lt.status = 'pending'
            ORDER BY lt.locale, lt.lesson_id
            LIMIT :batch
        """),
        {"batch": batch},
    )
    return result.fetchall()


async def get_lesson(session: AsyncSession, lesson_id) -> Optional[Lesson]:
    result = await session.execute(select(Lesson).where(Lesson.id == lesson_id))
    return result.scalar_one_or_none()


async def save_translation(session: AsyncSession, lesson_id, locale: str, translated: dict) -> None:
    await session.execute(
        text("""
            UPDATE lesson_translations
            SET status = 'done',
                title = :title,
                content_json = :content,
                translated_at = now()
            WHERE lesson_id = :lesson_id AND locale = :locale
        """),
        {
            "lesson_id": str(lesson_id),
            "locale": locale,
            "title": translated.get("title", ""),
            "content": json.dumps(translated, ensure_ascii=False),
        },
    )
    await session.commit()


async def mark_failed(session: AsyncSession, lesson_id, locale: str) -> None:
    await session.execute(
        text("UPDATE lesson_translations SET status = 'failed' WHERE lesson_id = :lid AND locale = :loc"),
        {"lid": str(lesson_id), "loc": locale},
    )
    await session.commit()


# ── Main ──────────────────────────────────────────────────────────────────────
async def main(batch: int) -> None:
    pool = _build_provider_pool()
    if not pool:
        log.error("No API keys found — check .env for GROQ_API_KEY_3, GEMINI_API_KEY_2, etc.")
        return

    log.info("Provider pool: %d providers — %s", len(pool), [p["name"] for p in pool])

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        pending = await get_pending_translations(session, batch)
        log.info("Pending translations to process: %d", len(pending))

        if not pending:
            log.info("Nothing to translate. Done.")
            return

    # Round-robin over provider pool
    provider_cycle = cycle(pool)
    provider = next(provider_cycle)

    total_ok = 0
    total_fail = 0

    for lesson_id, locale in pending:
        async with async_session() as session:
            lesson = await get_lesson(session, lesson_id)
            if not lesson:
                log.warning("Lesson %s not found — skipping", lesson_id)
                continue

            translatable = extract_translatable(lesson)
            system = build_system_prompt(locale)
            user = json.dumps(translatable, ensure_ascii=False)

            # Try up to len(pool) providers before giving up on this lesson
            success = False
            for attempt in range(len(pool)):
                try:
                    log.info(
                        "Translating lesson %s → %s via %s (attempt %d)",
                        lesson_id, locale, provider["name"], attempt + 1,
                    )
                    raw = await call_provider(provider, system, user)
                    translated = parse_json_response(raw)
                    await save_translation(session, lesson_id, locale, translated)
                    log.info("✅  %s → %s OK", lesson_id, locale)
                    total_ok += 1
                    success = True
                    break
                except Exception as e:
                    err = str(e)
                    log.warning("Provider %s failed for %s/%s: %s", provider["name"], lesson_id, locale, err[:120])
                    if "rate" in err.lower() or "quota" in err.lower() or "429" in err:
                        log.info("Rate limit — rotating to next provider")
                    provider = next(provider_cycle)
                    await asyncio.sleep(2)

            if not success:
                log.error("All providers failed for %s/%s — marking as failed", lesson_id, locale)
                async with async_session() as s2:
                    await mark_failed(s2, lesson_id, locale)
                total_fail += 1

            # Rotate provider each lesson to spread load
            provider = next(provider_cycle)

    log.info("Run complete — OK: %d | Failed: %d | Providers used: %d", total_ok, total_fail, len(pool))
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, default=BATCH_DEFAULT,
                        help="Number of pending translations to process per run")
    args = parser.parse_args()
    asyncio.run(main(args.batch))
