#!/usr/bin/env python3
"""
Generate cover images for MedMind articles that lack them.

Uses Together.ai FLUX.1-schnell to create professional medical illustrations.
Images are saved to /app/data/media/articles/ and the DB is updated.

Usage:
  python3 scripts/generate_article_images.py                   # process 20 at a time (default)
  python3 scripts/generate_article_images.py --limit 50        # process 50
  python3 scripts/generate_article_images.py --category oncology  # specific category
  python3 scripts/generate_article_images.py --dry-run         # show prompts only, no generation
  python3 scripts/generate_article_images.py --slug some-slug  # single article
  python3 scripts/generate_article_images.py --overwrite       # regenerate even if image exists

API key:  /opt/kids_channel/credentials/together_api_key.txt
Model:    black-forest-labs/FLUX.1-schnell  (~$0.0003/image)
Output:   /app/data/media/articles/{slug}.jpg  → URL: /media/articles/{slug}.jpg
"""

import argparse
import asyncio
import base64
import hashlib
import os
import sys
import time
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text, update
from sqlalchemy.orm import Session

# ── Config ────────────────────────────────────────────────────────────────────

TOGETHER_KEY_FILE = Path("/opt/kids_channel/credentials/together_api_key.txt")
TOGETHER_URL      = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL    = "black-forest-labs/FLUX.1-schnell"

MEDIA_DIR         = Path("/app/data/media/articles")        # inside Docker container
DOCKER_VOL_DIR    = Path("/var/lib/docker/volumes/medmind_media_data/_data/articles")  # host → Docker volume
MEDIA_URL_PREFIX  = "/media/articles"

# When run on host, connect via exposed port 5432
# When run inside Docker, DATABASE_URL env var already has the right host
_raw_db_url = os.environ.get(
    "DATABASE_URL",
    "postgresql://medmind:medmind_secret@localhost:5432/medmind"
)
DATABASE_URL = _raw_db_url.replace("+asyncpg", "").replace("@postgres:", "@localhost:")

# ── Medical image style ───────────────────────────────────────────────────────

STYLE = (
    "clean professional medical illustration, "
    "photorealistic 3D render, soft blue and white clinical color palette, "
    "high detail, no text, no labels, no watermarks, "
    "modern healthcare aesthetics, 16:9 format"
)

# Category → visual concept override (when title alone isn't enough)
CATEGORY_CONTEXT: dict[str, str] = {
    "cardiology":             "human heart anatomy, cardiovascular system",
    "neurology":              "human brain neuroscience illustration",
    "pharmacology":           "pharmaceutical pills and molecular structures",
    "drug-reference":         "medication bottles laboratory glassware",
    "oncology":               "cancer cell immunotherapy research laboratory",
    "infectious-diseases":    "virus bacteria microscopy pathology",
    "infectious-specific":    "virus bacteria microscopy pathology",
    "surgery-procedures":     "surgical instruments operating room",
    "diagnostics":            "medical diagnostic equipment laboratory",
    "diagnostics-interpretation": "ECG MRI scan radiology reading",
    "procedures":             "medical procedure clinical equipment",
    "ob-gyn":                 "obstetrics gynecology anatomy",
    "pediatrics":             "pediatric medicine children healthcare",
    "endocrinology":          "endocrine glands hormone system anatomy",
    "symptoms":               "human body clinical symptoms anatomy",
    "psychiatry":             "mental health brain psychology illustration",
    "pulmonology":            "lungs respiratory system anatomy",
    "gastroenterology":       "gastrointestinal tract digestive system",
    "nephrology":             "kidney renal anatomy urinary system",
    "rheumatology":           "joints arthritis musculoskeletal system",
    "hematology":             "blood cells hematology microscopy",
    "dermatology":            "skin dermatology cross-section anatomy",
    "ophthalmology":          "eye anatomy ophthalmology retina",
    "orthopedics":            "bone joint orthopedic anatomy",
    "emergency":              "emergency medicine critical care",
    "veterinary":             "veterinary medicine animal anatomy",
    "immunology":             "immune system cells antibody illustration",
    "genetics":               "DNA helix genetics chromosome",
    "pathology":              "pathology tissue microscopy slide",
}


def build_prompt(title: str, category: str, excerpt: str) -> str:
    """Build a FLUX-optimised image generation prompt for a medical article."""
    cat_context = CATEGORY_CONTEXT.get(category, "medical healthcare clinical")

    # Extract key topic from title (first 8 words max)
    words = title.split()[:8]
    short_title = " ".join(words)

    prompt = (
        f"{short_title}, {cat_context}, "
        f"{STYLE}"
    )
    return prompt


# ── Together.ai ───────────────────────────────────────────────────────────────

def load_key() -> str:
    if TOGETHER_KEY_FILE.exists():
        return TOGETHER_KEY_FILE.read_text().strip()
    key = os.environ.get("TOGETHER_API_KEY", "")
    if key:
        return key
    sys.exit(f"Together.ai key not found at {TOGETHER_KEY_FILE}\n"
             "Set TOGETHER_API_KEY env var or place key in that file.")


def generate_image(prompt: str, key: str) -> bytes | None:
    """Call Together.ai and return raw JPEG bytes, or None on failure."""
    try:
        r = httpx.post(
            TOGETHER_URL,
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": TOGETHER_MODEL,
                "prompt": prompt,
                "width": 1280,
                "height": 720,
                "steps": 4,
                "n": 1,
            },
            timeout=90,
        )
        if r.status_code != 200:
            try:
                msg = r.json().get("error", {}).get("message", r.text[:120])
            except Exception:
                msg = r.text[:120]
            print(f"    ✗ Together error {r.status_code}: {msg}")
            return None

        item = r.json()["data"][0]
        b64 = item.get("b64_json")
        if b64:
            return base64.b64decode(b64)
        url = item.get("url")
        if url:
            img_r = httpx.get(url, timeout=30)
            if img_r.status_code == 200:
                return img_r.content

    except Exception as e:
        print(f"    ✗ Request failed: {e}")
    return None


# ── DB helpers ────────────────────────────────────────────────────────────────

def get_articles(
    session: Session,
    limit: int,
    category: str | None,
    slug: str | None,
    overwrite: bool,
) -> list[dict]:
    filters = ["is_published = true"]
    params: dict = {}

    if not overwrite:
        filters.append("cover_image IS NULL")
    if category:
        filters.append("category = :category")
        params["category"] = category
    if slug:
        filters.append("slug = :slug")
        params["slug"] = slug

    where = " AND ".join(filters)
    rows = session.execute(
        text(f"SELECT id, slug, title, category, excerpt FROM articles WHERE {where} ORDER BY RANDOM() LIMIT :limit"),
        {**params, "limit": limit},
    ).fetchall()
    return [dict(r._mapping) for r in rows]


def save_cover_image(session: Session, article_id: str, image_url: str) -> None:
    session.execute(
        text("UPDATE articles SET cover_image = :url WHERE id = :id"),
        {"url": image_url, "id": article_id},
    )
    session.commit()


# ── Main ──────────────────────────────────────────────────────────────────────

def resolve_media_dir() -> Path:
    """Find the actual media directory — works both inside Docker and on host."""
    # Priority 1: Docker volume on host (script typically runs on host)
    if DOCKER_VOL_DIR.parent.exists():
        DOCKER_VOL_DIR.mkdir(parents=True, exist_ok=True)
        return DOCKER_VOL_DIR
    # Priority 2: Docker-internal path (when script runs inside container)
    if MEDIA_DIR.parent.exists():
        MEDIA_DIR.mkdir(parents=True, exist_ok=True)
        return MEDIA_DIR
    # Last resort: local ./data/media/articles
    fallback = Path("./data/media/articles")
    fallback.mkdir(parents=True, exist_ok=True)
    print(f"WARNING: saving to local {fallback} — images won't be served by backend!")
    return fallback


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate cover images for MedMind articles")
    parser.add_argument("--limit",     type=int,  default=20,   help="Max articles to process (default 20)")
    parser.add_argument("--category",  type=str,  default=None, help="Filter by category slug")
    parser.add_argument("--slug",      type=str,  default=None, help="Process a single article by slug")
    parser.add_argument("--dry-run",   action="store_true",     help="Print prompts only, no generation")
    parser.add_argument("--overwrite", action="store_true",     help="Regenerate even if image exists")
    parser.add_argument("--delay",     type=float, default=1.5, help="Seconds between requests (default 1.5)")
    args = parser.parse_args()

    key = load_key()
    media_dir = resolve_media_dir()
    engine = create_engine(DATABASE_URL)

    with Session(engine) as session:
        articles = get_articles(session, args.limit, args.category, args.slug, args.overwrite)

    if not articles:
        print("✓ No articles found needing images.")
        return

    print(f"Found {len(articles)} articles to process\n")

    success = 0
    skipped = 0
    failed  = 0

    with Session(engine) as session:
        for i, art in enumerate(articles, 1):
            slug     = art["slug"]
            title    = art["title"]
            category = art["category"]
            excerpt  = art["excerpt"] or ""

            prompt = build_prompt(title, category, excerpt)

            print(f"[{i}/{len(articles)}] {title[:70]}")
            print(f"  category: {category}")
            print(f"  prompt:   {prompt[:100]}…")

            if args.dry_run:
                print("  [dry-run] skipping generation\n")
                skipped += 1
                continue

            # Check if file already exists
            out_file = media_dir / f"{slug}.jpg"
            if out_file.exists() and not args.overwrite:
                image_url = f"{MEDIA_URL_PREFIX}/{slug}.jpg"
                save_cover_image(session, art["id"], image_url)
                print(f"  ✓ File already exists → DB updated: {image_url}\n")
                success += 1
                continue

            img_bytes = generate_image(prompt, key)
            if img_bytes is None:
                print("  ✗ Generation failed, skipping\n")
                failed += 1
            else:
                out_file.write_bytes(img_bytes)
                image_url = f"{MEDIA_URL_PREFIX}/{slug}.jpg"
                save_cover_image(session, art["id"], image_url)
                size_kb = len(img_bytes) // 1024
                print(f"  ✓ Saved {size_kb} KB → {image_url}\n")
                success += 1

            if i < len(articles):
                time.sleep(args.delay)

    print("─" * 60)
    print(f"Done: {success} generated, {skipped} skipped (dry-run), {failed} failed")
    if failed:
        print(f"Tip: re-run to retry failed articles (they still have no cover_image in DB)")


if __name__ == "__main__":
    main()
