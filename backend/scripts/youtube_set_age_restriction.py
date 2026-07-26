#!/usr/bin/env python3
"""
MedMind AI — Set age restriction on all existing YouTube videos.

Retroactively applies ytAgeRestricted to all uploaded videos on a channel.
Prevents YouTube from auto-adding restrictions unpredictably.

Usage:
    # Account 1 (EN channel):
    python3 youtube_set_age_restriction.py

    # Account 2 (ES channel):
    YT_TOKEN=/opt/medmind/youtube_token_account2.json \
    YT_CLIENT_SECRET=/opt/medmind/client_secret_account2.json \
    python3 youtube_set_age_restriction.py

    # Dry run (list videos without changing):
    python3 youtube_set_age_restriction.py --dry-run

    # Limit to N most recent videos:
    python3 youtube_set_age_restriction.py --max 50
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx

TOKEN_FILE    = Path(os.environ.get("YT_TOKEN",         "/opt/medmind/youtube_token.json"))
SECRET_FILE   = Path(os.environ.get("YT_CLIENT_SECRET", "/opt/medmind/client_secret_web.json"))
YT_API_BASE   = "https://www.googleapis.com/youtube/v3"


# ── Auth helpers (copied from youtube_uploader.py) ────────────────────────────

def load_secret() -> dict:
    data = json.loads(SECRET_FILE.read_text())
    return data.get("installed") or data.get("web") or data


def load_token() -> dict:
    if not TOKEN_FILE.exists():
        print(f"❌ Token not found: {TOKEN_FILE}")
        sys.exit(1)
    return json.loads(TOKEN_FILE.read_text())


def save_token(t: dict):
    TOKEN_FILE.write_text(json.dumps(t, indent=2))


def _token_expires_at(t: dict) -> float:
    if t.get("expires_at"):
        return float(t["expires_at"])
    if t.get("expiry"):
        try:
            import datetime as _dt
            dt = _dt.datetime.fromisoformat(t["expiry"].replace("Z", "+00:00"))
            return dt.timestamp()
        except Exception:
            pass
    return 0.0


def get_access_token() -> str:
    secret = load_secret()
    token  = load_token()
    creds  = token.get("client_id") and token or secret

    if time.time() >= _token_expires_at(token) - 60:
        print("Refreshing token…")
        resp = httpx.post("https://oauth2.googleapis.com/token", data={
            "client_id":     creds.get("client_id") or secret["client_id"],
            "client_secret": creds.get("client_secret") or secret["client_secret"],
            "refresh_token": token["refresh_token"],
            "grant_type":    "refresh_token",
        })
        resp.raise_for_status()
        token = {**token, **resp.json(), "expires_at": time.time() + resp.json().get("expires_in", 3600)}
        save_token(token)

    return token.get("access_token") or token.get("token")


# ── YouTube API helpers ───────────────────────────────────────────────────────

def get_channel_id(access_token: str) -> str:
    resp = httpx.get(
        f"{YT_API_BASE}/channels",
        params={"part": "id", "mine": "true"},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    resp.raise_for_status()
    items = resp.json().get("items", [])
    if not items:
        print("❌ No channel found for this token")
        sys.exit(1)
    return items[0]["id"]


def list_all_videos(channel_id: str, access_token: str, max_results: int | None = None) -> list[dict]:
    """Return list of {id, title} for all videos on the channel."""
    videos = []
    page_token = None

    while True:
        params: dict = {
            "part":       "snippet",
            "channelId":  channel_id,
            "type":       "video",
            "maxResults": 50,
            "order":      "date",
        }
        if page_token:
            params["pageToken"] = page_token

        resp = httpx.get(
            f"{YT_API_BASE}/search",
            params=params,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        ids = [item["id"]["videoId"] for item in data.get("items", [])]
        if not ids:
            break

        # Fetch full details
        det_resp = httpx.get(
            f"{YT_API_BASE}/videos",
            params={"part": "snippet,status", "id": ",".join(ids)},
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        det_resp.raise_for_status()

        for item in det_resp.json().get("items", []):
            videos.append({
                "id":         item["id"],
                "title":      item["snippet"]["title"][:70],
                "categoryId": item["snippet"].get("categoryId", "27"),
                "privacy":    item.get("status", {}).get("privacyStatus", "unknown"),
            })

        if max_results and len(videos) >= max_results:
            videos = videos[:max_results]
            break

        page_token = data.get("nextPageToken")
        if not page_token:
            break

        time.sleep(0.3)  # polite pause between pages

    return videos


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Note: YouTube Data API v3 no longer supports setting contentRating.ytRating via API.
    # Age restriction must be managed in YouTube Studio UI.
    # This script is now a channel video lister only.
    parser = argparse.ArgumentParser(description="List YouTube channel videos (age restriction via API deprecated)")
    parser.add_argument("--dry-run", action="store_true", help="List videos")
    parser.add_argument("--max",     type=int,  default=None, help="Limit to N most recent videos")
    parser.add_argument("--skip-restricted", action="store_true", help="(deprecated, no-op)")
    args = parser.parse_args()

    print(f"Token: {TOKEN_FILE}")
    access_token = get_access_token()

    print("Getting channel ID…")
    channel_id = get_channel_id(access_token)
    print(f"Channel: {channel_id}")

    print(f"Fetching video list{'(max ' + str(args.max) + ')' if args.max else ''}…")
    videos = list_all_videos(channel_id, access_token, args.max)
    print(f"Found {len(videos)} videos\n")

    for v in videos:
        print(f"  {v['id']} | {v['privacy']:8s} | {v['title']}")

    print(f"\nNote: Age restriction via API is no longer supported by YouTube Data API v3.")
    print(f"Manage age restriction in YouTube Studio: https://studio.youtube.com")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    main()
