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
    "gemini-2.0-flash":      {"rpd": 1500, "rpm": 15,  "desc": "Best free (default)"},
    "gemini-2.0-flash-lite": {"rpd": 1500, "rpm": 30,  "desc": "Faster, lighter"},
    "gemini-1.5-flash":      {"rpd": 1500, "rpm": 15,  "desc": "Previous gen, stable"},
    "gemini-1.5-pro":        {"rpd": 50,   "rpm": 2,   "desc": "High quality, strict limits"},
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
}

# Merge base + new topics
ALL_TOPICS: dict[str, list[str]] = {**BASE_TOPICS, **NEW_TOPICS}

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


# ── Article prompt (same format as Groq/Ollama — no JSON issues) ──────────────
ARTICLE_PROMPT = """\
You are a senior clinician writing an authoritative medical reference comparable to UpToDate or StatPearls.
Audience: medical students, residents, and practicing physicians.

Topic: {topic}
Category: {category}

Write a COMPREHENSIVE article of 2500-3000 words with SPECIFIC clinical details: exact drug doses, \
diagnostic criteria, lab thresholds, guideline recommendations (AHA/ACC/ESC/WHO/NICE).

Use EXACTLY this output format:

TITLE: [Clinical title, max 85 characters]
EXCERPT: [3 sentences: clinical significance, key mechanism, main management]
ARTICLE_START

## Key Points
List 7-9 critical clinical facts ("- " prefix). Each: one specific fact with numbers/doses/criteria.

## Overview and Epidemiology
Definition, incidence/prevalence, demographics, major risk factors. (250 words)

## Pathophysiology
Mechanisms, molecular basis, disease progression. (300 words)

## Clinical Presentation
Symptoms, physical signs, typical/atypical, red flags. (250 words)

## Diagnosis
Criteria with SPECIFIC values, lab workup, imaging, scoring systems. (300 words)

## Management and Treatment
First-line therapy: SPECIFIC drug names, doses, duration, monitoring. Second-line options.
Special populations: pregnancy, CKD, elderly, hepatic impairment. Reference guidelines. (500 words)

## Complications and Prognosis
Complications with incidence rates, prognostic factors, referral criteria. (200 words)

## Special Populations and Considerations
Pediatric, geriatric, pregnancy, comorbidities, drug interactions. (200 words)

## Clinical Pearls
List 6-8 USMLE-style teaching points ("- " prefix). Classic associations, pitfalls.

ARTICLE_END

Rules: state facts DIRECTLY with numbers. No references section. Complete full-length sections."""


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
                    err_msg = (err_body.get("error", {}).get("message", "")
                               or str(err_body))
                except Exception:
                    err_msg = resp.text[:200]

                retry_after = int(resp.headers.get("retry-after", "0") or "0")

                # Daily / quota exhausted → mark key exhausted
                is_daily = (retry_after > 3600 or
                            "per day" in err_msg.lower() or
                            "quota" in err_msg.lower() or
                            "RESOURCE_EXHAUSTED" in err_msg)
                if is_daily:
                    ok = rotator.rotate(exhausted=True)
                    consecutive_429 = 0
                    if not ok:
                        continue  # outer while → wait_for_reset
                    continue

                # RPM limit — use retry-after or back off
                if retry_after and retry_after < 120:
                    log.warning("  RPM limit — waiting %ds (key %d/%d)",
                                retry_after, rotator.idx + 1, len(rotator.keys))
                    time.sleep(retry_after + 1)
                    consecutive_429 = 0
                    continue

                # All keys saturated simultaneously — back off
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

    count = errors = skipped = 0
    phase1_limit = min(args.limit, len(pending))
    log.info("Phase 1: generating %d articles (limit=%d, pending=%d)",
             phase1_limit, args.limit, len(pending))

    for i, (category, topic) in enumerate(pending):
        if count >= args.limit:
            break

        log.info("[%d/%d] %s / %s", count + 1, phase1_limit, category, topic)

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
