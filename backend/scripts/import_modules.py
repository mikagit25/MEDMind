"""
Import 70+ JSON modules from /data/modules/ (or /Volumes/one/MEDMind/Modules/) into the database.

Usage:
    cd backend
    python -m scripts.import_modules                         # auto-detect Modules/ dir
    python -m scripts.import_modules --dir /path/to/modules  # explicit path
    python -m scripts.import_modules --dry-run               # validate without writing

Idempotent: re-running updates existing records, never duplicates.
When multiple files share the same module code (e.g. CARDIO-007.json and
CARDIO-007-1.json), the file that sorts LAST alphabetically wins (newest revision).
"""

import argparse
import asyncio
import json
import logging
import os
import sys
import uuid
from collections import defaultdict
from pathlib import Path

# Allow running as `python -m scripts.import_modules` from backend/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import settings
from app.models.models import (
    Base, Specialty, Module, Lesson, Flashcard, MCQQuestion, ClinicalCase,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("import")

# ─────────────────────────────────────────────
# Mappings
# ─────────────────────────────────────────────

LEVEL_MAP: dict[str, int] = {
    "foundation": 1,
    "beginner": 1,
    "basic": 1,
    "intermediate": 2,
    "advanced": 3,
    "expert": 4,
    "master": 5,
}

# specialty name (as it appears in JSON) → (code, name_ru, name_en, icon)
SPECIALTY_CATALOG: dict[str, tuple[str, str, str, str]] = {
    "Кардиология":                ("cardiology",      "Кардиология",                  "Cardiology",               "🫀"),
    "Терапия":                    ("therapy",         "Терапия",                      "Internal Medicine",         "🩺"),
    "Неврология":                 ("neurology",       "Неврология",                   "Neurology",                 "🧠"),
    "Хирургия":                   ("surgery",         "Хирургия",                     "Surgery",                   "🔪"),
    "Педиатрия":                  ("pediatrics",      "Педиатрия",                    "Pediatrics",                "👶"),
    "Акушерство и гинекология":   ("obstetrics",      "Акушерство и гинекология",     "Obstetrics & Gynecology",   "🤱"),
    "Anatomy & Physiology":       ("anatomy",         "Анатомия и физиология",        "Anatomy & Physiology",      "🦴"),
    "Physiology":                 ("physiology",      "Физиология",                   "Physiology",                "⚗️"),
    "Pharmacology":               ("pharmacology",    "Фармакология",                 "Pharmacology",              "💊"),
    "Clinical Diagnostics":       ("diagnostics",     "Клиническая диагностика",      "Clinical Diagnostics",      "🔬"),
    "Veterinary":                 ("veterinary",      "Ветеринария",                  "Veterinary Medicine",       "🐾"),
    "Emergency Medicine":         ("emergency",       "Неотложная медицина",          "Emergency Medicine",        "🚑"),
}


def resolve_specialty_key(meta: dict) -> str:
    """Return the SPECIALTY_CATALOG key for a module's meta dict."""
    return meta.get("specialty") or meta.get("subject") or "Clinical Diagnostics"


def level_int(meta: dict) -> int:
    raw = str(meta.get("level", "intermediate")).lower()
    return LEVEL_MAP.get(raw, 2)


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def pick_best_files(module_dir: Path) -> dict[str, Path]:
    """
    Return {code: best_path} — for duplicates, the last alphabetically wins.
    Skips files that are not valid JSON or lack meta.id.
    """
    candidates: dict[str, list[Path]] = defaultdict(list)
    for f in sorted(module_dir.glob("module_*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            code = data["meta"]["id"]
            candidates[code].append(f)
        except Exception as exc:
            log.warning("Skip %s: %s", f.name, exc)
    # last alphabetically = highest suffix number = newest revision
    return {code: sorted(paths)[-1] for code, paths in candidates.items()}


# ─────────────────────────────────────────────
# Database helpers
# ─────────────────────────────────────────────

async def ensure_specialty(
    db: AsyncSession,
    spec_key: str,
    cache: dict[str, uuid.UUID],
) -> uuid.UUID:
    if spec_key in cache:
        return cache[spec_key]

    catalog_entry = SPECIALTY_CATALOG.get(spec_key)
    if not catalog_entry:
        log.warning("Unknown specialty key '%s', using 'diagnostics'", spec_key)
        spec_key = "Clinical Diagnostics"
        catalog_entry = SPECIALTY_CATALOG[spec_key]

    code, name_ru, name_en, icon = catalog_entry
    result = await db.execute(select(Specialty).where(Specialty.code == code))
    spec = result.scalar_one_or_none()

    if spec is None:
        spec = Specialty(
            code=code,
            name=name_ru,
            name_en=name_en,
            icon=icon,
            is_veterinary=(code == "veterinary"),
            is_active=True,
        )
        db.add(spec)
        await db.flush()
        log.info("  Created specialty: %s (%s)", name_ru, code)

    cache[spec_key] = spec.id
    return spec.id


async def upsert_module(
    db: AsyncSession,
    data: dict,
    specialty_id: uuid.UUID,
) -> Module:
    meta = data["meta"]
    code = meta["id"]

    result = await db.execute(select(Module).where(Module.code == code))
    mod = result.scalar_one_or_none()

    level = level_int(meta)
    is_fundamental = code.startswith("BASE-")

    if mod is None:
        mod = Module(code=code)
        db.add(mod)

    mod.specialty_id = specialty_id
    mod.title = meta.get("title", code)
    mod.title_en = meta.get("title_en")
    mod.level = level
    mod.level_label = meta.get("level", "intermediate")
    mod.module_order = meta.get("order_in_specialty", 0)
    mod.duration_hours = float(meta.get("duration_hours", 1))
    mod.is_fundamental = is_fundamental
    mod.prerequisite_codes = meta.get("prerequisite_modules", [])
    mod.content = data  # full JSON stored as JSONB
    mod.is_published = True

    await db.flush()
    return mod


async def import_lessons(db: AsyncSession, mod: Module, lessons_data: list[dict]) -> int:
    await db.execute(delete(Lesson).where(Lesson.module_id == mod.id))
    count = 0
    for idx, ls in enumerate(lessons_data):
        lesson_content = ls.get("content", ls)
        db.add(Lesson(
            module_id=mod.id,
            lesson_code=ls.get("id", f"L{idx+1:03d}"),
            title=ls.get("title", f"Lesson {idx+1}"),
            lesson_order=ls.get("order", idx + 1),
            content=lesson_content,
            estimated_minutes=int(float(ls.get("duration_minutes", 20))),
        ))
        count += 1
    return count


async def import_flashcards(db: AsyncSession, mod: Module, cards_data: list[dict]) -> int:
    await db.execute(delete(Flashcard).where(Flashcard.module_id == mod.id))
    count = 0
    for fc in cards_data:
        db.add(Flashcard(
            module_id=mod.id,
            question=fc.get("question", ""),
            answer=fc.get("answer", ""),
            difficulty=fc.get("difficulty", "medium"),
            category=fc.get("category"),
        ))
        count += 1
    return count


async def import_mcq(db: AsyncSession, mod: Module, mcq_data: list[dict]) -> int:
    await db.execute(delete(MCQQuestion).where(MCQQuestion.module_id == mod.id))
    count = 0
    for q in mcq_data:
        db.add(MCQQuestion(
            module_id=mod.id,
            question=q.get("question", ""),
            options=q.get("options", {}),
            correct=str(q.get("correct", "A")),
            explanation=q.get("explanation"),
            difficulty=q.get("difficulty", "medium"),
        ))
        count += 1
    return count


async def import_cases(db: AsyncSession, mod: Module, cases_data: list[dict]) -> int:
    await db.execute(delete(ClinicalCase).where(ClinicalCase.module_id == mod.id))
    count = 0
    for case in cases_data:
        presentation_raw = case.get("presentation", {})
        if isinstance(presentation_raw, dict):
            chief = presentation_raw.get("chief_complaint", "")
            history = presentation_raw.get("history", "")
            presentation_text = f"{chief}\n{history}".strip()
            vitals = presentation_raw.get("vitals")
        else:
            presentation_text = str(presentation_raw)
            vitals = None

        management = case.get("management", [])
        if isinstance(management, str):
            management = [management]

        db.add(ClinicalCase(
            module_id=mod.id,
            title=case.get("title", "Clinical Case"),
            specialty=mod.title,
            presentation=presentation_text or "See full case.",
            vitals=vitals,
            diagnosis=case.get("diagnosis", ""),
            management=management,
            teaching_points=case.get("teaching_points", []),
            content=case,
            difficulty=case.get("difficulty", "medium"),
        ))
        count += 1
    return count


# ─────────────────────────────────────────────
# Main import loop
# ─────────────────────────────────────────────

async def run_import(module_dir: Path, dry_run: bool = False) -> None:
    best_files = pick_best_files(module_dir)
    total = len(best_files)
    log.info("Found %d unique modules in %s", total, module_dir)

    if dry_run:
        # Validate only — parse every file, report issues, no DB needed
        ok = 0
        errors = 0
        for i, (code, path) in enumerate(sorted(best_files.items()), 1):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                meta = data["meta"]
                assert "id" in meta, "meta.id missing"
                log.info(
                    "[%02d/%d] ✓ %s — %d lessons, %d cards, %d MCQ, %d cases",
                    i, total, code,
                    len(data.get("lessons", [])),
                    len(data.get("flashcards", [])),
                    len(data.get("mcq_questions", [])),
                    len(data.get("clinical_cases", [])),
                )
                ok += 1
            except Exception as exc:
                log.error("[%02d/%d] ✗ %s — %s", i, total, code, exc)
                errors += 1
        log.info("─" * 50)
        log.info("Dry-run done: %d valid, %d errors", ok, errors)
        if errors:
            sys.exit(1)
        return

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    specialty_cache: dict[str, uuid.UUID] = {}
    ok = 0
    errors = 0

    async with Session() as db:
        for i, (code, path) in enumerate(sorted(best_files.items()), 1):
            prefix = f"[{i:02d}/{total}]"
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                meta = data["meta"]

                spec_key = resolve_specialty_key(meta)
                specialty_id = await ensure_specialty(db, spec_key, specialty_cache)

                mod = await upsert_module(db, data, specialty_id)

                n_lessons   = await import_lessons(db, mod, data.get("lessons", []))
                n_cards     = await import_flashcards(db, mod, data.get("flashcards", []))
                n_mcq       = await import_mcq(db, mod, data.get("mcq_questions", []))
                n_cases     = await import_cases(db, mod, data.get("clinical_cases", []))

                if not dry_run:
                    await db.commit()

                log.info(
                    "%s ✓ %s — %d lessons, %d flashcards, %d MCQ, %d cases",
                    prefix, code, n_lessons, n_cards, n_mcq, n_cases,
                )
                ok += 1

            except Exception as exc:
                await db.rollback()
                log.error("%s ✗ %s — %s", prefix, code, exc)
                errors += 1

        # Update specialty module counts
        if not dry_run:
            for spec_key, spec_id in specialty_cache.items():
                result = await db.execute(
                    select(Specialty).where(Specialty.id == spec_id)
                )
                spec = result.scalar_one_or_none()
                if spec:
                    count_result = await db.execute(
                        select(Module).where(
                            Module.specialty_id == spec_id,
                            Module.is_published == True,
                        )
                    )
                    spec.module_count = len(count_result.scalars().all())
            await db.commit()

    await engine.dispose()

    log.info("─" * 50)
    log.info("Done: %d imported, %d errors (dry_run=%s)", ok, errors, dry_run)
    if errors:
        sys.exit(1)


# ─────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────

def find_modules_dir() -> Path:
    """Try common locations for the modules directory."""
    candidates = [
        Path(__file__).resolve().parent.parent / "data" / "modules",
        Path("/Volumes/one/MEDMind/Modules"),
        Path(__file__).resolve().parent.parent.parent / "Modules",
    ]
    for p in candidates:
        if p.exists() and list(p.glob("module_*.json")):
            return p
    raise FileNotFoundError(
        "Modules directory not found. Pass --dir explicitly.\n"
        f"Searched: {[str(p) for p in candidates]}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import JSON modules into MedMind DB")
    parser.add_argument("--dir", help="Path to directory containing module_*.json files")
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing to DB")
    args = parser.parse_args()

    module_dir = Path(args.dir) if args.dir else find_modules_dir()
    asyncio.run(run_import(module_dir, dry_run=args.dry_run))
