"""
Regenerate cover images for existing veterinary articles using Pexels curated queries.
Replaces Together.ai 3D renders and blank images with real animal photography.

Usage:
    python -m app.scripts.regen_vet_images [--dry-run] [--limit N] [--species dog]
"""
import argparse
import asyncio
import json
import logging
import time
import urllib.parse
import urllib.request

from sqlalchemy import select, update

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.models import Article

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

APP_UA = "MedMindBot/1.0"
MEDIA_URL_BASE = "/media/articles"

# ─── Curated Pexels queries per species ──────────────────────────────────────

SPECIES_PEXELS_QUERIES: dict[str, list[str]] = {
    "dog":     ["golden retriever dog outdoors", "labrador dog portrait", "dog nature sunny", "german shepherd dog"],
    "cat":     ["cat portrait natural light", "tabby cat indoor", "domestic cat window", "fluffy cat close-up"],
    "horse":   ["horse green field", "horse portrait sunset", "bay horse outdoors", "horse countryside"],
    "cattle":  ["dairy cow farm field", "cattle farm countryside", "cow pasture green"],
    "rabbit":  ["rabbit pet portrait", "bunny rabbit close-up", "white rabbit nature"],
    "bird":    ["parrot colorful portrait", "cockatiel pet bird", "macaw tropical bird"],
    "reptile": ["bearded dragon lizard", "gecko reptile portrait", "iguana green closeup"],
}

# Keywords to detect species from article slug/title
SPECIES_DETECT: dict[str, list[str]] = {
    "dog":     ["dog", "canine", "puppy", "parvovirus", "heartworm", "dachshund", "distemper"],
    "cat":     ["cat", "feline", "kitten"],
    "horse":   ["horse", "equine", "laminitis", "colic", "foal"],
    "cattle":  ["cattle", "bovine", "cow", "mastitis", "bvd"],
    "rabbit":  ["rabbit"],
    "bird":    ["bird", "parrot", "avian", "psittac"],
    "reptile": ["reptile", "bearded", "gecko", "lizard"],
}


def detect_species(slug: str) -> str:
    """Detect the primary species from article slug keywords."""
    slug_lower = slug.lower()
    for sp, keywords in SPECIES_DETECT.items():
        for kw in keywords:
            if kw in slug_lower:
                return sp
    return "dog"  # fallback


def _pexels_fetch(query: str, key: str) -> str | None:
    url = "https://api.pexels.com/v1/search?" + urllib.parse.urlencode(
        {"query": query, "per_page": 5, "orientation": "landscape"}
    )
    req = urllib.request.Request(url, headers={"Authorization": key, "User-Agent": APP_UA})
    with urllib.request.urlopen(req, timeout=12) as r:
        data = json.loads(r.read())
    photos = data.get("photos", [])
    if photos:
        return photos[0]["src"].get("large2x") or photos[0]["src"].get("original")
    return None


def fetch_pexels_image(species: str, slug: str) -> str | None:
    """Fetch a curated Pexels photo, rotating variant based on slug hash."""
    key = settings.PEXELS_API_KEY
    if not key:
        log.error("PEXELS_API_KEY not set")
        return None

    queries = SPECIES_PEXELS_QUERIES.get(species, [f"{species} animal portrait"])
    idx   = hash(slug) % len(queries)
    order = queries[idx:] + queries[:idx]

    for query in order:
        try:
            result = _pexels_fetch(query, key)
            if result:
                log.info("  Pexels ('%s'): %s", query, result[:80])
                return result
            time.sleep(0.3)
        except Exception as e:
            log.warning("  Pexels error for '%s': %s", query, e)
            time.sleep(1)

    return None


async def regen_images(dry_run: bool, limit: int, species_filter: str | None) -> None:
    async with AsyncSessionLocal() as session:
        stmt = select(Article.id, Article.slug, Article.cover_image).where(
            Article.category == "veterinary"
        )
        result = await session.execute(stmt)
        rows = result.all()

    log.info("Found %d veterinary articles", len(rows))

    updated = 0
    skipped = 0
    failed  = 0

    for art_id, slug, cover_image in rows:
        if updated >= limit:
            break

        species = detect_species(slug)

        if species_filter and species != species_filter:
            continue

        # Only replace Together.ai generated images (stored locally) or blank images.
        # Pexels images are https:// URLs and are already good — skip them.
        is_pexels = cover_image and cover_image.startswith("https://images.pexels.com")
        if is_pexels:
            skipped += 1
            continue

        log.info("[%d] %s  (species=%s, current=%s)", updated + 1, slug, species,
                 (cover_image or "none")[:60])

        new_url = fetch_pexels_image(species, slug)
        if not new_url:
            log.warning("  No Pexels result — keeping existing cover")
            failed += 1
            continue

        if dry_run:
            log.info("  [DRY RUN] would set: %s", new_url[:80])
        else:
            async with AsyncSessionLocal() as session:
                await session.execute(
                    update(Article).where(Article.id == art_id).values(cover_image=new_url)
                )
                await session.commit()
            log.info("  Updated ✓")

        updated += 1
        time.sleep(0.5)  # respect Pexels rate limit

    log.info("Done. Updated=%d  Skipped(already Pexels)=%d  Failed=%d", updated, skipped, failed)


def main() -> None:
    parser = argparse.ArgumentParser(description="Regenerate vet article cover images from Pexels")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without saving")
    parser.add_argument("--limit", type=int, default=200, help="Max articles to process")
    parser.add_argument("--species", type=str, default=None,
                        help="Only process articles for this species (dog/cat/horse/...)")
    args = parser.parse_args()

    asyncio.run(regen_images(args.dry_run, args.limit, args.species))


if __name__ == "__main__":
    main()
