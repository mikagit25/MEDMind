"""
Generate lay_summary + lay_glossary for lessons using Claude Haiku.

Usage:
  python -m app.scripts.generate_lay_summaries [OPTIONS]

Options:
  --max-lessons N   Process at most N lessons (default: all)
  --force           Overwrite existing lay_summary (default: skip)
  --dry-run         Show what would be processed, do not call API or save
  --module-code X   Only process lessons from module with this code
"""

import argparse
import asyncio
import json
import logging
import re
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.models import Lesson, Module
from app.prompts.lay_summary import LAY_SUMMARY_SYSTEM, LAY_SUMMARY_USER

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


def _extract_text_from_content(content: dict) -> str:
    """Flatten JSONB lesson content to a plain-text string for the prompt."""
    parts = []
    blocks = content.get("blocks") or content.get("sections") or []
    if isinstance(blocks, list):
        for block in blocks:
            if isinstance(block, dict):
                btype = block.get("type", "")
                if btype in ("text", "paragraph", "intro"):
                    parts.append(block.get("content", ""))
                elif btype == "heading":
                    parts.append(block.get("text", ""))
                elif btype in ("list", "bullet_list"):
                    for item in block.get("items", []):
                        if isinstance(item, str):
                            parts.append(f"- {item}")
                        elif isinstance(item, dict):
                            parts.append(f"- {item.get('text', '')}")
                elif btype == "key_point":
                    parts.append(f"Key point: {block.get('content', '')}")
                elif btype == "definition":
                    parts.append(f"{block.get('term', '')}: {block.get('definition', '')}")
    # Fallback: stringify the whole content
    if not parts:
        parts.append(json.dumps(content)[:3000])
    return "\n".join(p for p in parts if p).strip()


def _parse_ai_response(raw: str) -> dict:
    """Extract JSON from AI response, handling potential markdown fences."""
    raw = raw.strip()
    # Strip markdown code fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


async def _call_claude(title: str, content_text: str, client) -> dict | None:
    """Call Claude Haiku and return parsed JSON result."""
    try:
        response = await asyncio.to_thread(
            client.messages.create,
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=LAY_SUMMARY_SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": LAY_SUMMARY_USER.format(
                        title=title,
                        content_text=content_text[:4000],
                    ),
                }
            ],
        )
        raw = response.content[0].text
        return _parse_ai_response(raw)
    except json.JSONDecodeError as e:
        log.warning("JSON parse error for lesson '%s': %s", title, e)
        return None
    except Exception as e:
        log.error("API error for lesson '%s': %s", title, e)
        return None


async def run(
    max_lessons: int | None,
    force: bool,
    dry_run: bool,
    module_code: str | None,
):
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    engine = create_async_engine(settings.database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        # Build query
        stmt = select(Lesson).join(Module, Lesson.module_id == Module.id)
        if not force:
            stmt = stmt.where(Lesson.lay_summary.is_(None))
        if module_code:
            stmt = stmt.where(Module.module_code == module_code)
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
        for lesson in lessons:
            content_text = _extract_text_from_content(lesson.content or {})
            log.info("Processing: %s", lesson.title)

            result = await _call_claude(lesson.title, content_text, client)
            if not result:
                log.warning("Skipping '%s' — no valid response.", lesson.title)
                continue

            # Re-fetch for update
            db_lesson = await db.get(Lesson, lesson.id)
            if db_lesson:
                db_lesson.lay_summary = result.get("lay_summary")
                glossary = result.get("lay_glossary", [])
                db_lesson.lay_glossary = glossary if isinstance(glossary, list) else []
                await db.commit()
                log.info("  Saved lay_summary (%d chars) + %d glossary terms.",
                         len(db_lesson.lay_summary or ""), len(db_lesson.lay_glossary or []))
                processed += 1

    log.info("Done. Processed %d / %d lessons.", processed, len(lessons))
    await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="Generate lay summaries for lessons")
    parser.add_argument("--max-lessons", type=int, default=None, metavar="N",
                        help="Process at most N lessons")
    parser.add_argument("--force", action="store_true",
                        help="Overwrite existing lay_summary")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be processed without calling API")
    parser.add_argument("--module-code", type=str, default=None,
                        help="Only process lessons from this module (e.g. BASE-CARDIO-ANATOMY-001)")
    args = parser.parse_args()

    asyncio.run(run(
        max_lessons=args.max_lessons,
        force=args.force,
        dry_run=args.dry_run,
        module_code=args.module_code,
    ))


if __name__ == "__main__":
    main()
