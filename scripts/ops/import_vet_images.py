#!/usr/bin/env python3
"""Veterinary anatomy image importer — Wikimedia Commons.

Sources:
  1. Ruth Lawson "Anatomy and Physiology of Animals" — CC BY-SA (WikiBooks)
  2. Sisson & Grossman "Anatomy of Domestic Animals" (1914) — Public Domain
  3. BHL "Anatomical technology applied to domestic cat" — Public Domain
  4. Comparative anatomy textbooks — Public Domain
  5. Veterinary radiology / pathology categories

Run from HOST:
  nohup python3 /opt/medmind/import_vet_images.py > /tmp/vet_images.log 2>&1 &
  tail -f /tmp/vet_images.log
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

DB_DSN = "host=172.18.0.2 port=5432 dbname=medmind user=medmind password=medmind_secret"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
LOG = "/tmp/vet_images.log"
VALID_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp"}
VALID_MIMES = {"image/jpeg", "image/png", "image/svg+xml", "image/gif", "image/webp"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(LOG, mode="w")],
)
log = logging.getLogger()

S = requests.Session()
S.headers["User-Agent"] = "MedMind-Educational/3.0 (https://medmind.pro; medmind.edu.bot@gmail.com)"

# (search_term, modality, anatomy_region, species_tags, limit)
# species_tags: list of species this applies to
SEARCHES = [
    # ── Ruth Lawson "Anatomy and Physiology of Animals" (CC BY-SA) ─────────────
    ("anatomy physiology animals Ruth Lawson blood circulatory", "anatomy", "cardiovascular", ["dog", "cat", "horse", "cattle"], 50),
    ("anatomy physiology animals Ruth Lawson digestive system", "anatomy", "digestive", ["dog", "cat", "horse", "cattle"], 50),
    ("anatomy physiology animals Ruth Lawson nervous brain", "anatomy", "nervous system", ["dog", "cat", "horse", "cattle"], 50),
    ("anatomy physiology animals Ruth Lawson reproductive", "anatomy", "reproductive", ["dog", "cat", "horse", "cattle"], 50),
    ("anatomy physiology animals Ruth Lawson muscle skeleton", "anatomy", "musculoskeletal", ["dog", "cat", "horse", "cattle"], 50),
    ("anatomy physiology animals Ruth Lawson kidney urinary", "anatomy", "urinary", ["dog", "cat", "horse", "cattle"], 50),
    ("anatomy physiology animals Ruth Lawson respiratory lung", "anatomy", "respiratory", ["dog", "cat", "horse", "cattle"], 50),
    ("anatomy physiology animals Ruth Lawson skin coat", "anatomy", "integument", ["dog", "cat", "horse", "cattle"], 50),
    ("anatomy physiology animals Ruth Lawson endocrine gland", "anatomy", "endocrine", ["dog", "cat", "horse", "cattle"], 50),
    ("anatomy physiology animals Ruth Lawson eye ear sense", "anatomy", "sensory", ["dog", "cat", "horse", "cattle"], 50),
    ("anatomy physiology animals Ruth Lawson cell tissue", "histology", "tissue", ["general"], 50),
    ("anatomy physiology animals Ruth Lawson", "anatomy", "general", ["dog", "cat", "horse", "cattle"], 50),

    # ── Sisson & Grossman "Anatomy of Domestic Animals" 1914 PD ────────────────
    ("Sisson anatomy domestic animals 1914", "anatomy", "general", ["dog", "cat", "horse", "cattle", "pig"], 50),
    ("anatomy domestic animals Sisson", "anatomy", "musculoskeletal", ["horse", "cattle", "dog", "pig"], 50),

    # ── "Anatomical Technology" — Domestic Cat (BHL, PD) ───────────────────────
    ("anatomical technology domestic cat Straus", "anatomy", "general", ["cat"], 50),
    ("anatomy cat feline BHL Mivart", "anatomy", "general", ["cat"], 50),

    # ── Comparative anatomy (PD textbooks) ────────────────────────────────────
    ("comparative anatomy vertebrates Parker", "anatomy", "comparative", ["general"], 50),
    ("comparative anatomy vertebrates 1907", "anatomy", "comparative", ["general"], 50),
    ("On the anatomy of vertebrates Owen", "anatomy", "comparative", ["general"], 50),

    # ── Species-specific anatomy searches ─────────────────────────────────────
    ("equine horse anatomy musculoskeletal", "anatomy", "musculoskeletal", ["horse"], 40),
    ("equine forelimb hindlimb anatomy", "anatomy", "musculoskeletal", ["horse"], 30),
    ("equine hoof anatomy", "anatomy", "musculoskeletal", ["horse"], 20),
    ("equine digestive hindgut anatomy", "anatomy", "digestive", ["horse"], 20),
    ("canine dog anatomy organ system", "anatomy", "general", ["dog"], 40),
    ("canine olfactory brain dog anatomy", "anatomy", "nervous system", ["dog"], 20),
    ("feline cat anatomy organ system", "anatomy", "general", ["cat"], 40),
    ("rabbit anatomy cecum digestive", "anatomy", "digestive", ["rabbit"], 20),
    ("rabbit anatomy organ", "anatomy", "general", ["rabbit"], 30),
    ("avian bird anatomy internal organ", "anatomy", "general", ["bird", "parrot", "chicken"], 30),
    ("bovine cattle anatomy internal organ", "anatomy", "general", ["cattle", "cow"], 30),
    ("swine pig porcine anatomy organ", "anatomy", "general", ["pig"], 20),

    # ── Veterinary radiology ───────────────────────────────────────────────────
    ("veterinary radiology dog xray", "xray", "general", ["dog"], 40),
    ("veterinary radiology cat xray", "xray", "general", ["cat"], 30),
    ("veterinary radiology horse", "xray", "musculoskeletal", ["horse"], 30),
    ("veterinary radiograph thorax abdomen", "xray", "thorax", ["dog", "cat"], 30),
    ("animal xray fracture orthopedic", "xray", "musculoskeletal", ["dog", "cat"], 30),
    ("veterinary radiograph spine", "xray", "spine", ["dog", "cat"], 20),
    ("equine hoof radiograph", "xray", "musculoskeletal", ["horse"], 20),
    ("small animal dental xray", "xray", "oral", ["dog", "cat"], 20),

    # ── Veterinary histology / pathology ──────────────────────────────────────
    ("dog histopathology pathology tissue", "histology", "tissue", ["dog"], 30),
    ("cat histopathology pathology tissue", "histology", "tissue", ["cat"], 20),
    ("veterinary histopathology microscopy", "histology", "tissue", ["general"], 30),
    ("canine mast cell tumor histology", "histology", "tissue", ["dog"], 20),
    ("feline lymphoma histology", "histology", "tissue", ["cat"], 15),
    ("animal parasite pathology microscopy", "histology", "tissue", ["general"], 20),

    # ── Veterinary ophthalmology / dermatology ─────────────────────────────────
    ("dog eye fundus retina ophthalmology", "fundoscopy", "eye", ["dog"], 20),
    ("cat eye cornea veterinary ophthalmology", "fundoscopy", "eye", ["cat"], 15),
    ("dog skin dermatitis veterinary", "dermatoscopy", "skin", ["dog"], 20),
    ("cat skin lesion veterinary dermatology", "dermatoscopy", "skin", ["cat"], 15),
    ("animal mange mite skin microscopy", "dermatoscopy", "skin", ["dog", "cat"], 20),

    # ── Veterinary ultrasound ─────────────────────────────────────────────────
    ("veterinary ultrasound dog cat", "ultrasound", "abdomen", ["dog", "cat"], 30),
    ("equine ultrasound horse", "ultrasound", "general", ["horse"], 20),

    # ── Exotic animals ────────────────────────────────────────────────────────
    ("reptile lizard anatomy organ", "anatomy", "general", ["reptile", "lizard", "snake"], 30),
    ("snake anatomy internal organ", "anatomy", "general", ["snake", "reptile"], 20),
    ("guinea pig anatomy organ", "anatomy", "general", ["guinea pig"], 20),
    ("ferret anatomy organ", "anatomy", "general", ["ferret"], 15),
    ("hedgehog anatomy organ", "anatomy", "general", ["hedgehog"], 10),

    # ── Parasitology ──────────────────────────────────────────────────────────
    ("animal parasite helminth worm", "histology", "parasite", ["general"], 30),
    ("canine heartworm Dirofilaria", "histology", "cardiovascular", ["dog"], 15),
    ("Toxoplasma cyst tissue", "histology", "parasite", ["cat", "general"], 15),
    ("tick mite ectoparasite animal", "dermatoscopy", "skin", ["general"], 20),
]


def clean_title(raw: str) -> str:
    t = raw.replace("File:", "").replace("_", " ")
    t = re.sub(r"\.(png|jpg|jpeg|svg|gif|webp)$", "", t, flags=re.I)
    t = re.sub(r"^(Image from page \d+ of |Image from page \d+)", "", t)
    t = re.sub(r"\([\d]{13}\)", "", t)   # BHL numeric IDs
    t = re.sub(r"\s+-\s+(ru|de|fr|es|tr|ar)$", "", t)
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
            log.warning("HTTP %d for %r offset=%d", r.status_code, query, offset)
            return []
        return list(r.json().get("query", {}).get("pages", {}).values())
    except Exception as e:
        log.warning("Fetch error %r: %s", query, e)
        return []


def make_record(page: dict, modality: str, region: str, species_tags: list, query: str) -> dict | None:
    ii = page.get("imageinfo", [{}])[0]
    url = ii.get("url", "")
    if not url:
        return None
    url_l = url.lower().split("?")[0]
    mime = ii.get("mime", "")
    if not (any(url_l.endswith(ext) for ext in VALID_EXTS) or mime in VALID_MIMES):
        return None

    meta = ii.get("extmetadata", {})
    title = clean_title(page.get("title", ""))
    if not title or len(title) < 5:
        return None

    desc_raw = meta.get("ImageDescription", {}).get("value", "")
    desc = strip_html(desc_raw)
    if not desc or len(desc) < 15:
        desc = f"Veterinary {modality} image: {title}. Region: {region}."

    license_val = (
        meta.get("LicenseShortName", {}).get("value")
        or meta.get("License", {}).get("value")
        or "Public Domain"
    )
    artist = strip_html(meta.get("Artist", {}).get("value", ""))
    if "Ruth Lawson" in url or "Lawson" in title:
        license_val = "CC BY-SA 3.0"
        artist = "Ruth Lawson (WikiBooks)"
    elif "Sisson" in title or "domestic animals" in url.lower():
        license_val = "Public Domain"
        artist = "Septimus Sisson (1914)"
    elif not artist:
        artist = "Wikimedia Commons contributors"

    filename = url.rsplit("/", 1)[-1]
    source_url = f"https://commons.wikimedia.org/wiki/File:{filename}"
    thumb = ii.get("thumburl") or url

    tags = list({modality, region, "veterinary"} | set(species_tags) | set(query.split()[:3]))

    return {
        "title": title,
        "description": desc,
        "modality": modality,
        "anatomy_region": region,
        "specialty": "veterinary",
        "image_url": url,
        "thumbnail_url": thumb,
        "source_name": "Wikimedia Commons",
        "source_url": source_url,
        "license": license_val,
        "attribution": f"{artist} via Wikimedia Commons",
        "tags": json.dumps(tags),
    }


def main():
    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM medical_images WHERE specialty='veterinary'")
    start = cur.fetchone()[0]
    log.info("=== Veterinary Image Importer ===")
    log.info("Existing vet images: %d", start)

    cur.execute("SELECT image_url FROM medical_images WHERE specialty='veterinary'")
    existing = {row[0] for row in cur.fetchall()}

    total_added = 0

    for i, (search_term, modality, region, species_tags, limit) in enumerate(SEARCHES, 1):
        log.info("[%d/%d] %s → %s/%s | limit=%d", i, len(SEARCHES), search_term[:50], modality, region, limit)
        added = 0
        offset = 0

        while offset < limit:
            pages = fetch_page(search_term, offset, min(50, limit - offset))
            if not pages:
                break

            for page in pages:
                rec = make_record(page, modality, region, species_tags, search_term)
                if not rec or rec["image_url"] in existing:
                    continue
                existing.add(rec["image_url"])

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

    cur.execute("""
        SELECT anatomy_region, COUNT(*) FROM medical_images
        WHERE specialty='veterinary' GROUP BY anatomy_region ORDER BY count DESC
    """)
    log.info("\n=== DONE. Total new: %d ===", total_added)
    log.info("Final vet images in DB: %d", start + total_added)
    for row in cur.fetchall():
        log.info("  %-25s %d", row[0], row[1])

    conn.close()


if __name__ == "__main__":
    main()
