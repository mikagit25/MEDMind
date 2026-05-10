#!/usr/bin/env python3
"""Mass medical image importer — Wikimedia Commons + OpenI NLM.

Sources:
  1. Wikimedia Commons — Blausen Medical 3D illustrations (CC BY 3.0)
     + radiology, histology, anatomy categories
  2. OpenI NLM — real clinical images from peer-reviewed articles (open access)

Target: 500–2000 images across all medical specialties.

Run inside backend container:
  docker cp import_images_mass.py medmind_backend:/app/
  docker exec -d -u root medmind_backend python /app/import_images_mass.py
  docker exec medmind_backend tail -f /tmp/import_images.log
"""

import json
import logging
import re
import sys
import time
import uuid
from html import unescape

import psycopg2
import psycopg2.extras
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/tmp/import_images.log", mode="w"),
    ],
)
log = logging.getLogger("img_import")

DB_DSN = "host=172.18.0.2 port=5432 dbname=medmind user=medmind password=medmind_secret"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
OPENI_API = "https://openi.nlm.nih.gov/api/search"
THUMB_WIDTH = 800
SESSION = requests.Session()
SESSION.headers["User-Agent"] = "MedMind-Importer/1.0 (medical education; contact@medmind.pro)"


# ── Wikimedia Commons search topics ───────────────────────────────────────────
# (search_query, modality, anatomy_region, specialty)
COMMONS_SEARCHES = [
    # Blausen Medical 3D Illustrations (premium CC BY 3.0)
    ("Blausen 0 heart anatomy", "anatomy", "heart", "cardiology"),
    ("Blausen 0 brain anatomy", "anatomy", "brain", "neurology"),
    ("Blausen 0 lung anatomy", "anatomy", "lung", "pulmonology"),
    ("Blausen 0 kidney anatomy", "anatomy", "kidney", "nephrology"),
    ("Blausen 0 liver anatomy", "anatomy", "liver", "gastroenterology"),
    ("Blausen 0 spine vertebra", "anatomy", "spine", "orthopedics"),
    ("Blausen 0 knee anatomy", "anatomy", "knee", "orthopedics"),
    ("Blausen 0 hip anatomy", "anatomy", "pelvis", "orthopedics"),
    ("Blausen 0 shoulder anatomy", "anatomy", "shoulder", "orthopedics"),
    ("Blausen 0 eye anatomy", "anatomy", "eye", "ophthalmology"),
    ("Blausen 0 ear anatomy", "anatomy", "ear", "ENT"),
    ("Blausen 0 thyroid anatomy", "anatomy", "neck", "endocrinology"),
    ("Blausen 0 pancreas anatomy", "anatomy", "abdomen", "gastroenterology"),
    ("Blausen 0 stomach anatomy", "anatomy", "abdomen", "gastroenterology"),
    ("Blausen 0 colon anatomy", "anatomy", "abdomen", "gastroenterology"),
    ("Blausen 0 urinary bladder", "anatomy", "pelvis", "urology"),
    ("Blausen 0 prostate anatomy", "anatomy", "pelvis", "urology"),
    ("Blausen 0 uterus anatomy", "anatomy", "pelvis", "gynecology"),
    ("Blausen 0 skin anatomy", "anatomy", "skin", "dermatology"),
    ("Blausen 0 muscle anatomy", "anatomy", "musculoskeletal", "anatomy"),
    ("Blausen 0 skull anatomy", "anatomy", "skull", "neurosurgery"),
    ("Blausen 0 tooth dental anatomy", "anatomy", "oral", "dentistry"),
    ("Blausen 0 blood cell", "anatomy", "blood", "hematology"),
    ("Blausen 0 lymph node", "anatomy", "lymphatic", "immunology"),
    ("Blausen 0 neuron nerve", "anatomy", "nervous system", "neurology"),
    ("Blausen 0 alveoli lung", "anatomy", "lung", "pulmonology"),
    ("Blausen 0 glomerulus kidney", "anatomy", "kidney", "nephrology"),
    ("Blausen 0 bone osteoporosis", "anatomy", "bone", "orthopedics"),
    ("Blausen 0 artery atherosclerosis", "anatomy", "cardiovascular", "cardiology"),
    ("Blausen 0 aortic aneurysm", "anatomy", "cardiovascular", "vascular surgery"),
    # X-ray radiology
    ("chest radiograph pneumonia", "xray", "chest", "pulmonology"),
    ("chest X-ray tuberculosis", "xray", "chest", "infectious disease"),
    ("chest radiograph normal", "xray", "chest", "radiology"),
    ("bone fracture radiograph", "xray", "extremity", "orthopedics"),
    ("knee radiograph osteoarthritis", "xray", "knee", "orthopedics"),
    ("spine radiograph scoliosis", "xray", "spine", "orthopedics"),
    ("hip fracture X-ray", "xray", "pelvis", "orthopedics"),
    ("wrist fracture radiograph", "xray", "upper extremity", "orthopedics"),
    ("abdominal X-ray bowel", "xray", "abdomen", "surgery"),
    ("skull X-ray", "xray", "skull", "radiology"),
    # CT scans
    ("CT brain scan stroke", "ct", "brain", "neurology"),
    ("CT chest lung cancer", "ct", "chest", "oncology"),
    ("CT abdomen appendicitis", "ct", "abdomen", "surgery"),
    ("CT head trauma", "ct", "brain", "emergency"),
    ("CT scan coronary", "ct", "heart", "cardiology"),
    # MRI
    ("brain MRI tumor", "mri", "brain", "neurology"),
    ("knee MRI meniscus", "mri", "knee", "orthopedics"),
    ("spine MRI disc herniation", "mri", "spine", "neurosurgery"),
    ("brain MRI multiple sclerosis", "mri", "brain", "neurology"),
    ("cardiac MRI", "mri", "heart", "cardiology"),
    # Histology / pathology
    ("histology cancer pathology", "histology", "tissue", "pathology"),
    ("histology normal tissue", "histology", "tissue", "pathology"),
    ("renal biopsy histology", "histology", "kidney", "nephrology"),
    ("lung histopathology", "histology", "lung", "pathology"),
    ("liver biopsy cirrhosis histology", "histology", "liver", "pathology"),
    ("bone marrow histology", "histology", "blood", "hematology"),
    # Ultrasound
    ("ultrasound fetal pregnancy", "ultrasound", "obstetrics", "obstetrics"),
    ("echocardiogram ultrasound", "ultrasound", "heart", "cardiology"),
    ("abdominal ultrasound liver", "ultrasound", "abdomen", "gastroenterology"),
    ("thyroid ultrasound", "ultrasound", "neck", "endocrinology"),
    # Dermatology
    ("skin lesion melanoma", "dermatoscopy", "skin", "dermatology"),
    ("eczema dermatitis skin", "dermatoscopy", "skin", "dermatology"),
    ("psoriasis plaque", "dermatoscopy", "skin", "dermatology"),
    ("rash urticaria", "dermatoscopy", "skin", "dermatology"),
    # Ophthalmology
    ("fundus eye diabetic retinopathy", "fundoscopy", "eye", "ophthalmology"),
    ("fundus optic disc glaucoma", "fundoscopy", "eye", "ophthalmology"),
    ("retinal detachment fundoscopy", "fundoscopy", "eye", "ophthalmology"),
    # Dentistry
    ("dental panoramic X-ray", "xray", "oral", "dentistry"),
    ("tooth anatomy dental", "anatomy", "oral", "dentistry"),
]

# ── OpenI NLM topic searches ───────────────────────────────────────────────────
OPENI_SEARCHES = [
    ("chest radiograph pneumonia", "xray", "chest", "pulmonology"),
    ("tuberculosis chest xray", "xray", "chest", "infectious disease"),
    ("lung cancer CT", "ct", "chest", "oncology"),
    ("brain MRI ischemic stroke", "mri", "brain", "neurology"),
    ("brain CT hemorrhage", "ct", "brain", "neurology"),
    ("knee MRI tear", "mri", "knee", "orthopedics"),
    ("abdominal CT appendicitis", "ct", "abdomen", "surgery"),
    ("cardiac MRI echocardiogram", "mri", "heart", "cardiology"),
    ("mammography breast cancer", "xray", "breast", "oncology"),
    ("ultrasound liver gallbladder", "ultrasound", "abdomen", "gastroenterology"),
    ("histology cancer pathology", "histology", "tissue", "pathology"),
    ("retinal fundus diabetic", "fundoscopy", "eye", "ophthalmology"),
    ("spine MRI herniation", "mri", "spine", "neurosurgery"),
    ("skin dermatology lesion", "dermatoscopy", "skin", "dermatology"),
    ("bone fracture radiograph", "xray", "extremity", "orthopedics"),
    ("CT pulmonary embolism", "ct", "chest", "pulmonology"),
    ("brain tumor MRI glioma", "mri", "brain", "oncology"),
    ("heart failure cardiomegaly", "xray", "chest", "cardiology"),
    ("liver cirrhosis histology", "histology", "liver", "gastroenterology"),
    ("kidney renal MRI CT", "ct", "kidney", "nephrology"),
]


def strip_html(text: str) -> str:
    if not text:
        return ""
    text = unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:500]


def get_existing_urls(conn) -> set:
    cur = conn.cursor()
    cur.execute("SELECT image_url FROM medical_images WHERE is_user_upload = false")
    return {row[0] for row in cur.fetchall()}


def insert_image(cur, rec: dict, existing_urls: set) -> bool:
    url = rec.get("image_url", "")
    if not url or url in existing_urls:
        return False
    if not any(url.lower().endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp")):
        return False
    existing_urls.add(url)

    try:
        cur.execute("""
            INSERT INTO medical_images
              (id, title, description, modality, anatomy_region, specialty,
               image_url, thumbnail_url, source_name, source_url, license,
               attribution, tags, is_active, view_count, is_user_upload, created_at)
            VALUES
              (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,true,0,false,NOW())
        """, (
            str(uuid.uuid4()),
            rec["title"][:299],
            rec.get("description", "")[:2000],
            rec.get("modality", "other"),
            rec.get("anatomy_region"),
            rec.get("specialty"),
            url,
            rec.get("thumbnail_url", url),
            rec.get("source_name", "Wikimedia Commons"),
            rec.get("source_url"),
            rec.get("license", "CC BY-SA 3.0"),
            rec.get("attribution", rec.get("source_name", "Wikimedia Commons")),
            json.dumps(rec.get("tags", [])),
        ))
        return True
    except Exception as e:
        log.warning("Insert failed for %s: %s", url[:60], e)
        return False


# ── Wikimedia Commons importer ─────────────────────────────────────────────────

def search_commons(query: str, modality: str, region: str, specialty: str,
                   limit: int = 50) -> list[dict]:
    results = []
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": f"File: {query}",
        "gsrnamespace": 6,
        "gsrlimit": min(limit, 50),
        "prop": "imageinfo",
        "iiprop": "url|mime|extmetadata",
        "iiurlwidth": THUMB_WIDTH,
        "format": "json",
    }
    try:
        r = SESSION.get(COMMONS_API, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        log.warning("Commons search error '%s': %s", query, e)
        return results

    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        ii = page.get("imageinfo", [{}])[0]
        url = ii.get("url", "")
        thumb = ii.get("thumburl", url)
        mime = ii.get("mime", "")

        if not url:
            continue
        # Accept by mime OR by extension (API sometimes omits mime)
        url_lower = url.lower()
        valid_ext = any(url_lower.endswith(ext) for ext in (".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp"))
        valid_mime = mime in ("image/jpeg", "image/png", "image/svg+xml", "image/gif", "image/webp")
        if not valid_ext and not valid_mime:
            continue

        meta = ii.get("extmetadata", {})
        title_raw = page.get("title", "").replace("File:", "").replace("_", " ")
        # Clean Blausen titles: "Blausen 0597 KneeAnatomy Side-es.png" → "Knee Anatomy"
        title_clean = re.sub(r"^Blausen\s+\d+\s*", "", title_raw)
        title_clean = re.sub(r"\.(png|jpg|jpeg|svg|gif)$", "", title_clean, flags=re.I)
        title_clean = re.sub(r"[-_]", " ", title_clean)
        title_clean = re.sub(r"\s+", " ", title_clean).strip()
        # Remove language suffixes like "-es", "-de", "-fr", "-nl"
        title_clean = re.sub(r"\s+-\s*[a-z]{2}$", "", title_clean)
        if len(title_clean) < 4 or title_clean.lower() in ("", "unknown"):
            title_clean = title_raw[:60]

        desc_raw = meta.get("ImageDescription", {}).get("value", "")
        desc = strip_html(desc_raw) or f"Medical image: {title_clean}"
        if len(desc) < 10:
            desc = f"Medical illustration — {title_clean}. Modality: {modality.upper()}. Region: {region}."

        license_name = (
            meta.get("LicenseShortName", {}).get("value")
            or meta.get("License", {}).get("value")
            or "CC BY-SA 3.0"
        )
        artist = strip_html(meta.get("Artist", {}).get("value", "")) or "Wikimedia Commons"
        if "Blausen" in url:
            license_name = "CC BY 3.0"
            artist = "Blausen Medical Communications Inc."

        file_name = url.rsplit("/", 1)[-1]
        source_url = f"https://commons.wikimedia.org/wiki/File:{file_name}"

        results.append({
            "title": title_clean[:299],
            "description": desc,
            "modality": modality,
            "anatomy_region": region,
            "specialty": specialty,
            "image_url": url,
            "thumbnail_url": thumb or url,
            "source_name": "Wikimedia Commons",
            "source_url": source_url,
            "license": license_name,
            "attribution": f"{artist} via Wikimedia Commons",
            "tags": [modality, region, specialty, query.split()[0].lower()],
        })

    time.sleep(0.5)  # polite delay
    return results


def import_commons(conn) -> int:
    existing = get_existing_urls(conn)
    cur = conn.cursor()
    total = 0

    for i, (query, modality, region, specialty) in enumerate(COMMONS_SEARCHES, 1):
        log.info("[Commons %d/%d] %s → %s/%s", i, len(COMMONS_SEARCHES), query, modality, region)
        images = search_commons(query, modality, region, specialty, limit=50)

        added = 0
        for img in images:
            if insert_image(cur, img, existing):
                added += 1
                total += 1

        conn.commit()
        log.info("  Added %d/%d images (total so far: %d)", added, len(images), total)

    return total


# ── OpenI NLM importer ─────────────────────────────────────────────────────────

def search_openi(query: str, modality: str, region: str, specialty: str,
                 n: int = 50) -> list[dict]:
    results = []
    params = {
        "query": query,
        "n": min(n, 100),
        "m": 1,
    }
    try:
        r = SESSION.get(OPENI_API, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        log.warning("OpenI error '%s': %s", query, e)
        return results

    base_url = "https://openi.nlm.nih.gov"
    for rec in data.get("list", []):
        img_path = rec.get("imgLarge", "")
        if not img_path:
            continue
        img_url = base_url + img_path
        thumb_url = base_url + (rec.get("imgSmall") or rec.get("imgThumb") or img_path)

        caption = rec.get("caption") or ""
        if isinstance(caption, dict):
            caption = caption.get("_", "") or ""
        caption = caption.strip()

        article_title = (rec.get("title") or "").strip()
        abstract = (rec.get("abstractText") or "").strip()[:400]

        if caption and len(caption) > 20:
            title = caption[:100]
            desc = caption
            if abstract:
                desc += f" Context: {abstract[:300]}"
        elif article_title:
            title = article_title[:100]
            desc = article_title
            if abstract:
                desc += f". {abstract[:400]}"
        else:
            continue

        mesh = rec.get("MeSHmajor") or []
        tags = [modality, region] + [m.lower() for m in mesh[:3] if m]

        pmid = str(rec.get("uid", ""))
        source_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None

        results.append({
            "title": title[:299],
            "description": desc[:2000],
            "modality": modality,
            "anatomy_region": region,
            "specialty": specialty,
            "image_url": img_url,
            "thumbnail_url": thumb_url,
            "source_name": "Open-i (NLM/NIH)",
            "source_url": source_url,
            "license": "Open Access",
            "attribution": f"Open-i Medical Image Database, National Library of Medicine. PMID:{pmid}" if pmid else "NLM Open-i",
            "tags": tags,
        })

    time.sleep(1.0)
    return results


def import_openi(conn) -> int:
    existing = get_existing_urls(conn)
    cur = conn.cursor()
    total = 0

    for i, (query, modality, region, specialty) in enumerate(OPENI_SEARCHES, 1):
        log.info("[OpenI %d/%d] %s → %s/%s", i, len(OPENI_SEARCHES), query, modality, region)
        images = search_openi(query, modality, region, specialty, n=50)

        added = 0
        for img in images:
            if insert_image(cur, img, existing):
                added += 1
                total += 1

        conn.commit()
        log.info("  Added %d/%d images (total so far: %d)", added, len(images), total)

    return total


# ── Additional Wikimedia categories (direct category search) ──────────────────
WIKI_CATEGORIES = [
    ("Category:Blausen Medical", "anatomy", "human body", "anatomy"),
    ("Category:MRI scans of the brain", "mri", "brain", "neurology"),
    ("Category:Chest radiographs", "xray", "chest", "radiology"),
    ("Category:CT scans of the brain", "ct", "brain", "radiology"),
    ("Category:Histology", "histology", "tissue", "pathology"),
    ("Category:Dermatology images", "dermatoscopy", "skin", "dermatology"),
    ("Category:Ophthalmology", "fundoscopy", "eye", "ophthalmology"),
    ("Category:Bone fractures", "xray", "extremity", "orthopedics"),
    ("Category:Echocardiography", "ultrasound", "heart", "cardiology"),
    ("Category:Mammography", "xray", "breast", "oncology"),
]


def import_category(conn, category: str, modality: str, region: str, specialty: str,
                    limit: int = 100) -> int:
    existing = get_existing_urls(conn)
    cur = conn.cursor()
    total = 0
    cm_continue = None

    while True:
        params: dict = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category,
            "cmtype": "file",
            "cmlimit": 50,
            "format": "json",
        }
        if cm_continue:
            params["cmcontinue"] = cm_continue

        try:
            r = SESSION.get(COMMONS_API, params=params, timeout=20)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            log.warning("Category error %s: %s", category, e)
            break

        members = data.get("query", {}).get("categorymembers", [])
        if not members:
            break

        # Get image info for these files
        titles = "|".join(m["title"] for m in members[:20])
        info_params = {
            "action": "query",
            "titles": titles,
            "prop": "imageinfo",
            "iiprop": "url|mime|extmetadata",
            "iiurlwidth": THUMB_WIDTH,
            "format": "json",
        }
        try:
            ri = SESSION.get(COMMONS_API, params=info_params, timeout=20)
            ri.raise_for_status()
            idata = ri.json()
        except Exception as e:
            log.warning("Image info error: %s", e)
            break

        pages = idata.get("query", {}).get("pages", {})
        for page in pages.values():
            ii = page.get("imageinfo", [{}])[0]
            url = ii.get("url", "")
            if not url:
                continue
            mime = ii.get("mime", "")
            if mime not in ("image/jpeg", "image/png", "image/svg+xml"):
                continue

            meta = ii.get("extmetadata", {})
            title_raw = page.get("title", "").replace("File:", "").replace("_", " ")
            title_clean = re.sub(r"\.(png|jpg|jpeg|svg|gif)$", "", title_raw, flags=re.I).strip()
            title_clean = re.sub(r"^Blausen\s+\d+\s*", "", title_clean)

            desc_raw = meta.get("ImageDescription", {}).get("value", "")
            desc = strip_html(desc_raw) or f"Medical image: {title_clean}"

            license_name = meta.get("LicenseShortName", {}).get("value", "CC BY-SA 3.0")
            artist = strip_html(meta.get("Artist", {}).get("value", ""))
            if "Blausen" in url:
                license_name = "CC BY 3.0"
                artist = "Blausen Medical"

            file_name = url.rsplit("/", 1)[-1]
            thumb = ii.get("thumburl", url)
            rec = {
                "title": title_clean[:299],
                "description": desc,
                "modality": modality,
                "anatomy_region": region,
                "specialty": specialty,
                "image_url": url,
                "thumbnail_url": thumb,
                "source_name": "Wikimedia Commons",
                "source_url": f"https://commons.wikimedia.org/wiki/File:{file_name}",
                "license": license_name,
                "attribution": f"{artist} via Wikimedia Commons" if artist else "Wikimedia Commons",
                "tags": [modality, region, specialty],
            }
            if insert_image(cur, rec, existing):
                total += 1

        conn.commit()
        time.sleep(0.5)

        cont = data.get("continue", {}).get("cmcontinue")
        if not cont or total >= limit:
            break
        cm_continue = cont

    return total


def main():
    log.info("=" * 60)
    log.info("MedMind Mass Image Importer")
    log.info("=" * 60)

    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = False

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM medical_images WHERE is_user_upload=false")
    start_count = cur.fetchone()[0]
    log.info("Starting image count: %d", start_count)

    grand_total = 0

    # Phase 1: Wikimedia Commons searches
    log.info("\n=== PHASE 1: Wikimedia Commons searches ===")
    n = import_commons(conn)
    grand_total += n
    log.info("Phase 1 done: +%d images", n)

    # Phase 2: Wikimedia Commons category imports
    log.info("\n=== PHASE 2: Wikimedia Commons categories ===")
    for category, modality, region, specialty in WIKI_CATEGORIES:
        log.info("Category: %s", category)
        n = import_category(conn, category, modality, region, specialty, limit=100)
        grand_total += n
        log.info("  +%d from %s", n, category)

    # Phase 3: OpenI NLM
    log.info("\n=== PHASE 3: OpenI NLM ===")
    n = import_openi(conn)
    grand_total += n
    log.info("Phase 3 done: +%d images", n)

    # Final stats
    cur.execute("""
        SELECT modality, COUNT(*) as cnt
        FROM medical_images WHERE is_user_upload=false
        GROUP BY modality ORDER BY cnt DESC
    """)
    log.info("\n=== FINAL STATS ===")
    total_final = 0
    for row in cur.fetchall():
        log.info("  %s: %d", row[0], row[1])
        total_final += row[1]
    log.info("TOTAL IMAGES: %d (+%d new)", total_final, grand_total)

    conn.close()


if __name__ == "__main__":
    main()
