"""
MedMind AI — Free Article Generator via Ollama (qwen3:1.7b)

Generates articles for high-demand medical topics using locally installed
Ollama, completely bypassing Claude API. No cost, runs overnight.

Speed:  qwen3:1.7b ~5 tok/s → ~2.5 min/article → 200 articles/night
Model:  qwen3:1.7b (default) | qwen3:8b (better quality, slower)

Topics: curated 300+ high-demand niches (common meds, symptoms, lifestyle)

Run overnight:
    nohup python3 generate_articles_ollama.py --limit 100 > /tmp/ollama_gen.log 2>&1 &

Dry-run:
    python3 generate_articles_ollama.py --dry-run --limit 5
"""
import asyncio
import json
import logging
import re
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from pathlib import Path
import sys
import argparse

import httpx
import psycopg2
from psycopg2.extras import Json

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

try:
    from fetch_article_image import fetch_cover_image as _fetch_cover_image
    _HAS_COVER = True
except ImportError:
    _HAS_COVER = False

try:
    from generate_og_image import generate_og_image as _gen_og_image
    _HAS_OG = True
except ImportError:
    _HAS_OG = False

# ── Config ─────────────────────────────────────────────────────────────────────
OLLAMA_URL  = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen3:1.7b"   # fast model ~2.5 min/article; use --model qwen3:8b for quality
DB_URL      = "postgresql://medmind:medmind_secret@localhost:5432/medmind"
LOCALES     = ["ru", "de", "fr", "es", "tr", "ar"]
DELAY       = 3.0             # seconds between articles
INDEXNOW_KEY = "b58fd85c39a0441e97c1587402e9c9df"

SCHEMA_MAP = {
    "cardiology": "MedicalCondition", "neurology": "MedicalCondition",
    "diseases": "MedicalCondition", "symptoms": "MedicalCondition",
    "pharmacology": "Drug", "drugs": "Drug",
    "procedures": "MedicalProcedure", "diagnostics": "MedicalProcedure",
    "emergency": "MedicalCondition", "surgery": "MedicalProcedure",
}

# ── High-demand topic list ─────────────────────────────────────────────────────
# Curated by search volume + gaps in current content (439 articles already exist)
TOPICS: dict[str, list[str]] = {

    "pharmacology": [
        # Most searched medications globally
        "Aspirin Mechanisms Clinical Uses and Side Effects",
        "Ibuprofen Pharmacology Dosing and Adverse Effects",
        "Paracetamol Acetaminophen Mechanism Dosing and Toxicity",
        "Omeprazole Proton Pump Inhibitors Clinical Applications",
        "Metformin Diabetes Management and Mechanisms",
        "Atorvastatin Cholesterol Management and Side Effects",
        "Lisinopril ACE Inhibitor Clinical Use and Monitoring",
        "Amoxicillin Antibiotic Spectrum and Clinical Use",
        "Azithromycin Z-Pack Indications and Resistance",
        "Warfarin Anticoagulation Monitoring and Interactions",
        "Levothyroxine Thyroid Replacement Therapy",
        "Sertraline SSRI Depression Anxiety Treatment",
        "Amlodipine Calcium Channel Blocker Hypertension",
        "Metoprolol Beta Blocker Uses and Contraindications",
        "Pantoprazole GERD Treatment and Long-term Use",
        "Furosemide Loop Diuretic Heart Failure Management",
        "Gabapentin Neuropathic Pain and Epilepsy",
        "Losartan ARB Hypertension Kidney Protection",
        "Doxycycline Antibiotic Spectrum and Indications",
        "Ciprofloxacin Fluoroquinolone Clinical Applications",
        "Hydrochlorothiazide Thiazide Diuretic Hypertension",
        "Clopidogrel Antiplatelet Therapy Cardiovascular",
        "Alprazolam Benzodiazepine Anxiety Short-term Use",
        "Metronidazole Antibiotic Anaerobic Infections",
        "Tramadol Opioid Analgesic Pain Management",
        "Insulin Types Regimens Diabetes Management",
        "Albuterol Salbutamol Asthma Rescue Inhaler",
        "Prednisone Oral Corticosteroid Indications",
        "Ondansetron Antiemetic Nausea Vomiting",
        "Cetirizine Antihistamine Allergy Treatment",
    ],

    "symptoms": [
        # Top symptom searches
        "Headache Causes Types and When to See a Doctor",
        "Chest Pain Differential Diagnosis and Red Flags",
        "Chronic Fatigue Causes Evaluation and Management",
        "Dizziness Vertigo Causes and Clinical Approach",
        "Shortness of Breath Dyspnea Causes and Workup",
        "Nausea and Vomiting Causes and Management",
        "Abdominal Pain Location-Based Differential Diagnosis",
        "Joint Pain Arthralgia Causes and Approach",
        "Back Pain Low Back Causes and Treatment",
        "Fever Pathophysiology Causes and Management",
        "Unexplained Weight Loss Causes and Evaluation",
        "Palpitations Causes Evaluation and Management",
        "Edema Peripheral Swelling Causes and Workup",
        "Hair Loss Alopecia Types and Treatment",
        "Memory Problems Cognitive Decline Assessment",
        "Insomnia Causes and Evidence-Based Treatment",
        "Chronic Cough Differential Diagnosis and Workup",
        "Skin Rash Differential Diagnosis Approach",
        "Night Sweats Causes and Clinical Evaluation",
        "Numbness Tingling Peripheral Neuropathy Approach",
    ],

    "diseases": [
        # High-volume common conditions
        "Hypertension Lifestyle Modification and Treatment",
        "Type 2 Diabetes Prevention and Lifestyle Management",
        "GERD Gastroesophageal Reflux Disease Management",
        "Irritable Bowel Syndrome Diagnosis and Treatment",
        "Obesity Clinical Management and Weight Loss",
        "Insomnia Sleep Disorder Treatment",
        "Erectile Dysfunction Causes and Treatment",
        "Benign Prostatic Hyperplasia Symptoms and Management",
        "Urinary Tract Infection Diagnosis and Antibiotic Treatment",
        "Common Cold Rhinovirus Symptoms and Management",
        "Influenza Flu Symptoms Antiviral Treatment Prevention",
        "Migraine with Aura Diagnosis and Preventive Treatment",
        "Tension Headache Chronic Management",
        "Fibromyalgia Diagnosis Criteria and Management",
        "Celiac Disease Gluten Intolerance Diagnosis",
        "Lactose Intolerance Pathophysiology and Diet",
        "Kidney Stones Nephrolithiasis Types and Prevention",
        "Hemorrhoids Causes Treatment and Prevention",
        "Varicose Veins Pathophysiology and Management",
        "Thyroid Nodule Evaluation and Management",
        "Sinusitis Acute and Chronic Management",
        "Otitis Media Ear Infection Children Adults",
        "Plantar Fasciitis Heel Pain Treatment",
        "Carpal Tunnel Syndrome Conservative Treatment",
        "Shingles Herpes Zoster Antiviral Treatment",
    ],

    "nutrition": [
        # Most searched nutrition topics
        "Mediterranean Diet Health Benefits Evidence",
        "Vitamin D Deficiency Symptoms and Supplementation",
        "Vitamin B12 Deficiency Vegetarians and Elderly",
        "Iron Deficiency Symptoms Food Sources Supplementation",
        "Omega-3 Fatty Acids Health Benefits Dosing",
        "Magnesium Deficiency Symptoms and Foods",
        "Zinc Deficiency Immune Function Supplementation",
        "Intermittent Fasting Health Effects Evidence",
        "Protein Requirements Athletes Elderly",
        "Glycemic Index Diabetes Blood Sugar Management",
        "Anti-Inflammatory Diet Foods and Benefits",
        "Gut Microbiome Diet Probiotics Health",
        "Caffeine Effects on Health Recommended Limits",
        "Alcohol Health Effects Recommended Limits",
        "Hydration Water Intake Recommendations",
        "Calcium Osteoporosis Prevention Supplementation",
        "Folic Acid Pregnancy Neural Tube Defects",
        "Sugar Intake Health Effects Recommendations",
    ],

    "psychiatry": [
        # Mental health high demand
        "Depression Diagnosis Criteria and Treatment Options",
        "Generalized Anxiety Disorder CBT Medication",
        "Panic Attacks Recognition and Management",
        "Social Anxiety Disorder Treatment Approaches",
        "PTSD Recognition and Evidence-Based Treatment",
        "Burnout Syndrome Diagnosis and Recovery",
        "Stress Management Evidence-Based Techniques",
        "Sleep Hygiene Improving Sleep Quality",
        "Seasonal Affective Disorder Light Therapy",
        "Grief and Bereavement Normal vs Complicated",
        "Addiction Recognition and Treatment Principles",
        "ADHD Adult Diagnosis and Management",
        "Phobias Types and Exposure Therapy",
        "Mindfulness Meditation Evidence in Medicine",
        "Loneliness Health Effects and Interventions",
    ],

    "diagnostics": [
        # Common tests patients ask about
        "Complete Blood Count CBC Interpretation Guide",
        "Basic Metabolic Panel Interpretation",
        "Thyroid Function Tests TSH T3 T4 Interpretation",
        "Lipid Panel Cholesterol Results Interpretation",
        "HbA1c Glycated Hemoglobin Diabetes Monitoring",
        "Urinalysis Interpretation Clinical Guide",
        "Chest X-Ray Basic Interpretation ABCDE",
        "ECG Normal and Abnormal Patterns Basics",
        "Blood Pressure Monitoring Home Measurement",
        "BMI Body Mass Index Limitations and Use",
        "INR Monitoring Warfarin Anticoagulation",
        "PSA Prostate Specific Antigen Screening",
        "D-Dimer Test PE DVT Clinical Utility",
        "CRP Inflammation Marker Clinical Use",
        "Ferritin Iron Studies Interpretation",
    ],

    "procedures": [
        # Common procedures patients research
        "Colonoscopy Preparation What to Expect",
        "Endoscopy Upper GI Indications Preparation",
        "Cardiac Catheterization Procedure Patient Guide",
        "Biopsy Types Indications What to Expect",
        "MRI Scan Indications Contraindications Preparation",
        "CT Scan Radiation Risk Indications",
        "Lumbar Puncture Spinal Tap Procedure Guide",
        "Blood Transfusion Indications Complications",
        "Vaccination Schedule Adults Recommended Vaccines",
        "CPR Cardiopulmonary Resuscitation Technique",
        "Heimlich Maneuver Choking First Aid",
        "Wound Care First Aid Principles",
        "Defibrillation AED Use in Cardiac Arrest",
    ],

    "internal-medicine": [
        # High-demand internal medicine topics
        "High Cholesterol Hyperlipidemia Lifestyle Treatment",
        "Prediabetes Diagnosis and Reversal Strategies",
        "Metabolic Syndrome Criteria and Management",
        "Non-Alcoholic Fatty Liver Disease NAFLD Management",
        "Chronic Kidney Disease Diet and Lifestyle",
        "Gout Diet Uric Acid Management",
        "Osteoporosis Prevention Calcium Vitamin D Exercise",
        "Anemia Types Causes Iron B12 Folate",
        "Blood Clots DVT Prevention Risk Factors",
        "Autoimmune Disease Overview Mechanisms",
        "Sleep Apnea Diagnosis CPAP Treatment",
        "Chronic Pain Management Multidisciplinary Approach",
        "Hypertension White Coat and Masked Hypertension",
        "Preventive Health Screenings by Age",
        "Travel Medicine Vaccines and Precautions",
    ],

    "emergency": [
        # First aid and emergency recognition
        "Heart Attack Warning Signs First Response",
        "Stroke Recognition FAST Acronym Management",
        "Anaphylaxis Recognition Epinephrine Use",
        "Hypoglycemia Recognition and Treatment Steps",
        "Seizure First Aid and When to Call 911",
        "Syncope Fainting Causes and First Aid",
        "Asthma Attack Inhaler Use Emergency Steps",
        "Carbon Monoxide Poisoning Recognition Treatment",
        "Drug Overdose Recognition and First Response",
        "Head Injury Concussion Recognition and Monitoring",
    ],

    "geriatrics": [
        # Aging and elderly care
        "Healthy Aging Principles Evidence-Based Lifestyle",
        "Dementia Early Signs and Diagnosis Approach",
        "Fall Prevention Elderly Risk Assessment",
        "Polypharmacy Medication Review in Elderly",
        "Osteoporosis Fracture Prevention in Elderly",
        "Urinary Incontinence Treatment in Elderly",
        "Depression in Elderly Recognition and Treatment",
        "Hearing Loss Age-Related Management",
        "Cataracts Age-Related Eye Changes",
        "Frailty Syndrome Assessment and Intervention",
    ],

    "ob-gyn": [
        # Women's health high demand
        "Menstrual Irregularities Causes and Evaluation",
        "Premenstrual Syndrome PMS Management",
        "Polycystic Ovary Syndrome PCOS Lifestyle Treatment",
        "Endometriosis Symptoms Diagnosis and Treatment",
        "Menopause Symptoms Hormone Therapy Options",
        "Fertility Basics When to Seek Help",
        "Contraception Methods Comparison Effectiveness",
        "Prenatal Vitamins Pregnancy Nutrition",
        "Morning Sickness Nausea Pregnancy Management",
        "Postpartum Depression Recognition and Treatment",
        "Pelvic Floor Exercises Kegel Benefits",
        "Cervical Cancer Prevention HPV Vaccine Pap Smear",
        "Breast Self-Examination Cancer Awareness",
        "UTI in Women Prevention and Treatment",
        "Vaginal Yeast Infection Treatment Prevention",
    ],

    # ── Wave 2: High-Search-Volume Specialty Topics ────────────────────────────

    "cardiology": [
        "Atrial Fibrillation Diagnosis Risk Stratification and Management",
        "Heart Failure with Reduced Ejection Fraction HFrEF Treatment",
        "Acute Myocardial Infarction STEMI Management and Reperfusion",
        "Coronary Artery Disease Prevention and Medical Management",
        "Hypertensive Crisis Urgency versus Emergency Management",
        "Aortic Stenosis Valvular Disease Assessment and TAVR",
        "Pericarditis Diagnosis Colchicine Treatment and Recurrence",
        "Myocarditis Clinical Presentation Diagnosis and Management",
        "Pulmonary Hypertension Classification and Targeted Therapy",
        "Ventricular Tachycardia Recognition and Emergency Management",
        "Supraventricular Tachycardia SVT Vagal Maneuvers and Adenosine",
        "Infective Endocarditis Diagnosis Antibiotic Treatment Prophylaxis",
        "Abdominal Aortic Aneurysm Screening Monitoring Surgical Repair",
        "Peripheral Arterial Disease Ankle-Brachial Index and Revascularization",
        "Deep Vein Thrombosis Diagnosis Anticoagulation Prevention",
        "Heart Failure with Preserved Ejection Fraction HFpEF Management",
        "Cardiac Rehabilitation After Myocardial Infarction Evidence and Benefits",
        "Sudden Cardiac Death Risk Factors ICD Implantation Prevention",
        "Stable and Unstable Angina Pectoris Medical Management",
        "SGLT2 Inhibitors Heart Failure Cardiovascular Outcomes Evidence",
        "Hypertriglyceridemia Cardiovascular Risk and Management",
        "Arrhythmia Classification ECG Recognition and Management",
        "Cardiogenic Shock Recognition Inotropes Mechanical Circulatory Support",
    ],

    "neurology": [
        "Acute Ischemic Stroke tPA Thrombectomy Time Windows",
        "Alzheimer Disease Pathophysiology Early Detection and New Treatments",
        "Parkinson Disease Motor Non-Motor Symptoms Levodopa Treatment",
        "Epilepsy Classification Antiseizure Drug Selection Monitoring",
        "Multiple Sclerosis Disease-Modifying Therapies Relapse Management",
        "Migraine Prophylaxis CGRP Inhibitors Acute Treatment Options",
        "Peripheral Neuropathy Etiology Workup Symptomatic Treatment",
        "Guillain-Barre Syndrome IVIG Plasma Exchange Clinical Management",
        "Bacterial Meningitis CSF Analysis Empiric Antibiotics Dexamethasone",
        "Bell Palsy Diagnosis Corticosteroid Therapy Facial Nerve Recovery",
        "Benign Paroxysmal Positional Vertigo Epley Maneuver Diagnosis",
        "Essential Tremor Diagnosis versus Parkinsonism Treatment Options",
        "Tension-Type Headache Chronic Management and Prevention",
        "Transient Ischemic Attack TIA Workup and Stroke Prevention",
        "Dementia with Lewy Bodies Clinical Features and Management",
        "Amyotrophic Lateral Sclerosis ALS Riluzole Palliative Care",
        "Myasthenia Gravis Acetylcholine Receptor Antibodies Pyridostigmine",
        "Restless Legs Syndrome Diagnostic Criteria Dopamine Agonists",
        "Diabetic Peripheral Neuropathy Pain Management Gabapentin Duloxetine",
        "Concussion Traumatic Brain Injury Return-to-Play Protocol",
        "Idiopathic Intracranial Hypertension Papilledema Acetazolamide",
        "Cervical Myelopathy Spondylosis Diagnosis Surgical Decompression",
    ],

    "dermatology": [
        "Atopic Dermatitis Pathogenesis Dupilumab JAK Inhibitor Therapy",
        "Psoriasis Vulgaris Biologics IL-17 IL-23 Inhibitor Comparison",
        "Acne Vulgaris Treatment Ladder Retinoids Antibiotics Isotretinoin",
        "Melanoma ABCDE Criteria Staging Immunotherapy BRAF Inhibitors",
        "Basal Cell Carcinoma Recognition Mohs Surgery Prevention",
        "Squamous Cell Carcinoma Skin High-Risk Features Surgical Management",
        "Rosacea Subtypes Topical Metronidazole Azelaic Acid Laser Therapy",
        "Seborrheic Dermatitis Scalp Face Ketoconazole Zinc Pyrithione",
        "Contact Dermatitis Allergic versus Irritant Patch Testing Management",
        "Chronic Urticaria Antihistamines Omalizumab Management",
        "Tinea Infections Dermatophytosis Topical Oral Antifungal Treatment",
        "Scabies Diagnosis Permethrin Treatment Household Contacts",
        "Herpes Simplex Skin Manifestations Acyclovir Antiviral Therapy",
        "Herpes Zoster Shingles Antiviral Treatment Postherpetic Neuralgia",
        "Alopecia Areata Autoimmune Hair Loss JAK Inhibitor Baricitinib",
        "Androgenetic Alopecia Male Female Pattern Baldness Treatment",
        "Hidradenitis Suppurativa Severity Classification Biologic Treatment",
        "Warts Verruca Vulgaris Salicylic Acid Cryotherapy Options",
        "Cellulitis Skin Infection Antibiotic Therapy Complications",
        "Lichen Planus Oral Cutaneous Diagnosis Corticosteroid Treatment",
        "Drug-Induced Skin Reactions Maculopapular SJS TEN Recognition",
        "Sunscreen UV Protection SPF Skin Cancer Prevention Evidence",
    ],

    "oncology": [
        "Breast Cancer Staging Hormone Receptor HER2 Treatment Decisions",
        "Lung Cancer Screening Low-Dose CT NSCLC SCLC Treatment",
        "Colorectal Cancer Colonoscopy Screening Staging Chemotherapy",
        "Prostate Cancer PSA Screening Gleason Score Active Surveillance",
        "Cervical Cancer HPV Vaccination Pap Smear Colposcopy Conization",
        "Ovarian Cancer BRCA Testing Chemotherapy Bevacizumab PARP Inhibitors",
        "Pancreatic Cancer Early Detection Gemcitabine FOLFIRINOX Palliative",
        "Hepatocellular Carcinoma Cirrhosis Surveillance Sorafenib Atezolizumab",
        "Gastric Cancer H pylori Surgical and Systemic Treatment",
        "Thyroid Cancer Differentiated Papillary Follicular Radioiodine Therapy",
        "Lymphoma Hodgkin Non-Hodgkin Staging CHOP Chemotherapy",
        "Leukemia CML CLL AML Classification Targeted Therapy Imatinib",
        "Multiple Myeloma Bortezomib Lenalidomide Stem Cell Transplantation",
        "Advanced Melanoma BRAF V600E Mutation Immunotherapy Nivolumab",
        "Immunotherapy Checkpoint Inhibitors PD-1 CTLA-4 Immune Toxicities",
        "Cancer Pain Management WHO Analgesic Ladder Opioid Titration",
        "Chemotherapy Side Effects Nausea Neutropenia Neuropathy Management",
        "Cancer Screening Guidelines USPSTF Mammography Colonoscopy Lung CT",
        "Tumor Markers Clinical Use CEA CA-125 AFP PSA Interpretation",
        "Palliative Care Goals of Care Symptom Control End of Life",
        "Bone Metastases Pain Bisphosphonates Radiation Denosumab",
        "Febrile Neutropenia Management Empiric Antibiotics G-CSF Protocol",
    ],

    "infectious-diseases": [
        "Community-Acquired Pneumonia CURB-65 Antibiotic Duration Admission",
        "Urinary Tract Infection Uncomplicated Complicated Antibiotic Treatment",
        "Sepsis Surviving Sepsis Campaign Antibiotic Stewardship Hour-1 Bundle",
        "HIV Antiretroviral Therapy Drug Resistance Opportunistic Infections",
        "Tuberculosis Diagnosis Rifampin Isoniazid Drug-Resistant MDR-TB",
        "Hepatitis B Surface Antigen Vaccination Tenofovir Antiviral Treatment",
        "Hepatitis C Direct-Acting Antivirals Sofosbuvir Sustained Virologic Response",
        "Post-Acute COVID-19 Sequelae Long COVID Pathophysiology Management",
        "Lyme Disease Diagnosis Doxycycline Stages Chronic Lyme Controversy",
        "Influenza Oseltamivir Timing High-Risk Populations Vaccination",
        "Sexually Transmitted Infections Gonorrhea Chlamydia Syphilis Treatment",
        "Clostridioides difficile Colitis Vancomycin Fidaxomicin Fecal Transplant",
        "Necrotizing Fasciitis versus Cellulitis Surgical Emergency Antibiotics",
        "Meningococcal Disease Prophylaxis Ciprofloxacin Vaccination",
        "Malaria Chemoprophylaxis Chloroquine Artemisinin Combination Therapy",
        "Invasive Candidiasis Fluconazole Echinocandin Candidemia Management",
        "Adult Vaccination Schedule Tetanus Shingles Pneumococcal Influenza",
        "Travel Medicine Pre-Travel Vaccines Malaria Prophylaxis Diarrhea",
        "MRSA Methicillin-Resistant S aureus Vancomycin Daptomycin Treatment",
        "Opportunistic Infections HIV CD4 Count PCP MAC CMV Prophylaxis",
        "Food-Borne Illness Salmonella Campylobacter E coli Dehydration",
        "Respiratory Syncytial Virus Adults Elderly Nirsevimab Prevention",
    ],

    "endocrinology": [
        "Hypothyroidism TSH Target Levothyroxine Dosing Monitoring",
        "Hyperthyroidism Graves Disease Methimazole Radioactive Iodine Beta-Blocker",
        "Type 2 Diabetes GLP-1 SGLT2 Metformin Treatment Algorithm 2024",
        "Diabetic Ketoacidosis Pathophysiology Fluid Insulin Bicarbonate Protocol",
        "Thyroid Nodule Fine-Needle Aspiration Bethesda Classification Surveillance",
        "Subclinical Hypothyroidism Treatment Thresholds Evidence Review",
        "Hashimoto Thyroiditis Autoimmune Antibodies and Hypothyroidism",
        "Adrenal Insufficiency Primary Secondary ACTH Stimulation Cortisol Replacement",
        "Cushing Syndrome Hypercortisolism Screening Tests Surgical Treatment",
        "Primary Hyperaldosteronism Conn Syndrome Adrenal Venous Sampling",
        "Pheochromocytoma Catecholamine Excess Preoperative Alpha-Blockade Surgery",
        "Type 1 Diabetes Insulin Pumps Continuous Glucose Monitoring Targets",
        "Gestational Diabetes Screening Glyburide versus Insulin Outcomes",
        "Hypoglycemia Causes Symptoms Glucagon Treatment Unawareness",
        "Hyperprolactinemia Prolactinoma Cabergoline Dopamine Agonists",
        "Acromegaly Growth Hormone Excess IGF-1 Octreotide Surgery",
        "Vitamin D Deficiency Bone Health Supplementation Dosing Evidence",
        "Hypercalcemia Causes Primary Hyperparathyroidism Malignancy Management",
        "Metabolic Syndrome Insulin Resistance Waist Circumference Criteria",
        "Obesity GLP-1 Receptor Agonists Semaglutide Bariatric Surgery",
        "Thyroid Storm Life-Threatening Emergency Beta-Blockers Thionamides",
        "Adrenal Incidentaloma Workup Biochemical Testing Surveillance",
    ],

    "pediatrics": [
        "Fever in Children Age-Based Evaluation Temperature Management Referral",
        "Acute Otitis Media Antibiotic Selection Watchful Waiting Tubes",
        "Febrile Seizures Simple versus Complex Evaluation Management",
        "Bronchiolitis RSV Supportive Care Hospitalization Criteria",
        "Croup Laryngotracheobronchitis Dexamethasone Nebulized Racemic Epinephrine",
        "Childhood Asthma Step Therapy Controller Rescue Medications Monitoring",
        "ADHD Diagnostic Criteria Methylphenidate Amphetamine Behavioral Therapy",
        "Autism Spectrum Disorder M-CHAT Screening Early Intervention",
        "Childhood Vaccination Schedule MMR Varicella DTaP PCV Timing",
        "Streptococcal Pharyngitis Rapid Antigen Test Amoxicillin Complications",
        "Acute Gastroenteritis Dehydration Assessment Oral Rehydration Therapy",
        "Kawasaki Disease Diagnostic Criteria IVIG Aspirin Coronary Aneurysms",
        "Neonatal Jaundice Hyperbilirubinemia Phototherapy Exchange Transfusion",
        "Failure to Thrive Organic Non-Organic Causes Nutritional Workup",
        "Developmental Milestones Red Flags Ages and Stages Screening Tools",
        "Pediatric UTI Vesicoureteral Reflux DMSA Scan Prophylaxis",
        "Childhood Obesity BMI Percentiles Lifestyle Intervention",
        "Iron Deficiency Anemia Children Lead Screening Oral Iron",
        "Pediatric Appendicitis Alvarado Score Ultrasound CT Diagnosis",
        "Type 1 Diabetes Children Insulin Regimens HbA1c Targets",
        "Intussusception Colicky Pain Currant Jelly Stool Air Enema",
        "Breath-Holding Spells versus Seizures Parental Reassurance",
    ],

    "rheumatology": [
        "Rheumatoid Arthritis Early DMARD Methotrexate Biologic Treat-to-Target",
        "Systemic Lupus Erythematosus ACR-EULAR Criteria Organ Manifestations",
        "Gout Hyperuricemia Acute Attack Colchicine Allopurinol Urate Targets",
        "Osteoarthritis Pathophysiology NSAIDs Corticosteroid Hyaluronic Injections",
        "Psoriatic Arthritis Skin Joint Manifestations TNF IL-17 Inhibitors",
        "Ankylosing Spondylitis HLA-B27 NSAIDs TNF Inhibitors Secukinumab",
        "Sjögren Syndrome Dry Eyes Dry Mouth Extraglandular Manifestations",
        "Fibromyalgia Diagnostic Criteria Multidisciplinary Treatment CBT Exercise",
        "Polymyalgia Rheumatica Prednisone Response ESR CRP Monitoring",
        "Giant Cell Arteritis Temporal Arteritis Vision Loss Steroid Treatment",
        "ANCA-Associated Vasculitis Cyclophosphamide Rituximab Induction",
        "Antiphospholipid Syndrome Thrombosis Pregnancy Loss Anticoagulation",
        "Reactive Arthritis Post-Infectious Chlamydia Salmonella NSAIDs",
        "Pseudogout CPPD Crystal Deposition Joint Aspiration Treatment",
        "Septic Arthritis Joint Aspiration Culture Empiric Antibiotics",
        "Lupus Nephritis Kidney Biopsy WHO Classification Mycophenolate",
        "Systemic Sclerosis Scleroderma Pulmonary Fibrosis Bosentan",
        "Inflammatory Myopathies Dermatomyositis Polymyositis Creatine Kinase",
        "Raynaud Phenomenon Primary Secondary Calcium Channel Blockers",
        "Juvenile Idiopathic Arthritis Subtypes Methotrexate Biologic Therapy",
        "Relapsing Polychondritis Cartilage Destruction Dapsone Steroids",
        "Behçet Disease Mucosal Ulcers Colchicine Azathioprine Management",
    ],

    "pulmonology": [
        "COPD GOLD Staging Bronchodilators Exacerbation Prevention Vaccines",
        "Asthma Step-Up Step-Down Therapy ICS LABA Spirometry Monitoring",
        "Community-Acquired Pneumonia Antibiotic Duration Admission Criteria",
        "Pulmonary Embolism Wells Score CT Pulmonary Angiography DOAC Treatment",
        "Idiopathic Pulmonary Fibrosis Antifibrotics Pirfenidone Nintedanib",
        "Obstructive Sleep Apnea CPAP Pressure Titration Cardiovascular Risk",
        "Spontaneous Pneumothorax Diagnosis Chest Tube VATS Management",
        "Pleural Effusion Transudates Exudates Light Criteria Thoracentesis",
        "Lung Cancer Low-Dose CT Screening NSCLC SCLC Immunotherapy",
        "Sarcoidosis Pulmonary Extrapulmonary Corticosteroid Indications",
        "Acute Exacerbation COPD Triggers Antibiotics Steroids NIV",
        "Bronchiectasis Causes Airway Clearance Physiotherapy Antibiotics",
        "Interstitial Lung Disease Classification HRCT Biopsy Treatment",
        "Pulmonary Arterial Hypertension Right Heart Catheterization Prostanoids",
        "Cystic Fibrosis CFTR Modulators Elexacaftor Tezacaftor Ivacaftor",
        "ARDS Berlin Definition Lung-Protective Ventilation Prone Positioning",
        "Hypersensitivity Pneumonitis Allergen Avoidance Corticosteroid",
        "Alpha-1 Antitrypsin Deficiency Early-Onset Emphysema Pi ZZ Testing",
        "Hemoptysis Causes Evaluation Bronchoscopy CT Angiography Management",
        "Aspiration Pneumonia Risk Factors Anaerobic Coverage Management",
        "Occupational Lung Diseases Asbestosis Silicosis Workers Compensation",
        "Non-Invasive Ventilation BiPAP CPAP Indications COPD Heart Failure",
    ],

    "nephrology": [
        "Acute Kidney Injury KDIGO Stages Prerenal Intrinsic Postrenal Management",
        "Chronic Kidney Disease GFR Stages Progression Monitoring SGLT2",
        "Diabetic Nephropathy Albuminuria ACE Inhibitor ARB Glycemic Control",
        "IgA Nephropathy Oxford Classification Supportive RAAS Treatment",
        "Nephrotic Syndrome Minimal Change Membranous Causes Treatment",
        "Nephritic Syndrome Hematuria Complement IgA ANCA Workup",
        "Autosomal Dominant Polycystic Kidney Disease Tolvaptan Genetics",
        "Calcium Oxalate Kidney Stones Prevention Thiazide Citrate Diet",
        "Hypertensive Nephrosclerosis Blood Pressure Targets Progression",
        "Glomerulonephritis Rapidly Progressive Crescentic Kidney Biopsy",
        "Acute Tubular Necrosis Contrast-Induced Nephropathy Prevention",
        "Hemodialysis Access AV Fistula Graft Catheter Adequacy",
        "Kidney Transplantation Rejection Types Tacrolimus Immunosuppression",
        "Drug Dosing in Renal Failure Creatinine Clearance Cockcroft-Gault",
        "Hyperkalemia Emergency Treatment Calcium Kayexalate Patiromer",
        "Metabolic Acidosis Anion Gap Non-Anion Gap Bicarbonate Correction",
        "Hyponatremia SIADH Correction Rate Osmotic Demyelination",
        "Rhabdomyolysis Myoglobinuria AKI Prevention Fluid Resuscitation",
        "SGLT2 Inhibitors CKD Cardiovascular Renal Protection Outcomes",
        "Electrolyte Imbalances ICU Management Monitoring Replacement",
    ],

    "ophthalmology": [
        "Age-Related Macular Degeneration Dry Wet Anti-VEGF Ranibizumab",
        "Primary Open-Angle Glaucoma Tonometry Optic Disc Topical Medications",
        "Cataracts Age-Related Phacoemulsification IOL Types Selection",
        "Diabetic Retinopathy Screening Intervals Laser Ranibizumab Aflibercept",
        "Dry Eye Disease Meibomian Gland Cyclosporine Lifitegrast Treatment",
        "Acute Angle-Closure Glaucoma Emergency Pilocarpine Laser Iridotomy",
        "Rhegmatogenous Retinal Detachment Symptoms Surgery Outcomes",
        "Conjunctivitis Bacterial Viral Allergic Differential Diagnosis Treatment",
        "Anterior Uveitis Causes Corticosteroid Cycloplegic Management",
        "Central Retinal Artery Occlusion Stroke Equivalent Urgent Workup",
        "Optic Neuritis Multiple Sclerosis MRI Association IV Steroids",
        "Myopia Progressive Control Atropine Orthokeratology Myopia Progression",
        "Corneal Ulcer Bacterial Fungal Acanthamoeba Topical Antibiotics",
        "Strabismus Amblyopia Patching Atropine Surgery Timing",
        "Herpes Zoster Ophthalmicus Hutchinson Sign Antiviral Treatment",
        "Orbital Cellulitis Periorbital Preseptal CT Scan IV Antibiotics",
        "Floaters Posterior Vitreous Detachment Retinal Tear Emergency Signs",
        "Blepharitis Anterior Posterior Lid Scrubs Antibiotic Drops",
        "Papilledema Optic Disc Swelling Raised ICP Intracranial Causes",
        "Glaucoma Normal Tension Optic Nerve Damage Treatment Controversy",
    ],

    "orthopedics": [
        "Low Back Pain Red Flags Imaging Indications Conservative Management",
        "Knee Osteoarthritis NSAIDs Corticosteroid Hyaluronic Total Knee Arthroplasty",
        "ACL Tear Mechanism MRI Reconstruction Rehabilitation Return to Sport",
        "Rotator Cuff Tear MRI Findings Conservative versus Surgical Decision",
        "Meniscus Tear Degenerative Traumatic Repair versus Meniscectomy",
        "Osteoporosis DEXA Scan FRAX Score Bisphosphonates Fracture Prevention",
        "Hip Fracture Elderly 30-Day Mortality Surgical Repair Rehabilitation",
        "Frozen Shoulder Adhesive Capsulitis Stages Physiotherapy Manipulation",
        "Lateral Epicondylitis Tennis Elbow Eccentric Loading Steroid Injection",
        "Carpal Tunnel Syndrome Tinel Phalen Signs Night Splint Surgery",
        "Plantar Fasciitis Heel Pain Conservative Management Corticosteroid PRP",
        "Ankle Sprain Grade Classification RICE PRICE Proprioception Rehab",
        "Patellofemoral Pain Syndrome Runner Knee Quadriceps Strengthening",
        "Compartment Syndrome Acute Fasciotomy Pressure Measurement Emergency",
        "Lumbar Spinal Stenosis Claudication Epidural Injection Decompression",
        "Sciatica L4 L5 S1 Radiculopathy Conservative versus Surgical Treatment",
        "Adolescent Idiopathic Scoliosis Cobb Angle Bracing Surgery Criteria",
        "Shoulder Anterior Dislocation Bankart Reduction Immobilization Surgery",
        "Gout Acute Arthritis Colchicine NSAIDs Steroids Urate Lowering",
        "Stress Fracture Runners Bone Scan MRI Return-to-Activity Protocol",
        "Achilles Tendinopathy Eccentric Loading PRP Injection Surgical",
        "Developmental Dysplasia Hip Pavlik Harness Closed Open Reduction",
    ],

    "urology": [
        "Benign Prostatic Hyperplasia Alpha-Blockers 5-Alpha Reductase Inhibitors TURP",
        "Prostate Cancer Active Surveillance Radical Prostatectomy Radiation Therapy",
        "Erectile Dysfunction PDE5 Inhibitors Sildenafil Tadalafil Vacuum Device",
        "Nephrolithiasis ESWL Ureteroscopy Metabolic Workup Dietary Prevention",
        "Urinary Incontinence Stress Urge Mixed Pelvic Floor Anticholinergics",
        "Recurrent UTI Women Prophylaxis Nitrofurantoin Trimethoprim Cranberry",
        "Bladder Cancer Transitional Cell TURBT BCG Intravesical Immunotherapy",
        "Testicular Cancer Orchiectomy Retroperitoneal LND Cisplatin Chemotherapy",
        "Hematuria Gross Microscopic Cystoscopy CT Urogram Differential Causes",
        "Overactive Bladder Mirabegron Botulinum Toxin Posterior Tibial Nerve",
        "Renal Cell Carcinoma Partial versus Radical Nephrectomy Immunotherapy",
        "Male Infertility Semen Analysis Varicocele Assisted Reproduction",
        "Acute Urinary Retention Catheterization TWOC Alpha-Blocker Treatment",
        "Prostatitis Acute Bacterial Chronic Pelvic Pain Antibiotics Treatment",
        "Testicular Torsion Emergency Detorsion Blue Dot Sign Bilateral Fixation",
        "Pelvic Floor Dysfunction Dyssynergia Biofeedback Management",
        "Interstitial Cystitis Bladder Pain Syndrome Pentosan Polysulfate",
        "Vesicoureteral Reflux Grades Continuous Antibiotic Prophylaxis Surgery",
        "Nocturia Causes Desmopressin Sleep Quality Management",
        "Neurogenic Bladder Spinal Cord Injury CIC Anticholinergics Management",
    ],

    "hematology": [
        "Iron Deficiency Anemia Oral IV Iron Supplementation Transfusion Criteria",
        "Vitamin B12 Deficiency Pernicious Anemia Intrinsic Factor IM Injections",
        "Anemia of Chronic Disease Hepcidin Erythropoiesis-Stimulating Agents",
        "Sickle Cell Disease Vaso-Occlusive Crisis Hydroxyurea Exchange Transfusion",
        "Thalassemia Alpha Beta Classification Transfusion Chelation Gene Therapy",
        "Immune Thrombocytopenic Purpura ITP Steroids IVIG Eltrombopag",
        "Deep Vein Thrombosis Anticoagulation Duration Wells Score Compression",
        "Massive Pulmonary Embolism Risk Stratification Thrombolysis Embolectomy",
        "Hemophilia A Factor VIII Replacement Prophylaxis Inhibitor Development",
        "Disseminated Intravascular Coagulation DIC Sepsis Fibrinogen FFP",
        "Anticoagulation Warfarin versus DOACs Reversal Agents Drug Interactions",
        "Febrile Neutropenia Risk Stratification MASCC Score Antibiotic Protocol",
        "Polycythemia Vera JAK2 V617F Mutation Phlebotomy Hydroxyurea Ruxolitinib",
        "Heparin-Induced Thrombocytopenia HIT Platelet Factor 4 Argatroban",
        "Leukocytosis Left Shift Reactive versus Leukemia Differential Diagnosis",
        "Splenomegaly Causes Hypersplenism Diagnostic Workup",
        "Inherited Thrombophilias Factor V Leiden Prothrombin Mutation Testing",
        "Antiphospholipid Antibody Syndrome Triple Positive Catastrophic APS",
        "Myelodysplastic Syndrome Bone Marrow Failure Azacitidine Transplantation",
        "Lymphocytosis Differential Diagnosis CLL Viral EBV CMV Reactive",
    ],
}


# ── Google Translate ───────────────────────────────────────────────────────────

def gtranslate(text: str, locale: str) -> str:
    if not text or not text.strip():
        return text
    try:
        url = (
            "https://translate.googleapis.com/translate_a/single"
            "?client=gtx&sl=en&tl=" + locale
            + "&dt=t&q=" + urllib.parse.quote(text[:4500])
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read())
        return "".join(p[0] for p in data[0] if p[0])
    except Exception:
        return text


def translate_blocks(blocks: list, locale: str) -> list:
    result = []
    for block in blocks:
        btype = block.get("type", "")
        nb = dict(block)
        if btype in ("h2", "h3", "p", "callout"):
            if block.get("content"):
                nb["content"] = gtranslate(block["content"], locale)
                time.sleep(0.2)
        elif btype == "ul":
            nb["items"] = [gtranslate(it, locale) for it in block.get("items", [])]
            time.sleep(0.15)
        result.append(nb)
    return result


# ── Ollama generation ──────────────────────────────────────────────────────────

ARTICLE_PROMPT = """\
You are a senior clinician writing an authoritative medical reference, comparable to UpToDate or StatPearls. Audience: medical students, residents, and practicing physicians who need actionable clinical information.

Topic: {topic}
Category: {category}

Write a COMPREHENSIVE, AUTHORITATIVE article of 3000-3500 words. Include SPECIFIC clinical details: exact drug doses, diagnostic criteria with numbers, lab thresholds, staging systems, guideline recommendations (AHA/ACC/ESC/WHO/NICE), and evidence-based management algorithms.

Use EXACTLY this output format with the markers below:

TITLE: [Clinical title, max 85 characters]
EXCERPT: [3 sentences: clinical significance, key mechanism, main management approach]
ARTICLE_START

## Key Points
List 7-9 critical clinical facts as bullet points ("- " prefix). Each: one specific fact with numbers/doses/criteria.
- Example: Atrial fibrillation affects 33 million people worldwide; prevalence doubles each decade after age 55
- Example: Rate control target: resting HR < 80 bpm; rhythm control preferred in symptomatic or newly diagnosed AF < 1 year

## Overview and Epidemiology
Definition, incidence/prevalence, affected populations, demographics, major risk factors. (250-300 words)

## Pathophysiology
Underlying mechanisms, molecular and cellular basis, disease progression, why symptoms occur. (300-400 words)

## Clinical Presentation
Symptoms, physical signs, typical vs atypical presentations, red flags requiring urgent attention. (250-300 words)

## Diagnosis
Diagnostic criteria with SPECIFIC values, laboratory workup, imaging findings, differential diagnosis, validated scoring systems (Wells score, CURB-65, CHADS2-VASc, etc). (300-350 words)

## Management and Treatment
First-line therapy with SPECIFIC drug names, doses, duration, monitoring. Second-line and adjunct options. Special populations: pregnancy, CKD, elderly, hepatic impairment. Reference major guidelines (AHA/ACC/ESC/WHO/NICE). (500-600 words)

## Complications and Prognosis
Short and long-term complications with incidence rates. Prognostic factors. When to refer. (200-250 words)

## Special Populations and Considerations
Pediatric, geriatric, pregnancy, comorbidities, drug interactions, monitoring parameters. (200-250 words)

## Clinical Pearls
List 6-8 high-yield USMLE-style teaching points ("- " prefix). Classic associations, what not to miss, common pitfalls.

ARTICLE_END

Rules:
- State facts DIRECTLY with numbers — avoid vague hedging
- Use precise values: doses in mg/kg, lab values with units, timeframes in hours/days/weeks
- Do NOT write a references section
- Write COMPLETE, FULL-LENGTH sections — never abbreviate or summarize
- Output ONLY the structured text above, starting with TITLE:"""


def text_to_blocks(text: str) -> list[dict]:
    """Convert markdown article text to structured body blocks."""
    blocks  = []
    lines   = text.strip().split("\n")
    buffer: list[str] = []
    bullet_buffer: list[str] = []
    in_key_points = False

    def clean_md(s: str) -> str:
        s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
        s = re.sub(r"\*(.+?)\*", r"\1", s)
        s = re.sub(r"\*{1,3}", "", s)
        s = re.sub(r"`(.+?)`", r"\1", s)
        s = re.sub(r"#+\s+", "", s)
        return s.strip()

    def flush_buffer():
        para = " ".join(buffer).strip()
        if para:
            blocks.append({"type": "p", "content": clean_md(para)})
        buffer.clear()

    def flush_bullets():
        if bullet_buffer:
            items = [clean_md(b.lstrip("-•* ").strip())
                     for b in bullet_buffer if b.strip()]
            if in_key_points:
                blocks.append({
                    "type":    "callout",
                    "variant": "info",
                    "content": "\n".join(f"• {it}" for it in items)
                })
            else:
                blocks.append({"type": "ul", "items": items})
            bullet_buffer.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_buffer()
            flush_bullets()
        elif stripped.startswith("### "):
            flush_buffer(); flush_bullets()
            blocks.append({"type": "h3", "content": stripped[4:].strip()})
            in_key_points = False
        elif stripped.startswith("## "):
            flush_buffer(); flush_bullets()
            heading = stripped[3:].strip()
            blocks.append({"type": "h2", "content": heading})
            in_key_points = "key point" in heading.lower() or "clinical pearl" in heading.lower()
        elif stripped.startswith(("- ", "• ", "* ")) or (
            in_key_points and len(stripped) > 4 and stripped[0].isdigit()
            and stripped[1:3] in (". ", ") ")
        ):
            flush_buffer()
            bullet_buffer.append(stripped)
        else:
            flush_bullets()
            buffer.append(clean_md(stripped))

    flush_buffer()
    flush_bullets()
    return blocks


def _parse_article_output(content: str) -> dict | None:
    """Parse structured delimiter output from the model. No JSON involved."""
    # Extract TITLE
    title_m = re.search(r"^TITLE:\s*(.+)$", content, re.MULTILINE)
    if not title_m:
        return None
    title = title_m.group(1).strip().strip('"')

    # Extract EXCERPT (everything between EXCERPT: and ARTICLE_START)
    excerpt_m = re.search(
        r"^EXCERPT:\s*(.+?)(?=\nARTICLE_START|\n\n## |\nARTICLE_END)",
        content, re.MULTILINE | re.DOTALL
    )
    excerpt = excerpt_m.group(1).strip() if excerpt_m else ""

    # Extract ARTICLE body (between ARTICLE_START and ARTICLE_END)
    body_m = re.search(
        r"ARTICLE_START\s*\n(.*?)(?:ARTICLE_END|$)",
        content, re.DOTALL
    )
    if not body_m:
        # Fallback: everything from first ## heading
        body_m2 = re.search(r"(## Key Points.*)", content, re.DOTALL)
        if not body_m2:
            return None
        body_text = body_m2.group(1).strip()
    else:
        body_text = body_m.group(1).strip()

    if not body_text or len(body_text) < 500:
        return None

    return {"title": title, "excerpt": excerpt, "body_text": body_text}


def generate_with_ollama(topic: str, category: str, model: str) -> dict | None:
    """Call Ollama to generate article. Returns dict with title/excerpt/body_text."""
    prompt = ARTICLE_PROMPT.format(topic=topic, category=category)
    try:
        resp = httpx.post(
            OLLAMA_URL,
            json={
                "model":    model,
                "messages": [{"role": "user", "content": prompt}],
                "stream":   False,
                "options":  {
                    "temperature":    0.3,
                    "num_predict":    5000,   # ~3000 words; CPU ~28 min — worth the quality
                    "num_ctx":        8192,
                    "top_p":          0.9,
                    "repeat_penalty": 1.05,
                },
                "think": False,
            },
            timeout=300,   # 5 min max per article (qwen3:1.7b ~2.5 min; qwen3:8b use 900)
        )
        if resp.status_code != 200:
            log.error("Ollama error %s: %s", resp.status_code, resp.text[:200])
            return None

        content = resp.json().get("message", {}).get("content", "")
        if not content:
            log.error("Empty response from Ollama for '%s'", topic)
            return None

        data = _parse_article_output(content)
        if not data:
            log.error("Parse failed for '%s' — output preview: %s", topic, content[:300])
        return data

    except Exception as e:
        log.error("Ollama call failed for '%s': %s", topic, e)
        return None


# ── Slugify ────────────────────────────────────────────────────────────────────

def slugify(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug[:90]


# ── Database save ──────────────────────────────────────────────────────────────

def calc_reading_time(body: list) -> int:
    all_text = " ".join(
        b.get("content", "") or " ".join(b.get("items", []))
        for b in body
        if b.get("type") in ("p", "h2", "h3", "ul", "callout")
    )
    return max(5, len(all_text.split()) // 200)


def update_article(conn, article_id: str, title: str, excerpt: str,
                   body: list) -> bool:
    """Update body/excerpt/reading_time of an existing article by ID."""
    reading_time = calc_reading_time(body)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE articles
                   SET title = %s,
                       excerpt = %s,
                       body = %s::jsonb,
                       reading_time_minutes = %s,
                       updated_at = NOW()
                 WHERE id = %s
            """, (title, excerpt, json.dumps(body, ensure_ascii=False),
                  reading_time, article_id))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        log.error("DB update failed for %s: %s", article_id, e)
        return False


def save_article(conn, article_id: str, slug: str, title: str, excerpt: str,
                 body: list, category: str) -> bool:
    """Insert article into DB. Returns False if slug already exists."""
    schema_type = SCHEMA_MAP.get(category, "MedicalWebPage")
    reading_time = calc_reading_time(body)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM articles WHERE slug=%s", (slug,))
            if cur.fetchone():
                return False

            cur.execute("""
                INSERT INTO articles
                  (id, slug, title, excerpt, body, category, schema_type,
                   is_published, review_status, generated_by,
                   reading_time_minutes, created_at)
                VALUES
                  (%s,%s,%s,%s,%s::jsonb,%s,%s,true,'published','ollama-qwen3',
                   %s, NOW())
            """, (
                article_id, slug, title, excerpt,
                json.dumps(body, ensure_ascii=False),
                category, schema_type, reading_time,
            ))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        log.error("DB save failed for '%s': %s", slug, e)
        return False


def save_translations(conn, article_id: str, title: str, excerpt: str,
                      body: list) -> int:
    """Translate and save all 6 locales. Returns count saved."""
    saved = 0
    for locale in LOCALES:
        try:
            tr_title   = gtranslate(title, locale)
            time.sleep(0.3)
            tr_excerpt = gtranslate(excerpt, locale)
            time.sleep(0.3)
            tr_body    = translate_blocks(body, locale)

            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO article_translations
                      (article_id, locale, title, excerpt, body, status)
                    VALUES (%s,%s,%s,%s,%s::jsonb,'done')
                    ON CONFLICT (article_id, locale) DO UPDATE
                      SET title=EXCLUDED.title, excerpt=EXCLUDED.excerpt,
                          body=EXCLUDED.body, status='done'
                """, (
                    article_id, locale, tr_title, tr_excerpt,
                    json.dumps(tr_body, ensure_ascii=False),
                ))
            conn.commit()
            saved += 1
        except Exception as e:
            conn.rollback()
            log.warning("Translation failed for %s/%s: %s", article_id, locale, e)
    return saved


def notify_indexnow(slug: str):
    """Ping Bing/Yandex IndexNow for instant indexing."""
    url = f"https://medmind.pro/articles/{slug}"
    try:
        httpx.post(
            "https://api.indexnow.org/indexnow",
            json={"host": "medmind.pro", "key": INDEXNOW_KEY,
                  "urlList": [url]},
            timeout=5
        )
    except Exception:
        pass


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="MedMind Ollama Article Generator")
    parser.add_argument("--limit",      type=int,   default=20,
                        help="Max articles to generate (default: 20)")
    parser.add_argument("--model",      type=str,   default=OLLAMA_MODEL,
                        help=f"Ollama model (default: {OLLAMA_MODEL})")
    parser.add_argument("--category",   type=str,   default=None,
                        help="Only this category")
    parser.add_argument("--dry-run",    action="store_true",
                        help="Show topics without generating")
    parser.add_argument("--delay",      type=float, default=DELAY,
                        help="Seconds between articles (default: 2)")
    parser.add_argument("--regenerate", action="store_true",
                        help="Re-generate existing shallow Ollama articles (reading_time<=3)")
    args = parser.parse_args()

    log.info("Ollama Article Generator started | model=%s | limit=%d",
             args.model, args.limit)

    if args.dry_run:
        total = 0
        for cat, topics in TOPICS.items():
            if args.category and cat != args.category:
                continue
            print(f"\n{cat.upper()} ({len(topics)})")
            for t in topics:
                print(f"  - {t}")
            total += len(topics)
        print(f"\nTotal: {total} topics")
        return

    conn = psycopg2.connect(DB_URL)

    count   = 0
    errors  = 0
    skipped = 0

    # ── Regenerate mode: upgrade shallow Ollama articles ─────────────────────────
    if args.regenerate:
        with conn.cursor() as cur:
            query = """
                SELECT id, title, category
                FROM articles
                WHERE generated_by = 'ollama-qwen3'
                  AND reading_time_minutes <= 3
            """
            params: list = []
            if args.category:
                query += " AND category = %s"
                params.append(args.category)
            query += " ORDER BY created_at ASC LIMIT %s"
            params.append(args.limit)
            cur.execute(query, params)
            shallow = cur.fetchall()

        log.info("Regenerating %d shallow articles (reading_time<=3)", len(shallow))
        for article_id, title, category in shallow:
            log.info("[%d/%d] Regenerating: %s", count+1, len(shallow), title[:60])
            t0   = time.time()
            data = generate_with_ollama(title, category, args.model)
            elapsed = time.time() - t0

            if not data or not data.get("body_text"):
                log.warning("  x Generation failed (%.1fs)", elapsed)
                errors += 1
                continue

            new_title   = data.get("title", title)
            new_excerpt = data.get("excerpt", "")
            new_body    = text_to_blocks(data["body_text"])
            log.info("  Generated: '%s' (%.1fs, %d blocks)",
                     new_title[:60], elapsed, len(new_body))

            if update_article(conn, str(article_id), new_title, new_excerpt, new_body):
                n_tr = save_translations(conn, str(article_id), new_title, new_excerpt, new_body)
                rt   = calc_reading_time(new_body)
                log.info("  ok Updated (%d min read) + %d translations", rt, n_tr)
                new_slug = slugify(new_title)
                if _HAS_OG:
                    try:
                        _gen_og_image(new_slug, new_title, category, rt, force=True)
                    except Exception:
                        pass
                notify_indexnow(new_slug)
                count += 1
            else:
                errors += 1
            time.sleep(args.delay)

        conn.close()
        log.info("Done. Regenerated: %d | Errors: %d", count, errors)
        return

    # ── Normal mode: generate new topics ─────────────────────────────────────────
    for category, topics in TOPICS.items():
        if args.category and category != args.category:
            continue
        if count >= args.limit:
            break

        for topic in topics:
            if count >= args.limit:
                break

            log.info("[%d/%d] %s / %s", count+1, args.limit, category, topic)

            # Smart pre-check: use first 2 significant words to catch differently-titled
            # articles on the same subject (avoids wasting 25+ min generating a duplicate)
            STOP = {"and", "the", "of", "in", "with", "vs", "versus", "its", "for",
                    "or", "a", "an", "to", "from", "on", "at", "by", "as"}
            words = [w for w in re.split(r"[\s\-]+", topic.lower()) if w not in STOP]
            key2 = slugify(" ".join(words[:2]))   # e.g. "atrial-fibrillation"
            key1 = slugify(words[0])               # e.g. "atrial"

            with conn.cursor() as cur:
                # First: exact 2-word prefix match (most specific)
                cur.execute("SELECT 1 FROM articles WHERE slug LIKE %s LIMIT 1",
                            (key2 + "%",))
                if cur.fetchone():
                    log.info("  -- Skipped (keyword '%s' exists)", key2)
                    skipped += 1
                    continue
                # Second: full topic-slug prefix (original check)
                slug_pre = slugify(topic)[:50]
                cur.execute("SELECT 1 FROM articles WHERE slug LIKE %s LIMIT 1",
                            (slug_pre + "%",))
                if cur.fetchone():
                    log.info("  -- Skipped (topic slug exists)")
                    skipped += 1
                    continue

            t0   = time.time()
            data = generate_with_ollama(topic, category, args.model)
            elapsed = time.time() - t0

            if not data or not data.get("title") or not data.get("body_text"):
                log.warning("  x Generation failed (%.1fs)", elapsed)
                errors += 1
                continue

            title   = data["title"]
            excerpt = data.get("excerpt", "")
            body    = text_to_blocks(data["body_text"])
            slug    = slugify(title)

            log.info("  Generated: '%s' (%.1fs, %d blocks)",
                     title[:60], elapsed, len(body))

            # If the generated slug already exists, save under a unique variant
            article_id = str(uuid.uuid4())
            saved = save_article(conn, article_id, slug, title, excerpt,
                                 body, category)
            if not saved:
                # Try appending category suffix to make slug unique
                alt_slug = slugify(f"{title} {category}")[:90]
                saved = save_article(conn, article_id, alt_slug, title, excerpt,
                                     body, category)
            if not saved:
                log.info("  -- Slug conflict, skipping")
                skipped += 1
                continue

            n_tr = save_translations(conn, article_id, title, excerpt, body)
            log.info("  ok Published + %d translations | %s", n_tr, slug)

            if _HAS_COVER:
                try:
                    cover_url = _fetch_cover_image(title, category)
                    if cover_url:
                        with conn.cursor() as cur:
                            cur.execute("UPDATE articles SET cover_image=%s WHERE id=%s",
                                        (cover_url, article_id))
                        conn.commit()
                        log.info("  img Cover image: %s", cover_url[:60])
                except Exception as e:
                    log.warning("  Cover image failed: %s", e)

            if _HAS_OG:
                try:
                    rt = calc_reading_time(body)
                    _gen_og_image(slug, title, category, rt)
                except Exception as e:
                    log.warning("  OG image failed: %s", e)

            notify_indexnow(slug)

            count += 1
            time.sleep(args.delay)

    conn.close()
    log.info("Done. Generated: %d | Skipped: %d | Errors: %d",
             count, skipped, errors)


if __name__ == "__main__":
    main()
