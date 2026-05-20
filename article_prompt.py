"""
Централизованный промпт для всех генераторов статей MedMind.
Импортируется из generate_articles_groq.py, gemini.py, universal.py.
"""

ARTICLE_PROMPT = """\
You are a senior clinician and medical educator writing an authoritative clinical reference \
comparable to UpToDate, StatPearls, or Harrison's Principles of Internal Medicine.
Audience: medical students, residents, fellows, and practicing physicians.

Topic: {topic}
Category: {category}

Write a COMPREHENSIVE, DETAILED article of 4500-5000 words minimum. \
Include SPECIFIC clinical details: exact drug doses with units, diagnostic criteria with \
specific values, lab reference ranges, evidence-based guideline recommendations \
(AHA/ACC/ESC/WHO/NICE/IDSA/ACR). Every claim must have a specific number, percentage, or value.

Use EXACTLY this output format (do not skip any section):

TITLE: [Precise clinical title, max 90 characters]
EXCERPT: [4 sentences: epidemiological significance, pathophysiological mechanism, key diagnostic approach, primary management strategy]
ARTICLE_START

## Key Points
List 10-12 critical clinical facts ("- " prefix). Each point must contain a specific value, \
dose, percentage, or criterion. No vague statements.

## Overview and Epidemiology
Precise definition, ICD-10 code if relevant. Global and regional incidence/prevalence with \
specific numbers. Age/sex/race distribution. Economic burden. Major modifiable and \
non-modifiable risk factors with relative risks. (350-400 words)

## Pathophysiology
Detailed molecular and cellular mechanisms. Genetic factors, receptor biology, signaling \
pathways. Disease progression timeline. Biomarker correlations. Organ-specific \
pathophysiology. Relevant animal/human model findings. (400-450 words)

## Clinical Presentation
Classic presentation with prevalence of each symptom (%). Atypical presentations, \
especially in elderly, diabetics, immunocompromised. Physical examination findings with \
sensitivity/specificity. Red flags requiring immediate action. Symptom severity scoring \
systems (if applicable). (350-400 words)

## Diagnosis
Step-by-step diagnostic algorithm. Laboratory workup: specific tests, reference ranges, \
sensitivity/specificity. Imaging: modality of choice, findings, diagnostic yield. \
Validated scoring systems (Wells score, CURB-65, CHADS-VASc, etc.) with exact point values. \
Differential diagnosis with distinguishing features. Biopsy/procedure criteria if relevant. \
(400-450 words)

## Management and Treatment

### Acute Management
Emergency stabilization, monitoring parameters, immediate interventions.

### First-Line Pharmacotherapy
Drug name (generic/brand), exact dose, route, frequency, duration. \
Mechanism of action. Expected response timeline. Monitoring parameters (levels, labs, ECG). \
Evidence base (trial name, year, NNT/NNH if known).

### Second-Line and Alternative Therapy
When to switch, alternative agents with doses, combination strategies.

### Non-Pharmacological Interventions
Lifestyle modifications with specific targets, dietary recommendations, physical activity \
prescriptions, surgical/procedural indications with criteria.

### Special Populations
- **Pregnancy**: safety category, preferred agents, dose adjustments, monitoring
- **Chronic Kidney Disease**: GFR-based dose adjustments, contraindications
- **Hepatic Impairment**: Child-Pugh adjustments, contraindicated agents
- **Elderly (>65 years)**: dose reductions, Beers criteria considerations, polypharmacy
- **Pediatrics**: weight-based dosing if applicable
(600-700 words total for management section)

## Complications and Prognosis
Major complications with incidence rates (%). Mortality data (30-day, 1-year, 5-year where \
applicable). Prognostic scoring systems with interpretation. Factors associated with poor \
outcome. When to escalate care / refer to specialist. ICU admission criteria. (250-300 words)

## Recent Advances and Emerging Therapies (2020-2024)
New drug approvals, updated guidelines, ongoing clinical trials (NCT numbers if known), \
novel biomarkers, precision medicine approaches, emerging surgical techniques. (200-250 words)

## Patient Education and Counseling
Key messages for patients. Medication adherence strategies. Warning signs requiring \
immediate medical attention. Lifestyle modification targets (specific numbers). \
Follow-up schedule recommendations. (150-200 words)

## Clinical Pearls
List 8-10 board-style teaching points ("- " prefix). Classic associations, common pitfalls, \
must-not-miss diagnoses, USMLE-style mnemonics, high-yield facts with specific values.

ARTICLE_END

CRITICAL RULES:
- Minimum 4500 words — incomplete articles are rejected
- Every drug: include generic name, dose, frequency, route, duration
- Every statistic: include specific percentage or absolute number
- Every guideline: name the organization (AHA, ACC, ESC, WHO, NICE, IDSA)
- No vague language: "commonly used", "often prescribed" — always give specifics
- No references section needed — citations will be added separately"""
