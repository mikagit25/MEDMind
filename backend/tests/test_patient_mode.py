"""Tests for Phase 2 — Patient mode AI guardrails.

Verifies:
(a) 'patient' mode is registered in SYSTEM_PROMPTS enum
(b) Prompt contains all required guardrail phrases
(c) Post-filter appends disclaimer when missing
(d) Red-flag detection works correctly
(e) ensure_disclaimer is idempotent
"""
import pytest
from app.prompts.tutor_prompts import SYSTEM_PROMPTS
from app.prompts.patient_mode import (
    PATIENT_MODE_SYSTEM,
    PATIENT_MODE_DISCLAIMER,
    ensure_disclaimer,
    is_red_flag,
)


# ── (a) Mode registration ──────────────────────────────────────────────────────

class TestModeRegistration:
    def test_patient_mode_in_system_prompts(self):
        assert "patient" in SYSTEM_PROMPTS, \
            "'patient' must be a registered mode in SYSTEM_PROMPTS"

    def test_patient_mode_prompt_is_non_empty(self):
        assert len(SYSTEM_PROMPTS["patient"]) > 200, \
            "Patient mode prompt must be substantive (>200 chars)"

    def test_all_original_modes_still_present(self):
        for mode in ("tutor", "socratic", "case", "exam"):
            assert mode in SYSTEM_PROMPTS, f"Original mode '{mode}' must not be removed"


# ── (b) Prompt guardrail content ──────────────────────────────────────────────

class TestPatientModePromptGuardrails:
    def test_prompt_forbids_diagnosis(self):
        prompt = PATIENT_MODE_SYSTEM.lower()
        assert "diagnos" in prompt and "never" in prompt, \
            "Prompt must explicitly say NEVER diagnose"

    def test_prompt_forbids_dosages(self):
        prompt = PATIENT_MODE_SYSTEM.lower()
        assert "dosage" in prompt or "dose" in prompt, \
            "Prompt must mention dosage restrictions"

    def test_prompt_requires_emergency_first(self):
        prompt = PATIENT_MODE_SYSTEM.lower()
        assert "emergency" in prompt and "first" in prompt, \
            "Prompt must instruct to put emergency recommendation first for red flags"

    def test_prompt_includes_emergency_numbers(self):
        # Must reference at least one emergency number
        assert any(num in PATIENT_MODE_SYSTEM for num in ("911", "112", "103")), \
            "Prompt must include emergency service numbers"

    def test_prompt_requires_disclaimer_in_every_response(self):
        prompt = PATIENT_MODE_SYSTEM.lower()
        assert "every response" in prompt or "always append" in prompt or "disclaimer" in prompt, \
            "Prompt must require disclaimer in every response"

    def test_prompt_forbids_prescription_plans(self):
        prompt = PATIENT_MODE_SYSTEM.lower()
        assert "prescription" in prompt or "treatment plan" in prompt, \
            "Prompt must address prescription/treatment plan refusal"

    def test_prompt_mentions_plain_language(self):
        prompt = PATIENT_MODE_SYSTEM.lower()
        assert "plain" in prompt or "everyday" in prompt or "jargon" in prompt, \
            "Prompt must specify plain language requirement"

    def test_prompt_covers_veterinary_questions(self):
        prompt = PATIENT_MODE_SYSTEM.lower()
        assert "pet" in prompt or "animal" in prompt or "veterinarian" in prompt, \
            "Prompt must handle pet/animal questions"


# ── (c) Post-filter: ensure_disclaimer ────────────────────────────────────────

class TestEnsureDisclaimer:
    def test_appends_disclaimer_when_missing(self):
        response = "The heart is a muscle that pumps blood throughout the body."
        result = ensure_disclaimer(response)
        assert "educational purposes only" in result.lower() or \
               "does not replace" in result.lower() or \
               "consult" in result.lower(), \
            "ensure_disclaimer must append disclaimer when missing"

    def test_does_not_duplicate_when_already_present(self):
        response = (
            "The heart pumps blood. "
            "This information is for educational purposes only and does not replace "
            "professional medical advice. Always consult a qualified healthcare provider."
        )
        result = ensure_disclaimer(response)
        # Count occurrences of the key phrase — should be exactly 1
        count = result.lower().count("educational purposes only")
        assert count == 1, f"Disclaimer should appear exactly once, found {count}"

    def test_handles_partial_disclaimer_matches(self):
        """Texts that already have disclaimer-like language must not get a second block appended."""
        variants = [
            # Each text contains at least one marker phrase recognized by ensure_disclaimer
            "Always consult a qualified doctor before making any medical decisions.",
            "This does not replace advice from your healthcare provider.",
            "This information is not a substitute for medical advice.",
        ]
        for text in variants:
            result = ensure_disclaimer(text)
            # The function should NOT append the full disclaimer block again,
            # so the result length should be <= original + small epsilon
            assert len(result) <= len(text) + 5, (
                f"ensure_disclaimer should not append a full disclaimer to text that already contains "
                f"disclaimer language. Text: '{text[:60]}…'"
            )

    def test_disclaimer_appended_at_end(self):
        """Disclaimer should be appended at the end of the response, not the beginning."""
        response = "Your heart beats approximately 60-100 times per minute."
        result = ensure_disclaimer(response)
        assert result.startswith("Your heart"), "Original content must come first"

    def test_empty_response_gets_disclaimer(self):
        result = ensure_disclaimer("")
        assert len(result) > 0, "Even empty response should get disclaimer"


# ── (d) Red flag detection ─────────────────────────────────────────────────────

class TestRedFlagDetection:
    def test_chest_pain_is_red_flag(self):
        assert is_red_flag("I have chest pain and shortness of breath")

    def test_stroke_symptoms_are_red_flag(self):
        assert is_red_flag("My face is drooping and I have trouble speaking")

    def test_suicidal_ideation_is_red_flag(self):
        assert is_red_flag("I want to kill myself")

    def test_infant_symptoms_are_red_flag(self):
        assert is_red_flag("My baby is not breathing properly")

    def test_normal_question_is_not_red_flag(self):
        assert not is_red_flag("What is hypertension?")

    def test_general_headache_is_not_red_flag(self):
        assert not is_red_flag("I have a mild headache, what could cause it?")

    def test_case_insensitive(self):
        assert is_red_flag("CHEST PAIN for the last hour")

    def test_anaphylaxis_is_red_flag(self):
        assert is_red_flag("my throat is closing from a severe allergic reaction")

    def test_severe_bleeding_is_red_flag(self):
        assert is_red_flag("there is severe bleeding that won't stop")


# ── (e) Disclaimer idempotency ─────────────────────────────────────────────────

class TestDisclaimerIdempotency:
    def test_calling_twice_does_not_add_second_disclaimer(self):
        text = "Some medical information."
        once = ensure_disclaimer(text)
        twice = ensure_disclaimer(once)
        # Should be identical (no second disclaimer added)
        assert once == twice, "ensure_disclaimer must be idempotent"
