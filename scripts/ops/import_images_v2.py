#!/usr/bin/env python3
"""Mass medical image importer v2 — Wikimedia Commons.

Fetches medical images from Wikimedia Commons using proper Session/UA.
Run from HOST (has internet access):
  nohup python3 /opt/medmind/import_images_v2.py &
  tail -f /tmp/import_v2.log
"""
import json
import logging
import re
import sys
import time
import uuid
from html import unescape

import psycopg2
import requests

# ── Config ────────────────────────────────────────────────────────────────────
DB_DSN = "host=172.18.0.2 port=5432 dbname=medmind user=medmind password=medmind_secret"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
LOG = "/tmp/import_v2.log"
VALID_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp"}
VALID_MIMES = {"image/jpeg", "image/png", "image/svg+xml", "image/gif", "image/webp"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(LOG, mode="w")],
)
log = logging.getLogger()

S = requests.Session()
S.headers["User-Agent"] = "MedMind-Educational/2.0 (https://medmind.pro; medmind.edu.bot@gmail.com)"

# ── Search topics ─────────────────────────────────────────────────────────────
# (search_term, modality, region, specialty, limit)
SEARCHES = [
    # Blausen Medical 3D illustrations — CC BY 3.0, professional quality
    ("Blausen heart anatomy", "anatomy", "heart", "cardiology", 80),
    ("Blausen brain anatomy", "anatomy", "brain", "neurology", 80),
    ("Blausen lung anatomy", "anatomy", "lung", "pulmonology", 60),
    ("Blausen kidney anatomy", "anatomy", "kidney", "nephrology", 50),
    ("Blausen liver anatomy", "anatomy", "liver", "gastroenterology", 50),
    ("Blausen spine anatomy", "anatomy", "spine", "orthopedics", 60),
    ("Blausen joint anatomy", "anatomy", "joints", "orthopedics", 60),
    ("Blausen muscle anatomy", "anatomy", "musculoskeletal", "anatomy", 60),
    ("Blausen skull bone anatomy", "anatomy", "skull", "anatomy", 50),
    ("Blausen eye anatomy", "anatomy", "eye", "ophthalmology", 40),
    ("Blausen ear anatomy", "anatomy", "ear", "ENT", 40),
    ("Blausen skin anatomy", "anatomy", "skin", "dermatology", 40),
    ("Blausen blood cell", "anatomy", "blood", "hematology", 40),
    ("Blausen thyroid anatomy", "anatomy", "neck", "endocrinology", 30),
    ("Blausen pancreas anatomy", "anatomy", "abdomen", "gastroenterology", 30),
    ("Blausen reproductive anatomy", "anatomy", "pelvis", "gynecology", 40),
    ("Blausen urinary anatomy", "anatomy", "pelvis", "urology", 30),
    ("Blausen dental tooth anatomy", "anatomy", "oral", "dentistry", 30),
    ("Blausen neuron nerve anatomy", "anatomy", "nervous system", "neurology", 30),
    ("Blausen digestive system anatomy", "anatomy", "abdomen", "gastroenterology", 40),
    # X-ray radiographs
    ("chest X-ray radiograph", "xray", "chest", "radiology", 80),
    ("chest radiograph pneumonia", "xray", "chest", "pulmonology", 60),
    ("bone fracture X-ray radiograph", "xray", "extremity", "orthopedics", 60),
    ("spine X-ray radiograph", "xray", "spine", "orthopedics", 50),
    ("pelvis hip X-ray", "xray", "pelvis", "orthopedics", 40),
    ("dental X-ray panoramic", "xray", "oral", "dentistry", 30),
    ("hand wrist X-ray", "xray", "upper extremity", "orthopedics", 40),
    ("foot ankle X-ray", "xray", "lower extremity", "orthopedics", 30),
    ("skull X-ray cranium", "xray", "skull", "radiology", 30),
    ("knee X-ray", "xray", "knee", "orthopedics", 30),
    # CT scans
    ("CT scan brain head", "ct", "brain", "neurology", 50),
    ("CT scan chest lung", "ct", "chest", "radiology", 40),
    ("CT scan abdomen", "ct", "abdomen", "radiology", 40),
    ("CT scan spine", "ct", "spine", "radiology", 30),
    # MRI
    ("MRI brain", "mri", "brain", "neurology", 50),
    ("MRI spine", "mri", "spine", "neurosurgery", 40),
    ("MRI knee joint", "mri", "knee", "orthopedics", 40),
    ("MRI heart cardiac", "mri", "heart", "cardiology", 30),
    # Histology
    ("histology pathology cancer", "histology", "tissue", "pathology", 60),
    ("histology normal tissue", "histology", "tissue", "pathology", 60),
    ("histology stain microscopy", "histology", "tissue", "pathology", 60),
    # Ultrasound / Echo
    ("ultrasound sonography medical", "ultrasound", "abdomen", "radiology", 40),
    ("echocardiogram ultrasound heart", "ultrasound", "heart", "cardiology", 30),
    # Ophthalmology
    ("fundus retina eye", "fundoscopy", "eye", "ophthalmology", 40),
    ("slit lamp eye anterior segment", "fundoscopy", "eye", "ophthalmology", 30),
    # Dermatology
    ("skin lesion dermatology", "dermatoscopy", "skin", "dermatology", 50),
    ("dermatitis eczema skin rash", "dermatoscopy", "skin", "dermatology", 40),
    # ECG / Cardiology
    ("ECG electrocardiogram", "ecg", "heart", "cardiology", 30),
    # Endoscopy
    ("endoscopy gastroscopy", "endoscopy", "abdomen", "gastroenterology", 30),
    ("colonoscopy polyp", "endoscopy", "colon", "gastroenterology", 30),
    # Surgery / Anatomy
    ("surgical anatomy operative", "anatomy", "abdomen", "surgery", 40),
    ("laparoscopy surgical", "anatomy", "abdomen", "surgery", 30),
]


def clean_title(raw: str) -> str:
    t = raw.replace("File:", "").replace("_", " ")
    t = re.sub(r"\.(png|jpg|jpeg|svg|gif|webp)$", "", t, flags=re.I)
    t = re.sub(r"^Blausen\s+\d+\s*", "", t)
    t = re.sub(r"\s*-\s*[a-z]{2}(-[A-Z]{2})?$", "", t)  # remove locale suffixes
    t = re.sub(r"\s+", " ", t).strip()
    return t[:299] if t else raw[:60]


def strip_html(s: str) -> str:
    if not s:
        return ""
    s = unescape(s)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()[:800]


def fetch_page(query: str, offset: int, limit: int) -> list[dict]:
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": f"File: {query}",
        "gsrnamespace": 6,
        "gsrlimit": min(limit, 50),
        "gsroffset": offset,
        "prop": "imageinfo",
        "iiprop": "url|mime|extmetadata",
        "iiurlwidth": 800,
        "format": "json",
    }
    try:
        r = S.get(COMMONS_API, params=params, timeout=25)
        if r.status_code != 200:
            log.warning("HTTP %d for query=%r offset=%d", r.status_code, query, offset)
            return []
        return list(r.json().get("query", {}).get("pages", {}).values())
    except Exception as e:
        log.warning("Fetch error %r: %s", query, e)
        return []


def make_record(page: dict, modality: str, region: str, specialty: str, query: str) -> dict | None:
    ii = page.get("imageinfo", [{}])[0]
    url = ii.get("url", "")
    if not url:
        return None
    url_l = url.lower()
    mime = ii.get("mime", "")
    if not (any(url_l.endswith(ext) for ext in VALID_EXTS) or mime in VALID_MIMES):
        return None

    meta = ii.get("extmetadata", {})
    title = clean_title(page.get("title", ""))
    if not title or len(title) < 3:
        return None

    desc_raw = meta.get("ImageDescription", {}).get("value", "")
    desc = strip_html(desc_raw)
    if not desc or len(desc) < 10:
        desc = f"{modality.upper()} image: {title}. Category: {region}."

    license_val = (
        meta.get("LicenseShortName", {}).get("value")
        or meta.get("License", {}).get("value")
        or "CC BY-SA 3.0"
    )
    artist = strip_html(meta.get("Artist", {}).get("value", ""))
    if "Blausen" in url or "blausen" in url.lower():
        license_val = "CC BY 3.0"
        artist = "Blausen Medical Communications Inc."
    elif not artist:
        artist = "Wikimedia Commons contributors"

    filename = url.rsplit("/", 1)[-1]
    source_url = f"https://commons.wikimedia.org/wiki/File:{filename}"
    thumb = ii.get("thumburl") or url

    return {
        "title": title,
        "description": desc,
        "modality": modality,
        "anatomy_region": region,
        "specialty": specialty,
        "image_url": url,
        "thumbnail_url": thumb,
        "source_name": "Wikimedia Commons",
        "source_url": source_url,
        "license": license_val,
        "attribution": f"{artist} via Wikimedia Commons",
        "tags": json.dumps([modality, region, specialty] + query.split()[:2]),
    }


def main():
    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM medical_images WHERE is_user_upload=false")
    start = cur.fetchone()[0]
    log.info("=== Starting. Current images: %d ===", start)

    cur.execute("SELECT image_url FROM medical_images WHERE is_user_upload=false")
    existing = {row[0] for row in cur.fetchall()}
    log.info("Existing URLs loaded: %d", len(existing))

    total_added = 0

    for search_term, modality, region, specialty, limit in SEARCHES:
        log.info("[%s] query=%r limit=%d", modality.upper(), search_term, limit)
        added = 0
        offset = 0

        while offset < limit:
            pages = fetch_page(search_term, offset, min(50, limit - offset))
            if not pages:
                break

            for page in pages:
                rec = make_record(page, modality, region, specialty, search_term)
                if not rec:
                    continue
                url = rec["image_url"]
                if url in existing:
                    continue
                existing.add(url)

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
                        rec["title"], rec["description"], rec["modality"],
                        rec["anatomy_region"], rec["specialty"],
                        rec["image_url"], rec["thumbnail_url"],
                        rec["source_name"], rec["source_url"],
                        rec["license"], rec["attribution"], rec["tags"],
                    ))
                    added += 1
                    total_added += 1
                except Exception as e:
                    conn.rollback()
                    log.warning("Insert error: %s", e)
                    continue

            conn.commit()
            offset += 50
            time.sleep(0.4)

        log.info("  +%d images (total: %d)", added, total_added)

    # Final stats
    cur.execute("""
        SELECT modality, COUNT(*) FROM medical_images
        WHERE is_user_upload=false GROUP BY modality ORDER BY count DESC
    """)
    log.info("\n=== DONE. Total new: %d ===", total_added)
    for row in cur.fetchall():
        log.info("  %-15s %d", row[0], row[1])

    conn.close()


if __name__ == "__main__":
    main()
