"""
Batch article generation from open sources.
Generates original articles on 400+ medical/veterinary topics,
translates to 6 languages, publishes with auto-indexing.

Run: python3 generate_articles_batch.py [--limit N] [--category CAT] [--dry-run]
"""
import asyncio
import argparse
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Topic lists by category ─────────────────────────────────────────────────────

TOPICS: dict[str, list[str]] = {
    "cardiology": [
        "Hypertrophic Cardiomyopathy", "Dilated Cardiomyopathy", "Cardiac Tamponade",
        "Infective Endocarditis", "Rheumatic Heart Disease", "Cardiac Syncope",
        "Long QT Syndrome", "Brugada Syndrome", "Wolff-Parkinson-White Syndrome",
        "Pulmonary Hypertension", "Right Heart Failure", "Tricuspid Regurgitation",
        "Mitral Stenosis", "Aortic Regurgitation", "Hypertensive Crisis",
        "Ventricular Tachycardia", "Supraventricular Tachycardia", "Sick Sinus Syndrome",
        "Congestive Heart Failure Management", "Cardiac Rehabilitation",
        "Coronary Artery Bypass Grafting", "Percutaneous Coronary Intervention",
        "Cardiac Biomarkers in Clinical Practice", "Echocardiography Indications",
    ],
    "neurology": [
        "Alzheimer's Disease Pathophysiology", "Parkinson's Disease Management",
        "Multiple Sclerosis Clinical Features", "Myasthenia Gravis",
        "Guillain-Barre Syndrome", "Amyotrophic Lateral Sclerosis",
        "Migraine Pathophysiology and Treatment", "Cluster Headache",
        "Trigeminal Neuralgia", "Bell's Palsy", "Essential Tremor",
        "Huntington's Disease", "Cerebral Venous Thrombosis",
        "Subarachnoid Hemorrhage", "Subdural Hematoma",
        "Wernicke Encephalopathy", "Normal Pressure Hydrocephalus",
        "Status Epilepticus Management", "Peripheral Neuropathy",
        "Lumbar Disc Herniation", "Carpal Tunnel Syndrome",
        "Dementia Differential Diagnosis", "Neuroleptic Malignant Syndrome",
    ],
    "internal-medicine": [
        "Type 2 Diabetes Management", "Hypothyroidism Clinical Features",
        "Hyperthyroidism and Thyrotoxicosis", "Cushing's Syndrome",
        "Addison's Disease", "Hyperaldosteronism", "Pheochromocytoma",
        "Chronic Kidney Disease Stages", "Nephrotic Syndrome",
        "Glomerulonephritis", "Renal Tubular Acidosis", "Hyperkalemia Management",
        "Hyponatremia Clinical Approach", "Iron Deficiency Anemia",
        "Vitamin B12 Deficiency", "Folate Deficiency Anemia",
        "Hemolytic Anemia", "Sickle Cell Disease", "Thalassemia",
        "Thrombocytopenia Causes", "Deep Vein Thrombosis",
        "Pulmonary Embolism Diagnosis", "Pleural Effusion",
        "Community Acquired Pneumonia", "Hospital Acquired Pneumonia",
        "Tuberculosis Diagnosis and Treatment", "COPD Exacerbation",
        "Asthma Acute Management", "Interstitial Lung Disease",
        "Liver Cirrhosis Complications", "Portal Hypertension",
        "Spontaneous Bacterial Peritonitis", "Hepatic Encephalopathy",
        "Acute Pancreatitis Management", "Inflammatory Bowel Disease",
        "Celiac Disease", "Irritable Bowel Syndrome",
        "Upper GI Bleeding", "Lower GI Bleeding",
        "Rheumatoid Arthritis Management", "Systemic Lupus Erythematosus",
        "Ankylosing Spondylitis", "Gout Pathophysiology",
        "Sepsis and Septic Shock", "Disseminated Intravascular Coagulation",
    ],
    "surgery": [
        "Inguinal Hernia Repair", "Umbilical Hernia",
        "Bowel Obstruction Management", "Volvulus",
        "Diverticulitis Complications", "Colorectal Cancer Surgery",
        "Cholecystitis and Cholecystectomy", "Choledocholithiasis",
        "Liver Resection", "Pancreaticoduodenectomy",
        "Thyroid Surgery Complications", "Parathyroidectomy",
        "Adrenalectomy", "Splenectomy Indications",
        "Wound Healing and Closure", "Surgical Site Infections",
        "Postoperative Complications", "DVT Prophylaxis in Surgery",
        "Anastomotic Leak", "Abdominal Compartment Syndrome",
        "Trauma Primary Survey ABCDE", "Damage Control Surgery",
    ],
    "pediatrics": [
        "Kawasaki Disease", "Henoch-Schonlein Purpura",
        "Intussusception in Children", "Hirschsprung Disease",
        "Pyloric Stenosis", "Childhood Asthma Management",
        "Croup vs Epiglottitis", "Febrile Seizures",
        "Childhood Nephrotic Syndrome", "Urinary Tract Infection in Children",
        "Neonatal Jaundice", "Respiratory Distress Syndrome in Newborns",
        "Necrotizing Enterocolitis", "Sepsis in Neonates",
        "Congenital Heart Disease Overview", "Ventricular Septal Defect",
        "Tetralogy of Fallot", "Patent Ductus Arteriosus",
        "Childhood Vaccinations Schedule", "Growth Hormone Deficiency",
        "Precocious Puberty", "Type 1 Diabetes in Children",
        "ADHD Diagnosis and Management", "Autism Spectrum Disorder",
    ],
    "ob-gyn": [
        "Ectopic Pregnancy Management", "Miscarriage Clinical Approach",
        "Preeclampsia Pathophysiology", "HELLP Syndrome",
        "Placenta Previa", "Placental Abruption",
        "Gestational Diabetes", "Preterm Labor",
        "Cervical Incompetence", "Oligohydramnios",
        "Postpartum Hemorrhage", "Shoulder Dystocia",
        "Fetal Growth Restriction", "Neonatal Resuscitation",
        "Endometriosis Clinical Features", "Polycystic Ovary Syndrome",
        "Uterine Fibroids", "Ovarian Torsion",
        "Ovarian Cancer Staging", "Cervical Cancer Screening",
        "Breast Cancer in Pregnancy", "Hormonal Contraception",
    ],
    "pharmacology": [
        "ACE Inhibitors Clinical Use", "Beta Blockers in Cardiology",
        "Anticoagulant Therapy Comparison", "Antiplatelet Drugs",
        "Statins Mechanism and Use", "Diuretics Clinical Pharmacology",
        "Antiarrhythmic Drug Classes", "Antibiotics for Common Infections",
        "Aminoglycosides Toxicity", "Fluoroquinolone Use and Resistance",
        "Opioid Analgesics and Tolerance", "NSAIDs Adverse Effects",
        "Corticosteroid Systemic Effects", "Immunosuppressants in Transplant",
        "Chemotherapy Side Effects", "Targeted Cancer Therapy",
        "Antidiabetic Drug Classes", "Thyroid Drugs",
        "Antiepileptic Drug Comparison", "Antidepressants MOA",
        "Antipsychotic Drugs", "Benzodiazepine Pharmacology",
        "Drug-Drug Interactions", "Renal Dose Adjustments",
    ],
    "infectious-diseases": [
        "HIV Antiretroviral Therapy", "Opportunistic Infections in HIV",
        "Malaria Diagnosis and Treatment", "Dengue Fever",
        "Typhoid Fever", "Cholera Management",
        "Meningococcal Meningitis", "Viral Encephalitis",
        "Infective Endocarditis Criteria", "Osteomyelitis",
        "Septic Arthritis", "Cellulitis and Necrotizing Fasciitis",
        "Clostridium Difficile Infection", "Hepatitis B Chronic Management",
        "Hepatitis C Direct Acting Antivirals", "COVID-19 Clinical Manifestations",
        "Influenza Antiviral Treatment", "Rabies Post-Exposure Prophylaxis",
        "Tetanus Prophylaxis", "Lyme Disease",
        "Tuberculosis Drug Resistance", "Fungal Infections Candida Aspergillus",
        "Zika Virus Disease", "Ebola and Viral Hemorrhagic Fevers",
        "Antimicrobial Stewardship", "Prion Diseases Creutzfeldt-Jakob",
    ],
    "emergency": [
        "Anaphylaxis Treatment Protocol", "Acute Asthma Attack",
        "Acute MI Emergency Management", "Stroke Thrombolysis",
        "Hypertensive Emergency", "Acute Aortic Dissection",
        "Tension Pneumothorax", "Massive Haemothorax",
        "Burns Assessment and Management", "Drowning and Near-Drowning",
        "Hypothermia Management", "Heat Stroke",
        "Acute Poisoning Management", "Acetaminophen Overdose",
        "Tricyclic Antidepressant Overdose", "Opioid Overdose Naloxone",
        "Hypoglycemia Emergency", "Diabetic Ketoacidosis",
        "Hyperglycemic Hyperosmolar State", "Acute Adrenal Crisis",
    ],
    "psychiatry": [
        "Major Depressive Disorder Treatment", "Bipolar I vs Bipolar II",
        "Schizophrenia Positive and Negative Symptoms",
        "Generalized Anxiety Disorder", "Panic Disorder",
        "Post-Traumatic Stress Disorder", "Obsessive Compulsive Disorder",
        "Borderline Personality Disorder", "Eating Disorders Anorexia Bulimia",
        "Alcohol Use Disorder", "Opioid Use Disorder",
        "Suicide Risk Assessment", "Psychosis Acute Management",
        "Lithium Toxicity", "Serotonin Syndrome",
    ],
    "dermatology": [
        "Melanoma ABCDE Criteria", "Basal Cell Carcinoma",
        "Squamous Cell Carcinoma Skin", "Acne Vulgaris Pathophysiology",
        "Rosacea Clinical Features", "Pemphigus Vulgaris",
        "Bullous Pemphigoid", "Stevens-Johnson Syndrome",
        "Drug Hypersensitivity Reactions", "Contact Dermatitis",
        "Urticaria and Angioedema", "Lichen Planus",
        "Vitiligo Pathophysiology", "Alopecia Areata",
        "Fungal Skin Infections", "Scabies and Treatment",
    ],
    "oncology": [
        "Lung Cancer Small Cell vs Non-Small Cell", "Colon Cancer Staging",
        "Breast Cancer Hormone Receptor Status", "Prostate Cancer PSA",
        "Lymphoma Hodgkin vs Non-Hodgkin", "Leukemia Classification",
        "Multiple Myeloma", "Melanoma Staging",
        "Pancreatic Cancer Prognosis", "Hepatocellular Carcinoma",
        "Renal Cell Carcinoma", "Bladder Cancer",
        "Thyroid Cancer Papillary vs Follicular", "Ovarian Cancer CA-125",
        "Chemotherapy Principles", "Immunotherapy in Oncology",
        "Radiation Therapy Basics", "Palliative Care in Cancer",
        "Cancer Pain Management", "Paraneoplastic Syndromes",
    ],
    "veterinary": [
        "Canine Parvovirus Treatment", "Feline Infectious Peritonitis",
        "Canine Distemper", "Feline Leukemia Virus",
        "Canine Hip Dysplasia", "Feline Hyperthyroidism",
        "Canine Diabetes Mellitus", "Equine Laminitis",
        "Bovine Respiratory Disease", "Avian Influenza",
        "Canine Cushing's Disease", "Feline Chronic Kidney Disease",
        "Canine Epilepsy Treatment", "Equine Colic Types",
        "Bovine Mastitis", "Canine Osteosarcoma",
        "Feline Asthma", "Canine Allergic Dermatitis",
        "Avian Psittacosis", "Rabbit GI Stasis",
        "Small Mammal Anesthesia", "Reptile Metabolic Bone Disease",
        "Aquatic Animal Medicine", "Zoo Animal Formulary",
        "Wildlife Rehabilitation", "Exotic Pet Nutrition",
        "Canine Heartworm Disease", "Feline Toxoplasmosis",
        "Equine Strangles", "Bovine Johne's Disease",
    ],
    "diagnostics": [
        "Brachial Plexus Anatomy and Injuries", "Coronary Artery Anatomy",
        "Circle of Willis Variants", "Hepatic Portal System",
        "Cranial Nerve Functions and Examination", "Autonomic Nervous System",
        "MRI vs CT Indications", "Ultrasound in Emergency Medicine",
        "ECG Interpretation Basics", "Spirometry Interpretation",
        "Arterial Blood Gas Analysis", "Urinalysis Interpretation",
        "Liver Function Tests", "Cardiac Stress Testing",
        "Lumbar Puncture Indications and Interpretation",
    ],
    "orthopedics": [
        "Osteoarthritis Pathophysiology and Management",
        "Rotator Cuff Tears Diagnosis", "ACL Injury and Reconstruction",
        "Hip Replacement Indications", "Knee Replacement Surgery",
        "Fracture Healing Principles", "Open Fractures Management",
        "Vertebral Compression Fractures", "Scoliosis Classification",
        "Osteomyelitis Acute vs Chronic", "Septic Arthritis Management",
        "Compartment Syndrome Recognition", "Bone Tumors Classification",
        "Paget's Disease of Bone", "Avascular Necrosis of Femoral Head",
        "Shoulder Dislocation Reduction", "Ankle Sprains and Ligament Injuries",
        "Carpal Tunnel Syndrome Treatment", "Trigger Finger",
        "Dupuytren's Contracture",
    ],
    "rheumatology": [
        "Rheumatoid Arthritis Pathogenesis", "Systemic Lupus Erythematosus Criteria",
        "Ankylosing Spondylitis HLA-B27", "Psoriatic Arthritis",
        "Sjögren's Syndrome", "Polymyalgia Rheumatica",
        "Giant Cell Arteritis", "Wegener's Granulomatosis",
        "Antiphospholipid Syndrome", "Scleroderma Systemic Sclerosis",
        "Myositis Polymyositis Dermatomyositis", "Vasculitis Classification",
        "Reactive Arthritis", "Crystal Arthropathies Gout Pseudogout",
        "Fibromyalgia Diagnosis and Treatment", "Raynaud's Phenomenon",
        "Biologics in Rheumatology", "DMARD Therapy Monitoring",
    ],
    "hematology": [
        "Sickle Cell Disease Complications", "Thalassemia Types and Management",
        "Hemophilia A and B", "Von Willebrand Disease",
        "Aplastic Anemia", "Polycythemia Vera",
        "Essential Thrombocythemia", "Myelofibrosis",
        "Chronic Myeloid Leukemia BCR-ABL", "Acute Myeloid Leukemia",
        "Acute Lymphoblastic Leukemia", "Chronic Lymphocytic Leukemia",
        "Idiopathic Thrombocytopenic Purpura", "Thrombotic Thrombocytopenic Purpura",
        "Heparin Induced Thrombocytopenia", "Coagulation Disorders",
        "Blood Transfusion Reactions", "Bone Marrow Transplantation",
        "Iron Studies Interpretation", "Porphyrias Overview",
    ],
    "nephrology": [
        "Acute Kidney Injury RIFLE Criteria", "Chronic Kidney Disease Management",
        "Dialysis Hemodialysis vs Peritoneal", "Kidney Transplantation",
        "Nephrotic Syndrome Causes", "IgA Nephropathy",
        "Membranous Nephropathy", "Focal Segmental Glomerulosclerosis",
        "Hypertensive Nephrosclerosis", "Diabetic Nephropathy",
        "Polycystic Kidney Disease", "Renal Tubular Acidosis Types",
        "Hyperkalemia Emergency Management", "Hyponatremia Approach",
        "Contrast-Induced Nephropathy", "Renal Calculi Pathophysiology",
        "Urinary Tract Infection Complicated", "Renovascular Hypertension",
    ],
    "pulmonology": [
        "COPD Pathophysiology GOLD Staging", "Asthma Stepwise Management",
        "Pulmonary Embolism WELLS Score", "Acute Respiratory Distress Syndrome",
        "Pneumonia Atypical Pathogens", "Lung Abscess",
        "Pleural Effusion Light's Criteria", "Pneumothorax Management",
        "Interstitial Lung Disease Classification", "Idiopathic Pulmonary Fibrosis",
        "Sarcoidosis Pulmonary Manifestations", "Obstructive Sleep Apnea",
        "Pulmonary Hypertension WHO Groups", "Bronchiectasis Causes",
        "Mesothelioma Asbestos Exposure", "Hypersensitivity Pneumonitis",
        "Mechanical Ventilation Basics", "Non-Invasive Ventilation",
    ],
    "ophthalmology": [
        "Glaucoma Open vs Closed Angle", "Cataracts Pathophysiology",
        "Age-Related Macular Degeneration", "Diabetic Retinopathy Staging",
        "Retinal Detachment Emergency", "Uveitis Classification",
        "Optic Neuritis and MS", "Papilledema Causes",
        "Orbital Cellulitis vs Preseptal", "Corneal Ulcer Management",
        "Dry Eye Syndrome", "Strabismus in Children",
        "Red Eye Differential Diagnosis", "Hypertensive Retinopathy",
    ],
    "ent": [
        "Acute Otitis Media Management", "Otitis Media with Effusion",
        "Chronic Otitis Media Cholesteatoma", "Sudden Sensorineural Hearing Loss",
        "Ménière's Disease", "Benign Paroxysmal Positional Vertigo",
        "Acute Sinusitis vs Chronic Sinusitis", "Nasal Polyps",
        "Allergic Rhinitis Immunotherapy", "Obstructive Sleep Apnea ENT",
        "Tonsillitis Indications for Tonsillectomy", "Peritonsillar Abscess",
        "Laryngeal Cancer Risk Factors", "Thyroid Nodule Evaluation",
        "Epistaxis Management", "Epiglottitis Adult",
    ],
    "urology": [
        "Benign Prostatic Hyperplasia Management", "Prostate Cancer Screening PSA",
        "Bladder Cancer Staging", "Renal Cell Carcinoma Diagnosis",
        "Testicular Cancer Seminoma vs Non-Seminoma", "Urinary Incontinence Types",
        "Urethral Stricture", "Kidney Stones Metabolic Workup",
        "Urinary Tract Infections Recurrent", "Erectile Dysfunction",
        "Hematuria Evaluation", "Hydronephrosis Causes",
        "Vesicoureteral Reflux", "Neurogenic Bladder",
        "Cystitis Interstitial", "Varicocele",
    ],
    "geriatrics": [
        "Falls in Elderly Prevention", "Delirium vs Dementia Differentiation",
        "Polypharmacy Medication Review", "Frailty Assessment",
        "Pressure Ulcers Staging and Prevention", "Urinary Incontinence in Elderly",
        "Osteoporosis Screening and Treatment", "Elder Abuse Recognition",
        "Palliative Care Principles", "Advance Directives",
        "Geriatric Depression Scale", "Sarcopenia Definition",
        "End of Life Care Goals",
    ],
}


async def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit",    type=int, default=500, help="Max articles to generate")
    parser.add_argument("--category", type=str, default=None, help="Only this category")
    parser.add_argument("--model",    type=str, default="haiku", choices=["haiku", "sonnet"])
    parser.add_argument("--dry-run",  action="store_true", help="Print topics without generating")
    parser.add_argument("--delay",    type=float, default=2.0, help="Seconds between articles")
    args = parser.parse_args()

    if args.dry_run:
        total = 0
        for cat, topics in TOPICS.items():
            if args.category and cat != args.category:
                continue
            print(f"\n{'='*40}\n{cat.upper()} ({len(topics)} topics)\n{'='*40}")
            for t in topics:
                print(f"  - {t}")
            total += len(topics)
        print(f"\nTotal: {total} topics")
        return

    # Set up DB connection
    import os
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://medmind:medmind_secret@localhost:5434/medmind")

    from app.core.database import AsyncSessionLocal
    from app.services.article_pipeline import run_pipeline

    count = 0
    errors = 0

    for category, topics in TOPICS.items():
        if args.category and category != args.category:
            continue
        if count >= args.limit:
            break

        for topic in topics:
            if count >= args.limit:
                break

            log.info("[%d] Generating: %s / %s", count + 1, category, topic)
            try:
                async with AsyncSessionLocal() as db:
                    slug = await run_pipeline(
                        topic=topic,
                        category=category,
                        db=db,
                        model=args.model,
                        auto_publish=True,
                        skip_if_exists=True,
                    )
                if slug:
                    log.info("  ✓ Published: %s", slug)
                    count += 1
                else:
                    log.info("  — Skipped (exists)")
            except Exception as e:
                log.error("  ✗ Error for '%s': %s", topic, e)
                errors += 1

            await asyncio.sleep(args.delay)

    log.info("Done. Generated: %d, Errors: %d", count, errors)


if __name__ == "__main__":
    import sys, os
    # Support running both from project root and from inside the container at /app
    backend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
    if os.path.isdir(backend_path):
        sys.path.insert(0, backend_path)
    elif os.path.isdir("/app"):
        sys.path.insert(0, "/app")
    asyncio.run(run())
