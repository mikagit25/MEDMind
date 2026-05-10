#!/usr/bin/env python3
"""Background article generator — Ollama + auto-translate.

Generates medical articles via Ollama and immediately schedules translation
into all 6 languages. Runs indefinitely until all topics are processed.

Usage (inside backend container):
    python generate_articles_bg.py >> /tmp/gen_articles.log 2>&1
"""

import asyncio
import logging
import re
import sys
import unicodedata
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("gen_bg")

# ── Topic list ─────────────────────────────────────────────────────────────────
TOPICS = [
    # Cardiology
    ("Atrial Fibrillation: Diagnosis and Rhythm Control", "cardiology"),
    ("Heart Failure with Reduced Ejection Fraction: Management", "cardiology"),
    ("Stable Angina: Pathophysiology and Treatment", "cardiology"),
    ("Aortic Stenosis: Clinical Features and Management", "cardiology"),
    ("Infective Endocarditis: Diagnosis and Treatment", "cardiology"),
    ("Pulmonary Hypertension: Classification and Management", "cardiology"),
    ("Ventricular Tachycardia: Diagnosis and Emergency Management", "cardiology"),
    ("Dilated Cardiomyopathy: Causes and Treatment", "cardiology"),
    ("Cardiac Tamponade: Recognition and Pericardiocentesis", "cardiology"),
    ("Deep Vein Thrombosis and Pulmonary Embolism Management", "cardiology"),
    # Neurology
    ("Ischemic Stroke: Acute Management and Thrombolysis", "neurology"),
    ("Epilepsy: Classification, Diagnosis and Drug Treatment", "neurology"),
    ("Migraine: Pathophysiology and Prophylactic Treatment", "neurology"),
    ("Multiple Sclerosis: Disease-Modifying Therapies", "neurology"),
    ("Parkinson Disease: Motor and Non-Motor Features", "neurology"),
    ("Guillain-Barré Syndrome: Diagnosis and Management", "neurology"),
    ("Meningitis: Bacterial vs Viral Differentiation", "neurology"),
    ("Alzheimer Disease: Pathology and Current Treatments", "neurology"),
    ("Myasthenia Gravis: Diagnosis and Immunotherapy", "neurology"),
    ("Transient Ischemic Attack: Evaluation and Prevention", "neurology"),
    # Pulmonology / Diseases
    ("COPD: Gold Staging and Pharmacological Management", "diseases"),
    ("Pneumonia: Community-Acquired vs Hospital-Acquired", "diseases"),
    ("Pulmonary Fibrosis: Diagnosis and Antifibrotic Therapy", "diseases"),
    ("Asthma in Adults: Stepwise Management", "diseases"),
    ("Pleural Effusion: Transudate vs Exudate Evaluation", "diseases"),
    ("Tuberculosis: Diagnosis, Treatment and Drug Resistance", "diseases"),
    ("COVID-19: Pathophysiology and Clinical Management", "diseases"),
    ("Sarcoidosis: Pulmonary and Systemic Manifestations", "diseases"),
    ("Lung Cancer: Staging and Treatment Modalities", "oncology"),
    ("Obstructive Sleep Apnea: Diagnosis and CPAP Therapy", "diseases"),
    # Endocrinology
    ("Thyroid Nodules: Evaluation and Biopsy Indications", "endocrinology"),
    ("Cushing Syndrome: Diagnosis and Management", "endocrinology"),
    ("Primary Hyperaldosteronism: Conn Syndrome Workup", "endocrinology"),
    ("Diabetic Ketoacidosis: Pathogenesis and Treatment Protocol", "endocrinology"),
    ("Hypothyroidism: Causes, Diagnosis, and Levothyroxine Dosing", "endocrinology"),
    ("Adrenal Insufficiency: Primary vs Secondary", "endocrinology"),
    ("Polycystic Ovary Syndrome: Metabolic and Reproductive Management", "endocrinology"),
    ("Pheochromocytoma: Diagnosis and Perioperative Care", "endocrinology"),
    ("Osteoporosis: FRAX Score and Pharmacological Prevention", "diseases"),
    ("Vitamin D Deficiency: Clinical Consequences and Treatment", "endocrinology"),
    # Gastroenterology
    ("Peptic Ulcer Disease: H. pylori Eradication Therapy", "diseases"),
    ("Inflammatory Bowel Disease: Crohn vs Ulcerative Colitis", "diseases"),
    ("Cirrhosis: Complications and Management", "diseases"),
    ("Acute Pancreatitis: Severity Assessment and Management", "diseases"),
    ("Colorectal Cancer: Screening and Staging", "oncology"),
    ("GERD: Pathophysiology and Long-Term Management", "diseases"),
    ("Hepatitis B: Natural History and Antiviral Treatment", "diseases"),
    ("Hepatitis C: DAA Therapy and Cure Rates", "diseases"),
    ("Celiac Disease: Diagnosis and Gluten-Free Diet", "diseases"),
    ("Irritable Bowel Syndrome: Rome Criteria and Management", "diseases"),
    # Nephrology
    ("Chronic Kidney Disease: CKD Stages and Slowing Progression", "diseases"),
    ("Acute Kidney Injury: KDIGO Criteria and Management", "diseases"),
    ("Nephrotic Syndrome: Causes, Diagnosis and Treatment", "diseases"),
    ("Renal Calculi: Stone Types and Metabolic Evaluation", "diseases"),
    ("Polycystic Kidney Disease: Genetic Basis and Management", "diseases"),
    ("Hyponatremia: Differential Diagnosis and Correction", "diseases"),
    ("Hyperkalemia: ECG Changes and Emergency Treatment", "diseases"),
    ("Diabetic Nephropathy: Pathogenesis and Renoprotection", "diseases"),
    # Rheumatology
    ("Rheumatoid Arthritis: DMARD Therapy and Biologics", "diseases"),
    ("Systemic Lupus Erythematosus: Diagnosis and Management", "diseases"),
    ("Gout: Pathophysiology, Acute Attack and Prophylaxis", "diseases"),
    ("Ankylosing Spondylitis: Diagnosis and Biologic Therapy", "diseases"),
    ("Sjögren Syndrome: Exocrine and Systemic Features", "diseases"),
    ("Antiphospholipid Syndrome: Thrombosis and Pregnancy Loss", "diseases"),
    # Infectious diseases
    ("Sepsis: Sepsis-3 Definitions and Bundle Management", "infectious-diseases"),
    ("HIV/AIDS: Antiretroviral Therapy and Opportunistic Infections", "infectious-diseases"),
    ("Malaria: Diagnosis, Species Differentiation and Treatment", "infectious-diseases"),
    ("Urinary Tract Infection: Diagnosis and Antibiotic Selection", "infectious-diseases"),
    ("Infective Endocarditis: Duke Criteria and Antibiotic Regimens", "infectious-diseases"),
    ("Clostridioides difficile Infection: Diagnosis and Fidaxomicin", "infectious-diseases"),
    ("Methicillin-Resistant Staphylococcus aureus: Treatment", "infectious-diseases"),
    ("Dengue Fever: Clinical Phases and Supportive Management", "infectious-diseases"),
    ("Leptospirosis: Diagnosis and Doxycycline Treatment", "infectious-diseases"),
    ("Meningococcal Disease: Prevention and Chemoprophylaxis", "infectious-diseases"),
    # Oncology
    ("Breast Cancer: Receptor Status and Targeted Therapy", "oncology"),
    ("Prostate Cancer: PSA Screening and Management", "oncology"),
    ("Lymphoma: Hodgkin vs Non-Hodgkin Classification", "oncology"),
    ("Leukemia: AML and CLL — Diagnosis and Treatment", "oncology"),
    ("Pancreatic Cancer: Risk Factors and Surgical Candidacy", "oncology"),
    ("Hepatocellular Carcinoma: Surveillance and Locoregional Therapy", "oncology"),
    ("Thyroid Cancer: Papillary Carcinoma and Radioiodine", "oncology"),
    ("Renal Cell Carcinoma: Staging and Immunotherapy", "oncology"),
    # Surgery
    ("Appendicitis: Clinical Scoring and Laparoscopic Management", "surgery"),
    ("Cholecystitis: Acute Management and Cholecystectomy", "surgery"),
    ("Abdominal Aortic Aneurysm: Surveillance and Repair Thresholds", "surgery"),
    ("Bowel Obstruction: Small vs Large Bowel — Conservative vs Surgery", "surgery"),
    ("Inguinal Hernia: Anatomy and Surgical Repair Techniques", "surgery"),
    ("Trauma: Primary Survey ABCDE and Damage Control Surgery", "surgery"),
    ("Burns: Rule of Nines, Fluid Resuscitation, Wound Care", "surgery"),
    ("Postoperative Complications: Fever, DVT, SSI Recognition", "surgery"),
    # Psychiatry
    ("Major Depressive Disorder: SSRI Selection and Monitoring", "psychiatry"),
    ("Bipolar Disorder: Mood Stabilizers and Lithium Monitoring", "psychiatry"),
    ("Schizophrenia: Antipsychotic Classes and Metabolic Monitoring", "psychiatry"),
    ("Generalized Anxiety Disorder: CBT and Pharmacotherapy", "psychiatry"),
    ("Post-Traumatic Stress Disorder: Diagnostic Criteria and Treatment", "psychiatry"),
    ("Alcohol Use Disorder: Withdrawal Management and Naltrexone", "psychiatry"),
    ("Attention Deficit Hyperactivity Disorder in Adults: Diagnosis", "psychiatry"),
    ("Eating Disorders: Anorexia vs Bulimia — Medical Complications", "psychiatry"),
    # Pediatrics
    ("Febrile Seizures: Evaluation and Parental Guidance", "pediatrics"),
    ("Kawasaki Disease: Diagnosis and Aspirin-IVIG Protocol", "pediatrics"),
    ("Bronchiolitis: RSV, Supportive Care, Oxygen Thresholds", "pediatrics"),
    ("Failure to Thrive: Organic vs Non-Organic Causes", "pediatrics"),
    ("Neonatal Jaundice: Bilirubin Levels and Phototherapy", "pediatrics"),
    ("Intussusception: Clinical Presentation and Air Enema Reduction", "pediatrics"),
    ("Childhood Asthma: Stepwise Treatment and School Plans", "pediatrics"),
    ("Pediatric Sepsis: Surviving Sepsis Pediatric Guidelines", "pediatrics"),
    # Emergency
    ("Anaphylaxis: Recognition, Epinephrine and Biphasic Reactions", "emergency"),
    ("Acute Coronary Syndrome: STEMI vs NSTEMI Management", "emergency"),
    ("Status Epilepticus: Benzodiazepine Escalation Protocol", "emergency"),
    ("Hypertensive Emergency vs Urgency: Management", "emergency"),
    ("Ectopic Pregnancy: Diagnosis and Methotrexate vs Surgery", "emergency"),
    ("Carbon Monoxide Poisoning: Diagnosis and Hyperbaric Oxygen", "emergency"),
    ("Organophosphate Poisoning: Cholinergic Crisis and Atropine", "emergency"),
    ("Stroke Mimics: Distinguishing TIA from Todd Paralysis", "emergency"),
    # Drugs
    ("Warfarin vs Direct Oral Anticoagulants: Indications and Reversal", "drugs"),
    ("Beta-Blockers: Cardioselective vs Non-Selective Classes", "drugs"),
    ("Proton Pump Inhibitors: Mechanism, Uses and Side Effects", "drugs"),
    ("Statins: LDL Reduction, Side Effects and Monitoring", "drugs"),
    ("Corticosteroids: Systemic Effects and Tapering Protocols", "drugs"),
    ("ACE Inhibitors and ARBs: Renal Protection and Contraindications", "drugs"),
    ("Opioid Analgesics: Equianalgesic Dosing and Overdose Management", "drugs"),
    ("Antibiotics: Beta-Lactam Mechanisms and Allergy Cross-Reactivity", "drugs"),
    ("Insulin Types: Pharmacokinetics and Basal-Bolus Regimens", "drugs"),
    ("Metformin: Mechanism, Benefits and Lactic Acidosis Risk", "drugs"),
    # Diagnostics
    ("Electrocardiogram Interpretation: Systematic Approach", "diagnostics"),
    ("Arterial Blood Gas: Step-by-Step Interpretation", "diagnostics"),
    ("Chest X-Ray: Systematic Reading for Clinicians", "diagnostics"),
    ("Echocardiography: Indications and Key Measurements", "diagnostics"),
    ("Liver Function Tests: Hepatocellular vs Cholestatic Patterns", "diagnostics"),
    ("Complete Blood Count: Differential Diagnosis of Abnormalities", "diagnostics"),
    ("Lumbar Puncture: Indications and CSF Interpretation", "diagnostics"),
    ("Thyroid Function Tests: TSH, Free T4 and T3 Interpretation", "diagnostics"),
    ("Urinalysis: Microscopy and Clinical Correlation", "diagnostics"),
    ("Procalcitonin and CRP: Sepsis Biomarkers in Clinical Practice", "diagnostics"),
    # Procedures
    ("Central Venous Catheter Insertion: Subclavian vs Jugular Approach", "procedures"),
    ("Chest Tube Insertion: Indications and Technique", "procedures"),
    ("Endotracheal Intubation: RSI Protocol and Confirmation", "procedures"),
    ("Thoracentesis: Pleural Fluid Sampling Technique", "procedures"),
    ("Arthrocentesis: Joint Aspiration and Synovial Analysis", "procedures"),
    ("Paracentesis: Technique and Spontaneous Bacterial Peritonitis", "procedures"),
    ("Bone Marrow Biopsy: Indications and Procedure", "procedures"),
    ("Flexible Bronchoscopy: Diagnostic and Therapeutic Uses", "procedures"),
]


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "-", text).strip("-")


async def already_exists(db, slug: str) -> bool:
    from sqlalchemy import text
    r = await db.execute(text("SELECT 1 FROM articles WHERE slug LIKE :pat LIMIT 1"), {"pat": f"%{slug[:30]}%"})
    return r.first() is not None


async def generate_and_save(topic: str, category: str, db) -> str | None:
    """Generate one article, save, trigger translation. Returns slug or None."""
    from app.models.models import Article
    from app.services.article_generator import generate_medical_article
    from app.services.translation_service import schedule_article_translations

    slug_hint = slugify(topic)

    # Skip if likely already exists
    if await already_exists(db, slug_hint):
        logger.info("SKIP (exists): %s", topic)
        return None

    logger.info("START: %s [%s]", topic, category)
    t0 = datetime.utcnow()

    try:
        result = await generate_medical_article(
            topic=topic,
            category=category,
            schema_type="MedicalCondition" if category in ("diseases","cardiology","neurology","oncology","endocrinology","infectious-diseases","psychiatry","pediatrics") else "MedicalWebPage",
            language="en",
            model="ollama",
        )
    except Exception as exc:
        logger.error("GENERATION FAILED for %r: %s", topic, exc)
        return None

    # Ensure unique slug
    base_slug = result.get("slug", slug_hint)
    from sqlalchemy import text
    exists = (await db.execute(text("SELECT 1 FROM articles WHERE slug=:s"), {"s": base_slug})).first()
    if exists:
        import uuid
        base_slug = f"{base_slug}-{uuid.uuid4().hex[:4]}"
        result["slug"] = base_slug

    article = Article(
        slug=base_slug,
        title=result["title"],
        excerpt=result.get("excerpt", ""),
        body=result.get("body", []),
        category=category,
        subcategory=result.get("subcategory"),
        keywords=result.get("keywords", []),
        reading_time_minutes=result.get("reading_time_minutes", 7),
        schema_type=result.get("schema_type", "MedicalWebPage"),
        faq=result.get("faq", []),
        sources=result.get("sources", []),
        related_module_code=result.get("related_module_code"),
        og_title=result.get("og_title"),
        og_description=result.get("og_description"),
        is_published=True,
        published_at=datetime.utcnow(),
        generated_by="ollama-bg",
        review_status="published",
        revenue_share_pct=0,  # platform-generated article, no author revenue
    )
    db.add(article)
    await db.commit()
    await db.refresh(article)

    elapsed = (datetime.utcnow() - t0).seconds
    logger.info("SAVED: %s — %d body blocks, %d faq, slug=%s (%ds)", article.title, len(article.body or []), len(article.faq or []), article.slug, elapsed)

    # Schedule translations (background task within this same event loop)
    try:
        await schedule_article_translations(article.id, db)
        logger.info("TRANSLATION SCHEDULED: %s → 6 locales", article.slug)
    except Exception as exc:
        logger.error("TRANSLATION SCHEDULE FAILED for %s: %s", article.slug, exc)

    return article.slug


async def main():
    import sys
    sys.path.insert(0, "/app")  # inside Docker container

    from app.core.database import AsyncSessionLocal

    logger.info("=== MedMind Article Generator Started — %d topics ===", len(TOPICS))
    ok = 0
    skip = 0
    fail = 0

    for i, (topic, category) in enumerate(TOPICS, 1):
        logger.info("--- [%d/%d] ---", i, len(TOPICS))
        async with AsyncSessionLocal() as db:
            try:
                slug = await generate_and_save(topic, category, db)
                if slug:
                    ok += 1
                else:
                    skip += 1
            except Exception as exc:
                logger.error("UNHANDLED ERROR for %r: %s", topic, exc)
                fail += 1
        # Brief pause between articles to avoid hammering Ollama
        await asyncio.sleep(8)

    logger.info("=== DONE: %d generated, %d skipped, %d failed ===", ok, skip, fail)


if __name__ == "__main__":
    asyncio.run(main())
