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
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

# ── Config ─────────────────────────────────────────────────────────────────────
DAILY_LIMIT    = 4                             # 3 articles + 1 news = 4 total/day ≈ 9600 API units
WAIT_BETWEEN   = 60                            # seconds between uploads
OUTPUT_DIR     = Path("/tmp/yt_daily")
TRACKING_FILE  = Path(os.environ.get("YT_TRACKING",      "/opt/medmind/youtube_uploaded.json"))
NEWS_TRACKING  = Path(os.environ.get("YT_NEWS_TRACKING", "/opt/medmind/youtube_news_uploaded.json"))
PLAYLISTS_FILE = Path(os.environ.get("YT_PLAYLISTS",     "/opt/medmind/youtube_playlists.json"))
API_URL        = "https://medmind.pro/api/v1"

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.youtube_uploader import get_valid_token, process_one, process_news_one
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

def load_news_uploaded() -> dict:
    if NEWS_TRACKING.exists():
        with open(NEWS_TRACKING) as f:
            return json.load(f)
    return {}

def save_news_uploaded(data: dict):
    NEWS_TRACKING.parent.mkdir(parents=True, exist_ok=True)
    with open(NEWS_TRACKING, "w") as f:
        json.dump(data, f, indent=2)

def load_playlists() -> dict:
    if PLAYLISTS_FILE.exists():
        try:
            content = Path(PLAYLISTS_FILE).read_text().strip()
            return json.loads(content) if content else {}
        except (json.JSONDecodeError, ValueError):
            return {}
    return {}


# ── News fetching ──────────────────────────────────────────────────────────────

def fetch_latest_news(limit: int = 50, lang: str = "en") -> list[dict]:
    """Return list of {slug, category} for published news, newest first."""
    params: dict = {"limit": limit, "offset": 0}
    if lang != "en":
        params["locale"] = lang
    try:
        resp = httpx.get(f"{API_URL}/news", params=params, timeout=20)
        if resp.status_code == 200:
            return [
                {"slug": n["slug"], "category": n.get("category", "general-medicine")}
                for n in resp.json()
            ]
    except Exception as e:
        print(f"⚠️  Could not fetch news: {e}")
    return []


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

async def run(limit: int, dry_run: bool, lang: str = "en"):
    now = lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    log = lambda msg: print(f"[{now()}] {msg}", flush=True)

    log(f"{'[DRY RUN] ' if dry_run else ''}Daily YouTube upload started "
        f"(limit={limit}, lang={lang}): 1 news + {limit-1} articles")

    uploaded      = load_uploaded()
    news_uploaded = load_news_uploaded()
    playlists     = load_playlists()
    log(f"Already uploaded: {len(uploaded)} articles, {len(news_uploaded)} news")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    success = 0
    total_slots = limit

    # ── Slot 1: one news video ─────────────────────────────────────────────────
    all_news = fetch_latest_news(limit=50, lang=lang)
    news_queue = [n for n in all_news if n["slug"] not in news_uploaded][:1]

    if not news_queue:
        log("ℹ️  No new news to upload — filling slot with article instead")
        article_limit = total_slots       # use all slots for articles
    else:
        article_limit = total_slots - 1   # reserve 1 slot for news

    if dry_run and news_queue:
        n = news_queue[0]
        log(f"  [DRY] Would upload NEWS: {n['slug']}  [{n['category']}]")
    elif news_queue:
        n = news_queue[0]
        log(f"\n[NEWS] {n['slug']}  [{n['category']}]")
        access_token, _ = get_valid_token()
        try:
            video_id = await process_news_one(
                slug         = n["slug"],
                lang         = lang,
                access_token = access_token,
                output_dir   = OUTPUT_DIR,
                delete_after = True,
            )
            if video_id:
                news_uploaded[n["slug"]] = {
                    "video_id":    video_id,
                    "uploaded_at": datetime.now(timezone.utc).isoformat(),
                    "lang":        lang,
                    "category":    n["category"],
                }
                save_news_uploaded(news_uploaded)
                success += 1
                log(f"  ✅ https://youtu.be/{video_id}")
            else:
                log("  ❌ News upload failed — slot returned to articles")
                article_limit = total_slots
        except Exception as e:
            log(f"  ❌ News error: {e} — slot returned to articles")
            article_limit = total_slots

        if article_limit < total_slots:   # only wait if we'll upload more
            log(f"  ⏳ Waiting {WAIT_BETWEEN}s…")
            await asyncio.sleep(WAIT_BETWEEN)

    # ── Remaining slots: articles ──────────────────────────────────────────────
    all_articles = fetch_all_slugs(max_articles=300)
    if not all_articles:
        log("❌ Could not fetch article list. Aborting articles.")
    else:
        queue = [a for a in all_articles if a["slug"] not in uploaded][:article_limit]

        if not queue:
            log("✅ All articles already uploaded.")
        else:
            log(f"Queue: {len(queue)} article(s) to upload")

            if dry_run:
                for a in queue:
                    log(f"  [DRY] Would upload: {a['slug']}  [{a['category']}]")
            else:
                for i, article in enumerate(queue, 1):
                    slug     = article["slug"]
                    category = article["category"]
                    playlist_id = playlists.get(category)

                    log(f"\n[{i}/{len(queue)}] {slug}  [{category}]")
                    if playlist_id:
                        log(f"  → Playlist: {playlist_id}")

                    access_token, _ = get_valid_token()
                    try:
                        video_id = await process_one(
                            slug         = slug,
                            lang         = lang,
                            access_token = access_token,
                            output_dir   = OUTPUT_DIR,
                            delete_after = True,
                            playlist_id  = playlist_id,
                        )
                        if video_id:
                            uploaded[slug] = {
                                "video_id":    video_id,
                                "uploaded_at": datetime.now(timezone.utc).isoformat(),
                                "lang":        lang,
                                "category":    category,
                            }
                            save_uploaded(uploaded)
                            success += 1
                            log(f"  ✅ https://youtu.be/{video_id}")
                        else:
                            log("  ❌ Upload failed or skipped")
                    except Exception as e:
                        log(f"  ❌ Error: {e}")

                    if i < len(queue):
                        log(f"  ⏳ Waiting {WAIT_BETWEEN}s…")
                        await asyncio.sleep(WAIT_BETWEEN)

    log(f"\nDone. Uploaded {success}/{total_slots} videos. "
        f"Total: {len(uploaded)} articles, {len(news_uploaded)} news")


def main():
    parser = argparse.ArgumentParser(description="MedMind Daily YouTube Upload")
    parser.add_argument("--limit",   type=int, default=DAILY_LIMIT,
                        help=f"Max videos to upload total (default: {DAILY_LIMIT}; 1 news + rest articles)")
    parser.add_argument("--lang",    type=str, default="en",
                        help="Language code: en|ru|es|de|fr|ar|tr (default: en)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be uploaded without actually doing it")
    args = parser.parse_args()

    asyncio.run(run(args.limit, args.dry_run, args.lang))


if __name__ == "__main__":
    main()
