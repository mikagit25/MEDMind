"""
MedMind — Wikipedia/Commons image fetcher for articles.

Fetches a relevant medical image from Wikipedia's free API.
No API key required. Images are CC-BY-SA or Public Domain.

Usage:
    from fetch_article_image import fetch_cover_image
    url = fetch_cover_image("Psoriasis pathophysiology", "diseases")

    # Batch for all articles:
    python3 fetch_article_image.py --all --limit 100
    python3 fetch_article_image.py --slug "psoriasis-pathophysiology..."
"""
from __future__ import annotations

import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path

import psycopg2

DB_URL = "postgresql://medmind:medmind_secret@localhost:5432/medmind"
UA     = "MedMindAI/1.0 (https://medmind.pro; 33mikalai@gmail.com)"

# Medical search terms per category to improve relevance
CATEGORY_HINTS: dict[str, str] = {
    "cardiology":          "heart disease cardiology",
    "neurology":           "neurology brain",
    "pharmacology":        "medicine pharmacy",
    "drugs":               "medication drugs",
    "diseases":            "disease pathology",
    "symptoms":            "medical symptom",
    "emergency":           "emergency medicine",
    "surgery":             "surgery operation",
    "oncology":            "cancer oncology",
    "psychiatry":          "mental health psychiatry",
    "endocrinology":       "endocrine system hormone",
    "infectious-diseases": "infectious disease pathogen",
    "pediatrics":          "pediatrics child medicine",
    "nutrition":           "nutrition food health",
    "orthopedics":         "orthopedics bone joint",
    "dermatology":         "dermatology skin",
    "ophthalmology":       "ophthalmology eye",
    "pulmonology":         "lung respiratory",
    "nephrology":          "kidney renal",
    "rheumatology":        "arthritis rheumatology",
    "hematology":          "blood hematology",
    "geriatrics":          "geriatrics aging",
    "urology":             "urology urinary",
    "ob-gyn":              "obstetrics gynecology",
    "internal-medicine":   "internal medicine",
    "diagnostics":         "medical diagnosis laboratory",
    "procedures":          "medical procedure clinical",
    "ent":                 "ear nose throat ENT",
    "veterinary":          "veterinary animal medicine",
}


def _wp_api(params: dict) -> dict:
    """Call Wikipedia API. Returns JSON dict."""
    base   = "https://en.wikipedia.org/w/api.php"
    params = {"format": "json", **params}
    url    = base + "?" + urllib.parse.urlencode(params)
    req    = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


def _fetch_page_thumbnail(query: str, min_width: int = 400) -> str | None:
    """Try Wikipedia pageimages for a given search query."""
    try:
        data = _wp_api({
            "action":      "query",
            "titles":      query,
            "prop":        "pageimages",
            "pithumbsize": 1200,
            "pilicense":   "any",
        })
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            thumb = page.get("thumbnail", {})
            src   = thumb.get("source", "")
            w     = thumb.get("width", 0)
            if src and w >= min_width:
                return src
    except Exception:
        pass
    return None


def _search_commons(query: str, min_width: int = 400) -> str | None:
    """Search Wikimedia Commons for relevant images."""
    try:
        data = _wp_api({
            "action":       "query",
            "generator":    "search",
            "gsrsearch":    f"filetype:bitmap {query}",
            "gsrnamespace": 6,
            "gsrlimit":     8,
            "prop":         "imageinfo",
            "iiprop":       "url|mime|width|height",
            "origin":       "*",
        })
        pages = list(data.get("query", {}).get("pages", {}).values())
        # Sort by width descending (prefer larger images)
        pages.sort(key=lambda p: p.get("imageinfo", [{}])[0].get("width", 0), reverse=True)
        for page in pages:
            info = (page.get("imageinfo") or [{}])[0]
            url  = info.get("url", "")
            mime = info.get("mime", "")
            w    = info.get("width", 0)
            if url and mime.startswith("image/") and "svg" not in mime and w >= min_width:
                return url
    except Exception:
        pass
    return None


def fetch_cover_image(title: str, category: str = "") -> str | None:
    """
    Fetch a relevant medical image URL from Wikipedia/Commons.
    Returns a URL string or None if not found.

    Strategy:
    1. Try exact title lookup on Wikipedia → pageimages
    2. Extract main medical term from title and retry
    3. Search Commons with category hint + title keywords
    """
    # Clean title for Wikipedia search
    clean = (title
             .replace(":", " ")
             .replace("-", " ")
             .replace("  ", " ")
             .strip())

    # Remove common generic suffixes
    for suffix in ["pathophysiology", "clinical presentation", "evidence-based",
                   "management", "treatment", "diagnosis", "overview", "review",
                   "causes", "workup", "types"]:
        clean = clean.lower().replace(suffix, "").strip()

    # Capitalize properly
    clean = " ".join(w.capitalize() for w in clean.split() if len(w) > 2)
    clean = clean[:60].strip()

    hint = CATEGORY_HINTS.get(category, "medicine medical")

    # Strategy 1: Direct title
    url = _fetch_page_thumbnail(clean)
    if url:
        return url
    time.sleep(0.3)

    # Strategy 2: Category hint + main term
    if clean:
        url = _search_commons(f"{clean} {hint} medicine", min_width=300)
        if url:
            return url
        time.sleep(0.3)

    # Strategy 3: Category-level fallback
    url = _fetch_page_thumbnail(hint.split()[0])
    if url:
        return url

    return None


def update_article_cover(conn, article_id: str, cover_url: str) -> None:
    """Save cover_image URL to the articles table."""
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE articles SET cover_image = %s WHERE id = %s",
            (cover_url, str(article_id))
        )
    conn.commit()


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Fetch cover images for articles from Wikipedia")
    parser.add_argument("--all",      action="store_true", help="Process all articles missing cover_image")
    parser.add_argument("--force",    action="store_true", help="Re-fetch even if cover_image exists")
    parser.add_argument("--slug",     type=str, default=None)
    parser.add_argument("--limit",    type=int, default=200)
    parser.add_argument("--category", type=str, default=None)
    args = parser.parse_args()

    conn = psycopg2.connect(DB_URL)

    with conn.cursor() as cur:
        if args.slug:
            cur.execute("SELECT id, title, category FROM articles WHERE slug = %s", (args.slug,))
        elif args.force:
            q = "SELECT id, title, category FROM articles WHERE is_published=true"
            params: list = []
            if args.category:
                q += " AND category=%s"; params.append(args.category)
            q += " ORDER BY view_count DESC LIMIT %s"; params.append(args.limit)
            cur.execute(q, params)
        else:
            q = "SELECT id, title, category FROM articles WHERE is_published=true AND (cover_image IS NULL OR cover_image='')"
            params = []
            if args.category:
                q += " AND category=%s"; params.append(args.category)
            q += " ORDER BY view_count DESC, created_at DESC LIMIT %s"; params.append(args.limit)
            cur.execute(q, params)
        rows = cur.fetchall()

    print(f"Articles to process: {len(rows)}")
    done = 0
    skipped = 0

    for article_id, title, category in rows:
        print(f"  [{done+skipped+1}/{len(rows)}] {title[:60]}", end=" ... ", flush=True)
        url = fetch_cover_image(title, category)
        if url:
            update_article_cover(conn, str(article_id), url)
            print(f"✓ {url[:60]}")
            done += 1
        else:
            print("– no image found")
            skipped += 1
        time.sleep(0.5)   # be polite to Wikipedia

    conn.close()
    print(f"\nDone: {done} images found, {skipped} skipped")


if __name__ == "__main__":
    main()
