#!/usr/bin/env python3
"""Generate veterinary articles via Ollama and insert into DB.

Run from HOST (has internet for translations):
  nohup python3 /opt/medmind/generate_vet_articles.py > /tmp/vet_articles.log 2>&1 &
  tail -f /tmp/vet_articles.log
"""
import json
import re
import time
import uuid
import logging
import sys
import requests
import psycopg2
import psycopg2.extras

DB_DSN = "host=172.18.0.2 port=5432 dbname=medmind user=medmind password=medmind_secret"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3:8b"
LOG = "/tmp/vet_articles.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(LOG, mode="w")],
)
log = logging.getLogger()

LOCALES = ["ru", "de", "fr", "es", "tr", "ar"]

VET_ARTICLES = [
    # Pharmacology / Species differences
    ("Feline Drug Metabolism: Why Cats Need Different Medications", "veterinary", "pharmacology"),
    ("Canine Toxicology: Common Household Poisons in Dogs", "veterinary", "toxicology"),
    ("MDR1 Gene Mutation in Dogs: Ivermectin Sensitivity and Safe Prescribing", "veterinary", "pharmacology"),
    ("Veterinary NSAIDs: Species-Specific Safety and Contraindications", "veterinary", "pharmacology"),
    ("Antibiotic Use in Exotic Pets: Rabbits, Guinea Pigs and Birds", "veterinary", "pharmacology"),
    ("Equine Pharmacology: Bioavailability and Drug Administration in Horses", "veterinary", "pharmacology"),

    # Internal medicine — dog
    ("Canine Diabetes Mellitus: Diagnosis and Insulin Management", "veterinary", "internal-medicine"),
    ("Canine Hypothyroidism: Clinical Signs, Diagnosis and Treatment", "veterinary", "internal-medicine"),
    ("Canine Hyperadrenocorticism (Cushing's Disease): Diagnosis and Management", "veterinary", "internal-medicine"),
    ("Immune-Mediated Haemolytic Anaemia in Dogs", "veterinary", "internal-medicine"),
    ("Canine Dilated Cardiomyopathy: Pathophysiology and Treatment", "veterinary", "cardiology"),
    ("Gastric Dilatation-Volvulus in Dogs: Emergency Management", "veterinary", "emergency"),
    ("Canine Parvovirus: Pathogenesis, Diagnosis and Supportive Care", "veterinary", "infectious-diseases"),
    ("Canine Hip Dysplasia: Pathophysiology and Treatment Options", "veterinary", "orthopedics"),
    ("Epilepsy in Dogs: Classification and Anticonvulsant Therapy", "veterinary", "neurology"),

    # Internal medicine — cat
    ("Feline Hyperthyroidism: Diagnosis and Treatment Options", "veterinary", "internal-medicine"),
    ("Feline Chronic Kidney Disease: Staging and Management", "veterinary", "nephrology"),
    ("Feline Lower Urinary Tract Disease (FLUTD): Pathophysiology and Treatment", "veterinary", "urology"),
    ("Feline Asthma vs Cardiac Disease: Differential Diagnosis", "veterinary", "pulmonology"),
    ("Feline Infectious Peritonitis (FIP): Pathogenesis and Treatment", "veterinary", "infectious-diseases"),
    ("Feline Hypertension: Causes, Assessment and Amlodipine Therapy", "veterinary", "cardiology"),
    ("Feline Pancreatitis: Clinical Signs, Diagnosis and Management", "veterinary", "gastroenterology"),

    # Exotic animals
    ("GI Stasis in Rabbits: Emergency Recognition and Treatment", "veterinary", "emergency"),
    ("Rabbit Dental Disease (Malocclusion): Diagnosis and Management", "veterinary", "dentistry"),
    ("Avian Psittacosis: Zoonotic Infection, Diagnosis and Treatment", "veterinary", "infectious-diseases"),
    ("Psittacine Beak and Feather Disease: Diagnosis and Management", "veterinary", "infectious-diseases"),
    ("Reptile Husbandry-Related Disease: Metabolic Bone Disease in Lizards", "veterinary", "nutrition"),

    # Equine
    ("Equine Colic: Classification, Triage and Surgical Indications", "veterinary", "emergency"),
    ("PPID (Equine Cushing's Disease): Diagnosis and Pergolide Therapy", "veterinary", "internal-medicine"),
    ("Equine Laminitis: Pathophysiology, Stages and Emergency Treatment", "veterinary", "orthopedics"),

    # Zoonoses / public health
    ("Rabies: Virology, Prevention and Post-Exposure Prophylaxis", "veterinary", "infectious-diseases"),
    ("Leptospirosis: Epidemiology, Clinical Presentation and Treatment", "veterinary", "infectious-diseases"),
    ("Toxoplasmosis: Life Cycle, Risk Groups and Prevention", "veterinary", "infectious-diseases"),

    # Surgery / anaesthesia
    ("Veterinary Anaesthesia in Brachycephalic Dogs: Key Considerations", "veterinary", "anaesthesia"),
    ("Feline Castration and Spaying: Anaesthetic Protocols and Complications", "veterinary", "surgery"),

    # Nutrition / preventive
    ("Canine and Feline Obesity: Assessment and Dietary Management", "veterinary", "nutrition"),
    ("Vaccination Protocols for Dogs and Cats: Core vs Non-Core Vaccines", "veterinary", "preventive"),
    ("Canine Parvovirus Prevention: Vaccination, Disinfection and Quarantine", "veterinary", "preventive"),
]


SYSTEM_PROMPT = """You are a veterinary medicine expert writing educational content for veterinary students,
veterinary technicians, and clinicians. Write comprehensive, evidence-based veterinary articles.
Always write in English. Be specific, clinical, and educational. Include:
- Clear pathophysiology
- Species-specific considerations
- Diagnostic criteria
- Treatment protocols with actual drug names and doses
- Clinical pearls and common mistakes
- Prognosis information"""

ARTICLE_PROMPT = """Write a comprehensive veterinary medical article titled: "{title}"

Structure the article as a JSON object with this exact format:
{{
  "excerpt": "2-3 sentence clinical summary for veterinary professionals",
  "body": [
    {{"type": "h2", "content": "Section heading"}},
    {{"type": "p", "content": "Detailed paragraph text"}},
    {{"type": "ul", "items": ["bullet point 1", "bullet point 2", "bullet point 3"]}},
    {{"type": "h3", "content": "Subsection heading"}},
    {{"type": "p", "content": "More detailed text"}},
    {{"type": "callout", "content": "Clinical pearl or important warning"}}
  ],
  "faq": [
    {{"question": "Clinical question?", "answer": "Detailed answer."}}
  ],
  "keywords": ["keyword1", "keyword2"]
}}

Requirements:
- 8-12 body blocks covering: overview, pathophysiology, clinical signs, diagnosis, treatment, prognosis
- Include specific drug names, doses, and diagnostic values
- Include 3 FAQ entries and 5 keywords
- Use callout blocks for important clinical warnings

Topic context: {category} — {specialty}

Respond with ONLY the JSON object, no other text."""


def generate_article(title: str, category: str, specialty: str) -> dict | None:
    prompt = ARTICLE_PROMPT.format(title=title, category=category, specialty=specialty)
    try:
        # Use streaming to avoid read timeout on slow CPU inference
        r = requests.post(OLLAMA_URL, json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "system": SYSTEM_PROMPT,
            "stream": True,
            "options": {"temperature": 0.3, "num_predict": 2500, "num_ctx": 4096},
        }, stream=True, timeout=30)
        if r.status_code != 200:
            log.error("Ollama HTTP %d", r.status_code)
            return None

        # Collect streamed tokens
        raw = ""
        last_tok = time.time()
        for line in r.iter_lines():
            if not line:
                continue
            try:
                chunk = json.loads(line)
                raw += chunk.get("response", "")
                last_tok = time.time()
                if chunk.get("done"):
                    break
            except Exception:
                pass
            # Safety timeout: 600s total
            if time.time() - last_tok > 120:
                log.warning("Token stream stalled for %s", title)
                break

        # Extract JSON
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            log.error("No JSON found in response for: %s", title)
            return None
        return json.loads(m.group())
    except json.JSONDecodeError as e:
        log.error("JSON parse error for %s: %s", title, e)
        return None
    except Exception as e:
        log.error("Ollama error for %s: %s", title, e)
        return None


def slugify(title: str) -> str:
    s = title.lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s.strip("-")[:120]


def translate_text(text: str, target: str) -> str:
    if not text or not text.strip():
        return text
    try:
        r = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "en", "tl": target, "dt": "t", "q": text[:4500]},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=20,
        )
        if r.status_code == 200:
            data = r.json()
            return "".join(seg[0] for seg in data[0] if seg and seg[0]).strip() or text
    except Exception:
        pass
    return text


def translate_body(body: list, target: str) -> list:
    result = []
    for block in body:
        b = dict(block)
        if b.get("type") in ("h2", "h3", "h4", "p", "callout") and b.get("content"):
            b["content"] = translate_text(b["content"], target)
            time.sleep(0.15)
        elif b.get("type") in ("ul", "ol") and b.get("items"):
            sep = " |||SEP||| "
            joined = sep.join(b["items"])
            translated = translate_text(joined[:4500], target)
            parts = translated.split("|||SEP|||")
            if len(parts) == len(b["items"]):
                b["items"] = [p.strip() for p in parts]
            else:
                b["items"] = [translate_text(item, target) for item in b["items"]]
        result.append(b)
    return result


def translate_faq(faq: list, target: str) -> list:
    result = []
    for item in faq:
        result.append({
            "question": translate_text(item.get("question", ""), target),
            "answer": translate_text(item.get("answer", ""), target),
        })
        time.sleep(0.1)
    return result


def insert_article(conn, title: str, slug: str, category: str, specialty: str, article: dict) -> str | None:
    cur = conn.cursor()
    aid = str(uuid.uuid4())
    excerpt = article.get("excerpt", "")
    body = article.get("body", [])
    faq = article.get("faq", [])
    keywords = article.get("keywords", [])

    # Check slug uniqueness
    cur.execute("SELECT 1 FROM articles WHERE slug = %s", (slug,))
    if cur.fetchone():
        slug = slug + "-" + aid[:8]

    try:
        cur.execute("""
            INSERT INTO articles
              (id, title, slug, excerpt, body, faq, category, keywords,
               is_published, review_status, generated_by, reading_time_minutes,
               created_at, updated_at, published_at)
            VALUES
              (%s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s::jsonb,
               true, 'published', 'ai-ollama', %s,
               NOW(), NOW(), NOW())
        """, (
            aid, title, slug, excerpt,
            json.dumps(body, ensure_ascii=False),
            json.dumps(faq, ensure_ascii=False),
            category,
            json.dumps(keywords, ensure_ascii=False),
            max(5, len(body) // 3),
        ))
        conn.commit()
        return aid
    except Exception as e:
        conn.rollback()
        log.error("Insert error for %s: %s", title, e)
        return None


def insert_translations(conn, article_id: str, title: str, excerpt: str, body: list, faq: list):
    cur = conn.cursor()
    for locale in LOCALES:
        log.info("  Translating %s...", locale)
        try:
            tr_title = translate_text(title, locale)
            tr_excerpt = translate_text(excerpt, locale)
            tr_body = translate_body(body, locale)
            tr_faq = translate_faq(faq, locale)

            cur.execute("""
                INSERT INTO article_translations
                  (article_id, locale, title, excerpt, body, faq, status, created_at, updated_at)
                VALUES
                  (%s, %s, %s, %s, %s::jsonb, %s::jsonb, 'done', NOW(), NOW())
                ON CONFLICT (article_id, locale) DO UPDATE SET
                  title = EXCLUDED.title,
                  excerpt = EXCLUDED.excerpt,
                  body = EXCLUDED.body,
                  faq = EXCLUDED.faq,
                  status = 'done',
                  updated_at = NOW()
            """, (
                article_id, locale, tr_title, tr_excerpt,
                json.dumps(tr_body, ensure_ascii=False),
                json.dumps(tr_faq, ensure_ascii=False),
            ))
            conn.commit()
            time.sleep(0.5)
        except Exception as e:
            conn.rollback()
            log.error("Translation error %s/%s: %s", article_id, locale, e)


def main():
    conn = psycopg2.connect(DB_DSN)

    # Check existing vet articles
    cur = conn.cursor()
    cur.execute("SELECT slug FROM articles WHERE category = 'veterinary'")
    existing_slugs = {r[0] for r in cur.fetchall()}
    log.info("=== Veterinary Article Generator ===")
    log.info("Existing vet articles: %d", len(existing_slugs))
    log.info("Articles to generate: %d", len(VET_ARTICLES))

    total_ok = 0
    for i, (title, category, specialty) in enumerate(VET_ARTICLES, 1):
        slug = slugify(title)
        if slug in existing_slugs or slug + "-" in " ".join(existing_slugs):
            log.info("[%d/%d] SKIP (exists): %s", i, len(VET_ARTICLES), title[:60])
            continue

        log.info("[%d/%d] Generating: %s", i, len(VET_ARTICLES), title[:70])
        t0 = time.time()
        article = generate_article(title, category, specialty)
        if not article:
            log.warning("  FAILED to generate: %s", title)
            continue

        blocks = len(article.get("body", []))
        elapsed = time.time() - t0
        log.info("  Generated %d blocks in %.0fs", blocks, elapsed)

        article_id = insert_article(conn, title, slug, category, specialty, article)
        if not article_id:
            continue

        existing_slugs.add(slug)
        total_ok += 1

        # Translate
        log.info("  Translating to %d locales...", len(LOCALES))
        insert_translations(
            conn, article_id, title,
            article.get("excerpt", ""),
            article.get("body", []),
            article.get("faq", []),
        )
        log.info("  Done. Total so far: %d", total_ok)

    log.info("=== COMPLETE. Generated %d veterinary articles ===", total_ok)
    conn.close()


if __name__ == "__main__":
    main()
