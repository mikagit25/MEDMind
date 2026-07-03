#!/usr/bin/env python3
"""
MedMind AI — Module content generator.

Generates detailed educational module JSON files using Groq / Cerebras / Claude.
Generated files are saved to /opt/medmind/Modules/ and can be imported with:
    python -m app.scripts.import_modules

Usage:
    # List all planned modules
    python generate_modules.py --list

    # Generate all specialty modules (Groq, fast)
    python generate_modules.py --type specialty --model groq

    # Generate disease deep-dive modules (Claude Haiku, best quality)
    python generate_modules.py --type disease --model haiku

    # Single specialty
    python generate_modules.py --type specialty --filter PULM --model cerebras

    # Single module by id
    python generate_modules.py --id PULM-001 --model groq

    # Dry run (just print plan)
    python generate_modules.py --type specialty --dry-run

    # After generation — import to DB
    cd /opt/medmind/backend && python -m app.scripts.import_modules

Model guide:
    groq      — Groq llama-3.3-70b (KEY_3/KEY_4). Fast, free, good quality.
    cerebras  — Cerebras llama3.1-70b (KEY_3/KEY_4). Very fast, free tier.
    haiku     — Claude Haiku (Anthropic). $0.01/call, best medical accuracy.
    sonnet    — Claude Sonnet. Best quality, use for disease deep-dives.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path
from datetime import datetime

# ── Keys ────────────────────────────────────────────────────────────────────
# GROQ_KEY_MODULE — dedicated key for module generation (separate from article pipeline)
GROQ_KEYS = [k for k in [
    os.getenv("GROQ_KEY_MODULE", ""),
    os.getenv("GROQ_KEY_MODULE_2", ""),
] if k]
CEREBRAS_KEYS = [
    os.getenv("CEREBRAS_API_KEY_3", ""),
    os.getenv("CEREBRAS_API_KEY_4", ""),
]
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")

GROQ_MODEL     = "llama-3.3-70b-versatile"
CEREBRAS_MODEL = "llama3.1-70b"
HAIKU_MODEL    = "claude-haiku-4-5-20251001"
SONNET_MODEL   = "claude-sonnet-4-6"

OUTPUT_DIR = Path(os.getenv("MODULES_DIR", "/opt/medmind/Modules"))

DELAY_GROQ     = 65   # GROQ_KEY_MODULE: 12,000 tokens/min → 1 large call/min
DELAY_CEREBRAS = 4
DELAY_HAIKU    = 5
DELAY_SONNET   = 12

# ── Module registry ───────────────────────────────────────────────────────────
# format: {"id", "title_en", "level", "lessons_count", "duration_hours"}

SPECIALTY_MODULES: list[dict] = [
    # ── PULMONOLOGY (missing) ─────────────────────────────────────────────────
    {"id": "PULM-001", "specialty": "Pulmonology", "specialty_ru": "Пульмонология",
     "title_en": "COPD: Diagnosis, Staging (GOLD) and Evidence-Based Management",
     "level": "intermediate", "lessons": 5, "hours": 5},
    {"id": "PULM-002", "specialty": "Pulmonology", "specialty_ru": "Пульмонология",
     "title_en": "Bronchial Asthma: Pathophysiology, GINA Stepwise Approach and Biologics",
     "level": "intermediate", "lessons": 5, "hours": 5},
    {"id": "PULM-003", "specialty": "Pulmonology", "specialty_ru": "Пульмонология",
     "title_en": "Community-Acquired and Hospital-Acquired Pneumonia: Pathogens, CURB-65, Treatment",
     "level": "intermediate", "lessons": 4, "hours": 4},
    {"id": "PULM-004", "specialty": "Pulmonology", "specialty_ru": "Пульмонология",
     "title_en": "Pulmonary Embolism and DVT: CTPA, Risk Stratification and Anticoagulation",
     "level": "advanced", "lessons": 5, "hours": 5},
    {"id": "PULM-005", "specialty": "Pulmonology", "specialty_ru": "Пульмонология",
     "title_en": "ARDS and Mechanical Ventilation: Lung-Protective Strategies",
     "level": "advanced", "lessons": 4, "hours": 5},
    {"id": "PULM-006", "specialty": "Pulmonology", "specialty_ru": "Пульмонология",
     "title_en": "Pulmonary Hypertension: Classification, Diagnosis and Targeted Therapy",
     "level": "advanced", "lessons": 4, "hours": 4},
    {"id": "PULM-007", "specialty": "Pulmonology", "specialty_ru": "Пульмонология",
     "title_en": "Interstitial Lung Diseases: ILD, IPF, Sarcoidosis",
     "level": "advanced", "lessons": 4, "hours": 4},
    {"id": "PULM-008", "specialty": "Pulmonology", "specialty_ru": "Пульмонология",
     "title_en": "Tuberculosis: Epidemiology, Diagnosis and DOTS Treatment",
     "level": "intermediate", "lessons": 4, "hours": 4},
    {"id": "PULM-009", "specialty": "Pulmonology", "specialty_ru": "Пульмонология",
     "title_en": "Obstructive Sleep Apnoea: Pathophysiology, Diagnosis and CPAP",
     "level": "intermediate", "lessons": 3, "hours": 3},
    {"id": "PULM-010", "specialty": "Pulmonology", "specialty_ru": "Пульмонология",
     "title_en": "Pleural Diseases: Pleural Effusion, Pneumothorax, Empyema",
     "level": "intermediate", "lessons": 4, "hours": 4},

    # ── NEPHROLOGY (missing) ──────────────────────────────────────────────────
    {"id": "NEPH-001", "specialty": "Nephrology", "specialty_ru": "Нефрология",
     "title_en": "Chronic Kidney Disease: Staging (KDIGO), Progression and Management",
     "level": "intermediate", "lessons": 5, "hours": 5},
    {"id": "NEPH-002", "specialty": "Nephrology", "specialty_ru": "Нефрология",
     "title_en": "Acute Kidney Injury: KDIGO Criteria, Staging and Management",
     "level": "intermediate", "lessons": 5, "hours": 5},
    {"id": "NEPH-003", "specialty": "Nephrology", "specialty_ru": "Нефрология",
     "title_en": "Glomerulonephritis and Nephrotic Syndrome: Classification and Treatment",
     "level": "advanced", "lessons": 5, "hours": 5},
    {"id": "NEPH-004", "specialty": "Nephrology", "specialty_ru": "Нефрология",
     "title_en": "Renal Replacement Therapy: Haemodialysis, Peritoneal Dialysis, Transplantation",
     "level": "advanced", "lessons": 5, "hours": 6},
    {"id": "NEPH-005", "specialty": "Nephrology", "specialty_ru": "Нефрология",
     "title_en": "Hypertensive Nephropathy and Diabetic Nephropathy",
     "level": "intermediate", "lessons": 4, "hours": 4},
    {"id": "NEPH-006", "specialty": "Nephrology", "specialty_ru": "Нефрология",
     "title_en": "Renal Tubular Disorders: RTA, Fanconi Syndrome, Electrolyte Disorders",
     "level": "advanced", "lessons": 4, "hours": 4},
    {"id": "NEPH-007", "specialty": "Nephrology", "specialty_ru": "Нефрология",
     "title_en": "Polycystic Kidney Disease and Hereditary Nephropathies",
     "level": "advanced", "lessons": 3, "hours": 4},
    {"id": "NEPH-008", "specialty": "Nephrology", "specialty_ru": "Нефрология",
     "title_en": "Nephrolithiasis: Stone Types, Metabolic Workup and Treatment",
     "level": "intermediate", "lessons": 3, "hours": 3},

    # ── GASTROENTEROLOGY (missing) ────────────────────────────────────────────
    {"id": "GASTRO-001", "specialty": "Gastroenterology", "specialty_ru": "Гастроэнтерология",
     "title_en": "GERD and Barrett's Oesophagus: Pathophysiology, Diagnosis and Management",
     "level": "intermediate", "lessons": 4, "hours": 4},
    {"id": "GASTRO-002", "specialty": "Gastroenterology", "specialty_ru": "Гастроэнтерология",
     "title_en": "Peptic Ulcer Disease and H. pylori: Diagnosis, Eradication and Complications",
     "level": "intermediate", "lessons": 4, "hours": 4},
    {"id": "GASTRO-003", "specialty": "Gastroenterology", "specialty_ru": "Гастроэнтерология",
     "title_en": "Inflammatory Bowel Disease: Crohn's Disease and Ulcerative Colitis",
     "level": "advanced", "lessons": 6, "hours": 6},
    {"id": "GASTRO-004", "specialty": "Gastroenterology", "specialty_ru": "Гастроэнтерология",
     "title_en": "Acute and Chronic Pancreatitis: Pathogenesis, Severity and Treatment",
     "level": "intermediate", "lessons": 4, "hours": 5},
    {"id": "GASTRO-005", "specialty": "Gastroenterology", "specialty_ru": "Гастроэнтерология",
     "title_en": "Liver Cirrhosis: Complications — Ascites, Varices, HE, HRS",
     "level": "advanced", "lessons": 6, "hours": 6},
    {"id": "GASTRO-006", "specialty": "Gastroenterology", "specialty_ru": "Гастроэнтерология",
     "title_en": "Viral Hepatitis B and C: Virology, Diagnosis and Antiviral Therapy",
     "level": "intermediate", "lessons": 5, "hours": 5},
    {"id": "GASTRO-007", "specialty": "Gastroenterology", "specialty_ru": "Гастроэнтерология",
     "title_en": "GI Bleeding: Upper and Lower GI Bleed — Endoscopy and Management",
     "level": "advanced", "lessons": 4, "hours": 4},
    {"id": "GASTRO-008", "specialty": "Gastroenterology", "specialty_ru": "Гастроэнтерология",
     "title_en": "Colorectal Cancer: Screening, Diagnosis and Multidisciplinary Treatment",
     "level": "advanced", "lessons": 4, "hours": 5},
    {"id": "GASTRO-009", "specialty": "Gastroenterology", "specialty_ru": "Гастроэнтерология",
     "title_en": "Irritable Bowel Syndrome and Functional GI Disorders",
     "level": "intermediate", "lessons": 3, "hours": 3},
    {"id": "GASTRO-010", "specialty": "Gastroenterology", "specialty_ru": "Гастроэнтерология",
     "title_en": "Cholecystitis, Cholelithiasis and Biliary Tract Disorders",
     "level": "intermediate", "lessons": 4, "hours": 4},

    # ── ENDOCRINOLOGY (missing) ───────────────────────────────────────────────
    {"id": "ENDO-001", "specialty": "Endocrinology", "specialty_ru": "Эндокринология",
     "title_en": "Type 2 Diabetes Mellitus: Pathophysiology, Pharmacotherapy and Targets",
     "level": "intermediate", "lessons": 6, "hours": 6},
    {"id": "ENDO-002", "specialty": "Endocrinology", "specialty_ru": "Эндокринология",
     "title_en": "Type 1 Diabetes Mellitus: Autoimmunity, Insulin Regimens and Complications",
     "level": "intermediate", "lessons": 5, "hours": 5},
    {"id": "ENDO-003", "specialty": "Endocrinology", "specialty_ru": "Эндокринология",
     "title_en": "Diabetic Ketoacidosis and Hyperosmolar State: Emergency Management",
     "level": "advanced", "lessons": 4, "hours": 4},
    {"id": "ENDO-004", "specialty": "Endocrinology", "specialty_ru": "Эндокринология",
     "title_en": "Hypothyroidism and Hyperthyroidism: Diagnosis and Treatment",
     "level": "intermediate", "lessons": 5, "hours": 5},
    {"id": "ENDO-005", "specialty": "Endocrinology", "specialty_ru": "Эндокринология",
     "title_en": "Adrenal Disorders: Cushing's Syndrome, Addison's Disease, Phaeochromocytoma",
     "level": "advanced", "lessons": 5, "hours": 5},
    {"id": "ENDO-006", "specialty": "Endocrinology", "specialty_ru": "Эндокринология",
     "title_en": "Metabolic Syndrome and Obesity: Pathogenesis, GLP-1 and Bariatric Surgery",
     "level": "intermediate", "lessons": 4, "hours": 5},
    {"id": "ENDO-007", "specialty": "Endocrinology", "specialty_ru": "Эндокринология",
     "title_en": "Osteoporosis: Bone Metabolism, FRAX, Bisphosphonates and Novel Agents",
     "level": "intermediate", "lessons": 4, "hours": 4},
    {"id": "ENDO-008", "specialty": "Endocrinology", "specialty_ru": "Эндокринология",
     "title_en": "Pituitary and Hypothalamic Disorders: Acromegaly, Prolactinoma, DI",
     "level": "advanced", "lessons": 4, "hours": 5},

    # ── RHEUMATOLOGY (missing) ────────────────────────────────────────────────
    {"id": "RHEUM-001", "specialty": "Rheumatology", "specialty_ru": "Ревматология",
     "title_en": "Rheumatoid Arthritis: Pathogenesis, ACR/EULAR Criteria, DMARDs, Biologics",
     "level": "intermediate", "lessons": 5, "hours": 5},
    {"id": "RHEUM-002", "specialty": "Rheumatology", "specialty_ru": "Ревматология",
     "title_en": "Systemic Lupus Erythematosus: SLICC Criteria, Organ Manifestations, Treatment",
     "level": "advanced", "lessons": 5, "hours": 6},
    {"id": "RHEUM-003", "specialty": "Rheumatology", "specialty_ru": "Ревматология",
     "title_en": "Crystal Arthropathies: Gout, Pseudogout — Pathogenesis and Management",
     "level": "intermediate", "lessons": 4, "hours": 4},
    {"id": "RHEUM-004", "specialty": "Rheumatology", "specialty_ru": "Ревматология",
     "title_en": "Spondyloarthropathies: Ankylosing Spondylitis, Psoriatic Arthritis, ReA",
     "level": "advanced", "lessons": 4, "hours": 5},
    {"id": "RHEUM-005", "specialty": "Rheumatology", "specialty_ru": "Ревматология",
     "title_en": "Vasculitis: Classification, Giant Cell Arteritis, ANCA-Associated Vasculitis",
     "level": "advanced", "lessons": 4, "hours": 5},
    {"id": "RHEUM-006", "specialty": "Rheumatology", "specialty_ru": "Ревматология",
     "title_en": "Systemic Sclerosis and Myositis: Diagnosis and Organ-Based Management",
     "level": "advanced", "lessons": 4, "hours": 4},
    {"id": "RHEUM-007", "specialty": "Rheumatology", "specialty_ru": "Ревматология",
     "title_en": "Osteoarthritis: Pathogenesis, Imaging and Treatment Ladder",
     "level": "intermediate", "lessons": 3, "hours": 3},

    # ── INFECTIOUS DISEASES (missing) ─────────────────────────────────────────
    {"id": "INFECT-001", "specialty": "Infectious Diseases", "specialty_ru": "Инфекционные болезни",
     "title_en": "Sepsis and Septic Shock: Surviving Sepsis Campaign — Bundles and Vasopressors",
     "level": "advanced", "lessons": 5, "hours": 5},
    {"id": "INFECT-002", "specialty": "Infectious Diseases", "specialty_ru": "Инфекционные болезни",
     "title_en": "HIV/AIDS: Lifecycle, ART Regimens, OIs and Prophylaxis",
     "level": "advanced", "lessons": 6, "hours": 6},
    {"id": "INFECT-003", "specialty": "Infectious Diseases", "specialty_ru": "Инфекционные болезни",
     "title_en": "Tuberculosis: Drug-Sensitive and Drug-Resistant TB — Regimens and Monitoring",
     "level": "intermediate", "lessons": 5, "hours": 5},
    {"id": "INFECT-004", "specialty": "Infectious Diseases", "specialty_ru": "Инфекционные болезни",
     "title_en": "Bacterial Meningitis and Encephalitis: Empiric Therapy and CSF Interpretation",
     "level": "advanced", "lessons": 4, "hours": 4},
    {"id": "INFECT-005", "specialty": "Infectious Diseases", "specialty_ru": "Инфекционные болезни",
     "title_en": "Infective Endocarditis: Duke Criteria, Organisms, Antibiotic Protocols",
     "level": "advanced", "lessons": 4, "hours": 5},
    {"id": "INFECT-006", "specialty": "Infectious Diseases", "specialty_ru": "Инфекционные болезни",
     "title_en": "Antimicrobial Stewardship: PK/PD Principles, Resistance Mechanisms, De-escalation",
     "level": "advanced", "lessons": 5, "hours": 5},
    {"id": "INFECT-007", "specialty": "Infectious Diseases", "specialty_ru": "Инфекционные болезни",
     "title_en": "Malaria, Typhoid and Tropical Infections: Diagnosis and Treatment",
     "level": "intermediate", "lessons": 4, "hours": 4},
    {"id": "INFECT-008", "specialty": "Infectious Diseases", "specialty_ru": "Инфекционные болезни",
     "title_en": "COVID-19 and Respiratory Viral Infections: Pathogenesis and Evidence-Based Treatment",
     "level": "intermediate", "lessons": 4, "hours": 4},

    # ── DERMATOLOGY (partial — existing DERM specialty) ───────────────────────
    {"id": "DERM-001", "specialty": "Dermatology", "specialty_ru": "Дерматология",
     "title_en": "Psoriasis: Pathogenesis, Classification and Biologic Therapy",
     "level": "intermediate", "lessons": 4, "hours": 4},
    {"id": "DERM-002", "specialty": "Dermatology", "specialty_ru": "Дерматология",
     "title_en": "Atopic Dermatitis: Pathophysiology, TH2 Axis and Dupilumab",
     "level": "intermediate", "lessons": 4, "hours": 4},
    {"id": "DERM-003", "specialty": "Dermatology", "specialty_ru": "Дерматология",
     "title_en": "Melanoma and Skin Cancers: Diagnosis, Staging and Immunotherapy",
     "level": "advanced", "lessons": 4, "hours": 5},
    {"id": "DERM-004", "specialty": "Dermatology", "specialty_ru": "Дерматология",
     "title_en": "Acne Vulgaris: Pathogenesis, Topical and Systemic Treatment",
     "level": "intermediate", "lessons": 3, "hours": 3},
    {"id": "DERM-005", "specialty": "Dermatology", "specialty_ru": "Дерматология",
     "title_en": "Bullous Diseases: Pemphigus, Pemphigoid — Autoimmune Blistering",
     "level": "advanced", "lessons": 3, "hours": 4},
    {"id": "DERM-006", "specialty": "Dermatology", "specialty_ru": "Дерматология",
     "title_en": "Skin Infections: Bacterial, Fungal and Viral Dermatoses",
     "level": "intermediate", "lessons": 4, "hours": 4},

    # ── EMERGENCY MEDICINE (missing) ──────────────────────────────────────────
    {"id": "EMERG-001", "specialty": "Emergency Medicine", "specialty_ru": "Скорая и неотложная помощь",
     "title_en": "ACLS and Cardiac Arrest: Resuscitation Algorithms and Post-ROSC Care",
     "level": "advanced", "lessons": 5, "hours": 5},
    {"id": "EMERG-002", "specialty": "Emergency Medicine", "specialty_ru": "Скорая и неотложная помощь",
     "title_en": "Anaphylaxis and Severe Allergic Reactions: Recognition and Management",
     "level": "intermediate", "lessons": 3, "hours": 3},
    {"id": "EMERG-003", "specialty": "Emergency Medicine", "specialty_ru": "Скорая и неотложная помощь",
     "title_en": "Acute Stroke: Window Periods, tPA Protocol and Thrombectomy",
     "level": "advanced", "lessons": 4, "hours": 4},
    {"id": "EMERG-004", "specialty": "Emergency Medicine", "specialty_ru": "Скорая и неотложная помощь",
     "title_en": "Trauma Assessment: ATLS Primary and Secondary Survey",
     "level": "intermediate", "lessons": 5, "hours": 5},
    {"id": "EMERG-005", "specialty": "Emergency Medicine", "specialty_ru": "Скорая и неотложная помощь",
     "title_en": "Toxicology: Common Poisonings, Antidotes and Supportive Care",
     "level": "intermediate", "lessons": 5, "hours": 5},
    {"id": "EMERG-006", "specialty": "Emergency Medicine", "specialty_ru": "Скорая и неотложная помощь",
     "title_en": "Acute Respiratory Failure: Oxygen Therapy, NIV and Emergency Intubation",
     "level": "advanced", "lessons": 4, "hours": 4},

    # ── CRITICAL CARE / ICU (missing) ────────────────────────────────────────
    {"id": "ICU-001", "specialty": "Critical Care", "specialty_ru": "Реаниматология и ИТ",
     "title_en": "Mechanical Ventilation: Modes, Lung-Protective Ventilation, Weaning",
     "level": "advanced", "lessons": 5, "hours": 6},
    {"id": "ICU-002", "specialty": "Critical Care", "specialty_ru": "Реаниматология и ИТ",
     "title_en": "Hemodynamic Monitoring: Arterial Lines, CVP, PA Catheter, Echo-Guided",
     "level": "advanced", "lessons": 4, "hours": 5},
    {"id": "ICU-003", "specialty": "Critical Care", "specialty_ru": "Реаниматология и ИТ",
     "title_en": "Vasopressors and Inotropes: Pharmacology, Targets and Clinical Use",
     "level": "advanced", "lessons": 4, "hours": 4},
    {"id": "ICU-004", "specialty": "Critical Care", "specialty_ru": "Реаниматология и ИТ",
     "title_en": "ICU Nutrition: Enteral vs Parenteral, Caloric Targets, Refeeding Syndrome",
     "level": "intermediate", "lessons": 3, "hours": 3},
    {"id": "ICU-005", "specialty": "Critical Care", "specialty_ru": "Реаниматология и ИТ",
     "title_en": "Sedation and Analgesia in the ICU: ABCDEF Bundle, Delirium Management",
     "level": "advanced", "lessons": 4, "hours": 4},

    # ── HEMATOLOGY (missing) ──────────────────────────────────────────────────
    {"id": "HEMA-001", "specialty": "Hematology", "specialty_ru": "Гематология",
     "title_en": "Anaemia: Pathophysiology, Classification and Differential Diagnosis",
     "level": "intermediate", "lessons": 5, "hours": 5},
    {"id": "HEMA-002", "specialty": "Hematology", "specialty_ru": "Гематология",
     "title_en": "Leukaemia: ALL, AML, CLL, CML — Diagnosis, Cytogenetics and Treatment",
     "level": "advanced", "lessons": 6, "hours": 7},
    {"id": "HEMA-003", "specialty": "Hematology", "specialty_ru": "Гематология",
     "title_en": "Lymphoma: Hodgkin and Non-Hodgkin — Classification and Chemotherapy",
     "level": "advanced", "lessons": 5, "hours": 6},
    {"id": "HEMA-004", "specialty": "Hematology", "specialty_ru": "Гематология",
     "title_en": "Coagulation Disorders: Haemophilia, vWD, DIC — Pathophysiology and Management",
     "level": "advanced", "lessons": 5, "hours": 5},
    {"id": "HEMA-005", "specialty": "Hematology", "specialty_ru": "Гематология",
     "title_en": "Thrombocytopenia: ITP, HIT, TTP — Mechanisms and Treatment",
     "level": "advanced", "lessons": 4, "hours": 4},
    {"id": "HEMA-006", "specialty": "Hematology", "specialty_ru": "Гематология",
     "title_en": "Multiple Myeloma and Plasma Cell Disorders: Diagnosis and Novel Agents",
     "level": "advanced", "lessons": 4, "hours": 5},

    # ── ONCOLOGY ADDITIONS (ONC prefix already exists) ────────────────────────
    {"id": "ONC-001", "specialty": "Oncology", "specialty_ru": "Онкология",
     "title_en": "Breast Cancer: Molecular Subtypes, Staging and Targeted Therapy",
     "level": "advanced", "lessons": 6, "hours": 6},
    {"id": "ONC-002", "specialty": "Oncology", "specialty_ru": "Онкология",
     "title_en": "Lung Cancer: NSCLC vs SCLC, Mutations (EGFR, ALK), Immunotherapy",
     "level": "advanced", "lessons": 6, "hours": 6},
    {"id": "ONC-003", "specialty": "Oncology", "specialty_ru": "Онкология",
     "title_en": "Colorectal Cancer: Screening, RAS/BRAF, Surgery and Systemic Therapy",
     "level": "advanced", "lessons": 5, "hours": 6},
    {"id": "ONC-004", "specialty": "Oncology", "specialty_ru": "Онкология",
     "title_en": "Prostate Cancer: PSA, Gleason, Hormonal Therapy and CRPC Management",
     "level": "advanced", "lessons": 5, "hours": 5},
    {"id": "ONC-005", "specialty": "Oncology", "specialty_ru": "Онкология",
     "title_en": "Oncological Emergencies: Hypercalcaemia, SVC Syndrome, Cord Compression",
     "level": "advanced", "lessons": 4, "hours": 4},
    {"id": "ONC-006", "specialty": "Oncology", "specialty_ru": "Онкология",
     "title_en": "Chemotherapy Principles: Cell Cycle, Classes, Toxicity and Supportive Care",
     "level": "intermediate", "lessons": 5, "hours": 5},
    {"id": "ONC-007", "specialty": "Oncology", "specialty_ru": "Онкология",
     "title_en": "Immunotherapy and Targeted Therapy: Checkpoint Inhibitors, irAEs",
     "level": "advanced", "lessons": 5, "hours": 5},

    # ── OPHTHALMOLOGY (missing) ───────────────────────────────────────────────
    {"id": "OPH-001", "specialty": "Ophthalmology", "specialty_ru": "Офтальмология",
     "title_en": "Glaucoma: Pathophysiology, IOP, Types and Treatment",
     "level": "intermediate", "lessons": 4, "hours": 4},
    {"id": "OPH-002", "specialty": "Ophthalmology", "specialty_ru": "Офтальмология",
     "title_en": "Diabetic Retinopathy and Hypertensive Retinopathy: Screening and Treatment",
     "level": "intermediate", "lessons": 4, "hours": 4},
    {"id": "OPH-003", "specialty": "Ophthalmology", "specialty_ru": "Офтальмология",
     "title_en": "Age-Related Macular Degeneration: Dry vs Wet AMD, Anti-VEGF",
     "level": "intermediate", "lessons": 3, "hours": 3},
    {"id": "OPH-004", "specialty": "Ophthalmology", "specialty_ru": "Офтальмология",
     "title_en": "Cataract and Refractive Errors: Optics and Surgical Correction",
     "level": "intermediate", "lessons": 3, "hours": 3},
    {"id": "OPH-005", "specialty": "Ophthalmology", "specialty_ru": "Офтальмология",
     "title_en": "Uveitis and Ocular Inflammation: Anterior and Posterior Uveitis",
     "level": "advanced", "lessons": 3, "hours": 4},

    # ── ENT / OTORHINOLARYNGOLOGY (missing) ───────────────────────────────────
    {"id": "ENT-001", "specialty": "Otorhinolaryngology", "specialty_ru": "ЛОР-болезни",
     "title_en": "Otitis Media: Acute, Chronic and Complications — Diagnosis and Treatment",
     "level": "intermediate", "lessons": 4, "hours": 4},
    {"id": "ENT-002", "specialty": "Otorhinolaryngology", "specialty_ru": "ЛОР-болезни",
     "title_en": "Rhinosinusitis: Acute and Chronic — Diagnosis, CRS and Surgery Indications",
     "level": "intermediate", "lessons": 3, "hours": 3},
    {"id": "ENT-003", "specialty": "Otorhinolaryngology", "specialty_ru": "ЛОР-болезни",
     "title_en": "Vertigo and Vestibular Disorders: BPPV, Meniere's Disease, Vestibular Neuritis",
     "level": "intermediate", "lessons": 4, "hours": 4},
    {"id": "ENT-004", "specialty": "Otorhinolaryngology", "specialty_ru": "ЛОР-болезни",
     "title_en": "Hearing Loss: Conductive vs Sensorineural — Audiometry and Rehabilitation",
     "level": "intermediate", "lessons": 3, "hours": 3},
    {"id": "ENT-005", "specialty": "Otorhinolaryngology", "specialty_ru": "ЛОР-болезни",
     "title_en": "Head and Neck Cancer: Staging, HPV Role and Multidisciplinary Treatment",
     "level": "advanced", "lessons": 4, "hours": 5},

    # ── ORTHOPEDICS (missing) ─────────────────────────────────────────────────
    {"id": "ORTHO-001", "specialty": "Orthopedics", "specialty_ru": "Ортопедия и травматология",
     "title_en": "Hip and Femur Fractures: Classification, Surgical Management and Rehabilitation",
     "level": "intermediate", "lessons": 4, "hours": 4},
    {"id": "ORTHO-002", "specialty": "Orthopedics", "specialty_ru": "Ортопедия и травматология",
     "title_en": "Spine Disorders: Disc Herniation, Spinal Stenosis, Spondylolisthesis",
     "level": "intermediate", "lessons": 4, "hours": 4},
    {"id": "ORTHO-003", "specialty": "Orthopedics", "specialty_ru": "Ортопедия и травматология",
     "title_en": "Knee Pathology: ACL/Meniscal Injuries, OA, Arthroplasty",
     "level": "intermediate", "lessons": 4, "hours": 4},
    {"id": "ORTHO-004", "specialty": "Orthopedics", "specialty_ru": "Ортопедия и травматология",
     "title_en": "Shoulder and Rotator Cuff: Anatomy, Impingement, Tears and Repair",
     "level": "intermediate", "lessons": 3, "hours": 3},
]

# ── Disease deep-dive modules (comprehensive, 6-8 lessons each) ───────────────
DISEASE_MODULES: list[dict] = [
    {"id": "DISEASE-CAD-001", "specialty": "Cardiology", "specialty_ru": "Кардиология",
     "title_en": "Coronary Artery Disease: Complete Guide from Discovery to Modern Intervention",
     "level": "advanced", "lessons": 8, "hours": 10, "type": "disease"},
    {"id": "DISEASE-HF-001", "specialty": "Cardiology", "specialty_ru": "Кардиология",
     "title_en": "Heart Failure: Pathophysiology, Phenotypes (HFrEF/HFpEF) and Quadruple Therapy",
     "level": "advanced", "lessons": 7, "hours": 8, "type": "disease"},
    {"id": "DISEASE-HTN-001", "specialty": "Internal Medicine", "specialty_ru": "Терапия",
     "title_en": "Arterial Hypertension: History, Mechanisms, Target Organ Damage and Treatment",
     "level": "intermediate", "lessons": 6, "hours": 7, "type": "disease"},
    {"id": "DISEASE-DM2-001", "specialty": "Endocrinology", "specialty_ru": "Эндокринология",
     "title_en": "Type 2 Diabetes: Epidemic, Pathophysiology, Pharmacotherapy and Prevention",
     "level": "intermediate", "lessons": 7, "hours": 8, "type": "disease"},
    {"id": "DISEASE-STROKE-001", "specialty": "Neurology", "specialty_ru": "Неврология",
     "title_en": "Ischaemic Stroke: From Brain Anatomy to Thrombectomy and Neuroprotection",
     "level": "advanced", "lessons": 7, "hours": 8, "type": "disease"},
    {"id": "DISEASE-SEPSIS-001", "specialty": "Critical Care", "specialty_ru": "Реаниматология и ИТ",
     "title_en": "Sepsis: Historical Definitions, Pathophysiology, Biomarkers and Surviving Sepsis 2024",
     "level": "advanced", "lessons": 7, "hours": 8, "type": "disease"},
    {"id": "DISEASE-COPD-001", "specialty": "Pulmonology", "specialty_ru": "Пульмонология",
     "title_en": "COPD: From Emphysema History to Personalized Triple Therapy",
     "level": "advanced", "lessons": 7, "hours": 8, "type": "disease"},
    {"id": "DISEASE-IBD-001", "specialty": "Gastroenterology", "specialty_ru": "Гастроэнтерология",
     "title_en": "Inflammatory Bowel Disease: Discovery, Microbiome, Biologics and Surgical Options",
     "level": "advanced", "lessons": 7, "hours": 8, "type": "disease"},
    {"id": "DISEASE-CKD-001", "specialty": "Nephrology", "specialty_ru": "Нефрология",
     "title_en": "Chronic Kidney Disease: From Glomerular Discovery to SGLT2i and ESRD Prevention",
     "level": "advanced", "lessons": 7, "hours": 8, "type": "disease"},
    {"id": "DISEASE-RA-001", "specialty": "Rheumatology", "specialty_ru": "Ревматология",
     "title_en": "Rheumatoid Arthritis: Autoimmunity Discovery, ACR Criteria, JAK Inhibitors",
     "level": "advanced", "lessons": 6, "hours": 7, "type": "disease"},
    {"id": "DISEASE-HIV-001", "specialty": "Infectious Diseases", "specialty_ru": "Инфекционные болезни",
     "title_en": "HIV/AIDS: Discovery, Retrovirology, ART Revolution and Long-Term Management",
     "level": "advanced", "lessons": 8, "hours": 9, "type": "disease"},
    {"id": "DISEASE-TB-001", "specialty": "Infectious Diseases", "specialty_ru": "Инфекционные болезни",
     "title_en": "Tuberculosis: Koch's Discovery, Pathogenesis, Drug Resistance and Global Control",
     "level": "advanced", "lessons": 7, "hours": 8, "type": "disease"},
    {"id": "DISEASE-BRCA-001", "specialty": "Oncology", "specialty_ru": "Онкология",
     "title_en": "Breast Cancer: Molecular Biology, BRCA Mutations, Targeted Therapy and Survivorship",
     "level": "advanced", "lessons": 8, "hours": 9, "type": "disease"},
    {"id": "DISEASE-LUNGCA-001", "specialty": "Oncology", "specialty_ru": "Онкология",
     "title_en": "Lung Cancer: Smoking Carcinogenesis, Driver Mutations, Immunotherapy Breakthrough",
     "level": "advanced", "lessons": 7, "hours": 8, "type": "disease"},
    {"id": "DISEASE-PD-001", "specialty": "Neurology", "specialty_ru": "Неврология",
     "title_en": "Parkinson's Disease: Lewy Bodies, Dopamine Pathways, L-DOPA and Deep Brain Stimulation",
     "level": "advanced", "lessons": 7, "hours": 8, "type": "disease"},
    {"id": "DISEASE-AD-001", "specialty": "Neurology", "specialty_ru": "Неврология",
     "title_en": "Alzheimer's Disease: Amyloid Hypothesis, Biomarkers, Lecanemab and Future Directions",
     "level": "advanced", "lessons": 7, "hours": 8, "type": "disease"},
    {"id": "DISEASE-SLE-001", "specialty": "Rheumatology", "specialty_ru": "Ревматология",
     "title_en": "Systemic Lupus Erythematosus: Autoimmunity, Organ Manifestations and Belimumab",
     "level": "advanced", "lessons": 7, "hours": 8, "type": "disease"},
    {"id": "DISEASE-CIRRH-001", "specialty": "Gastroenterology", "specialty_ru": "Гастроэнтерология",
     "title_en": "Liver Cirrhosis: Fibrogenesis, Portal Hypertension, Complications and Transplantation",
     "level": "advanced", "lessons": 8, "hours": 9, "type": "disease"},
    {"id": "DISEASE-ANEMIA-001", "specialty": "Hematology", "specialty_ru": "Гематология",
     "title_en": "Iron Deficiency and Anaemia: Discovery of Iron Metabolism, Hepcidin and IV Iron",
     "level": "intermediate", "lessons": 6, "hours": 6, "type": "disease"},
    {"id": "DISEASE-PSORIASIS-001", "specialty": "Dermatology", "specialty_ru": "Дерматология",
     "title_en": "Psoriasis: IL-17/23 Axis, Psoriatic Arthritis, Biologics and Quality of Life",
     "level": "advanced", "lessons": 6, "hours": 7, "type": "disease"},
]

# ── Prompt templates ──────────────────────────────────────────────────────────

SPECIALTY_MODULE_PROMPT = """You are a medical education expert. Generate a complete educational module in JSON format for medical students and physicians.

Module to generate:
- ID: {module_id}
- Title: {title_en}
- Specialty: {specialty}
- Level: {level}
- Number of lessons: {lessons_count}
- Duration: {hours} hours

LESSON STRUCTURE FOR SPECIALTY MODULE:
Each lesson should cover a distinct clinical aspect. Typical lesson plan:
1. Epidemiology & Pathophysiology
2. Clinical Presentation & Diagnosis
3. Investigations & Diagnostic Criteria
4. Treatment & Management
5. Complications, Prognosis & Follow-up
(adjust lesson count and titles to best fit the topic)

OUTPUT: Return ONLY valid JSON (no markdown, no explanation). Schema:
{{
  "meta": {{
    "id": "MODULE_ID",
    "type": "specialty_module",
    "specialty": "{specialty}",
    "specialty_ru": "{specialty_ru}",
    "title_en": "...",
    "order_in_specialty": 1,
    "level": "{level}",
    "duration_hours": {hours},
    "version": "1.0",
    "generated_by": "ai",
    "generated_at": "{date}"
  }},
  "lessons": [
    {{
      "id": "L001",
      "order": 1,
      "title": "Lesson title in English",
      "content": {{
        "intro": "2-3 paragraph introduction to this lesson topic (300-400 words, detailed)",
        "sections": [
          {{
            "heading": "Section heading",
            "text": "Detailed text for this section (400-600 words). Include specific values, doses, criteria, percentages, guidelines (ESC/ACC/AHA/NICE), clinical decision rules, and evidence-based recommendations. Do not be vague."
          }}
        ],
        "clinical_pearl": "A memorable, specific clinical insight — a number, exception, mnemonic, or pitfall that experienced clinicians know (100-150 words)",
        "key_points": [
          "Specific, numbered clinical fact — not vague statements. Include numbers, thresholds, drug names and doses where relevant."
        ],
        "references": [
          {{
            "title": "Guideline/trial title",
            "authors": "Author(s) or society",
            "journal_or_source": "Journal name",
            "year": 2024,
            "type": "guideline",
            "note": "Key finding or recommendation"
          }}
        ]
      }}
    }}
  ]
}}

Requirements:
- Each lesson: exactly 3-4 sections, 6-8 key_points, 2-4 references
- Total word count per lesson: ~1500-2000 words of medical content
- Use ESC/ACC/AHA/WHO/NICE guidelines with years (e.g., "ESC 2023")
- Include specific drug names, doses, thresholds (e.g., "Atorvastatin 40-80mg", "LDL <1.4 mmol/L")
- Reference landmark trials by name (PARADIGM-HF, DAPA-HF, RECOVERY, etc.)
- Content must be clinically accurate and evidence-based
- Do NOT include placeholder text or say "as per guidelines" without specifics
"""

DISEASE_MODULE_PROMPT = """You are a senior medical educator and historian of medicine. Generate a comprehensive disease deep-dive educational module in JSON format.

Disease module to generate:
- ID: {module_id}
- Title: {title_en}
- Specialty: {specialty}
- Level: {level}
- Number of lessons: {lessons_count}
- Duration: {hours} hours

MANDATORY LESSON STRUCTURE FOR DISEASE DEEP-DIVE:
Lesson 1: History of the Disease — Discovery, Historical Cases, Milestones
  - Who first described it and when
  - Evolution of understanding (key historical figures, Nobel prizes, landmark papers)
  - Famous historical cases and their impact
  - How the concept of the disease changed over centuries

Lesson 2: Pathophysiology & Aetiology
  - Molecular mechanisms (cellular, genetic, biochemical)
  - Risk factors and causative agents
  - Disease subtypes and their pathogenic differences

Lesson 3: Clinical Presentation & Symptoms
  - Cardinal symptoms and signs in detail
  - Clinical stages and progression
  - Atypical presentations and special populations

Lesson 4: Diagnosis — Investigations and Criteria
  - Diagnostic criteria (with specific scoring systems and cutoffs)
  - Laboratory tests, imaging, pathology
  - Differential diagnosis

Lesson 5: Treatment — Pharmacological & Non-pharmacological
  - First-line treatments with doses and evidence
  - Second-line and special situation management
  - Surgical/procedural options

Lesson 6: Complications & Prognosis
  - Major complications with incidence data
  - Prognostic scores and survival data
  - Long-term follow-up

Lesson 7: Special Populations & Emerging Therapies
  - Paediatric, elderly, pregnancy considerations
  - Novel treatments and pipeline drugs
  - Future directions in research

Lesson 8 (if applicable): Clinical Cases & Applied Knowledge
  - 2 clinical vignettes with teaching points

OUTPUT: Return ONLY valid JSON (no markdown, no explanation). Same schema as specialty modules but with richer content.

Key requirements:
- Lesson 1 MUST contain real history: specific years, names of scientists/physicians, landmark papers, Nobel prizes if applicable
- Include famous historical patients or outbreaks where relevant
- Cite landmark clinical trials by name with year and key result
- Include the most recent treatment guidelines (2023-2024)
- Each section: 500-700 words of dense, specific medical content
- key_points: 8-10 specific, numbered facts with numbers/thresholds
- Do NOT be vague or generic — every sentence should contain specific clinical information

Schema (same as specialty module):
{{
  "meta": {{
    "id": "{module_id}",
    "type": "disease_module",
    "specialty": "{specialty}",
    "specialty_ru": "{specialty_ru}",
    "title_en": "{title_en}",
    "order_in_specialty": 1,
    "level": "{level}",
    "duration_hours": {hours},
    "version": "1.0",
    "generated_by": "ai",
    "generated_at": "{date}"
  }},
  "lessons": [...]
}}
"""

# ── API call functions ────────────────────────────────────────────────────────

def call_groq(prompt: str, key_idx: int = 0) -> str:
    """Call Groq API (OpenAI-compatible). Returns generated text."""
    try:
        import httpx
    except ImportError:
        raise RuntimeError("pip install httpx")

    key = GROQ_KEYS[key_idx % len(GROQ_KEYS)]
    if not key:
        raise RuntimeError("GROQ_API_KEY_3 or _4 not set")

    resp = httpx.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 32000,
            "response_format": {"type": "json_object"},
        },
        timeout=120.0,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Groq {resp.status_code}: {resp.text[:300]}")
    return resp.json()["choices"][0]["message"]["content"]


def call_cerebras(prompt: str, key_idx: int = 0) -> str:
    """Call Cerebras API (OpenAI-compatible). Returns generated text."""
    try:
        import httpx
    except ImportError:
        raise RuntimeError("pip install httpx")

    key = CEREBRAS_KEYS[key_idx % len(CEREBRAS_KEYS)]
    if not key:
        raise RuntimeError("CEREBRAS_API_KEY_3 or _4 not set")

    resp = httpx.post(
        "https://api.cerebras.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": CEREBRAS_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3,
            "max_tokens": 16000,
        },
        timeout=120.0,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Cerebras {resp.status_code}: {resp.text[:300]}")
    return resp.json()["choices"][0]["message"]["content"]


def call_claude(prompt: str, model: str = HAIKU_MODEL) -> str:
    """Call Anthropic Claude API. Returns generated text."""
    try:
        import httpx
    except ImportError:
        raise RuntimeError("pip install httpx")

    if not ANTHROPIC_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    resp = httpx.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": 16000,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=180.0,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Claude {resp.status_code}: {resp.text[:300]}")
    return resp.json()["content"][0]["text"]


def generate_with_model(prompt: str, model: str, key_idx: int = 0) -> str:
    if model == "groq":
        return call_groq(prompt, key_idx)
    elif model == "cerebras":
        return call_cerebras(prompt, key_idx)
    elif model == "haiku":
        return call_claude(prompt, HAIKU_MODEL)
    elif model == "sonnet":
        return call_claude(prompt, SONNET_MODEL)
    else:
        raise ValueError(f"Unknown model: {model}")


def extract_json(text: str) -> dict:
    """Extract JSON object from text, handling markdown code blocks."""
    text = text.strip()
    # Strip markdown
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text.strip())
    # Find JSON boundaries
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("No JSON object found in response")
    return json.loads(text[start:end])


def generate_module(mod: dict, model: str, key_idx: int = 0,
                    delay_fn=None) -> dict:
    """Generate a single module. Disease modules with >4 lessons are split into
    two calls (first half + second half) and merged to stay within token limits."""
    is_disease = mod.get("type") == "disease"
    template = DISEASE_MODULE_PROMPT if is_disease else SPECIALTY_MODULE_PROMPT
    lessons_count = mod["lessons"]

    # For large disease modules on token-limited APIs, split into two calls
    if is_disease and lessons_count > 4 and model in ("groq", "cerebras"):
        half1 = max(4, lessons_count // 2)
        half2 = lessons_count - half1

        prompt1 = template.format(
            module_id=mod["id"],
            title_en=mod["title_en"],
            specialty=mod["specialty"],
            specialty_ru=mod["specialty_ru"],
            level=mod["level"],
            lessons_count=half1,
            hours=mod["hours"],
            date=datetime.utcnow().strftime("%Y-%m-%d"),
        ) + f"\n\nGenerate ONLY the first {half1} lessons (L001-L00{half1}). Start from Lesson 1: History."

        text1 = generate_with_model(prompt1, model, key_idx)
        data1 = extract_json(text1)

        # Pause between the two halves
        if delay_fn:
            delay_fn()

        prompt2 = template.format(
            module_id=mod["id"],
            title_en=mod["title_en"],
            specialty=mod["specialty"],
            specialty_ru=mod["specialty_ru"],
            level=mod["level"],
            lessons_count=half2,
            hours=mod["hours"],
            date=datetime.utcnow().strftime("%Y-%m-%d"),
        ) + (
            f"\n\nGenerate ONLY lessons L00{half1+1}-L00{lessons_count} "
            f"(the last {half2} lessons). Continue from Lesson {half1+1}: "
            "Treatment. Do NOT repeat earlier lessons."
        )

        text2 = generate_with_model(prompt2, model, key_idx)
        data2 = extract_json(text2)

        # Merge: meta from first call, lessons from both
        merged = data1.copy()
        extra_lessons = data2.get("lessons", [])
        # Renumber extra lessons to continue sequence
        base = len(merged.get("lessons", []))
        for i, lesson in enumerate(extra_lessons):
            lesson["id"] = f"L{base + i + 1:03d}"
            lesson["order"] = base + i + 1
        merged["lessons"] = merged.get("lessons", []) + extra_lessons
        merged["meta"]["duration_hours"] = mod["hours"]
        return merged

    # Single call for specialty modules or small disease modules
    prompt = template.format(
        module_id=mod["id"],
        title_en=mod["title_en"],
        specialty=mod["specialty"],
        specialty_ru=mod["specialty_ru"],
        level=mod["level"],
        lessons_count=lessons_count,
        hours=mod["hours"],
        date=datetime.utcnow().strftime("%Y-%m-%d"),
    )
    text = generate_with_model(prompt, model, key_idx)
    return extract_json(text)


def save_module(data: dict, mod_id: str) -> Path:
    """Save module JSON to Modules/ directory."""
    fname = f"module_{mod_id}.json"
    path = OUTPUT_DIR / fname
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def module_exists(mod_id: str) -> bool:
    """Check if module JSON already exists."""
    return (OUTPUT_DIR / f"module_{mod_id}.json").exists()


# ── Main ──────────────────────────────────────────────────────────────────────

def get_all_modules() -> list[dict]:
    return SPECIALTY_MODULES + DISEASE_MODULES


def main() -> None:
    parser = argparse.ArgumentParser(description="MedMind module content generator")
    parser.add_argument("--type", choices=["specialty", "disease", "all"], default="all",
                        help="Type of modules to generate")
    parser.add_argument("--filter", default="",
                        help="Filter by specialty prefix (e.g. PULM, NEPH, GASTRO)")
    parser.add_argument("--id", default="", help="Generate a single module by ID")
    parser.add_argument("--model", default="groq",
                        choices=["groq", "cerebras", "haiku", "sonnet"],
                        help="AI model to use")
    parser.add_argument("--limit", type=int, default=0, help="Max modules to generate (0=all)")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without generating")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing files")
    parser.add_argument("--list", action="store_true", help="List all planned modules and exit")
    args = parser.parse_args()

    all_mods = get_all_modules()

    # ── --list ────────────────────────────────────────────────────────────────
    if args.list:
        spec_mods = [m for m in all_mods if m.get("type") != "disease"]
        dis_mods  = [m for m in all_mods if m.get("type") == "disease"]
        print(f"\n{'='*60}")
        print(f"SPECIALTY MODULES ({len(spec_mods)} total)")
        print(f"{'='*60}")
        cur_spec = ""
        for m in spec_mods:
            if m["specialty"] != cur_spec:
                cur_spec = m["specialty"]
                print(f"\n  {cur_spec}:")
            ex = " [EXISTS]" if module_exists(m["id"]) else ""
            print(f"    {m['id']:20s}  {m['title_en'][:55]}{ex}")
        print(f"\n{'='*60}")
        print(f"DISEASE DEEP-DIVE MODULES ({len(dis_mods)} total)")
        print(f"{'='*60}")
        for m in dis_mods:
            ex = " [EXISTS]" if module_exists(m["id"]) else ""
            print(f"  {m['id']:25s}  {m['title_en'][:50]}{ex}")
        print(f"\nTotal: {len(all_mods)} modules | "
              f"Existing: {sum(1 for m in all_mods if module_exists(m['id']))} | "
              f"Missing: {sum(1 for m in all_mods if not module_exists(m['id']))}")
        return

    # ── Filter modules ────────────────────────────────────────────────────────
    mods = all_mods
    if args.id:
        mods = [m for m in all_mods if m["id"] == args.id]
        if not mods:
            print(f"Module {args.id!r} not found in registry.")
            sys.exit(1)
    else:
        if args.type == "specialty":
            mods = [m for m in mods if m.get("type") != "disease"]
        elif args.type == "disease":
            mods = [m for m in mods if m.get("type") == "disease"]
        if args.filter:
            prefix = args.filter.upper()
            mods = [m for m in mods if m["id"].startswith(prefix)]
        if not args.overwrite:
            mods = [m for m in mods if not module_exists(m["id"])]
        if args.limit > 0:
            mods = mods[: args.limit]

    if not mods:
        print("Nothing to generate (all already exist, use --overwrite to regenerate).")
        return

    delay = {
        "groq": DELAY_GROQ,
        "cerebras": DELAY_CEREBRAS,
        "haiku": DELAY_HAIKU,
        "sonnet": DELAY_SONNET,
    }[args.model]

    print(f"\nGenerating {len(mods)} modules with model={args.model}")
    print(f"Output dir: {OUTPUT_DIR}")
    print(f"Delay between calls: {delay}s\n")

    if args.dry_run:
        for m in mods:
            print(f"  [DRY] {m['id']:25s}  {m['title_en']}")
        return

    errors = []
    def do_delay():
        print(f"  ⏳ Waiting {delay}s (rate limit)…", flush=True)
        time.sleep(delay)

    for i, mod in enumerate(mods):
        key_idx = i % len(GROQ_KEYS) if args.model == "groq" else i % max(len(CEREBRAS_KEYS), 1)
        is_disease = mod.get("type") == "disease"
        split_note = " (2-part generation)" if is_disease and mod["lessons"] > 4 and args.model in ("groq","cerebras") else ""
        print(f"[{i+1}/{len(mods)}] {mod['id']} — {mod['title_en'][:55]}{split_note}", flush=True)
        try:
            data = generate_module(mod, args.model, key_idx, delay_fn=do_delay)
            path = save_module(data, mod["id"])
            lesson_count = len(data.get("lessons", []))
            print(f"  ✓ Saved {path.name} ({lesson_count} lessons)", flush=True)
        except json.JSONDecodeError as e:
            print(f"  ✗ JSON parse error: {e}", flush=True)
            errors.append((mod["id"], str(e)))
        except Exception as e:
            print(f"  ✗ Error: {e}", flush=True)
            errors.append((mod["id"], str(e)))

        if i < len(mods) - 1:
            do_delay()

    print(f"\nDone. Generated: {len(mods) - len(errors)}, Errors: {len(errors)}")
    if errors:
        print("Errors:")
        for mid, err in errors:
            print(f"  {mid}: {err}")
    print(f"\nNext step: import to DB:")
    print(f"  cd /opt/medmind/backend && python -m app.scripts.import_modules")


if __name__ == "__main__":
    # Load .env from backend dir
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())
    main()
