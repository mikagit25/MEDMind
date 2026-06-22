#!/usr/bin/env python3
"""
Bulk-patch all uploaded MedMind videos to selfDeclaredMadeForKids=False.

Reads tracking JSON files to collect all video IDs, then calls
videos.update for each one via the YouTube Data API v3.

Usage:
    python3 fix_made_for_kids.py             # dry run
    python3 fix_made_for_kids.py --apply     # actually update
    python3 fix_made_for_kids.py --apply --account2   # run for ES account
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import httpx

MEDMIND_DIR = Path("/opt/medmind")

# ── Tracking files ────────────────────────────────────────────────────────────
TRACKING_FILES_ACCOUNT1 = [
    MEDMIND_DIR / "youtube_uploaded.json",
    MEDMIND_DIR / "youtube_news_uploaded.json",
    MEDMIND_DIR / "youtube_shorts_uploaded.json",
]

TRACKING_FILES_ACCOUNT2 = [
    MEDMIND_DIR / "youtube_uploaded_es.json",
    MEDMIND_DIR / "youtube_shorts_uploaded_es.json",
    MEDMIND_DIR / "youtube_playlists_es.json",  # might not have video_id
]

# ── Auth ──────────────────────────────────────────────────────────────────────

def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def get_access_token(secret_path: Path, token_path: Path) -> str:
    secret = _load_json(secret_path)
    token = _load_json(token_path)

    client_id = (secret.get("installed") or secret.get("web") or {}).get("client_id")
    client_secret = (secret.get("installed") or secret.get("web") or {}).get("client_secret")

    # Try to refresh
    r = httpx.post("https://oauth2.googleapis.com/token", data={
        "client_id":     client_id,
        "client_secret": client_secret,
        "refresh_token": token["refresh_token"],
        "grant_type":    "refresh_token",
    }, timeout=15)
    r.raise_for_status()
    new_token = r.json()
    # Save updated token
    token.update(new_token)
    _save_json(token_path, token)
    return new_token["access_token"]


# ── Collect video IDs ─────────────────────────────────────────────────────────

def collect_video_ids(tracking_files: list[Path]) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    for path in tracking_files:
        data = _load_json(path)
        for key, val in data.items():
            if isinstance(val, dict):
                vid = val.get("video_id")
            elif isinstance(val, str):
                vid = val  # some tracking files store just the ID
            else:
                continue
            if vid and vid not in seen:
                ids.append(vid)
                seen.add(vid)
    return ids


# ── Patch a single video ──────────────────────────────────────────────────────

def patch_video(video_id: str, access_token: str) -> tuple[bool, str]:
    """Set selfDeclaredMadeForKids=False on one video. Returns (success, message)."""
    r = httpx.put(
        "https://www.googleapis.com/youtube/v3/videos",
        params={"part": "status"},
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        content=json.dumps({
            "id": video_id,
            "status": {
                "selfDeclaredMadeForKids": False,
            },
        }).encode(),
        timeout=20,
    )
    if r.status_code == 200:
        return True, "OK"
    if r.status_code == 403:
        return False, f"403 Forbidden — might not own this video or token issue"
    if r.status_code == 404:
        return False, f"404 Not found"
    return False, f"{r.status_code} {r.text[:120]}"


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Fix selfDeclaredMadeForKids on MedMind videos")
    parser.add_argument("--apply", action="store_true", help="Actually send API requests (default: dry run)")
    parser.add_argument("--account2", action="store_true", help="Use account 2 credentials (ES channel)")
    parser.add_argument("--delay", type=float, default=0.5, help="Seconds between API calls (default: 0.5)")
    args = parser.parse_args()

    if args.account2:
        secret_path = MEDMIND_DIR / "client_secret_account2.json"
        token_path  = MEDMIND_DIR / "youtube_token_account2.json"
        tracking    = TRACKING_FILES_ACCOUNT2
        label       = "Account 2 (ES)"
    else:
        secret_path = MEDMIND_DIR / "client_secret.json"
        token_path  = MEDMIND_DIR / "youtube_token.json"
        tracking    = TRACKING_FILES_ACCOUNT1
        label       = "Account 1 (EN)"

    video_ids = collect_video_ids(tracking)
    print(f"=== Fix selfDeclaredMadeForKids — {label} ===")
    print(f"Videos found: {len(video_ids)}")
    print(f"Mode: {'APPLY' if args.apply else 'DRY RUN'}\n")

    if not video_ids:
        print("Nothing to do.")
        return

    if not args.apply:
        for vid in video_ids:
            print(f"  [dry] would patch: {vid}")
        print(f"\nRun with --apply to actually update {len(video_ids)} videos.")
        return

    # Get token
    print("Getting access token...")
    try:
        access_token = get_access_token(secret_path, token_path)
    except Exception as e:
        print(f"❌ Auth failed: {e}")
        sys.exit(1)
    print("Token OK\n")

    ok = 0
    fail = 0
    for i, vid in enumerate(video_ids, 1):
        success, msg = patch_video(vid, access_token)
        status = "✅" if success else "❌"
        print(f"  [{i:3d}/{len(video_ids)}] {status} {vid} — {msg}")
        if success:
            ok += 1
        else:
            fail += 1
        if args.delay > 0:
            time.sleep(args.delay)

    print(f"\n=== Done: {ok} updated, {fail} failed ===")


if __name__ == "__main__":
    main()
