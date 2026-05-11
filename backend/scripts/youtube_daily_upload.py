#!/usr/bin/env python3
"""
MedMind AI — Daily YouTube Upload (cron script)

Runs daily at 10:00 UTC. Uploads up to DAILY_LIMIT new videos,
skipping articles already uploaded. Automatically adds each video
to the matching category playlist.

Tracking file: /opt/medmind/youtube_uploaded.json
  { "slug": { "video_id": "...", "uploaded_at": "...", "lang": "en", "category": "..." } }

Cron setup (already done via CronCreate):
  0 10 * * * python3 /opt/medmind/backend/scripts/youtube_daily_upload.py

Manual run:
    python3 backend/scripts/youtube_daily_upload.py
    python3 backend/scripts/youtube_daily_upload.py --limit 3
    python3 backend/scripts/youtube_daily_upload.py --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

# ── Config ─────────────────────────────────────────────────────────────────────
DAILY_LIMIT    = 6                             # YouTube unverified channel quota
WAIT_BETWEEN   = 60                            # seconds between uploads
OUTPUT_DIR     = Path("/tmp/yt_daily")
TRACKING_FILE  = Path("/opt/medmind/youtube_uploaded.json")
PLAYLISTS_FILE = Path("/opt/medmind/youtube_playlists.json")
API_URL        = "https://medmind.pro/api/v1"

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.youtube_uploader import get_valid_token, process_one
from scripts.youtube_playlists import get_playlist_id, add_video_to_playlist


# ── Tracking helpers ───────────────────────────────────────────────────────────

def load_uploaded() -> dict:
    if TRACKING_FILE.exists():
        with open(TRACKING_FILE) as f:
            return json.load(f)
    return {}

def save_uploaded(data: dict):
    TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TRACKING_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_playlists() -> dict:
    if PLAYLISTS_FILE.exists():
        with open(PLAYLISTS_FILE) as f:
            return json.load(f)
    return {}


# ── Article fetching ───────────────────────────────────────────────────────────

def fetch_all_slugs(max_articles: int = 400) -> list[dict]:
    """Fetch all published articles via pagination. Returns list of {slug, category}."""
    result = []
    page   = 1
    per    = 100
    try:
        while len(result) < max_articles:
            resp = httpx.get(
                f"{API_URL}/articles",
                params={"limit": per, "page": page},
                timeout=20,
            )
            if resp.status_code != 200:
                break
            data     = resp.json()
            articles = data.get("articles", data) if isinstance(data, dict) else data
            if not articles:
                break
            result.extend({"slug": a["slug"], "category": a.get("category", "")} for a in articles)
            if len(articles) < per:
                break
            page += 1
    except Exception as e:
        print(f"⚠️  Could not fetch articles: {e}")
    return result


# ── Main ───────────────────────────────────────────────────────────────────────

async def run(limit: int, dry_run: bool):
    now     = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    log     = lambda msg: print(f"[{now}] {msg}", flush=True)

    log(f"{'[DRY RUN] ' if dry_run else ''}Daily YouTube upload started (limit={limit})")

    uploaded  = load_uploaded()
    playlists = load_playlists()
    log(f"Already uploaded: {len(uploaded)} videos")

    # Fetch all published articles
    articles = fetch_all_slugs(max_articles=300)
    if not articles:
        log("❌ Could not fetch article list. Aborting.")
        return

    # Filter out already uploaded slugs
    queue = [a for a in articles if a["slug"] not in uploaded][:limit]

    if not queue:
        log("✅ All articles already uploaded. Nothing to do.")
        return

    log(f"Queue: {len(queue)} new videos to upload")

    if dry_run:
        for a in queue:
            log(f"  [DRY] Would upload: {a['slug']}  [{a['category']}]")
        return

    access_token, _ = get_valid_token()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    success = 0
    for i, article in enumerate(queue, 1):
        slug     = article["slug"]
        category = article["category"]
        playlist_id = playlists.get(category)

        log(f"\n[{i}/{len(queue)}] {slug}  [{category}]")
        if playlist_id:
            log(f"  → Playlist: {playlist_id}")

        try:
            video_id = await process_one(
                slug         = slug,
                lang         = "en",
                access_token = access_token,
                output_dir   = OUTPUT_DIR,
                delete_after = True,
                playlist_id  = playlist_id,
            )

            if video_id:
                uploaded[slug] = {
                    "video_id":    video_id,
                    "uploaded_at": datetime.now(timezone.utc).isoformat(),
                    "lang":        "en",
                    "category":    category,
                }
                save_uploaded(uploaded)
                success += 1
                log(f"  ✅ https://youtu.be/{video_id}")
            else:
                log(f"  ❌ Upload failed or skipped")

        except Exception as e:
            log(f"  ❌ Error: {e}")

        if i < len(queue):
            log(f"  ⏳ Waiting {WAIT_BETWEEN}s…")
            await asyncio.sleep(WAIT_BETWEEN)

    log(f"\nDone. Uploaded {success}/{len(queue)} videos. Total: {len(uploaded)}")


def main():
    parser = argparse.ArgumentParser(description="MedMind Daily YouTube Upload")
    parser.add_argument("--limit",   type=int, default=DAILY_LIMIT,
                        help=f"Max videos to upload (default: {DAILY_LIMIT})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be uploaded without actually doing it")
    args = parser.parse_args()

    asyncio.run(run(args.limit, args.dry_run))


if __name__ == "__main__":
    main()
