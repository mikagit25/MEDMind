"""E8: import_modules.py idempotency — running twice never duplicates records."""
import json
import pytest
import pytest_asyncio
import tempfile
from pathlib import Path

from sqlalchemy import select, func
from app.models.models import Module, Lesson, Flashcard, MCQQuestion
from app.scripts.import_modules import import_module


# ---------------------------------------------------------------------------
# Minimal module fixture — just enough structure to pass import
# ---------------------------------------------------------------------------

SAMPLE_MODULE = {
    "meta": {
        "id": "TEST-001",
        "title": "Test Cardiology Module",
        "title_en": "Test Cardiology",
        "specialty": "Кардиология",
        "level": "intermediate",
        "order_in_specialty": 1,
        "duration_hours": 2,
        "prerequisite_modules": [],
    },
    "lessons": [
        {
            "id": "TEST-001-L1",
            "title": "Lesson One",
            "order": 1,
            "content": {"text": "Introduction text", "estimated_minutes": 20},
        }
    ],
    "flashcards": [
        {"question": "Q1?", "answer": "A1", "difficulty": "easy", "category": "cardiology"},
        {"question": "Q2?", "answer": "A2", "difficulty": "medium", "category": "cardiology"},
    ],
    "mcq_questions": [
        {
            "question": "Which drug is a beta-blocker?",
            "options": {"A": "Metoprolol", "B": "Atorvastatin", "C": "Aspirin", "D": "Furosemide"},
            "correct": "A",
            "explanation": "Metoprolol is a selective beta-1 blocker.",
            "difficulty": "medium",
        }
    ],
    "clinical_cases": [],
}


@pytest.fixture
def module_json(tmp_path: Path) -> Path:
    """Write sample module JSON to a temp file and return its path."""
    file = tmp_path / "module_TEST-001.json"
    file.write_text(json.dumps(SAMPLE_MODULE), encoding="utf-8")
    return file


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_import_creates_module(db_session, module_json):
    """First import creates the module record."""
    ok = await import_module(db_session, module_json)
    assert ok is True

    result = await db_session.execute(select(Module).where(Module.code == "TEST-001"))
    module = result.scalar_one_or_none()
    assert module is not None
    assert module.title == "Test Cardiology Module"


@pytest.mark.asyncio
async def test_import_creates_child_records(db_session, module_json):
    """Import populates lessons, flashcards, and MCQ questions."""
    await import_module(db_session, module_json)

    result = await db_session.execute(select(Module).where(Module.code == "TEST-001"))
    module = result.scalar_one_or_none()

    lesson_count = await db_session.execute(
        select(func.count()).where(Lesson.module_id == module.id)
    )
    assert lesson_count.scalar() == 1

    fc_count = await db_session.execute(
        select(func.count()).where(Flashcard.module_id == module.id)
    )
    assert fc_count.scalar() == 2

    mcq_count = await db_session.execute(
        select(func.count()).where(MCQQuestion.module_id == module.id)
    )
    assert mcq_count.scalar() == 1


@pytest.mark.asyncio
async def test_import_is_idempotent_module(db_session, module_json):
    """Running import twice produces exactly one Module record (no duplicate)."""
    await import_module(db_session, module_json)
    await import_module(db_session, module_json)

    count = await db_session.execute(
        select(func.count()).where(Module.code == "TEST-001")
    )
    assert count.scalar() == 1


@pytest.mark.asyncio
async def test_import_is_idempotent_children(db_session, module_json):
    """Running import twice does not duplicate lessons, flashcards, or MCQ."""
    await import_module(db_session, module_json)
    await import_module(db_session, module_json)

    result = await db_session.execute(select(Module).where(Module.code == "TEST-001"))
    module = result.scalar_one_or_none()

    for model_class, expected in [(Lesson, 1), (Flashcard, 2), (MCQQuestion, 1)]:
        count = await db_session.execute(
            select(func.count()).where(model_class.module_id == module.id)
        )
        actual = count.scalar()
        assert actual == expected, f"{model_class.__name__}: expected {expected}, got {actual}"


@pytest.mark.asyncio
async def test_import_updates_title_on_second_run(db_session, module_json, tmp_path):
    """Second import with updated title overwrites the existing record."""
    await import_module(db_session, module_json)

    # Modify the JSON
    updated = json.loads(module_json.read_text())
    updated["meta"]["title"] = "Updated Title"
    module_json.write_text(json.dumps(updated))

    await import_module(db_session, module_json)

    result = await db_session.execute(select(Module).where(Module.code == "TEST-001"))
    module = result.scalar_one_or_none()
    assert module.title == "Updated Title"


@pytest.mark.asyncio
async def test_import_missing_id_returns_false(db_session, tmp_path):
    """A module JSON without an 'id' field should return False (not crash)."""
    bad_file = tmp_path / "module_bad.json"
    bad_file.write_text(json.dumps({"meta": {"title": "No ID"}, "lessons": []}))
    ok = await import_module(db_session, bad_file)
    assert ok is False
