"""
Add MCQ questions to NURSE-009, -010, -011, -018
and create new modules NURSE-012 through NURSE-017.
Run: python3 /opt/medmind/backend/scripts/add_nurse_mcqs_and_modules.py
"""
import json, os

MODULES_DIR = "/opt/medmind/Modules"

# ─────────────────────────────────────────────────────────────────────────────
# MCQs for NURSE-009: Mental Health & Psychiatric Nursing
# ─────────────────────────────────────────────────────────────────────────────
NURSE009_MCQ = [
  {
    "question": "A nurse is assessing a patient with schizophrenia who has been prescribed haloperidol. The patient demonstrates sustained muscle contractions causing abnormal postures. Which extrapyramidal side effect is this?",
    "question_type": "mcq",
    "options": {"A": "Akathisia", "B": "Tardive dyskinesia", "C": "Dystonia", "D": "Pseudoparkinsonism"},
    "correct": "C",
    "explanation": "Acute dystonia presents as sudden, sustained involuntary muscle contractions causing abnormal posturing (e.g., torticollis, oculogyric crisis). It occurs early in antipsychotic treatment and is treated with anticholinergics (benztropine) or antihistamines (diphenhydramine). Akathisia is motor restlessness; tardive dyskinesia is late-onset repetitive movements; pseudoparkinsonism mimics Parkinson's disease.",
    "difficulty": "medium"
  },
  {
    "question": "A patient on clozapine therapy reports fever, sore throat, and malaise. The nurse's priority action is:",
    "question_type": "mcq",
    "options": {"A": "Administer acetaminophen and continue clozapine", "B": "Obtain a CBC with differential immediately", "C": "Schedule an appointment for next week", "D": "Switch to a different antipsychotic"},
    "correct": "B",
    "explanation": "Clozapine carries a black-box warning for agranulocytosis (ANC <500/μL). Fever, sore throat, and malaise are warning signs. A CBC with differential must be obtained immediately. If ANC <1000/μL, clozapine must be withheld; <500/μL requires permanent discontinuation. REMS program mandates regular ANC monitoring before dispensing.",
    "difficulty": "hard"
  },
  {
    "question": "Which therapeutic communication technique is MOST appropriate when a patient states, 'No one cares about me'?",
    "question_type": "mcq",
    "options": {"A": "\"Of course people care — your family visits every day\"", "B": "\"Tell me more about what makes you feel that way\"", "C": "\"That's not true. I care about you\"", "D": "\"Have you been sleeping well?\""},
    "correct": "B",
    "explanation": "Exploring the patient's statement with an open-ended prompt encourages self-expression and demonstrates genuine interest. Reassurance ('of course people care') or denying feelings ('that's not true') invalidates the patient's experience. Changing the subject derails therapeutic engagement. The nurse's role is to explore, not correct.",
    "difficulty": "easy"
  },
  {
    "question": "A patient with bipolar disorder is started on lithium. Which early sign of lithium toxicity must the nurse teach the patient to report?",
    "question_type": "mcq",
    "options": {"A": "Polyuria and polydipsia", "B": "Coarse tremor, vomiting, and diarrhea", "C": "Weight gain and acne", "D": "Mild fine hand tremor at rest"},
    "correct": "B",
    "explanation": "Coarse tremor, nausea/vomiting, and diarrhea indicate early-moderate lithium toxicity (levels >1.5 mEq/L). Fine hand tremor is a benign side effect at therapeutic levels. Polyuria/polydipsia are side effects, not toxicity signs. Therapeutic range is 0.6–1.2 mEq/L for maintenance. Severe toxicity (>2.0 mEq/L) causes ataxia, seizures, and coma.",
    "difficulty": "medium"
  },
  {
    "question": "A patient tells the nurse: 'I have a specific plan to kill myself tonight — I have pills at home.' The nurse's FIRST action is:",
    "question_type": "mcq",
    "options": {"A": "Ask the patient to promise not to hurt themselves", "B": "Initiate a safety/no-harm contract", "C": "Stay with the patient and notify the provider immediately", "D": "Contact family members to remove the pills from home"},
    "correct": "C",
    "explanation": "This patient has a specific, lethal plan with means available — high lethality risk. The priority is maintaining constant observation (1:1 monitoring) and immediately notifying the provider for crisis evaluation and possible involuntary hold. Safety contracts are not evidence-based for high-risk patients. Contacting family is secondary and requires HIPAA considerations.",
    "difficulty": "medium"
  },
  {
    "question": "When caring for a patient experiencing alcohol withdrawal on day 2, the nurse should prioritize monitoring for:",
    "question_type": "mcq",
    "options": {"A": "Delirium tremens (DTs) and seizures", "B": "Hyperglycemia and weight gain", "C": "Akathisia and dystonia", "D": "Orthostatic hypotension only"},
    "correct": "A",
    "explanation": "Alcohol withdrawal seizures peak at 24–48 hours; delirium tremens (autonomic instability, confusion, hallucinations) peaks 48–96 hours after last drink. Both are life-threatening. The CIWA-Ar scale guides benzodiazepine treatment. Thiamine (B1) must be given before glucose to prevent Wernicke's encephalopathy.",
    "difficulty": "hard"
  },
  {
    "question": "The nurse administers olanzapine to a patient with schizophrenia. Which metabolic parameters require long-term monitoring?",
    "question_type": "mcq",
    "options": {"A": "Serum lithium levels and renal function", "B": "Weight, fasting glucose, and lipid panel", "C": "CBC with differential monthly", "D": "QTc interval weekly"},
    "correct": "B",
    "explanation": "Second-generation (atypical) antipsychotics like olanzapine, clozapine, and quetiapine cause metabolic syndrome: weight gain, hyperglycemia, and dyslipidemia. Monitoring: BMI monthly for 3 months then quarterly; fasting glucose and lipids at baseline, 3 months, then annually. QTc monitoring applies mainly to ziprasidone; CBC monitoring to clozapine.",
    "difficulty": "medium"
  },
  {
    "question": "A nurse on a psychiatric unit observes a patient wringing hands, pacing, and stating 'I can't sit still — it's unbearable.' This is MOST consistent with:",
    "question_type": "mcq",
    "options": {"A": "Tardive dyskinesia", "B": "Acute mania", "C": "Akathisia", "D": "Neuroleptic malignant syndrome"},
    "correct": "C",
    "explanation": "Akathisia is a subjective sense of inner restlessness with an irresistible urge to move — a common EPS from antipsychotics. It is distressing and increases suicide/non-adherence risk. Treatment: reduce antipsychotic dose, or add propranolol/benzodiazepine. NMS presents with hyperthermia, rigidity, autonomic instability, and elevated CK — a medical emergency.",
    "difficulty": "medium"
  },
  {
    "question": "When applying the principle of least restrictive environment in psychiatric care, which intervention is implemented LAST?",
    "question_type": "mcq",
    "options": {"A": "Verbal de-escalation techniques", "B": "PRN oral medication", "C": "Physical restraints", "D": "Moving the patient to a quiet room"},
    "correct": "C",
    "explanation": "Physical restraints are used only as a last resort after all less restrictive measures have failed, per TJC and CMS standards. The hierarchy is: verbal de-escalation → environmental modification (quiet room) → voluntary PRN medication → involuntary IM medication → physical restraints. Restraints require a physician/APRN order, continuous monitoring, and regular reassessment.",
    "difficulty": "easy"
  },
  {
    "question": "A patient with major depressive disorder is started on sertraline (SSRI). Which patient education point is MOST important in the first 2 weeks?",
    "question_type": "mcq",
    "options": {"A": "Avoid all caffeinated beverages", "B": "Report any increase in suicidal ideation immediately", "C": "Full antidepressant effect is expected within 3 days", "D": "Stop taking if nausea occurs"},
    "correct": "B",
    "explanation": "SSRIs carry an FDA black-box warning for increased suicidal ideation in patients under 25 during the first weeks of treatment. The nurse must instruct the patient (and family) to report worsening depression, agitation, or suicidal thoughts immediately. Nausea is common but manageable — do not stop abruptly. Full therapeutic effect takes 4–6 weeks.",
    "difficulty": "medium"
  },
  {
    "question": "Which assessment finding in a patient taking an MAOI antidepressant requires IMMEDIATE nursing action?",
    "question_type": "mcq",
    "options": {"A": "Mild headache after eating aged cheese", "B": "BP 210/118 with severe occipital headache and diaphoresis", "C": "Dry mouth and constipation", "D": "Mild sexual dysfunction"},
    "correct": "B",
    "explanation": "Hypertensive crisis (BP ≥180/120 with target organ signs) from tyramine ingestion is a life-threatening emergency with MAOIs (phenelzine, tranylcypromine). Tyramine-rich foods (aged cheese, cured meats, red wine) must be avoided. Treatment: phentolamine or nifedipine. The patient must call 911 immediately for severe headache + hypertension — intracerebral hemorrhage risk.",
    "difficulty": "hard"
  },
  {
    "question": "A nurse is caring for a patient with anorexia nervosa who is medically stable and beginning nutritional rehabilitation. Which vital sign change requires immediate attention?",
    "question_type": "mcq",
    "options": {"A": "Bradycardia (HR 55 bpm)", "B": "Temperature 36.8°C", "C": "BP 100/65 mmHg lying flat", "D": "Respiratory rate 14/min"},
    "correct": "A",
    "explanation": "Bradycardia is a cardinal sign of severe malnutrition and increased risk of fatal arrhythmia in anorexia nervosa. Refeeding syndrome (hypophosphatemia causing cardiac arrhythmia) is a major risk in early nutritional rehabilitation. HR <50 or any sign of arrhythmia requires immediate cardiology evaluation. Phosphate, potassium, and magnesium must be monitored daily during refeeding.",
    "difficulty": "hard"
  },
  {
    "question": "Which statement by a patient with PTSD indicates understanding of trauma-focused therapy goals?",
    "question_type": "mcq",
    "options": {"A": "\"I need to avoid anything that reminds me of what happened\"", "B": "\"I'll learn to process the trauma so it no longer controls my life\"", "C": "\"Medication alone will eliminate my flashbacks\"", "D": "\"Talking about the trauma will make it worse\""},
    "correct": "B",
    "explanation": "Evidence-based PTSD treatments (Prolonged Exposure, EMDR, Cognitive Processing Therapy) work by gradually processing traumatic memories to reduce their emotional power — not avoidance. Avoidance perpetuates PTSD. Medications (SSRIs, prazosin for nightmares) are adjuncts, not monotherapy. Understanding that processing leads to recovery indicates good therapeutic alliance.",
    "difficulty": "medium"
  },
  {
    "question": "Which intervention is CONTRAINDICATED for a patient experiencing an acute manic episode?",
    "question_type": "mcq",
    "options": {"A": "Providing a structured, low-stimulation environment", "B": "Offering high-calorie finger foods during activity", "C": "Encouraging group therapy participation with many peers", "D": "Setting clear, consistent limits on behaviour"},
    "correct": "C",
    "explanation": "During acute mania, the patient is highly stimulable, grandiose, and may escalate in group settings — peer interaction increases stimulation. Interventions should reduce environmental stimulation: quiet environment, short 1:1 interactions, simple clear boundaries. Nutrition is important as manic patients may not stop to eat. Group therapy is appropriate only after acute symptoms stabilize.",
    "difficulty": "medium"
  },
  {
    "question": "A nurse witnesses a patient receive an unexpected prognosis and then become completely silent and motionless. The patient's affect is flat and they do not respond to questions. The nurse should FIRST:",
    "question_type": "mcq",
    "options": {"A": "Leave the patient alone to process the information privately", "B": "Call a rapid response due to unresponsiveness", "C": "Sit with the patient in silence and acknowledge the difficulty of the news", "D": "Ask the patient to rate their pain on a 0-10 scale"},
    "correct": "C",
    "explanation": "This patient is in acute psychological shock — a normal response to devastating news. Silence and presence is a powerful therapeutic communication technique. Leaving them alone abandons them; calling a rapid response is inappropriate for emotional shock without neurological signs; immediately assessing pain is tone-deaf to the situation. Sit, be present, and acknowledge: 'I can see this is very difficult news.'",
    "difficulty": "medium"
  }
]

# ─────────────────────────────────────────────────────────────────────────────
# MCQs for NURSE-010: Crisis Intervention, Abuse & Substance Use
# ─────────────────────────────────────────────────────────────────────────────
NURSE010_MCQ = [
  {
    "question": "A nurse in the ED is caring for a woman with multiple bruises in various stages of healing. The patient's partner stays very close and answers questions on her behalf. The nurse's PRIORITY action is:",
    "question_type": "mcq",
    "options": {"A": "Treat the injuries and discharge without confrontation", "B": "Ask the partner to wait outside and speak privately with the patient", "C": "Document suspected abuse and continue the visit normally", "D": "Confront the partner about the bruises"},
    "correct": "B",
    "explanation": "Separating the potential victim from the suspected abuser is the priority — it allows private, safe disclosure. Abusers commonly control the narrative during healthcare visits. After separation, use validated screening (HITS or SAFE questions). Mandatory reporting varies by state for adult IPV but is required for child/elder abuse. Confronting the abuser can escalate danger.",
    "difficulty": "medium"
  },
  {
    "question": "A patient in alcohol withdrawal presents with HR 120, BP 160/100, temperature 38.2°C, and generalized tremors. Their CIWA-Ar score is 18. Which treatment is MOST appropriate?",
    "question_type": "mcq",
    "options": {"A": "IV lorazepam per CIWA-Ar protocol", "B": "IV haloperidol for agitation", "C": "Oral naltrexone", "D": "Oral thiamine only"},
    "correct": "A",
    "explanation": "CIWA-Ar ≥10 indicates moderate-severe withdrawal requiring benzodiazepines. IV/IM lorazepam (or diazepam) is the first-line treatment — GABA-A agonists prevent seizures and DTs. Haloperidol lowers seizure threshold and worsens withdrawal. Naltrexone is for maintenance, not acute withdrawal. Thiamine is adjunct (given before dextrose) but does not treat withdrawal itself.",
    "difficulty": "hard"
  },
  {
    "question": "A nurse using crisis intervention for a patient threatening self-harm should FIRST:",
    "question_type": "mcq",
    "options": {"A": "Assess the patient's usual coping mechanisms", "B": "Establish rapport and ensure immediate safety", "C": "Contact the patient's family", "D": "Review the patient's psychiatric history"},
    "correct": "B",
    "explanation": "Roberts' 7-Stage Crisis Intervention Model begins with: (1) assess lethality and immediate danger, (2) establish rapport. Safety is the foundation of all crisis intervention — without it, no therapeutic work can proceed. Coping assessment and history are important but secondary. Family contact may be appropriate but requires patient consent and comes after stabilization.",
    "difficulty": "medium"
  },
  {
    "question": "A nurse is assessing a 4-year-old child who presents with multiple bruises on the buttocks and inner thighs in various stages of healing. The parent's explanation is inconsistent with the injury pattern. The nurse MUST:",
    "question_type": "mcq",
    "options": {"A": "Document and report suspected child abuse to child protective services", "B": "Ask the child directly if they were hurt by their parent", "C": "Confront the parent about the inconsistency", "D": "Wait for more evidence before reporting"},
    "correct": "A",
    "explanation": "Nurses are mandated reporters. Suspected child abuse MUST be reported regardless of certainty — the threshold is reasonable suspicion, not proof. Injuries in protected areas (buttocks, inner thighs) with inconsistent explanation are highly concerning. Mandated reporters are protected from liability for good-faith reports. Direct forensic questioning of the child should be done by trained investigators to avoid contaminating testimony.",
    "difficulty": "medium"
  },
  {
    "question": "Which assessment finding in an opioid-dependent patient who received naloxone 30 minutes ago is MOST concerning?",
    "question_type": "mcq",
    "options": {"A": "Mild agitation and diaphoresis", "B": "Respiratory rate 14/min, SpO2 97%", "C": "Return of pinpoint pupils and RR 8/min", "D": "Requesting water and complaining of headache"},
    "correct": "C",
    "explanation": "Naloxone has a shorter half-life (30–90 min) than most opioids. Renarcotization — return of opioid toxidrome (miosis, respiratory depression) after naloxone wears off — is the primary danger. RR 8 with pinpoint pupils after naloxone indicates renarcotization requiring repeat dosing and continuous monitoring. Mild agitation is expected (opioid withdrawal precipitation); requesting water is benign.",
    "difficulty": "hard"
  },
  {
    "question": "A nurse performs a CAGE assessment. A patient answers 'yes' to 3 of 4 questions. This result suggests:",
    "question_type": "mcq",
    "options": {"A": "Alcohol dependence requiring further evaluation", "B": "Safe alcohol consumption patterns", "C": "Marijuana dependence", "D": "Depression requiring antidepressant therapy"},
    "correct": "A",
    "explanation": "CAGE: Cut down, Annoyed, Guilty, Eye-opener. ≥2 positive answers has 60–95% sensitivity for alcohol use disorder — requires further evaluation and intervention. 3-4 positives strongly suggests dependence. CAGE screens specifically for alcohol, not other substances. A positive screen initiates brief intervention, referral, and medical assessment for withdrawal risk.",
    "difficulty": "easy"
  },
  {
    "question": "A pregnant patient in her third trimester discloses she has been using heroin daily. The MOST appropriate initial intervention is:",
    "question_type": "mcq",
    "options": {"A": "Immediate referral to detoxification (cold turkey withdrawal)", "B": "Methadone or buprenorphine maintenance therapy with obstetric co-management", "C": "Naltrexone to block opioid effects", "D": "Encourage gradual self-tapering at home"},
    "correct": "B",
    "explanation": "SAMHSA guidelines strongly recommend medication-assisted treatment (methadone or buprenorphine) in pregnancy — NOT abrupt withdrawal. Opioid withdrawal in pregnancy risks preterm labour, placental abruption, and fetal death. Methadone/buprenorphine stabilizes the fetus. Neonatal abstinence syndrome (NAS) is expected and manageable. Naltrexone is contraindicated in active opioid use (precipitates withdrawal).",
    "difficulty": "hard"
  },
  {
    "question": "An elderly patient presents with confusion, unexplained weight loss, poor hygiene, and fearful body language toward the adult son who is the caregiver. This presentation is MOST consistent with:",
    "question_type": "mcq",
    "options": {"A": "Normal age-related cognitive decline", "B": "Elder abuse and neglect", "C": "Early Alzheimer's disease", "D": "Delirium from UTI"},
    "correct": "B",
    "explanation": "Multiple red flags for elder abuse: weight loss (neglect), poor hygiene (neglect), fearful affect toward caregiver (possible physical/psychological abuse), and confusion that may be from malnutrition or fear. Elder abuse affects 1 in 10 elderly Americans. Assessment tools include the Elder Abuse Suspicion Index (EASI). Mandatory reporting applies in all US states for elder abuse in care settings.",
    "difficulty": "medium"
  },
  {
    "question": "During a Motivational Interviewing session, a patient states: 'I know I should stop drinking, but I'm not sure I'm ready.' The BEST response using MI principles is:",
    "question_type": "mcq",
    "options": {"A": "\"You need to stop drinking now — it will kill you\"", "B": "\"What would need to be different for you to feel ready?\"", "C": "\"You've already tried before and failed — what makes this time different?\"", "D": "\"I'll refer you to AA immediately\""},
    "correct": "B",
    "explanation": "Motivational Interviewing uses open-ended questions, affirmations, reflective listening, and summaries (OARS). The patient is in the contemplation stage (Prochaska's TTM). Exploring what would build readiness honors autonomy and evokes the patient's own motivation (internal vs. external). Confrontation ('you'll die') creates reactance. MI is non-confrontational and collaborative.",
    "difficulty": "medium"
  },
  {
    "question": "A patient arrives in the ED after a suicide attempt by overdose. After medical stabilization, the psychiatry team recommends discharge. The nurse's PRIORITY before discharge is:",
    "question_type": "mcq",
    "options": {"A": "Provide a list of crisis hotline numbers", "B": "Ensure a safety plan is developed and the patient can verbalize it", "C": "Contact the patient's employer about the absence", "D": "Arrange a follow-up appointment in 30 days"},
    "correct": "B",
    "explanation": "A safety plan (Stanley-Brown model) is evidence-based crisis planning: warning signs, coping strategies, social contacts, means restriction, and professional contacts. The patient must be able to verbalize and demonstrate understanding. Means counselling (removing firearms, medications) is critical. Follow-up within 24–72 hours, not 30 days. Hotline numbers alone are insufficient after a serious attempt.",
    "difficulty": "medium"
  },
  {
    "question": "Which finding in a patient with cocaine intoxication requires IMMEDIATE intervention?",
    "question_type": "mcq",
    "options": {"A": "Elevated mood and increased energy", "B": "Dilated pupils and mild tachycardia (HR 95)", "C": "Chest pain with ST-segment elevation on ECG", "D": "Mild diaphoresis and restlessness"},
    "correct": "C",
    "explanation": "Cocaine causes coronary vasospasm and thrombosis leading to myocardial infarction — the most common cause of cocaine-related death. ST-elevation indicates STEMI requiring immediate cath lab activation. Note: nitroglycerin and calcium-channel blockers are used over beta-blockers (beta-blockers can worsen cocaine-induced vasospasm via unopposed alpha activity). Aspirin and benzodiazepines (for hypertension/agitation) are first-line.",
    "difficulty": "hard"
  },
  {
    "question": "A nurse documents suspected child abuse. The parent threatens the nurse with a lawsuit if a report is made. The nurse's BEST response is:",
    "question_type": "mcq",
    "options": {"A": "Delay the report until consulting hospital legal counsel", "B": "Proceed with the mandatory report — nurses are legally protected for good-faith reports", "C": "Document the parent's threat and wait for supervisor approval", "D": "Transfer care to a physician to make the report"},
    "correct": "B",
    "explanation": "All 50 US states grant immunity from civil and criminal liability for mandated reporters who make good-faith reports. Failing to report is a crime — penalties include license revocation and prosecution. The duty to report is the nurse's individual legal obligation and cannot be transferred. Threats from parents do not suspend mandated reporting requirements.",
    "difficulty": "medium"
  },
  {
    "question": "Which nursing intervention BEST supports recovery for a patient with substance use disorder being discharged to the community?",
    "question_type": "mcq",
    "options": {"A": "Instruct the patient to avoid all social contact for 6 months", "B": "Connect the patient with peer support, MAT continuation, and community recovery services", "C": "Provide a list of inpatient detox programs only", "D": "Advise the patient to rely solely on willpower"},
    "correct": "B",
    "explanation": "Recovery is sustained by a continuum of care: medication-assisted treatment (MAT — buprenorphine/methadone for opioids, naltrexone for alcohol), peer support specialists, 12-step or SMART Recovery meetings, case management, and housing stability. Isolation increases relapse risk. Willpower-only approaches have the lowest evidence base. The SAMHSA 8 Dimensions of Wellness framework guides holistic recovery.",
    "difficulty": "easy"
  }
]

# ─────────────────────────────────────────────────────────────────────────────
# MCQs for NURSE-011: Maternal Nursing
# ─────────────────────────────────────────────────────────────────────────────
NURSE011_MCQ = [
  {
    "question": "A patient at 32 weeks gestation presents with sudden-onset bright red, painless vaginal bleeding. The nurse's PRIORITY action is:",
    "question_type": "mcq",
    "options": {"A": "Perform a vaginal exam to assess cervical dilation", "B": "Place the patient in left lateral position and apply fetal monitor", "C": "Prepare for immediate amniocentesis", "D": "Encourage ambulation to stimulate labour"},
    "correct": "B",
    "explanation": "Painless bright red bleeding at 32 weeks is placenta previa until proven otherwise. Vaginal exams are CONTRAINDICATED (can cause catastrophic haemorrhage). Priority: left lateral positioning (relieve aortocaval compression), continuous fetal monitoring, IV access, type and crossmatch, call provider. Diagnosis confirmed by ultrasound. Emergency C-section if haemodynamically unstable.",
    "difficulty": "hard"
  },
  {
    "question": "A primigravida at 38 weeks has BP 158/105 mmHg, 3+ proteinuria, and reports persistent severe headache and visual changes. Which diagnosis and intervention are CORRECT?",
    "question_type": "mcq",
    "options": {"A": "Gestational hypertension — start oral nifedipine and monitor", "B": "Severe preeclampsia — initiate IV magnesium sulfate and prepare for delivery", "C": "Chronic hypertension — continue home antihypertensives", "D": "Mild preeclampsia — bed rest and repeat labs in 1 week"},
    "correct": "B",
    "explanation": "Severe preeclampsia criteria (ACOG): BP ≥160/110 on two readings, severe symptoms (headache, visual changes, epigastric pain), plus proteinuria. IV magnesium sulfate 4-6g loading dose is given for seizure prophylaxis. Definitive treatment is delivery. Magnesium toxicity signs: loss of DTRs (first sign), RR <12, urinary output <25mL/hr. Calcium gluconate is the antidote.",
    "difficulty": "hard"
  },
  {
    "question": "A nurse is administering IV magnesium sulfate to a preeclamptic patient. Which finding requires the nurse to STOP the infusion immediately?",
    "question_type": "mcq",
    "options": {"A": "Flushing and mild diaphoresis", "B": "Absent deep tendon reflexes and respiratory rate 10/min", "C": "Urine output 30 mL/hr", "D": "Serum magnesium level 5 mg/dL"},
    "correct": "B",
    "explanation": "Absent DTRs (earliest clinical sign of toxicity) + RR <12 indicate severe magnesium toxicity. Stop infusion immediately and prepare calcium gluconate 1g IV (antidote). Therapeutic range: 4–7 mg/dL (2–3.5 mEq/L). Toxic: DTR loss at 7–10 mg/dL; respiratory arrest at 10–13 mg/dL. Mild flushing is an expected side effect, not toxicity.",
    "difficulty": "hard"
  },
  {
    "question": "A patient at 28 weeks is diagnosed with gestational diabetes mellitus (GDM). Which dietary instruction is CORRECT?",
    "question_type": "mcq",
    "options": {"A": "Follow a high-protein, carbohydrate-free diet", "B": "Distribute carbohydrate intake evenly across 3 meals and 2–3 snacks daily", "C": "Eliminate all fruit and dairy from the diet", "D": "Follow the same diet as a non-pregnant diabetic patient"},
    "correct": "B",
    "explanation": "ADA/ACOG recommendation: consistent carbohydrate distribution (175g/day minimum in pregnancy), not elimination. Three meals and 2-3 snacks prevent post-meal glucose spikes and fasting hypoglycaemia. Morning carbohydrate is limited (insulin resistance is highest in the morning). Blood glucose targets: fasting <95 mg/dL; 1-hr postprandial <140 mg/dL. Most GDM is managed with diet/exercise first.",
    "difficulty": "medium"
  },
  {
    "question": "Which assessment finding in a postpartum patient at 12 hours after vaginal delivery requires IMMEDIATE nursing action?",
    "question_type": "mcq",
    "options": {"A": "Fundus firm, at umbilicus, slightly right of midline", "B": "Saturating one perineal pad per hour for 3 consecutive hours", "C": "Temperature 37.8°C on one reading", "D": "Afterbirth pains rated 4/10 during breastfeeding"},
    "correct": "B",
    "explanation": "Saturating >1 pad/hour is abnormal postpartum bleeding (PPH). Primary PPH occurs in the first 24 hours; most common cause is uterine atony. IMMEDIATE assessment: uterine tone (boggy uterus → fundal massage), bladder distension (full bladder displaces fundus, causes atony), vital signs. Notify provider, establish IV access, administer oxytocin. A single temperature of 37.8°C is not immediately concerning.",
    "difficulty": "medium"
  },
  {
    "question": "A nurse is teaching a breastfeeding patient about mastitis. Which statement by the patient indicates INCORRECT understanding?",
    "question_type": "mcq",
    "options": {"A": "\"I should continue breastfeeding even when I have mastitis\"", "B": "\"I need to stop breastfeeding immediately to let my breast heal\"", "C": "\"I should complete the full antibiotic course even if I feel better\"", "D": "\"Applying warm compresses before feeding may help drainage\""},
    "correct": "B",
    "explanation": "Mastitis is an infection of breast tissue common in the first 6 weeks postpartum. WHO and ABM guidelines recommend CONTINUING breastfeeding (or pumping) — emptying the breast is therapeutic and does not harm the infant. Stopping breastfeeding increases risk of abscess formation. Treatment: antistaphylococcal antibiotics (dicloxacillin/cephalexin), supportive care, and continued emptying.",
    "difficulty": "medium"
  },
  {
    "question": "A patient at 36 weeks presents with severe abdominal pain described as 'tearing,' a rigid board-like abdomen, and minimal vaginal bleeding. Fetal heart tones are 80 bpm. This presentation is MOST consistent with:",
    "question_type": "mcq",
    "options": {"A": "Normal onset of labour", "B": "Placenta previa", "C": "Placental abruption (abruptio placentae)", "D": "Braxton-Hicks contractions"},
    "correct": "C",
    "explanation": "Placental abruption: sudden severe abdominal pain, rigid abdomen, dark vaginal bleeding (or concealed), fetal distress. Fetal bradycardia (80 bpm) indicates fetal compromise. This is an obstetric emergency: emergency C-section. Risk factors: hypertension, cocaine use, trauma, prior abruption. Distinct from placenta previa (painless bright red bleeding). DIC can complicate severe abruption.",
    "difficulty": "hard"
  },
  {
    "question": "Which Rh-related nursing intervention is required for an Rh-negative mother who delivers an Rh-positive infant?",
    "question_type": "mcq",
    "options": {"A": "Administer Rh immunoglobulin (RhoGAM) within 72 hours of delivery", "B": "No intervention is needed after delivery if RhoGAM was given at 28 weeks", "C": "Give the infant RhoGAM to prevent haemolysis", "D": "Perform exchange transfusion on the newborn"},
    "correct": "A",
    "explanation": "Postpartum RhoGAM (300 mcg IM) must be given within 72 hours to an Rh-negative mother who delivers an Rh-positive infant. RhoGAM at 28 weeks is antenatal prophylaxis — postpartum dose is still required. Without it, the mother develops anti-D antibodies that attack Rh-positive fetuses in future pregnancies (erythroblastosis fetalis). RhoGAM is given to the mother, not the infant.",
    "difficulty": "medium"
  },
  {
    "question": "A patient who delivered 4 days ago calls the clinic reporting feeling 'sad and tearful' and occasionally overwhelmed. She is sleeping and eating adequately and is caring for her infant. This MOST likely represents:",
    "question_type": "mcq",
    "options": {"A": "Postpartum psychosis requiring immediate hospitalization", "B": "Postpartum blues — a normal, self-limiting condition", "C": "Postpartum depression requiring antidepressant therapy", "D": "Normal adjustment that requires no follow-up"},
    "correct": "B",
    "explanation": "Postpartum blues affect 50–75% of mothers, beginning day 2–3 and resolving by day 10–14 without treatment. Symptoms: tearfulness, mood swings, anxiety — while maintaining functional ability. Postpartum depression (PPD) persists >2 weeks, impairs functioning, and requires SSRI ± therapy. Postpartum psychosis is rare, rapid-onset (<72 hrs), with delusions/hallucinations — a psychiatric emergency. Edinburgh Postnatal Depression Scale (EPDS) screens at 2-week and 6-week visits.",
    "difficulty": "medium"
  },
  {
    "question": "A primigravida at 41 weeks undergoes labour induction with misoprostol (Cytotec). Twenty minutes after insertion, the fetal monitor shows a 7-minute contraction with late decelerations. The nurse's FIRST action is:",
    "question_type": "mcq",
    "options": {"A": "Increase the IV oxytocin infusion", "B": "Remove the misoprostol insert and prepare for tocolysis", "C": "Administer oxygen at 10L/min via non-rebreather mask", "D": "Notify the provider and document"},
    "correct": "B",
    "explanation": "Tachysystole (>5 contractions in 10 min) with late decelerations indicates uterine hyperstimulation causing uteroplacental insufficiency. For misoprostol: remove the vaginal insert immediately. For oxytocin: stop infusion. Then: lateral positioning, IV fluid bolus, supplemental oxygen. Tocolysis (terbutaline 0.25mg SQ) may be needed if tachysystole persists. NEVER increase oxytocin when tachysystole is occurring.",
    "difficulty": "hard"
  },
  {
    "question": "Which TORCH infection transmitted during pregnancy causes periventricular calcifications and chorioretinitis in the newborn?",
    "question_type": "mcq",
    "options": {"A": "Toxoplasmosis", "B": "Cytomegalovirus (CMV)", "C": "Rubella", "D": "Herpes simplex virus (HSV)"},
    "correct": "B",
    "explanation": "Congenital CMV is the most common congenital infection and the leading infectious cause of hearing loss and neurodevelopmental disability. Classic findings: periventricular calcifications, chorioretinitis, microcephaly, sensorineural hearing loss. CMV is transmitted via urine, saliva, breast milk. Toxoplasmosis causes diffuse intracranial calcifications. Rubella causes cataracts, cardiac defects, deafness (congenital rubella syndrome). HSV causes encephalitis.",
    "difficulty": "hard"
  },
  {
    "question": "A patient at 20 weeks is newly diagnosed with placenta previa. She is asymptomatic. The nurse should educate her to AVOID:",
    "question_type": "mcq",
    "options": {"A": "Prenatal vitamins and iron supplementation", "B": "Pelvic rest — no sexual intercourse, vaginal exams, or tampons", "C": "Light walking and low-impact exercise", "D": "All travel outside the home"},
    "correct": "B",
    "explanation": "Placenta previa (placenta covering the cervical os) requires pelvic rest: no vaginal intercourse, vaginal exams, or anything inserted into the vagina. These can trigger catastrophic haemorrhage by disturbing the placenta overlying the os. Many placenta previas resolve by 28–32 weeks as the lower uterine segment develops. Ultrasound follow-up at 28-32 weeks is standard. Iron supplementation is recommended due to haemorrhage risk.",
    "difficulty": "medium"
  }
]

# ─────────────────────────────────────────────────────────────────────────────
# MCQs for NURSE-018: Renal, Urinary & Fluid-Electrolyte Nursing
# ─────────────────────────────────────────────────────────────────────────────
NURSE018_MCQ = [
  {
    "question": "A patient in acute kidney injury (AKI) has the following lab values: K+ 6.4 mEq/L, ECG shows peaked T-waves. The nurse's PRIORITY intervention is:",
    "question_type": "mcq",
    "options": {"A": "Administer oral sodium polystyrene sulfonate (Kayexalate)", "B": "Obtain IV access and administer IV calcium gluconate", "C": "Restrict dietary potassium intake", "D": "Start haemodialysis immediately"},
    "correct": "B",
    "explanation": "Peaked T-waves with K+ 6.4 indicate severe hyperkalaemia with cardiac toxicity. IV calcium gluconate is the FIRST intervention — it stabilises the myocardium within minutes (does not lower potassium, but protects the heart). Then: insulin + dextrose (shifts K+ into cells, works in 30 min), sodium bicarbonate (if acidosis), inhaled albuterol. Kayexalate removes potassium slowly and is not first-line in emergencies. Dialysis is definitive if refractory.",
    "difficulty": "hard"
  },
  {
    "question": "A patient on haemodialysis is found to have the following post-dialysis vitals: BP 85/55 mmHg, HR 118 bpm, dizziness. This MOST likely represents:",
    "question_type": "mcq",
    "options": {"A": "Hypertensive urgency", "B": "Intradialytic hypotension", "C": "Dialysis disequilibrium syndrome", "D": "Air embolism"},
    "correct": "B",
    "explanation": "Intradialytic hypotension (IDH) is the most common complication of haemodialysis — caused by rapid fluid removal exceeding compensatory mechanisms. Treatment: Trendelenburg position, saline bolus 100–200mL, reduce ultrafiltration rate. Dialysis disequilibrium presents with neurological symptoms (headache, nausea, seizure) in new dialysis patients from cerebral oedema. Air embolism presents with sudden chest pain and dyspnea.",
    "difficulty": "medium"
  },
  {
    "question": "A nurse is caring for a patient with SIADH. Which electrolyte imbalance and its CORRECT intervention are expected?",
    "question_type": "mcq",
    "options": {"A": "Hypernatraemia — give D5W IV", "B": "Hyponatraemia — restrict free water intake", "C": "Hyperkalaemia — administer furosemide", "D": "Hyponatraemia — give IV 3% saline rapidly"},
    "correct": "B",
    "explanation": "SIADH (Syndrome of Inappropriate ADH secretion) causes dilutional hyponatraemia from water retention. Mainstay treatment: fluid restriction 800–1000mL/day. IV 3% saline is reserved for severe symptomatic hyponatraemia (Na+ <120 with seizures) and must be infused SLOWLY (max correction 8-10 mEq/L in 24 hrs) to prevent osmotic demyelination syndrome (central pontine myelinolysis). D5W worsens dilutional hyponatraemia.",
    "difficulty": "hard"
  },
  {
    "question": "Which assessment finding in a patient with nephrotic syndrome is expected?",
    "question_type": "mcq",
    "options": {"A": "Haematuria and oliguria", "B": "Massive proteinuria, hypoalbuminaemia, oedema, and hyperlipidaemia", "C": "Hypertension with elevated BUN/creatinine", "D": "Polyuria and dilute urine"},
    "correct": "B",
    "explanation": "Nephrotic syndrome triad: (1) massive proteinuria >3.5g/24hrs, (2) hypoalbuminaemia <3g/dL, (3) generalised oedema (periorbital, ascites, anasarca). Hyperlipidaemia and lipiduria are also classic. Haematuria and elevated BUN/creatinine suggest nephritic syndrome (inflammatory). Nursing: diuretics for oedema, low-sodium/high-protein diet, anticoagulation if albumin <2 (VTE risk), monitor for infections (loss of immunoglobulins).",
    "difficulty": "medium"
  },
  {
    "question": "A patient with CKD stage 4 has serum phosphate 6.2 mg/dL and complains of itching. The nurse anticipates which medication class?",
    "question_type": "mcq",
    "options": {"A": "Calcineurin inhibitors", "B": "Phosphate binders (calcium carbonate or sevelamer)", "C": "ACE inhibitors", "D": "Loop diuretics"},
    "correct": "B",
    "explanation": "In CKD, failing kidneys cannot excrete phosphate → hyperphosphataemia → calcium-phosphate product elevated → metastatic calcification and pruritus. KDIGO guidelines: phosphate binders taken with meals to bind dietary phosphate. Calcium-based binders (calcium carbonate): risk of hypercalcaemia and calcification if overused. Non-calcium binders (sevelamer) are preferred in advanced CKD. Dietary phosphate restriction is adjunct.",
    "difficulty": "medium"
  },
  {
    "question": "A patient with a urinary catheter develops fever 38.8°C, suprapubic pain, and cloudy malodorous urine. Which action is MOST appropriate?",
    "question_type": "mcq",
    "options": {"A": "Increase IV fluid rate and observe for 24 hours", "B": "Obtain urine culture from catheter port, change catheter, and notify provider", "C": "Remove catheter and send for urinalysis only", "D": "Administer antipyretics and reassess in 4 hours"},
    "correct": "B",
    "explanation": "CAUTI (Catheter-Associated UTI) diagnosis and management: obtain urine culture via the catheter sampling port (not the bag), replace the indwelling catheter before culturing to avoid biofilm contamination, notify provider for antibiotic prescription, and assess need for continued catheterisation. CAUTI prevention (CDC HICPAC): remove catheters as soon as clinically possible, use closed drainage system, hand hygiene.",
    "difficulty": "medium"
  },
  {
    "question": "A patient with a serum sodium of 120 mEq/L develops seizures. Which IV solution is CORRECT?",
    "question_type": "mcq",
    "options": {"A": "Lactated Ringer's (130 mEq/L Na)", "B": "0.9% Normal saline (154 mEq/L Na)", "C": "3% Hypertonic saline (513 mEq/L Na)", "D": "D5W (0 mEq/L Na)"},
    "correct": "C",
    "explanation": "Severe symptomatic hyponatraemia (Na <125 with seizures) requires 3% hypertonic saline to rapidly raise sodium and stop the seizure. Rate: 100mL IV bolus, then reassess. Target: raise Na by 4-6 mEq/L in the first hour to stop seizure, then slow the rate. Maximum safe correction: 8-10 mEq/L in 24 hours to prevent osmotic demyelination syndrome. D5W would worsen hyponatraemia; normal saline may not be concentrated enough for emergency correction.",
    "difficulty": "hard"
  },
  {
    "question": "A patient post-kidney transplant is on tacrolimus (FK506). Which finding suggests nephrotoxicity from the drug?",
    "question_type": "mcq",
    "options": {"A": "Blood pressure 140/90 mmHg", "B": "Rising serum creatinine with supratherapeutic tacrolimus trough levels", "C": "Mild tremors and headache", "D": "Fasting blood glucose 130 mg/dL"},
    "correct": "B",
    "explanation": "Calcineurin inhibitor (tacrolimus/cyclosporine) nephrotoxicity: rising creatinine + supratherapeutic drug trough levels. Tacrolimus trough target varies by time post-transplant (year 1: 8-12 ng/mL; maintenance: 5-8 ng/mL). Toxicity signs: decreased GFR, hyperkalemia. Must distinguish from acute rejection (also causes rising creatinine but with sub-therapeutic levels). Tremors and headache are side effects; hypertension and NODAT (new-onset diabetes) are common calcineurin inhibitor effects.",
    "difficulty": "hard"
  },
  {
    "question": "A patient with end-stage renal disease (ESRD) refuses dialysis. The nurse's BEST response is:",
    "question_type": "mcq",
    "options": {"A": "Initiate dialysis anyway — ESRD is life-threatening", "B": "Contact family members to override the decision", "C": "Explore the patient's understanding, concerns, and goals; document the informed decision", "D": "Refer immediately to psychiatry for competency evaluation"},
    "correct": "C",
    "explanation": "Competent adults have the right to refuse life-sustaining treatment, including dialysis, even if it results in death. The nurse's role is to: ensure informed decision-making (patient understands consequences), explore values and concerns, document thoroughly, and refer to palliative care for symptom management and goals-of-care discussion. Overriding a competent patient's refusal is unethical and illegal. Psychiatric referral is appropriate only if competency is genuinely uncertain.",
    "difficulty": "medium"
  },
  {
    "question": "Which dietary instruction is MOST appropriate for a patient with CKD stage 3b (eGFR 32 mL/min)?",
    "question_type": "mcq",
    "options": {"A": "High protein diet (>1.5g/kg/day) to prevent muscle wasting", "B": "Restrict protein (0.6-0.8g/kg/day), potassium, phosphate, and sodium", "C": "Liberal fluid intake to maintain renal perfusion", "D": "Increase dairy products for calcium supplementation"},
    "correct": "B",
    "explanation": "KDIGO nutrition guidelines for non-dialysis CKD: protein restriction 0.6-0.8g/kg/day slows progression by reducing glomerular hyperfiltration and urea generation. Restrict potassium (impaired excretion → hyperkalaemia), phosphate (hyperphosphataemia → renal bone disease), and sodium (hypertension control). Fluid restriction is individualized. High protein accelerates CKD progression. Dairy is high in phosphorus and potassium — limit intake.",
    "difficulty": "medium"
  },
  {
    "question": "A post-operative patient receiving aggressive IV fluid resuscitation develops SpO2 88%, bilateral crackles, and a new S3 gallop. The nurse suspects fluid overload. FIRST nursing action:",
    "question_type": "mcq",
    "options": {"A": "Increase IV fluid rate to maintain urine output", "B": "Stop or slow IV fluids and elevate head of bed 30-45°", "C": "Administer morphine for anxiety", "D": "Prepare for chest X-ray and observe"},
    "correct": "B",
    "explanation": "Iatrogenic fluid overload causing pulmonary oedema: immediate priority is stopping the source (IV fluids), improving ventilation (HOB 30-45°), and applying supplemental oxygen. Then: IV furosemide, prepare for possible CPAP/NIV. S3 gallop + crackles + hypoxia = cardiogenic pulmonary oedema until proven otherwise. Increasing fluids is directly harmful. Chest X-ray is important but observation alone delays treatment.",
    "difficulty": "medium"
  },
  {
    "question": "A patient receiving peritoneal dialysis (PD) develops a cloudy, white peritoneal effluent with abdominal pain. This is MOST consistent with:",
    "question_type": "mcq",
    "options": {"A": "Normal fibrin in the dialysate", "B": "Peritonitis — send dialysate for culture and administer intraperitoneal antibiotics", "C": "Dialysate leakage requiring catheter replacement", "D": "Ultrafiltration failure"},
    "correct": "B",
    "explanation": "Peritonitis is the most serious complication of peritoneal dialysis. Cloudy effluent (WBC >100/μL with >50% neutrophils on dialysate microscopy) + abdominal pain is peritonitis until proven otherwise. Management: send effluent for cell count, Gram stain, and culture; start empirical intraperitoneal antibiotics (covering gram-positives and gram-negatives). Most PD peritonitis can be treated without catheter removal if caused by coagulase-negative Staph; persistent/fungal peritonitis requires catheter removal.",
    "difficulty": "hard"
  }
]


def add_mcqs_to_module(code, mcqs):
    path = f"{MODULES_DIR}/module_{code}.json"
    with open(path) as f:
        data = json.load(f)

    existing = len(data.get("mcq_questions", []))
    data["mcq_questions"] = data.get("mcq_questions", []) + mcqs

    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"  {code}: {existing} → {len(data['mcq_questions'])} MCQs")


print("=== Adding MCQs to existing modules ===")
add_mcqs_to_module("NURSE-009", NURSE009_MCQ)
add_mcqs_to_module("NURSE-010", NURSE010_MCQ)
add_mcqs_to_module("NURSE-011", NURSE011_MCQ)
add_mcqs_to_module("NURSE-018", NURSE018_MCQ)

print("\nDone. Now run import_modules.py to push MCQs to the database.")
