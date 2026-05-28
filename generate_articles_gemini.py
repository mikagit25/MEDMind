"""
MedMind AI — Article Generator via Google Gemini API (FREE)

Speed:  ~500 tok/s → ~8 sec/article
Model:  gemini-2.0-flash (default) — 1500 req/day FREE per key
Limits: 1500 RPD | 15 RPM | 1M TPM per key → 5 keys = 7500 articles/day

Key feature: SMART PRE-FILTER — loads all existing article slugs at startup,
             generates ONLY topics not yet in DB (no wasted API calls).

Usage:
    python3 generate_articles_gemini.py --limit 100
    python3 generate_articles_gemini.py --category veterinary --limit 200
    python3 generate_articles_gemini.py --dry-run        # show pending topics
    python3 generate_articles_gemini.py --list-topics    # count per category

Run in background:
    nohup python3 generate_articles_gemini.py --limit 1000 > /tmp/gemini_gen.log 2>&1 &
    nohup python3 generate_articles_gemini.py --category veterinary > /tmp/gemini_vet.log 2>&1 &
"""
import argparse
import json
import logging
import os
import re
import sys
import time
import uuid
from datetime import datetime

import httpx
import psycopg2

# ── Import shared utilities from Ollama script ────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from generate_articles_ollama import (
    TOPICS as BASE_TOPICS, SCHEMA_MAP, DB_URL, LOCALES,
    slugify, text_to_blocks, calc_reading_time, save_article, update_article,
    save_translations, notify_indexnow, gtranslate, translate_blocks,
)

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

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Gemini config ─────────────────────────────────────────────────────────────
GEMINI_URL  = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_MODEL = "gemini-2.0-flash"
GEMINI_MODELS = {
    "gemini-2.5-flash":      {"rpd": 500,  "rpm": 10,  "desc": "Latest, best quality (default)"},
    "gemini-2.0-flash":      {"rpd": 1500, "rpm": 15,  "desc": "Fast, high daily limit"},
    "gemini-2.0-flash-lite": {"rpd": 1500, "rpm": 30,  "desc": "Faster, lighter"},
    "gemini-2.5-flash-lite": {"rpd": 500,  "rpm": 15,  "desc": "Lite version of 2.5"},
}

# ── New high-traffic topics (not in base TOPICS dict) ────────────────────────
NEW_TOPICS: dict[str, list[str]] = {
    "veterinary": [
        "Canine Parvovirus Diagnosis and Treatment Protocol",
        "Feline Chronic Kidney Disease Dietary Management",
        "Dog Hip Dysplasia Conservative and Surgical Options",
        "Hyperthyroidism in Cats Methimazole vs Radioiodine",
        "Canine Diabetes Mellitus Insulin Types and Dosing",
        "Feline Asthma Bronchodilators and Corticosteroids",
        "Heartworm Disease Prevention Macrocyclic Lactones",
        "Feline Lower Urinary Tract Disease FLUTD Management",
        "Canine Epilepsy Phenobarbital and Potassium Bromide",
        "Feline Infectious Peritonitis FIP GS-441524 Treatment",
        "Dog Cushing Disease Diagnosis Trilostane vs Mitotane",
        "Canine Lyme Disease Doxycycline Treatment and Prevention",
        "Feline Pancreatitis Diagnosis Feline Pancreatic Lipase",
        "Dog Allergic Dermatitis Immunotherapy and Biologics",
        "Canine Osteosarcoma Limb Sparing and Carboplatin",
        "Hypertrophic Cardiomyopathy Cats Echocardiogram",
        "Gastric Dilatation Volvulus GDV Emergency Surgery",
        "Feline Herpesvirus Corneal Ulcer Antiviral Treatment",
        "Canine Hypothyroidism Levothyroxine Dosing Monitoring",
        "Canine Intervertebral Disc Disease IVDD Grading Surgery",
        "Feline Lymphoma Chemotherapy CHOP Protocol",
        "Dog Patellar Luxation Grading Surgical Correction",
        "Toxoplasmosis in Cats Zoonotic Risk Pregnant Women",
        "Canine Autoimmune Hemolytic Anemia Immunosuppression",
        "Feline Hyperthyroidism Iodine-Restricted Diet",
        "Canine Pituitary-Dependent Hyperadrenocorticism",
        "Pyoderma Dogs Surface Deep Antibiotic Selection",
        "Feline Infectious Anemia Mycoplasma Haemofelis",
        "Canine Atopic Dermatitis Oclacitinib Lokivetmab",
        "Feline Diabetes Remission Tight Glycemic Control",
        "Canine Dilated Cardiomyopathy Pimobendan Therapy",
        "Feline Asthma vs Chronic Bronchitis Differentiation",
        "Dog Dental Disease Periodontal Staging Treatment",
        "Feline Constipation Megacolon Subtotal Colectomy",
        "Canine Pancreatitis Lipase Diagnosis and Management",
        "Rabbit GI Stasis Emergency Treatment Protocol",
        "Avian Proventricular Dilatation Disease PDD",
        "Reptile Metabolic Bone Disease UVB Calcium",
        "Feline Injection Site Sarcoma Surgical Margins",
        "Canine Mast Cell Tumor Grading Toceranib Treatment",
    ],
    "mental-health": [
        "Generalized Anxiety Disorder CBT and SSRI Comparison",
        "Major Depressive Disorder Antidepressant Selection Guide",
        "Bipolar I Disorder Lithium Monitoring and Toxicity",
        "ADHD Adults Stimulant Medications Dosing Titration",
        "Borderline Personality Disorder DBT Skills Training",
        "PTSD Prolonged Exposure vs EMDR Evidence",
        "OCD Exposure Response Prevention and Fluvoxamine",
        "Schizophrenia First and Second Generation Antipsychotics",
        "Panic Disorder Cognitive Restructuring and SSRIs",
        "Social Anxiety Disorder SSRI vs Psychotherapy",
        "Anorexia Nervosa Medical Complications Refeeding",
        "Bulimia Nervosa CBT-BN and Fluoxetine Protocol",
        "Autism Spectrum Disorder Applied Behavior Analysis",
        "Insomnia Disorder CBT-I vs Pharmacotherapy",
        "Alcohol Use Disorder Naltrexone Acamprosate Disulfiram",
        "Opioid Use Disorder Buprenorphine Methadone",
        "Postpartum Depression Edinburgh Scale and Treatment",
        "Suicide Risk Assessment Columbia Protocol Safety Plan",
        "Dementia Behavioral Psychological Symptoms BPSD",
        "Cannabis Use Disorder Clinical Features Withdrawal",
        "Stimulant Use Disorder Cocaine Methamphetamine",
        "Gambling Disorder Naltrexone and CBT",
        "Dissociative Identity Disorder Diagnosis Treatment",
        "Schizoaffective Disorder Differential Diagnosis",
        "Treatment Resistant Depression ECT Ketamine Options",
        "Seasonal Affective Disorder Light Therapy SAD",
        "Body Dysmorphic Disorder ERP and SSRIs",
        "Hoarding Disorder CBT Motivational Interviewing",
        "Psychosis First Episode Early Intervention",
        "Adjustment Disorder DSM-5 Criteria Brief Therapy",
    ],
    "nutrition": [
        "Vitamin D Deficiency Supplementation Dosing Guidelines",
        "Iron Deficiency Anemia Dietary and IV Iron Protocol",
        "Vitamin B12 Deficiency Neurological Subacute Degeneration",
        "Omega-3 Fatty Acids EPA DHA Cardiovascular Evidence",
        "Mediterranean Diet Pattern Disease Prevention Evidence",
        "Magnesium Deficiency Manifestations and Repletion",
        "Zinc Deficiency Immune Function Wound Healing",
        "Folate Deficiency Neural Tube Defects Prevention",
        "Iodine Deficiency Goiter Hypothyroidism Prevention",
        "Malnutrition Screening MUST MNA Assessment Tools",
        "Total Parenteral Nutrition TPN Formulation Monitoring",
        "Enteral Nutrition Nasogastric Feeding Complications",
        "Obesity Medical Nutrition Therapy Caloric Deficit",
        "Celiac Disease Gluten-Free Diet Long-term Compliance",
        "Type 2 Diabetes Carbohydrate Counting Glycemic Index",
        "DASH Diet Hypertension Evidence Sodium Restriction",
        "Ketogenic Diet Epilepsy Weight Loss Mechanism",
        "Intermittent Fasting Metabolic Effects 16:8 Protocol",
        "Protein Requirements Critical Illness ICU Nutrition",
        "Micronutrient Deficiencies Post Bariatric Surgery",
        "Short Bowel Syndrome Nutritional Management",
        "Refeeding Syndrome Prevention Phosphate Monitoring",
        "Thiamine Deficiency Wernicke Encephalopathy",
        "Vitamin C Deficiency Scurvy Clinical Features",
        "Vitamin K Deficiency Coagulation Newborn",
        "Selenium Deficiency Keshan Disease Heart",
        "Copper Deficiency Myelopathy Neurological",
        "Eating Disorder Malnutrition Refeeding Protocol",
        "Sarcopenia Nutritional Interventions Muscle Loss",
        "FODMAP Diet Irritable Bowel Syndrome Evidence",
    ],
    "sports-medicine": [
        "ACL Tear Reconstruction BPTB vs Hamstring Graft",
        "Rotator Cuff Tear Partial Full Thickness Treatment",
        "Lateral Epicondylitis Platelet Rich Plasma Evidence",
        "Stress Fractures High Risk Sites Return to Sport",
        "Concussion Graded Return to Play Protocol",
        "Plantar Fasciitis Night Splint Corticosteroid Shockwave",
        "Achilles Tendinopathy Eccentric Loading Rehab",
        "Patellofemoral Pain Syndrome VMO Strengthening",
        "Medial Tibial Stress Syndrome Shin Splints Etiology",
        "Shoulder Dislocation Bankart Repair Arthroscopic",
        "Ankle Sprain Lateral Grade I II III Treatment",
        "Iliotibial Band Syndrome Runners Hip Abductor",
        "Exercise Induced Bronchoconstriction Diagnosis",
        "Exertional Heat Stroke Core Cooling Techniques",
        "Rhabdomyolysis Exercise Induced CK Hydration",
        "Overtraining Syndrome Hormonal Markers Recovery",
        "Femoroacetabular Impingement Hip Cam Pincer",
        "Meniscus Tear Repair vs Meniscectomy Outcomes",
        "Sports Hernia Athletic Pubalgia Diagnosis Surgery",
        "RICE POLICE PEACE LOVE Soft Tissue Injury",
        "Return to Sport Testing Functional Criteria",
        "Muscle Strain Grading Myotendinous Junction",
        "Growth Plate Injuries Salter Harris Classification",
        "Female Athlete Triad Relative Energy Deficiency RED-S",
        "Pre-participation Physical Examination Cardiac Screen",
    ],
    "travel-medicine": [
        "Malaria Prophylaxis Atovaquone Doxycycline Mefloquine",
        "Travelers Diarrhea Azithromycin Rifaximin Prevention",
        "Yellow Fever Vaccination Requirements Contraindications",
        "Dengue Fever Breakbone Disease Clinical Phases",
        "Typhoid Fever Oral vs Injectable Vaccine",
        "Altitude Sickness AMS HACE HACE Acetazolamide",
        "Zika Virus Sexual Transmission Pregnancy Risks",
        "Rabies Pre-Exposure Prophylaxis High Risk Travel",
        "Chikungunya Arthritis Diagnosis Treatment",
        "Japanese Encephalitis Vaccination Asia Travel",
        "Cholera Oral Vaccine Dukoral Indications",
        "DVT Prevention Long Haul Flights Compression",
        "Jet Lag Melatonin Chronobiotics Light Therapy",
        "Schistosomiasis Freshwater Exposure Praziquantel",
        "Leptospirosis Flood Exposure Penicillin Treatment",
        "Rickettsial Disease Spotted Fever Doxycycline",
        "Traveler Health Pre-Travel Consultation Checklist",
        "Hepatitis A Vaccine Schedule Dosing",
        "Leishmaniasis Visceral Cutaneous Treatment",
        "Meningococcal Vaccination Hajj Requirements",
    ],
    "genetics": [
        "Down Syndrome Trisomy 21 Prenatal Screening",
        "BRCA1 BRCA2 Hereditary Breast Ovarian Cancer",
        "Cystic Fibrosis CFTR Modulators Trikafta Treatment",
        "Huntington Disease Genetic Testing Counseling",
        "Marfan Syndrome FBN1 Cardiovascular Surveillance",
        "Hemophilia A B Factor Replacement Gene Therapy",
        "Fragile X Syndrome FMR1 Repeat Expansion",
        "Phenylketonuria PKU Dietary Phenylalanine Restriction",
        "Sickle Cell Disease Hydroxyurea Gene Therapy",
        "Thalassemia Alpha Beta Transfusion Chelation",
        "Neurofibromatosis Type 1 NF1 MEK Inhibitors",
        "Hereditary Hemochromatosis HFE Phlebotomy",
        "Wilson Disease ATP7B Chelation Liver Transplant",
        "Familial Hypercholesterolemia LDL Receptor PCSK9",
        "Spinal Muscular Atrophy SMN1 Nusinersen Zolgensma",
        "Duchenne Muscular Dystrophy Dystrophin Exon Skipping",
        "Lynch Syndrome Mismatch Repair Colorectal Screening",
        "Li-Fraumeni Syndrome TP53 Surveillance Protocol",
        "Prader Willi Angelman Syndrome Genomic Imprinting",
        "Ehlers Danlos Syndrome Hypermobility Collagen",
    ],
    "allergy-immunology": [
        "Anaphylaxis Epinephrine Dosing Emergency Management",
        "Allergic Rhinitis Subcutaneous Sublingual Immunotherapy",
        "Asthma Step Therapy GINA Guidelines 2024",
        "Food Allergy IgE Mediated Oral Immunotherapy",
        "Atopic Dermatitis Dupilumab Biologics Step Therapy",
        "Urticaria Chronic Spontaneous Antihistamine Omalizumab",
        "Drug Allergy Penicillin Allergy Delabeling",
        "Latex Allergy Cross-Reactive Foods Avocado Banana",
        "Contact Dermatitis Patch Testing Allergen Avoidance",
        "Eosinophilic Esophagitis Proton Pump Inhibitor Diet",
        "Hereditary Angioedema HAE C1 Inhibitor Icatibant",
        "Mastocytosis Systemic KIT D816V Midostaurin",
        "Common Variable Immunodeficiency CVID IVIG",
        "Selective IgA Deficiency Transfusion Precautions",
        "Hypersensitivity Pneumonitis Antigen Avoidance",
        "Allergic Bronchopulmonary Aspergillosis ABPA",
        "Venom Allergy Bee Wasp Immunotherapy Duration",
        "Aspirin Exacerbated Respiratory Disease AERD",
        "Autoimmune Urticaria IgG Anti-FcεRI Testing",
        "Primary Immunodeficiency Screening SCID Newborn",
    ],

    # ── High-volume drug reference articles ────────────────────────────────────
    "drug-reference": [
        "Metformin Type 2 Diabetes First-Line Therapy Mechanism",
        "Atorvastatin High-Intensity Statin ASCVD Prevention",
        "Amlodipine Calcium Channel Blocker Hypertension Angina",
        "Lisinopril ACE Inhibitor Heart Failure CKD Dosing",
        "Levothyroxine Hypothyroidism Dosing TSH Monitoring",
        "Omeprazole PPI GERD Peptic Ulcer H pylori",
        "Sertraline SSRI Depression Anxiety Dosing Titration",
        "Escitalopram SSRI Anxiety Disorder First-Line",
        "Quetiapine Antipsychotic Bipolar Schizophrenia Sedation",
        "Aripiprazole Atypical Antipsychotic Augmentation",
        "Duloxetine SNRI Depression Neuropathic Pain Fibromyalgia",
        "Venlafaxine SNRI Depression Anxiety Hot Flashes",
        "Bupropion Antidepressant Smoking Cessation ADHD",
        "Mirtazapine Antidepressant Insomnia Weight Gain",
        "Trazodone Antidepressant Insomnia Off-Label Use",
        "Clonazepam Benzodiazepine Panic Disorder Seizure",
        "Lorazepam Benzodiazepine Anxiety Alcohol Withdrawal",
        "Alprazolam Benzodiazepine Short-Term Anxiety Management",
        "Zolpidem Non-Benzodiazepine Insomnia Risks Elderly",
        "Methylphenidate ADHD Stimulant Dosing Monitoring",
        "Amphetamine Salts ADHD Adults Children Dosing",
        "Atomoxetine Non-Stimulant ADHD Cardiovascular Effects",
        "Naltrexone Opioid Alcohol Dependence Monthly Injection",
        "Buprenorphine Opioid Use Disorder Induction Protocol",
        "Varenicline Smoking Cessation Neuropsychiatric Warning",
        "Topiramate Epilepsy Migraine Prevention Weight Loss",
        "Lamotrigine Bipolar Depression Epilepsy Rash Risk",
        "Valproate Bipolar Epilepsy Hepatotoxicity Pregnancy",
        "Levetiracetam Epilepsy Behavioral Side Effects",
        "Carbamazepine Epilepsy Trigeminal Neuralgia Drug Interactions",
        "Gabapentin Neuropathic Pain Epilepsy Misuse Potential",
        "Pregabalin Neuropathic Pain Fibromyalgia Schedule V",
        "Amitriptyline TCA Depression Neuropathic Pain Low Dose",
        "Nortriptyline TCA Depression Pain ADHD Monitoring",
        "Warfarin Anticoagulation INR Monitoring Drug Interactions",
        "Rivaroxaban DOAC VTE AFib No Monitoring Reversal",
        "Apixaban DOAC Stroke Prevention Renal Adjustment",
        "Dabigatran DOAC Dyspepsia Idarucizumab Reversal",
        "Clopidogrel Antiplatelet ACS CYP2C19 Resistance",
        "Ticagrelor P2Y12 Inhibitor ACS Dyspnea Side Effect",
        "Aspirin Antiplatelet Cardiovascular Dose GI Risk",
        "Heparin Unfractionated DVT PE Monitoring HIT",
        "Enoxaparin LMWH DVT Prophylaxis Renal Adjustment",
        "Furosemide Loop Diuretic Heart Failure Electrolytes",
        "Spironolactone Aldosterone Antagonist Heart Failure Hyperkalemia",
        "Carvedilol Beta Blocker Heart Failure Titration",
        "Bisoprolol Beta-1 Selective Heart Failure AFib",
        "Sacubitril Valsartan ARNI HFrEF Mortality Benefit",
        "Dapagliflozin SGLT2 Inhibitor Diabetes Heart Failure Renal",
        "Empagliflozin SGLT2 Inhibitor Cardiovascular Renal Outcomes",
        "Semaglutide GLP-1 Agonist Weight Loss Cardiovascular",
        "Liraglutide GLP-1 Agonist Diabetes Obesity Dosing",
        "Insulin Glargine Basal Insulin Dosing Titration",
        "Insulin Aspart Bolus Insulin Dosing Correction",
        "Pioglitazone Thiazolidinedione Insulin Resistance NASH",
        "Sitagliptin DPP-4 Inhibitor Diabetes Renal Safety",
        "Allopurinol Gout Uric Acid Lowering HLA-B5801",
        "Febuxostat Gout Cardiovascular Warning FDA",
        "Colchicine Gout Flare FMF Pericarditis Dosing",
        "Prednisone Systemic Corticosteroid Tapering Adrenal",
        "Methylprednisolone IV Pulse Multiple Sclerosis IBD",
        "Dexamethasone High Potency Steroid Cerebral Edema",
        "Hydroxychloroquine Lupus RA Ophthalmology Screening",
        "Methotrexate Rheumatoid Arthritis Folate Supplementation",
        "Sulfasalazine IBD Rheumatoid Arthritis Monitoring",
        "Adalimumab TNF Inhibitor RA IBD Psoriasis Screening",
        "Etanercept TNF Inhibitor Rheumatoid Arthritis Subcutaneous",
        "Rituximab Anti-CD20 RA Lymphoma PML Risk",
        "Tocilizumab IL-6 Inhibitor RA GCA Cytokine Release",
        "Tofacitinib JAK Inhibitor RA Safety Monitoring",
        "Ustekinumab IL-12 23 Psoriasis Crohn Disease",
        "Secukinumab IL-17 Inhibitor Psoriasis Ankylosing",
        "Dupilumab IL-4 13 Atopic Dermatitis Asthma",
        "Omalizumab Anti-IgE Asthma Urticaria Subcutaneous",
        "Mepolizumab Anti-IL-5 Severe Eosinophilic Asthma",
        "Benralizumab IL-5 Receptor Severe Asthma Monthly",
        "Montelukast Leukotriene Antagonist Asthma Allergic Rhinitis",
        "Budesonide ICS Asthma Crohn Disease Low Bioavailability",
        "Tiotropium LAMA COPD Spiriva Dry Powder Inhaler",
        "Salmeterol LABA Asthma COPD Combination Therapy",
        "N-Acetylcysteine Acetaminophen Overdose Protocol",
        "Naloxone Opioid Reversal Dosing Repeat Dosing",
        "Flumazenil Benzodiazepine Reversal Seizure Risk",
        "Amoxicillin First-Line Otitis Media Strep Throat",
        "Amoxicillin-Clavulanate ABRS Bite Wounds Skin Infections",
        "Doxycycline Atypical Pneumonia MRSA Tick-Borne STI",
        "Azithromycin Z-Pack Respiratory Infections QT Risk",
        "Clarithromycin H pylori Triple Therapy Drug Interactions",
        "Ciprofloxacin Fluoroquinolone UTI GI Tendon Risk",
        "Levofloxacin Respiratory Fluoroquinolone Tendinopathy",
        "Trimethoprim Sulfamethoxazole UTI PCP Prophylaxis",
        "Nitrofurantoin Uncomplicated UTI Avoid Late Pregnancy",
        "Metronidazole Anaerobes BV C difficile Alcohol Warning",
        "Clindamycin MRSA Skin Anaerobes C difficile Risk",
        "Vancomycin MRSA Monitoring AUC-Based Dosing",
        "Linezolid MRSA VRE Serotonin Syndrome Risk",
        "Ceftriaxone Third Generation Cephalosporin Meningitis",
        "Piperacillin-Tazobactam Broad Spectrum Hospital Infections",
        "Meropenem Carbapenem MDR Gram-Negative Infections",
        "Fluconazole Candida Mucosal Systemic Dosing",
        "Itraconazole Aspergillus Dermatophyte Drug Interactions",
        "Voriconazole Invasive Aspergillosis Visual Disturbances",
        "Acyclovir Herpes HSV VZV Renal Dosing IV Oral",
        "Valacyclovir Herpes Simplex Zoster Suppression",
        "Oseltamivir Influenza Treatment Prophylaxis Timing",
        "Tenofovir HIV Hepatitis B Renal Bone Safety",
        "Emtricitabine Tenofovir HIV PrEP Combination",
    ],

    # ── Specific clinical conditions and syndromes ─────────────────────────────
    "clinical-syndromes": [
        "Sepsis and Septic Shock Hour-1 Bundle Management",
        "ARDS Berlin Definition Lung Protective Ventilation",
        "Disseminated Intravascular Coagulation DIC Management",
        "Hemolytic Uremic Syndrome HUS STEC E coli",
        "Thrombotic Thrombocytopenic Purpura TTP ADAMTS13",
        "Antiphospholipid Syndrome Diagnosis Anticoagulation",
        "Systemic Inflammatory Response Syndrome SIRS Criteria",
        "Cytokine Release Syndrome CAR-T Immunotherapy",
        "Tumor Lysis Syndrome Rasburicase Prevention",
        "Superior Vena Cava Syndrome Malignant Emergency",
        "Neuroleptic Malignant Syndrome Bromocriptine Cooling",
        "Serotonin Syndrome Hunter Criteria Cyproheptadine",
        "Malignant Hyperthermia Dantrolene Triggering Agents",
        "DRESS Syndrome Drug Reaction Eosinophilia Systemic",
        "Stevens Johnson Syndrome Toxic Epidermal Necrolysis",
        "Reye Syndrome Aspirin Children Mitochondrial",
        "Hemophagocytic Lymphohistiocytosis HLH Etoposide",
        "Macrophage Activation Syndrome Secondary HLH",
        "Waterhouse-Friderichsen Syndrome Meningococcal",
        "Lemierre Syndrome Fusobacterium Internal Jugular",
        "Fournier Gangrene Necrotizing Fasciitis Perineum",
        "Calciphylaxis Warfarin Sodium Thiosulfate Dialysis",
        "Posterior Reversible Encephalopathy PRES Hypertension",
        "Central Pontine Myelinolysis Osmotic Demyelination",
        "Wernicke-Korsakoff Syndrome Thiamine IV Before Glucose",
        "Normal Pressure Hydrocephalus Triad Shunting",
        "Cauda Equina Syndrome MRI Emergency Surgery",
        "Compartment Syndrome Forearm Leg Fasciotomy",
        "Rhabdomyolysis CK Hydration Dialysis Threshold",
        "Fat Embolism Syndrome Long Bone Fracture Petechiae",
        "Air Embolism Venous Arterial Durant Maneuver",
        "Transfusion Reactions TRALI TACO Hemolytic Delayed",
        "Heparin Induced Thrombocytopenia HIT 4T Score",
        "Methemoglobinemia Methylene Blue Dapsone Nitrates",
        "Carbon Monoxide Poisoning Hyperbaric Oxygen",
        "Cyanide Poisoning Hydroxocobalamin Bitter Almond",
        "Acetaminophen Overdose Rumack Matthew Nomogram",
        "Salicylate Toxicity Alkaline Diuresis Hemodialysis",
        "Tricyclic Antidepressant Overdose Sodium Bicarbonate",
        "Beta Blocker Overdose High Dose Insulin Lipid Emulsion",
        "Calcium Channel Blocker Overdose Calcium Insulin",
    ],

    # ── Diagnostic tests and interpretation ────────────────────────────────────
    "diagnostics-interpretation": [
        "Troponin I T High Sensitivity ACS NSTEMI Interpretation",
        "BNP NT-proBNP Heart Failure Diagnosis Cutoffs",
        "D-Dimer VTE Diagnosis Wells Score Pretest Probability",
        "Arterial Blood Gas Interpretation Systematic Approach",
        "Lactate Sepsis Shock Clearance Goal-Directed",
        "Procalcitonin Bacterial Infection Antibiotic Stewardship",
        "CRP ESR Inflammation Acute Phase Reactants",
        "Ferritin Iron Studies Anemia Classification",
        "Thyroid Function Tests TSH T4 T3 Interpretation",
        "HbA1c Diabetes Monitoring Limitations Hemoglobin Variants",
        "Creatinine eGFR CKD Staging MDRD CKD-EPI",
        "Liver Function Tests ALT AST Bilirubin Patterns",
        "Coagulation Studies PT INR PTT Thrombin Time",
        "Complete Blood Count Interpretation White Cell Differential",
        "Urinalysis Interpretation Dipstick Microscopy",
        "Cerebrospinal Fluid Analysis Meningitis Interpretation",
        "Pleural Fluid Analysis Light Criteria Exudate Transudate",
        "Peritoneal Fluid SAAG Ascites Cause Differential",
        "Synovial Fluid Analysis Crystal Arthritis Septic Joint",
        "Bone Marrow Biopsy Indications Interpretation",
        "Flow Cytometry Lymphoma Leukemia Immunophenotyping",
        "Genetic Testing BRCA Lynch Pharmacogenomics",
        "Tumor Markers PSA CEA CA-125 AFP Interpretation",
        "Point of Care Ultrasound POCUS Cardiac Lung FAST",
        "ECG Systematic Reading Blocks Intervals Axis",
        "Holter Monitor Event Recorder Arrhythmia Detection",
        "Echocardiography Systolic Diastolic Function EF",
        "Stress Testing Duke Treadmill Score Interpretation",
        "Coronary Angiography CT Angiography FFR iFR",
        "Pulmonary Function Tests Spirometry DLCO Patterns",
        "Sleep Study Polysomnography AHI OSA Severity",
        "EEG Epileptiform Discharges Status Interpretation",
        "EMG Nerve Conduction Studies Neuropathy Myopathy",
        "MRI Brain Stroke Diffusion Weighted Imaging",
        "CT Head Hemorrhage Hyperdense Midline Shift",
        "Chest X-Ray Systematic Reading Effusion Infiltrate",
        "CT Pulmonary Angiography PE Protocol Wells Score",
        "Abdominal CT Appendicitis Alvarado Diverticulitis",
        "Bone Density DEXA T-Score FRAX Osteoporosis",
        "Mammography BI-RADS Breast Cancer Screening",
    ],

    # ── Women's health detailed topics ─────────────────────────────────────────
    "womens-health": [
        "Polycystic Ovary Syndrome PCOS Rotterdam Criteria Treatment",
        "Endometriosis Staging Laparoscopy Medical Management",
        "Uterine Fibroids Myomectomy Uterine Artery Embolization",
        "Cervical Cancer Screening Colposcopy ASCUS HSIL",
        "Ovarian Cancer CA-125 Debulking Platinum Taxane",
        "Breast Cancer HER2 ER PR Trastuzumab Tamoxifen",
        "Preeclampsia Severe Features Magnesium Delivery Timing",
        "Gestational Diabetes A1C Postpartum Screening",
        "Placenta Previa Accreta Spectrum Risk Delivery",
        "Ectopic Pregnancy Methotrexate Criteria Surgery",
        "Premature Ovarian Insufficiency POI HRT Management",
        "Menopause Hormone Therapy Risks Benefits Timing",
        "Osteoporosis Postmenopause Bisphosphonate DEXA",
        "Vulvar Disorders Lichen Sclerosus Diagnosis Treatment",
        "Pelvic Inflammatory Disease Criteria Inpatient Outpatient",
        "Bacterial Vaginosis Recurrence Prevention Treatment",
        "Vulvovaginal Candidiasis Recurrent Treatment",
        "Interstitial Cystitis Painful Bladder Syndrome",
        "Pelvic Floor Dysfunction Prolapse Pessary Surgery",
        "Urinary Incontinence Stress Urge Mixed Treatment",
        "Premenstrual Dysphoric Disorder PMDD SSRI Treatment",
        "Primary Dysmenorrhea NSAIDs Oral Contraceptives",
        "Contraception Methods Efficacy Failure Rates",
        "Emergency Contraception Levonorgestrel Copper IUD",
        "Intrauterine Device IUD Copper Hormonal Insertion",
        "Fertility Evaluation AMH FSH HSG Sperm Analysis",
        "Recurrent Pregnancy Loss Evaluation Antiphospholipid",
        "HELLP Syndrome Diagnosis Delivery Timing",
        "Postpartum Hemorrhage Active Management Prevention",
        "Breastfeeding Lactation Medications Safety LactMed",
    ],

    # ── Pediatric specific topics ──────────────────────────────────────────────
    "pediatrics-specific": [
        "Neonatal Jaundice Bilirubin Phototherapy Exchange",
        "Respiratory Syncytial Virus RSV Bronchiolitis Palivizumab",
        "Croup Stridor Racemic Epinephrine Dexamethasone",
        "Epiglottitis H influenzae Type B Vaccination Airway",
        "Kawasaki Disease Coronary Aneurysm IVIG Aspirin",
        "Juvenile Idiopathic Arthritis Subtypes Biologics",
        "Celiac Disease Pediatric Tissue Transglutaminase",
        "Type 1 Diabetes Children Insulin Pump CGM",
        "Congenital Heart Disease VSD ASD Tetralogy Surgery",
        "Neonatal Sepsis GBS Early Late Onset Empiric",
        "Meningitis Pediatric Empiric Ceftriaxone Dexamethasone",
        "Febrile Seizures Simple Complex Management",
        "Pediatric UTI Vesicoureteral Reflux VCUG Prophylaxis",
        "Intussusception Air Enema Reduction Surgical",
        "Pyloric Stenosis Projectile Vomiting Pyloromyotomy",
        "Failure to Thrive Organic Nonorganic Evaluation",
        "Developmental Delay Screening MCHAT M-CHAT-R",
        "ADHD Pediatric Diagnosis DSM-5 Stimulant Dosing",
        "Autism Spectrum Disorder Early Intervention ABA",
        "Pediatric Asthma Stepwise GINA Management",
        "Cystic Fibrosis Sweat Test CFTR Modulators",
        "Sickle Cell Disease Pediatric Hydroxyurea Prophylaxis",
        "Thalassemia Pediatric Transfusion Chelation Bone Marrow",
        "Wilms Tumor Nephroblastoma Staging Surgery Chemo",
        "Neuroblastoma MYCN Amplification Staging Treatment",
        "Pediatric Obesity BMI Percentile Metabolic Syndrome",
        "Rickets Vitamin D Calcium Deficiency X-Ray",
        "Growth Hormone Deficiency IGF-1 GH Stimulation Test",
        "Precocious Puberty Central Peripheral GnRH Analog",
        "Neonatal Abstinence Syndrome Opioid Finnegan Scale",
    ],

    # ── Specific surgical and procedural topics ────────────────────────────────
    "surgery-procedures": [
        "Appendectomy Laparoscopic Open Perforated Management",
        "Cholecystectomy Laparoscopic Bile Duct Injury",
        "Hernia Inguinal Hiatal Ventral Repair Mesh",
        "Thyroidectomy Complications Parathyroid Recurrent Laryngeal",
        "Colectomy Colorectal Cancer Anastomosis Diversion",
        "Bariatric Surgery Roux-en-Y Sleeve Complications",
        "Coronary Artery Bypass CABG vs PCI Selection",
        "Aortic Valve Replacement TAVR SAVR Indications",
        "Hip Replacement Total Arthroplasty DVT Prevention",
        "Knee Replacement TKA Outcomes Complications",
        "Spinal Fusion Lumbar TLIF Outcomes Complications",
        "Carotid Endarterectomy vs Stenting Symptomatic",
        "Kidney Transplant Immunosuppression Rejection",
        "Liver Transplant MELD Score Allocation Rejection",
        "Central Line Insertion Complications Bundle Care",
        "Chest Tube Insertion Technique Complications",
        "Lumbar Puncture Technique Contraindications CSF",
        "Paracentesis Technique Large Volume Albumin",
        "Thoracentesis Technique Complications Ultrasound",
        "Endoscopy Upper GI Scope Sedation Complication",
        "Colonoscopy Bowel Prep Polypectomy Perforation",
        "Bronchoscopy Indications BAL Transbronchial Biopsy",
        "ERCP Choledocholithiasis Stent Pancreatitis Risk",
        "Cardiac Catheterization PCI Stent Types Antiplatelet",
        "Ablation Atrial Fibrillation Pulmonary Vein Isolation",
        "Pacemaker Implantation Indications Interrogation",
        "Implantable Cardioverter Defibrillator ICD Primary Prevention",
        "Dialysis Hemodialysis Peritoneal Access Adequacy",
        "Plasmapheresis Indications GBS TTP Myasthenia",
        "Bone Marrow Transplant Allogeneic Autologous GVHD",
    ],

    # ── Infectious disease specific ────────────────────────────────────────────
    "infectious-specific": [
        "HIV Antiretroviral Therapy When to Start Regimens",
        "Tuberculosis Active Latent RIPE Treatment DOT",
        "Pneumocystis jirovecii PCP Prophylaxis TMP-SMX",
        "Cryptococcal Meningitis HIV Liposomal Amphotericin",
        "CMV Retinitis Colitis Ganciclovir Valganciclovir",
        "Toxoplasmosis CNS HIV Pyrimethamine Sulfadiazine",
        "Clostridioides difficile Severity Fidaxomicin Fecal",
        "Methicillin Resistant Staphylococcus Aureus MRSA Decolonization",
        "Carbapenem Resistant Enterobacteriaceae CRE Colistin",
        "Pseudomonas aeruginosa Treatment Ceftolozane Ceftazidime",
        "Aspergillus Invasive Voriconazole Isavuconazole",
        "Candida Bloodstream Echinocandin Ophthalmology",
        "Infective Endocarditis Duke Criteria Surgery Timing",
        "Osteomyelitis Acute Chronic Staphylococcus Imaging",
        "Septic Arthritis Joint Aspiration Empiric Treatment",
        "Meningitis Bacterial Empiric Dexamethasone CSF",
        "Encephalitis HSV Acyclovir MRI EEG Treatment",
        "Malaria Severe Artesunate IV Quinine Alternatives",
        "Dengue Fever Platelet Transfusion Thresholds Warning",
        "Leptospirosis Weil Disease Penicillin Doxycycline",
        "Brucellosis Doxycycline Rifampin Combination",
        "Q Fever Coxiella Doxycycline Endocarditis Treatment",
        "Rocky Mountain Spotted Fever Doxycycline Timing",
        "Lyme Disease Stages Doxycycline Amoxicillin IV",
        "Influenza Severe Oseltamivir ICU Empiric",
        "COVID-19 Severe Dexamethasone Remdesivir Anticoagulation",
        "Mpox Diagnosis Tecovirimat Treatment Contact Tracing",
        "Hepatitis B Antiviral Tenofovir Entecavir HCC Screen",
        "Hepatitis C Direct Acting Antivirals SVR Cure Rate",
        "Gonorrhea Ceftriaxone Resistance Dual Therapy",
    ],

    # ── Cardiology specific ────────────────────────────────────────────────────
    "cardiology-advanced": [
        "STEMI Primary PCI Door Balloon Time Thrombolytics",
        "NSTEMI Risk Stratification TIMI GRACE Early Invasive",
        "Atrial Fibrillation Rate vs Rhythm Control EAST-AFNET",
        "Atrial Flutter Cavotricuspid Isthmus Ablation",
        "Ventricular Tachycardia Storm Amiodarone Ablation",
        "Wolff-Parkinson-White WPW Pathway Ablation Danger",
        "Long QT Syndrome LQTS Genetic Subtypes Avoid Drugs",
        "Brugada Syndrome Sodium Channel ICD Risk",
        "Heart Failure Preserved Ejection HFpEF SGLT2",
        "Cardiac Tamponade Echocardiography Pericardiocentesis",
        "Constrictive Pericarditis CT MRI Pericardiectomy",
        "Hypertrophic Cardiomyopathy Obstructive Mavacamten",
        "Dilated Cardiomyopathy Gene Mutations LBBB Resync",
        "Arrhythmogenic Cardiomyopathy ARVC Epsilon Wave",
        "Cardiac Amyloidosis TTR Light Chain Tafamidis",
        "Aortic Stenosis Severe Low Flow Gradient TAVR",
        "Mitral Regurgitation Primary Secondary MitraClip",
        "Mitral Stenosis Rheumatic MVA Gradient Commissurotomy",
        "Aortic Regurgitation Chronic Acute Vasodilator Surgery",
        "Pulmonary Hypertension WHO Groups ERA PDE5",
        "Aortic Dissection Type A B Stanford Surgery Medical",
        "Abdominal Aortic Aneurysm Surveillance EVAR Open",
        "Peripheral Artery Disease ABI Revascularization",
        "Deep Vein Thrombosis Proximal Anticoagulation IVC Filter",
        "Pulmonary Embolism Massive Submassive Thrombolytics",
        "Cardiac Arrest ACLS Algorithm ROSC Post-Care",
        "Cardiogenic Shock Hemodynamic Support Impella IABP",
        "Myocarditis Cardiac MRI Biopsy Endomyocardial",
        "Congestive Heart Failure Acute Decompensated Diuresis",
        "Takotsubo Syndrome Stress Cardiomyopathy Apical Balloon",
    ],

    # ── Neurology specific ─────────────────────────────────────────────────────
    "neurology-advanced": [
        "Ischemic Stroke tPA Thrombectomy Window Exclusions",
        "Hemorrhagic Stroke Hypertension Reversal Surgery",
        "Subarachnoid Hemorrhage Hunt Hess Nimodipine Vasospasm",
        "Transient Ischemic Attack ABCD2 Score Dual Antiplatelet",
        "Multiple Sclerosis Relapsing Remitting High Efficacy DMT",
        "Neuromyelitis Optica Aquaporin-4 Rituximab",
        "Parkinson Disease Levodopa Dyskinesia Deep Brain",
        "Dementia with Lewy Bodies Alpha-Synuclein Antipsychotic",
        "Frontotemporal Dementia Behavior Language Variants",
        "Alzheimer Disease Amyloid PET Lecanemab MMSE",
        "Epilepsy Drug Resistant Surgery Vagus Nerve Stimulator",
        "Status Epilepticus Refractory Treatment Protocol",
        "Myasthenia Gravis Thymectomy Pyridostigmine Crisis",
        "Guillain Barre Syndrome IVIG Plasmapheresis Variants",
        "Peripheral Neuropathy Length Dependent Evaluation",
        "Diabetic Neuropathy Duloxetine Pregabalin Topical",
        "Carpal Tunnel Syndrome Splint Steroid Surgery",
        "Migraine Triptans CGRP Preventive Acute Treatment",
        "Cluster Headache Oxygen Verapamil Preventive",
        "Trigeminal Neuralgia Carbamazepine Microvascular",
        "Bell Palsy Facial Nerve Prednisone Acyclovir",
        "Benign Paroxysmal Positional Vertigo Epley Maneuver",
        "Meniere Disease Hydrops Low Sodium Gentamicin",
        "Idiopathic Intracranial Hypertension Acetazolamide",
        "ALS Amyotrophic Lateral Sclerosis Riluzole Edaravone",
        "Huntington Disease Tetrabenazine Genetic Testing",
        "Cerebral Venous Sinus Thrombosis Anticoagulation",
        "Brain Abscess Empiric Antibiotics Surgery Threshold",
        "Neuroleptic Malignant Syndrome vs Serotonin Syndrome",
        "Functional Neurological Disorder Psychotherapy",
    ],
}

# Merge base + new topics
ALL_TOPICS: dict[str, list[str]] = {**BASE_TOPICS, **NEW_TOPICS}

# Load discovered topics from discover_topics.py (if file exists)
_EXTRA_FILE = os.path.join(os.path.dirname(__file__), "topics_extra.json")
if os.path.exists(_EXTRA_FILE):
    with open(_EXTRA_FILE) as _f:
        for _cat, _topics in json.load(_f).items():
            ALL_TOPICS.setdefault(_cat, [])
            _existing_set = {t.lower() for t in ALL_TOPICS[_cat]}
            for _t in _topics:
                if _t.lower() not in _existing_set:
                    ALL_TOPICS[_cat].append(_t)
                    _existing_set.add(_t.lower())

STOP = {"and", "the", "of", "in", "with", "vs", "versus", "its", "for",
        "or", "a", "an", "to", "from", "on", "at", "by", "as", "during",
        "after", "before", "using", "via", "per"}


# ── Smart pre-filter: load existing articles once at startup ──────────────────

def load_existing_keys(conn) -> set[str]:
    """Load slug-derived keys for all published articles — O(1) duplicate check."""
    existing = set()
    with conn.cursor() as cur:
        cur.execute("SELECT slug, title FROM articles WHERE is_published = true")
        for slug, title in cur.fetchall():
            # Key from slug (first 2 significant slug segments)
            parts = [w for w in slug.split("-") if w not in STOP and len(w) > 1]
            if parts:
                existing.add("-".join(parts[:2]))
            # Key from title words
            words = [w for w in re.split(r"[\s\-]+", title.lower()) if w not in STOP and len(w) > 1]
            if words:
                existing.add("-".join(words[:2]))
    return existing


def topic_key(topic: str) -> str:
    words = [w for w in re.split(r"[\s\-]+", topic.lower()) if w not in STOP and len(w) > 1]
    return "-".join(words[:2])


def build_pending_topics(conn, category_filter: str | None) -> list[tuple[str, str]]:
    """Return list of (category, topic) not yet in DB."""
    existing = load_existing_keys(conn)
    log.info("DB has %d existing article keys", len(existing))

    pending = []
    total_topics = 0
    for cat, topics in ALL_TOPICS.items():
        if category_filter and cat != category_filter:
            continue
        for topic in topics:
            total_topics += 1
            if topic_key(topic) not in existing:
                pending.append((cat, topic))

    log.info("Topics checked: %d | Pending (not in DB): %d | Already exist: %d",
             total_topics, len(pending), total_topics - len(pending))
    return pending


# ── Gemini KeyRotator ─────────────────────────────────────────────────────────

class GeminiKeyRotator:
    def __init__(self, keys: list[str]):
        self.keys = [k for k in keys if k]
        self.idx = 0
        self.exhausted: set[int] = set()
        self.requests: dict[int, int] = {i: 0 for i in range(len(self.keys))}

    @property
    def current(self) -> str:
        return self.keys[self.idx]

    @property
    def active_count(self) -> int:
        return len(self.keys) - len(self.exhausted)

    def rotate(self, exhausted: bool = False) -> bool:
        """Switch to next active key. Returns False if all exhausted."""
        if exhausted:
            self.exhausted.add(self.idx)
            log.warning("  Key %d/%d daily limit — marking exhausted",
                        self.idx + 1, len(self.keys))
        for _ in range(len(self.keys)):
            self.idx = (self.idx + 1) % len(self.keys)
            if self.idx not in self.exhausted:
                log.info("  Switched to key %d/%d", self.idx + 1, len(self.keys))
                return True
        return False  # all exhausted

    def wait_for_reset(self):
        import datetime as _dt
        now = _dt.datetime.utcnow()
        tomorrow = (now + _dt.timedelta(days=1)).replace(hour=0, minute=2, second=0, microsecond=0)
        wait_sec = int((tomorrow - now).total_seconds())
        h, m = wait_sec // 3600, (wait_sec % 3600) // 60
        log.info("=" * 60)
        log.info("ALL GEMINI KEYS EXHAUSTED — sleeping %dh %dm until %s UTC",
                 h, m, tomorrow.strftime("%H:%M"))
        log.info("Status: %s", self.status())
        log.info("=" * 60)
        time.sleep(wait_sec)
        self.exhausted.clear()
        self.idx = 0
        log.info("Daily limits reset — resuming with all %d Gemini keys", len(self.keys))

    def record(self):
        self.requests[self.idx] = self.requests.get(self.idx, 0) + 1

    def status(self) -> str:
        parts = []
        for i, _ in enumerate(self.keys):
            tag = "✓" if i not in self.exhausted else "✗"
            parts.append(f"key{i+1}:{tag}({self.requests.get(i,0)}req)")
        return " | ".join(parts)


from article_prompt import ARTICLE_PROMPT


def _parse_output(content: str) -> dict | None:
    title_m = re.search(r"^TITLE:\s*(.+)$", content, re.MULTILINE)
    if not title_m:
        return None
    title = title_m.group(1).strip().strip('"')

    excerpt_m = re.search(
        r"^EXCERPT:\s*(.+?)(?=\nARTICLE_START|\n\n## |\nARTICLE_END)",
        content, re.MULTILINE | re.DOTALL
    )
    excerpt = excerpt_m.group(1).strip() if excerpt_m else ""

    body_m = re.search(r"ARTICLE_START\s*\n(.*?)(?:ARTICLE_END|$)", content, re.DOTALL)
    if not body_m:
        body_m2 = re.search(r"(## Key Points.*)", content, re.DOTALL)
        body_text = body_m2.group(1).strip() if body_m2 else ""
    else:
        body_text = body_m.group(1).strip()

    if not body_text or len(body_text) < 400:
        return None
    return {"title": title, "excerpt": excerpt, "body_text": body_text}


# ── Gemini API call with key rotation ────────────────────────────────────────

def generate_with_gemini(topic: str, category: str, model: str,
                         rotator: GeminiKeyRotator) -> dict | None:
    prompt = ARTICLE_PROMPT.format(topic=topic, category=category)
    consecutive_429 = 0

    while True:
        if rotator.active_count == 0:
            rotator.wait_for_reset()
            consecutive_429 = 0

        api_key = rotator.current
        url = GEMINI_URL.format(model=model)
        try:
            resp = httpx.post(
                url,
                params={"key": api_key},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.3,
                        "maxOutputTokens": 8192,
                        "topP": 0.9,
                    },
                    "safetySettings": [
                        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT",  "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_HARASSMENT",          "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_HATE_SPEECH",         "threshold": "BLOCK_NONE"},
                        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",   "threshold": "BLOCK_NONE"},
                    ],
                },
                timeout=120,
            )

            if resp.status_code == 429:
                consecutive_429 += 1
                try:
                    err_body = resp.json()
                    err = err_body.get("error", {})
                    err_msg = err.get("message", "")
                    # Parse actual retry delay from message text (Gemini puts it there, not in header)
                    retry_match = re.search(r"retry in (\d+\.?\d*)\s*s", err_msg.lower())
                    retry_seconds = float(retry_match.group(1)) if retry_match else 0
                    # Check violations: only "PerDay" quotaId → real daily exhaustion
                    is_daily = False
                    for detail in err.get("details", []):
                        for v in detail.get("violations", []):
                            if "PerDay" in v.get("quotaId", ""):
                                is_daily = True
                                break
                except Exception:
                    err_msg = resp.text[:200]
                    retry_seconds = 0
                    is_daily = False

                # Daily limit exhausted → mark key, rotate, outer while handles wait
                if is_daily:
                    rotator.rotate(exhausted=True)
                    consecutive_429 = 0
                    continue  # outer while: active_count==0 → wait_for_reset

                # Temporary RPM/TPM limit → wait suggested retry time, same key
                if retry_seconds and retry_seconds < 300:
                    log.warning("  Rate limit — waiting %.0fs (key %d/%d)",
                                retry_seconds + 2, rotator.idx + 1, len(rotator.keys))
                    time.sleep(retry_seconds + 2)
                    consecutive_429 = 0
                    continue

                # All keys hit RPM simultaneously → back off before rotating
                if consecutive_429 >= len(rotator.keys):
                    wait = min(60, consecutive_429 * 5)
                    log.warning("  All Gemini keys rate-limited — backing off %ds", wait)
                    time.sleep(wait)
                    consecutive_429 = 0
                    continue

                # Generic 429 — small pause then rotate
                log.warning("  429 — switching key [%s]", err_msg[:80])
                time.sleep(4)
                rotator.rotate(exhausted=False)
                continue

            consecutive_429 = 0

            if resp.status_code == 400:
                log.error("  Gemini 400 (bad request): %s", resp.text[:300])
                return None

            if resp.status_code == 403:
                log.error("  Key %d invalid/forbidden — marking exhausted", rotator.idx + 1)
                rotator.rotate(exhausted=True)
                continue

            if resp.status_code == 503:
                log.warning("  Gemini 503 overloaded — waiting 30s")
                time.sleep(30)
                continue

            if resp.status_code != 200:
                log.error("Gemini error %s: %s", resp.status_code, resp.text[:300])
                return None

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                # Safety block or empty response
                finish = data.get("promptFeedback", {}).get("blockReason", "unknown")
                log.warning("  Gemini returned no candidates (blockReason=%s)", finish)
                return None

            content = candidates[0]["content"]["parts"][0]["text"]
            usage = data.get("usageMetadata", {})
            log.info("  Tokens: %d in / %d out [key %d/%d]",
                     usage.get("promptTokenCount", 0),
                     usage.get("candidatesTokenCount", 0),
                     rotator.idx + 1, len(rotator.keys))

            rotator.record()
            result = _parse_output(content)
            if not result:
                log.error("Parse failed — preview: %s", content[:300])
            return result

        except httpx.TimeoutException:
            log.error("Gemini timeout for '%s' (key %d)", topic, rotator.idx + 1)
            return None
        except Exception as e:
            log.error("Gemini call failed: %s", e)
            return None


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="MedMind Gemini Article Generator")
    parser.add_argument("--limit",        type=int, default=50,  help="Max articles to generate")
    parser.add_argument("--model",        type=str, default=DEFAULT_MODEL)
    parser.add_argument("--category",     type=str, default=None, help="Only this category slug")
    parser.add_argument("--dry-run",      action="store_true", help="Show pending topics, no generation")
    parser.add_argument("--list-topics",  action="store_true", help="Count topics per category")
    parser.add_argument("--delay",        type=float, default=4.0, help="Seconds between articles (Gemini RPM=15)")
    parser.add_argument("--no-phase2",    action="store_true", help="Skip shallow article regeneration")
    args = parser.parse_args()

    if args.list_topics:
        print("\nAll categories and topic counts:\n")
        for cat, topics in sorted(ALL_TOPICS.items()):
            mark = " [NEW]" if cat in NEW_TOPICS else ""
            print(f"  {cat:<28} {len(topics):3d} topics{mark}")
        total = sum(len(t) for t in ALL_TOPICS.values())
        print(f"\n  Total: {total} topics across {len(ALL_TOPICS)} categories\n")
        return

    # ── Load API keys ──────────────────────────────────────────────────────────
    keys: list[str] = []
    env_vars = ["GEMINI_API_KEY"] + [f"GEMINI_API_KEY_{i}" for i in range(2, 10)]

    env_file = os.path.join(os.path.dirname(__file__), "backend", ".env.prod")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                for var in env_vars:
                    if line.startswith(f"{var}="):
                        val = line.split("=", 1)[1].strip()
                        if val and val not in keys:
                            keys.append(val)

    for var in env_vars:
        val = os.environ.get(var, "")
        if val and val not in keys:
            keys.append(val)

    if not keys:
        print("\n❌  No GEMINI_API_KEY configured!")
        print("Add to backend/.env.prod: GEMINI_API_KEY=AIzaSy...")
        sys.exit(1)

    # ── Verify keys ────────────────────────────────────────────────────────────
    # 429 = rate-limited but valid; 400/403 = actually invalid
    valid_keys = []
    for k in keys:
        try:
            test = httpx.post(
                GEMINI_URL.format(model=args.model),
                params={"key": k},
                json={"contents": [{"parts": [{"text": "Say OK"}]}],
                      "generationConfig": {"maxOutputTokens": 3}},
                timeout=15,
            )
            if test.status_code == 200:
                valid_keys.append(k)
                log.info("  ✓ Key %d/%d valid (active): %s...", len(valid_keys), len(keys), k[:20])
            elif test.status_code == 429:
                # Rate-limited = key exists and is valid, just hit quota
                valid_keys.append(k)
                log.info("  ✓ Key %d/%d valid (rate-limited): %s...", len(valid_keys), len(keys), k[:20])
            elif test.status_code in (400, 403):
                log.warning("  ✗ Key invalid/forbidden: %s... (HTTP %s)", k[:20], test.status_code)
            else:
                log.warning("  ? Key status unclear: %s... (HTTP %s)", k[:20], test.status_code)
                valid_keys.append(k)  # include anyway, will fail gracefully during generation
        except Exception as e:
            log.warning("  ✗ Key check failed: %s... (%s)", k[:20], e)

    if not valid_keys:
        print("\n❌  No valid Gemini API keys (400/403 on all keys).\n")
        sys.exit(1)

    rotator = GeminiKeyRotator(valid_keys)
    log.info("Gemini Article Generator | model=%s | keys=%d | delay=%.1fs",
             args.model, len(valid_keys), args.delay)

    # ── Connect to DB and build pending topic list ─────────────────────────────
    conn = psycopg2.connect(DB_URL)

    if args.dry_run:
        pending = build_pending_topics(conn, args.category)
        conn.close()
        print(f"\nPending topics ({len(pending)} total):\n")
        by_cat: dict[str, list[str]] = {}
        for cat, topic in pending:
            by_cat.setdefault(cat, []).append(topic)
        for cat, topics in sorted(by_cat.items()):
            print(f"\n{cat.upper()} ({len(topics)} pending):")
            for t in topics[:10]:
                print(f"  - {t}")
            if len(topics) > 10:
                print(f"  ... and {len(topics) - 10} more")
        return

    pending = build_pending_topics(conn, args.category)
    if not pending:
        log.info("No pending topics — all already generated! Proceeding to Phase 2.")

    # In-memory set of generated topic keys — updated after each success so a
    # parallel Groq process doesn't waste API calls on the same topic
    generated_keys: set[str] = set()

    count = errors = skipped = 0

    def _reload_pending_if_needed():
        """Reload pending list if topics_extra.json was updated by discover_topics.py."""
        if not os.path.exists(_EXTRA_FILE):
            return pending
        mtime = os.path.getmtime(_EXTRA_FILE)
        if not hasattr(_reload_pending_if_needed, "_last_mtime"):
            _reload_pending_if_needed._last_mtime = mtime
            return pending
        if mtime > _reload_pending_if_needed._last_mtime:
            _reload_pending_if_needed._last_mtime = mtime
            new_pending = build_pending_topics(conn, args.category)
            added = [t for t in new_pending if topic_key(t[1]) not in generated_keys]
            if added:
                log.info("topics_extra.json updated — added %d new pending topics", len(added))
                pending.extend(added)
        return pending

    phase1_limit = min(args.limit, len(pending)) if pending else 0
    log.info("Phase 1: generating %d articles (limit=%d, pending=%d)",
             phase1_limit, args.limit, len(pending))

    for i, (category, topic) in enumerate(pending):
        if count >= args.limit:
            break

        # Skip if already generated this session (prevents Groq/Gemini overlap)
        if topic_key(topic) in generated_keys:
            continue

        _reload_pending_if_needed()

        log.info("[%d/%d] %s / %s", count + 1, args.limit, category, topic)

        t0 = time.time()
        data = generate_with_gemini(topic, category, args.model, rotator)
        elapsed = time.time() - t0

        if not data or not data.get("title") or not data.get("body_text"):
            log.warning("  ✗ Generation failed (%.1fs)", elapsed)
            errors += 1
            continue

        title   = data["title"]
        excerpt = data.get("excerpt", "")
        body    = text_to_blocks(data["body_text"])
        slug    = slugify(title)

        log.info("  Generated: '%s' (%.1fs, %d blocks)", title[:60], elapsed, len(body))

        article_id = str(uuid.uuid4())
        saved = save_article(conn, article_id, slug, title, excerpt, body, category)
        if not saved:
            alt_slug = slugify(f"{title} {category}")[:90]
            saved = save_article(conn, article_id, alt_slug, title, excerpt, body, category)
        if not saved:
            log.info("  -- Slug conflict, skipping")
            skipped += 1
            continue

        # Update generated_by to 'gemini'
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE articles SET generated_by='gemini' WHERE id=%s", (article_id,))
            conn.commit()
        except Exception:
            conn.rollback()

        generated_keys.add(topic_key(topic))  # mark so Groq doesn't repeat it
        n_tr = save_translations(conn, article_id, title, excerpt, body)
        log.info("  ✓ Published + %d translations | %s", n_tr, slug)

        if _HAS_COVER:
            try:
                cover_url = _fetch_cover_image(title, category)
                if cover_url:
                    with conn.cursor() as cur:
                        cur.execute("UPDATE articles SET cover_image=%s WHERE id=%s",
                                    (cover_url, article_id))
                    conn.commit()
                    log.info("  Cover: %s", cover_url[:60])
            except Exception as e:
                log.warning("  Cover failed: %s", e)

        if _HAS_OG:
            try:
                _gen_og_image(slug, title, category, calc_reading_time(body))
            except Exception:
                pass

        notify_indexnow(slug)
        count += 1
        time.sleep(args.delay)

    log.info("Phase 1 done. Generated: %d | Skipped: %d | Errors: %d", count, skipped, errors)

    # ── Phase 2: regenerate shallow articles ───────────────────────────────────
    if not args.no_phase2:
        log.info("=" * 60)
        log.info("Phase 2: regenerating shallow articles (reading_time_minutes <= 3)...")
        log.info("=" * 60)
        regen_count = regen_errors = 0

        while True:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, title, excerpt, category
                    FROM articles
                    WHERE reading_time_minutes <= 3
                      AND is_published = true
                      AND generated_by IN ('ollama-qwen3', 'groq', 'gemini')
                    ORDER BY created_at ASC
                    LIMIT 50
                """)
                rows = cur.fetchall()

            if not rows:
                log.info("Phase 2 complete — no more shallow articles.")
                break

            log.info("Phase 2 batch: %d shallow articles", len(rows))
            for art_id, art_title, art_excerpt, art_cat in rows:
                log.info("  [regen] %s / %s", art_cat, art_title[:60])
                t0 = time.time()
                data = generate_with_gemini(art_title, art_cat, args.model, rotator)
                elapsed = time.time() - t0

                if not data or not data.get("body_text"):
                    log.warning("  ✗ Regen failed (%.1fs)", elapsed)
                    regen_errors += 1
                    continue

                new_body    = text_to_blocks(data["body_text"])
                new_title   = data.get("title") or art_title
                new_excerpt = data.get("excerpt") or art_excerpt
                rt = calc_reading_time(new_body)

                if update_article(conn, art_id, new_title, new_excerpt, new_body):
                    try:
                        with conn.cursor() as cur:
                            cur.execute("UPDATE articles SET generated_by='gemini' WHERE id=%s",
                                        (art_id,))
                        conn.commit()
                    except Exception:
                        conn.rollback()
                    save_translations(conn, art_id, new_title, new_excerpt, new_body)
                    log.info("  ✓ Regenerated: '%s' (%d min, %.1fs)", new_title[:55], rt, elapsed)
                    regen_count += 1
                else:
                    regen_errors += 1
                time.sleep(args.delay)

        log.info("Phase 2 done. Regenerated: %d | Errors: %d", regen_count, regen_errors)

    conn.close()
    log.info("=" * 60)
    log.info("All done. Generated: %d | Shallow improved: %d", count,
             locals().get("regen_count", 0))
    log.info("Key usage: %s", rotator.status())


if __name__ == "__main__":
    main()
