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
SECRET_FILE   = Path(os.environ.get("YT_CLIENT_SECRET", "/opt/medmind/client_secret.json"))
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
    """Return list of {id, title, contentRating} for all videos on the channel."""
    videos = []
    page_token = None

    while True:
        params: dict = {
            "part":       "snippet,contentRating,status",
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

        # Fetch full details including contentRating
        det_resp = httpx.get(
            f"{YT_API_BASE}/videos",
            params={"part": "snippet,contentRating,status", "id": ",".join(ids)},
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        det_resp.raise_for_status()

        for item in det_resp.json().get("items", []):
            cr = item.get("contentRating", {})
            videos.append({
                "id":     item["id"],
                "title":  item["snippet"]["title"][:70],
                "restricted": cr.get("ytRating") == "ytAgeRestricted",
                "categoryId": item["snippet"].get("categoryId", "27"),
            })

        if max_results and len(videos) >= max_results:
            videos = videos[:max_results]
            break

        page_token = data.get("nextPageToken")
        if not page_token:
            break

        time.sleep(0.3)  # polite pause between pages

    return videos


def set_age_restriction(video_id: str, title: str, category_id: str, access_token: str) -> bool:
    """Update a single video to add ytAgeRestricted content rating."""
    body = {
        "id": video_id,
        "contentRating": {
            "ytRating": "ytAgeRestricted",
        },
    }
    resp = httpx.put(
        f"{YT_API_BASE}/videos",
        params={"part": "contentRating"},
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type":  "application/json",
        },
        content=json.dumps(body).encode(),
        timeout=15,
    )
    if resp.status_code in (200, 204):
        return True
    print(f"    ❌ Failed {video_id}: {resp.status_code} {resp.text[:150]}")
    return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Set YouTube age restriction on all channel videos")
    parser.add_argument("--dry-run", action="store_true", help="List videos without modifying")
    parser.add_argument("--max",     type=int,  default=None, help="Limit to N most recent videos")
    parser.add_argument("--skip-restricted", action="store_true",
                        help="Skip videos already age-restricted (default: re-apply to all)")
    args = parser.parse_args()

    print(f"Token: {TOKEN_FILE}")
    access_token = get_access_token()

    print("Getting channel ID…")
    channel_id = get_channel_id(access_token)
    print(f"Channel: {channel_id}")

    print(f"Fetching video list{'(max ' + str(args.max) + ')' if args.max else ''}…")
    videos = list_all_videos(channel_id, access_token, args.max)
    print(f"Found {len(videos)} videos")

    if args.dry_run:
        print("\n[DRY RUN] Would restrict these videos:")
        for v in videos:
            status = "✅ already restricted" if v["restricted"] else "⚠️  not restricted"
            print(f"  {v['id']} | {status} | {v['title']}")
        return

    need_update = videos if not args.skip_restricted else [v for v in videos if not v["restricted"]]
    already_ok  = len(videos) - len(need_update)

    print(f"\n{already_ok} already restricted, updating {len(need_update)}…\n")

    updated = 0
    failed  = 0
    for i, v in enumerate(need_update, 1):
        print(f"  [{i}/{len(need_update)}] {v['id']} — {v['title']}", end=" ")
        ok = set_age_restriction(v["id"], v["title"], v["categoryId"], access_token)
        if ok:
            print("✅")
            updated += 1
        else:
            failed += 1
        time.sleep(0.5)  # stay within quota (150 units/day free for videos.update)

    print(f"\nDone — updated: {updated} | failed: {failed} | already restricted: {already_ok}")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    main()
