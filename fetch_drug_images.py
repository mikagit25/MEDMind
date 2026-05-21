"""
Fetch drug images from Wikipedia and store in drugs.image_url.
Runs once to pre-populate, no external API key needed.

Usage:
    python3 fetch_drug_images.py              # all drugs without image
    python3 fetch_drug_images.py --force      # re-fetch all (overwrite)
    python3 fetch_drug_images.py --limit 50   # first N drugs
"""
import argparse
import logging
import time
import urllib.parse
import urllib.request
import json
import re
import sys
import os

import psycopg2

sys.path.insert(0, os.path.dirname(__file__))
from generate_articles_ollama import DB_URL

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def get_wiki_image(query: str, size: int = 400) -> str | None:
    """Fetch drug image from Wikipedia page images API."""
    encoded = urllib.parse.quote(query)
    url = (f"https://en.wikipedia.org/w/api.php?action=query"
           f"&titles={encoded}&prop=pageimages&format=json"
           f"&pithumbsize={size}&pilimit=1")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "MedMindAI/1.0 (info@medmind.pro)"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            if "thumbnail" in page:
                return page["thumbnail"]["source"]
    except Exception as e:
        log.debug("Wiki image error for '%s': %s", query, e)
    return None


def clean_name(name: str) -> str:
    """Strip salt forms and dosage info for cleaner Wikipedia search."""
    name = re.sub(r"\s+(hydrochloride|sulfate|sodium|potassium|besylate|maleate|"
                  r"acetate|phosphate|tartrate|citrate|hfa|er|sr|xr|ir)\b", "",
                  name, flags=re.IGNORECASE).strip()
    name = re.sub(r"\s+and\s+\w+", "", name, flags=re.IGNORECASE).strip()
    return name


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Re-fetch all, overwrite existing")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    conn = psycopg2.connect(DB_URL)
    with conn.cursor() as cur:
        if args.force:
            cur.execute("SELECT id, name, generic_name FROM drugs ORDER BY name")
        else:
            cur.execute("SELECT id, name, generic_name FROM drugs WHERE image_url IS NULL ORDER BY name")
        rows = cur.fetchall()

    if args.limit:
        rows = rows[:args.limit]

    log.info("Fetching images for %d drugs…", len(rows))
    found = skipped = 0

    for drug_id, name, generic_name in rows:
        # Try generic_name first (cleaner), then brand name
        candidates = []
        if generic_name and generic_name != name:
            candidates.append(clean_name(generic_name))
        candidates.append(clean_name(name))
        # Add bare active ingredient
        bare = clean_name(generic_name or name).split()[0]
        if bare not in candidates:
            candidates.append(bare)

        img_url = None
        for candidate in candidates:
            img_url = get_wiki_image(candidate)
            if img_url:
                break
            time.sleep(0.2)

        if img_url:
            with conn.cursor() as cur:
                cur.execute("UPDATE drugs SET image_url=%s WHERE id=%s", (img_url, drug_id))
            conn.commit()
            log.info("  ✓ %s → %s…", name[:40], img_url[:60])
            found += 1
        else:
            log.info("  – %s: no image", name[:40])
            skipped += 1

        time.sleep(0.3)  # respect Wikipedia rate limit

    conn.close()
    log.info("Done. Found: %d | No image: %d", found, skipped)


if __name__ == "__main__":
    main()
