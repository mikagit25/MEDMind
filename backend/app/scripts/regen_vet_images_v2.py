"""
Assign unique Pexels photos to all veterinary articles.

Strategy:
  - For each species, build a large photo pool from multiple Pexels queries
    (up to MAX_POOL photos per species, fetching per_page=80 per query).
  - Articles are sorted by slug (deterministic) and each gets a unique index
    into the pool. If pool runs out it wraps, but with 400+ photos per species
    the chance of a repeat is very low for our 192 articles.
  - Only articles that ALREADY have a Pexels image are re-assigned; articles
    with no image also get one.

Usage:
    python -m app.scripts.regen_vet_images_v2 [--dry-run] [--species dog]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from typing import Optional

from sqlalchemy import select, update

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.models import Article

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

APP_UA = "MedMindBot/1.0"

# ── Species detection (from slug keywords) ────────────────────────────────────

SPECIES_DETECT: dict[str, list[str]] = {
    "dog":     ["dog", "canine", "puppy", "parvovirus", "heartworm", "dachshund", "distemper", "labrador", "retriever", "shepherd"],
    "cat":     ["cat", "feline", "kitten"],
    "horse":   ["horse", "equine", "laminitis", "colic", "foal"],
    "cattle":  ["cattle", "bovine", "cow", "mastitis", "bvd"],
    "rabbit":  ["rabbit"],
    "bird":    ["bird", "parrot", "avian", "psittac", "cockatiel"],
    "reptile": ["reptile", "bearded", "gecko", "lizard", "iguana"],
}

def detect_species(slug: str) -> str:
    s = slug.lower()
    for sp, kws in SPECIES_DETECT.items():
        for kw in kws:
            if kw in s:
                return sp
    return "dog"

# ── Pexels queries — multiple per species for variety ────────────────────────

# Each list entry → one Pexels search. We fetch per_page=80 for each entry
# so 6 entries = up to 480 unique photos per species.
SPECIES_QUERIES: dict[str, list[str]] = {
    "dog": [
        "golden retriever dog",
        "labrador dog portrait",
        "german shepherd dog",
        "border collie dog",
        "bulldog cute",
        "husky dog nature",
        "beagle puppy",
        "poodle dog",
    ],
    "cat": [
        "cat portrait natural light",
        "tabby cat close-up",
        "domestic cat window",
        "fluffy cat indoor",
        "kitten cute",
        "orange cat sunlight",
        "black cat portrait",
        "siamese cat",
    ],
    "horse": [
        "horse green field",
        "horse portrait sunset",
        "bay horse galloping",
        "white horse meadow",
        "black horse nature",
        "horse riding countryside",
    ],
    "cattle": [
        "dairy cow farm",
        "cattle field green",
        "cow pasture sunny",
        "black and white cow",
        "herd cattle countryside",
    ],
    "rabbit": [
        "rabbit pet portrait",
        "bunny rabbit close-up",
        "white rabbit grass",
        "fluffy rabbit indoor",
        "rabbit nature",
    ],
    "bird": [
        "parrot colorful portrait",
        "cockatiel pet bird",
        "macaw tropical bird",
        "budgerigar parakeet",
        "bird colorful feathers",
    ],
    "reptile": [
        "bearded dragon lizard",
        "gecko reptile portrait",
        "iguana green close-up",
        "chameleon colorful",
        "python snake",
    ],
}


# ── Pexels fetcher ────────────────────────────────────────────────────────────

def _fetch_pexels_page(query: str, key: str, page: int = 1, per_page: int = 80) -> list[str]:
    """Fetch one page of Pexels results; return list of large2x URLs."""
    params = urllib.parse.urlencode({
        "query": query,
        "per_page": per_page,
        "page": page,
        "orientation": "landscape",
    })
    url = f"https://api.pexels.com/v1/search?{params}"
    req = urllib.request.Request(url, headers={"Authorization": key, "User-Agent": APP_UA})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        return [
            p["src"].get("large2x") or p["src"].get("original")
            for p in data.get("photos", [])
            if p.get("src")
        ]
    except Exception as e:
        log.warning("Pexels error for '%s' p%d: %s", query, page, e)
        return []


def build_species_pool(species: str, key: str) -> list[str]:
    """
    Build a pool of unique Pexels photo URLs for a species.
    Fetches per_page=80 for each query, deduplicates.
    """
    queries = SPECIES_QUERIES.get(species, [f"{species} animal"])
    pool: list[str] = []
    seen: set[str] = set()

    for query in queries:
        urls = _fetch_pexels_page(query, key, per_page=80)
        for url in urls:
            if url and url not in seen:
                pool.append(url)
                seen.add(url)
        log.info("  [%s] '%s' → %d photos (pool: %d)", species, query, len(urls), len(pool))
        time.sleep(0.4)  # respect Pexels rate limit (~150 req/min)

    return pool


# ── Main ──────────────────────────────────────────────────────────────────────

async def regen(dry_run: bool, species_filter: Optional[str]) -> None:
    key = settings.PEXELS_API_KEY
    if not key:
        log.error("PEXELS_API_KEY not set in .env")
        return

    # Load all vet articles sorted by slug (deterministic order)
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Article.id, Article.slug, Article.cover_image)
            .where(Article.category == "veterinary")
            .order_by(Article.slug)
        )
        rows = result.all()

    log.info("Loaded %d veterinary articles", len(rows))

    # Group by detected species
    by_species: dict[str, list[tuple]] = defaultdict(list)
    for art_id, slug, cover in rows:
        sp = detect_species(slug)
        by_species[sp].append((art_id, slug, cover))

    for sp, articles in sorted(by_species.items()):
        if species_filter and sp != species_filter:
            continue

        log.info("\n=== %s (%d articles) ===", sp.upper(), len(articles))

        # Build photo pool for this species
        pool = build_species_pool(sp, key)
        if not pool:
            log.warning("No photos for species %s — skipping", sp)
            continue

        log.info("Pool size: %d unique photos for %d articles", len(pool), len(articles))
        if len(pool) < len(articles):
            log.warning("Pool smaller than article count — %d articles will share photos",
                        len(articles) - len(pool))

        # Assign unique photos round-robin
        updated = 0
        for i, (art_id, slug, old_cover) in enumerate(articles):
            new_url = pool[i % len(pool)]

            # Skip if already has this exact URL
            if old_cover == new_url:
                continue

            log.info("  [%d/%d] %s", i + 1, len(articles), slug[:60])
            log.info("    old: %s", (old_cover or "none")[:70])
            log.info("    new: %s", new_url[:70])

            if not dry_run:
                async with AsyncSessionLocal() as session:
                    await session.execute(
                        update(Article)
                        .where(Article.id == art_id)
                        .values(cover_image=new_url)
                    )
                    await session.commit()
            updated += 1

        log.info("%s: %d articles updated", sp, updated)

    log.info("\nDone.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Assign unique Pexels photos to vet articles")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--species", type=str, default=None)
    args = parser.parse_args()

    asyncio.run(regen(args.dry_run, args.species))


if __name__ == "__main__":
    main()
