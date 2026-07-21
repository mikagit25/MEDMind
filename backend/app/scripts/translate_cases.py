"""
Translate Russian clinical cases to EN and other locales using Claude Haiku.

Usage:
  python -m app.scripts.translate_cases                      # all locales
  python -m app.scripts.translate_cases --locale en          # only EN
  python -m app.scripts.translate_cases --limit 10           # first 10 cases
  python -m app.scripts.translate_cases --dry-run            # preview only
  python -m app.scripts.translate_cases --force              # overwrite existing

Translates from Russian → [en, de, fr, es, tr, ar] in one API call per case.
Only processes cases where title contains Cyrillic characters (= Russian originals).
"""
import argparse
import asyncio
import json
import logging
import re
import sys
import uuid
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

TARGET_LOCALES = ["en", "de", "fr", "es", "tr", "ar"]
LOCALE_NAMES = {
    "en": "English",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "tr": "Turkish",
    "ar": "Arabic",
}

SYSTEM_PROMPT = """You are a professional medical translator specialising in clinical case studies.
Translate Russian medical content into multiple languages simultaneously.
Rules:
- Preserve all medical terminology accurately; use standard medical terms in the target language
- Keep JSON structure intact (only translate string values, not keys)
- Do not add, remove or rearrange items in arrays
- Return only valid JSON with no markdown fences
- Numbers, units, drug doses, abbreviations (e.g. BP, HR, SpO2) stay as-is
- For Arabic: use RTL-appropriate medical Arabic terminology"""

def _build_prompt(case: ClinicalCase, locales: list[str]) -> str:
    locale_list = ", ".join(f"{l} ({LOCALE_NAMES[l]})" for l in locales)
    case_data = {
        "title": case.title,
        "presentation": case.presentation,
        "teaching_points": case.teaching_points or [],
        "management": case.management or [],
    }
    return (
        f"Translate this Russian clinical case into: {locale_list}.\n\n"
        "Return JSON object where each key is a locale code, value is the translated case:\n"
        '{\n  "en": {"title": "...", "presentation": {...}, "teaching_points": [...], "management": [...]},\n'
        '  "de": {"title": "...", ...},\n  ...\n}\n\n'
        f"Russian source:\n{json.dumps(case_data, ensure_ascii=False, indent=2)}"
    )

def _parse_response(raw: str) -> dict[str, Any] | None:
    raw = raw.strip()
    # Strip markdown fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    # Extract JSON object from anywhere in the response (handles preamble text)
    match = re.search(r"\{[\s\S]*\}", raw)
    if match:
        raw = match.group(0)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        log.warning("JSON parse error: %s — raw: %s…", e, raw[:200])
        return None

async def _call_ollama(system: str, user: str) -> str:
    """Call local Ollama as fallback."""
    async with httpx.AsyncClient(timeout=180) as http:
        resp = await http.post(
            f"{settings.OLLAMA_URL}/api/chat",
            json={
                "model": "qwen3:8b",
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 4096},
                "messages": [
                    {"role": "system", "content": "/no_think\n" + system},
                    {"role": "user", "content": user},
                ],
            },
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]


async def _call_groq(system: str, user: str) -> str:
    """Call Groq API with key rotation on 429, falling back to Ollama."""
    global _key_index
    keys = _get_groq_keys()
    tried = 0
    async with httpx.AsyncClient(timeout=120) as http:
        while tried < len(keys):
            api_key = keys[_key_index % len(keys)]
            resp = await http.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": settings.GROQ_MODEL,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "max_tokens": 4096,
                    "temperature": 0.1,
                },
            )
            if resp.status_code == 429:
                log.warning("Key #%d rate limited — rotating", _key_index % len(keys))
                _key_index += 1
                tried += 1
                await asyncio.sleep(1)
                continue
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    # All Groq keys exhausted — fall back to Ollama
    log.info("All Groq keys rate-limited — using local Ollama")
    return await _call_ollama(system, user)


def _get_groq_keys() -> list[str]:
    """Content pipeline pool — KEY_4 reserved for articles, KEY_5 for news."""
    keys = []
    for attr in ("GROQ_KEY_CASES", "GROQ_API_KEY_3", "GROQ_API_KEY_6", "GROQ_KEY_MODULE_2", "GROQ_KEY_VET_MODULES"):
        k = getattr(settings, attr, "")
        if k:
            keys.append(k)
    if not keys:
        raise RuntimeError("No Groq keys configured for case translation (GROQ_KEY_CASES/GROQ_API_KEY_3/4/5)")
    return keys


_key_index = 0


async def _translate_case(
    case: ClinicalCase,
    locales: list[str],
) -> dict[str, Any] | None:
    prompt = _build_prompt(case, locales)
    try:
        raw = await _call_groq(SYSTEM_PROMPT, prompt)
        return _parse_response(raw)
    except Exception as e:
        log.error("API error for case %s (%s): %s", case.id, case.title[:50], e)
        return None

async def _get_existing_locales(db: AsyncSession, case_id: uuid.UUID) -> set[str]:
    result = await db.execute(
        sql_text("SELECT locale FROM clinical_case_translations WHERE case_id = :cid").bindparams(cid=case_id)
    )
    return {row.locale for row in result}

async def _upsert_translation(
    db: AsyncSession,
    case_id: uuid.UUID,
    locale: str,
    data: dict,
    force: bool,
) -> bool:
    """Insert or update a translation row. Returns True if written."""
    title = data.get("title") or ""
    presentation = data.get("presentation")
    teaching_points = data.get("teaching_points") or []
    management = data.get("management") or []

    if not title:
        log.warning("  [%s] Empty title — skipping", locale)
        return False

    # presentation may come back as a JSON-encoded string — parse it
    if isinstance(presentation, str):
        try:
            presentation = json.loads(presentation)
        except json.JSONDecodeError:
            pass  # keep as-is

    # Check if exists
    exists = await db.execute(
        sql_text(
            "SELECT id FROM clinical_case_translations WHERE case_id = :cid AND locale = :loc"
        ).bindparams(cid=case_id, loc=locale)
    )
    row = exists.fetchone()

    if row and not force:
        return False  # already exists

    pres_json = json.dumps(presentation, ensure_ascii=False) if presentation else None
    # Build text[] literals for PostgreSQL
    def to_pg_array(items: list[str]) -> str | None:
        if not items:
            return None
        escaped = [s.replace("\\", "\\\\").replace('"', '\\"') for s in items]
        return "{" + ",".join(f'"{e}"' for e in escaped) + "}"

    tp_arr = to_pg_array(teaching_points)
    mg_arr = to_pg_array(management)

    if row:
        await db.execute(
            sql_text(
                "UPDATE clinical_case_translations "
                "SET title = :title, "
                "    presentation = CAST(:pres_j AS jsonb), "
                "    teaching_points = CAST(:tp_a AS text[]), "
                "    management = CAST(:mg_a AS text[]) "
                "WHERE case_id = :cid AND locale = :loc"
            ).bindparams(title=title, pres_j=pres_json, tp_a=tp_arr, mg_a=mg_arr, cid=case_id, loc=locale)
        )
    else:
        await db.execute(
            sql_text(
                "INSERT INTO clinical_case_translations "
                "    (id, case_id, locale, title, presentation, teaching_points, management, status) "
                "VALUES "
                "    (uuid_generate_v4(), :cid, :loc, :title, "
                "     CAST(:pres_j AS jsonb), CAST(:tp_a AS text[]), CAST(:mg_a AS text[]), 'done')"
            ).bindparams(cid=case_id, loc=locale, title=title, pres_j=pres_json, tp_a=tp_arr, mg_a=mg_arr)
        )
    return True

async def run(
    only_locale: str | None,
    limit: int,
    dry_run: bool,
    force: bool,
    batch_size: int = 5,
) -> None:
    target_locales = [only_locale] if only_locale else TARGET_LOCALES
    if not dry_run:
        keys = _get_groq_keys()
        log.info("Using %d Groq key(s) for translation", len(keys))

    async with AsyncSessionLocal() as db:
        # Fetch all Russian-language cases (Cyrillic title = original Russian content)
        result = await db.execute(
            select(ClinicalCase).order_by(ClinicalCase.specialty, ClinicalCase.title)
        )
        all_cases = result.scalars().all()
        russian_cases = [c for c in all_cases if CYRILLIC.search(c.title or "")]
        log.info("Found %d Russian cases out of %d total", len(russian_cases), len(all_cases))

        if limit:
            russian_cases = russian_cases[:limit]

        done = 0
        skipped = 0
        errors = 0

        for i, case in enumerate(russian_cases):
            existing = await _get_existing_locales(db, case.id)
            needed = [l for l in target_locales if l not in existing or force]
            if not needed:
                log.info("[%d/%d] SKIP %s (all %s already exist)", i + 1, len(russian_cases), case.title[:50], target_locales)
                skipped += 1
                continue

            log.info("[%d/%d] Translating: %s → %s", i + 1, len(russian_cases), case.title[:60], needed)

            if dry_run:
                done += 1
                continue

            translations = await _translate_case(case, needed)
            if not translations:
                log.error("  Translation failed — skipping case")
                errors += 1
                continue

            written = 0
            for locale in needed:
                locale_data = translations.get(locale)
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

            # Delay between requests to stay under Groq rate limit
            await asyncio.sleep(3)  # ~20 req/min — well within free tier limits

    log.info("Done. Translated: %d  Skipped: %d  Errors: %d", done, skipped, errors)

def main() -> None:
    parser = argparse.ArgumentParser(description="Translate Russian clinical cases")
    parser.add_argument("--locale", help="Only translate to this locale (e.g. en)")
    parser.add_argument("--limit", type=int, default=0, help="Max cases to process (0=all)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--force", action="store_true", help="Overwrite existing translations")
    parser.add_argument("--batch-size", type=int, default=5, help="Commit every N cases")
    args = parser.parse_args()

    asyncio.run(run(
        only_locale=args.locale,
        limit=args.limit,
        dry_run=args.dry_run,
        force=args.force,
        batch_size=args.batch_size,
    ))

if __name__ == "__main__":
    main()
