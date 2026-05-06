"""Lesson & Module translation service.

Uses Claude Haiku for high-quality medical translation.
Falls back to Ollama (local) when Anthropic API key is not set.

Supports 6 non-English locales: ru, ar, tr, de, fr, es
English (en) is the source of truth — never translated.

Usage:
    from app.services.translation_service import schedule_lesson_translations
    await schedule_lesson_translations(lesson_id, db)

Translation is done block-by-block so:
  - Only text content is sent (images, iframes are language-neutral)
  - JSON structure is preserved exactly (quizzes, flashcards, dosage tables)
  - Terminology glossary is injected in the system prompt
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

import anthropic
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.models import Article, ArticleTranslation, Lesson, LessonTranslation, Module, ModuleTranslation, SUPPORTED_LOCALES

logger = logging.getLogger(__name__)

_claude = anthropic.AsyncAnthropic(
    api_key=settings.ANTHROPIC_API_KEY,
    timeout=120.0,
)

# ── Language metadata ─────────────────────────────────────────────────────────
LOCALE_NAMES = {
    "ru": "Russian",
    "ar": "Arabic",
    "tr": "Turkish",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
}

# Medical glossary hints per language to improve consistency
MEDICAL_HINTS = {
    "ru": "Use standard Russian medical terminology (МКБ-10 codes, РНМОТ guidelines). "
          "Translate 'drug' as 'препарат' or 'лекарство' depending on context. "
          "Keep Latin drug names in Latin. Use formal medical register.",
    "ar": "Use Modern Standard Arabic (MSA) for medical terms. "
          "Keep drug names in their international Latin form. "
          "Direction: RTL. Use male grammatical form as default.",
    "tr": "Use official Turkish medical terminology (TTD guidelines). "
          "Keep Latin drug names unchanged. Use formal register (resmi dil).",
    "de": "Use standard German medical terminology (AWMF guidelines). "
          "Keep Latin/Greek medical terms where conventional. "
          "Use Sie-form. Capitalize all nouns per German grammar.",
    "fr": "Use standard French medical terminology (HAS guidelines). "
          "Keep international drug names (DCI). "
          "Use vous-form. Apply proper French medical register.",
    "es": "Use standard Spanish medical terminology (OMC guidelines). "
          "Keep international drug names (DCI). "
          "Use usted-form. Use Spain Spanish as default.",
}

# Block types where only specific fields contain translatable text
TRANSLATABLE_FIELD_MAP: dict[str, list[str]] = {
    "text": ["content"],
    "quiz": [],  # handled specially — question + options
    "case": ["presentation", "diagnosis", "management", "teaching_points"],
    "image": ["caption", "description"],
    "anatomy_3d": ["caption", "description"],
    "flashcard": ["question", "answer"],
    "dosage_table": ["drug_name", "clinical_warning"],
    # dosage_table rows: drug, route, warning — handled specially
}


# ── Main entry point ──────────────────────────────────────────────────────────

async def schedule_lesson_translations(lesson_id: UUID, db: AsyncSession) -> None:
    """Create pending translation records and kick off background tasks.
    Called immediately after a lesson is published.
    """
    lesson = await db.get(Lesson, lesson_id)
    if not lesson:
        return

    for locale in SUPPORTED_LOCALES:
        # Upsert: if translation already exists, reset to pending
        existing = await db.get(LessonTranslation, (lesson_id, locale))
        if existing:
            existing.status = "pending"
            existing.error_message = None
        else:
            db.add(LessonTranslation(
                lesson_id=lesson_id,
                locale=locale,
                title=lesson.title,          # placeholder — overwritten on completion
                content_json=lesson.content,  # placeholder
                status="pending",
            ))
    await db.commit()

    # Fire-and-forget background task (doesn't block HTTP response)
    asyncio.create_task(_translate_lesson_all_locales(lesson_id))

    logger.info("Scheduled translations for lesson %s → %s", lesson_id, SUPPORTED_LOCALES)


async def schedule_module_translations(module_id: UUID, db: AsyncSession) -> None:
    """Translate module title + description. Called when module is published."""
    module = await db.get(Module, module_id)
    if not module:
        return

    for locale in SUPPORTED_LOCALES:
        existing = await db.get(ModuleTranslation, (module_id, locale))
        if existing:
            existing.status = "pending"
        else:
            db.add(ModuleTranslation(
                module_id=module_id,
                locale=locale,
                title=module.title,
                description=module.description,
                status="pending",
            ))
    await db.commit()
    asyncio.create_task(_translate_module_all_locales(module_id))


# ── Internal async workers ────────────────────────────────────────────────────

async def _translate_lesson_all_locales(lesson_id: UUID) -> None:
    """Run sequentially to avoid hammering Anthropic API."""
    async with AsyncSessionLocal() as db:
        lesson = await db.get(Lesson, lesson_id)
        if not lesson:
            return
        for locale in SUPPORTED_LOCALES:
            await _translate_lesson_one(lesson, locale, db)


async def _translate_module_all_locales(module_id: UUID) -> None:
    async with AsyncSessionLocal() as db:
        module = await db.get(Module, module_id)
        if not module:
            return
        for locale in SUPPORTED_LOCALES:
            await _translate_module_one(module, locale, db)


async def _translate_lesson_one(lesson: Lesson, locale: str, db: AsyncSession) -> None:
    """Translate a single lesson into one locale and persist."""
    tr = await db.get(LessonTranslation, (lesson.id, locale))
    if not tr:
        return

    tr.status = "translating"
    await db.commit()

    try:
        translated_title, translated_blocks = await _translate_lesson_content(
            title=lesson.title,
            blocks=lesson.content if isinstance(lesson.content, list) else [],
            locale=locale,
        )
        tr.title = translated_title
        tr.content_json = translated_blocks
        tr.status = "done"
        tr.translated_at = datetime.utcnow()
        tr.error_message = None
    except Exception as exc:
        logger.error("Translation failed lesson=%s locale=%s: %s", lesson.id, locale, exc)
        tr.status = "failed"
        tr.error_message = str(exc)[:500]

    await db.commit()


async def _translate_module_one(module: Module, locale: str, db: AsyncSession) -> None:
    tr = await db.get(ModuleTranslation, (module.id, locale))
    if not tr:
        return

    tr.status = "translating"
    await db.commit()

    try:
        result = await _translate_text_batch(
            texts={"title": module.title, "description": module.description or ""},
            locale=locale,
            context="medical module",
        )
        tr.title = result.get("title", module.title)
        tr.description = result.get("description")
        tr.status = "done"
        tr.translated_at = datetime.utcnow()
    except Exception as exc:
        logger.error("Module translation failed module=%s locale=%s: %s", module.id, locale, exc)
        tr.status = "failed"

    await db.commit()


# ── Core translation logic ────────────────────────────────────────────────────

async def _translate_lesson_content(
    title: str,
    blocks: list[dict],
    locale: str,
) -> tuple[str, list[dict]]:
    """Translate lesson title and all text blocks into target locale.
    Returns (translated_title, translated_blocks).
    """
    lang_name = LOCALE_NAMES[locale]
    hints = MEDICAL_HINTS.get(locale, "")

    # Extract only the translatable text from blocks
    extraction = _extract_translatable(blocks)
    if not extraction["texts"]:
        # Nothing to translate — return originals
        return title, blocks

    system_prompt = f"""You are a professional medical translator specialising in clinical education content.
Translate from English to {lang_name}.

Rules:
1. {hints}
2. Preserve ALL JSON keys exactly — only translate the VALUES.
3. Do NOT translate: drug names (INN/generic), gene names, species names, units (mg, kg, mL), lab values, diagnostic codes (ICD-10).
4. Preserve markdown formatting (**, *, #, -, >) in translated text.
5. Keep numbers, percentages, and ranges unchanged.
6. Medical abbreviations: either keep original or add translated equivalent in parentheses.
7. Return ONLY valid JSON — no explanation, no markdown code fences.

You will receive a JSON object with string values to translate.
Return a JSON object with the same keys and translated values."""

    payload = json.dumps({"title": title, **extraction["texts"]}, ensure_ascii=False)

    translated_raw = await _call_translation_api(system_prompt, payload)
    translated_map: dict[str, Any] = _parse_json_response(translated_raw, {"title": title})

    translated_title = translated_map.pop("title", title)
    translated_blocks = _apply_translations(blocks, extraction["key_map"], translated_map)

    return translated_title, translated_blocks


def _parse_json_response(raw: str, fallback: dict) -> dict:
    """Parse JSON from Claude response, stripping markdown code fences if present."""
    text = raw.strip()
    # Strip ```json ... ``` or ``` ... ``` wrappers
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```) and last line (```)
        inner_lines = lines[1:]
        if inner_lines and inner_lines[-1].strip() == "```":
            inner_lines = inner_lines[:-1]
        text = "\n".join(inner_lines).strip()
    try:
        return json.loads(text)
    except Exception:
        # Try to extract JSON object from anywhere in the text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(text[start:end])
            except Exception:
                pass
    return fallback


async def _translate_text_batch(
    texts: dict[str, str],
    locale: str,
    context: str = "medical education",
) -> dict[str, str]:
    """Generic batch text translation. Returns same-keyed dict with translated values."""
    lang_name = LOCALE_NAMES[locale]
    hints = MEDICAL_HINTS.get(locale, "")

    system_prompt = f"""Professional medical translator, English to {lang_name}.
{hints}
Preserve all JSON keys. Return ONLY valid JSON with translated values."""

    payload = json.dumps(texts, ensure_ascii=False)
    raw = await _call_translation_api(system_prompt, payload)
    return _parse_json_response(raw, texts)


_claude_unavailable = False  # Set True after first credit error to skip future Claude calls


async def _call_translation_api(system_prompt: str, user_content: str) -> str:
    """Call Claude Haiku for translation. Falls back to Ollama on any error."""
    global _claude_unavailable
    if settings.ANTHROPIC_API_KEY and not _claude_unavailable:
        try:
            msg = await _claude.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
            )
            return msg.content[0].text
        except Exception as e:
            err_str = str(e)
            if "credit balance" in err_str or "insufficient_quota" in err_str:
                _claude_unavailable = True
                logger.warning("Claude credits exhausted — switching to Ollama for all translations")
            else:
                logger.warning("Claude translation failed, falling back to Ollama: %s", e)

    # Fallback: Ollama (local) — retry with smaller payload on timeout
    try:
        return await _call_ollama_translation(system_prompt, user_content)
    except Exception as e:
        if "Timeout" in type(e).__name__ and len(user_content) > 500:
            # Retry with truncated content (first half)
            half = user_content[: len(user_content) // 2]
            logger.warning("Ollama timeout, retrying with truncated payload (%d chars)", len(half))
            return await _call_ollama_translation(system_prompt, half)
        raise


async def _call_ollama_translation(system_prompt: str, user_content: str) -> str:
    # Prepend /no_think to force qwen3 to skip reasoning and reply directly
    no_think_prompt = "/no_think\n" + system_prompt
    async with httpx.AsyncClient(timeout=120) as http:
        resp = await http.post(
            f"{settings.OLLAMA_URL}/api/chat",
            json={
                "model": settings.OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": no_think_prompt},
                    {"role": "user", "content": user_content},
                ],
                "stream": False,
                "think": False,
                "options": {"temperature": 0.1, "num_predict": 256},
            },
        )
        resp.raise_for_status()
        raw = resp.json()["message"]["content"]
        import re
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        return raw


# ── Block extraction / injection helpers ──────────────────────────────────────

def _extract_translatable(blocks: list[dict]) -> dict:
    """Extract all translatable text from blocks into a flat dict for batch translation.

    Returns:
        {
          "texts": {"block_0_content": "...", "block_2_question": "..."},
          "key_map": {"block_0_content": (0, "content"), ...}
        }
    """
    texts: dict[str, str] = {}
    key_map: dict[str, tuple] = {}

    for i, block in enumerate(blocks):
        btype = block.get("type", "")
        content = block.get("content", {})
        if not isinstance(content, dict):
            continue

        if btype == "text":
            _add_field(texts, key_map, i, content, "content")

        elif btype == "quiz":
            _add_field(texts, key_map, i, content, "question")
            opts = content.get("options", [])
            for j, opt in enumerate(opts):
                if isinstance(opt, dict) and "text" in opt:
                    key = f"block_{i}_opt_{j}_text"
                    texts[key] = opt["text"]
                    key_map[key] = (i, "options", j, "text")
            _add_field(texts, key_map, i, content, "explanation")

        elif btype == "case":
            for field in ["presentation", "diagnosis", "management_summary"]:
                _add_field(texts, key_map, i, content, field)
            tps = content.get("teaching_points", [])
            if isinstance(tps, list):
                for j, tp in enumerate(tps):
                    if isinstance(tp, str) and tp:
                        key = f"block_{i}_tp_{j}"
                        texts[key] = tp
                        key_map[key] = (i, "teaching_points", j)

        elif btype == "flashcard":
            _add_field(texts, key_map, i, content, "question")
            _add_field(texts, key_map, i, content, "answer")

        elif btype == "image":
            _add_field(texts, key_map, i, content, "caption")

        elif btype == "anatomy_3d":
            _add_field(texts, key_map, i, content, "caption")

        elif btype == "dosage_table":
            _add_field(texts, key_map, i, content, "drug_name")
            _add_field(texts, key_map, i, content, "clinical_warning")
            rows = content.get("rows", [])
            for j, row in enumerate(rows):
                if isinstance(row, dict):
                    for field in ["warning"]:
                        if row.get(field):
                            key = f"block_{i}_row_{j}_{field}"
                            texts[key] = row[field]
                            key_map[key] = (i, "rows", j, field)

    return {"texts": texts, "key_map": key_map}


def _add_field(texts: dict, key_map: dict, block_idx: int, content: dict, field: str) -> None:
    val = content.get(field)
    if val and isinstance(val, str) and val.strip():
        key = f"block_{block_idx}_{field}"
        texts[key] = val
        key_map[key] = (block_idx, field)


def _apply_translations(
    blocks: list[dict],
    key_map: dict[str, tuple],
    translated_map: dict[str, str],
) -> list[dict]:
    """Inject translated values back into blocks (deep-copied)."""
    import copy
    result = copy.deepcopy(blocks)

    for flat_key, path in key_map.items():
        translated_val = translated_map.get(flat_key)
        if not translated_val:
            continue

        block_idx = path[0]
        if block_idx >= len(result):
            continue

        content = result[block_idx].get("content", {})
        if not isinstance(content, dict):
            continue

        if len(path) == 2:
            # (block_idx, field)
            content[path[1]] = translated_val

        elif len(path) == 4:
            _, container_field, sub_idx, sub_field = path
            container = content.get(container_field, [])
            if isinstance(container, list) and sub_idx < len(container):
                if isinstance(container[sub_idx], dict):
                    container[sub_idx][sub_field] = translated_val
                elif isinstance(container[sub_idx], str):
                    container[sub_idx] = translated_val

    return result


# ── Article translation ───────────────────────────────────────────────────────

async def schedule_article_translations(article_id: UUID, db: AsyncSession) -> None:
    """Create pending translation records for all locales and kick off background tasks.
    Called when an article is published/approved.
    """
    article = await db.get(Article, article_id)
    if not article:
        return

    for locale in SUPPORTED_LOCALES:
        existing = await db.get(ArticleTranslation, (article_id, locale))
        if existing:
            existing.status = "pending"
            existing.error_message = None
        else:
            db.add(ArticleTranslation(
                article_id=article_id,
                locale=locale,
                title=article.title,
                excerpt=article.excerpt,
                body=article.body or [],
                faq=article.faq,
                status="pending",
            ))
    await db.commit()

    asyncio.create_task(_translate_article_all_locales(article_id))
    logger.info("Scheduled article translations for %s → %s", article_id, SUPPORTED_LOCALES)


async def _translate_article_all_locales(article_id: UUID) -> None:
    async with AsyncSessionLocal() as db:
        article = await db.get(Article, article_id)
        if not article:
            return
        for locale in SUPPORTED_LOCALES:
            await _translate_article_one(article, locale, db)


async def _translate_article_one(article: Article, locale: str, db: AsyncSession) -> None:
    tr = await db.get(ArticleTranslation, (article.id, locale))
    if not tr:
        return

    tr.status = "translating"
    await db.commit()

    try:
        texts = {
            "title": article.title,
            "excerpt": article.excerpt,
        }
        translated_meta = await _translate_text_batch(texts, locale, context="medical article")

        translated_body = await _translate_article_body(article.body or [], locale)
        translated_faq = await _translate_article_faq(article.faq or [], locale)

        tr.title = translated_meta.get("title", article.title)
        tr.excerpt = translated_meta.get("excerpt", article.excerpt)
        tr.body = translated_body
        tr.faq = translated_faq if translated_faq else article.faq
        tr.status = "done"
        tr.translated_at = datetime.utcnow()
        tr.error_message = None
    except Exception as exc:
        err_msg = f"{type(exc).__name__}: {exc}"
        logger.error("Article translation failed article=%s locale=%s: %s", article.id, locale, err_msg)
        tr.status = "failed"
        tr.error_message = err_msg[:500]

    await db.commit()


def _extract_body_texts(blocks: list[dict]) -> tuple[dict, dict]:
    """Extract translatable texts from body blocks into flat dicts."""
    texts: dict[str, str] = {}
    key_map: dict[str, tuple] = {}
    for i, block in enumerate(blocks):
        btype = block.get("type", "")
        if btype in ("h2", "h3", "p", "callout"):
            val = block.get("content", "")
            if val and isinstance(val, str):
                key = f"b{i}_content"
                texts[key] = val
                key_map[key] = (i, "content")
        elif btype == "ul":
            for j, item in enumerate(block.get("items", [])):
                if item and isinstance(item, str):
                    key = f"b{i}_item{j}"
                    texts[key] = item
                    key_map[key] = (i, "items", j)
        elif btype == "table":
            for j, h in enumerate(block.get("headers", [])):
                if h and isinstance(h, str):
                    key = f"b{i}_hdr{j}"
                    texts[key] = h
                    key_map[key] = (i, "headers", j)
            for j, row in enumerate(block.get("rows", [])):
                for k, cell in enumerate(row):
                    if cell and isinstance(cell, str):
                        key = f"b{i}_r{j}c{k}"
                        texts[key] = cell
                        key_map[key] = (i, "rows", j, k)
        elif btype == "image":
            for field in ("caption", "alt"):
                val = block.get(field, "")
                if val and isinstance(val, str):
                    key = f"b{i}_{field}"
                    texts[key] = val
                    key_map[key] = (i, field)
    return texts, key_map


async def _translate_article_body(blocks: list[dict], locale: str) -> list[dict]:
    """Translate article body blocks in chunks to avoid Ollama timeouts on large articles."""
    import copy
    if not blocks:
        return blocks

    texts, key_map = _extract_body_texts(blocks)
    if not texts:
        return blocks

    # Keep chunks small: ~600 chars ≈ 100 words ≈ 80-120 output tokens ≈ 40-60s on CPU
    CHUNK_CHAR_LIMIT = 600
    chunks: list[dict] = []
    current_chunk: dict = {}
    current_size = 0
    for key, val in texts.items():
        val_size = len(val)
        if current_chunk and current_size + val_size > CHUNK_CHAR_LIMIT:
            chunks.append(current_chunk)
            current_chunk = {}
            current_size = 0
        current_chunk[key] = val
        current_size += val_size
    if current_chunk:
        chunks.append(current_chunk)

    # Translate each chunk and merge
    translated: dict = {}
    for chunk in chunks:
        result = await _translate_text_batch(chunk, locale, context="medical article body")
        translated.update(result)

    result = copy.deepcopy(blocks)
    for flat_key, path in key_map.items():
        val = translated.get(flat_key)
        if not val:
            continue
        i = path[0]
        if i >= len(result):
            continue
        if len(path) == 2:
            result[i][path[1]] = val
        elif len(path) == 3:  # ul items
            items = result[i].get(path[1], [])
            if path[2] < len(items):
                items[path[2]] = val
        elif len(path) == 4:  # table rows
            rows = result[i].get(path[1], [])
            if path[2] < len(rows) and path[3] < len(rows[path[2]]):
                rows[path[2]][path[3]] = val

    return result


async def _translate_article_faq(faq: list[dict], locale: str) -> list[dict]:
    if not faq:
        return faq

    texts: dict[str, str] = {}
    for i, item in enumerate(faq):
        if item.get("question"):
            texts[f"faq{i}_q"] = item["question"]
        if item.get("answer"):
            texts[f"faq{i}_a"] = item["answer"]

    if not texts:
        return faq

    translated = await _translate_text_batch(texts, locale, context="medical FAQ")

    import copy
    result = copy.deepcopy(faq)
    for i, item in enumerate(result):
        if translated.get(f"faq{i}_q"):
            item["question"] = translated[f"faq{i}_q"]
        if translated.get(f"faq{i}_a"):
            item["answer"] = translated[f"faq{i}_a"]
    return result


# ── Re-translation utility (for admin/teacher use) ────────────────────────────

async def retranslate_lesson(lesson_id: UUID, locale: str, db: AsyncSession) -> LessonTranslation:
    """Force re-translation of a specific lesson+locale. Returns updated record."""
    lesson = await db.get(Lesson, lesson_id)
    if not lesson:
        raise ValueError(f"Lesson {lesson_id} not found")

    tr = await db.get(LessonTranslation, (lesson_id, locale))
    if not tr:
        tr = LessonTranslation(
            lesson_id=lesson_id,
            locale=locale,
            title=lesson.title,
            content_json=lesson.content,
            status="pending",
        )
        db.add(tr)
        await db.commit()

    await _translate_lesson_one(lesson, locale, db)
    await db.refresh(tr)
    return tr
