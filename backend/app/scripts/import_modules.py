"""
Module import script — reads all module_*.json files and imports them into the database.
Idempotent: re-running updates existing records, never duplicates.
Usage: python -m app.scripts.import_modules
"""
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

from app.core.config import settings
from app.models.models import Specialty, Module, Lesson, Flashcard, MCQQuestion, ClinicalCase

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Level mapping
LEVEL_MAP = {
    "basic": 1, "beginner": 1, "foundation": 1,
    "elementary": 2,
    "intermediate": 3,
    "advanced": 4,
    "expert": 5,
}

# Specialty name → specialty code in DB
SPECIALTY_CODE_MAP = {
    "Кардиология": "cardiology",
    "Терапия": "therapy",
    "Internal Medicine": "therapy",
    "Неврология": "neurology",
    "Хирургия": "surgery",
    "Педиатрия": "pediatrics",
    "Акушерство и гинекология": "obstetrics",
    "Акушерство": "obstetrics",
    "Базовые дисциплины": "pharmacology",
    "Foundations": "pharmacology",
    "Фармакология": "pharmacology",
    "Психиатрия": "therapy",
    "Анестезиология": "surgery",
    "Онкология": "therapy",
    "Дерматология": "therapy",
    "Veterinary": "veterinary",
    "Ветеринария": "veterinary",
}


async def get_specialty_id(db: AsyncSession, specialty_name: str) -> str | None:
    code = SPECIALTY_CODE_MAP.get(specialty_name)
    if not code:
        # Try by name
        result = await db.execute(select(Specialty).where(Specialty.name == specialty_name))
        spec = result.scalar_one_or_none()
        return str(spec.id) if spec else None

    result = await db.execute(select(Specialty).where(Specialty.code == code))
    spec = result.scalar_one_or_none()
    return str(spec.id) if spec else None


async def import_module(db: AsyncSession, file_path: Path) -> bool:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        meta = data.get("meta", {})
        module_code = meta.get("id") or meta.get("code")
        if not module_code:
            logger.warning(f"No module ID in {file_path.name}, skipping")
            return False

        specialty_name = meta.get("specialty", "")
        specialty_id = await get_specialty_id(db, specialty_name)

        level_str = str(meta.get("level", "intermediate")).lower()
        level_int = LEVEL_MAP.get(level_str, 3)

        is_fundamental = module_code.startswith("BASE-")
        is_vet = module_code.startswith("VET-")

        # Check if module already exists
        existing = await db.execute(select(Module).where(Module.code == module_code))
        module = existing.scalar_one_or_none()

        if module:
            logger.info(f"Updating existing module: {module_code}")
        else:
            module = Module(code=module_code)
            db.add(module)

        module.title = meta.get("title", module_code)
        module.title_en = meta.get("title_en")
        module.specialty_id = specialty_id
        module.level = level_int
        module.level_label = meta.get("level", "intermediate")
        module.module_order = meta.get("order_in_specialty", 0)
        module.duration_hours = meta.get("duration_hours", 0)
        module.is_fundamental = is_fundamental
        module.is_veterinary = is_vet
        module.prerequisite_codes = meta.get("prerequisite_modules", [])
        module.content = data
        module.is_published = True

        await db.flush()

        # Remove and re-import lessons, flashcards, MCQ, cases
        # (simpler than diffing — if module exists, delete children first)
        for child_class in [Lesson, Flashcard, MCQQuestion, ClinicalCase]:
            existing_children = await db.execute(
                select(child_class).where(child_class.module_id == module.id)
            )
            for child in existing_children.scalars().all():
                await db.delete(child)
        await db.flush()

        # Import lessons
        for lesson_data in data.get("lessons", []):
            content = lesson_data.get("content", lesson_data)
            lesson = Lesson(
                module_id=module.id,
                lesson_code=lesson_data.get("id", ""),
                title=lesson_data.get("title", ""),
                lesson_order=lesson_data.get("order", 0),
                content=content,
                estimated_minutes=content.get("estimated_minutes", 20),
            )
            db.add(lesson)

        # Import flashcards
        for fc_data in data.get("flashcards", []):
            fc = Flashcard(
                module_id=module.id,
                question=fc_data.get("question", ""),
                answer=fc_data.get("answer", ""),
                difficulty=fc_data.get("difficulty", "medium"),
                category=fc_data.get("category", specialty_name),
            )
            db.add(fc)

        # Import MCQ questions
        for mcq_data in data.get("mcq_questions", []):
            options = mcq_data.get("options", {})
            # Normalize options to dict if list
            if isinstance(options, list):
                options = {chr(65 + i): opt for i, opt in enumerate(options)}

            mcq = MCQQuestion(
                module_id=module.id,
                question=mcq_data.get("question", ""),
                options=options,
                correct=str(mcq_data.get("correct", "A")).upper(),
                explanation=mcq_data.get("explanation", ""),
                difficulty=mcq_data.get("difficulty", "medium"),
            )
            db.add(mcq)

        # Import clinical cases
        for case_data in data.get("clinical_cases", []):
            pres = case_data.get("presentation", "")
            if isinstance(pres, dict):
                pres = json.dumps(pres, ensure_ascii=False)
            case = ClinicalCase(
                module_id=module.id,
                title=case_data.get("title", "Clinical Case"),
                specialty=specialty_name,
                presentation=pres,
                vitals=case_data.get("vitals"),
                diagnosis=case_data.get("diagnosis", ""),
                differential_diagnosis=case_data.get("differential_diagnosis", []),
                management=case_data.get("management", []),
                teaching_points=case_data.get("teaching_points", []),
                content=case_data,
                difficulty=case_data.get("difficulty", "medium"),
            )
            db.add(case)

        await db.commit()
        logger.info(f"✅ Imported: {module_code}")
        return True

    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Error importing {file_path.name}: {e}")
        return False


async def main():
    modules_dir = Path(settings.MODULES_DIR)

    # Fallback to local Modules directory
    if not modules_dir.exists():
        local_dir = Path(__file__).parent.parent.parent.parent / "Modules"
        if local_dir.exists():
            modules_dir = local_dir
        else:
            logger.error(f"Modules directory not found: {modules_dir}")
            return

    logger.info(f"Importing modules from: {modules_dir}")

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    json_files = sorted(modules_dir.glob("module_*.json"))
    logger.info(f"Found {len(json_files)} module files")

    success = 0
    failed = 0

    async with session_factory() as db:
        for f in json_files:
            ok = await import_module(db, f)
            if ok:
                success += 1
            else:
                failed += 1

    # Update specialty module counts
    async with session_factory() as db:
        specialties = await db.execute(select(Specialty))
        for spec in specialties.scalars().all():
            count_result = await db.execute(
                select(Module).where(
                    Module.specialty_id == spec.id,
                    Module.is_published == True,
                )
            )
            spec.module_count = len(count_result.scalars().all())
        await db.commit()

    await engine.dispose()
    logger.info(f"\n{'='*50}")
    logger.info(f"Import complete: {success} succeeded, {failed} failed")
    logger.info(f"{'='*50}")


if __name__ == "__main__":
    asyncio.run(main())
