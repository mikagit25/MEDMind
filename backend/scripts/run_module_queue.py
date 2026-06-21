#!/usr/bin/env python3
"""
MedMind — Autonomous module generation queue (cron-friendly).

Generates all 115 planned modules one by one.
Safe to restart — skips already-generated files (idempotent).

Cron setup (runs every hour, picks up from where it left off):
    crontab -e
    0 * * * * . /opt/medmind/backend/.env.sh && /usr/bin/python3 \
        /opt/medmind/backend/scripts/run_module_queue.py \
        >> /tmp/module_queue.log 2>&1

Or pass key inline:
    GROQ_KEY_MODULE=gsk_... python3 run_module_queue.py
    GROQ_KEY_MODULE=gsk_... python3 run_module_queue.py --type specialty
    GROQ_KEY_MODULE=gsk_... python3 run_module_queue.py --status

Rate limit handling:
    - TPM (tokens/min):  waits exact seconds from error + 10s buffer
    - TPD (tokens/day):  exits immediately with code 0 — cron will retry next run
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path


class TPDLimitError(Exception):
    """Raised when Groq daily token limit is hit — cron will retry next run."""


# ── Config ────────────────────────────────────────────────────────────────────
GROQ_KEY    = os.getenv("GROQ_KEY_MODULE", "")
GROQ_MODEL  = "llama-3.3-70b-versatile"
OUTPUT_DIR  = Path(os.getenv("MODULES_DIR", "/opt/medmind/Modules"))
LOG_FILE    = Path("/tmp/module_queue.log")

# Between successful calls (seconds).
# 12 000 TPM → each module ≈ 8 000-10 000 tokens → 1 call per 65s
INTER_CALL_DELAY = 68

# ── Module registry (all 115) ─────────────────────────────────────────────────
SPECIALTY_MODULES = [
    # PULMONOLOGY
    {"id":"PULM-001","specialty":"Pulmonology","specialty_ru":"Пульмонология","title_en":"COPD: Diagnosis, Staging (GOLD) and Evidence-Based Management","level":"intermediate","lessons":5,"hours":5},
    {"id":"PULM-002","specialty":"Pulmonology","specialty_ru":"Пульмонология","title_en":"Bronchial Asthma: Pathophysiology, GINA Stepwise Approach and Biologics","level":"intermediate","lessons":5,"hours":5},
    {"id":"PULM-003","specialty":"Pulmonology","specialty_ru":"Пульмонология","title_en":"Community-Acquired and Hospital-Acquired Pneumonia: Pathogens, CURB-65, Treatment","level":"intermediate","lessons":4,"hours":4},
    {"id":"PULM-004","specialty":"Pulmonology","specialty_ru":"Пульмонология","title_en":"Pulmonary Embolism and DVT: CTPA, Risk Stratification and Anticoagulation","level":"advanced","lessons":5,"hours":5},
    {"id":"PULM-005","specialty":"Pulmonology","specialty_ru":"Пульмонология","title_en":"ARDS and Mechanical Ventilation: Lung-Protective Strategies","level":"advanced","lessons":4,"hours":5},
    {"id":"PULM-006","specialty":"Pulmonology","specialty_ru":"Пульмонология","title_en":"Pulmonary Hypertension: Classification, Diagnosis and Targeted Therapy","level":"advanced","lessons":4,"hours":4},
    {"id":"PULM-007","specialty":"Pulmonology","specialty_ru":"Пульмонология","title_en":"Interstitial Lung Diseases: ILD, IPF, Sarcoidosis","level":"advanced","lessons":4,"hours":4},
    {"id":"PULM-008","specialty":"Pulmonology","specialty_ru":"Пульмонология","title_en":"Tuberculosis: Epidemiology, Diagnosis and DOTS Treatment","level":"intermediate","lessons":4,"hours":4},
    {"id":"PULM-009","specialty":"Pulmonology","specialty_ru":"Пульмонология","title_en":"Obstructive Sleep Apnoea: Pathophysiology, Diagnosis and CPAP","level":"intermediate","lessons":3,"hours":3},
    {"id":"PULM-010","specialty":"Pulmonology","specialty_ru":"Пульмонология","title_en":"Pleural Diseases: Pleural Effusion, Pneumothorax, Empyema","level":"intermediate","lessons":4,"hours":4},
    # NEPHROLOGY
    {"id":"NEPH-001","specialty":"Nephrology","specialty_ru":"Нефрология","title_en":"Chronic Kidney Disease: Staging (KDIGO), Progression and Management","level":"intermediate","lessons":5,"hours":5},
    {"id":"NEPH-002","specialty":"Nephrology","specialty_ru":"Нефрология","title_en":"Acute Kidney Injury: KDIGO Criteria, Staging and Management","level":"intermediate","lessons":5,"hours":5},
    {"id":"NEPH-003","specialty":"Nephrology","specialty_ru":"Нефрология","title_en":"Glomerulonephritis and Nephrotic Syndrome: Classification and Treatment","level":"advanced","lessons":5,"hours":5},
    {"id":"NEPH-004","specialty":"Nephrology","specialty_ru":"Нефрология","title_en":"Renal Replacement Therapy: Haemodialysis, Peritoneal Dialysis, Transplantation","level":"advanced","lessons":5,"hours":6},
    {"id":"NEPH-005","specialty":"Nephrology","specialty_ru":"Нефрология","title_en":"Hypertensive Nephropathy and Diabetic Nephropathy","level":"intermediate","lessons":4,"hours":4},
    {"id":"NEPH-006","specialty":"Nephrology","specialty_ru":"Нефрология","title_en":"Renal Tubular Disorders: RTA, Fanconi Syndrome, Electrolyte Disorders","level":"advanced","lessons":4,"hours":4},
    {"id":"NEPH-007","specialty":"Nephrology","specialty_ru":"Нефрология","title_en":"Polycystic Kidney Disease and Hereditary Nephropathies","level":"advanced","lessons":3,"hours":4},
    {"id":"NEPH-008","specialty":"Nephrology","specialty_ru":"Нефрология","title_en":"Nephrolithiasis: Stone Types, Metabolic Workup and Treatment","level":"intermediate","lessons":3,"hours":3},
    # GASTROENTEROLOGY
    {"id":"GASTRO-001","specialty":"Gastroenterology","specialty_ru":"Гастроэнтерология","title_en":"GERD and Barrett's Oesophagus: Pathophysiology, Diagnosis and Management","level":"intermediate","lessons":4,"hours":4},
    {"id":"GASTRO-002","specialty":"Gastroenterology","specialty_ru":"Гастроэнтерология","title_en":"Peptic Ulcer Disease and H. pylori: Diagnosis, Eradication and Complications","level":"intermediate","lessons":4,"hours":4},
    {"id":"GASTRO-003","specialty":"Gastroenterology","specialty_ru":"Гастроэнтерология","title_en":"Inflammatory Bowel Disease: Crohn's Disease and Ulcerative Colitis","level":"advanced","lessons":6,"hours":6},
    {"id":"GASTRO-004","specialty":"Gastroenterology","specialty_ru":"Гастроэнтерология","title_en":"Acute and Chronic Pancreatitis: Pathogenesis, Severity and Treatment","level":"intermediate","lessons":4,"hours":5},
    {"id":"GASTRO-005","specialty":"Gastroenterology","specialty_ru":"Гастроэнтерология","title_en":"Liver Cirrhosis: Complications — Ascites, Varices, HE, HRS","level":"advanced","lessons":6,"hours":6},
    {"id":"GASTRO-006","specialty":"Gastroenterology","specialty_ru":"Гастроэнтерология","title_en":"Viral Hepatitis B and C: Virology, Diagnosis and Antiviral Therapy","level":"intermediate","lessons":5,"hours":5},
    {"id":"GASTRO-007","specialty":"Gastroenterology","specialty_ru":"Гастроэнтерология","title_en":"GI Bleeding: Upper and Lower GI Bleed — Endoscopy and Management","level":"advanced","lessons":4,"hours":4},
    {"id":"GASTRO-008","specialty":"Gastroenterology","specialty_ru":"Гастроэнтерология","title_en":"Colorectal Cancer: Screening, Diagnosis and Multidisciplinary Treatment","level":"advanced","lessons":4,"hours":5},
    {"id":"GASTRO-009","specialty":"Gastroenterology","specialty_ru":"Гастроэнтерология","title_en":"Irritable Bowel Syndrome and Functional GI Disorders","level":"intermediate","lessons":3,"hours":3},
    {"id":"GASTRO-010","specialty":"Gastroenterology","specialty_ru":"Гастроэнтерология","title_en":"Cholecystitis, Cholelithiasis and Biliary Tract Disorders","level":"intermediate","lessons":4,"hours":4},
    # ENDOCRINOLOGY
    {"id":"ENDO-001","specialty":"Endocrinology","specialty_ru":"Эндокринология","title_en":"Type 2 Diabetes Mellitus: Pathophysiology, Pharmacotherapy and Targets","level":"intermediate","lessons":6,"hours":6},
    {"id":"ENDO-002","specialty":"Endocrinology","specialty_ru":"Эндокринология","title_en":"Type 1 Diabetes Mellitus: Autoimmunity, Insulin Regimens and Complications","level":"intermediate","lessons":5,"hours":5},
    {"id":"ENDO-003","specialty":"Endocrinology","specialty_ru":"Эндокринология","title_en":"Diabetic Ketoacidosis and Hyperosmolar State: Emergency Management","level":"advanced","lessons":4,"hours":4},
    {"id":"ENDO-004","specialty":"Endocrinology","specialty_ru":"Эндокринология","title_en":"Hypothyroidism and Hyperthyroidism: Diagnosis and Treatment","level":"intermediate","lessons":5,"hours":5},
    {"id":"ENDO-005","specialty":"Endocrinology","specialty_ru":"Эндокринология","title_en":"Adrenal Disorders: Cushing's Syndrome, Addison's Disease, Phaeochromocytoma","level":"advanced","lessons":5,"hours":5},
    {"id":"ENDO-006","specialty":"Endocrinology","specialty_ru":"Эндокринология","title_en":"Metabolic Syndrome and Obesity: Pathogenesis, GLP-1 and Bariatric Surgery","level":"intermediate","lessons":4,"hours":5},
    {"id":"ENDO-007","specialty":"Endocrinology","specialty_ru":"Эндокринология","title_en":"Osteoporosis: Bone Metabolism, FRAX, Bisphosphonates and Novel Agents","level":"intermediate","lessons":4,"hours":4},
    {"id":"ENDO-008","specialty":"Endocrinology","specialty_ru":"Эндокринология","title_en":"Pituitary and Hypothalamic Disorders: Acromegaly, Prolactinoma, DI","level":"advanced","lessons":4,"hours":5},
    # RHEUMATOLOGY
    {"id":"RHEUM-001","specialty":"Rheumatology","specialty_ru":"Ревматология","title_en":"Rheumatoid Arthritis: Pathogenesis, ACR/EULAR Criteria, DMARDs, Biologics","level":"intermediate","lessons":5,"hours":5},
    {"id":"RHEUM-002","specialty":"Rheumatology","specialty_ru":"Ревматология","title_en":"Systemic Lupus Erythematosus: SLICC Criteria, Organ Manifestations, Treatment","level":"advanced","lessons":5,"hours":6},
    {"id":"RHEUM-003","specialty":"Rheumatology","specialty_ru":"Ревматология","title_en":"Crystal Arthropathies: Gout, Pseudogout — Pathogenesis and Management","level":"intermediate","lessons":4,"hours":4},
    {"id":"RHEUM-004","specialty":"Rheumatology","specialty_ru":"Ревматология","title_en":"Spondyloarthropathies: Ankylosing Spondylitis, Psoriatic Arthritis, ReA","level":"advanced","lessons":4,"hours":5},
    {"id":"RHEUM-005","specialty":"Rheumatology","specialty_ru":"Ревматология","title_en":"Vasculitis: Classification, Giant Cell Arteritis, ANCA-Associated Vasculitis","level":"advanced","lessons":4,"hours":5},
    {"id":"RHEUM-006","specialty":"Rheumatology","specialty_ru":"Ревматология","title_en":"Systemic Sclerosis and Myositis: Diagnosis and Organ-Based Management","level":"advanced","lessons":4,"hours":4},
    {"id":"RHEUM-007","specialty":"Rheumatology","specialty_ru":"Ревматология","title_en":"Osteoarthritis: Pathogenesis, Imaging and Treatment Ladder","level":"intermediate","lessons":3,"hours":3},
    # INFECTIOUS DISEASES
    {"id":"INFECT-001","specialty":"Infectious Diseases","specialty_ru":"Инфекционные болезни","title_en":"Sepsis and Septic Shock: Surviving Sepsis Campaign — Bundles and Vasopressors","level":"advanced","lessons":5,"hours":5},
    {"id":"INFECT-002","specialty":"Infectious Diseases","specialty_ru":"Инфекционные болезни","title_en":"HIV/AIDS: Lifecycle, ART Regimens, OIs and Prophylaxis","level":"advanced","lessons":6,"hours":6},
    {"id":"INFECT-003","specialty":"Infectious Diseases","specialty_ru":"Инфекционные болезни","title_en":"Tuberculosis: Drug-Sensitive and Drug-Resistant TB — Regimens and Monitoring","level":"intermediate","lessons":5,"hours":5},
    {"id":"INFECT-004","specialty":"Infectious Diseases","specialty_ru":"Инфекционные болезни","title_en":"Bacterial Meningitis and Encephalitis: Empiric Therapy and CSF Interpretation","level":"advanced","lessons":4,"hours":4},
    {"id":"INFECT-005","specialty":"Infectious Diseases","specialty_ru":"Инфекционные болезни","title_en":"Infective Endocarditis: Duke Criteria, Organisms, Antibiotic Protocols","level":"advanced","lessons":4,"hours":5},
    {"id":"INFECT-006","specialty":"Infectious Diseases","specialty_ru":"Инфекционные болезни","title_en":"Antimicrobial Stewardship: PK/PD Principles, Resistance Mechanisms, De-escalation","level":"advanced","lessons":5,"hours":5},
    {"id":"INFECT-007","specialty":"Infectious Diseases","specialty_ru":"Инфекционные болезни","title_en":"Malaria, Typhoid and Tropical Infections: Diagnosis and Treatment","level":"intermediate","lessons":4,"hours":4},
    {"id":"INFECT-008","specialty":"Infectious Diseases","specialty_ru":"Инфекционные болезни","title_en":"COVID-19 and Respiratory Viral Infections: Pathogenesis and Evidence-Based Treatment","level":"intermediate","lessons":4,"hours":4},
    # DERMATOLOGY
    {"id":"DERM-001","specialty":"Dermatology","specialty_ru":"Дерматология","title_en":"Psoriasis: Pathogenesis, Classification and Biologic Therapy","level":"intermediate","lessons":4,"hours":4},
    {"id":"DERM-002","specialty":"Dermatology","specialty_ru":"Дерматология","title_en":"Atopic Dermatitis: Pathophysiology, TH2 Axis and Dupilumab","level":"intermediate","lessons":4,"hours":4},
    {"id":"DERM-003","specialty":"Dermatology","specialty_ru":"Дерматология","title_en":"Melanoma and Skin Cancers: Diagnosis, Staging and Immunotherapy","level":"advanced","lessons":4,"hours":5},
    {"id":"DERM-004","specialty":"Dermatology","specialty_ru":"Дерматология","title_en":"Acne Vulgaris: Pathogenesis, Topical and Systemic Treatment","level":"intermediate","lessons":3,"hours":3},
    {"id":"DERM-005","specialty":"Dermatology","specialty_ru":"Дерматология","title_en":"Bullous Diseases: Pemphigus, Pemphigoid — Autoimmune Blistering","level":"advanced","lessons":3,"hours":4},
    {"id":"DERM-006","specialty":"Dermatology","specialty_ru":"Дерматология","title_en":"Skin Infections: Bacterial, Fungal and Viral Dermatoses","level":"intermediate","lessons":4,"hours":4},
    # EMERGENCY MEDICINE
    {"id":"EMERG-001","specialty":"Emergency Medicine","specialty_ru":"Скорая и неотложная помощь","title_en":"ACLS and Cardiac Arrest: Resuscitation Algorithms and Post-ROSC Care","level":"advanced","lessons":5,"hours":5},
    {"id":"EMERG-002","specialty":"Emergency Medicine","specialty_ru":"Скорая и неотложная помощь","title_en":"Anaphylaxis and Severe Allergic Reactions: Recognition and Management","level":"intermediate","lessons":3,"hours":3},
    {"id":"EMERG-003","specialty":"Emergency Medicine","specialty_ru":"Скорая и неотложная помощь","title_en":"Acute Stroke: Window Periods, tPA Protocol and Thrombectomy","level":"advanced","lessons":4,"hours":4},
    {"id":"EMERG-004","specialty":"Emergency Medicine","specialty_ru":"Скорая и неотложная помощь","title_en":"Trauma Assessment: ATLS Primary and Secondary Survey","level":"intermediate","lessons":5,"hours":5},
    {"id":"EMERG-005","specialty":"Emergency Medicine","specialty_ru":"Скорая и неотложная помощь","title_en":"Toxicology: Common Poisonings, Antidotes and Supportive Care","level":"intermediate","lessons":5,"hours":5},
    {"id":"EMERG-006","specialty":"Emergency Medicine","specialty_ru":"Скорая и неотложная помощь","title_en":"Acute Respiratory Failure: Oxygen Therapy, NIV and Emergency Intubation","level":"advanced","lessons":4,"hours":4},
    # CRITICAL CARE
    {"id":"ICU-001","specialty":"Critical Care","specialty_ru":"Реаниматология и ИТ","title_en":"Mechanical Ventilation: Modes, Lung-Protective Ventilation, Weaning","level":"advanced","lessons":5,"hours":6},
    {"id":"ICU-002","specialty":"Critical Care","specialty_ru":"Реаниматология и ИТ","title_en":"Hemodynamic Monitoring: Arterial Lines, CVP, PA Catheter, Echo-Guided","level":"advanced","lessons":4,"hours":5},
    {"id":"ICU-003","specialty":"Critical Care","specialty_ru":"Реаниматология и ИТ","title_en":"Vasopressors and Inotropes: Pharmacology, Targets and Clinical Use","level":"advanced","lessons":4,"hours":4},
    {"id":"ICU-004","specialty":"Critical Care","specialty_ru":"Реаниматология и ИТ","title_en":"ICU Nutrition: Enteral vs Parenteral, Caloric Targets, Refeeding Syndrome","level":"intermediate","lessons":3,"hours":3},
    {"id":"ICU-005","specialty":"Critical Care","specialty_ru":"Реаниматология и ИТ","title_en":"Sedation and Analgesia in the ICU: ABCDEF Bundle, Delirium Management","level":"advanced","lessons":4,"hours":4},
    # HEMATOLOGY
    {"id":"HEMA-001","specialty":"Hematology","specialty_ru":"Гематология","title_en":"Anaemia: Pathophysiology, Classification and Differential Diagnosis","level":"intermediate","lessons":5,"hours":5},
    {"id":"HEMA-002","specialty":"Hematology","specialty_ru":"Гематология","title_en":"Leukaemia: ALL, AML, CLL, CML — Diagnosis, Cytogenetics and Treatment","level":"advanced","lessons":6,"hours":7},
    {"id":"HEMA-003","specialty":"Hematology","specialty_ru":"Гематология","title_en":"Lymphoma: Hodgkin and Non-Hodgkin — Classification and Chemotherapy","level":"advanced","lessons":5,"hours":6},
    {"id":"HEMA-004","specialty":"Hematology","specialty_ru":"Гематология","title_en":"Coagulation Disorders: Haemophilia, vWD, DIC — Pathophysiology and Management","level":"advanced","lessons":5,"hours":5},
    {"id":"HEMA-005","specialty":"Hematology","specialty_ru":"Гематология","title_en":"Thrombocytopenia: ITP, HIT, TTP — Mechanisms and Treatment","level":"advanced","lessons":4,"hours":4},
    {"id":"HEMA-006","specialty":"Hematology","specialty_ru":"Гематология","title_en":"Multiple Myeloma and Plasma Cell Disorders: Diagnosis and Novel Agents","level":"advanced","lessons":4,"hours":5},
    # ONCOLOGY
    {"id":"ONC-001","specialty":"Oncology","specialty_ru":"Онкология","title_en":"Breast Cancer: Molecular Subtypes, Staging and Targeted Therapy","level":"advanced","lessons":6,"hours":6},
    {"id":"ONC-002","specialty":"Oncology","specialty_ru":"Онкология","title_en":"Lung Cancer: NSCLC vs SCLC, Mutations (EGFR, ALK), Immunotherapy","level":"advanced","lessons":6,"hours":6},
    {"id":"ONC-003","specialty":"Oncology","specialty_ru":"Онкология","title_en":"Colorectal Cancer: Screening, RAS/BRAF, Surgery and Systemic Therapy","level":"advanced","lessons":5,"hours":6},
    {"id":"ONC-004","specialty":"Oncology","specialty_ru":"Онкология","title_en":"Prostate Cancer: PSA, Gleason, Hormonal Therapy and CRPC Management","level":"advanced","lessons":5,"hours":5},
    {"id":"ONC-005","specialty":"Oncology","specialty_ru":"Онкология","title_en":"Oncological Emergencies: Hypercalcaemia, SVC Syndrome, Cord Compression","level":"advanced","lessons":4,"hours":4},
    {"id":"ONC-006","specialty":"Oncology","specialty_ru":"Онкология","title_en":"Chemotherapy Principles: Cell Cycle, Classes, Toxicity and Supportive Care","level":"intermediate","lessons":5,"hours":5},
    {"id":"ONC-007","specialty":"Oncology","specialty_ru":"Онкология","title_en":"Immunotherapy and Targeted Therapy: Checkpoint Inhibitors, irAEs","level":"advanced","lessons":5,"hours":5},
    # OPHTHALMOLOGY
    {"id":"OPH-001","specialty":"Ophthalmology","specialty_ru":"Офтальмология","title_en":"Glaucoma: Pathophysiology, IOP, Types and Treatment","level":"intermediate","lessons":4,"hours":4},
    {"id":"OPH-002","specialty":"Ophthalmology","specialty_ru":"Офтальмология","title_en":"Diabetic Retinopathy and Hypertensive Retinopathy: Screening and Treatment","level":"intermediate","lessons":4,"hours":4},
    {"id":"OPH-003","specialty":"Ophthalmology","specialty_ru":"Офтальмология","title_en":"Age-Related Macular Degeneration: Dry vs Wet AMD, Anti-VEGF","level":"intermediate","lessons":3,"hours":3},
    {"id":"OPH-004","specialty":"Ophthalmology","specialty_ru":"Офтальмология","title_en":"Cataract and Refractive Errors: Optics and Surgical Correction","level":"intermediate","lessons":3,"hours":3},
    {"id":"OPH-005","specialty":"Ophthalmology","specialty_ru":"Офтальмология","title_en":"Uveitis and Ocular Inflammation: Anterior and Posterior Uveitis","level":"advanced","lessons":3,"hours":4},
    # ENT
    {"id":"ENT-001","specialty":"Otorhinolaryngology","specialty_ru":"ЛОР-болезни","title_en":"Otitis Media: Acute, Chronic and Complications — Diagnosis and Treatment","level":"intermediate","lessons":4,"hours":4},
    {"id":"ENT-002","specialty":"Otorhinolaryngology","specialty_ru":"ЛОР-болезни","title_en":"Rhinosinusitis: Acute and Chronic — Diagnosis, CRS and Surgery Indications","level":"intermediate","lessons":3,"hours":3},
    {"id":"ENT-003","specialty":"Otorhinolaryngology","specialty_ru":"ЛОР-болезни","title_en":"Vertigo and Vestibular Disorders: BPPV, Meniere's Disease, Vestibular Neuritis","level":"intermediate","lessons":4,"hours":4},
    {"id":"ENT-004","specialty":"Otorhinolaryngology","specialty_ru":"ЛОР-болезни","title_en":"Hearing Loss: Conductive vs Sensorineural — Audiometry and Rehabilitation","level":"intermediate","lessons":3,"hours":3},
    {"id":"ENT-005","specialty":"Otorhinolaryngology","specialty_ru":"ЛОР-болезни","title_en":"Head and Neck Cancer: Staging, HPV Role and Multidisciplinary Treatment","level":"advanced","lessons":4,"hours":5},
    # ORTHOPEDICS
    {"id":"ORTHO-001","specialty":"Orthopedics","specialty_ru":"Ортопедия и травматология","title_en":"Hip and Femur Fractures: Classification, Surgical Management and Rehabilitation","level":"intermediate","lessons":4,"hours":4},
    {"id":"ORTHO-002","specialty":"Orthopedics","specialty_ru":"Ортопедия и травматология","title_en":"Spine Disorders: Disc Herniation, Spinal Stenosis, Spondylolisthesis","level":"intermediate","lessons":4,"hours":4},
    {"id":"ORTHO-003","specialty":"Orthopedics","specialty_ru":"Ортопедия и травматология","title_en":"Knee Pathology: ACL/Meniscal Injuries, OA, Arthroplasty","level":"intermediate","lessons":4,"hours":4},
    {"id":"ORTHO-004","specialty":"Orthopedics","specialty_ru":"Ортопедия и травматология","title_en":"Shoulder and Rotator Cuff: Anatomy, Impingement, Tears and Repair","level":"intermediate","lessons":3,"hours":3},
    # CARDIOLOGY
    {"id":"CARD-001","specialty":"Cardiology","specialty_ru":"Кардиология","title_en":"Acute Coronary Syndromes: STEMI, NSTEMI — Reperfusion, DAPT and Post-MI Care","level":"advanced","lessons":6,"hours":6},
    {"id":"CARD-002","specialty":"Cardiology","specialty_ru":"Кардиология","title_en":"Heart Failure: GDMT — ARNI, Beta-blockers, MRA, SGLT2i and Device Therapy","level":"advanced","lessons":6,"hours":6},
    {"id":"CARD-003","specialty":"Cardiology","specialty_ru":"Кардиология","title_en":"Atrial Fibrillation: Classification, Rate/Rhythm Control and Stroke Prevention","level":"intermediate","lessons":5,"hours":5},
    {"id":"CARD-004","specialty":"Cardiology","specialty_ru":"Кардиология","title_en":"Valvular Heart Disease: Aortic Stenosis, Mitral Regurgitation and TAVI/MitraClip","level":"advanced","lessons":5,"hours":5},
    {"id":"CARD-005","specialty":"Cardiology","specialty_ru":"Кардиология","title_en":"Cardiac Arrhythmias: SVT, VT, WPW — ECG Interpretation and Ablation","level":"advanced","lessons":5,"hours":5},
    {"id":"CARD-006","specialty":"Cardiology","specialty_ru":"Кардиология","title_en":"Cardiomyopathies: DCM, HCM, Restrictive — Genetics, Imaging and Management","level":"advanced","lessons":5,"hours":5},
    {"id":"CARD-007","specialty":"Cardiology","specialty_ru":"Кардиология","title_en":"Pericardial and Myocardial Diseases: Pericarditis, Myocarditis, Tamponade","level":"intermediate","lessons":4,"hours":4},
    {"id":"CARD-008","specialty":"Cardiology","specialty_ru":"Кардиология","title_en":"Dyslipidaemia: LDL Biology, Statins, Ezetimibe, PCSK9 Inhibitors and Risk Targets","level":"intermediate","lessons":4,"hours":4},
    {"id":"CARD-009","specialty":"Cardiology","specialty_ru":"Кардиология","title_en":"Cardiovascular Prevention: Risk Scores (SCORE2), Lifestyle and Secondary Prevention","level":"intermediate","lessons":4,"hours":4},
    {"id":"CARD-010","specialty":"Cardiology","specialty_ru":"Кардиология","title_en":"Cardiac Imaging: ECG Mastery, Echocardiography and CT Coronary Angiography","level":"advanced","lessons":5,"hours":5},
    # NEUROLOGY
    {"id":"NEUR-001","specialty":"Neurology","specialty_ru":"Неврология","title_en":"Ischaemic Stroke: Penumbra, tPA, Mechanical Thrombectomy and Secondary Prevention","level":"advanced","lessons":6,"hours":6},
    {"id":"NEUR-002","specialty":"Neurology","specialty_ru":"Неврология","title_en":"Epilepsy: Seizure Classification, AED Selection and Status Epilepticus Management","level":"advanced","lessons":5,"hours":5},
    {"id":"NEUR-003","specialty":"Neurology","specialty_ru":"Неврология","title_en":"Multiple Sclerosis: Demyelination, McDonald Criteria, DMTs and Monitoring","level":"advanced","lessons":5,"hours":6},
    {"id":"NEUR-004","specialty":"Neurology","specialty_ru":"Неврология","title_en":"Headache Disorders: Migraine Pathophysiology, Triptans, CGRP Inhibitors and Cluster HA","level":"intermediate","lessons":4,"hours":4},
    {"id":"NEUR-005","specialty":"Neurology","specialty_ru":"Неврология","title_en":"Peripheral Neuropathies: Diabetic PN, Guillain-Barré Syndrome, CIDP — EMG and Treatment","level":"advanced","lessons":5,"hours":5},
    {"id":"NEUR-006","specialty":"Neurology","specialty_ru":"Неврология","title_en":"CNS Infections: Bacterial Meningitis, Viral Encephalitis, TB Meningitis — Empiric Therapy","level":"advanced","lessons":5,"hours":5},
    {"id":"NEUR-007","specialty":"Neurology","specialty_ru":"Неврология","title_en":"Dementia: Alzheimer's, Vascular and Lewy Body — Biomarkers, Lecanemab and Care","level":"advanced","lessons":5,"hours":5},
    {"id":"NEUR-008","specialty":"Neurology","specialty_ru":"Неврология","title_en":"Neuromuscular Diseases: Myasthenia Gravis, ALS, Muscular Dystrophies","level":"advanced","lessons":5,"hours":5},
    {"id":"NEUR-009","specialty":"Neurology","specialty_ru":"Неврология","title_en":"Movement Disorders: Parkinson's Pathways, L-DOPA, DBS and Essential Tremor","level":"advanced","lessons":5,"hours":5},
    {"id":"NEUR-010","specialty":"Neurology","specialty_ru":"Неврология","title_en":"Raised ICP and Space-Occupying Lesions: Herniation, Brain Tumours and Management","level":"advanced","lessons":4,"hours":4},
    # SURGERY
    {"id":"SURG-001","specialty":"Surgery","specialty_ru":"Хирургия","title_en":"Acute Abdomen: Appendicitis, Peritonitis, Bowel Obstruction — Surgical Decision-Making","level":"advanced","lessons":5,"hours":5},
    {"id":"SURG-002","specialty":"Surgery","specialty_ru":"Хирургия","title_en":"Colorectal Surgery: Colectomy, Anastomosis Techniques, Stoma Formation and Care","level":"advanced","lessons":5,"hours":5},
    {"id":"SURG-003","specialty":"Surgery","specialty_ru":"Хирургия","title_en":"Hepatobiliary Surgery: Cholecystectomy, Liver Resection and Whipple Procedure","level":"advanced","lessons":5,"hours":5},
    {"id":"SURG-004","specialty":"Surgery","specialty_ru":"Хирургия","title_en":"Upper GI Surgery: Oesophagectomy, Gastrectomy and Bariatric Surgery Principles","level":"advanced","lessons":5,"hours":5},
    {"id":"SURG-005","specialty":"Surgery","specialty_ru":"Хирургия","title_en":"Breast Surgery: Mastectomy, Sentinel Node Biopsy and Oncoplastic Reconstruction","level":"intermediate","lessons":4,"hours":4},
    {"id":"SURG-006","specialty":"Surgery","specialty_ru":"Хирургия","title_en":"Endocrine Surgery: Thyroidectomy, Parathyroidectomy and Adrenalectomy","level":"advanced","lessons":4,"hours":4},
    {"id":"SURG-007","specialty":"Surgery","specialty_ru":"Хирургия","title_en":"Hernia Surgery: Inguinal, Incisional, Paraumbilical — Open vs Laparoscopic Repair","level":"intermediate","lessons":4,"hours":4},
    {"id":"SURG-008","specialty":"Surgery","specialty_ru":"Хирургия","title_en":"Vascular Surgery: PAD, Carotid Endarterectomy, AAA and Endovascular Repair","level":"advanced","lessons":5,"hours":5},
    {"id":"SURG-009","specialty":"Surgery","specialty_ru":"Хирургия","title_en":"Perioperative Medicine: Preoperative Assessment, Risk Stratification and Post-op Complications","level":"intermediate","lessons":5,"hours":5},
    {"id":"SURG-010","specialty":"Surgery","specialty_ru":"Хирургия","title_en":"Trauma Surgery: ATLS Principles, Damage Control, Orthopaedic Emergencies","level":"advanced","lessons":5,"hours":5},
    # PAEDIATRICS
    {"id":"PAED-001","specialty":"Pediatrics","specialty_ru":"Педиатрия","title_en":"Neonatal Medicine: Assessment, Respiratory Distress Syndrome, Neonatal Jaundice","level":"intermediate","lessons":5,"hours":5},
    {"id":"PAED-002","specialty":"Pediatrics","specialty_ru":"Педиатрия","title_en":"Paediatric Respiratory Infections: Bronchiolitis, Croup, Pneumonia and Wheezing","level":"intermediate","lessons":4,"hours":4},
    {"id":"PAED-003","specialty":"Pediatrics","specialty_ru":"Педиатрия","title_en":"Febrile Child: Differential Diagnosis, Meningitis Red Flags and Antibiotic Choice","level":"advanced","lessons":4,"hours":4},
    {"id":"PAED-004","specialty":"Pediatrics","specialty_ru":"Педиатрия","title_en":"Congenital Heart Disease: VSD, ASD, ToF — Classification and Surgical Repair","level":"advanced","lessons":5,"hours":5},
    {"id":"PAED-005","specialty":"Pediatrics","specialty_ru":"Педиатрия","title_en":"Paediatric Endocrinology: Type 1 DM, Growth Disorders, Congenital Hypothyroidism","level":"intermediate","lessons":4,"hours":4},
    {"id":"PAED-006","specialty":"Pediatrics","specialty_ru":"Педиатрия","title_en":"Childhood Haematology-Oncology: ALL, Sickle Cell Disease, Thalassaemia","level":"advanced","lessons":5,"hours":5},
    {"id":"PAED-007","specialty":"Pediatrics","specialty_ru":"Педиатрия","title_en":"Neurodevelopmental Disorders: ADHD, Autism Spectrum Disorder, Learning Disabilities","level":"intermediate","lessons":4,"hours":4},
    {"id":"PAED-008","specialty":"Pediatrics","specialty_ru":"Педиатрия","title_en":"Paediatric Emergencies: Anaphylaxis, Status Epilepticus and DKA in Children","level":"advanced","lessons":4,"hours":4},
    # OBSTETRICS & GYNAECOLOGY
    {"id":"OBG-001","specialty":"Obstetrics","specialty_ru":"Акушерство и гинекология","title_en":"Normal Pregnancy: Antenatal Care, Physiological Changes and Screening","level":"intermediate","lessons":5,"hours":5},
    {"id":"OBG-002","specialty":"Obstetrics","specialty_ru":"Акушерство и гинекология","title_en":"Hypertensive Disorders of Pregnancy: Preeclampsia, Eclampsia and HELLP Syndrome","level":"advanced","lessons":5,"hours":5},
    {"id":"OBG-003","specialty":"Obstetrics","specialty_ru":"Акушерство и гинекология","title_en":"Gestational Diabetes and Medical Comorbidities in Pregnancy","level":"intermediate","lessons":4,"hours":4},
    {"id":"OBG-004","specialty":"Obstetrics","specialty_ru":"Акушерство и гинекология","title_en":"Labour, Delivery and Obstetric Emergencies: Partogram, PPH and Shoulder Dystocia","level":"advanced","lessons":5,"hours":5},
    {"id":"OBG-005","specialty":"Obstetrics","specialty_ru":"Акушерство и гинекология","title_en":"Gynaecological Cancers: Cervical, Endometrial, Ovarian — Staging and Treatment","level":"advanced","lessons":6,"hours":6},
    {"id":"OBG-006","specialty":"Obstetrics","specialty_ru":"Акушерство и гинекология","title_en":"Polycystic Ovary Syndrome: Pathophysiology, Fertility and Metabolic Management","level":"intermediate","lessons":4,"hours":4},
    {"id":"OBG-007","specialty":"Obstetrics","specialty_ru":"Акушерство и гинекология","title_en":"Menopause and HRT: Symptom Management, Cardiovascular and Bone Health","level":"intermediate","lessons":4,"hours":4},
    {"id":"OBG-008","specialty":"Obstetrics","specialty_ru":"Акушерство и гинекология","title_en":"Gynaecological Emergencies: Ectopic Pregnancy, Ovarian Torsion and PID","level":"advanced","lessons":4,"hours":4},
    # PSYCHIATRY
    {"id":"PSY-001","specialty":"Psychiatry","specialty_ru":"Психиатрия","title_en":"Schizophrenia and Psychotic Disorders: Dopamine Hypothesis, Antipsychotics and Rehab","level":"advanced","lessons":5,"hours":5},
    {"id":"PSY-002","specialty":"Psychiatry","specialty_ru":"Психиатрия","title_en":"Depressive Disorders: Neurobiology, SSRI/SNRI, Augmentation and TMS/ECT","level":"intermediate","lessons":5,"hours":5},
    {"id":"PSY-003","specialty":"Psychiatry","specialty_ru":"Психиатрия","title_en":"Bipolar Disorder: Mood Stabilisers, Lithium Monitoring and Long-Term Management","level":"advanced","lessons":5,"hours":5},
    {"id":"PSY-004","specialty":"Psychiatry","specialty_ru":"Психиатрия","title_en":"Anxiety and Related Disorders: GAD, Panic, OCD, PTSD — CBT and Pharmacotherapy","level":"intermediate","lessons":5,"hours":5},
    {"id":"PSY-005","specialty":"Psychiatry","specialty_ru":"Психиатрия","title_en":"Substance Use Disorders: Alcohol, Opioids, Stimulants — Dependence and Withdrawal","level":"advanced","lessons":5,"hours":5},
    {"id":"PSY-006","specialty":"Psychiatry","specialty_ru":"Психиатрия","title_en":"Eating Disorders: Anorexia, Bulimia, BED — Pathogenesis and Multidisciplinary Treatment","level":"advanced","lessons":4,"hours":4},
    {"id":"PSY-007","specialty":"Psychiatry","specialty_ru":"Психиатрия","title_en":"Child and Adolescent Psychiatry: ADHD, Autism, Conduct Disorder, Adolescent Depression","level":"intermediate","lessons":4,"hours":4},
    # ANESTHESIOLOGY
    {"id":"ANESTH-001","specialty":"Anesthesiology","specialty_ru":"Анестезиология и реанимация","title_en":"General Anaesthesia: Pharmacology, Induction Agents, Volatile Agents and Emergence","level":"advanced","lessons":5,"hours":5},
    {"id":"ANESTH-002","specialty":"Anesthesiology","specialty_ru":"Анестезиология и реанимация","title_en":"Regional Anaesthesia: Spinal, Epidural and Peripheral Nerve Block Techniques","level":"advanced","lessons":5,"hours":5},
    {"id":"ANESTH-003","specialty":"Anesthesiology","specialty_ru":"Анестезиология и реанимация","title_en":"Airway Management: Difficult Airway Algorithm, RSI and Video Laryngoscopy","level":"advanced","lessons":4,"hours":4},
    {"id":"ANESTH-004","specialty":"Anesthesiology","specialty_ru":"Анестезиология и реанимация","title_en":"Anaesthetic Complications: Malignant Hyperthermia, Awareness, LAST, Anaphylaxis","level":"advanced","lessons":4,"hours":4},
    {"id":"ANESTH-005","specialty":"Anesthesiology","specialty_ru":"Анестезиология и реанимация","title_en":"Acute and Chronic Pain Management: Multimodal Analgesia and Interventional Techniques","level":"intermediate","lessons":5,"hours":5},
    {"id":"ANESTH-006","specialty":"Anesthesiology","specialty_ru":"Анестезиология и реанимация","title_en":"Obstetric Anaesthesia: Labour Epidural, Spinal for C-Section and Complications","level":"advanced","lessons":4,"hours":4},
    # PHARMACOLOGY
    {"id":"PHARM-001","specialty":"Pharmacology","specialty_ru":"Фармакология","title_en":"Cardiovascular Pharmacology: Antihypertensives, Antiarrhythmics and Anticoagulants","level":"advanced","lessons":6,"hours":6},
    {"id":"PHARM-002","specialty":"Pharmacology","specialty_ru":"Фармакология","title_en":"Antimicrobial Pharmacology: PK/PD Principles, Beta-lactams, Macrolides and Resistance","level":"advanced","lessons":5,"hours":5},
    {"id":"PHARM-003","specialty":"Pharmacology","specialty_ru":"Фармакология","title_en":"CNS Pharmacology: Antidepressants, Antipsychotics, Benzodiazepines, Antiepileptics","level":"advanced","lessons":6,"hours":6},
    {"id":"PHARM-004","specialty":"Pharmacology","specialty_ru":"Фармакология","title_en":"Anti-inflammatory Pharmacology: NSAIDs, Corticosteroids, DMARDs and Biologics","level":"advanced","lessons":5,"hours":5},
    {"id":"PHARM-005","specialty":"Pharmacology","specialty_ru":"Фармакология","title_en":"Oncology Pharmacology: Cytotoxics, Targeted Agents, Immunotherapy — Mechanisms and Toxicity","level":"advanced","lessons":5,"hours":5},
    {"id":"PHARM-006","specialty":"Pharmacology","specialty_ru":"Фармакология","title_en":"Analgesic Pharmacology: Opioid Receptors, WHO Pain Ladder, Adjuvants and Side Effects","level":"intermediate","lessons":4,"hours":4},
    # UROLOGY
    {"id":"UROL-001","specialty":"Urology","specialty_ru":"Урология","title_en":"Benign Prostatic Hyperplasia: LUTS, Alpha-blockers, 5-ARIs and Surgical Options","level":"intermediate","lessons":4,"hours":4},
    {"id":"UROL-002","specialty":"Urology","specialty_ru":"Урология","title_en":"Prostate Cancer: PSA, Gleason Score, Active Surveillance, Radical Prostatectomy and ADT","level":"advanced","lessons":5,"hours":5},
    {"id":"UROL-003","specialty":"Urology","specialty_ru":"Урология","title_en":"Bladder and Renal Cancers: Urothelial Biology, BCG, Immunotherapy and Nephrectomy","level":"advanced","lessons":5,"hours":5},
    {"id":"UROL-004","specialty":"Urology","specialty_ru":"Урология","title_en":"Urinary Incontinence: Stress, Urge and Mixed — Pelvic Floor, Anticholinergics and Surgery","level":"intermediate","lessons":4,"hours":4},
    {"id":"UROL-005","specialty":"Urology","specialty_ru":"Урология","title_en":"Male Sexual Health: Erectile Dysfunction, Peyronie's Disease and Male Infertility","level":"intermediate","lessons":4,"hours":4},
]

DISEASE_MODULES = [
    {"id":"DISEASE-CAD-001","specialty":"Cardiology","specialty_ru":"Кардиология","title_en":"Coronary Artery Disease: Complete Guide from Discovery to Modern Intervention","level":"advanced","lessons":8,"hours":10,"type":"disease"},
    {"id":"DISEASE-HF-001","specialty":"Cardiology","specialty_ru":"Кардиология","title_en":"Heart Failure: Pathophysiology, Phenotypes (HFrEF/HFpEF) and Quadruple Therapy","level":"advanced","lessons":7,"hours":8,"type":"disease"},
    {"id":"DISEASE-HTN-001","specialty":"Internal Medicine","specialty_ru":"Терапия","title_en":"Arterial Hypertension: History, Mechanisms, Target Organ Damage and Treatment","level":"intermediate","lessons":6,"hours":7,"type":"disease"},
    {"id":"DISEASE-DM2-001","specialty":"Endocrinology","specialty_ru":"Эндокринология","title_en":"Type 2 Diabetes: Epidemic, Pathophysiology, Pharmacotherapy and Prevention","level":"intermediate","lessons":7,"hours":8,"type":"disease"},
    {"id":"DISEASE-STROKE-001","specialty":"Neurology","specialty_ru":"Неврология","title_en":"Ischaemic Stroke: From Brain Anatomy to Thrombectomy and Neuroprotection","level":"advanced","lessons":7,"hours":8,"type":"disease"},
    {"id":"DISEASE-SEPSIS-001","specialty":"Critical Care","specialty_ru":"Реаниматология и ИТ","title_en":"Sepsis: Historical Definitions, Pathophysiology, Biomarkers and Surviving Sepsis 2024","level":"advanced","lessons":7,"hours":8,"type":"disease"},
    {"id":"DISEASE-COPD-001","specialty":"Pulmonology","specialty_ru":"Пульмонология","title_en":"COPD: From Emphysema History to Personalized Triple Therapy","level":"advanced","lessons":7,"hours":8,"type":"disease"},
    {"id":"DISEASE-IBD-001","specialty":"Gastroenterology","specialty_ru":"Гастроэнтерология","title_en":"Inflammatory Bowel Disease: Discovery, Microbiome, Biologics and Surgical Options","level":"advanced","lessons":7,"hours":8,"type":"disease"},
    {"id":"DISEASE-CKD-001","specialty":"Nephrology","specialty_ru":"Нефрология","title_en":"Chronic Kidney Disease: From Glomerular Discovery to SGLT2i and ESRD Prevention","level":"advanced","lessons":7,"hours":8,"type":"disease"},
    {"id":"DISEASE-RA-001","specialty":"Rheumatology","specialty_ru":"Ревматология","title_en":"Rheumatoid Arthritis: Autoimmunity Discovery, ACR Criteria, JAK Inhibitors","level":"advanced","lessons":6,"hours":7,"type":"disease"},
    {"id":"DISEASE-HIV-001","specialty":"Infectious Diseases","specialty_ru":"Инфекционные болезни","title_en":"HIV/AIDS: Discovery, Retrovirology, ART Revolution and Long-Term Management","level":"advanced","lessons":8,"hours":9,"type":"disease"},
    {"id":"DISEASE-TB-001","specialty":"Infectious Diseases","specialty_ru":"Инфекционные болезни","title_en":"Tuberculosis: Koch's Discovery, Pathogenesis, Drug Resistance and Global Control","level":"advanced","lessons":7,"hours":8,"type":"disease"},
    {"id":"DISEASE-BRCA-001","specialty":"Oncology","specialty_ru":"Онкология","title_en":"Breast Cancer: Molecular Biology, BRCA Mutations, Targeted Therapy and Survivorship","level":"advanced","lessons":8,"hours":9,"type":"disease"},
    {"id":"DISEASE-LUNGCA-001","specialty":"Oncology","specialty_ru":"Онкология","title_en":"Lung Cancer: Smoking Carcinogenesis, Driver Mutations, Immunotherapy Breakthrough","level":"advanced","lessons":7,"hours":8,"type":"disease"},
    {"id":"DISEASE-PD-001","specialty":"Neurology","specialty_ru":"Неврология","title_en":"Parkinson's Disease: Lewy Bodies, Dopamine Pathways, L-DOPA and Deep Brain Stimulation","level":"advanced","lessons":7,"hours":8,"type":"disease"},
    {"id":"DISEASE-AD-001","specialty":"Neurology","specialty_ru":"Неврология","title_en":"Alzheimer's Disease: Amyloid Hypothesis, Biomarkers, Lecanemab and Future Directions","level":"advanced","lessons":7,"hours":8,"type":"disease"},
    {"id":"DISEASE-SLE-001","specialty":"Rheumatology","specialty_ru":"Ревматология","title_en":"Systemic Lupus Erythematosus: Autoimmunity, Organ Manifestations and Belimumab","level":"advanced","lessons":7,"hours":8,"type":"disease"},
    {"id":"DISEASE-CIRRH-001","specialty":"Gastroenterology","specialty_ru":"Гастроэнтерология","title_en":"Liver Cirrhosis: Fibrogenesis, Portal Hypertension, Complications and Transplantation","level":"advanced","lessons":8,"hours":9,"type":"disease"},
    {"id":"DISEASE-ANEMIA-001","specialty":"Hematology","specialty_ru":"Гематология","title_en":"Iron Deficiency and Anaemia: Discovery of Iron Metabolism, Hepcidin and IV Iron","level":"intermediate","lessons":6,"hours":6,"type":"disease"},
    {"id":"DISEASE-PSORIASIS-001","specialty":"Dermatology","specialty_ru":"Дерматология","title_en":"Psoriasis: IL-17/23 Axis, Psoriatic Arthritis, Biologics and Quality of Life","level":"advanced","lessons":6,"hours":7,"type":"disease"},
    {"id":"DISEASE-AFIB-001","specialty":"Cardiology","specialty_ru":"Кардиология","title_en":"Atrial Fibrillation: From Discovery of AF Mechanisms to DOACs and Catheter Ablation","level":"advanced","lessons":7,"hours":8,"type":"disease"},
    {"id":"DISEASE-ASTHMA-001","specialty":"Pulmonology","specialty_ru":"Пульмонология","title_en":"Bronchial Asthma: From Hippocrates to ICS, Biologics and SMART Therapy","level":"advanced","lessons":7,"hours":8,"type":"disease"},
    {"id":"DISEASE-MS-001","specialty":"Neurology","specialty_ru":"Неврология","title_en":"Multiple Sclerosis: Autoimmune Demyelination, MRI Revolution and High-Efficacy DMTs","level":"advanced","lessons":7,"hours":8,"type":"disease"},
    {"id":"DISEASE-EPILEPSY-001","specialty":"Neurology","specialty_ru":"Неврология","title_en":"Epilepsy: Ancient Descriptions to Precision AED Therapy and Surgical Cure","level":"advanced","lessons":7,"hours":8,"type":"disease"},
    {"id":"DISEASE-GOUT-001","specialty":"Rheumatology","specialty_ru":"Ревматология","title_en":"Gout: Urate Crystal Biology, Hyperuricaemia, Allopurinol and Treat-to-Target Era","level":"advanced","lessons":6,"hours":7,"type":"disease"},
    {"id":"DISEASE-NAFLD-001","specialty":"Gastroenterology","specialty_ru":"Гастроэнтерология","title_en":"NAFLD/MASLD: From Steatosis Discovery to Fibrosis, FIB-4 Score and Resmetirom","level":"advanced","lessons":7,"hours":8,"type":"disease"},
    {"id":"DISEASE-VTE-001","specialty":"Hematology","specialty_ru":"Гематология","title_en":"Venous Thromboembolism (DVT/PE): Pathogenesis, DOAC Revolution and Chronic Sequelae","level":"advanced","lessons":7,"hours":8,"type":"disease"},
    {"id":"DISEASE-OSA-001","specialty":"Pulmonology","specialty_ru":"Пульмонология","title_en":"Obstructive Sleep Apnoea: Discovery, Polysomnography, CPAP and Cardiovascular Risk","level":"advanced","lessons":6,"hours":7,"type":"disease"},
    {"id":"DISEASE-HYPOTHYROID-001","specialty":"Endocrinology","specialty_ru":"Эндокринология","title_en":"Hypothyroidism: Autoimmune Thyroiditis, Levothyroxine Dosing and TSH Targets","level":"advanced","lessons":6,"hours":7,"type":"disease"},
    {"id":"DISEASE-PCOS-001","specialty":"Obstetrics","specialty_ru":"Акушерство и гинекология","title_en":"Polycystic Ovary Syndrome: Pathogenesis, Fertility, Metabolic Consequences and GLP-1","level":"advanced","lessons":7,"hours":8,"type":"disease"},
    {"id":"DISEASE-MIGRAINE-001","specialty":"Neurology","specialty_ru":"Неврология","title_en":"Migraine: CGRP Biology, Triptans, Gepants and Preventive Monoclonal Antibodies","level":"advanced","lessons":7,"hours":8,"type":"disease"},
    {"id":"DISEASE-GASTRIC-CA-001","specialty":"Gastroenterology","specialty_ru":"Гастроэнтерология","title_en":"Gastric Cancer: H. pylori Oncogenesis, HER2 Amplification, Surgery and Immunotherapy","level":"advanced","lessons":7,"hours":8,"type":"disease"},
    {"id":"DISEASE-PANCREATITIS-001","specialty":"Gastroenterology","specialty_ru":"Гастроэнтерология","title_en":"Pancreatitis: Acinar Cell Injury, Severity Scoring, ERCP and Chronic Complications","level":"advanced","lessons":7,"hours":8,"type":"disease"},
    {"id":"DISEASE-OST-001","specialty":"Endocrinology","specialty_ru":"Эндокринология","title_en":"Osteoporosis: Bone Remodelling, FRAX Score, Bisphosphonates and Romosozumab","level":"advanced","lessons":7,"hours":8,"type":"disease"},
    {"id":"DISEASE-BLADDER-CA-001","specialty":"Urology","specialty_ru":"Урология","title_en":"Bladder Cancer: Urothelial Carcinogenesis, BCG Therapy, Cystectomy and Pembrolizumab","level":"advanced","lessons":6,"hours":7,"type":"disease"},
]

# Patient guides — comprehensive disease guides written for patients/public.
# Covers: what it is, causes, symptoms, diagnosis, treatment, prevention (primary + secondary),
# daily life with the disease, and questions to ask your doctor.
PATIENT_GUIDE_MODULES = [
    # ── CARDIOVASCULAR ────────────────────────────────────────────────────────
    {"id":"PG-CV-001","specialty":"Cardiology","specialty_ru":"Кардиология","title_en":"Coronary Heart Disease and Angina — Complete Patient Guide","level":"intermediate","lessons":7,"hours":6,"type":"patient_guide"},
    {"id":"PG-CV-002","specialty":"Cardiology","specialty_ru":"Кардиология","title_en":"Heart Failure — Complete Patient Guide","level":"intermediate","lessons":7,"hours":6,"type":"patient_guide"},
    {"id":"PG-CV-003","specialty":"Cardiology","specialty_ru":"Кардиология","title_en":"Atrial Fibrillation — Complete Patient Guide","level":"intermediate","lessons":7,"hours":6,"type":"patient_guide"},
    {"id":"PG-CV-004","specialty":"Cardiology","specialty_ru":"Кардиология","title_en":"Arterial Hypertension (High Blood Pressure) — Complete Patient Guide","level":"intermediate","lessons":7,"hours":6,"type":"patient_guide"},
    {"id":"PG-CV-005","specialty":"Neurology","specialty_ru":"Неврология","title_en":"Stroke and TIA — Complete Patient Guide","level":"intermediate","lessons":7,"hours":6,"type":"patient_guide"},
    # ── METABOLIC & ENDOCRINE ─────────────────────────────────────────────────
    {"id":"PG-META-001","specialty":"Endocrinology","specialty_ru":"Эндокринология","title_en":"Type 2 Diabetes Mellitus — Complete Patient Guide","level":"intermediate","lessons":7,"hours":7,"type":"patient_guide"},
    {"id":"PG-META-002","specialty":"Endocrinology","specialty_ru":"Эндокринология","title_en":"Type 1 Diabetes Mellitus — Complete Patient Guide","level":"intermediate","lessons":7,"hours":7,"type":"patient_guide"},
    {"id":"PG-META-003","specialty":"Endocrinology","specialty_ru":"Эндокринология","title_en":"Obesity and Metabolic Syndrome — Complete Patient Guide","level":"intermediate","lessons":7,"hours":6,"type":"patient_guide"},
    {"id":"PG-META-004","specialty":"Endocrinology","specialty_ru":"Эндокринология","title_en":"Hypothyroidism — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    {"id":"PG-META-005","specialty":"Endocrinology","specialty_ru":"Эндокринология","title_en":"Hyperthyroidism and Graves' Disease — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    {"id":"PG-META-006","specialty":"Rheumatology","specialty_ru":"Ревматология","title_en":"Gout and Hyperuricaemia — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    {"id":"PG-META-007","specialty":"Rheumatology","specialty_ru":"Ревматология","title_en":"Osteoporosis — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    # ── RESPIRATORY ───────────────────────────────────────────────────────────
    {"id":"PG-RESP-001","specialty":"Pulmonology","specialty_ru":"Пульмонология","title_en":"Bronchial Asthma — Complete Patient Guide","level":"intermediate","lessons":7,"hours":6,"type":"patient_guide"},
    {"id":"PG-RESP-002","specialty":"Pulmonology","specialty_ru":"Пульмонология","title_en":"COPD (Chronic Obstructive Pulmonary Disease) — Complete Patient Guide","level":"intermediate","lessons":7,"hours":6,"type":"patient_guide"},
    {"id":"PG-RESP-003","specialty":"Pulmonology","specialty_ru":"Пульмонология","title_en":"Obstructive Sleep Apnoea — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    {"id":"PG-RESP-004","specialty":"Pulmonology","specialty_ru":"Пульмонология","title_en":"Allergic Rhinitis and Hay Fever — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    # ── DIGESTIVE ─────────────────────────────────────────────────────────────
    {"id":"PG-GI-001","specialty":"Gastroenterology","specialty_ru":"Гастроэнтерология","title_en":"GERD and Acid Reflux — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    {"id":"PG-GI-002","specialty":"Gastroenterology","specialty_ru":"Гастроэнтерология","title_en":"Peptic Ulcer Disease and H. pylori Infection — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    {"id":"PG-GI-003","specialty":"Gastroenterology","specialty_ru":"Гастроэнтерология","title_en":"Irritable Bowel Syndrome (IBS) — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    {"id":"PG-GI-004","specialty":"Gastroenterology","specialty_ru":"Гастроэнтерология","title_en":"Crohn's Disease — Complete Patient Guide","level":"intermediate","lessons":7,"hours":6,"type":"patient_guide"},
    {"id":"PG-GI-005","specialty":"Gastroenterology","specialty_ru":"Гастроэнтерология","title_en":"Ulcerative Colitis — Complete Patient Guide","level":"intermediate","lessons":7,"hours":6,"type":"patient_guide"},
    {"id":"PG-GI-006","specialty":"Gastroenterology","specialty_ru":"Гастроэнтерология","title_en":"Non-Alcoholic Fatty Liver Disease (NAFLD/MASLD) — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    {"id":"PG-GI-007","specialty":"Gastroenterology","specialty_ru":"Гастроэнтерология","title_en":"Gallstones and Cholecystitis — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    # ── KIDNEY & URINARY ──────────────────────────────────────────────────────
    {"id":"PG-RENAL-001","specialty":"Nephrology","specialty_ru":"Нефрология","title_en":"Chronic Kidney Disease — Complete Patient Guide","level":"intermediate","lessons":7,"hours":6,"type":"patient_guide"},
    {"id":"PG-RENAL-002","specialty":"Nephrology","specialty_ru":"Нефрология","title_en":"Kidney Stones (Nephrolithiasis) — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    {"id":"PG-RENAL-003","specialty":"Nephrology","specialty_ru":"Нефрология","title_en":"Urinary Tract Infections (UTI) — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    # ── MUSCULOSKELETAL ───────────────────────────────────────────────────────
    {"id":"PG-MSK-001","specialty":"Rheumatology","specialty_ru":"Ревматология","title_en":"Osteoarthritis (Knee, Hip, Spine) — Complete Patient Guide","level":"intermediate","lessons":7,"hours":6,"type":"patient_guide"},
    {"id":"PG-MSK-002","specialty":"Rheumatology","specialty_ru":"Ревматология","title_en":"Rheumatoid Arthritis — Complete Patient Guide","level":"intermediate","lessons":7,"hours":6,"type":"patient_guide"},
    {"id":"PG-MSK-003","specialty":"Orthopedics","specialty_ru":"Ортопедия и травматология","title_en":"Chronic Lower Back Pain — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    # ── NEUROLOGY ─────────────────────────────────────────────────────────────
    {"id":"PG-NEURO-001","specialty":"Neurology","specialty_ru":"Неврология","title_en":"Migraine — Complete Patient Guide","level":"intermediate","lessons":7,"hours":6,"type":"patient_guide"},
    {"id":"PG-NEURO-002","specialty":"Neurology","specialty_ru":"Неврология","title_en":"Epilepsy — Complete Patient Guide","level":"intermediate","lessons":7,"hours":6,"type":"patient_guide"},
    {"id":"PG-NEURO-003","specialty":"Neurology","specialty_ru":"Неврология","title_en":"Alzheimer's Disease and Dementia — Complete Patient Guide","level":"intermediate","lessons":7,"hours":7,"type":"patient_guide"},
    {"id":"PG-NEURO-004","specialty":"Neurology","specialty_ru":"Неврология","title_en":"Parkinson's Disease — Complete Patient Guide","level":"intermediate","lessons":7,"hours":7,"type":"patient_guide"},
    # ── MENTAL HEALTH ─────────────────────────────────────────────────────────
    {"id":"PG-MH-001","specialty":"Psychiatry","specialty_ru":"Психиатрия","title_en":"Depression — Complete Patient Guide","level":"intermediate","lessons":7,"hours":6,"type":"patient_guide"},
    {"id":"PG-MH-002","specialty":"Psychiatry","specialty_ru":"Психиатрия","title_en":"Anxiety Disorders — Complete Patient Guide","level":"intermediate","lessons":7,"hours":6,"type":"patient_guide"},
    {"id":"PG-MH-003","specialty":"Psychiatry","specialty_ru":"Психиатрия","title_en":"Insomnia and Sleep Disorders — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    {"id":"PG-MH-004","specialty":"Psychiatry","specialty_ru":"Психиатрия","title_en":"Burnout and Chronic Stress — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    # ── INFECTIOUS DISEASES ───────────────────────────────────────────────────
    {"id":"PG-INF-001","specialty":"Infectious Diseases","specialty_ru":"Инфекционные болезни","title_en":"HIV and AIDS — Complete Patient Guide","level":"intermediate","lessons":7,"hours":7,"type":"patient_guide"},
    {"id":"PG-INF-002","specialty":"Infectious Diseases","specialty_ru":"Инфекционные болезни","title_en":"Hepatitis B — Complete Patient Guide","level":"intermediate","lessons":7,"hours":6,"type":"patient_guide"},
    {"id":"PG-INF-003","specialty":"Infectious Diseases","specialty_ru":"Инфекционные болезни","title_en":"Hepatitis C — Complete Patient Guide","level":"intermediate","lessons":7,"hours":6,"type":"patient_guide"},
    {"id":"PG-INF-004","specialty":"Infectious Diseases","specialty_ru":"Инфекционные болезни","title_en":"Tuberculosis — Complete Patient Guide","level":"intermediate","lessons":7,"hours":6,"type":"patient_guide"},
    # ── ONCOLOGY ──────────────────────────────────────────────────────────────
    {"id":"PG-ONC-001","specialty":"Oncology","specialty_ru":"Онкология","title_en":"Breast Cancer — Complete Patient Guide","level":"intermediate","lessons":7,"hours":7,"type":"patient_guide"},
    {"id":"PG-ONC-002","specialty":"Oncology","specialty_ru":"Онкология","title_en":"Colorectal Cancer — Complete Patient Guide","level":"intermediate","lessons":7,"hours":7,"type":"patient_guide"},
    {"id":"PG-ONC-003","specialty":"Oncology","specialty_ru":"Онкология","title_en":"Lung Cancer — Complete Patient Guide","level":"intermediate","lessons":7,"hours":7,"type":"patient_guide"},
    {"id":"PG-ONC-004","specialty":"Oncology","specialty_ru":"Онкология","title_en":"Prostate Cancer — Complete Patient Guide","level":"intermediate","lessons":7,"hours":7,"type":"patient_guide"},
    {"id":"PG-ONC-005","specialty":"Oncology","specialty_ru":"Онкология","title_en":"Cervical Cancer and HPV Prevention — Complete Patient Guide","level":"intermediate","lessons":6,"hours":6,"type":"patient_guide"},
    # ── DERMATOLOGY ───────────────────────────────────────────────────────────
    {"id":"PG-DERM-001","specialty":"Dermatology","specialty_ru":"Дерматология","title_en":"Psoriasis — Complete Patient Guide","level":"intermediate","lessons":7,"hours":6,"type":"patient_guide"},
    {"id":"PG-DERM-002","specialty":"Dermatology","specialty_ru":"Дерматология","title_en":"Atopic Dermatitis (Eczema) — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    {"id":"PG-DERM-003","specialty":"Dermatology","specialty_ru":"Дерматология","title_en":"Acne Vulgaris — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    # ── BLOOD ─────────────────────────────────────────────────────────────────
    {"id":"PG-HEM-001","specialty":"Hematology","specialty_ru":"Гематология","title_en":"Iron Deficiency Anaemia — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    # ── GYNAECOLOGY ───────────────────────────────────────────────────────────
    {"id":"PG-WOMENS-001","specialty":"Obstetrics","specialty_ru":"Акушерство и гинекология","title_en":"Endometriosis — Complete Patient Guide","level":"intermediate","lessons":7,"hours":6,"type":"patient_guide"},
    {"id":"PG-WOMENS-002","specialty":"Obstetrics","specialty_ru":"Акушерство и гинекология","title_en":"Polycystic Ovary Syndrome (PCOS) — Complete Patient Guide","level":"intermediate","lessons":7,"hours":6,"type":"patient_guide"},
    {"id":"PG-WOMENS-003","specialty":"Obstetrics","specialty_ru":"Акушерство и гинекология","title_en":"Menopause: Symptoms, HRT and Long-Term Health — Complete Patient Guide","level":"intermediate","lessons":7,"hours":6,"type":"patient_guide"},
    {"id":"PG-PREG-001","specialty":"Obstetrics","specialty_ru":"Акушерство и гинекология","title_en":"Gestational Diabetes — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    {"id":"PG-PREG-002","specialty":"Obstetrics","specialty_ru":"Акушерство и гинекология","title_en":"Preeclampsia and High-Risk Pregnancy — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    # ── UROLOGY ───────────────────────────────────────────────────────────────
    {"id":"PG-UROL-001","specialty":"Urology","specialty_ru":"Урология","title_en":"Enlarged Prostate (Benign Prostatic Hyperplasia) — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    {"id":"PG-UROL-002","specialty":"Urology","specialty_ru":"Урология","title_en":"Erectile Dysfunction — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    {"id":"PG-UROL-003","specialty":"Urology","specialty_ru":"Урология","title_en":"Prostate Cancer — Complete Patient Guide","level":"intermediate","lessons":7,"hours":7,"type":"patient_guide"},
    {"id":"PG-UROL-004","specialty":"Urology","specialty_ru":"Урология","title_en":"Urinary Incontinence — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    # ── DIGESTIVE (extra) ─────────────────────────────────────────────────────
    {"id":"PG-GI-008","specialty":"Gastroenterology","specialty_ru":"Гастроэнтерология","title_en":"Celiac Disease and Gluten Intolerance — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    {"id":"PG-GI-009","specialty":"Gastroenterology","specialty_ru":"Гастроэнтерология","title_en":"Hemorrhoids — Complete Patient Guide","level":"intermediate","lessons":5,"hours":4,"type":"patient_guide"},
    {"id":"PG-GI-010","specialty":"Gastroenterology","specialty_ru":"Гастроэнтерология","title_en":"Chronic Constipation and Digestive Health — Complete Patient Guide","level":"intermediate","lessons":5,"hours":4,"type":"patient_guide"},
    {"id":"PG-GI-011","specialty":"Gastroenterology","specialty_ru":"Гастроэнтерология","title_en":"Chronic Pancreatitis — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    # ── NEUROLOGY (extra) ─────────────────────────────────────────────────────
    {"id":"PG-NEURO-005","specialty":"Neurology","specialty_ru":"Неврология","title_en":"Multiple Sclerosis — Complete Patient Guide","level":"intermediate","lessons":7,"hours":7,"type":"patient_guide"},
    # ── EYE ──────────────────────────────────────────────────────────────────
    {"id":"PG-EYE-001","specialty":"Ophthalmology","specialty_ru":"Офтальмология","title_en":"Glaucoma — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    {"id":"PG-EYE-002","specialty":"Ophthalmology","specialty_ru":"Офтальмология","title_en":"Cataracts — Complete Patient Guide","level":"intermediate","lessons":5,"hours":4,"type":"patient_guide"},
    {"id":"PG-EYE-003","specialty":"Ophthalmology","specialty_ru":"Офтальмология","title_en":"Diabetic Retinopathy — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    # ── EAR, NOSE, THROAT ─────────────────────────────────────────────────────
    {"id":"PG-EAR-001","specialty":"Otorhinolaryngology","specialty_ru":"ЛОР-болезни","title_en":"Tinnitus — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    {"id":"PG-EAR-002","specialty":"Otorhinolaryngology","specialty_ru":"ЛОР-болезни","title_en":"Age-Related Hearing Loss (Presbycusis) — Complete Patient Guide","level":"intermediate","lessons":5,"hours":4,"type":"patient_guide"},
    {"id":"PG-EAR-003","specialty":"Otorhinolaryngology","specialty_ru":"ЛОР-болезни","title_en":"Chronic Sinusitis — Complete Patient Guide","level":"intermediate","lessons":5,"hours":4,"type":"patient_guide"},
    # ── METABOLIC (extra) ─────────────────────────────────────────────────────
    {"id":"PG-META-008","specialty":"Endocrinology","specialty_ru":"Эндокринология","title_en":"Vitamin D Deficiency — Complete Patient Guide","level":"intermediate","lessons":5,"hours":4,"type":"patient_guide"},
    {"id":"PG-META-009","specialty":"Endocrinology","specialty_ru":"Эндокринология","title_en":"Chronic Fatigue Syndrome and ME/CFS — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    {"id":"PG-META-010","specialty":"Endocrinology","specialty_ru":"Эндокринология","title_en":"Fibromyalgia — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    # ── ONCOLOGY (extra) ──────────────────────────────────────────────────────
    {"id":"PG-ONC-006","specialty":"Oncology","specialty_ru":"Онкология","title_en":"Thyroid Cancer — Complete Patient Guide","level":"intermediate","lessons":6,"hours":6,"type":"patient_guide"},
    {"id":"PG-ONC-007","specialty":"Oncology","specialty_ru":"Онкология","title_en":"Skin Cancer and Melanoma — Complete Patient Guide","level":"intermediate","lessons":6,"hours":6,"type":"patient_guide"},
    # ── CARDIOVASCULAR (extra) ────────────────────────────────────────────────
    {"id":"PG-CARD-001","specialty":"Cardiology","specialty_ru":"Кардиология","title_en":"Peripheral Arterial Disease and Leg Circulation — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    {"id":"PG-CARD-002","specialty":"Cardiology","specialty_ru":"Кардиология","title_en":"DVT and Pulmonary Embolism — Complete Patient Guide","level":"intermediate","lessons":7,"hours":6,"type":"patient_guide"},
    {"id":"PG-CARD-003","specialty":"Cardiology","specialty_ru":"Кардиология","title_en":"Varicose Veins and Chronic Venous Insufficiency — Complete Patient Guide","level":"intermediate","lessons":5,"hours":4,"type":"patient_guide"},
    # ── MUSCULOSKELETAL (extra) ───────────────────────────────────────────────
    {"id":"PG-MSK-004","specialty":"Orthopedics","specialty_ru":"Ортопедия и травматология","title_en":"Carpal Tunnel Syndrome — Complete Patient Guide","level":"intermediate","lessons":5,"hours":4,"type":"patient_guide"},
    {"id":"PG-MSK-005","specialty":"Orthopedics","specialty_ru":"Ортопедия и травматология","title_en":"Plantar Fasciitis — Complete Patient Guide","level":"intermediate","lessons":5,"hours":4,"type":"patient_guide"},
    # ── INFECTIOUS (extra) ────────────────────────────────────────────────────
    {"id":"PG-INF-005","specialty":"Infectious Diseases","specialty_ru":"Инфекционные болезни","title_en":"Shingles (Herpes Zoster) — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    {"id":"PG-INF-006","specialty":"Infectious Diseases","specialty_ru":"Инфекционные болезни","title_en":"Lyme Disease — Complete Patient Guide","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    # ── PAEDIATRIC (guides for parents) ──────────────────────────────────────
    {"id":"PG-PAED-001","specialty":"Pediatrics","specialty_ru":"Педиатрия","title_en":"ADHD in Children — Complete Guide for Parents","level":"intermediate","lessons":7,"hours":6,"type":"patient_guide"},
    {"id":"PG-PAED-002","specialty":"Pediatrics","specialty_ru":"Педиатрия","title_en":"Childhood Asthma — Complete Guide for Parents","level":"intermediate","lessons":6,"hours":5,"type":"patient_guide"},
    {"id":"PG-PAED-003","specialty":"Pediatrics","specialty_ru":"Педиатрия","title_en":"Autism Spectrum Disorder — Complete Guide for Parents and Families","level":"intermediate","lessons":7,"hours":6,"type":"patient_guide"},
]

ALL_MODULES = SPECIALTY_MODULES + DISEASE_MODULES + PATIENT_GUIDE_MODULES

# ── Prompts ───────────────────────────────────────────────────────────────────
SPECIALTY_PROMPT = """You are a senior medical educator. Generate a complete educational module as a single JSON object.

Module:
- ID: {module_id}
- Title: {title_en}
- Specialty: {specialty}
- Level: {level}
- Lessons: {lessons_count}
- Duration: {hours} hours

Generate exactly {lessons_count} lessons covering: Epidemiology & Pathophysiology / Clinical Presentation / Investigations & Diagnosis / Treatment & Management / Complications & Prognosis (adjust to topic).

Return ONLY valid JSON, no markdown. Schema:
{{"meta":{{"id":"{module_id}","type":"specialty_module","specialty":"{specialty}","specialty_ru":"{specialty_ru}","title_en":"{title_en}","level":"{level}","duration_hours":{hours},"version":"1.0","generated_by":"ai","generated_at":"{date}"}},"lessons":[{{"id":"L001","order":1,"title":"Lesson title","content":{{"intro":"2-3 paragraph intro (250 words, specific clinical details)","sections":[{{"heading":"Section","text":"300-400 words with specific drug names, doses, guidelines (ESC/ACC/AHA year), thresholds, trial names"}}],"clinical_pearl":"Key clinical insight with specific numbers (100 words)","key_points":["Specific fact with numbers/doses"],"references":[{{"title":"Guideline/trial","authors":"Authors or society","journal_or_source":"Journal","year":2024,"type":"guideline","note":"Key finding"}}]}}}}]}}

Requirements per lesson: 3 sections, 6 key_points, 3 references. Include ESC/AHA/NICE guideline years, drug doses, landmark trial names. Total ≈8 000 tokens."""

DISEASE_PROMPT = """You are a senior medical educator and historian of medicine. Generate a disease deep-dive module as a single JSON object.

Disease Module:
- ID: {module_id}
- Title: {title_en}
- Specialty: {specialty}
- Level: {level}
- Lessons: {lessons_count}
- Duration: {hours} hours
{lesson_range_note}

Mandatory lesson structure:
L1: History of the Disease (who discovered it, when, key milestones, Nobel prizes, famous cases, how understanding evolved)
L2: Pathophysiology & Aetiology (molecular mechanisms, genetic factors, subtypes)
L3: Clinical Presentation (cardinal symptoms, stages, atypical presentations)
L4: Diagnosis (criteria, scoring systems, labs, imaging, differential)
L5: Treatment — Pharmacological & Non-pharmacological (first/second line, doses, evidence)
L6: Complications & Prognosis (incidence data, prognostic scores)
L7: Special Populations & Emerging Therapies (paediatric/elderly/pregnancy, pipeline drugs)
L8: Clinical Case & Applied Knowledge (if 8 lessons)

Return ONLY valid JSON, no markdown. Same schema as specialty module but type="disease_module".
L1 MUST include: specific years, scientist names, landmark papers, historical patients/outbreaks.
Each section: 350-450 words. key_points: 8 per lesson. Total ≈9 000 tokens."""

PATIENT_GUIDE_PROMPT = """You are a compassionate medical writer creating a comprehensive patient education guide. Generate a complete module as a single JSON object.

Patient Guide:
- ID: {module_id}
- Title: {title_en}
- Specialty: {specialty}
- Lessons: {lessons_count}
- Duration: {hours} hours
{lesson_range_note}

Mandatory lesson structure (7 lessons):
L1: What Is This Disease? — plain-language definition, how common it is, who gets it, why it matters, key statistics
L2: Causes and Risk Factors — genetic factors, lifestyle triggers, modifiable vs non-modifiable risks, who is most at risk and why
L3: Symptoms and How the Disease Develops — early warning signs, how the disease progresses over time, what patients actually feel, when to seek urgent care
L4: How Is It Diagnosed? — which tests are done, what the results mean, what to expect at appointments, how long diagnosis takes
L5: Treatment Options — all available treatments (medications with plain-language explanations, procedures, surgery, rehabilitation), how to choose between options, side effects to know about
L6: Prevention — PRIMARY (how to avoid getting the disease: lifestyle, screening, vaccination) and SECONDARY (how to prevent complications and slow progression after diagnosis: monitoring, targets, self-management)
L7: Living Well with This Condition — daily life adjustments, diet and exercise guidance, what to monitor at home, red flags that need urgent attention, how to talk to your doctor, support resources, mental health aspects, outlook

Adjust to 6 lessons for simpler diseases by merging L6+L7 into one lesson.

Writing style:
- Plain language understandable to a patient with no medical background
- Warm, reassuring tone — not alarming, not dismissive
- Use analogies to explain complex concepts
- Specific, actionable advice (e.g., "aim for HbA1c below 7%", "walk 30 minutes 5 days per week")
- Include "Questions to ask your doctor" at end of each lesson (3 questions)
- Include "Key takeaway" box at end of each lesson

Return ONLY valid JSON, no markdown. Schema:
{{"meta":{{"id":"{module_id}","type":"patient_guide","specialty":"{specialty}","specialty_ru":"{specialty_ru}","title_en":"{title_en}","level":"{level}","duration_hours":{hours},"version":"1.0","generated_by":"ai","generated_at":"{date}","audience":"patient"}},"lessons":[{{"id":"L001","order":1,"title":"Lesson title","content":{{"intro":"2-3 paragraph friendly intro (200 words)","sections":[{{"heading":"Section","text":"300-400 words in plain language, with specific numbers and practical advice"}}],"clinical_pearl":"Key fact every patient should know (80 words, plain language)","key_points":["Practical takeaway point"],"questions_for_doctor":["Question to ask your doctor?"],"references":[{{"title":"Source","authors":"Organisation","journal_or_source":"Source","year":2024,"type":"guideline","note":"Key recommendation"}}]}}}}]}}

Requirements per lesson: 3 sections, 6 key_points, 3 questions_for_doctor, 2 references. Total ≈8 000 tokens."""


# ── Rate limit parser ─────────────────────────────────────────────────────────

def parse_retry_seconds(error_text: str) -> float:
    """
    Parse 'Please try again in 7h32m33.792s' from Groq error body.
    Returns total seconds to wait, or 0 if not found.
    """
    m = re.search(r"try again in\s+((?:\d+h)?(?:\d+m)?(?:\d+(?:\.\d+)?s)?)", error_text)
    if not m:
        return 0.0
    s = m.group(1)
    total = 0.0
    for pat, mult in [(r"(\d+)h", 3600), (r"(\d+)m", 60), (r"(\d+(?:\.\d+)?)s", 1)]:
        n = re.search(pat, s)
        if n:
            total += float(n.group(1)) * mult
    return total


def sleep_with_log(seconds: float, reason: str) -> None:
    wake = datetime.now() + timedelta(seconds=seconds)
    log(f"  ⏳ {reason} — waiting {seconds/3600:.2f}h until {wake.strftime('%H:%M:%S')}")
    # Log every 30 min so we know it's alive
    chunk = 1800
    remaining = seconds
    while remaining > 0:
        s = min(chunk, remaining)
        time.sleep(s)
        remaining -= s
        if remaining > 60:
            log(f"  … {remaining/3600:.1f}h remaining")


# ── Logging ───────────────────────────────────────────────────────────────────

def log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


# ── JSON extraction ───────────────────────────────────────────────────────────

def extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text.strip())
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("No JSON found in response")
    return json.loads(text[start:end])


# ── Groq call with full retry logic ──────────────────────────────────────────

def call_groq(prompt: str, max_retries: int = 10) -> str:
    """Call Groq API. Handles 429 TPM and TPD limits with exact waits."""
    import httpx

    if not GROQ_KEY:
        raise RuntimeError("GROQ_KEY_MODULE env var not set")

    for attempt in range(max_retries):
        try:
            resp = httpx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 10000,
                    "response_format": {"type": "json_object"},
                },
                timeout=180.0,
            )
        except Exception as e:
            log(f"  Network error (attempt {attempt+1}): {e}")
            time.sleep(30)
            continue

        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]

        if resp.status_code == 429:
            body = resp.text
            wait = parse_retry_seconds(body)
            if "tokens per day" in body or "TPD" in body:
                # Daily limit hit — exit so cron can retry after reset
                raise TPDLimitError(body)
            elif "tokens per minute" in body or "TPM" in body:
                # Per-minute limit — add 10s buffer
                wait = max(wait, 10) + 10
                log(f"  TPM limit — waiting {wait:.0f}s")
                time.sleep(wait)
            else:
                # Unknown 429
                wait = max(wait, 120) + 60
                log(f"  Rate limit (unknown) — waiting {wait:.0f}s")
                time.sleep(wait)
            continue

        if resp.status_code in (500, 502, 503):
            log(f"  Server error {resp.status_code} (attempt {attempt+1}) — waiting 60s")
            time.sleep(60)
            continue

        raise RuntimeError(f"Groq {resp.status_code}: {resp.text[:300]}")

    raise RuntimeError(f"Max retries ({max_retries}) exceeded")


# ── Module generation ─────────────────────────────────────────────────────────

def build_prompt(mod: dict, lesson_range: tuple[int,int] | None = None) -> str:
    mtype = mod.get("type", "specialty")
    if mtype == "disease":
        template = DISEASE_PROMPT
    elif mtype == "patient_guide":
        template = PATIENT_GUIDE_PROMPT
    else:
        template = SPECIALTY_PROMPT

    note = ""
    lcount = mod["lessons"]
    mtype = mod.get("type", "specialty")
    if lesson_range:
        s, e = lesson_range
        lcount = e - s + 1
        note = f"\nGenerate ONLY lessons L{s:03d}–L{e:03d} (lessons {s} to {e} of {mod['lessons']} total)."
        if mtype in ("disease", "patient_guide"):
            note += f" Start from Lesson {s} in the mandatory structure above."

    return template.format(
        module_id=mod["id"],
        title_en=mod["title_en"],
        specialty=mod["specialty"],
        specialty_ru=mod["specialty_ru"],
        level=mod["level"],
        lessons_count=lcount,
        hours=mod["hours"],
        date=datetime.now().strftime("%Y-%m-%d"),
        lesson_range_note=note,
    )


def validate_module(data: dict, mod: dict) -> list[str]:
    """
    Structural and basic content quality check.
    Returns list of warning strings (empty = OK).
    Does NOT block saving — warnings are logged only.
    """
    issues: list[str] = []
    mtype = mod.get("type", "specialty")

    # Top-level structure
    if "meta" not in data:
        issues.append("Missing 'meta' key")
    if "lessons" not in data or not isinstance(data.get("lessons"), list):
        issues.append("Missing or empty 'lessons' list")
        return issues  # can't proceed without lessons

    lessons = data["lessons"]
    expected_min = max(3, mod["lessons"] - 1)
    if len(lessons) < expected_min:
        issues.append(f"Only {len(lessons)} lessons generated, expected ≥{expected_min}")

    AI_ARTIFACTS = [
        "as an ai", "i cannot", "i apologize", "i'm unable",
        "as a language model", "i don't have access",
        "please note that i", "i must clarify",
    ]

    for idx, lesson in enumerate(lessons):
        prefix = f"Lesson {idx+1}"
        content = lesson.get("content", {})

        intro = content.get("intro", "")
        if len(intro) < 100:
            issues.append(f"{prefix}: intro too short ({len(intro)} chars)")

        sections = content.get("sections", [])
        if len(sections) < 2:
            issues.append(f"{prefix}: only {len(sections)} sections (expected ≥2)")
        for si, sec in enumerate(sections):
            text = sec.get("text", "")
            if len(text) < 150:
                issues.append(f"{prefix} section {si+1}: text too short ({len(text)} chars)")
            # Detect AI self-reference artifacts
            tl = text.lower()
            for artifact in AI_ARTIFACTS:
                if artifact in tl:
                    issues.append(f"{prefix} section {si+1}: AI artifact found: '{artifact}'")
                    break

        key_points = content.get("key_points", [])
        if len(key_points) < 4:
            issues.append(f"{prefix}: only {len(key_points)} key_points (expected ≥4)")

        refs = content.get("references", [])
        if len(refs) < 1:
            issues.append(f"{prefix}: no references")

        if mtype == "patient_guide":
            if not content.get("questions_for_doctor"):
                issues.append(f"{prefix}: missing questions_for_doctor (patient guide)")

    return issues


def generate_module(mod: dict) -> dict:
    """Generate module, splitting large disease/patient-guide modules into 2 calls."""
    mtype = mod.get("type", "specialty")
    total = mod["lessons"]

    # Split large modules (disease + patient guide) into 2 calls to stay within TPM
    if mtype in ("disease", "patient_guide") and total > 4:
        half = total // 2
        # First half
        log(f"    → Part 1 (lessons 1–{half})")
        text1 = call_groq(build_prompt(mod, (1, half)))
        data1 = extract_json(text1)

        # Delay between the two parts
        log(f"    → Part 1 done. Waiting {INTER_CALL_DELAY}s before Part 2…")
        time.sleep(INTER_CALL_DELAY)

        # Second half
        log(f"    → Part 2 (lessons {half+1}–{total})")
        text2 = call_groq(build_prompt(mod, (half + 1, total)))
        data2 = extract_json(text2)

        # Merge
        base = len(data1.get("lessons", []))
        for i, lesson in enumerate(data2.get("lessons", [])):
            lesson["id"] = f"L{base + i + 1:03d}"
            lesson["order"] = base + i + 1
        data1["lessons"] = data1.get("lessons", []) + data2.get("lessons", [])
        data1["meta"]["duration_hours"] = mod["hours"]
        return data1

    text = call_groq(build_prompt(mod))
    return extract_json(text)


def module_done(mod: dict) -> bool:
    return (OUTPUT_DIR / f"module_{mod['id']}.json").exists()


def save_module(data: dict, mod_id: str) -> Path:
    path = OUTPUT_DIR / f"module_{mod_id}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


# ── Main queue ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="MedMind autonomous module queue")
    parser.add_argument("--type", choices=["specialty", "disease", "patient_guide", "all"], default="all")
    parser.add_argument("--filter", default="", help="Filter by ID prefix, e.g. PULM")
    parser.add_argument("--status", action="store_true", help="Show progress and exit")
    args = parser.parse_args()

    mods = ALL_MODULES
    if args.type == "specialty":
        mods = [m for m in mods if m.get("type") not in ("disease", "patient_guide")]
    elif args.type == "disease":
        mods = [m for m in mods if m.get("type") == "disease"]
    elif args.type == "patient_guide":
        mods = [m for m in mods if m.get("type") == "patient_guide"]
    if args.filter:
        mods = [m for m in mods if m["id"].startswith(args.filter.upper())]

    done = [m for m in mods if module_done(m)]
    todo = [m for m in mods if not module_done(m)]

    if args.status:
        print(f"\nTotal: {len(mods)} | Done: {len(done)} | Remaining: {len(todo)}")
        if todo:
            print("\nRemaining:")
            for m in todo:
                print(f"  {m['id']:25s}  {m['title_en'][:55]}")
        return

    log(f"{'='*60}")
    log(f"MedMind Module Queue started")
    log(f"Total: {len(mods)} | Done: {len(done)} | Remaining: {len(todo)}")
    log(f"Output: {OUTPUT_DIR}")
    log(f"Model: {GROQ_MODEL} | Key: ...{GROQ_KEY[-8:] if GROQ_KEY else 'NOT SET'}")
    log(f"Inter-call delay: {INTER_CALL_DELAY}s")
    log(f"{'='*60}")

    if not todo:
        log("All modules already generated!")
        return

    errors = []
    generated_this_run = 0
    for i, mod in enumerate(todo):
        mtype = mod.get("type", "specialty")
        tag = {"disease": "[DISEASE]", "patient_guide": "[PATIENT]"}.get(mtype, "[SPEC]   ")
        log(f"\n[{i+1}/{len(todo)}] {tag} {mod['id']} — {mod['title_en'][:55]}")

        try:
            data = generate_module(mod)
            n_lessons = len(data.get("lessons", []))
            # Validate content quality before saving
            issues = validate_module(data, mod)
            if issues:
                for w in issues:
                    log(f"  ⚠ QA: {w}")
            path = save_module(data, mod["id"])
            status = "✓" if not issues else "✓ (with warnings)"
            log(f"  {status} Saved {path.name} ({n_lessons} lessons, {len(issues)} QA warnings)")
            generated_this_run += 1
        except TPDLimitError as e:
            wait = parse_retry_seconds(str(e))
            resume_at = datetime.now() + timedelta(seconds=wait) if wait else None
            log(f"\n  ⛔ Daily token limit (TPD) reached on {mod['id']}.")
            if resume_at:
                log(f"     Groq resets at ~{resume_at.strftime('%Y-%m-%d %H:%M')} (local time).")
            log(f"     Generated this run: {generated_this_run} | Remaining: {len(todo)-i}")
            log(f"     Cron will resume automatically next run. Exiting.")
            log(f"{'='*60}")
            sys.exit(0)
        except json.JSONDecodeError as e:
            log(f"  ✗ JSON error: {e} — skipping")
            errors.append(mod["id"])
        except Exception as e:
            log(f"  ✗ Error: {e} — skipping")
            errors.append(mod["id"])

        if i < len(todo) - 1:
            log(f"  ⏳ Waiting {INTER_CALL_DELAY}s…")
            time.sleep(INTER_CALL_DELAY)

    done_final = generated_this_run
    log(f"\n{'='*60}")
    log(f"Queue complete. Generated: {done_final} | Errors: {len(errors)}")
    if errors:
        log(f"Failed: {', '.join(errors)}")
    log(f"Next: import to DB:")
    log(f"  docker exec medmind_backend python3 -m app.scripts.import_modules")
    log(f"{'='*60}")


if __name__ == "__main__":
    # Load .env if present (local dev)
    for env_path in [Path(__file__).parent.parent / ".env",
                     Path("/opt/medmind/backend/.env")]:
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())
            break
    main()
