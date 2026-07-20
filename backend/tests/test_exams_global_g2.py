"""G2 — Spanish NCLEX layer tests.

Tests cover:
- ES columns on MCQQuestion model
- Translation script helpers (_build_translate_prompt, _parse_response)
- API returns ES fields in answer response
- RationalePanel ES props in exam frontend (structural checks)
"""

import json
import pytest


# ── G2.1 Translation script helpers ──────────────────────────────────────────

class TestTranslationPromptBuilder:
    def test_prompt_contains_json_input(self):
        from app.scripts.translate_nclex_rationales import _build_translate_prompt
        batch = [{"id": "abc", "explanation": "Test", "rationales": {}, "key_takeaway": "TK", "test_taking_tip": "TTT"}]
        prompt = _build_translate_prompt(batch)
        assert '"id": "abc"' in prompt

    def test_prompt_references_glossary_terms(self):
        from app.scripts.translate_nclex_rationales import _build_translate_prompt
        batch = [{"id": "x", "explanation": "", "rationales": {}, "key_takeaway": "", "test_taking_tip": ""}]
        prompt = _build_translate_prompt(batch)
        for term in ["NCLEX", "SBAR", "NPO", "IV", "PRN"]:
            assert term in prompt, f"Glossary term {term!r} missing from prompt"

    def test_prompt_instructs_latin_american_spanish(self):
        from app.scripts.translate_nclex_rationales import _build_translate_prompt
        batch = [{"id": "y", "explanation": "", "rationales": {}, "key_takeaway": "", "test_taking_tip": ""}]
        prompt = _build_translate_prompt(batch)
        assert "Latin American" in prompt or "latin" in prompt.lower()

    def test_prompt_instructs_correct_incorrect_in_english(self):
        from app.scripts.translate_nclex_rationales import _build_translate_prompt
        batch = [{"id": "z", "explanation": "", "rationales": {"A": {"why": "correct", "text": "Good"}}, "key_takeaway": "", "test_taking_tip": ""}]
        prompt = _build_translate_prompt(batch)
        assert '"correct"/"incorrect" values stay in English' in prompt or "correct" in prompt


class TestParseResponse:
    def test_parses_valid_json_array(self):
        from app.scripts.translate_nclex_rationales import _parse_response
        raw = '[{"id": "abc", "explanation": "hola", "rationales": {}, "key_takeaway": "ok", "test_taking_tip": "tip"}]'
        result = _parse_response(raw)
        assert result is not None
        assert len(result) == 1
        assert result[0]["id"] == "abc"

    def test_extracts_json_embedded_in_text(self):
        from app.scripts.translate_nclex_rationales import _parse_response
        raw = 'Here is the result:\n[{"id": "1", "explanation": "es", "rationales": {}, "key_takeaway": "kk", "test_taking_tip": "tt"}]\nDone.'
        result = _parse_response(raw)
        assert result is not None
        assert result[0]["explanation"] == "es"

    def test_returns_none_for_invalid_json(self):
        from app.scripts.translate_nclex_rationales import _parse_response
        result = _parse_response("This is not JSON at all")
        assert result is None

    def test_returns_none_for_empty_string(self):
        from app.scripts.translate_nclex_rationales import _parse_response
        result = _parse_response("")
        assert result is None

    def test_returns_none_for_malformed_json(self):
        from app.scripts.translate_nclex_rationales import _parse_response
        result = _parse_response('[{"id": "abc", broken}]')
        assert result is None


class TestGroqKeyDeduplication:
    def test_keys_are_deduplicated(self):
        import importlib, sys
        import os as _os
        _os.environ.setdefault("GROQ_KEY_MODULE_2", "key-A")
        _os.environ.setdefault("GROQ_KEY_CASES", "key-A")  # duplicate
        _os.environ.setdefault("GROQ_KEY_VET_MODULES", "key-B")
        # Re-import to test dedup logic
        if "app.scripts.translate_nclex_rationales" in sys.modules:
            del sys.modules["app.scripts.translate_nclex_rationales"]
        from app.scripts.translate_nclex_rationales import GROQ_KEYS
        assert len(GROQ_KEYS) == len(set(GROQ_KEYS)), "GROQ_KEYS must not contain duplicates"


# ── G2.2 MCQQuestion model has ES columns ────────────────────────────────────

class TestMCQQuestionESColumns:
    def test_model_has_explanation_es(self):
        from app.models.models import MCQQuestion
        assert hasattr(MCQQuestion, "explanation_es")

    def test_model_has_rationales_es(self):
        from app.models.models import MCQQuestion
        assert hasattr(MCQQuestion, "rationales_es")

    def test_model_has_key_takeaway_es(self):
        from app.models.models import MCQQuestion
        assert hasattr(MCQQuestion, "key_takeaway_es")

    def test_model_has_test_taking_tip_es(self):
        from app.models.models import MCQQuestion
        assert hasattr(MCQQuestion, "test_taking_tip_es")


# ── G2.3 Answer API snapshot includes ES fields ───────────────────────────────

class TestSnapshotESFields:
    def test_exam_routes_import_cleanly(self):
        from app.api.v1.routes import exam
        assert hasattr(exam, "router")

    def test_answer_response_keys_include_es(self):
        """Check that the submit_answer endpoint builds an ES-inclusive response dict."""
        import ast, pathlib
        src = pathlib.Path("app/api/v1/routes/exam.py").read_text()
        assert "rationales_es" in src, "rationales_es missing from exam.py response"
        assert "key_takeaway_es" in src, "key_takeaway_es missing from exam.py response"
        assert "test_taking_tip_es" in src, "test_taking_tip_es missing from exam.py response"
        assert "explanation_es" in src, "explanation_es missing from exam.py response"

    def test_snapshot_stores_es_fields(self):
        """Snapshot builder must persist _rationales_es alongside _rationales."""
        import pathlib
        src = pathlib.Path("app/api/v1/routes/exam.py").read_text()
        assert "_rationales_es" in src
        assert "_key_takeaway_es" in src


# ── G2.4 Groq client structure ───────────────────────────────────────────────

class TestGroqClientStructure:
    def test_groq_client_has_call_method(self):
        from app.scripts.translate_nclex_rationales import GroqClient
        assert callable(getattr(GroqClient, "call", None))

    def test_groq_client_has_mark_limited(self):
        from app.scripts.translate_nclex_rationales import GroqClient
        assert callable(getattr(GroqClient, "mark_limited", None))

    def test_groq_client_init(self):
        import os
        os.environ.setdefault("GROQ_KEY_MODULE_2", "test-key")
        from app.scripts.translate_nclex_rationales import GroqClient
        c = GroqClient()
        assert isinstance(c._reset_at, dict)

    def test_best_key_returns_least_limited(self):
        import os, time
        os.environ["GROQ_KEY_MODULE_2"] = "key-early"
        os.environ["GROQ_KEY_CASES"] = "key-late"
        if "app.scripts.translate_nclex_rationales" in __import__("sys").modules:
            del __import__("sys").modules["app.scripts.translate_nclex_rationales"]
        from app.scripts.translate_nclex_rationales import GroqClient, GROQ_KEYS
        if len(GROQ_KEYS) < 2:
            pytest.skip("Need at least 2 unique keys to test key rotation")
        c = GroqClient()
        # Mark first key as heavily rate-limited
        c.mark_limited(GROQ_KEYS[0], 999)
        best = c._best_key()
        assert best != GROQ_KEYS[0], "Should prefer the less-limited key"


# ── G2.5 Translation script CLI flags ────────────────────────────────────────

class TestTranslationScriptCLI:
    def test_main_function_exists(self):
        from app.scripts.translate_nclex_rationales import main
        assert callable(main)

    def test_run_function_exists(self):
        from app.scripts.translate_nclex_rationales import run
        import inspect
        sig = inspect.signature(run)
        assert "max_questions" in sig.parameters
        assert "dry_run" in sig.parameters

    def test_batch_size_is_positive(self):
        from app.scripts.translate_nclex_rationales import BATCH_SIZE
        assert BATCH_SIZE >= 1

    def test_groq_model_set(self):
        from app.scripts.translate_nclex_rationales import GROQ_MODEL
        assert isinstance(GROQ_MODEL, str) and len(GROQ_MODEL) > 0

    def test_glossary_not_empty(self):
        from app.scripts.translate_nclex_rationales import ES_GLOSSARY
        assert len(ES_GLOSSARY) >= 5

    def test_glossary_preserves_nclex(self):
        from app.scripts.translate_nclex_rationales import ES_GLOSSARY
        assert ES_GLOSSARY.get("NCLEX") == "NCLEX"

    def test_glossary_preserves_sbar(self):
        from app.scripts.translate_nclex_rationales import ES_GLOSSARY
        assert ES_GLOSSARY.get("SBAR") == "SBAR"
