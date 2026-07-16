"""
Seed NCLEX question bank with curated expert-written questions.
These supplement AI-generated questions and ensure quality baseline.

Coverage: all 8 NURSE modules, all question types, all NCLEX categories.
Run: python -m app.scripts.nclex_seed_questions
"""

import asyncio
import uuid
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.models import Module, MCQQuestion

# fmt: off
SEED_QUESTIONS = [

# ══════════════════════════════════════════════════════════════════════════════
# NURSE-001: Nursing Process & Documentation
# ══════════════════════════════════════════════════════════════════════════════
{"module_code": "NURSE-001", "question_type": "mcq", "difficulty": "medium",
 "nclex_client_needs": "safe_effective_care", "cjmm_skill": "analyze_cues",
 "question": "A nurse is assessing a 68-year-old patient admitted with heart failure. The patient states 'I can't breathe well when I lie flat.' Which nursing diagnosis is MOST appropriate based on this assessment finding?",
 "options": {"A": "Activity Intolerance related to decreased cardiac output", "B": "Impaired Gas Exchange related to fluid accumulation in lungs", "C": "Disturbed Sleep Pattern related to dyspnea", "D": "Risk for Aspiration related to supine positioning"},
 "correct": "B", "explanation": "Orthopnea (inability to breathe lying flat) with heart failure indicates fluid accumulation in the lungs causing impaired gas exchange. This is the most direct and specific nursing diagnosis. Activity Intolerance may also be present but doesn't address the primary complaint of dyspnea when supine."},

{"module_code": "NURSE-001", "question_type": "sata", "difficulty": "medium",
 "nclex_client_needs": "safe_effective_care", "cjmm_skill": "take_actions",
 "question": "A nurse is documenting a patient's care plan using the ADPIE framework. Which of the following are correctly categorized as 'Assessment' components? Select all that apply.",
 "options": {"A": "Vital signs: BP 148/92, HR 88", "B": "Administer metoprolol 25 mg PO daily", "C": "Patient reports headache rated 7/10", "D": "Educate patient on low-sodium diet", "E": "Bilateral pitting edema 2+ in lower extremities"},
 "correct_answers": ["A", "C", "E"], "correct": "A",
 "explanation": "A, C, and E are assessment data — objective (VS, edema) and subjective (headache report). B is an intervention (administering medication) and D is an intervention (education). Assessment is the first step of ADPIE and includes all data gathered about the patient."},

{"module_code": "NURSE-001", "question_type": "ordered", "difficulty": "easy",
 "nclex_client_needs": "safe_effective_care", "cjmm_skill": "take_actions",
 "question": "Place the steps of the ADPIE nursing process in the correct order.",
 "options": {"A": "Planning — set SMART goals with patient", "B": "Assessment — gather subjective and objective data", "C": "Evaluation — determine if goals were met", "D": "Nursing Diagnosis — identify patient problems", "E": "Implementation — carry out interventions"},
 "correct_order": ["B", "D", "A", "E", "C"], "correct": "B",
 "explanation": "ADPIE: Assessment → Diagnosis → Planning → Implementation → Evaluation. Assessment provides the data foundation. Diagnosis identifies the problem. Planning sets goals. Implementation executes interventions. Evaluation determines outcome."},

{"module_code": "NURSE-001", "question_type": "mcq", "difficulty": "hard",
 "nclex_client_needs": "safe_effective_care", "cjmm_skill": "prioritize_hypotheses",
 "question": "A nurse uses SBAR to hand off a patient to the oncoming shift. The patient has a temp of 38.9°C, BP 90/58, HR 122, and confusion. Using SBAR, which information belongs in the 'Background' component?",
 "options": {"A": "BP 90/58, HR 122, temp 38.9°C, new confusion", "B": "Patient is a 54-year-old with Type 2 diabetes admitted 2 days ago with a UTI", "C": "I am concerned the patient may be developing sepsis", "D": "Recommend blood cultures x2, IV fluid bolus, and physician notification immediately"},
 "correct": "B", "explanation": "SBAR: Situation (current issue), Background (relevant history/context), Assessment (nurse's clinical judgment), Recommendation (what is needed). B — the patient's age, diagnosis, and admission reason — is Background. A is Situation, C is Assessment, D is Recommendation."},

{"module_code": "NURSE-001", "question_type": "mcq", "difficulty": "easy",
 "nclex_client_needs": "safe_effective_care", "cjmm_skill": "take_actions",
 "question": "A nurse must document a medication error. Which principle of legal documentation is MOST important in this situation?",
 "options": {"A": "Document only what you observed, using objective language", "B": "Write 'error' prominently and describe what should have happened", "C": "Avoid documenting the error in the chart; file an incident report only", "D": "Use correction fluid to remove the incorrect entry before documenting correctly"},
 "correct": "A", "explanation": "Legal documentation requires accuracy, objectivity, and factual recording. Document what happened factually using objective terms. Never use correction fluid (use single line through error with initials). The medical record should reflect what occurred; incident reports are separate. Never avoid documenting significant events."},

{"module_code": "NURSE-001", "question_type": "mcq", "difficulty": "medium",
 "nclex_client_needs": "health_promotion", "cjmm_skill": "generate_solutions",
 "question": "A nurse is writing a nursing diagnosis for a patient who is newly diagnosed with Type 2 diabetes. The patient states 'I don't know what I'm supposed to eat.' Which nursing diagnosis is MOST appropriate?",
 "options": {"A": "Ineffective Health Management related to lack of understanding of therapeutic regimen", "B": "Noncompliance related to new diabetes diagnosis", "C": "Risk for Unstable Blood Glucose Level related to lack of knowledge", "D": "Deficient Knowledge: Diabetic Diet related to new diagnosis as evidenced by patient verbalization"},
 "correct": "D", "explanation": "D uses the correct PES format (Problem + Etiology + Signs/Symptoms) for an actual nursing diagnosis. The patient has verbalized lack of knowledge (evidence). Noncompliance (B) is inappropriate — the patient hasn't been given the chance to comply yet. Risk diagnoses (C) are used for potential problems, not actual ones with evidence."},

# ══════════════════════════════════════════════════════════════════════════════
# NURSE-002: Medication Safety
# ══════════════════════════════════════════════════════════════════════════════
{"module_code": "NURSE-002", "question_type": "sata", "difficulty": "medium",
 "nclex_client_needs": "pharmacological", "cjmm_skill": "recognize_cues",
 "question": "A nurse is preparing to administer medications. Which of the following are included in the 5 Rights of Medication Administration? Select all that apply.",
 "options": {"A": "Right patient", "B": "Right route", "C": "Right prescriber", "D": "Right dose", "E": "Right time", "F": "Right documentation"},
 "correct_answers": ["A", "B", "D", "E"], "correct": "A",
 "explanation": "The 5 Rights are: Right Patient, Right Medication, Right Dose, Right Route, Right Time. Documentation and prescriber are NOT traditionally in the core 5 Rights (though some institutions add Right Documentation as a 6th Right). The core 5 focus on safe administration, not ordering."},

{"module_code": "NURSE-002", "question_type": "mcq", "difficulty": "hard",
 "nclex_client_needs": "pharmacological", "cjmm_skill": "prioritize_hypotheses",
 "question": "A nurse receives an order for heparin 5000 units IV bolus. The pharmacy sends heparin 10,000 units/mL. A colleague says 'Just give 0.5 mL, that's correct.' What should the nurse do FIRST?",
 "options": {"A": "Trust the colleague's calculation and administer 0.5 mL", "B": "Independently verify the calculation: 5000 units ÷ 10,000 units/mL = 0.5 mL, then administer", "C": "Call pharmacy to confirm the concentration before administration", "D": "Refuse to administer until a pharmacist double-checks"},
 "correct": "B", "explanation": "Heparin is a high-alert medication requiring independent double-check. The nurse should always perform their OWN independent calculation — 5000 ÷ 10,000 = 0.5 mL is correct. Independent verification (not relying on another's calculation) is the safe practice. The calculation is straightforward and correct, so calling pharmacy is not required once verified independently."},

{"module_code": "NURSE-002", "question_type": "ordered", "difficulty": "medium",
 "nclex_client_needs": "pharmacological", "cjmm_skill": "take_actions",
 "question": "Place the steps for safe medication administration in the correct order.",
 "options": {"A": "Administer medication using appropriate technique", "B": "Verify 5 rights at bedside with patient ID band", "C": "Document medication given in MAR immediately", "D": "Perform hand hygiene and prepare medication in clean area"},
 "correct_order": ["D", "B", "A", "C"], "correct": "D",
 "explanation": "Safe sequence: Hand hygiene + preparation → Verify 5 rights at bedside → Administer → Document. Never document before administration (anticipatory documentation is unsafe). The 5 rights check at the bedside (not at the med cart) prevents errors from interrupted checks."},

{"module_code": "NURSE-002", "question_type": "mcq", "difficulty": "medium",
 "nclex_client_needs": "pharmacological", "cjmm_skill": "recognize_cues",
 "question": "Which of the following medications is classified as a High-Alert Medication (HAM) requiring extra safety checks before administration?",
 "options": {"A": "Acetaminophen 500 mg PO", "B": "Amoxicillin 500 mg PO", "C": "Concentrated potassium chloride IV", "D": "Ondansetron 4 mg IV"},
 "correct": "C", "explanation": "Concentrated potassium chloride IV is a classic high-alert medication that can cause fatal cardiac arrest if administered as an IV push. HAMs include anticoagulants, concentrated electrolytes, chemotherapy, insulin, opioids, and neuromuscular blockers. Acetaminophen, amoxicillin, and ondansetron at standard doses are not high-alert medications."},

{"module_code": "NURSE-002", "question_type": "sata", "difficulty": "hard",
 "nclex_client_needs": "safe_effective_care", "cjmm_skill": "generate_solutions",
 "question": "A nurse discovers they administered metformin 500 mg to the wrong patient. The patient was not prescribed metformin and has no known allergies. Which actions should the nurse take? Select all that apply.",
 "options": {"A": "Assess the patient immediately for adverse effects", "B": "Notify the physician of the error", "C": "Document the error and all actions taken in the medical record", "D": "File an incident/occurrence report", "E": "Ask the patient not to tell family members"},
 "correct_answers": ["A", "B", "C", "D"], "correct": "A",
 "explanation": "A through D are all required after a medication error: immediate patient assessment, physician notification, factual chart documentation, and incident report. E is unacceptable — patients have the right to know what happened, and concealing errors is unethical and potentially illegal. Transparency is the standard of care."},

{"module_code": "NURSE-002", "question_type": "calculation", "difficulty": "medium",
 "nclex_client_needs": "pharmacological", "cjmm_skill": "take_actions",
 "question": "A patient is ordered vancomycin 1250 mg IV. The pharmacy sends vancomycin 500 mg/100 mL. How many mL should the nurse administer?",
 "options": {}, "correct": "", "numeric_answer": 250.0, "numeric_tolerance": 5.0, "numeric_unit": "mL",
 "explanation": "Step 1: 1250 mg ÷ 500 mg = 2.5 bags. Step 2: 2.5 × 100 mL = 250 mL total volume to administer."},

# ══════════════════════════════════════════════════════════════════════════════
# NURSE-003: Dose Calculations & IV Therapy
# ══════════════════════════════════════════════════════════════════════════════
{"module_code": "NURSE-003", "question_type": "calculation", "difficulty": "medium",
 "nclex_client_needs": "pharmacological", "cjmm_skill": "take_actions",
 "question": "A patient weighing 88 kg requires dopamine at 5 mcg/kg/min. The pharmacy provides dopamine 400 mg in 250 mL D5W. What infusion rate in mL/h should the nurse program on the IV pump?",
 "options": {}, "correct": "", "numeric_answer": 16.5, "numeric_tolerance": 0.5, "numeric_unit": "mL/h",
 "explanation": "Step 1: Dose = 5 mcg/kg/min × 88 kg = 440 mcg/min. Step 2: Concentration = 400,000 mcg ÷ 250 mL = 1600 mcg/mL. Step 3: Rate = 440 mcg/min ÷ 1600 mcg/mL = 0.275 mL/min. Step 4: 0.275 × 60 = 16.5 mL/h."},

{"module_code": "NURSE-003", "question_type": "calculation", "difficulty": "easy",
 "nclex_client_needs": "pharmacological", "cjmm_skill": "take_actions",
 "question": "An IV order reads: 1 L of NS to infuse over 8 hours. The IV tubing has a drop factor of 20 gtt/mL. What is the correct drip rate in gtt/min?",
 "options": {}, "correct": "", "numeric_answer": 41.7, "numeric_tolerance": 1.0, "numeric_unit": "gtt/min",
 "explanation": "Formula: (Volume × Drop factor) ÷ Time in minutes = (1000 mL × 20 gtt/mL) ÷ 480 min = 20,000 ÷ 480 = 41.7 gtt/min. Round to 42 gtt/min in practice (within tolerance)."},

{"module_code": "NURSE-003", "question_type": "calculation", "difficulty": "medium",
 "nclex_client_needs": "pharmacological", "cjmm_skill": "take_actions",
 "question": "A child weighing 22 kg requires amoxicillin 40 mg/kg/day divided every 8 hours. The suspension is 250 mg/5 mL. How many mL per dose should the nurse administer?",
 "options": {}, "correct": "", "numeric_answer": 5.9, "numeric_tolerance": 0.3, "numeric_unit": "mL",
 "explanation": "Step 1: Daily dose = 40 mg/kg × 22 kg = 880 mg/day. Step 2: Per-dose = 880 ÷ 3 doses = 293.3 mg. Step 3: Volume = 293.3 mg ÷ 250 mg × 5 mL = 5.87 mL ≈ 5.9 mL."},

{"module_code": "NURSE-003", "question_type": "sata", "difficulty": "medium",
 "nclex_client_needs": "reduction_risk", "cjmm_skill": "recognize_cues",
 "question": "A nurse is monitoring a patient receiving IV potassium chloride 40 mEq in 500 mL NS at 125 mL/h. Which assessment findings should the nurse report immediately? Select all that apply.",
 "options": {"A": "Serum K+ 5.8 mEq/L", "B": "Urine output 30 mL/h", "C": "ECG showing peaked T-waves", "D": "Patient reports burning at IV site", "E": "BP 118/74 mmHg"},
 "correct_answers": ["A", "C", "D"], "correct": "A",
 "explanation": "A (K+ 5.8 — hyperkalemia, stop infusion), C (peaked T-waves — cardiac hyperkalemia effect), D (burning — phlebitis or extravasation, stop infusion). B (urine 30 mL/h is acceptable minimum for KCl admin — would concern at <30), E (normal BP)."},

{"module_code": "NURSE-003", "question_type": "mcq", "difficulty": "medium",
 "nclex_client_needs": "pharmacological", "cjmm_skill": "take_actions",
 "question": "A patient has an order for morphine 4 mg IV PRN. The nurse prepares a 10 mg/mL vial. How many mL should the nurse draw up to administer 4 mg?",
 "options": {"A": "0.2 mL", "B": "0.4 mL", "C": "4 mL", "D": "2.5 mL"},
 "correct": "B", "explanation": "4 mg ÷ 10 mg/mL = 0.4 mL. This is a high-alert medication calculation — always double-check. Many nursing errors occur with morphine due to concentration confusion."},

# ══════════════════════════════════════════════════════════════════════════════
# NURSE-004: Infection Control & Hand Hygiene
# ══════════════════════════════════════════════════════════════════════════════
{"module_code": "NURSE-004", "question_type": "ordered", "difficulty": "easy",
 "nclex_client_needs": "safe_effective_care", "cjmm_skill": "take_actions",
 "question": "A nurse is putting on PPE to enter the room of a patient on contact precautions. Place the donning sequence in the correct order.",
 "options": {"A": "Gloves (over cuffs)", "B": "Gown", "C": "Hand hygiene", "D": "Mask/respirator (if needed)", "E": "Goggles/face shield (if needed)"},
 "correct_order": ["C", "B", "D", "E", "A"], "correct": "C",
 "explanation": "PPE donning order: Hand hygiene → Gown → Mask → Eye protection → Gloves. Gloves go on last to cover gown cuffs. This sequence protects the nurse from contamination. Doffing is the reverse (gloves first, hand hygiene between each step)."},

{"module_code": "NURSE-004", "question_type": "sata", "difficulty": "medium",
 "nclex_client_needs": "safe_effective_care", "cjmm_skill": "generate_solutions",
 "question": "A patient is admitted with C. difficile infection. Which infection control measures should the nurse implement? Select all that apply.",
 "options": {"A": "Place patient in a private room", "B": "Use alcohol-based hand sanitizer after patient care", "C": "Wear gown and gloves for all contact with patient", "D": "Use soap and water for hand hygiene", "E": "Use N95 respirator for routine care"},
 "correct_answers": ["A", "C", "D"], "correct": "A",
 "explanation": "C. diff requires Contact Precautions: private room (A), gown and gloves (C), and crucially — soap and water NOT alcohol (D). Alcohol-based sanitizers do NOT kill C. diff spores (B is wrong). N95 is for airborne precautions — C. diff is contact only (E is wrong)."},

{"module_code": "NURSE-004", "question_type": "mcq", "difficulty": "hard",
 "nclex_client_needs": "safe_effective_care", "cjmm_skill": "recognize_cues",
 "question": "A patient with active pulmonary tuberculosis is being admitted. Which type of isolation precaution is REQUIRED, and what specific room requirement applies?",
 "options": {"A": "Contact precautions in any private room", "B": "Droplet precautions with door closed", "C": "Airborne precautions in a negative-pressure room", "D": "Standard precautions only — TB is not airborne after treatment starts"},
 "correct": "C", "explanation": "Active TB requires Airborne Precautions: negative-pressure room (air flows in, not out), N95 respirators for healthcare workers, and door kept closed. TB is spread by airborne droplet nuclei (<5 microns) that remain suspended in air. Surgical masks are insufficient — N95 or higher is required."},

{"module_code": "NURSE-004", "question_type": "mcq", "difficulty": "medium",
 "nclex_client_needs": "safe_effective_care", "cjmm_skill": "take_actions",
 "question": "According to WHO's 5 Moments for Hand Hygiene, when should hand hygiene be performed BEFORE touching a patient?",
 "options": {"A": "Only if the patient appears visibly ill", "B": "Before any patient contact, including straightening their bed linens", "C": "Before invasive procedures only", "D": "Only after removing gloves"},
 "correct": "B", "explanation": "WHO Moment 1 is 'Before Touching a Patient' — this applies to ALL patient contact including non-invasive activities like adjusting pillows or checking IV lines. Hand hygiene protects the patient from organisms on the nurse's hands. It applies even if gloves will be worn."},

# ══════════════════════════════════════════════════════════════════════════════
# NURSE-005: Recognising Deterioration (NEWS2)
# ══════════════════════════════════════════════════════════════════════════════
{"module_code": "NURSE-005", "question_type": "mcq", "difficulty": "hard",
 "nclex_client_needs": "physiological_adaptation", "cjmm_skill": "prioritize_hypotheses",
 "question": "A 72-year-old patient has the following NEWS2 parameters: RR 24, SpO2 91% (on O2), BP 88/56, HR 116, Temp 38.8°C, and is confused. What is the PRIORITY nursing action?",
 "options": {"A": "Reassess in 30 minutes and document findings", "B": "Notify the physician using SBAR and request urgent review", "C": "Administer antipyretic and recheck temp", "D": "Increase oxygen flow rate and continue monitoring"},
 "correct": "B", "explanation": "This patient has a high NEWS2 score (each parameter scores 2-3: RR=2, SpO2=2, BP=3, HR=2, Temp=1, AVPU=3 = ~13/20). A score ≥7 requires EMERGENCY response — immediate physician notification using SBAR. Waiting 30 min or only adjusting O2 is dangerous given this hemodynamic profile suggesting early septic shock."},

{"module_code": "NURSE-005", "question_type": "sata", "difficulty": "hard",
 "nclex_client_needs": "physiological_adaptation", "cjmm_skill": "generate_solutions",
 "question": "A nurse suspects a patient is developing sepsis (Sepsis Six protocol). Which interventions should be initiated WITHIN THE FIRST HOUR? Select all that apply.",
 "options": {"A": "Administer high-flow oxygen", "B": "Take blood cultures x2 before antibiotics", "C": "Start broad-spectrum antibiotics", "D": "Give IV fluid challenge", "E": "Check serum lactate"},
 "correct_answers": ["A", "B", "C", "D", "E"], "correct": "A",
 "explanation": "All 5 are part of the Sepsis Six 'give 3, take 3' — Give: O2 (A), IV fluids (D), antibiotics (C); Take: blood cultures (B), lactate (E), urine output measurement. The full Sepsis Six must be completed within 1 hour of recognition. Blood cultures BEFORE antibiotics but do not delay antibiotics for cultures."},

{"module_code": "NURSE-005", "question_type": "mcq", "difficulty": "medium",
 "nclex_client_needs": "physiological_adaptation", "cjmm_skill": "recognize_cues",
 "question": "A nurse is calculating a NEWS2 score. The patient has: RR 22 breaths/min, SpO2 95% (no supplemental O2), BP 112/70, HR 102, Temp 37.2°C, alert and oriented. What component scores 2 points?",
 "options": {"A": "SpO2 95%", "B": "Heart rate 102", "C": "Blood pressure 112/70", "D": "Respiratory rate 22"},
 "correct": "D", "explanation": "NEWS2 scoring: RR 21-24 = 2 points. HR 101-110 = 1 point. SpO2 94-95% = 1 point. BP 111-120 = 1 point. Temperature 36.1-38.0°C = 0 points. So RR 22 is the only parameter scoring 2 points. Total NEWS2 ≈ 5 — medium clinical risk requiring increased monitoring."},

{"module_code": "NURSE-005", "question_type": "calculation", "difficulty": "medium",
 "nclex_client_needs": "reduction_risk", "cjmm_skill": "analyze_cues",
 "question": "A patient with sepsis receives a fluid challenge of 30 mL/kg. The patient weighs 70 kg. How many mL of fluid should be administered in this bolus?",
 "options": {}, "correct": "", "numeric_answer": 2100.0, "numeric_tolerance": 50.0, "numeric_unit": "mL",
 "explanation": "30 mL/kg × 70 kg = 2100 mL. The Sepsis-3 bundle recommends 30 mL/kg crystalloid IV fluid for sepsis-induced hypoperfusion, administered within 3 hours. Reassess after each 500 mL bolus for fluid responsiveness."},

# ══════════════════════════════════════════════════════════════════════════════
# NURSE-006: Emergency Skills
# ══════════════════════════════════════════════════════════════════════════════
{"module_code": "NURSE-006", "question_type": "ordered", "difficulty": "medium",
 "nclex_client_needs": "physiological_adaptation", "cjmm_skill": "take_actions",
 "question": "A nurse witnesses an adult patient collapse. Place the BLS sequence in the correct order.",
 "options": {"A": "Begin chest compressions 30:2", "B": "Shout for help / activate emergency response", "C": "Check for pulse (no more than 10 seconds)", "D": "Ensure scene safety and check patient responsiveness", "E": "Apply AED and deliver shock if advised"},
 "correct_order": ["D", "B", "C", "A", "E"], "correct": "D",
 "explanation": "AHA BLS sequence: Scene safety + responsiveness → Activate EMS → Check pulse/breathing (≤10 sec) → Begin CPR 30:2 → AED as soon as available. Note: In healthcare settings, activate the code team (B) immediately upon finding an unresponsive patient."},

{"module_code": "NURSE-006", "question_type": "mcq", "difficulty": "hard",
 "nclex_client_needs": "physiological_adaptation", "cjmm_skill": "take_actions",
 "question": "A patient receives penicillin IV and within 5 minutes develops: urticaria, stridor, wheezing, and BP 78/40. Which medication is the FIRST priority treatment?",
 "options": {"A": "Diphenhydramine 50 mg IV", "B": "Methylprednisolone 125 mg IV", "C": "Epinephrine 0.3 mg IM (1:1000 concentration)", "D": "Albuterol nebulizer"},
 "correct": "C", "explanation": "Anaphylaxis treatment: Epinephrine IM (thigh) is ALWAYS first-line — it reverses all 3 life-threatening components: bronchospasm, vasodilation, and angioedema. It must be given IMMEDIATELY. Antihistamines (A) are second-line and do NOT reverse anaphylaxis. Corticosteroids (B) take hours to work. Albuterol (D) addresses bronchospasm only."},

{"module_code": "NURSE-006", "question_type": "sata", "difficulty": "medium",
 "nclex_client_needs": "physiological_adaptation", "cjmm_skill": "recognize_cues",
 "question": "A nurse is performing a neurological assessment on a post-op patient. Which findings indicate a DECLINE in neurological status requiring immediate reporting? Select all that apply.",
 "options": {"A": "GCS drops from 15 to 11", "B": "Pupils equal and reactive at 3 mm", "C": "Patient becomes increasingly restless and agitated", "D": "New slurred speech", "E": "BP 122/78 (baseline 120/80)"},
 "correct_answers": ["A", "C", "D"], "correct": "A",
 "explanation": "A (GCS drop of 4 points), C (new agitation — often earliest sign of neurological deterioration or hypoxia), D (new slurred speech) all indicate declining neuro status. B (equal reactive pupils) is normal. E (BP barely changed) is not significant."},

# ══════════════════════════════════════════════════════════════════════════════
# NURSE-007: Patient Care — Wounds, Falls, Mobility
# ══════════════════════════════════════════════════════════════════════════════
{"module_code": "NURSE-007", "question_type": "mcq", "difficulty": "medium",
 "nclex_client_needs": "basic_care", "cjmm_skill": "analyze_cues",
 "question": "A nurse assesses a patient's sacral wound and documents: '3 cm × 2 cm wound, base is yellow with slough, wound edges are well-defined, no tunneling, surrounding skin is erythematous.' Based on NPUAP staging, what is this pressure injury?",
 "options": {"A": "Stage 1 — non-blanchable erythema", "B": "Stage 2 — partial thickness skin loss", "C": "Stage 3 — full thickness skin loss", "D": "Unstageable — slough obscures depth"},
 "correct": "D", "explanation": "Unstageable pressure injuries cannot be staged because slough or eschar covering the wound base obscures the depth of tissue loss. The wound must be debrided before staging is possible. Until the base is visible, it is classified as Unstageable regardless of size. If slough were removed and it was a full-thickness wound, it would be Stage 3 or 4."},

{"module_code": "NURSE-007", "question_type": "sata", "difficulty": "medium",
 "nclex_client_needs": "reduction_risk", "cjmm_skill": "generate_solutions",
 "question": "A patient scores 16 on the Morse Fall Scale. Which interventions should the nurse implement? Select all that apply.",
 "options": {"A": "Apply yellow fall-risk wristband", "B": "Keep bed in lowest position with call light in reach", "C": "Order a 1:1 sitter", "D": "Educate patient on fall prevention", "E": "Document risk level and interventions in care plan"},
 "correct_answers": ["A", "B", "D", "E"], "correct": "A",
 "explanation": "Morse score 0-24 = Low risk. Standard fall precautions: visual identifier (A), bed position + call light (B), education (D), documentation (E). A 1:1 sitter (C) is for high-risk patients (Morse ≥ 45) or those who cannot follow fall-prevention instructions. Score 16 is low risk — sitter is not indicated and wastes resources."},

{"module_code": "NURSE-007", "question_type": "mcq", "difficulty": "easy",
 "nclex_client_needs": "basic_care", "cjmm_skill": "generate_solutions",
 "question": "A nurse is turning a patient with a Braden score of 10 to prevent pressure injuries. What is the MINIMUM recommended repositioning frequency for this patient?",
 "options": {"A": "Every 4 hours", "B": "Every 2 hours", "C": "Every 1 hour", "D": "Every shift (8 hours)"},
 "correct": "B", "explanation": "A Braden score of 10 = High risk (scores ≤12 are high risk, 13-14 moderate, 15-18 mild, 19-23 no risk). High-risk patients require repositioning every 2 hours minimum to relieve pressure. Lower scores indicate greater risk; some facilities increase to every 1 hour for very high-risk patients. Every 4 or 8 hours is insufficient."},

# ══════════════════════════════════════════════════════════════════════════════
# NURSE-008: Communication, Family & SBAR Handoff
# ══════════════════════════════════════════════════════════════════════════════
{"module_code": "NURSE-008", "question_type": "sata", "difficulty": "medium",
 "nclex_client_needs": "psychosocial", "cjmm_skill": "generate_solutions",
 "question": "A nurse is using therapeutic communication with a patient who is crying and states 'I'm so scared about my surgery tomorrow.' Which responses demonstrate therapeutic communication? Select all that apply.",
 "options": {"A": "'I understand how you feel. Tell me more about what worries you most.'", "B": "'Don't worry, the surgeon does this every day.'", "C": "'It sounds like you're feeling frightened. What can I do to help?'", "D": "'Surgery is always scary but you'll be fine.'", "E": "'Your fear makes sense. Would you like me to sit with you for a while?'"},
 "correct_answers": ["A", "C", "E"], "correct": "A",
 "explanation": "Therapeutic techniques: A (open-ended + validation), C (reflection + empathy + open-ended), E (validation + presence). Non-therapeutic: B ('Don't worry' dismisses feelings; false reassurance), D ('you'll be fine' is false reassurance that disregards the patient's fear and avoids engagement."},

{"module_code": "NURSE-008", "question_type": "mcq", "difficulty": "medium",
 "nclex_client_needs": "safe_effective_care", "cjmm_skill": "evaluate_outcomes",
 "question": "A nurse uses teach-back to evaluate patient understanding of a new insulin injection technique. The patient correctly demonstrates the technique on a model. What should the nurse document?",
 "options": {"A": "'Patient education provided regarding insulin injection.'", "B": "'Patient verbalizes understanding of insulin injection technique.'", "C": "'Patient correctly demonstrated subcutaneous insulin injection using teach-back method on anatomical model.'", "D": "'Insulin education completed. Patient compliant.'"},
 "correct": "C", "explanation": "Effective documentation of teach-back includes WHAT was taught, HOW it was evaluated (teach-back demonstration), and WHAT the patient did (correctly demonstrated). A is vague — no evidence of understanding. B only documents verbalization, not demonstration. D uses the problematic term 'compliant' (implies judgment) and lacks specifics."},

{"module_code": "NURSE-008", "question_type": "ordered", "difficulty": "medium",
 "nclex_client_needs": "safe_effective_care", "cjmm_skill": "take_actions",
 "question": "A nurse is completing an SBAR handoff for a patient being transferred to the ICU. Place the SBAR components in the correct order of presentation.",
 "options": {"A": "Assessment — 'I believe she is developing septic shock based on MAP 58, lactate 4.2, and temperature 39.1°C'", "B": "Recommendation — 'She needs urgent ICU admission, vasopressors ready, and ID consult for antibiotics'", "C": "Situation — 'I'm calling about Mrs. Chen in room 412, a 61-year-old admitted for pneumonia who is now hypotensive'", "D": "Background — 'She has diabetes and CKD, was started on ceftriaxone 12 hours ago, and has had 2L NS without improvement'"},
 "correct_order": ["C", "D", "A", "B"], "correct": "C",
 "explanation": "SBAR: Situation → Background → Assessment → Recommendation. Situation first (who, what problem). Background (relevant history, current treatment). Assessment (your clinical judgment). Recommendation (what you need). This structured communication reduces ambiguity and ensures the receiving provider has context before hearing the recommendation."},

{"module_code": "NURSE-008", "question_type": "mcq", "difficulty": "medium",
 "nclex_client_needs": "psychosocial", "cjmm_skill": "generate_solutions",
 "question": "A nurse is caring for a patient with terminal cancer who says 'I just want to go home and spend my last days with family. The doctors keep suggesting more treatments.' Which nursing response BEST demonstrates patient advocacy?",
 "options": {"A": "Encourage the patient to try one more round of treatment before deciding", "B": "Notify the physician of the patient's wishes and request a palliative care consult", "C": "Tell the patient their family needs them to fight and not give up", "D": "Document the statement and wait for the physician to bring it up"},
 "correct": "B", "explanation": "Patient advocacy means acting in the patient's best interest and ensuring their voice is heard. B: notifying the physician AND requesting palliative care (the correct team for this conversation) is the best advocacy action. A and C are persuasive and disregard the patient's autonomy. D is passive — the nurse has an obligation to act proactively."},

{"module_code": "NURSE-008", "question_type": "sata", "difficulty": "medium",
 "nclex_client_needs": "psychosocial", "cjmm_skill": "take_actions",
 "question": "A nurse is caring for a patient who is deaf and uses American Sign Language (ASL). Which actions should the nurse take to ensure effective communication? Select all that apply.",
 "options": {"A": "Request a qualified ASL interpreter before any significant discussion", "B": "Communicate by writing notes on paper for routine care", "C": "Ask a family member to interpret all clinical information", "D": "Face the patient directly and maintain eye contact when speaking", "E": "Ensure adequate lighting so the patient can see interpreter clearly"},
 "correct_answers": ["A", "D", "E"], "correct": "A",
 "explanation": "A (qualified interpreter — legal requirement for significant information), D (direct eye contact shows respect and aids communication), E (lighting essential for visual communication). B (paper notes — acceptable for very brief exchanges but inadequate for complex information). C (family interpreters are inappropriate — privacy issues, bias, lack of medical vocabulary — prohibited for consent and clinical discussions by HIPAA/ADA)."},

{"module_code": "NURSE-008", "question_type": "mcq", "difficulty": "easy",
 "nclex_client_needs": "psychosocial", "cjmm_skill": "recognize_cues",
 "question": "A patient with newly diagnosed HIV states 'Please don't tell anyone I'm here or why.' The patient's employer calls the unit asking to confirm admission. What should the nurse say?",
 "options": {"A": "Confirm the admission but say nothing about the diagnosis", "B": "'I cannot confirm or deny that any patient is admitted here.'", "C": "Confirm the admission since the employer may need to know", "D": "Put the employer on hold and ask the patient's permission"},
 "correct": "B", "explanation": "HIPAA requires confidentiality. The nurse cannot confirm OR deny a patient's presence without the patient's explicit consent (even for admission status). B is the legally correct response — it neither confirms nor denies. A violates confidentiality by confirming admission. C clearly violates HIPAA. D is procedurally incorrect — you do not place callers on hold to ask patients; the answer should be immediate."},

{"module_code": "NURSE-008", "question_type": "ordered", "difficulty": "medium",
 "nclex_client_needs": "safe_effective_care", "cjmm_skill": "take_actions",
 "question": "A nurse needs to obtain informed consent for an urgent procedure. Place the steps in the correct order.",
 "options": {"A": "Witness the patient's signature on the consent form", "B": "Assess the patient's capacity to make decisions", "C": "Ensure the physician has explained risks, benefits, and alternatives", "D": "Ask the patient to verbalize understanding of the procedure"},
 "correct_order": ["B", "C", "D", "A"], "correct": "B",
 "explanation": "Informed consent sequence: Assess decision-making capacity (B — can't consent without capacity) → Physician explanation of risks/benefits/alternatives (C — this is the physician's legal responsibility) → Teach-back to verify understanding (D) → Witness signature (A). The nurse witnesses consent but does not obtain it — obtaining consent is the physician/provider's responsibility."},

{"module_code": "NURSE-008", "question_type": "mcq", "difficulty": "hard",
 "nclex_client_needs": "psychosocial", "cjmm_skill": "analyze_cues",
 "question": "A nurse notices that a teenage patient becomes withdrawn and gives one-word answers whenever a parent enters the room but communicates openly alone. The patient has unexplained bruising on the upper arms. What is the PRIORITY nursing action?",
 "options": {"A": "Document the behavioral change and continue monitoring", "B": "Ask the parent directly about the bruising during the family assessment", "C": "Privately ask the patient open-ended questions about their safety and relationship at home", "D": "Call child protective services immediately based on the behavioral pattern"},
 "correct": "C", "explanation": "These are red flags for abuse (unexplained bruising + behavioural change with parent). Priority: assess privately first — ask the patient open-ended questions ('Tell me about what's happening at home. Do you ever feel unsafe?'). C establishes safety and gathers information without endangering the patient. D is premature without further assessment. A ignores the concern. B confronting the parent may endanger the patient."},

{"module_code": "NURSE-008", "question_type": "mcq", "difficulty": "medium",
 "nclex_client_needs": "psychosocial", "cjmm_skill": "take_actions",
 "question": "A nurse is discharging a patient who does not speak English. The discharge instructions are complex and include medication dosing, wound care, and follow-up appointments. Which action is MOST appropriate?",
 "options": {"A": "Provide written instructions in English and ask the patient to have a friend translate", "B": "Use a picture-based instruction sheet only", "C": "Use a qualified medical interpreter and provide instructions translated in the patient's language", "D": "Ask a bilingual nurse from another unit to translate"},
 "correct": "C", "explanation": "Complex discharge instructions require professional medical interpretation and written materials in the patient's language. C: qualified interpreter + translated written materials is the gold standard. A (English-only written materials) is inadequate. B (pictures only) is insufficient for complex medication instructions. D (informal interpretation from staff) is not appropriate — staff may not have adequate medical translation skills and this creates liability."},

{"module_code": "NURSE-008", "question_type": "mcq", "difficulty": "medium",
 "nclex_client_needs": "health_promotion", "cjmm_skill": "evaluate_outcomes",
 "question": "A nurse uses the teach-back method with a diabetic patient about hypoglycemia management. The patient correctly states what to do when blood sugar is low. Which additional teach-back verification should the nurse perform?",
 "options": {"A": "Have the patient teach the information back to a family member", "B": "Ask the patient to demonstrate checking their blood sugar and treating a low reading", "C": "Provide a written quiz and grade their answers", "D": "The teach-back is complete — verbal recall is sufficient"},
 "correct": "B", "explanation": "Effective teach-back for psychomotor skills requires DEMONSTRATION, not just verbal recall. Hypoglycemia management includes both recognizing symptoms AND correctly using the glucometer and treating with fast-acting glucose. B verifies the full skill. A (teaching a family member) is a more advanced technique but not the next step. C (written quiz) is not part of standard teach-back. D is insufficient for procedural skills."},

{"module_code": "NURSE-008", "question_type": "mcq", "difficulty": "hard",
 "nclex_client_needs": "safe_effective_care", "cjmm_skill": "prioritize_hypotheses",
 "question": "The nurse-to-patient ratio on a medical-surgical floor is suddenly increased from 1:4 to 1:8 due to a staffing shortage. A nurse is asked to accept 4 additional patients. What is the nurse's BEST initial action?",
 "options": {"A": "Accept the assignment and work as fast as possible", "B": "Refuse to work and leave the unit", "C": "Accept under protest in writing, notify the charge nurse and supervisor formally, and prioritize by acuity", "D": "Ask patients to call family to help with basic care"},
 "correct": "C", "explanation": "Nurses cannot abandon patients (B is abandonment). However, a nurse should: accept the assignment under protest to protect patients immediately, document the objection in writing (formal objection form), notify charge nurse and nursing supervisor for escalation, and prioritize care by acuity. This protects both patients and the nurse's license. A (silent acceptance) fails to document the unsafe condition. D is inappropriate."},

{"module_code": "NURSE-008", "question_type": "mcq", "difficulty": "hard",
 "nclex_client_needs": "psychosocial", "cjmm_skill": "take_actions",
 "question": "The family of a critically ill patient demands to know the patient's prognosis and insists the nurse 'tell them everything.' The patient is alert, competent, and has not signed a HIPAA release. What is the nurse's BEST response?",
 "options": {"A": "Share all clinical information to support the family's coping", "B": "Refuse all information and instruct family to ask the physician only", "C": "Acknowledge the family's concern and offer to arrange a care conference with the patient present", "D": "Tell the family only the diagnosis but not the prognosis"},
 "correct": "C", "explanation": "A competent patient controls their own health information. Sharing without consent violates HIPAA and patient autonomy — even with family. C respects autonomy while supporting the family: the patient can decide what to share in a conference. B is too rigid and unhelpful. A violates HIPAA. D still shares information without consent. The patient should be the one to authorize what the family learns."},

# ══════════════════════════════════════════════════════════════════════════════
# BOW-TIE NGN QUESTIONS (cross-module)
# ══════════════════════════════════════════════════════════════════════════════
{"module_code": "NURSE-005", "question_type": "mcq", "ngn_type": "bowtie",
 "difficulty": "hard", "nclex_client_needs": "physiological_adaptation", "cjmm_skill": "prioritize_hypotheses",
 "question": "A nurse is caring for a 58-year-old patient in the ED. Vitals: BP 82/54, HR 128, RR 26, Temp 39.2°C, SpO2 93% on room air. The patient is confused and reports right flank pain for 3 days. WBC 22,000, lactate 3.8 mmol/L. Complete the bow-tie clinical judgment item.",
 "options": {"A": "See bow-tie diagram"},
 "correct": "A",
 "explanation": "Septic shock from urosepsis: fever, hypotension, tachycardia, elevated WBC and lactate, confusion, flank pain (UTI/pyelonephritis source). Actions: Blood cultures before antibiotics + IV fluid bolus. Monitor: MAP (goal ≥65) + urine output (goal ≥0.5 mL/kg/h).",
 "bowtie_data": {
   "condition_options": ["Septic shock", "Cardiogenic shock", "Hemorrhagic shock", "Hypovolemic shock", "Neurogenic shock"],
   "action_options": ["Obtain blood cultures x2 before antibiotics", "Administer broad-spectrum antibiotics", "Give 30 mL/kg IV fluid bolus", "Administer norepinephrine", "Insert urinary catheter to monitor output", "Apply supplemental oxygen via NRB mask"],
   "parameter_options": ["Mean arterial pressure (MAP)", "Urine output (mL/h)", "Serum lactate trend", "Temperature trend", "Blood cultures result", "Capillary refill time"],
   "correct_condition": "Septic shock",
   "correct_actions": ["Obtain blood cultures x2 before antibiotics", "Give 30 mL/kg IV fluid bolus"],
   "correct_parameters": ["Mean arterial pressure (MAP)", "Urine output (mL/h)"]
 },
 "tags": ["sepsis", "septic_shock", "ngn", "bowtie", "urosepsis"]},

{"module_code": "NURSE-006", "question_type": "mcq", "ngn_type": "bowtie",
 "difficulty": "hard", "nclex_client_needs": "physiological_adaptation", "cjmm_skill": "prioritize_hypotheses",
 "question": "A nurse is triaging a patient who presents with sudden-onset throat tightness, generalized urticaria, and lip swelling 10 minutes after eating peanuts. BP 88/52, HR 130, SpO2 95%. Complete the bow-tie clinical judgment item.",
 "options": {"A": "See bow-tie diagram"},
 "correct": "A",
 "explanation": "Anaphylaxis: IgE-mediated hypersensitivity with systemic vasodilation and bronchospasm. First-line: epinephrine IM + call rapid response. Monitor: BP (vasodilation reversal) + SpO2/respiratory status (bronchospasm resolution).",
 "bowtie_data": {
   "condition_options": ["Anaphylaxis", "Angioedema only", "Urticaria without systemic involvement", "Vasovagal syncope", "Acute asthma exacerbation"],
   "action_options": ["Administer epinephrine 0.3 mg IM anterolateral thigh", "Call for rapid response team", "Administer diphenhydramine 50 mg IV", "Apply oxygen via non-rebreather mask", "Place in supine position with legs elevated", "Administer hydrocortisone 200 mg IV"],
   "parameter_options": ["Blood pressure q5 min", "SpO2 and respiratory rate", "Urticaria resolution", "Heart rate trend", "Level of consciousness", "Skin color and capillary refill"],
   "correct_condition": "Anaphylaxis",
   "correct_actions": ["Administer epinephrine 0.3 mg IM anterolateral thigh", "Call for rapid response team"],
   "correct_parameters": ["Blood pressure q5 min", "SpO2 and respiratory rate"]
 },
 "tags": ["anaphylaxis", "ngn", "bowtie", "emergency", "allergy"]},

]
# fmt: on


async def seed():
    async with AsyncSessionLocal() as session:
        # Cache module lookups
        modules: dict[str, object] = {}
        result = await session.execute(select(Module).where(Module.is_nursing == True))
        for mod in result.scalars().all():
            modules[mod.code] = mod

        # Get existing questions to skip duplicates
        existing = await session.execute(
            select(MCQQuestion.question).join(Module).where(Module.is_nursing == True)
        )
        existing_texts = {r[0] for r in existing.fetchall()}

        imported = 0
        skipped = 0

        for q in SEED_QUESTIONS:
            module_code = q.get("module_code")
            module = modules.get(module_code)
            if not module:
                print(f"  ✗ Module {module_code} not found in DB")
                skipped += 1
                continue

            qtext = q["question"]
            if qtext in existing_texts:
                skipped += 1
                continue

            mcq = MCQQuestion(
                id=uuid.uuid4(),
                module_id=module.id,
                question=qtext,
                options=q.get("options", {}),
                correct=q.get("correct", "A"),
                explanation=q.get("explanation", ""),
                difficulty=q.get("difficulty", "medium"),
                tags=q.get("tags", []),
                question_type=q.get("question_type", "mcq"),
                correct_answers=q.get("correct_answers"),
                correct_order=q.get("correct_order"),
                numeric_answer=float(q["numeric_answer"]) if q.get("numeric_answer") is not None else None,
                numeric_tolerance=float(q.get("numeric_tolerance") or 0.5),
                numeric_unit=q.get("numeric_unit"),
                partial_scoring=False,
                nclex_client_needs=q.get("nclex_client_needs"),
                cjmm_skill=q.get("cjmm_skill"),
                ngn_type=q.get("ngn_type"),
                bowtie_data=q.get("bowtie_data"),
            )
            session.add(mcq)
            existing_texts.add(qtext)
            imported += 1

        await session.commit()
        print(f"\n  Seed complete: {imported} imported, {skipped} skipped")


if __name__ == "__main__":
    asyncio.run(seed())
