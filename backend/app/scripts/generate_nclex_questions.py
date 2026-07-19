"""
NCLEX Question Bank Generator
Generates 40 questions per NURSE-* module using Groq (KEY_3/KEY_4 — content pipeline).

Usage:
  python -m app.scripts.generate_nclex_questions          # all modules
  python -m app.scripts.generate_nclex_questions NURSE-002 # specific module

Output: Modules/nclex_qbank_NURSE-XXX.json (one file per module)
Import: python -m app.scripts.import_nclex_questions
"""

import asyncio
import json
import os
import random
import re
import sys
import time
from pathlib import Path

import httpx

# ── Config ────────────────────────────────────────────────────────────────────
# Generation keys: dedicated module-gen keys + VET_MODULES reserve key
# Never use GROQ_API_KEY / GROQ_API_KEY_2 (user tutor) or the news/articles keys
GROQ_KEYS = [k for k in [
    os.getenv("GROQ_KEY_MODULE_2", ""),
    os.getenv("GROQ_KEY_CASES", ""),
    os.getenv("GROQ_KEY_VET_MODULES", ""),
    os.getenv("GROQ_API_KEY_3", ""),
] if k]
# Deduplicate
_seen: set = set()
GROQ_KEYS = [k for k in GROQ_KEYS if not (k in _seen or _seen.add(k))]
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODULES_DIR = (
    Path("/app/data/modules") if Path("/app/data/modules").exists()
    else Path(__file__).parents[4] / "Modules"
)
OUTPUT_DIR = Path("/tmp/nclex_output")
OUTPUT_PREFIX = "nclex_qbank_"

# ── NCLEX Metadata Maps ───────────────────────────────────────────────────────

MODULE_META = {
    # ── Original 8 modules ──────────────────────────────────────────────────────
    "NURSE-001": {
        "title": "Nursing Process & Documentation",
        "client_needs": ["safe_effective_care", "health_promotion"],
        "tags": ["adpie", "sbar", "nursing_diagnosis", "documentation", "care_plan"],
    },
    "NURSE-002": {
        "title": "Medication Safety",
        "client_needs": ["pharmacological", "safe_effective_care"],
        "tags": ["medication_safety", "five_rights", "high_alert_meds", "sata", "pharmacology"],
    },
    "NURSE-003": {
        "title": "Dose Calculations & IV Therapy",
        "client_needs": ["pharmacological", "reduction_risk"],
        "tags": ["dose_calculation", "iv_therapy", "infusion_rate", "weight_based"],
    },
    "NURSE-004": {
        "title": "Infection Control & Hand Hygiene",
        "client_needs": ["safe_effective_care", "reduction_risk"],
        "tags": ["infection_control", "hand_hygiene", "precautions", "ppe", "who_5_moments"],
    },
    "NURSE-005": {
        "title": "Recognising Deterioration (NEWS2)",
        "client_needs": ["physiological_adaptation", "reduction_risk"],
        "tags": ["news2", "sepsis", "deterioration", "escalation", "qsofa"],
    },
    "NURSE-006": {
        "title": "Emergency Skills: Nurse's Role",
        "client_needs": ["physiological_adaptation", "safe_effective_care"],
        "tags": ["bls", "anaphylaxis", "emergency", "code_blue", "airway"],
    },
    "NURSE-007": {
        "title": "Patient Care: Wounds, Falls, Mobility",
        "client_needs": ["basic_care", "reduction_risk"],
        "tags": ["wound_care", "falls_prevention", "braden_scale", "morse_scale", "pressure_injury"],
    },
    "NURSE-008": {
        "title": "Communication, Family & SBAR Handoff",
        "client_needs": ["psychosocial", "safe_effective_care"],
        "tags": ["sbar_handoff", "therapeutic_communication", "teach_back", "family_care"],
    },
    # ── Expansion batch: 20 new modules targeting thin NCLEX categories ─────────
    "NURSE-009": {
        "title": "Mental Health & Psychiatric Nursing",
        "client_needs": ["psychosocial", "safe_effective_care"],
        "tags": ["mental_health", "therapeutic_relationship", "psychiatric_disorders", "de_escalation", "milieu_therapy"],
    },
    "NURSE-010": {
        "title": "Crisis Intervention, Abuse & Substance Use",
        "client_needs": ["psychosocial", "reduction_risk"],
        "tags": ["suicide_risk", "substance_withdrawal", "abuse_assessment", "crisis_intervention", "safety_planning"],
    },
    "NURSE-011": {
        "title": "Maternal Nursing: Antepartum & Complications",
        "client_needs": ["health_promotion", "physiological_adaptation"],
        "tags": ["prenatal_care", "ectopic_pregnancy", "preeclampsia", "gestational_diabetes", "fetal_monitoring"],
    },
    "NURSE-012": {
        "title": "Intrapartum, Postpartum & Newborn Care",
        "client_needs": ["physiological_adaptation", "basic_care"],
        "tags": ["labor_stages", "fetal_heart_rate", "postpartum_hemorrhage", "breastfeeding", "newborn_assessment"],
    },
    "NURSE-013": {
        "title": "Pediatric Nursing & Child Development",
        "client_needs": ["health_promotion", "basic_care"],
        "tags": ["growth_development", "immunizations", "pediatric_vitals", "fever_management", "child_safety"],
    },
    "NURSE-014": {
        "title": "Cardiovascular Nursing & Cardiac Pharmacology",
        "client_needs": ["physiological_adaptation", "pharmacological"],
        "tags": ["heart_failure", "myocardial_infarction", "arrhythmias", "cardiac_drugs", "hemodynamic_monitoring"],
    },
    "NURSE-015": {
        "title": "Respiratory Nursing & Ventilator Management",
        "client_needs": ["physiological_adaptation", "reduction_risk"],
        "tags": ["asthma", "copd", "pneumonia", "mechanical_ventilation", "oxygen_therapy", "respiratory_failure"],
    },
    "NURSE-016": {
        "title": "Neurological Nursing & Stroke Care",
        "client_needs": ["physiological_adaptation", "reduction_risk"],
        "tags": ["stroke", "traumatic_brain_injury", "seizures", "icp_management", "neuro_assessment", "glasgow"],
    },
    "NURSE-017": {
        "title": "Endocrine Nursing & Diabetes Management",
        "client_needs": ["pharmacological", "physiological_adaptation"],
        "tags": ["insulin_management", "thyroid_disorders", "adrenal_crisis", "glucose_monitoring", "DKA", "HHS"],
    },
    "NURSE-018": {
        "title": "Renal, Urinary & Fluid-Electrolyte Nursing",
        "client_needs": ["physiological_adaptation", "reduction_risk"],
        "tags": ["acute_kidney_injury", "CKD", "dialysis", "electrolyte_imbalance", "catheter_care", "fluid_balance"],
    },
    "NURSE-019": {
        "title": "GI Nursing, Nutrition & Enteral Feeding",
        "client_needs": ["basic_care", "physiological_adaptation"],
        "tags": ["enteral_nutrition", "GI_bleeding", "bowel_obstruction", "stoma_care", "liver_disease", "ng_tube"],
    },
    "NURSE-020": {
        "title": "Oncology Nursing & Palliative Care",
        "client_needs": ["pharmacological", "psychosocial"],
        "tags": ["chemotherapy", "neutropenic_precautions", "pain_management", "end_of_life", "cancer_care", "hospice"],
    },
    "NURSE-021": {
        "title": "ICU & Critical Care Nursing",
        "client_needs": ["physiological_adaptation", "safe_effective_care"],
        "tags": ["hemodynamic_monitoring", "vasopressors", "septic_shock", "ARDS", "central_line", "arterial_line"],
    },
    "NURSE-022": {
        "title": "Perioperative & Surgical Nursing",
        "client_needs": ["reduction_risk", "safe_effective_care"],
        "tags": ["preoperative_assessment", "surgical_safety_checklist", "anesthesia", "PACU", "postoperative_complications"],
    },
    "NURSE-023": {
        "title": "Leadership, Delegation & Scope of Practice",
        "client_needs": ["safe_effective_care", "psychosocial"],
        "tags": ["delegation", "scope_of_practice", "prioritization", "management", "staffing", "chain_of_command"],
    },
    "NURSE-024": {
        "title": "Ethics, Law, Patient Rights & Advocacy",
        "client_needs": ["safe_effective_care", "psychosocial"],
        "tags": ["informed_consent", "hipaa", "patient_rights", "advance_directives", "advocacy", "ethical_principles"],
    },
    "NURSE-025": {
        "title": "Community Health, Public Health & Screening",
        "client_needs": ["health_promotion", "safe_effective_care"],
        "tags": ["community_health", "health_screening", "immunization_schedule", "epidemiology", "health_education"],
    },
    "NURSE-026": {
        "title": "Pharmacology: High-Alert Drugs & Drug Classes",
        "client_needs": ["pharmacological", "reduction_risk"],
        "tags": ["anticoagulants", "antibiotics", "antihypertensives", "drug_interactions", "adverse_effects", "antidotes"],
    },
    "NURSE-027": {
        "title": "Acid-Base Balance & Fluid Management",
        "client_needs": ["physiological_adaptation", "pharmacological"],
        "tags": ["ABG_interpretation", "metabolic_acidosis", "respiratory_alkalosis", "IV_fluids", "electrolytes"],
    },
    "NURSE-028": {
        "title": "Gerontological Nursing & Long-Term Care",
        "client_needs": ["health_promotion", "basic_care"],
        "tags": ["aging_changes", "dementia_care", "polypharmacy", "fall_risk_elderly", "long_term_care", "restraints"],
    },
}

CJMM_SKILLS = [
    "recognize_cues",
    "analyze_cues",
    "prioritize_hypotheses",
    "generate_solutions",
    "take_actions",
    "evaluate_outcomes",
]

# How many questions of each type per module (~53 total for calc modules, ~48 for others)
QUESTION_MIX = {
    "mcq": 30,        # standard 4-option MCQ
    "sata": 10,       # Select All That Apply (4-6 options, 2-4 correct)
    "ordered": 5,     # Put-in-order (4-5 steps)
    "calculation": 5, # numeric answer (only for relevant modules)
    "bowtie": 3,      # NGN bow-tie (clinical judgment)
}

# Modules with meaningful calculation questions
CALC_MODULES = {"NURSE-002", "NURSE-003", "NURSE-005", "NURSE-006", "NURSE-017", "NURSE-018", "NURSE-026", "NURSE-027"}

# ── Prompts ───────────────────────────────────────────────────────────────────

MCQ_PROMPT = """You are an expert NCLEX question writer with 15 years of experience.
Generate {count} NCLEX-RN style MCQ questions about: {topic}
Module: {module_title}

Rules:
- Each question must have exactly 4 options (A, B, C, D)
- Only ONE option is correct
- Use clinical scenarios whenever possible
- Include a clear explanation of why the correct answer is right AND why the distractors are wrong
- Difficulty distribution: {easy} easy, {medium} medium, {hard} hard
- Cover these NCLEX client needs categories as specified per question
- Question stem must be at least 2 sentences with a clinical scenario
- For rationales: apply nursing priority logic (ABC, Maslow, nursing process)

Return ONLY valid JSON array, no markdown, no extra text:
[
  {{
    "question": "Clinical scenario...",
    "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
    "correct": "B",
    "explanation": "B is correct because... A is wrong because... C is wrong because...",
    "rationales": {{
      "A": {{"text": "Why A is incorrect — specific clinical reasoning.", "why": "incorrect"}},
      "B": {{"text": "Why B is correct — specific clinical reasoning with nursing principle.", "why": "correct"}},
      "C": {{"text": "Why C is incorrect — specific clinical reasoning.", "why": "incorrect"}},
      "D": {{"text": "Why D is incorrect — specific clinical reasoning.", "why": "incorrect"}}
    }},
    "key_takeaway": "One sentence summarizing the core nursing principle tested.",
    "test_taking_tip": "One sentence tip for eliminating distractors on the NCLEX.",
    "difficulty": "medium",
    "nclex_client_needs": "pharmacological",
    "cjmm_skill": "take_actions",
    "tags": ["tag1", "tag2"]
  }}
]"""

SATA_PROMPT = """You are an expert NCLEX question writer.
Generate {count} NCLEX-RN style SATA (Select All That Apply) questions about: {topic}
Module: {module_title}

Rules:
- Each question has 5-6 options (A through E or F)
- 2-4 options must be correct
- NEVER have only 1 or all options correct
- This is ALL-OR-NOTHING scoring (NCLEX standard)
- Clinical nursing scenario required
- Explanation must address EACH option

Return ONLY valid JSON array:
[
  {{
    "question": "A nurse is caring for... Select all that apply.",
    "question_type": "sata",
    "options": {{"A": "...", "B": "...", "C": "...", "D": "...", "E": "..."}},
    "correct_answers": ["A", "C", "E"],
    "explanation": "A is correct: ... B is incorrect: ... C is correct: ...",
    "rationales": {{
      "A": {{"text": "Why A should be selected — clinical evidence.", "why": "correct"}},
      "B": {{"text": "Why B should NOT be selected — clinical reasoning.", "why": "incorrect"}},
      "C": {{"text": "Why C should be selected — clinical evidence.", "why": "correct"}},
      "D": {{"text": "Why D should NOT be selected — clinical reasoning.", "why": "incorrect"}},
      "E": {{"text": "Why E should be selected — clinical evidence.", "why": "correct"}}
    }},
    "key_takeaway": "One sentence summarizing the core nursing principle tested.",
    "test_taking_tip": "One sentence tip for SATA elimination strategy on the NCLEX.",
    "difficulty": "medium",
    "nclex_client_needs": "safe_effective_care",
    "cjmm_skill": "generate_solutions",
    "tags": ["tag1"]
  }}
]"""

ORDERED_PROMPT = """You are an expert NCLEX question writer.
Generate {count} NCLEX-RN style ordered/sequencing questions about: {topic}
Module: {module_title}

Rules:
- Student must place 4-5 steps in the CORRECT clinical sequence
- Options are labeled A-D or A-E
- Only one correct sequence exists
- Must be a genuine clinical procedure or assessment sequence

Return ONLY valid JSON array:
[
  {{
    "question": "A nurse must perform the following steps. Place them in the correct order.",
    "question_type": "ordered",
    "options": {{"A": "Step text", "B": "Step text", "C": "Step text", "D": "Step text"}},
    "correct_order": ["C", "A", "D", "B"],
    "explanation": "The correct sequence is C→A→D→B because...",
    "key_takeaway": "One sentence summarizing the sequencing principle tested.",
    "test_taking_tip": "One sentence tip — e.g., always assess before intervening.",
    "difficulty": "medium",
    "nclex_client_needs": "safe_effective_care",
    "cjmm_skill": "take_actions",
    "tags": ["tag1"]
  }}
]"""

BOWTIE_PROMPT = """You are an expert NGN (Next Generation NCLEX) question writer.
Generate {count} bow-tie clinical judgment questions about: {topic}
Module: {module_title}

A bow-tie question has 3 components:
1. Condition most likely (1 correct from 4-5 options)
2. Two nursing actions to take (2 correct from 5-6 action options)
3. Two parameters to monitor (2 correct from 5-6 monitoring options)

This tests ALL 6 CJMM clinical judgment skills in one item.

Return ONLY valid JSON array:
[
  {{
    "question": "A nurse is caring for [detailed patient scenario with vitals/history]...",
    "question_type": "mcq",
    "ngn_type": "bowtie",
    "options": {{"A": "placeholder — see bowtie_data"}},
    "correct": "A",
    "explanation": "The condition is X because... The nurse should take actions Y and Z because... Monitor A and B because...",
    "difficulty": "hard",
    "nclex_client_needs": "physiological_adaptation",
    "cjmm_skill": "prioritize_hypotheses",
    "bowtie_data": {{
      "condition_options": ["Septic shock", "Hypovolemic shock", "Cardiogenic shock", "Anaphylaxis", "Neurogenic shock"],
      "action_options": ["Administer O2 via NRB mask", "Place in Trendelenburg", "Give IV fluid bolus 500mL NS", "Obtain blood cultures x2", "Administer epinephrine IM", "Call rapid response team"],
      "parameter_options": ["Blood pressure", "Urine output", "Temperature", "Serum lactate", "SpO2", "Mental status"],
      "correct_condition": "Septic shock",
      "correct_actions": ["Administer O2 via NRB mask", "Obtain blood cultures x2"],
      "correct_parameters": ["Blood pressure", "Serum lactate"]
    }},
    "tags": ["sepsis", "shock", "ngn"]
  }}
]"""


# ── Groq Client ───────────────────────────────────────────────────────────────

class GroqClient:
    """
    Smart key-pool client: tracks per-key rate-limit reset times from Groq
    response headers and sleeps exactly as long as needed — no blind backoff.
    """

    def __init__(self):
        if not GROQ_KEYS:
            raise RuntimeError("No Groq API keys configured")
        # epoch-second timestamp when each key becomes usable again (0 = now)
        self._reset_at: dict[str, float] = {k: 0.0 for k in GROQ_KEYS}

    def _best_key(self) -> tuple[str, float]:
        """Return (key, seconds_to_wait) for the soonest-available key."""
        now = time.time()
        key = min(GROQ_KEYS, key=lambda k: self._reset_at[k])
        wait = max(0.0, self._reset_at[key] - now)
        return key, wait

    def _parse_reset(self, headers: dict, fallback: float = 62.0) -> float:
        """Extract wait seconds from Groq rate-limit headers."""
        for h in ("retry-after", "x-ratelimit-reset-tokens", "x-ratelimit-reset-requests"):
            v = headers.get(h)
            if v is None:
                continue
            try:
                # Value may be "1.234" seconds or an integer
                return float(v) + 1.0   # +1s buffer
            except ValueError:
                pass
        return fallback

    async def generate(self, prompt: str, max_tokens: int = 3000,
                       max_wait: float = 90.0) -> str:
        """
        max_wait: if ALL keys need to wait longer than this, raise RateLimitExhausted
        so the caller can exit cleanly and let cron retry later.
        """
        for attempt in range(len(GROQ_KEYS) * 4):
            key, wait = self._best_key()
            if wait > max_wait:
                raise RateLimitExhausted(
                    f"All {len(GROQ_KEYS)} keys rate-limited for >{max_wait:.0f}s "
                    f"(soonest reset in {wait:.0f}s). Exiting — cron will retry."
                )
            if wait > 0:
                print(f"  Keys limited — sleeping {wait:.0f}s until reset "
                      f"(within {max_wait:.0f}s budget)...")
                await asyncio.sleep(wait)

            try:
                async with httpx.AsyncClient(timeout=90) as client:
                    resp = await client.post(
                        GROQ_URL,
                        headers={"Authorization": f"Bearer {key}",
                                 "Content-Type": "application/json"},
                        json={
                            "model": GROQ_MODEL,
                            "messages": [{"role": "user", "content": prompt}],
                            "max_tokens": max_tokens,
                            "temperature": 0.7,
                        },
                    )

                if resp.status_code == 429:
                    reset_in = self._parse_reset(dict(resp.headers))
                    self._reset_at[key] = time.time() + reset_in
                    print(f"  Key {GROQ_KEYS.index(key)+1}/{len(GROQ_KEYS)} limited, "
                          f"resets in {reset_in:.0f}s — switching key")
                    continue

                resp.raise_for_status()
                await asyncio.sleep(2)  # polite gap after a successful call
                return resp.json()["choices"][0]["message"]["content"]

            except httpx.HTTPStatusError:
                raise
            except Exception as e:
                print(f"  Request error: {e} — retrying")
                self._reset_at[key] = time.time() + 5
                continue

        raise RuntimeError(f"Groq API failed after {len(GROQ_KEYS) * 4} attempts")


class RateLimitExhausted(Exception):
    """All keys rate-limited beyond acceptable wait — exit and retry next cron run."""


# ── Parsers ───────────────────────────────────────────────────────────────────

def extract_json(text: str) -> list:
    """Extract JSON array from LLM output (handles markdown fences and partial JSON)."""
    text = text.strip()
    # Remove markdown code fences
    text = re.sub(r"```(?:json)?\s*", "", text)
    text = re.sub(r"```\s*$", "", text)
    text = text.strip()
    # Find first [ ... ] block
    start = text.find("[")
    if start == -1:
        raise ValueError(f"No JSON array found in output: {text[:200]}")

    # Try full array first
    end = text.rfind("]") + 1
    if end > 0:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

    # Partial recovery: extract valid objects one by one
    items = []
    depth = 0
    in_str = False
    escape = False
    obj_start = None

    i = start + 1  # skip opening [
    while i < len(text):
        c = text[i]
        if escape:
            escape = False
        elif c == "\\" and in_str:
            escape = True
        elif c == '"' and not escape:
            in_str = not in_str
        elif not in_str:
            if c == "{":
                if depth == 0:
                    obj_start = i
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0 and obj_start is not None:
                    try:
                        obj = json.loads(text[obj_start:i + 1])
                        items.append(obj)
                    except json.JSONDecodeError:
                        pass
                    obj_start = None
        i += 1

    if not items:
        raise ValueError(f"Could not extract any valid JSON objects from output: {text[:300]}")
    return items


def validate_mcq(q: dict) -> bool:
    return (
        isinstance(q.get("question"), str) and len(q["question"]) > 20
        and isinstance(q.get("options"), dict) and len(q["options"]) >= 4
        and q.get("correct") in q.get("options", {})
        and isinstance(q.get("explanation"), str)
    )


def validate_sata(q: dict) -> bool:
    opts = q.get("options", {})
    correct = q.get("correct_answers", [])
    return (
        isinstance(correct, list) and 2 <= len(correct) <= len(opts) - 1
        and all(c in opts for c in correct)
        and len(opts) >= 5
    )


def validate_ordered(q: dict) -> bool:
    opts = q.get("options", {})
    order = q.get("correct_order", [])
    return (
        isinstance(order, list) and len(order) == len(opts)
        and set(order) == set(opts.keys())
    )


def validate_bowtie(q: dict) -> bool:
    bd = q.get("bowtie_data", {})
    return (
        isinstance(bd.get("condition_options"), list) and len(bd["condition_options"]) >= 4
        and isinstance(bd.get("action_options"), list) and len(bd["action_options"]) >= 5
        and isinstance(bd.get("parameter_options"), list) and len(bd["parameter_options"]) >= 5
        and isinstance(bd.get("correct_condition"), str) and bd["correct_condition"] in bd["condition_options"]
        and isinstance(bd.get("correct_actions"), list) and len(bd["correct_actions"]) == 2
        and all(a in bd["action_options"] for a in bd["correct_actions"])
        and isinstance(bd.get("correct_parameters"), list) and len(bd["correct_parameters"]) == 2
        and all(p in bd["parameter_options"] for p in bd["correct_parameters"])
    )


# ── Generator ─────────────────────────────────────────────────────────────────

async def generate_for_module(module_code: str, groq: GroqClient) -> list:
    meta = MODULE_META[module_code]
    title = meta["title"]
    client_needs_list = meta["client_needs"]
    tags = meta["tags"]
    is_calc_module = module_code in CALC_MODULES

    print(f"\n{'='*60}")
    print(f"  Generating questions for {module_code}: {title}")
    print(f"{'='*60}")

    all_questions = []
    cjmm_cycle = list(CJMM_SKILLS)

    # 1. Standard MCQ — split into 2 batches of 15 to avoid token-limit 429s
    mcq_total = QUESTION_MIX["mcq"]
    batch_size = 15
    print(f"  → MCQ ({mcq_total} questions in batches of {batch_size})...")
    for batch_idx, offset in enumerate(range(0, mcq_total, batch_size)):
        count_this = min(batch_size, mcq_total - offset)
        prompt = MCQ_PROMPT.format(
            count=count_this,
            topic=f"{title} — covering {', '.join(tags)}",
            module_title=title,
            easy=max(1, count_this // 5),
            medium=count_this // 2,
            hard=max(1, count_this // 5),
        )
        try:
            raw = await groq.generate(prompt)
            questions = extract_json(raw)
            valid = [q for q in questions if validate_mcq(q)]
            base_i = len(all_questions)
            for i, q in enumerate(valid):
                q["question_type"] = "mcq"
                q.setdefault("nclex_client_needs", client_needs_list[(base_i + i) % len(client_needs_list)])
                q.setdefault("cjmm_skill", cjmm_cycle[(base_i + i) % len(cjmm_cycle)])
                q.setdefault("tags", tags[:2])
                if not q.get("correct"):
                    q["correct"] = list(q["options"].keys())[0]
            all_questions.extend(valid)
            print(f"     ✓ batch {batch_idx+1}: {len(valid)}/{len(questions)} valid MCQ")
        except RateLimitExhausted:
            raise
        except Exception as e:
            print(f"     ✗ MCQ batch {batch_idx+1} failed: {e}")

    # 2. SATA — split into 2 batches of 5
    sata_total = QUESTION_MIX["sata"]
    sata_batch = 5
    print(f"  → SATA ({sata_total} questions in batches of {sata_batch})...")
    for batch_idx, offset in enumerate(range(0, sata_total, sata_batch)):
        count_this = min(sata_batch, sata_total - offset)
        prompt = SATA_PROMPT.format(
            count=count_this,
            topic=f"{title} — clinical nursing scenarios",
            module_title=title,
        )
        try:
            raw = await groq.generate(prompt)
            questions = extract_json(raw)
            valid = [q for q in questions if validate_sata(q)]
            base_i = len(all_questions)
            for i, q in enumerate(valid):
                q["question_type"] = "sata"
                q.setdefault("nclex_client_needs", client_needs_list[(base_i + i) % len(client_needs_list)])
                q.setdefault("cjmm_skill", cjmm_cycle[(base_i + i + 2) % len(cjmm_cycle)])
                q.setdefault("tags", tags[:2])
                q.setdefault("correct", list(q["options"].keys())[0])
                q["partial_scoring"] = False
            all_questions.extend(valid)
            print(f"     ✓ SATA batch {batch_idx+1}: {len(valid)}/{len(questions)} valid")
        except RateLimitExhausted:
            raise
        except Exception as e:
            print(f"     ✗ SATA batch {batch_idx+1} failed: {e}")

    # 3. Ordered
    print(f"  → Ordered ({QUESTION_MIX['ordered']} questions)...")
    prompt = ORDERED_PROMPT.format(
        count=QUESTION_MIX["ordered"],
        topic=f"{title} — clinical procedures and sequences",
        module_title=title,
    )
    try:
        raw = await groq.generate(prompt)
        questions = extract_json(raw)
        valid = [q for q in questions if validate_ordered(q)]
        for i, q in enumerate(valid):
            q["question_type"] = "ordered"
            q.setdefault("nclex_client_needs", client_needs_list[0])
            q.setdefault("cjmm_skill", "take_actions")
            q.setdefault("tags", tags[:2])
            q.setdefault("correct", list(q["options"].keys())[0])
        all_questions.extend(valid)
        print(f"     ✓ {len(valid)}/{len(questions)} valid Ordered")
    except RateLimitExhausted:
        raise
    except Exception as e:
        print(f"     ✗ Ordered generation failed: {e}")
    await asyncio.sleep(2)

    # 4. Bow-tie (NGN)
    print(f"  → Bow-tie NGN ({QUESTION_MIX['bowtie']} questions)...")
    prompt = BOWTIE_PROMPT.format(
        count=QUESTION_MIX["bowtie"],
        topic=f"{title} — complex clinical judgment scenarios",
        module_title=title,
    )
    try:
        raw = await groq.generate(prompt)
        questions = extract_json(raw)
        valid = [q for q in questions if validate_bowtie(q)]
        for i, q in enumerate(valid):
            q["question_type"] = "mcq"
            q["ngn_type"] = "bowtie"
            q.setdefault("nclex_client_needs", client_needs_list[-1])
            q.setdefault("cjmm_skill", "prioritize_hypotheses")
            q.setdefault("tags", tags[:2] + ["ngn", "bowtie"])
            q.setdefault("correct", "A")
            q.setdefault("difficulty", "hard")
            if "options" not in q or not q["options"]:
                q["options"] = {"A": "See bow-tie diagram"}
        all_questions.extend(valid)
        print(f"     ✓ {len(valid)}/{len(questions)} valid Bow-tie")
    except RateLimitExhausted:
        raise
    except Exception as e:
        print(f"     ✗ Bow-tie generation failed: {e}")
    await asyncio.sleep(2)

    # 5. Calculation (only for relevant modules)
    if is_calc_module:
        print(f"  → Calculation ({QUESTION_MIX['calculation']} questions)...")
        calc_prompt = f"""Generate {QUESTION_MIX['calculation']} NCLEX-style numeric calculation questions about {title}.
Each question requires computing a specific numeric answer (dose, rate, etc.).
Include step-by-step solution in explanation.

Return ONLY valid JSON array:
[
  {{
    "question": "Clinical calculation scenario...",
    "question_type": "calculation",
    "options": {{}},
    "correct": "",
    "numeric_answer": 9.0,
    "numeric_tolerance": 0.5,
    "numeric_unit": "mL",
    "explanation": "Step 1: ... Step 2: ... Answer: 9 mL",
    "difficulty": "medium",
    "nclex_client_needs": "pharmacological",
    "cjmm_skill": "take_actions",
    "tags": ["dose_calculation"]
  }}
]"""
        try:
            raw = await groq.generate(calc_prompt)
            questions = extract_json(raw)
            valid = [q for q in questions
                     if isinstance(q.get("numeric_answer"), (int, float))
                     and q.get("numeric_unit")]
            for q in valid:
                q["question_type"] = "calculation"
                q.setdefault("nclex_client_needs", "pharmacological")
                q.setdefault("cjmm_skill", "take_actions")
                q.setdefault("options", {})
                q.setdefault("correct", "")
                q["numeric_tolerance"] = float(q.get("numeric_tolerance", 0.5))
                q["numeric_answer"] = float(q["numeric_answer"])
            all_questions.extend(valid)
            print(f"     ✓ {len(valid)}/{len(questions)} valid Calculation")
        except RateLimitExhausted:
            raise
        except Exception as e:
            print(f"     ✗ Calculation generation failed: {e}")
        await asyncio.sleep(2)

    print(f"\n  Total for {module_code}: {len(all_questions)} questions")
    return all_questions


# ── Main ──────────────────────────────────────────────────────────────────────

def _pending_modules() -> list[str]:
    """Return modules that don't yet have an output file with ≥20 questions."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pending = []
    for code in MODULE_META.keys():
        path = OUTPUT_DIR / f"{OUTPUT_PREFIX}{code}.json"
        if not path.exists():
            pending.append(code)
            continue
        try:
            data = json.loads(path.read_text())
            if data.get("total", 0) < 20:  # too few — regenerate
                pending.append(code)
        except Exception:
            pending.append(code)
    return pending


async def main():
    args = sys.argv[1:]

    # --next flag: pick the single next pending module (for cron)
    cron_mode = "--next" in args
    if cron_mode:
        args = [a for a in args if a != "--next"]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if cron_mode and not args:
        pending = _pending_modules()
        if not pending:
            print("✓ All modules already generated — nothing to do.")
            print(f"  Run: python -m app.scripts.import_nclex_questions")
            return
        target_modules = [pending[0]]
        print(f"[CRON] Picking next pending module: {target_modules[0]}")
        print(f"       Remaining after this: {len(pending) - 1} modules")
    else:
        target_modules = args if args else list(MODULE_META.keys())

    invalid = [m for m in target_modules if m not in MODULE_META]
    if invalid:
        print(f"Unknown modules: {invalid}")
        sys.exit(1)

    groq = GroqClient()
    total_generated = 0

    for module_code in target_modules:
        try:
            questions = await generate_for_module(module_code, groq)
        except RateLimitExhausted as e:
            print(f"\n  ⚠ {e}")
            print(f"  Cron will retry this module on the next run.")
            break  # exit loop cleanly; cron picks it up next time

        output_path = OUTPUT_DIR / f"{OUTPUT_PREFIX}{module_code}.json"
        if not questions:
            print(f"  ✗ No valid questions generated for {module_code} — skipping write")
            continue
        output = {
            "module_code": module_code,
            "module_title": MODULE_META[module_code]["title"],
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "total": len(questions),
            "questions": questions,
        }
        output_path.write_text(json.dumps(output, ensure_ascii=False, indent=2))
        print(f"  Saved → {output_path}")
        total_generated += len(questions)

    remaining = len(_pending_modules())
    print(f"\n{'='*60}")
    print(f"  DONE: {total_generated} questions generated this run")
    if remaining > 0:
        print(f"  Remaining modules: {remaining} — cron will handle them")
    else:
        print(f"  All modules complete! Run: python -m app.scripts.import_nclex_questions")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
