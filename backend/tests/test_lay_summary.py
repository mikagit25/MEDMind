"""Tests for Phase 1 — lay_summary / lay_glossary fields and API."""
import json
import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from app.schemas.schemas import LessonLayView, GlossaryTerm
from app.prompts.lay_summary import LAY_SUMMARY_SYSTEM, LAY_SUMMARY_USER


# ── Schema tests ──────────────────────────────────────────────────────────────

class TestLessonLayView:
    def test_lay_view_includes_disclaimer(self):
        view = LessonLayView(id=uuid4(), title="Test Lesson")
        assert "educational purposes" in view.disclaimer
        assert "does not replace" in view.disclaimer

    def test_lay_view_optional_fields_none(self):
        view = LessonLayView(id=uuid4(), title="Test Lesson")
        assert view.lay_summary is None
        assert view.lay_glossary is None

    def test_lay_view_with_data(self):
        terms = [GlossaryTerm(term="Hypertension", simple_definition="High blood pressure")]
        view = LessonLayView(
            id=uuid4(),
            title="Cardiology Basics",
            lay_summary="The heart is a pump that moves blood around your body.",
            lay_glossary=terms,
        )
        assert "pump" in view.lay_summary
        assert len(view.lay_glossary) == 1
        assert view.lay_glossary[0].term == "Hypertension"

    def test_glossary_term_structure(self):
        term = GlossaryTerm(term="Myocardial infarction", simple_definition="Heart attack — when blood flow to part of the heart is blocked")
        assert term.term == "Myocardial infarction"
        assert "Heart attack" in term.simple_definition


# ── Prompt safety tests ───────────────────────────────────────────────────────

class TestLaySummaryPrompt:
    def test_system_prompt_forbids_diagnoses(self):
        prompt_lower = LAY_SUMMARY_SYSTEM.lower()
        assert "not" in prompt_lower and "diagnos" in prompt_lower, \
            "System prompt must explicitly forbid diagnosing"

    def test_system_prompt_requires_disclaimer(self):
        assert "disclaimer" in LAY_SUMMARY_SYSTEM.lower() or "does not replace" in LAY_SUMMARY_SYSTEM.lower(), \
            "System prompt must require a disclaimer in output"

    def test_system_prompt_forbids_dosages(self):
        assert "dosage" in LAY_SUMMARY_SYSTEM.lower() or "dose" in LAY_SUMMARY_SYSTEM.lower(), \
            "System prompt must mention dosage restrictions"

    def test_system_prompt_reading_level(self):
        assert "8th" in LAY_SUMMARY_SYSTEM or "grade" in LAY_SUMMARY_SYSTEM.lower(), \
            "System prompt must specify reading level"

    def test_system_prompt_json_output(self):
        assert "JSON" in LAY_SUMMARY_SYSTEM or "json" in LAY_SUMMARY_SYSTEM.lower(), \
            "System prompt must specify JSON output format"

    def test_user_prompt_template_variables(self):
        rendered = LAY_SUMMARY_USER.format(title="Test Title", content_text="Some medical content")
        assert "Test Title" in rendered
        assert "Some medical content" in rendered


# ── Script unit tests ─────────────────────────────────────────────────────────

class TestGenerateLaySummaries:
    def test_extract_text_from_content_blocks(self):
        from app.scripts.generate_lay_summaries import _extract_text_from_content
        content = {
            "blocks": [
                {"type": "text", "content": "The heart beats 60-100 times per minute."},
                {"type": "heading", "text": "Anatomy"},
                {"type": "list", "items": ["Right ventricle", "Left ventricle"]},
            ]
        }
        result = _extract_text_from_content(content)
        assert "heart beats" in result
        assert "Anatomy" in result
        assert "Right ventricle" in result

    def test_extract_text_fallback_empty_content(self):
        from app.scripts.generate_lay_summaries import _extract_text_from_content
        result = _extract_text_from_content({})
        assert isinstance(result, str)

    def test_parse_ai_response_clean_json(self):
        from app.scripts.generate_lay_summaries import _parse_ai_response
        raw = json.dumps({
            "lay_summary": "The heart pumps blood.",
            "lay_glossary": [{"term": "Artery", "simple_definition": "A blood vessel."}],
            "disclaimer": "Educational only.",
        })
        result = _parse_ai_response(raw)
        assert result["lay_summary"] == "The heart pumps blood."

    def test_parse_ai_response_strips_markdown_fences(self):
        from app.scripts.generate_lay_summaries import _parse_ai_response
        raw = '```json\n{"lay_summary": "Test", "lay_glossary": [], "disclaimer": "..."}\n```'
        result = _parse_ai_response(raw)
        assert result["lay_summary"] == "Test"

    def test_parse_ai_response_invalid_json_raises(self):
        from app.scripts.generate_lay_summaries import _parse_ai_response
        with pytest.raises(json.JSONDecodeError):
            _parse_ai_response("not valid json")
