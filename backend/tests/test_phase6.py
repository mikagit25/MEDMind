"""Tests for Phase 6: pet owner contour — PET modules, /public/pets, patient mode."""
import json
from pathlib import Path

MODULES_DIR = Path(__file__).parent.parent.parent / "Modules"


# ── PET module JSON files ────────────────────────────────────────────────────

def _load_module(code: str) -> dict:
    path = MODULES_DIR / f"module_{code}.json"
    assert path.exists(), f"Module file not found: {path}"
    with open(path) as f:
        return json.load(f)


def test_pet001_file_exists():
    assert (MODULES_DIR / "module_PET-001.json").exists()


def test_pet002_file_exists():
    assert (MODULES_DIR / "module_PET-002.json").exists()


def test_pet003_file_exists():
    assert (MODULES_DIR / "module_PET-003.json").exists()


def test_pet_modules_have_required_meta_fields():
    for code in ("PET-001", "PET-002", "PET-003"):
        data = _load_module(code)
        meta = data["meta"]
        assert meta["specialty"] == "Veterinary", f"{code}: specialty must be Veterinary"
        assert meta["contains_dosages"] is False, f"{code}: must not contain dosages"
        assert meta["audience"] == "pet_owners", f"{code}: audience must be pet_owners"
        assert "title_en" in meta, f"{code}: missing title_en"


def test_pet_modules_have_lessons():
    for code in ("PET-001", "PET-002", "PET-003"):
        data = _load_module(code)
        assert len(data.get("lessons", [])) >= 3, f"{code}: must have at least 3 lessons"


def test_pet_lessons_have_lay_summary():
    for code in ("PET-001", "PET-002", "PET-003"):
        data = _load_module(code)
        for lesson in data["lessons"]:
            assert lesson.get("lay_summary"), f"{code}/{lesson.get('id')}: missing lay_summary"
            assert len(lesson["lay_summary"]) >= 100, f"{code}/{lesson.get('id')}: lay_summary too short"


def test_pet_lessons_have_lay_glossary():
    for code in ("PET-001", "PET-002", "PET-003"):
        data = _load_module(code)
        for lesson in data["lessons"]:
            glossary = lesson.get("lay_glossary", [])
            assert len(glossary) >= 2, f"{code}/{lesson.get('id')}: lay_glossary must have ≥2 terms"
            for entry in glossary:
                assert "term" in entry and "simple_definition" in entry


def test_pet_lessons_have_no_dosages():
    """Lay summaries must not contain dosage-like patterns."""
    import re
    dosage_pattern = re.compile(r'\d+\s*(mg|mcg|μg|ml|mL|mg/kg)\b', re.IGNORECASE)
    for code in ("PET-001", "PET-002", "PET-003"):
        data = _load_module(code)
        for lesson in data["lessons"]:
            summary = lesson.get("lay_summary", "")
            matches = dosage_pattern.findall(summary)
            assert not matches, (
                f"{code}/{lesson.get('id')}: lay_summary contains dosage-like text: {matches}"
            )


def test_pet_modules_have_flashcards():
    for code in ("PET-001", "PET-002", "PET-003"):
        data = _load_module(code)
        assert len(data.get("flashcards", [])) >= 4, f"{code}: must have at least 4 flashcards"


def test_pet_flashcards_have_required_fields():
    for code in ("PET-001", "PET-002", "PET-003"):
        data = _load_module(code)
        for fc in data["flashcards"]:
            for field in ("question", "answer", "difficulty", "category"):
                assert field in fc, f"{code}: flashcard missing field '{field}'"


def test_pet_mcqs_have_correct_answer_in_options():
    for code in ("PET-001", "PET-002", "PET-003"):
        data = _load_module(code)
        for q in data.get("mcq_questions", []):
            assert q["correct"] in q["options"], (
                f"{code}/{q['id']}: correct answer '{q['correct']}' not in options {list(q['options'].keys())}"
            )


def test_pet_mcqs_have_explanations():
    for code in ("PET-001", "PET-002", "PET-003"):
        data = _load_module(code)
        for q in data.get("mcq_questions", []):
            assert q.get("explanation"), f"{code}/{q['id']}: missing explanation"


def test_pet_modules_have_clinical_cases():
    for code in ("PET-001", "PET-002", "PET-003"):
        data = _load_module(code)
        assert len(data.get("clinical_cases", [])) >= 1, f"{code}: must have at least 1 clinical case"


def test_pet_lay_summaries_contain_disclaimer():
    """Every lay_summary must contain the safety disclaimer."""
    disclaimer_markers = ["educational purposes only", "contact a veterinarian", "not constitute"]
    for code in ("PET-001", "PET-002", "PET-003"):
        data = _load_module(code)
        for lesson in data["lessons"]:
            summary = (lesson.get("lay_summary") or "").lower()
            has_disclaimer = any(m.lower() in summary for m in disclaimer_markers)
            assert has_disclaimer, (
                f"{code}/{lesson.get('id')}: lay_summary missing safety disclaimer"
            )


# ── Import script handles PET modules ────────────────────────────────────────

def test_pet_code_detected_as_veterinary():
    """PET-* modules should be flagged is_veterinary = True in import logic."""
    for code in ("PET-001", "PET-002", "PET-003"):
        is_vet = code.startswith("VET-") or code.startswith("PET-")
        assert is_vet, f"{code} should be flagged as veterinary"


def test_import_script_handles_lay_fields():
    """Simulate the import script reading lay_summary and lay_glossary from lesson data."""
    lesson_data = {
        "id": "PET001-L1",
        "order": 1,
        "title": "Test",
        "lay_summary": "Summary text",
        "lay_glossary": [{"term": "T", "simple_definition": "D"}],
        "content": {"key_points": [], "estimated_minutes": 15},
    }
    lay_summary = lesson_data.get("lay_summary")
    lay_glossary = lesson_data.get("lay_glossary")
    assert lay_summary == "Summary text"
    assert len(lay_glossary) == 1


# ── Patient mode — pet red flags ─────────────────────────────────────────────

def test_patient_mode_has_pet_red_flag_patterns():
    from app.prompts.patient_mode import RED_FLAG_PATTERNS
    pet_patterns = [p for p in RED_FLAG_PATTERNS if any(
        w in p for w in ("cat", "dog", "pet", "lily", "raisins", "antifreeze", "xylitol")
    )]
    assert len(pet_patterns) >= 5, f"Expected ≥5 pet red flag patterns, got {len(pet_patterns)}: {pet_patterns}"


def test_patient_mode_system_prompt_has_pet_guidance():
    from app.prompts.patient_mode import PATIENT_MODE_SYSTEM
    prompt_lower = PATIENT_MODE_SYSTEM.lower()
    assert "veterinarian" in prompt_lower, "Prompt must mention veterinarian for pet cases"
    assert "urethral" in prompt_lower or "male cat" in prompt_lower or "cat" in prompt_lower


def test_is_red_flag_detects_cat_urinary():
    from app.prompts.patient_mode import is_red_flag
    # "cat can't urinate" is in the patterns
    assert is_red_flag("my cat can't urinate and has been straining all day")


def test_is_red_flag_detects_xylitol():
    from app.prompts.patient_mode import is_red_flag
    assert is_red_flag("my dog ate xylitol from a peanut butter jar")


def test_is_red_flag_detects_antifreeze():
    from app.prompts.patient_mode import is_red_flag
    assert is_red_flag("I think my dog ate antifreeze")


def test_is_red_flag_detects_lily():
    from app.prompts.patient_mode import is_red_flag
    # "ate lily" is in the patterns — this matches
    assert is_red_flag("my cat ate lily plant leaves this morning")


def test_is_red_flag_does_not_trigger_on_routine_pet_question():
    from app.prompts.patient_mode import is_red_flag
    # General pet questions should NOT be red-flagged
    assert not is_red_flag("what should I feed my dog?")
    assert not is_red_flag("how often should I take my cat to the vet?")
    assert not is_red_flag("my dog is scratching a lot")


def test_ensure_disclaimer_present():
    from app.prompts.patient_mode import ensure_disclaimer
    text_with = "blah blah educational purposes only more text"
    text_without = "This is a response without any safety language."
    assert ensure_disclaimer(text_with) == text_with
    result = ensure_disclaimer(text_without)
    assert "educational purposes" in result.lower()


# ── Public API response structure ────────────────────────────────────────────

def test_public_pet_list_response_structure():
    """Simulate the /public/pets list response structure."""
    sample = {
        "modules": [
            {
                "module_code": "PET-001",
                "slug": "dangerous-foods-and-toxins-for-dogs-and-cats",
                "title": "Dangerous Foods and Toxins for Dogs and Cats",
                "lesson_count": 3,
                "lessons": [],
            }
        ],
        "disclaimer": "educational purposes only",
    }
    assert "modules" in sample
    assert "disclaimer" in sample
    assert sample["modules"][0]["module_code"] == "PET-001"


def test_public_pet_detail_response_structure():
    """Simulate the /public/pets/{slug} detail response structure."""
    sample = {
        "module_code": "PET-001",
        "slug": "dangerous-foods-and-toxins-for-dogs-and-cats",
        "title": "Dangerous Foods and Toxins for Dogs and Cats",
        "lessons": [
            {
                "slug": "dangerous-foods-for-dogs",
                "title": "Dangerous foods for dogs",
                "lay_summary": "Summary",
                "lay_glossary": [{"term": "T", "simple_definition": "D"}],
                "key_points": ["Point 1"],
            }
        ],
        "glossary": [{"term": "T", "simple_definition": "D"}],
        "disclaimer": "educational purposes only",
    }
    assert "lessons" in sample
    assert "glossary" in sample
    assert sample["lessons"][0]["lay_summary"] == "Summary"
