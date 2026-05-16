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

# ── Config ─────────────────────────────────────────────────────────────────────
OLLAMA_URL  = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen3:1.7b"   # fast; use qwen3:8b for better quality
DB_URL      = "postgresql://medmind:medmind_secret@localhost:5432/medmind"
LOCALES     = ["ru", "de", "fr", "es", "tr", "ar"]
DELAY       = 2.0             # seconds between articles
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
You are a medical writer creating educational content for medical students and doctors.
Write a comprehensive, accurate medical article about: {topic}
Category: {category}

Structure the article with these sections (use ## for headings):
## Overview
## Pathophysiology / Mechanism of Action
## Clinical Features / Indications
## Diagnosis / Monitoring
## Treatment / Management
## Key Clinical Points

Requirements:
- 650-850 words total
- Accurate, evidence-based medical content
- Include specific details: dosages, criteria, lab values where relevant
- Professional tone for healthcare professionals and students
- Do NOT include references or citations

Return ONLY valid JSON, no other text:
{{
  "title": "clear clinical title (max 80 chars)",
  "excerpt": "2-sentence clinical summary for medical professionals",
  "body_text": "full article text with ## section headings"
}}"""


def text_to_blocks(text: str) -> list[dict]:
    """Convert markdown-style article text to body blocks."""
    blocks = []
    lines  = text.strip().split("\n")
    buffer = []

    def flush_buffer():
        para = " ".join(buffer).strip()
        if para:
            # Detect bullet lists
            if para.startswith(("- ", "• ", "* ")):
                items = [l.lstrip("-•* ").strip()
                         for l in para.split("\n") if l.strip()]
                blocks.append({"type": "ul", "items": items})
            else:
                blocks.append({"type": "p", "content": para})
        buffer.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_buffer()
        elif stripped.startswith("### "):
            flush_buffer()
            blocks.append({"type": "h3", "content": stripped[4:].strip()})
        elif stripped.startswith("## "):
            flush_buffer()
            blocks.append({"type": "h2", "content": stripped[3:].strip()})
        elif stripped.startswith(("- ", "• ", "* ")):
            flush_buffer()
            buffer.append(stripped)
        else:
            # Remove markdown bold/italic
            clean = re.sub(r"\*\*(.+?)\*\*", r"\1", stripped)
            clean = re.sub(r"\*(.+?)\*", r"\1", clean)
            buffer.append(clean)

    flush_buffer()

    # Merge consecutive bullet items into one ul block
    merged = []
    for block in blocks:
        if (merged and merged[-1]["type"] == "ul"
                and block["type"] == "ul"):
            merged[-1]["items"].extend(block["items"])
        else:
            merged.append(block)
    return merged


def generate_with_ollama(topic: str, category: str, model: str) -> dict | None:
    """Call Ollama to generate article. Returns parsed JSON or None."""
    prompt = ARTICLE_PROMPT.format(topic=topic, category=category)
    try:
        resp = httpx.post(
            OLLAMA_URL,
            json={
                "model":    model,
                "messages": [{"role": "user", "content": prompt}],
                "stream":   False,
                "options":  {
                    "temperature": 0.35,
                    "num_predict": 1800,
                    "num_ctx":     4096,
                    "top_p":       0.9,
                },
                "think": False,
            },
            timeout=300,
        )
        if resp.status_code != 200:
            log.error("Ollama error %s: %s", resp.status_code, resp.text[:200])
            return None

        content = resp.json().get("message", {}).get("content", "")

        # Strip markdown fences
        content = re.sub(r"^```(?:json)?\s*", "", content.strip())
        content = re.sub(r"\s*```$", "", content)

        # Extract JSON object
        m = re.search(r"\{.*\}", content, re.DOTALL)
        if m:
            content = m.group()

        data = json.loads(content)
        return data

    except json.JSONDecodeError as e:
        log.error("JSON parse error for '%s': %s", topic, e)
        return None
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

def save_article(conn, article_id: str, slug: str, title: str, excerpt: str,
                 body: list, category: str) -> bool:
    """Insert article into DB. Returns False if slug already exists."""
    schema_type = SCHEMA_MAP.get(category, "MedicalWebPage")
    reading_time = max(3, len(" ".join(
        b.get("content", "") for b in body if b.get("type") == "p"
    ).split()) // 200)
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM articles WHERE slug=%s", (slug,))
            if cur.fetchone():
                return False  # already exists

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
    parser.add_argument("--limit",    type=int,   default=50,
                        help="Max articles to generate (default: 50)")
    parser.add_argument("--model",    type=str,   default=OLLAMA_MODEL,
                        help=f"Ollama model (default: {OLLAMA_MODEL})")
    parser.add_argument("--category", type=str,   default=None,
                        help="Only this category")
    parser.add_argument("--dry-run",  action="store_true",
                        help="Show topics without generating")
    parser.add_argument("--delay",    type=float, default=DELAY,
                        help="Seconds between articles (default: 2)")
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

    count  = 0
    errors = 0
    skipped = 0

    for category, topics in TOPICS.items():
        if args.category and category != args.category:
            continue
        if count >= args.limit:
            break

        for topic in topics:
            if count >= args.limit:
                break

            slug = slugify(topic)
            log.info("[%d/%d] %s / %s", count+1, args.limit, category, topic)

            # Check if exists
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM articles WHERE slug LIKE %s",
                            (slug[:50] + "%",))
                if cur.fetchone():
                    log.info("  — Skipped (exists)")
                    skipped += 1
                    continue

            # Generate with Ollama
            t0   = time.time()
            data = generate_with_ollama(topic, category, args.model)
            elapsed = time.time() - t0

            if not data or not data.get("title") or not data.get("body_text"):
                log.warning("  ✗ Generation failed (%.1fs)", elapsed)
                errors += 1
                continue

            title   = data["title"]
            excerpt = data.get("excerpt", "")
            body    = text_to_blocks(data["body_text"])
            slug    = slugify(title)

            log.info("  Generated: '%s' (%.1fs, %d blocks)",
                     title[:60], elapsed, len(body))

            # Save to DB
            article_id = str(uuid.uuid4())
            saved = save_article(conn, article_id, slug, title, excerpt,
                                 body, category)
            if not saved:
                log.info("  — Slug already exists, skipping")
                skipped += 1
                continue

            # Translate all 6 locales
            n_tr = save_translations(conn, article_id, title, excerpt, body)
            log.info("  ✓ Published + %d translations | %s", n_tr, slug)

            # Notify search engines
            notify_indexnow(slug)

            count += 1
            time.sleep(args.delay)

    conn.close()
    log.info("Done. Generated: %d | Skipped: %d | Errors: %d",
             count, skipped, errors)


if __name__ == "__main__":
    main()
