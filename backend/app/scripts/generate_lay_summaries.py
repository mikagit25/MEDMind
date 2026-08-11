"""
Generate lay_summary + lay_glossary for lessons using Groq (llama-3.3-70b).

Usage:
  python -m app.scripts.generate_lay_summaries [OPTIONS]

Options:
  --max-lessons N   Process at most N lessons (default: all)
  --force           Overwrite existing lay_summary (default: skip)
  --dry-run         Show what would be processed, do not call API or save
  --module-code X   Only process lessons from module with this code
  --delay S         Seconds between requests to avoid rate limiting (default: 1.5)
"""

import argparse
import asyncio
import itertools
import json
import logging
import os
import re

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.models import Lesson, Module
from app.prompts.lay_summary import LAY_SUMMARY_SYSTEM, LAY_SUMMARY_USER

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

_GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
_GROQ_MODEL = "llama-3.1-8b-instant"   # 500K+ TPD vs 100K for 70b


def _g(name: str) -> str:
    return os.getenv(name, getattr(settings, name, ""))


def _build_key_cycle():
    keys = [
        _g("GROQ_API_KEY"), _g("GROQ_API_KEY_2"), _g("GROQ_API_KEY_3"),
        _g("GROQ_API_KEY_4"), _g("GROQ_API_KEY_5"), _g("GROQ_API_KEY_6"),
        _g("GROQ_KEY_MODULE"), _g("GROQ_KEY_MODULE_2"),
    ]
    deduped = list(dict.fromkeys(k for k in keys if k))
    if not deduped:
        raise RuntimeError("No Groq API keys configured. Set GROQ_API_KEY (and optionally GROQ_API_KEY_2, etc.) in .env")
    log.info("Using %d Groq key(s) with round-robin rotation.", len(deduped))
    return itertools.cycle(deduped)


def _str(v) -> str:
    """Safely coerce any value to string."""
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        return v.get("text", "") or v.get("content", "") or ""
    return str(v) if v else ""


def _extract_text_from_content(content: dict) -> str:
    parts = []
    blocks = content.get("sections") or content.get("blocks") or []
    if isinstance(blocks, list):
        for block in blocks:
            if not isinstance(block, dict):
                continue
            btype = block.get("type", "")
            if btype in ("text", "paragraph", "intro"):
                parts.append(_str(block.get("content") or block.get("text")))
            elif btype == "heading":
                parts.append(_str(block.get("text")))
            elif btype in ("list", "bullet_list"):
                for item in block.get("items", []):
                    parts.append(f"- {_str(item)}")
            elif btype == "key_point":
                parts.append(f"Key point: {_str(block.get('content'))}")
            elif btype == "definition":
                parts.append(f"{_str(block.get('term'))}: {_str(block.get('definition'))}")
    # Gulf module format: top-level intro + sections with title/text
    if not parts:
        intro = content.get("intro") or content.get("introduction", "")
        if intro:
            parts.append(_str(intro))
        for sec in content.get("sections", []):
            if isinstance(sec, dict):
                for field in ("title", "text", "content"):
                    v = sec.get(field)
                    if v:
                        parts.append(_str(v))
    if not parts:
        parts.append(json.dumps(content)[:3000])
    return "\n".join(p for p in parts if p).strip()


def _parse_ai_response(raw: str) -> dict:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


async def _call_groq(title: str, content_text: str, key_cycle, retries: int = 2) -> dict | None:
    prompt = LAY_SUMMARY_USER.format(title=title, content_text=content_text[:3500])
    for attempt in range(retries + 1):
        key = next(key_cycle)
        try:
            async with httpx.AsyncClient(timeout=60) as c:
                resp = await c.post(
                    _GROQ_URL,
                    headers={"Authorization": f"Bearer {key}"},
                    json={
                        "model": _GROQ_MODEL,
                        "messages": [
                            {"role": "system", "content": LAY_SUMMARY_SYSTEM},
                            {"role": "user", "content": prompt},
                        ],
                        "max_tokens": 1500,
                        "temperature": 0.2,
                    },
                )
                resp.raise_for_status()
                raw = resp.json()["choices"][0]["message"]["content"]
                return _parse_ai_response(raw)
        except json.JSONDecodeError as e:
            log.warning("JSON parse error for '%s' (attempt %d): %s", title, attempt + 1, e)
            if attempt < retries:
                await asyncio.sleep(5)
        except httpx.HTTPStatusError as e:
            log.error("Groq HTTP %s for '%s': %s", e.response.status_code, title, e.response.text[:200])
            if e.response.status_code == 429 and attempt < retries:
                await asyncio.sleep(30)
            else:
                return None
        except Exception as e:
            log.error("API error for '%s': %s", title, e)
            return None
    return None


async def run(
    max_lessons: int | None,
    force: bool,
    dry_run: bool,
    module_code: str | None,
    delay: float,
):
    key_cycle = _build_key_cycle()

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        stmt = select(Lesson).join(Module, Lesson.module_id == Module.id)
        if not force:
            stmt = stmt.where(Lesson.lay_summary.is_(None))
        if module_code:
            stmt = stmt.where(Module.code == module_code)
        stmt = stmt.order_by(Lesson.created_at)
        if max_lessons:
            stmt = stmt.limit(max_lessons)

        result = await db.execute(stmt)
        lessons = result.scalars().all()

    log.info("Found %d lesson(s) to process.", len(lessons))

    if dry_run:
        for lesson in lessons:
            log.info("[DRY RUN] Would process: %s (id=%s)", lesson.title, lesson.id)
        await engine.dispose()
        return

    processed = 0
    async with async_session() as db:
        for i, lesson in enumerate(lessons):
            content_text = _extract_text_from_content(lesson.content or {})
            log.info("[%d/%d] Processing: %s", i + 1, len(lessons), lesson.title)

            result = await _call_groq(lesson.title, content_text, key_cycle)
            if not result:
                log.warning("Skipping '%s' — no valid response.", lesson.title)
            else:
                db_lesson = await db.get(Lesson, lesson.id)
                if db_lesson:
                    db_lesson.lay_summary = result.get("lay_summary")
                    glossary = result.get("lay_glossary", [])
                    db_lesson.lay_glossary = glossary if isinstance(glossary, list) else []
                    await db.commit()
                    log.info("  Saved (%d chars, %d glossary terms).",
                             len(db_lesson.lay_summary or ""), len(db_lesson.lay_glossary or []))
                    processed += 1

            if delay > 0 and i < len(lessons) - 1:
                await asyncio.sleep(delay)

    log.info("Done. Processed %d / %d lessons.", processed, len(lessons))
    await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="Generate lay summaries for lessons via Groq")
    parser.add_argument("--max-lessons", type=int, default=None, metavar="N")
    parser.add_argument("--force", action="store_true", help="Overwrite existing lay_summary")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--module-code", type=str, default=None,
                        help="Only process lessons from this module code")
    parser.add_argument("--delay", type=float, default=1.5,
                        help="Seconds between requests (default: 1.5)")
    args = parser.parse_args()

    asyncio.run(run(
        max_lessons=args.max_lessons,
        force=args.force,
        dry_run=args.dry_run,
        module_code=args.module_code,
        delay=args.delay,
    ))


if __name__ == "__main__":
    main()
