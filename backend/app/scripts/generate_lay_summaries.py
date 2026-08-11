"""
Generate lay_summary + lay_glossary for lessons using full AI provider cascade.

Cascade order: Claude → Gemini (5 keys) → Cerebras (6 keys)
               → SambaNova (3 keys) → Groq (all keys) → Ollama (local)

Usage:
  python -m app.scripts.generate_lay_summaries [OPTIONS]

Options:
  --max-lessons N   Process at most N lessons (default: all)
  --force           Overwrite existing lay_summary (default: skip)
  --dry-run         Show what would be processed, do not call API or save
  --module-code X   Only process lessons from module with this code
  --delay S         Seconds between requests (default: 1.0)
"""

import argparse
import asyncio
import json
import logging
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.models import Lesson, Module
from app.prompts.lay_summary import LAY_SUMMARY_SYSTEM, LAY_SUMMARY_USER

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


def _str(v) -> str:
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


async def _generate_for_lesson(title: str, content_text: str) -> dict | None:
    """Call the full AI cascade. Returns parsed dict or None on failure."""
    from app.services.ai_router import call_generation_ai

    prompt = LAY_SUMMARY_USER.format(title=title, content_text=content_text[:3500])
    try:
        raw, model = await call_generation_ai(
            system=LAY_SUMMARY_SYSTEM,
            user_message=prompt,
            max_tokens=1500,
        )
        log.debug("  model used: %s", model)
        return _parse_ai_response(raw)
    except json.JSONDecodeError as e:
        log.warning("JSON parse error for '%s': %s", title, e)
        return None
    except Exception as e:
        log.error("All providers failed for '%s': %s", title, e)
        return None


async def run(
    max_lessons: int | None,
    force: bool,
    dry_run: bool,
    module_code: str | None,
    delay: float,
):
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

    log.info("Found %d lesson(s) without lay_summary to process.", len(lessons))

    if dry_run:
        for lesson in lessons:
            log.info("[DRY RUN] Would process: %s (id=%s)", lesson.title, lesson.id)
        await engine.dispose()
        return

    processed = 0
    failed = 0
    async with async_session() as db:
        for i, lesson in enumerate(lessons):
            raw_content = lesson.content or {}
            if isinstance(raw_content, str):
                try:
                    raw_content = json.loads(raw_content)
                except (json.JSONDecodeError, ValueError):
                    raw_content = {"intro": raw_content}
            content_text = _extract_text_from_content(raw_content)
            log.info("[%d/%d] %s", i + 1, len(lessons), lesson.title)

            result = await _generate_for_lesson(lesson.title, content_text)
            if not result:
                log.warning("  Skipping — no valid response from any provider.")
                failed += 1
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

    log.info("Done. Processed %d / %d lessons. Failed: %d.", processed, len(lessons), failed)
    await engine.dispose()


def main():
    parser = argparse.ArgumentParser(
        description="Generate lay summaries for lessons via full AI cascade "
                    "(Claude → Gemini → Cerebras → SambaNova → Groq → Ollama)"
    )
    parser.add_argument("--max-lessons", type=int, default=None, metavar="N")
    parser.add_argument("--force", action="store_true", help="Overwrite existing lay_summary")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--module-code", type=str, default=None,
                        help="Only process lessons from this module code")
    parser.add_argument("--delay", type=float, default=1.0,
                        help="Seconds between requests (default: 1.0)")
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
