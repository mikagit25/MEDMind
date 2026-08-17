"""Translate English-origin clinical cases to ru, de, fr, es, tr, ar.

Handles cases where the title does NOT contain Cyrillic characters (English source).
Skips locales that already have translations.

Usage:
    python -m app.scripts.translate_cases_en
    python -m app.scripts.translate_cases_en --dry-run
    python -m app.scripts.translate_cases_en --limit 5
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from typing import Any

import httpx
from sqlalchemy import select, text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.models import ClinicalCase

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

CYRILLIC = re.compile(r"[А-Яа-яёЁ]")
TARGET_LOCALES = ["ru", "de", "fr", "es", "tr", "ar"]
LOCALE_NAMES = {
    "ru": "Russian", "de": "German", "fr": "French",
    "es": "Spanish", "tr": "Turkish", "ar": "Arabic",
}

SYSTEM_PROMPT = """You are a professional medical translator specialising in clinical case studies.
Translate English medical content into multiple languages simultaneously.
Rules:
- Preserve all medical terminology accurately; use standard medical terms in the target language
- Keep JSON structure intact (only translate string values, not keys)
- Do not add, remove or rearrange items in arrays
- Return only valid JSON with no markdown fences
- Numbers, units, drug doses, abbreviations (e.g. BP, HR, SpO2) stay as-is
- For Arabic: use RTL-appropriate medical Arabic terminology
- For Russian: use standard Russian medical terminology"""


def _build_prompt(case: ClinicalCase, locales: list[str]) -> str:
    locale_list = ", ".join(f"{l} ({LOCALE_NAMES[l]})" for l in locales)
    case_data = {
        "title": case.title,
        "presentation": case.presentation,
        "teaching_points": case.teaching_points or [],
        "management": case.management or [],
    }
    return (
        f"Translate this English clinical case into: {locale_list}.\n\n"
        "Return JSON object where each key is a locale code, value is the translated case:\n"
        '{\n  "ru": {"title": "...", "presentation": {...}, "teaching_points": [...], "management": [...]},\n'
        '  "de": {"title": "...", ...},\n  ...\n}\n\n'
        f"English source:\n{json.dumps(case_data, ensure_ascii=False, indent=2)}"
    )


def _parse_response(raw: str) -> dict[str, Any] | None:
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    match = re.search(r"\{[\s\S]*\}", raw)
    if match:
        raw = match.group(0)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        log.warning("JSON parse error: %s — raw: %s", e, raw[:80] if raw else "…")
        return None


def _get_groq_keys() -> list[str]:
    keys = []
    for attr in ("GROQ_KEY_CASES", "GROQ_API_KEY_3", "GROQ_API_KEY_6", "GROQ_KEY_MODULE_2", "GROQ_KEY_VET_MODULES"):
        k = getattr(settings, attr, "")
        if k:
            keys.append(k)
    if not keys:
        raise RuntimeError("No Groq keys configured")
    return keys


_key_index = 0


async def _call_ollama(prompt: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=300) as http:
            resp = await http.post(
                f"{getattr(settings, 'OLLAMA_URL', 'http://host-gateway:11434')}/api/chat",
                json={
                    "model": "qwen3:1.7b",
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 6000},
                    "messages": [
                        {"role": "system", "content": "/no_think\n" + SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                },
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"]
    except Exception as e:
        log.error("Ollama fallback failed: %s", e)
        return None


async def _translate_case(case: ClinicalCase, locales: list[str]) -> dict[str, Any] | None:
    global _key_index
    keys = _get_groq_keys()
    prompt = _build_prompt(case, locales)
    tried = 0
    async with httpx.AsyncClient(timeout=120) as http:
        while tried < len(keys):
            api_key = keys[_key_index % len(keys)]
            resp = await http.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "openai/gpt-oss-120b",
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 6000,
                    "temperature": 0.1,
                },
            )
            if resp.status_code == 429:
                log.warning("Key #%d rate limited — rotating", _key_index % len(keys))
                _key_index += 1
                tried += 1
                await asyncio.sleep(2)
                continue
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"]
            return _parse_response(raw)
    log.info("All Groq keys rate-limited — using local Ollama")
    raw = await _call_ollama(prompt)
    if raw:
        return _parse_response(raw)
    return None


async def _get_existing_locales(db: AsyncSession, case_id) -> list[str]:
    r = await db.execute(
        sql_text("SELECT locale FROM clinical_case_translations WHERE case_id = CAST(:cid AS uuid)"),
        {"cid": str(case_id)},
    )
    return [row[0] for row in r.fetchall()]


async def _upsert_translation(
    db: AsyncSession, case_id, locale: str, data: dict, force: bool
) -> bool:
    title = data.get("title", "")
    pres = data.get("presentation")
    tp = data.get("teaching_points", [])
    mg = data.get("management", [])
    if not title:
        return False
    pres_json = json.dumps(pres, ensure_ascii=False) if pres else "{}"
    tp_arr = "{" + ",".join(f'"{x.replace(chr(34), chr(39))}"' for x in (tp or [])) + "}"
    mg_arr = "{" + ",".join(f'"{x.replace(chr(34), chr(39))}"' for x in (mg or [])) + "}"
    await db.execute(
        sql_text(
            "INSERT INTO clinical_case_translations "
            "    (id, case_id, locale, title, presentation, teaching_points, management, status) "
            "VALUES "
            "    (uuid_generate_v4(), CAST(:cid AS uuid), :loc, :title, "
            "     CAST(:pres_j AS jsonb), CAST(:tp_a AS text[]), CAST(:mg_a AS text[]), 'done') "
            "ON CONFLICT (case_id, locale) DO UPDATE SET "
            "    title=EXCLUDED.title, presentation=EXCLUDED.presentation, "
            "    teaching_points=EXCLUDED.teaching_points, management=EXCLUDED.management, "
            "    status='done'"
        ).bindparams(cid=str(case_id), loc=locale, title=title, pres_j=pres_json,
                     tp_a=tp_arr, mg_a=mg_arr)
    )
    return True


async def run(limit: int, dry_run: bool, force: bool) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ClinicalCase).order_by(ClinicalCase.specialty, ClinicalCase.title)
        )
        all_cases = result.scalars().all()
        english_cases = [c for c in all_cases if not CYRILLIC.search(c.title or "")]
        log.info("Found %d English cases out of %d total", len(english_cases), len(all_cases))

        if limit:
            english_cases = english_cases[:limit]

    done = skipped = errors = 0
    for i, case in enumerate(english_cases):
        async with AsyncSessionLocal() as db:
            existing = await _get_existing_locales(db, case.id)
        needed = [l for l in TARGET_LOCALES if l not in existing or force]
        if not needed:
            log.info("[%d/%d] SKIP %s (all done)", i + 1, len(english_cases), case.title[:50])
            skipped += 1
            continue

        log.info("[%d/%d] Translating: %s → %s", i + 1, len(english_cases), case.title[:60], needed)
        if dry_run:
            done += 1
            continue

        # Translate in batches of 3 to stay within the model's context window
        batches = [needed[j:j + 3] for j in range(0, len(needed), 3)]
        all_translations: dict[str, Any] = {}
        batch_error = False
        for batch in batches:
            result = await _translate_case(case, batch)
            if not result:
                log.error("  Translation batch %s failed", batch)
                batch_error = True
                break
            all_translations.update(result)
            await asyncio.sleep(2)

        if batch_error and not all_translations:
            errors += 1
            continue

        written = 0
        async with AsyncSessionLocal() as db:
            for locale in needed:
                locale_data = all_translations.get(locale)
                if not locale_data:
                    log.warning("  [%s] No data in response", locale)
                    continue
                ok = await _upsert_translation(db, case.id, locale, locale_data, force)
                if ok:
                    written += 1
                    log.info("  [%s] ✓ %s", locale, locale_data.get("title", "")[:60])
            if written:
                await db.commit()
                done += 1
            else:
                log.warning("  Nothing written for case %s", case.id)

    log.info("Done. Translated: %d  Skipped: %d  Errors: %d", done, skipped, errors)


def main() -> None:
    parser = argparse.ArgumentParser(description="Translate English clinical cases")
    parser.add_argument("--limit", type=int, default=0, help="Max cases to process (0=all)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--force", action="store_true", help="Overwrite existing translations")
    args = parser.parse_args()
    asyncio.run(run(limit=args.limit, dry_run=args.dry_run, force=args.force))


if __name__ == "__main__":
    main()
