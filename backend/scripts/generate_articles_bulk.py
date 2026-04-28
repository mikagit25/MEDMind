"""
MedMind AI — Bulk article generation script.

Generates medical articles via the local backend API (must be running).

Usage:
    # Generate all topics (default — all categories)
    python -m scripts.generate_articles_bulk

    # One specific category
    python -m scripts.generate_articles_bulk --category diseases

    # Limit count per run
    python -m scripts.generate_articles_bulk --limit 20

    # Use Sonnet for higher quality (slower, costs more)
    python -m scripts.generate_articles_bulk --model sonnet

    # Dry run — just print topics without generating
    python -m scripts.generate_articles_bulk --dry-run

    # Skip already-existing slugs check (faster, may create duplicates)
    python -m scripts.generate_articles_bulk --no-check

Requirements:
    pip install httpx
    Backend must be running: uvicorn app.main:app --port 8000

    Set ADMIN_EMAIL and ADMIN_PASSWORD as env vars or edit defaults below.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from typing import Any

import httpx

# ── Config ────────────────────────────────────────────────────────────────────
API_BASE    = os.getenv("API_BASE",      "http://localhost:8000/api/v1")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL",   "admin@medmind.ai")
ADMIN_PASS  = os.getenv("ADMIN_PASSWORD","adminpass123")

# Delay between requests (seconds). Haiku: 3s is safe. Sonnet: 8s.
DELAY_HAIKU  = 4
DELAY_SONNET = 10

# ── Topic list (category → [(topic, schema_type)]) ───────────────────────────
# schema_type: MedicalCondition | Drug | MedicalProcedure | MedicalWebPage
TOPICS: dict[str, list[tuple[str, str]]] = {

    "diseases": [
        ("Myocardial Infarction (Heart Attack)", "MedicalCondition"),
        ("Type 2 Diabetes Mellitus", "MedicalCondition"),
        ("Arterial Hypertension", "MedicalCondition"),
        ("Ischemic Stroke", "MedicalCondition"),
        ("Community-Acquired Pneumonia", "MedicalCondition"),
        ("Chronic Obstructive Pulmonary Disease (COPD)", "MedicalCondition"),
        ("Bronchial Asthma", "MedicalCondition"),
        ("Heart Failure", "MedicalCondition"),
        ("Atrial Fibrillation", "MedicalCondition"),
        ("Deep Vein Thrombosis", "MedicalCondition"),
        ("Pulmonary Embolism", "MedicalCondition"),
        ("Acute Pancreatitis", "MedicalCondition"),
        ("Liver Cirrhosis", "MedicalCondition"),
        ("Peptic Ulcer Disease", "MedicalCondition"),
        ("Crohn's Disease", "MedicalCondition"),
        ("Ulcerative Colitis", "MedicalCondition"),
        ("Rheumatoid Arthritis", "MedicalCondition"),
        ("Systemic Lupus Erythematosus", "MedicalCondition"),
        ("Multiple Sclerosis", "MedicalCondition"),
        ("Parkinson's Disease", "MedicalCondition"),
        ("Alzheimer's Disease", "MedicalCondition"),
        ("Epilepsy", "MedicalCondition"),
        ("Migraine", "MedicalCondition"),
        ("Hypothyroidism", "MedicalCondition"),
        ("Hyperthyroidism (Graves Disease)", "MedicalCondition"),
        ("Cushing's Syndrome", "MedicalCondition"),
        ("Adrenal Insufficiency (Addison's Disease)", "MedicalCondition"),
        ("Chronic Kidney Disease", "MedicalCondition"),
        ("Nephrotic Syndrome", "MedicalCondition"),
        ("Anemia — Classification and Management", "MedicalCondition"),
        ("Iron Deficiency Anemia", "MedicalCondition"),
        ("Sepsis and Septic Shock", "MedicalCondition"),
        ("HIV/AIDS — Clinical Management", "MedicalCondition"),
        ("Tuberculosis", "MedicalCondition"),
        ("Pneumonia — Differential Diagnosis", "MedicalCondition"),
        ("Acute Respiratory Distress Syndrome (ARDS)", "MedicalCondition"),
        ("Osteoporosis", "MedicalCondition"),
        ("Gout", "MedicalCondition"),
        ("Psoriasis", "MedicalCondition"),
        ("Eczema (Atopic Dermatitis)", "MedicalCondition"),
    ],

    "cardiology": [
        ("Stable Angina Pectoris", "MedicalCondition"),
        ("Unstable Angina and NSTEMI", "MedicalCondition"),
        ("STEMI — ST-Elevation Myocardial Infarction", "MedicalCondition"),
        ("Aortic Stenosis", "MedicalCondition"),
        ("Mitral Valve Regurgitation", "MedicalCondition"),
        ("Dilated Cardiomyopathy", "MedicalCondition"),
        ("Hypertrophic Cardiomyopathy", "MedicalCondition"),
        ("Infective Endocarditis", "MedicalCondition"),
        ("Pericarditis and Cardiac Tamponade", "MedicalCondition"),
        ("Ventricular Tachycardia", "MedicalCondition"),
        ("ECG Interpretation — A Clinical Guide", "MedicalWebPage"),
        ("Heart Block — Types and Management", "MedicalCondition"),
        ("Aortic Dissection", "MedicalCondition"),
        ("Peripheral Arterial Disease", "MedicalCondition"),
        ("Cardiac Arrest and Resuscitation Principles", "MedicalWebPage"),
    ],

    "neurology": [
        ("Hemorrhagic Stroke (Intracerebral Hemorrhage)", "MedicalCondition"),
        ("Subarachnoid Hemorrhage", "MedicalCondition"),
        ("Transient Ischemic Attack (TIA)", "MedicalCondition"),
        ("Meningitis — Bacterial and Viral", "MedicalCondition"),
        ("Encephalitis", "MedicalCondition"),
        ("Guillain-Barré Syndrome", "MedicalCondition"),
        ("Amyotrophic Lateral Sclerosis (ALS)", "MedicalCondition"),
        ("Brain Tumor — Glioblastoma", "MedicalCondition"),
        ("Cerebral Venous Sinus Thrombosis", "MedicalCondition"),
        ("Peripheral Neuropathy", "MedicalCondition"),
        ("Myasthenia Gravis", "MedicalCondition"),
        ("Cluster Headache", "MedicalCondition"),
        ("Spinal Cord Injury — Management", "MedicalCondition"),
        ("Dementia — Clinical Approach", "MedicalWebPage"),
        ("Status Epilepticus", "MedicalCondition"),
    ],

    "drugs": [
        ("Aspirin — Mechanism, Uses and Dosing", "Drug"),
        ("Metformin — Pharmacology and Clinical Use", "Drug"),
        ("Atorvastatin — Statins in Cardiovascular Disease", "Drug"),
        ("Lisinopril — ACE Inhibitors Clinical Guide", "Drug"),
        ("Amlodipine — Calcium Channel Blockers", "Drug"),
        ("Metoprolol — Beta-Blockers in Cardiology", "Drug"),
        ("Warfarin — Anticoagulation Management", "Drug"),
        ("Rivaroxaban — Direct Oral Anticoagulants", "Drug"),
        ("Amoxicillin — Penicillin Antibiotics", "Drug"),
        ("Ciprofloxacin — Fluoroquinolone Antibiotics", "Drug"),
        ("Vancomycin — Glycopeptide Antibiotics", "Drug"),
        ("Dexamethasone — Corticosteroids in Medicine", "Drug"),
        ("Furosemide — Loop Diuretics", "Drug"),
        ("Omeprazole — Proton Pump Inhibitors", "Drug"),
        ("Insulin Therapy — Types and Protocols", "Drug"),
        ("Morphine — Opioid Analgesics", "Drug"),
        ("Paracetamol (Acetaminophen) — Uses and Overdose", "Drug"),
        ("Ibuprofen — NSAIDs in Clinical Practice", "Drug"),
        ("Salbutamol (Albuterol) — Beta-2 Agonists", "Drug"),
        ("Prednisolone — Oral Corticosteroids", "Drug"),
        ("Digoxin — Cardiac Glycosides", "Drug"),
        ("Heparin — Unfractionated and LMWH", "Drug"),
        ("Amiodarone — Antiarrhythmic Therapy", "Drug"),
        ("Clopidogrel — Antiplatelet Therapy", "Drug"),
        ("Ondansetron — Antiemetics", "Drug"),
    ],

    "procedures": [
        ("Cardiopulmonary Resuscitation (CPR)", "MedicalProcedure"),
        ("Endotracheal Intubation", "MedicalProcedure"),
        ("Central Venous Catheter Insertion", "MedicalProcedure"),
        ("Lumbar Puncture", "MedicalProcedure"),
        ("Thoracentesis", "MedicalProcedure"),
        ("Paracentesis", "MedicalProcedure"),
        ("Arterial Blood Gas — Sampling and Interpretation", "MedicalProcedure"),
        ("Urinary Catheterization", "MedicalProcedure"),
        ("Nasogastric Tube Insertion", "MedicalProcedure"),
        ("Chest Tube Insertion (Thoracostomy)", "MedicalProcedure"),
        ("Defibrillation and Cardioversion", "MedicalProcedure"),
        ("Intraosseous Access", "MedicalProcedure"),
        ("Wound Closure Techniques — Suturing", "MedicalProcedure"),
        ("Pericardiocentesis", "MedicalProcedure"),
        ("Mechanical Ventilation — Setting Up and Monitoring", "MedicalProcedure"),
    ],

    "symptoms": [
        ("Chest Pain — Differential Diagnosis Approach", "MedicalWebPage"),
        ("Dyspnea (Shortness of Breath) — Clinical Approach", "MedicalWebPage"),
        ("Headache — Differential Diagnosis", "MedicalWebPage"),
        ("Fever — Evaluation and Management", "MedicalWebPage"),
        ("Syncope — Causes and Workup", "MedicalWebPage"),
        ("Abdominal Pain — Diagnostic Approach", "MedicalWebPage"),
        ("Dizziness and Vertigo — Differential Diagnosis", "MedicalWebPage"),
        ("Palpitations — Clinical Evaluation", "MedicalWebPage"),
        ("Edema — Causes and Approach", "MedicalWebPage"),
        ("Hemoptysis — Causes and Management", "MedicalWebPage"),
        ("Hematuria — Clinical Approach", "MedicalWebPage"),
        ("Jaundice — Differential Diagnosis", "MedicalWebPage"),
        ("Weight Loss — Unintentional, Causes and Workup", "MedicalWebPage"),
        ("Back Pain — Red Flags and Management", "MedicalWebPage"),
        ("Cough — Acute and Chronic Differential", "MedicalWebPage"),
    ],

    "diagnostics": [
        ("Complete Blood Count (CBC) — Interpretation Guide", "MedicalWebPage"),
        ("Liver Function Tests — Clinical Interpretation", "MedicalWebPage"),
        ("Renal Function Tests — BUN and Creatinine", "MedicalWebPage"),
        ("Troponin in Acute Coronary Syndrome", "MedicalWebPage"),
        ("D-dimer — Uses and Limitations", "MedicalWebPage"),
        ("Chest X-Ray Interpretation — Systematic Approach", "MedicalWebPage"),
        ("ECG — Reading and Interpretation Basics", "MedicalWebPage"),
        ("Arterial Blood Gas Interpretation", "MedicalWebPage"),
        ("Coagulation Studies — PT, INR, aPTT", "MedicalWebPage"),
        ("Thyroid Function Tests — TSH, T3, T4", "MedicalWebPage"),
        ("HbA1c — Diabetes Monitoring", "MedicalWebPage"),
        ("Urinalysis — Interpretation Guide", "MedicalWebPage"),
        ("Chest CT Scan — When to Order and How to Read", "MedicalWebPage"),
        ("Echocardiography — Indications and Findings", "MedicalWebPage"),
        ("Lumbar Puncture — CSF Analysis Interpretation", "MedicalWebPage"),
    ],

    "emergency": [
        ("Anaphylaxis — Recognition and Emergency Management", "MedicalCondition"),
        ("Diabetic Ketoacidosis (DKA)", "MedicalCondition"),
        ("Hyperosmolar Hyperglycemic State (HHS)", "MedicalCondition"),
        ("Hypertensive Emergency", "MedicalCondition"),
        ("Acute Asthma Exacerbation", "MedicalCondition"),
        ("Status Asthmaticus", "MedicalCondition"),
        ("Tension Pneumothorax", "MedicalCondition"),
        ("Acute Upper GI Bleeding", "MedicalCondition"),
        ("Acute Liver Failure", "MedicalCondition"),
        ("Hyperkalemia — Emergency Management", "MedicalCondition"),
        ("Hypoglycemia — Recognition and Treatment", "MedicalCondition"),
        ("Stroke — Acute Management and tPA Protocol", "MedicalCondition"),
        ("Major Trauma — Primary Survey ABCDE", "MedicalWebPage"),
        ("Burns — Classification and Initial Management", "MedicalCondition"),
        ("Overdose and Poisoning — General Approach", "MedicalWebPage"),
    ],

    "oncology": [
        ("Lung Cancer — NSCLC and SCLC", "MedicalCondition"),
        ("Breast Cancer — Diagnosis and Treatment", "MedicalCondition"),
        ("Colorectal Cancer", "MedicalCondition"),
        ("Prostate Cancer", "MedicalCondition"),
        ("Leukemia — AML, CML, ALL, CLL Overview", "MedicalCondition"),
        ("Lymphoma — Hodgkin and Non-Hodgkin", "MedicalCondition"),
        ("Pancreatic Cancer", "MedicalCondition"),
        ("Hepatocellular Carcinoma", "MedicalCondition"),
        ("Cervical Cancer and HPV", "MedicalCondition"),
        ("Melanoma — Diagnosis and Staging", "MedicalCondition"),
        ("Cancer Pain Management", "MedicalWebPage"),
        ("Chemotherapy Side Effects — Management Guide", "MedicalWebPage"),
        ("Tumor Markers — Clinical Utility", "MedicalWebPage"),
    ],

    "infectious-diseases": [
        ("COVID-19 — Clinical Features and Management", "MedicalCondition"),
        ("Influenza — Diagnosis and Antiviral Therapy", "MedicalCondition"),
        ("Urinary Tract Infection (UTI)", "MedicalCondition"),
        ("Cellulitis and Skin Infections", "MedicalCondition"),
        ("Septic Arthritis", "MedicalCondition"),
        ("Hepatitis B — Virology and Treatment", "MedicalCondition"),
        ("Hepatitis C — Diagnosis and DAA Therapy", "MedicalCondition"),
        ("Malaria — Diagnosis and Treatment", "MedicalCondition"),
        ("Lyme Disease", "MedicalCondition"),
        ("Clostridioides difficile Infection", "MedicalCondition"),
        ("Antibiotic Resistance — MRSA and ESBL", "MedicalWebPage"),
        ("Antimicrobial Stewardship Principles", "MedicalWebPage"),
    ],

    "nutrition": [
        ("Nutritional Assessment in Clinical Practice", "MedicalWebPage"),
        ("Parenteral Nutrition — Indications and Monitoring", "MedicalWebPage"),
        ("Vitamin D Deficiency and Supplementation", "MedicalCondition"),
        ("Vitamin B12 Deficiency", "MedicalCondition"),
        ("Obesity — Medical Management and Comorbidities", "MedicalCondition"),
        ("Malnutrition in Hospitalized Patients", "MedicalCondition"),
        ("Mediterranean Diet and Cardiovascular Risk", "MedicalWebPage"),
        ("Dietary Management of Type 2 Diabetes", "MedicalWebPage"),
        ("Eating Disorders — Anorexia and Bulimia", "MedicalCondition"),
        ("Micronutrient Deficiencies — Global Overview", "MedicalWebPage"),
    ],

    "pediatrics": [
        ("Febrile Seizures in Children", "MedicalCondition"),
        ("Kawasaki Disease", "MedicalCondition"),
        ("Pediatric Asthma Management", "MedicalCondition"),
        ("Acute Otitis Media", "MedicalCondition"),
        ("Croup (Laryngotracheobronchitis)", "MedicalCondition"),
        ("Bronchiolitis in Infants", "MedicalCondition"),
        ("Neonatal Jaundice", "MedicalCondition"),
        ("Pediatric Vaccination Schedule — Evidence-Based Guide", "MedicalWebPage"),
        ("Pediatric Fluid Resuscitation", "MedicalWebPage"),
        ("ADHD — Diagnosis and Management in Children", "MedicalCondition"),
        ("Failure to Thrive", "MedicalCondition"),
        ("Epiglottitis — Emergency Management", "MedicalCondition"),
    ],

    "psychiatry": [
        ("Major Depressive Disorder — Diagnosis and Treatment", "MedicalCondition"),
        ("Bipolar Disorder — Mood Stabilizer Therapy", "MedicalCondition"),
        ("Schizophrenia — Antipsychotic Management", "MedicalCondition"),
        ("Generalized Anxiety Disorder", "MedicalCondition"),
        ("Post-Traumatic Stress Disorder (PTSD)", "MedicalCondition"),
        ("Alcohol Use Disorder — Withdrawal and Management", "MedicalCondition"),
        ("Opioid Use Disorder and MAT", "MedicalCondition"),
        ("Delirium — ICU and Post-Operative", "MedicalCondition"),
        ("Suicide Risk Assessment", "MedicalWebPage"),
        ("Benzodiazepine Use and Dependence", "MedicalWebPage"),
    ],

    "endocrinology": [
        ("Type 1 Diabetes Mellitus", "MedicalCondition"),
        ("Diabetic Complications — Nephropathy, Neuropathy, Retinopathy", "MedicalCondition"),
        ("Metabolic Syndrome", "MedicalCondition"),
        ("Polycystic Ovary Syndrome (PCOS)", "MedicalCondition"),
        ("Primary Hyperaldosteronism (Conn Syndrome)", "MedicalCondition"),
        ("Pheochromocytoma", "MedicalCondition"),
        ("Acromegaly", "MedicalCondition"),
        ("Thyroid Nodule — Evaluation and Management", "MedicalWebPage"),
        ("Thyroid Cancer", "MedicalCondition"),
        ("Hypercalcemia — Causes and Management", "MedicalCondition"),
    ],

    "surgery": [
        ("Appendicitis — Diagnosis and Surgical Management", "MedicalCondition"),
        ("Acute Cholecystitis", "MedicalCondition"),
        ("Inguinal Hernia — Repair Techniques", "MedicalProcedure"),
        ("Bowel Obstruction", "MedicalCondition"),
        ("Perioperative Risk Assessment", "MedicalWebPage"),
        ("Surgical Site Infection Prevention", "MedicalWebPage"),
        ("Abdominal Aortic Aneurysm", "MedicalCondition"),
        ("Laparoscopic Cholecystectomy", "MedicalProcedure"),
        ("Postoperative Complications — Recognition and Management", "MedicalWebPage"),
        ("Wound Care and Debridement", "MedicalProcedure"),
    ],
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def log(msg: str) -> None:
    print(msg, flush=True)


async def get_token(client: httpx.AsyncClient) -> str:
    r = await client.post(
        f"{API_BASE}/auth/login",
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASS},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if r.status_code != 200:
        raise RuntimeError(f"Login failed: {r.status_code} — {r.text}")
    token = r.json().get("access_token")
    if not token:
        raise RuntimeError("No access_token in login response")
    return token


async def fetch_existing_slugs(client: httpx.AsyncClient, token: str) -> set[str]:
    """Get all existing article slugs to skip already-generated ones."""
    r = await client.get(
        f"{API_BASE}/articles/admin/list",
        params={"limit": 1000},
        headers={"Authorization": f"Bearer {token}"},
    )
    if r.status_code != 200:
        log(f"  [warn] Could not fetch existing slugs: {r.status_code}")
        return set()
    data = r.json()
    articles = data if isinstance(data, list) else data.get("articles", [])
    slugs = {a.get("slug", "") for a in articles}
    log(f"  Found {len(slugs)} existing articles in DB.")
    return slugs


def slug_exists(title: str, existing: set[str]) -> bool:
    """Rough check — slugify title and see if something similar exists."""
    import unicodedata, re
    t = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    t = re.sub(r"[^\w\s-]", "", t.lower())
    slug = re.sub(r"[-\s]+", "-", t).strip("-")
    # Check first 40 chars (slug might have suffix from date)
    prefix = slug[:40]
    return any(s.startswith(prefix) for s in existing)


async def generate_one(
    client: httpx.AsyncClient,
    token: str,
    topic: str,
    category: str,
    schema_type: str,
    model: str,
) -> dict[str, Any]:
    r = await client.post(
        f"{API_BASE}/articles/generate",
        json={
            "topic": topic,
            "category": category,
            "schema_type": schema_type,
            "language": "en",
            "model": model,
            "auto_publish": True,
        },
        headers={"Authorization": f"Bearer {token}"},
        timeout=120.0,
    )
    if r.status_code not in (200, 201):
        raise RuntimeError(f"{r.status_code} — {r.text[:200]}")
    return r.json()


# ── Main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    parser = argparse.ArgumentParser(description="MedMind bulk article generator")
    parser.add_argument("--category", default="all", help="Category key or 'all'")
    parser.add_argument("--limit", type=int, default=0, help="Max articles to generate (0 = unlimited)")
    parser.add_argument("--model", default="haiku", choices=["haiku", "sonnet"])
    parser.add_argument("--dry-run", action="store_true", help="Print topics without generating")
    parser.add_argument("--no-check", action="store_true", help="Skip existing slug check")
    args = parser.parse_args()

    delay = DELAY_SONNET if args.model == "sonnet" else DELAY_HAIKU

    # Build work list
    if args.category == "all":
        work = [(cat, topic, stype) for cat, items in TOPICS.items() for topic, stype in items]
    elif args.category in TOPICS:
        work = [(args.category, topic, stype) for topic, stype in TOPICS[args.category]]
    else:
        log(f"Unknown category '{args.category}'. Available: {', '.join(TOPICS)}")
        sys.exit(1)

    if args.limit:
        work = work[: args.limit]

    total = len(work)
    log(f"\nMedMind Bulk Article Generator")
    log(f"  Model     : {args.model}")
    log(f"  Category  : {args.category}")
    log(f"  Topics    : {total}")
    log(f"  Dry run   : {args.dry_run}")
    log(f"  Est. time : ~{total * delay // 60} min\n")

    if args.dry_run:
        for i, (cat, topic, stype) in enumerate(work, 1):
            log(f"  {i:3}. [{cat}] {topic} ({stype})")
        return

    async with httpx.AsyncClient(timeout=30) as client:
        log("Logging in…")
        token = await get_token(client)
        log("  Login OK.\n")

        existing: set[str] = set()
        if not args.no_check:
            log("Fetching existing slugs…")
            existing = await fetch_existing_slugs(client, token)
            log("")

        done = 0
        skipped = 0
        errors = 0

        for i, (cat, topic, stype) in enumerate(work, 1):
            prefix = f"[{i}/{total}] [{cat}]"

            if not args.no_check and slug_exists(topic, existing):
                log(f"{prefix} SKIP (exists): {topic}")
                skipped += 1
                continue

            log(f"{prefix} Generating: {topic}")
            t0 = time.time()
            try:
                result = await generate_one(client, token, topic, cat, stype, args.model)
                elapsed = time.time() - t0
                slug = result.get("slug", "?")
                log(f"  OK  /articles/{slug}  ({elapsed:.1f}s)")
                existing.add(slug)
                done += 1
            except Exception as e:
                log(f"  ERR {e}")
                errors += 1

            if i < total:
                await asyncio.sleep(delay)

    log(f"\nDone. Generated: {done}  Skipped: {skipped}  Errors: {errors}")


if __name__ == "__main__":
    asyncio.run(main())
