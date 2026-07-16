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
# Use only keys not claimed by scheduler (news/article pipelines use KEY_3/4/5/1/2/6)
# GROQ_KEY_MODULE_2 and GROQ_KEY_CASES are dedicated to one-off generation scripts
GROQ_KEYS = [k for k in [
    os.getenv("GROQ_KEY_MODULE_2", ""),
    os.getenv("GROQ_KEY_CASES", ""),
] if k]
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
}

CJMM_SKILLS = [
    "recognize_cues",
    "analyze_cues",
    "prioritize_hypotheses",
    "generate_solutions",
    "take_actions",
    "evaluate_outcomes",
]

# How many questions of each type per module (total 42)
QUESTION_MIX = {
    "mcq": 24,       # standard 4-option MCQ
    "sata": 8,       # Select All That Apply (4-6 options, 2-4 correct)
    "ordered": 4,    # Put-in-order (4-5 steps)
    "calculation": 4, # numeric answer (only NURSE-002, 003, 005 have real calc)
    "bowtie": 2,     # NGN bow-tie (clinical judgment)
}

# Modules with meaningful calculation questions
CALC_MODULES = {"NURSE-002", "NURSE-003", "NURSE-005", "NURSE-006"}

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

Return ONLY valid JSON array, no markdown, no extra text:
[
  {{
    "question": "Clinical scenario...",
    "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
    "correct": "B",
    "explanation": "B is correct because... A is wrong because... C is wrong because...",
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
    def __init__(self):
        self._key_idx = 0

    def _next_key(self) -> str:
        key = GROQ_KEYS[self._key_idx % len(GROQ_KEYS)]
        self._key_idx += 1
        return key

    async def generate(self, prompt: str, max_tokens: int = 4000) -> str:
        for attempt in range(3):
            key = self._next_key()
            if not key:
                raise RuntimeError("No Groq API key configured (GROQ_API_KEY_3 or GROQ_API_KEY_4)")
            try:
                async with httpx.AsyncClient(timeout=90) as client:
                    resp = await client.post(
                        GROQ_URL,
                        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                        json={
                            "model": GROQ_MODEL,
                            "messages": [{"role": "user", "content": prompt}],
                            "max_tokens": max_tokens,
                            "temperature": 0.7,
                        },
                    )
                    resp.raise_for_status()
                    return resp.json()["choices"][0]["message"]["content"]
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    wait = 15 * (attempt + 1)
                    print(f"  Rate limited, waiting {wait}s...")
                    await asyncio.sleep(wait)
                else:
                    raise
        raise RuntimeError("Groq API failed after 3 attempts")


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

    # 1. Standard MCQ
    print(f"  → MCQ ({QUESTION_MIX['mcq']} questions)...")
    prompt = MCQ_PROMPT.format(
        count=QUESTION_MIX["mcq"],
        topic=f"{title} — covering {', '.join(tags)}",
        module_title=title,
        easy=6, medium=12, hard=6,
    )
    try:
        raw = await groq.generate(prompt)
        questions = extract_json(raw)
        valid = [q for q in questions if validate_mcq(q)]
        for i, q in enumerate(valid):
            q["question_type"] = "mcq"
            q.setdefault("nclex_client_needs", client_needs_list[i % len(client_needs_list)])
            q.setdefault("cjmm_skill", cjmm_cycle[i % len(cjmm_cycle)])
            q.setdefault("tags", tags[:2])
            if not q.get("correct"):
                q["correct"] = list(q["options"].keys())[0]
        all_questions.extend(valid)
        print(f"     ✓ {len(valid)}/{len(questions)} valid MCQ")
    except Exception as e:
        print(f"     ✗ MCQ generation failed: {e}")
    await asyncio.sleep(1)

    # 2. SATA
    print(f"  → SATA ({QUESTION_MIX['sata']} questions)...")
    prompt = SATA_PROMPT.format(
        count=QUESTION_MIX["sata"],
        topic=f"{title} — clinical nursing scenarios",
        module_title=title,
    )
    try:
        raw = await groq.generate(prompt)
        questions = extract_json(raw)
        valid = [q for q in questions if validate_sata(q)]
        for i, q in enumerate(valid):
            q["question_type"] = "sata"
            q.setdefault("nclex_client_needs", client_needs_list[i % len(client_needs_list)])
            q.setdefault("cjmm_skill", cjmm_cycle[(i + 2) % len(cjmm_cycle)])
            q.setdefault("tags", tags[:2])
            q.setdefault("correct", list(q["options"].keys())[0])
            q["partial_scoring"] = False
        all_questions.extend(valid)
        print(f"     ✓ {len(valid)}/{len(questions)} valid SATA")
    except Exception as e:
        print(f"     ✗ SATA generation failed: {e}")
    await asyncio.sleep(1)

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
        except Exception as e:
            print(f"     ✗ Calculation generation failed: {e}")
        await asyncio.sleep(2)

    print(f"\n  Total for {module_code}: {len(all_questions)} questions")
    return all_questions


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    target_modules = sys.argv[1:] if len(sys.argv) > 1 else list(MODULE_META.keys())
    invalid = [m for m in target_modules if m not in MODULE_META]
    if invalid:
        print(f"Unknown modules: {invalid}")
        sys.exit(1)

    groq = GroqClient()
    total_generated = 0

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for module_code in target_modules:
        questions = await generate_for_module(module_code, groq)

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

    print(f"\n{'='*60}")
    print(f"  DONE: {total_generated} questions across {len(target_modules)} modules")
    print(f"  Next: python -m app.scripts.import_nclex_questions")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
