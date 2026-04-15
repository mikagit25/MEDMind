"""Seed content modules for PSYCH, ANES, ONC, DERM specialties.

Idempotent — safe to run multiple times (skips existing module codes).
Auto-runs at startup (non-fatal). Can also run manually:
    cd backend && python -m scripts.seed_new_specialties
"""
import asyncio
import uuid
from datetime import datetime

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.models import Specialty, Module, Lesson, Flashcard, MCQQuestion


MODULES = [

    # ── PSYCHIATRY ─────────────────────────────────────────────────────────
    {
        "specialty_code": "psychiatry",
        "code": "PSYCH-001",
        "title": "Mood Disorders",
        "description": "Major depressive disorder, bipolar disorder, cyclothymia — diagnosis and management.",
        "difficulty": "intermediate",
        "estimated_hours": 3,
        "lessons": [
            {
                "title": "Major Depressive Disorder",
                "lesson_order": 0,
                "estimated_minutes": 25,
                "content": {"blocks": [
                    {"type": "text", "content": "## Major Depressive Disorder (MDD)\n\nMDD affects 264 million people worldwide. Defined by ≥5 DSM-5 criteria for ≥2 weeks, including depressed mood or anhedonia.\n\n**SIG E CAPS mnemonic:**\n- **S**leep disturbance\n- **I**nterest loss (anhedonia)\n- **G**uilt / worthlessness\n- **E**nergy loss\n- **C**oncentration difficulty\n- **A**ppetite change\n- **P**sychomotor changes\n- **S**uicidal ideation\n\n**Pathophysiology:** Monoamine deficiency (serotonin, norepinephrine, dopamine). HPA axis dysregulation and neuroinflammation also implicated.\n\n**First-line treatment:** SSRIs (fluoxetine, sertraline, escitalopram). Allow 4–6 weeks for full effect. CBT equally effective in mild-moderate cases."},
                    {"type": "quiz", "question": "A 34-year-old presents with 3 weeks of depressed mood, insomnia, poor appetite, poor concentration, and fatigue. PHQ-9 score 18. What is the most appropriate initial management?", "options": {"A": "Lithium monotherapy", "B": "Sertraline + CBT referral", "C": "Haloperidol", "D": "Watchful waiting only"}, "correct": "B", "explanation": "Moderate-severe MDD (PHQ-9 ≥15) warrants combined SSRI + psychotherapy. Lithium is for bipolar disorder, not MDD first-line."},
                ]},
            },
            {
                "title": "Bipolar Disorder",
                "lesson_order": 1,
                "estimated_minutes": 30,
                "content": {"blocks": [
                    {"type": "text", "content": "## Bipolar Disorder\n\n**Types:**\n- **Bipolar I:** ≥1 manic episode (≥7 days or hospitalisation required)\n- **Bipolar II:** Hypomanic episodes (≥4 days) + depressive episodes; no full mania\n- **Cyclothymia:** Subsyndromal mood swings >2 years\n\n**Mania features (DIG FAST):** Distractibility, Impulsivity, Grandiosity, Flight of ideas, Activity↑, Sleep↓, Talkativeness.\n\n**Management:**\n- Acute mania: lithium, valproate, or atypical antipsychotic\n- Maintenance: lithium (also reduces suicide risk)\n- Depression phase: quetiapine, lurasidone, lamotrigine\n- Avoid antidepressant monotherapy → risk of inducing mania\n\n**Lithium monitoring:** Level 0.6–1.2 mEq/L, TSH, creatinine every 6 months."},
                    {"type": "quiz", "question": "A 28-year-old with bipolar I stable on lithium plans a pregnancy. What is the most important counselling point?", "options": {"A": "Lithium is completely safe in pregnancy", "B": "Lithium is associated with Ebstein's anomaly; risk-benefit discussion required", "C": "Stop lithium immediately — it causes neural tube defects", "D": "Switch to carbamazepine which is safer"}, "correct": "B", "explanation": "Lithium carries a small risk of Ebstein's anomaly (tricuspid valve). Risk-benefit must be discussed. Carbamazepine causes neural tube defects — not safer."},
                ]},
            },
        ],
        "flashcards": [
            {"question": "DSM-5 criteria for MDD (mnemonic)?", "answer": "SIG E CAPS: Sleep, Interest, Guilt, Energy, Concentration, Appetite, Psychomotor, Suicidality. ≥5 symptoms for ≥2 weeks, including depressed mood or anhedonia.", "difficulty": "medium"},
            {"question": "Therapeutic lithium serum level range?", "answer": "0.6–1.2 mEq/L (acute mania 1.0–1.2; maintenance 0.6–0.8 mEq/L)", "difficulty": "medium"},
            {"question": "DIG FAST mnemonic for mania?", "answer": "Distractibility, Impulsivity/Indiscretion, Grandiosity, Flight of ideas, Activity↑, Sleep↓, Talkativeness (pressured speech)", "difficulty": "easy"},
            {"question": "First-line agent for bipolar depression?", "answer": "Quetiapine or lurasidone; lamotrigine as adjunct. Avoid antidepressant monotherapy (risk of inducing mania).", "difficulty": "hard"},
        ],
        "mcqs": [
            {"question": "A 45-year-old is started on lithium. Which baseline investigation is MOST important?", "options": {"A": "Liver function tests", "B": "Renal function and thyroid function", "C": "Full blood count", "D": "Chest X-ray"}, "correct": "B", "explanation": "Lithium is renally cleared and causes nephrogenic diabetes insipidus and hypothyroidism. Baseline renal + thyroid (+ ECG in elderly) are essential.", "difficulty": "medium"},
        ],
    },

    {
        "specialty_code": "psychiatry",
        "code": "PSYCH-002",
        "title": "Anxiety & Psychotic Disorders",
        "description": "GAD, panic disorder, OCD, PTSD, schizophrenia spectrum.",
        "difficulty": "intermediate",
        "estimated_hours": 3,
        "lessons": [
            {
                "title": "Anxiety Disorders Overview",
                "lesson_order": 0,
                "estimated_minutes": 25,
                "content": {"blocks": [
                    {"type": "text", "content": "## Anxiety Disorders\n\n**GAD:** Excessive worry ≥6 months + ≥3 somatic symptoms (restlessness, fatigue, poor concentration, irritability, muscle tension, sleep disturbance). Treatment: SSRIs/SNRIs, buspirone, CBT.\n\n**Panic Disorder:** Recurrent unexpected panic attacks + persistent concern about future attacks. Treatment: SSRIs + CBT; avoid long-term benzodiazepines.\n\n**OCD:** Obsessions + compulsions. Treatment: high-dose SSRI + ERP (exposure and response prevention). Clomipramine if refractory.\n\n**PTSD:** Trauma exposure + 4 clusters: intrusion, avoidance, negative cognitions, hyperarousal (duration >1 month). Treatment: trauma-focused CBT, EMDR, sertraline/paroxetine."},
                    {"type": "quiz", "question": "A 32-year-old has recurrent unexpected episodes of palpitations, chest tightness, dizziness, and fear of dying lasting 10 minutes, and now avoids crowded places. What is the diagnosis?", "options": {"A": "GAD", "B": "Panic disorder with agoraphobia", "C": "Specific phobia", "D": "Social anxiety disorder"}, "correct": "B", "explanation": "Recurrent unexpected panic attacks + avoidance behaviour due to fear of attacks = panic disorder with agoraphobia."},
                ]},
            },
            {
                "title": "Schizophrenia",
                "lesson_order": 1,
                "estimated_minutes": 30,
                "content": {"blocks": [
                    {"type": "text", "content": "## Schizophrenia\n\n**DSM-5:** ≥2 of: hallucinations, delusions, disorganised speech, disorganised behaviour, negative symptoms — ≥1 month, total duration ≥6 months + functional impairment.\n\n**Positive symptoms:** auditory hallucinations, delusions, thought disorder\n**Negative symptoms (4As):** Alogia, Avolition, Anhedonia, Affect blunting\n\n**Pathophysiology:** Mesolimbic D2 hyperactivity → positive symptoms. Mesocortical D1 hypoactivity → negative symptoms.\n\n**Treatment:**\n- First episode: atypical antipsychotic (risperidone, olanzapine, quetiapine, aripiprazole)\n- Treatment-resistant: clozapine (monitor ANC — agranulocytosis risk ~1%)\n- Duration: minimum 1–2 years; often lifelong for recurrent episodes\n\n**Monitoring:** Metabolic syndrome, EPS, prolactin, QTc."},
                    {"type": "quiz", "question": "A patient on clozapine develops sore throat and fever. Immediate management?", "options": {"A": "Continue clozapine and give paracetamol", "B": "Stop clozapine immediately and obtain urgent FBC", "C": "Switch to haloperidol", "D": "Add broad-spectrum antibiotic and continue"}, "correct": "B", "explanation": "Sore throat + fever on clozapine = possible agranulocytosis. Stop immediately and check ANC. ANC <1000 cells/μL → permanent contraindication to clozapine."},
                ]},
            },
        ],
        "flashcards": [
            {"question": "4 clusters of PTSD symptoms?", "answer": "1) Intrusion (flashbacks, nightmares) 2) Avoidance 3) Negative alterations in cognitions/mood 4) Hyperarousal (startle, insomnia, hypervigilance)", "difficulty": "medium"},
            {"question": "Why is clozapine reserved for treatment-resistant schizophrenia?", "answer": "Risk of agranulocytosis (~1%) requiring mandatory blood monitoring. Also: metabolic syndrome, myocarditis, seizures.", "difficulty": "medium"},
            {"question": "Dopamine hypothesis of schizophrenia?", "answer": "Mesolimbic D2 hyperactivity → positive symptoms. Mesocortical D1 hypoactivity → negative symptoms. All effective antipsychotics block D2 receptors.", "difficulty": "hard"},
        ],
        "mcqs": [],
    },

    # ── ANESTHESIOLOGY ─────────────────────────────────────────────────────
    {
        "specialty_code": "anesthesiology",
        "code": "ANES-001",
        "title": "Perioperative Assessment & Airway Management",
        "description": "Pre-operative evaluation, ASA classification, airway assessment, rapid sequence induction.",
        "difficulty": "advanced",
        "estimated_hours": 4,
        "lessons": [
            {
                "title": "Pre-operative Assessment",
                "lesson_order": 0,
                "estimated_minutes": 30,
                "content": {"blocks": [
                    {"type": "text", "content": "## Pre-operative Assessment\n\n**ASA Physical Status Classification:**\n- ASA I: Healthy, no systemic disease\n- ASA II: Mild systemic disease (well-controlled HTN/DM, BMI <40)\n- ASA III: Severe systemic disease (poorly controlled DM, COPD, morbid obesity, EF <35%)\n- ASA IV: Severe disease — constant threat to life (unstable angina, decompensated CHF, recent MI/CVA <3 months)\n- ASA V: Moribund, unlikely to survive without operation\n- ASA VI: Brain-dead organ donor\n- Add 'E' suffix for emergency procedures\n\n**Fasting (NPO) guidelines:**\n- Clear liquids: 2 hours\n- Breast milk: 4 hours\n- Non-human milk / light meal: 6 hours\n- Heavy/fried meal: 8 hours\n\n**Key investigations:**\n- ECG: age ≥50 or cardiac disease\n- U&E: renal disease, diuretics, ACEi/ARBs\n- Coagulation: anticoagulants, liver disease\n- Group & save: anticipated blood loss >500 mL"},
                    {"type": "quiz", "question": "A 68-year-old with poorly controlled type 2 diabetes and GOLD stage 2 COPD requires elective hip replacement. What is his ASA classification?", "options": {"A": "ASA II", "B": "ASA III", "C": "ASA IV", "D": "ASA V"}, "correct": "B", "explanation": "Poorly controlled DM + moderate COPD = severe systemic disease that is not an immediate threat to life = ASA III. ASA IV requires conditions like unstable angina or decompensated heart failure."},
                ]},
            },
            {
                "title": "Airway Management & RSI",
                "lesson_order": 1,
                "estimated_minutes": 35,
                "content": {"blocks": [
                    {"type": "text", "content": "## Airway Assessment\n\n**Difficult airway predictors — LEMON:**\n- **L**ook externally (short neck, small mouth, micrognathia)\n- **E**valuate 3-3-2 rule: mouth opening ≥3 fingers, hyoid-to-chin ≥3 fingers, thyroid-to-floor-of-mouth ≥2 fingers\n- **M**allampati score (III/IV = likely difficult)\n- **O**bstruction\n- **N**eck mobility\n\n## Rapid Sequence Induction (RSI)\n\nUsed for aspiration risk (full stomach, GORD, pregnancy, bowel obstruction).\n\n**Steps:**\n1. Pre-oxygenation (100% O₂ × 3–5 min)\n2. Induction: propofol 2 mg/kg OR ketamine 1–2 mg/kg (haemodynamic instability)\n3. Neuromuscular blockade: suxamethonium 1.5 mg/kg OR rocuronium 1.2 mg/kg\n4. Cricoid pressure (Sellick manoeuvre)\n5. Intubate when conditions optimal\n\n**Suxamethonium contraindications:** Hyperkalaemia, rhabdomyolysis, burns/crush/denervation >24h, MH history, pseudocholinesterase deficiency.\n\n**CICO (Can't Intubate Can't Oxygenate):** Immediate needle or surgical cricothyrotomy.\n\n**Rocuronium reversal:** Sugammadex 2 mg/kg routine; 16 mg/kg immediate reversal."},
                    {"type": "quiz", "question": "A patient requires emergency laparotomy for bowel obstruction. Which induction technique is most appropriate?", "options": {"A": "Inhalational induction with sevoflurane", "B": "Rapid sequence induction with suxamethonium", "C": "Awake fibreoptic intubation", "D": "Standard IV induction with propofol alone"}, "correct": "B", "explanation": "Bowel obstruction = full stomach = high aspiration risk → RSI is indicated. Awake fibreoptic is for anticipated difficult airway. Inhalational induction is slow with no aspiration protection."},
                ]},
            },
        ],
        "flashcards": [
            {"question": "Suxamethonium contraindications?", "answer": "Hyperkalaemia, rhabdomyolysis, burns/crush/denervation >24h, malignant hyperthermia history, pseudocholinesterase deficiency, upper motor neurone lesions", "difficulty": "hard"},
            {"question": "NPO guidelines for elective surgery?", "answer": "Clear liquids: 2h | Breast milk: 4h | Non-human milk/light meal: 6h | Heavy/fried meal: 8h", "difficulty": "easy"},
            {"question": "Mallampati classification — what does it predict?", "answer": "Difficulty of laryngoscopy. Class I (full palate/uvula/fauces visible) = easy; Class IV (only hard palate visible) = likely difficult intubation.", "difficulty": "medium"},
            {"question": "What drug reverses rocuronium?", "answer": "Sugammadex: 2 mg/kg routine reversal; 16 mg/kg for immediate full reversal in CICO emergency.", "difficulty": "medium"},
        ],
        "mcqs": [
            {"question": "Which is a contraindication to suxamethonium?", "options": {"A": "Acute appendicitis", "B": "Severe burns 48 hours post-injury", "C": "Pregnancy at term", "D": "Hyponatraemia"}, "correct": "B", "explanation": "Burns >24h cause upregulation of extrajunctional ACh receptors → massive K+ efflux with suxamethonium → cardiac arrest. Pregnancy is not a contraindication.", "difficulty": "hard"},
        ],
    },

    {
        "specialty_code": "anesthesiology",
        "code": "ANES-002",
        "title": "General Anaesthesia & Regional Techniques",
        "description": "Induction agents, volatile agents, epidural/spinal anaesthesia, local anaesthetic toxicity.",
        "difficulty": "advanced",
        "estimated_hours": 3,
        "lessons": [
            {
                "title": "Induction & Volatile Agents",
                "lesson_order": 0,
                "estimated_minutes": 30,
                "content": {"blocks": [
                    {"type": "text", "content": "## IV Induction Agents\n\n| Agent | Dose | Onset | Key features |\n|---|---|---|---|\n| Propofol | 1–2.5 mg/kg | 30 s | Pain on injection, ↓BP, antiemetic |\n| Thiopental | 3–5 mg/kg | 30 s | Porphyria contraindicated, safe in status epilepticus |\n| Ketamine | 1–2 mg/kg | 60 s | Dissociative, bronchodilator, maintains BP — ideal in haemodynamic instability; emergence reactions |\n| Etomidate | 0.3 mg/kg | 30 s | Cardiovascularly stable; adrenal suppression (single dose safe, infusion avoid) |\n| Midazolam | 0.05–0.1 mg/kg | 2–3 min | Amnesia, anxiolysis; not induction-level agent alone |\n\n## Volatile Agents\n\n- **Sevoflurane:** Most used for inhalational induction (pleasant, low pungency). MAC 2.0%. Renal fluoride — use with high fresh gas flow in long cases.\n- **Desflurane:** Fast on/off (MAC 6%). Pungent — cannot use for inhalational induction. Highest GHG footprint.\n- **Isoflurane:** MAC 1.15%. Cheap, widespread. Moderate pungency.\n\n**MAC (Minimum Alveolar Concentration):** Concentration of volatile agent at which 50% of patients do not move to surgical incision. ↓ by: age, hypothermia, opioids, α2-agonists, pregnancy. ↑ by: hyperthermia, chronic alcohol, paediatric age."},
                    {"type": "quiz", "question": "A trauma patient with haemorrhagic shock (BP 70/40) needs emergency surgery. Which induction agent is most appropriate?", "options": {"A": "Propofol 2 mg/kg", "B": "Ketamine 1.5 mg/kg", "C": "Thiopental 4 mg/kg", "D": "Midazolam 0.1 mg/kg"}, "correct": "B", "explanation": "Ketamine is the agent of choice in haemodynamic instability — it stimulates catecholamine release, maintaining BP and heart rate. Propofol and thiopental cause significant hypotension."},
                ]},
            },
            {
                "title": "Regional Anaesthesia & LA Toxicity",
                "lesson_order": 1,
                "estimated_minutes": 30,
                "content": {"blocks": [
                    {"type": "text", "content": "## Spinal vs. Epidural Anaesthesia\n\n| | Spinal | Epidural |\n|---|---|---|\n| Space | Subarachnoid (CSF) | Epidural space |\n| Onset | 5–10 min | 15–30 min |\n| Block height | Less controllable | Titratable |\n| Dose of LA | Small (1–3 mL) | Large (10–20 mL) |\n| Catheter | No | Yes (for infusions) |\n| Uses | C-section, lower limb, TURP | Labour, thoracic/abdominal surgery |\n\n**Spinal headache (PDPH):** Dural puncture → CSF leak → traction on meninges. Postural (worse upright, better supine). Treatment: bed rest, caffeine, epidural blood patch.\n\n## Local Anaesthetic Systemic Toxicity (LAST)\n\n**Mechanism:** Na+ channel blockade in CNS and heart → seizures then cardiac arrest.\n\n**Signs (CNS first, then cardiac):**\n- Early: perioral tingling, tinnitus, metallic taste, agitation\n- Late: seizures, loss of consciousness, VT/VF, cardiac arrest\n\n**Treatment:** Stop LA immediately, 100% O₂, call for help.\n- Seizures: benzodiazepine or thiopental\n- Cardiac arrest: CPR + **Intralipid 20%** (lipid sink theory): 1.5 mL/kg bolus → infusion 0.25 mL/kg/min\n- Avoid propofol as substitute (too low lipid concentration)\n\n**Highest risk agents:** Bupivacaine (most cardiotoxic); levobupivacaine/ropivacaine safer."},
                    {"type": "quiz", "question": "A patient receiving a brachial plexus block suddenly has perioral tingling, then seizures. What is the immediate treatment after stopping LA and giving O₂?", "options": {"A": "IV adrenaline 1 mg", "B": "IV Intralipid 20% 1.5 mL/kg bolus", "C": "IV amiodarone 300 mg", "D": "IM glucagon"}, "correct": "B", "explanation": "LAST treatment: after stopping LA and oxygenation, Intralipid 20% is the specific antidote (lipid sink). Adrenaline is used but at reduced dose (≤1 μg/kg). Standard ACLS drugs are used cautiously."},
                ]},
            },
        ],
        "flashcards": [
            {"question": "Which induction agent is safest in haemodynamic instability?", "answer": "Ketamine — stimulates catecholamine release, maintains BP and HR. Also a bronchodilator. Beware emergence reactions (hallucinations).", "difficulty": "easy"},
            {"question": "What is MAC?", "answer": "Minimum Alveolar Concentration — the alveolar concentration of volatile agent at which 50% of patients do not move to surgical incision. Used to compare potency.", "difficulty": "medium"},
            {"question": "Treatment of Local Anaesthetic Systemic Toxicity (LAST)?", "answer": "Stop LA, 100% O₂, benzodiazepine for seizures, CPR if cardiac arrest, Intralipid 20% 1.5 mL/kg bolus then infusion 0.25 mL/kg/min.", "difficulty": "hard"},
            {"question": "Most cardiotoxic local anaesthetic?", "answer": "Bupivacaine. Preferably replaced by levobupivacaine or ropivacaine for high-dose blocks.", "difficulty": "medium"},
        ],
        "mcqs": [],
    },

    # ── ONCOLOGY ───────────────────────────────────────────────────────────
    {
        "specialty_code": "oncology",
        "code": "ONC-001",
        "title": "Oncological Emergencies",
        "description": "Tumour lysis syndrome, SVC obstruction, malignant spinal cord compression, hypercalcaemia.",
        "difficulty": "advanced",
        "estimated_hours": 3,
        "lessons": [
            {
                "title": "Tumour Lysis Syndrome",
                "lesson_order": 0,
                "estimated_minutes": 25,
                "content": {"blocks": [
                    {"type": "text", "content": "## Tumour Lysis Syndrome (TLS)\n\n**Definition:** Massive release of intracellular contents following rapid tumour cell death.\n\n**Cairo-Bishop — Laboratory TLS (≥2 of):**\n- Uric acid ≥476 μmol/L (8 mg/dL) or ↑25%\n- K+ ≥6.0 mmol/L or ↑25%\n- Phosphate ≥1.45 mmol/L or ↑25%\n- Ca²+ ≤1.75 mmol/L or ↓25%\n\n**Clinical TLS:** Lab TLS + creatinine ≥1.5× ULN, arrhythmia, or seizure.\n\n**High-risk tumours:** Burkitt lymphoma, ALL (WBC >100K), AML, bulky DLBCL.\n\n**Prevention:** Aggressive IV hydration (3 L/m²/day), allopurinol (reduces uric acid production), rasburicase (rapidly lowers uric acid — contraindicated in G6PD deficiency).\n\n**Treatment:** IV fluids, treat hyperkalaemia (insulin-dextrose, calcium gluconate), haemodialysis if refractory."},
                    {"type": "quiz", "question": "A 22-year-old with Burkitt lymphoma starts chemotherapy. 12 hours later: K+ 6.8, PO₄ 2.1, uric acid 620 μmol/L, Ca²+ 1.6, creatinine 200 (baseline 80). Immediate management?", "options": {"A": "Continue chemotherapy and monitor", "B": "IV fluids, treat hyperkalaemia, rasburicase, nephrology review", "C": "Give allopurinol only", "D": "IV calcium first then reassess"}, "correct": "B", "explanation": "Clinical TLS (lab TLS + rising creatinine). Priorities: cardiac protection (treat K+ 6.8 urgently with insulin-dextrose + calcium gluconate), aggressive hydration, rasburicase for uric acid, early nephrology for dialysis consideration."},
                ]},
            },
            {
                "title": "Malignant Spinal Cord Compression",
                "lesson_order": 1,
                "estimated_minutes": 20,
                "content": {"blocks": [
                    {"type": "text", "content": "## Malignant Spinal Cord Compression (MSCC)\n\n**Epidemiology:** Complicates ~5% of cancers. Most common causes: lung, breast, prostate, myeloma, renal cell carcinoma.\n\n**Key point:** Back pain in a cancer patient = MSCC until proven otherwise.\n\n**Presentation:** Back pain (95%) → progressive leg weakness → sensory level → bladder/bowel dysfunction.\n\n**Diagnosis:** MRI whole spine (gold standard).\n\n**Management — time-critical (within 24h):**\n1. High-dose dexamethasone immediately (16 mg loading → 4–8 mg QDS)\n2. Urgent oncology/neurosurgery referral\n3. Surgical decompression if: single site, good prognosis, fit for surgery, deteriorating on RT, bone instability\n4. Radiotherapy: primary treatment for inoperable cases\n\n**Prognosis:** Ambulant at diagnosis → 80% remain ambulant after treatment. Paraplegia >48h → rarely recover."},
                    {"type": "quiz", "question": "A 65-year-old with known prostate cancer presents with 3-week worsening back pain and new bilateral leg weakness. Still ambulant. Immediate next step?", "options": {"A": "Plain X-ray spine", "B": "IV dexamethasone + urgent MRI whole spine", "C": "Bone scan and await results", "D": "Urgent radiotherapy"}, "correct": "B", "explanation": "Presumed MSCC — treat immediately. Dexamethasone reduces cord oedema while MRI is arranged. Do not delay steroids for imaging. Preserving ambulation is the goal."},
                ]},
            },
            {
                "title": "Hypercalcaemia of Malignancy",
                "lesson_order": 2,
                "estimated_minutes": 20,
                "content": {"blocks": [
                    {"type": "text", "content": "## Hypercalcaemia of Malignancy\n\n**Most common cause of hypercalcaemia in hospitalised patients.**\n\n**Mechanisms:**\n- PTHrP secretion (humoral hypercalcaemia of malignancy — 80%): squamous cell carcinoma, renal, bladder\n- Osteolytic metastases (20%): breast, myeloma\n- 1,25(OH)₂D production: lymphomas\n\n**Symptoms (bones, stones, groans, psychic moans):**\n- Bones: bone pain\n- Stones: renal calculi, polyuria, polydipsia\n- Groans: nausea, vomiting, constipation\n- Psychic moans: confusion, depression, lethargy → coma\n\n**Treatment (corrected Ca²+ >3.0 mmol/L):**\n1. IV 0.9% NaCl rehydration (2–4 L over 24h) — first-line\n2. IV bisphosphonate (zoledronic acid 4 mg over 15 min) — onset 48–72h, lasts 3–4 weeks\n3. Denosumab (RANK-L inhibitor) for bisphosphonate-refractory cases\n4. Calcitonin for rapid effect (tachyphylaxis limits use to 48h)\n5. Treat underlying malignancy"},
                    {"type": "quiz", "question": "A patient with squamous cell lung carcinoma presents with confusion, nausea, and polyuria. Corrected calcium 3.4 mmol/L. PTHrP elevated, PTH suppressed. Management?", "options": {"A": "Oral calcimimetic", "B": "IV 0.9% NaCl + IV zoledronic acid", "C": "Oral bisphosphonate alone", "D": "Furosemide alone"}, "correct": "B", "explanation": "Humoral hypercalcaemia of malignancy. Initial: aggressive IV hydration (rehydration takes priority). Then: IV zoledronic acid — the most potent bisphosphonate. Furosemide alone is no longer recommended (causes dehydration). Oral bisphosphonates are too slow."},
                ]},
            },
        ],
        "flashcards": [
            {"question": "Cairo-Bishop criteria for laboratory TLS (≥2 of)?", "answer": "Uric acid ≥476 μmol/L | K+ ≥6.0 | Phosphate ≥1.45 | Calcium ≤1.75 (or 25% change from baseline)", "difficulty": "hard"},
            {"question": "Why is rasburicase contraindicated in G6PD deficiency?", "answer": "Rasburicase generates H₂O₂ as by-product → G6PD-deficient RBCs cannot detoxify it → haemolytic anaemia.", "difficulty": "hard"},
            {"question": "Most common cancers causing MSCC?", "answer": "Lung, Breast, Prostate (+ myeloma, renal cell carcinoma).", "difficulty": "medium"},
            {"question": "Mechanism of hypercalcaemia in squamous cell carcinoma?", "answer": "PTHrP (parathyroid hormone-related peptide) secretion — activates PTH receptors → bone resorption + renal calcium reabsorption.", "difficulty": "medium"},
            {"question": "First-line treatment for severe hypercalcaemia of malignancy?", "answer": "IV 0.9% NaCl (aggressive rehydration) + IV zoledronic acid (bisphosphonate). Onset 48–72h.", "difficulty": "medium"},
        ],
        "mcqs": [
            {"question": "Which tumour type has the HIGHEST risk of tumour lysis syndrome?", "options": {"A": "Colon adenocarcinoma", "B": "Burkitt lymphoma", "C": "Thyroid papillary carcinoma", "D": "Bladder transitional cell carcinoma"}, "correct": "B", "explanation": "Burkitt lymphoma has the highest proliferation rate (doubling time ~24h) and is most TLS-prone. ALL with very high WBC is also high risk. Solid tumours carry low TLS risk.", "difficulty": "medium"},
        ],
    },

    # ── DERMATOLOGY ────────────────────────────────────────────────────────
    {
        "specialty_code": "dermatology",
        "code": "DERM-001",
        "title": "Common Inflammatory Skin Conditions",
        "description": "Eczema, psoriasis, acne vulgaris, and urticaria — diagnosis and management.",
        "difficulty": "intermediate",
        "estimated_hours": 3,
        "lessons": [
            {
                "title": "Eczema & Psoriasis",
                "lesson_order": 0,
                "estimated_minutes": 30,
                "content": {"blocks": [
                    {"type": "text", "content": "## Atopic Eczema (Atopic Dermatitis)\n\n**Epidemiology:** ~20% of children, 3% adults. Associated with asthma + allergic rhinitis (atopic triad).\n\n**Diagnosis:** Itchy skin + ≥3 of: flexural involvement, history of dry skin, onset before age 2, personal/family history of atopy.\n\n**Treatment ladder:**\n1. Emollients (cornerstone — apply liberally and frequently)\n2. Mild TCS: hydrocortisone 1% (face/flexures)\n3. Moderate-potent TCS: betamethasone valerate (body)\n4. Topical calcineurin inhibitors (tacrolimus, pimecrolimus) — steroid-sparing, safe for face/eyelids\n5. Dupilumab (IL-4/IL-13 inhibitor) — moderate-severe refractory cases\n\n---\n## Psoriasis\n\n**Pathophysiology:** T-cell mediated inflammation → keratinocyte hyperproliferation. HLA-Cw6 + environmental triggers.\n\n**Morphology:** Well-demarcated erythematous plaques, silvery scale. Auspitz sign. Koebner phenomenon.\n\n**Distribution:** Extensor surfaces (elbows, knees), scalp, nails (pitting, onycholysis, oil-drop sign), sacrum.\n\n**Management:**\n- Mild: TCS + calcipotriol (vitamin D analogue)\n- Moderate-severe: NB-UVB phototherapy, methotrexate, ciclosporin\n- Biologics: TNF-α inhibitors (adalimumab, etanercept), IL-17 inhibitors (secukinumab), IL-23 inhibitors (guselkumab)"},
                    {"type": "quiz", "question": "A 35-year-old has well-demarcated erythematous plaques with silvery scale on both elbows and knees, nail pitting, and lesions at sites of skin trauma. Diagnosis?", "options": {"A": "Atopic eczema", "B": "Tinea corporis", "C": "Psoriasis vulgaris", "D": "Pityriasis rosea"}, "correct": "C", "explanation": "Classic psoriasis: extensor plaques, silvery scale, nail pitting, Koebner phenomenon. Eczema is flexural without silvery scale. Tinea is annular with central clearing."},
                ]},
            },
            {
                "title": "Acne Vulgaris & Urticaria",
                "lesson_order": 1,
                "estimated_minutes": 25,
                "content": {"blocks": [
                    {"type": "text", "content": "## Acne Vulgaris\n\n**Pathophysiology (4 factors):** Sebum overproduction, follicular hyperkeratinisation, C. acnes colonisation, inflammation.\n\n**Treatment by severity:**\n- Mild (comedones, few papules): topical retinoid (adapalene) ± benzoyl peroxide\n- Moderate (papulopustular): topical retinoid + topical antibiotic (clindamycin) OR oral doxycycline 100 mg OD × 3 months\n- Severe/nodular: oral isotretinoin (0.5–1 mg/kg/day × 4–6 months)\n\n**Isotretinoin monitoring:** LFTs, lipids, β-hCG monthly (teratogenic — mandatory contraception, pregnancy prevention programme).\n\n---\n## Urticaria\n\n**Acute** (<6 weeks): Usually IgE-mediated (foods, drugs, insect stings). Individual weals <24h.\n**Chronic spontaneous** (≥6 weeks): Often no identifiable cause; autoimmune in ~45%.\n\n**Management:**\n- Avoid triggers (if identified)\n- 2nd-generation antihistamines (cetirizine, loratadine) — first-line; up-titrate to 4× dose\n- Omalizumab (anti-IgE) for refractory chronic urticaria\n- Short prednisolone course for acute severe episodes"},
                    {"type": "quiz", "question": "A 17-year-old with severe nodulocystic acne has failed two courses of oral antibiotics. Most appropriate next step?", "options": {"A": "Add oral fluconazole", "B": "Refer for oral isotretinoin therapy", "C": "Increase topical corticosteroid strength", "D": "Prescribe co-cyprindiol only"}, "correct": "B", "explanation": "Severe/nodulocystic acne not responding to antibiotics is the primary indication for isotretinoin. Topical corticosteroids are not used for acne. Co-cyprindiol is an adjunct in females, not a treatment for nodular acne."},
                ]},
            },
        ],
        "flashcards": [
            {"question": "Auspitz sign in psoriasis?", "answer": "Pinpoint bleeding when psoriatic scale is removed — caused by thinning of suprapapillary epidermis over dilated dermal capillaries.", "difficulty": "easy"},
            {"question": "Treatment ladder for moderate psoriasis (after topicals fail)?", "answer": "1. NB-UVB phototherapy 2. Methotrexate or ciclosporin 3. Biologics (TNF-α, IL-17, IL-23 inhibitors)", "difficulty": "medium"},
            {"question": "4 factors in acne pathogenesis?", "answer": "1) Sebum overproduction 2) Follicular hyperkeratinisation 3) C. acnes colonisation 4) Inflammation", "difficulty": "easy"},
            {"question": "Why is isotretinoin teratogenic?", "answer": "Causes craniofacial, cardiac, CNS, and thymic malformations. Mandatory pregnancy prevention (contraception + monthly β-hCG) required during and 1 month after treatment.", "difficulty": "hard"},
            {"question": "First-line treatment for chronic spontaneous urticaria?", "answer": "2nd-generation antihistamines (cetirizine, loratadine, fexofenadine). Up-titrate to 4× standard dose. Add omalizumab if refractory.", "difficulty": "medium"},
        ],
        "mcqs": [
            {"question": "A 28-year-old with severe psoriasis has failed topicals and NB-UVB. Which biologic targets the IL-17 pathway?", "options": {"A": "Adalimumab", "B": "Secukinumab", "C": "Ustekinumab", "D": "Etanercept"}, "correct": "B", "explanation": "Secukinumab is an IL-17A inhibitor. Adalimumab and etanercept are TNF-α inhibitors. Ustekinumab targets IL-12/23 (p40 subunit).", "difficulty": "hard"},
        ],
    },

    {
        "specialty_code": "dermatology",
        "code": "DERM-002",
        "title": "Skin Infections & Malignancy",
        "description": "Bacterial/viral/fungal skin infections, melanoma, BCC, SCC — recognition and management.",
        "difficulty": "intermediate",
        "estimated_hours": 3,
        "lessons": [
            {
                "title": "Skin Infections",
                "lesson_order": 0,
                "estimated_minutes": 25,
                "content": {"blocks": [
                    {"type": "text", "content": "## Bacterial Skin Infections\n\n**Impetigo:** Superficial, highly contagious. Golden-crusted lesions. S. aureus (bullous) or Strep pyogenes (non-bullous). Treatment: topical fusidic acid or mupirocin; systemic flucloxacillin for widespread disease.\n\n**Cellulitis:** Non-necrotising infection of dermis + subcutaneous tissue. Usually Strep pyogenes. Tender erythema, warmth, swelling, fever. Treatment: oral amoxicillin/co-amoxiclav or IV benzylpenicillin + flucloxacillin for severe cases. Mark border with pen to monitor spread.\n\n**Necrotising fasciitis:** Surgical emergency. Pain disproportionate to appearance, rapid spread, systemic toxicity, skin necrosis. 'Dishwater' fluid in wounds. Treatment: urgent surgical debridement + broad-spectrum IV antibiotics (pip/taz + clindamycin).\n\n## Viral\n\n**Herpes zoster (shingles):** VZV reactivation. Dermatomal distribution, vesicular rash. Postherpetic neuralgia common. Treatment: aciclovir 800 mg 5× daily × 7 days (within 72h of rash). Vaccination (Shingrix) for ≥50 years.\n\n**Molluscum contagiosum:** Poxvirus. Pearly, umbilicated papules. Self-limiting in immunocompetent (6–18 months). Treat if extensive or immunocompromised.\n\n## Fungal\n\n**Tinea (dermatophyte):** Annular with central clearing, active advancing edge. Tinea capitis requires oral antifungal (griseofulvin or terbinafine). Tinea pedis/corporis: topical clotrimazole.\n\n**Candida:** Intertrigo in skin folds. Satellite lesions. Topical clotrimazole; oral fluconazole for resistant cases."},
                    {"type": "quiz", "question": "A 55-year-old diabetic develops severe pain in the right leg out of proportion to the mild erythema visible. The skin is slightly mottled and she is septic. What is the immediate management?", "options": {"A": "Oral flucloxacillin and observe", "B": "IV antibiotics and urgent surgical debridement", "C": "Mark cellulitis border and review in 24 hours", "D": "Antifungal cream and analgesia"}, "correct": "B", "explanation": "Pain disproportionate to appearance + rapid systemic deterioration + skin discolouration = necrotising fasciitis. This is a surgical emergency. Immediate broad-spectrum IV antibiotics (pip/taz + clindamycin) AND urgent surgical debridement. Delay = death."},
                ]},
            },
            {
                "title": "Skin Cancer — Melanoma, BCC, SCC",
                "lesson_order": 1,
                "estimated_minutes": 30,
                "content": {"blocks": [
                    {"type": "text", "content": "## Skin Malignancies\n\n### Melanoma\n**ABCDE criteria:** Asymmetry, Border irregularity, Colour variation, Diameter >6mm, Evolution.\n\nMost common in fair-skinned individuals with UV exposure. Can arise de novo or from existing naevus.\n\n**Staging:** Breslow thickness (depth in mm) is the most important prognostic factor.\n- <1 mm: 5-year survival >95%\n- >4 mm or ulcerated: 5-year survival ~50%\n\n**Treatment:** Wide local excision (margins depend on Breslow). Sentinel lymph node biopsy for >1 mm. Metastatic: pembrolizumab (PD-1 inhibitor), BRAF inhibitors (vemurafenib) if BRAF V600E mutation.\n\n### Basal Cell Carcinoma (BCC)\n**Most common skin cancer.** Pearly, rolled edges, telangiectasia, central ulceration ('rodent ulcer'). Sun-exposed areas (face, ears). Rarely metastasises.\n\nTreatment: surgical excision, Mohs micrographic surgery (cosmetically sensitive areas), PDT, imiquimod.\n\n### Squamous Cell Carcinoma (SCC)\nArises from keratinocytes. Risk factors: UV, immunosuppression, actinic keratoses, HPV. Crusted, indurated lesion on sun-exposed skin. Can metastasise (especially lip/ear/immunocompromised).\n\nTreatment: wide local excision ± sentinel node biopsy for high-risk lesions."},
                    {"type": "quiz", "question": "A 70-year-old presents with a pearly papule with rolled, translucent edges and a central ulcer on his nose. He is a retired farmer. Diagnosis?", "options": {"A": "Squamous cell carcinoma", "B": "Basal cell carcinoma", "C": "Melanoma", "D": "Keratoacanthoma"}, "correct": "B", "explanation": "Pearly, rolled edges with central ulceration ('rodent ulcer') on sun-exposed skin = BCC. SCC is crusted and indurated. Melanoma follows ABCDE criteria. Keratoacanthoma grows rapidly and has a central keratin plug."},
                ]},
            },
        ],
        "flashcards": [
            {"question": "Signs of necrotising fasciitis vs. cellulitis?", "answer": "NF: pain disproportionate to appearance, rapid spread, bullae, skin necrosis, crepitus, systemic toxicity, 'dishwater' discharge. Cellulitis: localised erythema/warmth/swelling, responds to antibiotics.", "difficulty": "hard"},
            {"question": "Breslow thickness — prognostic significance in melanoma?", "answer": "Most important prognostic factor. <1 mm: >95% 5-year survival. 1–4 mm: intermediate. >4 mm or ulcerated: ~50% 5-year survival.", "difficulty": "medium"},
            {"question": "ABCDE criteria for melanoma?", "answer": "Asymmetry, Border irregularity, Colour variation, Diameter >6mm, Evolution (change over time)", "difficulty": "easy"},
            {"question": "Treatment for metastatic BRAF V600E-mutated melanoma?", "answer": "BRAF inhibitor (vemurafenib/dabrafenib) ± MEK inhibitor (trametinib). Also: pembrolizumab (PD-1 inhibitor) for PD-L1+ or as first-line immunotherapy.", "difficulty": "hard"},
        ],
        "mcqs": [
            {"question": "Which skin malignancy most commonly metastasises to regional lymph nodes?", "options": {"A": "Basal cell carcinoma", "B": "Squamous cell carcinoma", "C": "Seborrhoeic keratosis", "D": "Dermatofibroma"}, "correct": "B", "explanation": "SCC can metastasise, especially from high-risk sites (lip, ear, immunocompromised hosts). BCC very rarely metastasises (<0.5%). Seborrhoeic keratosis and dermatofibroma are benign.", "difficulty": "medium"},
        ],
    },
]


async def seed() -> int:
    """Idempotent seed for PSYCH, ANES, ONC, DERM modules. Returns count seeded."""
    async with AsyncSessionLocal() as db:
        seeded = 0
        for mod_def in MODULES:
            # Find specialty
            spec_result = await db.execute(
                select(Specialty).where(Specialty.code == mod_def["specialty_code"])
            )
            specialty = spec_result.scalar_one_or_none()
            if not specialty:
                continue  # specialty not yet created — retry on next startup

            # Idempotency check
            existing = await db.execute(select(Module).where(Module.code == mod_def["code"]))
            if existing.scalar_one_or_none():
                continue

            mod_id = uuid.uuid4()
            module = Module(
                id=mod_id,
                specialty_id=specialty.id,
                code=mod_def["code"],
                title=mod_def["title"],
                description=mod_def.get("description", ""),
                difficulty=mod_def.get("difficulty", "intermediate"),
                estimated_hours=mod_def.get("estimated_hours", 2),
                is_fundamental=False,
                is_published=True,
            )
            db.add(module)
            await db.flush()

            for l in mod_def.get("lessons", []):
                db.add(Lesson(
                    module_id=mod_id,
                    title=l["title"],
                    lesson_order=l.get("lesson_order", 0),
                    estimated_minutes=l.get("estimated_minutes", 20),
                    content=l["content"],
                    status="published",
                    published_at=datetime.utcnow(),
                ))

            for f in mod_def.get("flashcards", []):
                db.add(Flashcard(
                    module_id=mod_id,
                    question=f["question"],
                    answer=f["answer"],
                    difficulty=f.get("difficulty", "medium"),
                ))

            for q in mod_def.get("mcqs", []):
                db.add(MCQQuestion(
                    module_id=mod_id,
                    question=q["question"],
                    options=q["options"],
                    correct=q["correct"],
                    explanation=q.get("explanation", ""),
                    difficulty=q.get("difficulty", "medium"),
                ))

            await db.commit()
            seeded += 1

        return seeded


if __name__ == "__main__":
    count = asyncio.run(seed())
    print(f"Seeded {count} new specialty modules.")
