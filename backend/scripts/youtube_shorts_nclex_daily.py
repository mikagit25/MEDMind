#!/usr/bin/env python3
"""
MedMind AI — Daily NCLEX Q&A Shorts Upload

Picks DAILY_LIMIT unuploaded NCLEX questions with key_takeaway,
renders each into a 9:16 Short, and uploads to YouTube (EN account).

Tracking: /opt/medmind/youtube_shorts_nclex_uploaded.json

Cron: 37 11 * * *  (11:37 UTC — after regular Shorts at 10:11)

Usage:
    python3 youtube_shorts_nclex_daily.py
    python3 youtube_shorts_nclex_daily.py --limit 3 --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from nclex_to_shorts import (
    build_video,
    list_available_questions,
    load_question,
    _save_tracking,
    TRACKING_FILE,
)

DAILY_LIMIT    = 2
WAIT_BETWEEN   = 45   # seconds between uploads

TOKEN_FILE     = Path(os.environ.get("YT_TOKEN",         "/opt/medmind/youtube_token.json"))
SECRET_FILE    = Path(os.environ.get("YT_CLIENT_SECRET", "/opt/medmind/client_secret_web.json"))

HASHTAGS = (
    "#NCLEX #NursingStudent #NursingSchool #NCLEXRN #NursingEducation "
    "#MedMindAI #Shorts #NurseLife #NursingStudy #PassNCLEX"
)


def _yt_upload(mp4: str, title: str, description: str, token_file: Path, secret_file: Path) -> str | None:
    """Upload MP4 to YouTube. Returns video ID or None."""
    try:
        import google.oauth2.credentials
        import googleapiclient.discovery
        import googleapiclient.http
    except ImportError:
        print("[error] google-api-python-client not installed")
        return None

    creds_data = json.loads(token_file.read_text())

    # client_id/secret may be in the token or in the separate secret file
    client_id     = creds_data.get("client_id")
    client_secret = creds_data.get("client_secret")
    if (not client_id or not client_secret) and secret_file.exists():
        raw = json.loads(secret_file.read_text())
        sec = raw.get("web") or raw.get("installed") or {}
        client_id     = client_id or sec.get("client_id")
        client_secret = client_secret or sec.get("client_secret")

    creds = google.oauth2.credentials.Credentials(
        token         = creds_data.get("access_token") or creds_data.get("token"),
        refresh_token = creds_data.get("refresh_token"),
        token_uri     = creds_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id     = client_id,
        client_secret = client_secret,
    )

    yt = googleapiclient.discovery.build("youtube", "v3", credentials=creds)
    body = {
        "snippet": {
            "title":       title[:100],
            "description": description[:4900],
            "tags":        [
                "nclex", "nursing student", "nclex rn", "nursing school",
                "nursing education", "medmind", "medical education",
                "nclex practice", "nursing quiz", "pass nclex",
            ],
            "categoryId":  "27",   # Education
        },
        "status": {
            "privacyStatus":         "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    media = googleapiclient.http.MediaFileUpload(
        mp4, chunksize=-1, resumable=True, mimetype="video/mp4"
    )
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        _, response = req.next_chunk()

    vid_id = response.get("id")

    # Save refreshed access token if updated
    orig_access = creds_data.get("access_token") or creds_data.get("token")
    if creds.token and creds.token != orig_access:
        creds_data["access_token"] = creds.token
        import time as _time
        creds_data["expires_at"] = _time.time() + 3600
        token_file.write_text(json.dumps(creds_data, indent=2))

    return vid_id


def _make_title(q: dict) -> str:
    diff = q.get("difficulty", "medium").capitalize()
    module = (q.get("module_title") or "NCLEX")[:40]
    return f"🩺 NCLEX Challenge: {module} ({diff}) #Shorts"[:100]


def _make_description(q: dict, correct: str) -> str:
    question = q["question"][:200]
    options  = q["options"] if isinstance(q["options"], dict) else json.loads(q["options"])
    takeaway = q.get("key_takeaway", "")[:300]
    module   = (q.get("module_title") or "NCLEX Prep")

    desc = (
        f"Can you answer this NCLEX question? Test your nursing knowledge!\n\n"
        f"📋 Topic: {module}\n\n"
        f"❓ {question}\n\n"
        f"A) {options.get('A', '')}\n"
        f"B) {options.get('B', '')}\n"
        f"C) {options.get('C', '')}\n"
        f"D) {options.get('D', '')}\n\n"
        f"✅ Answer: {correct}\n\n"
        f"💡 Key Takeaway: {takeaway}\n\n"
        f"Practice 1,000+ NCLEX questions for FREE at:\n"
        f"🔗 https://medmind.pro/nclex\n\n"
        f"{HASHTAGS}"
    )
    return desc


async def run(limit: int, dry_run: bool):
    questions = list_available_questions(limit)
    if not questions:
        print("✅ No new NCLEX questions to upload today.")
        return

    print(f"📋 Found {len(questions)} question(s) to upload (limit={limit})")

    if not TOKEN_FILE.exists() and not dry_run:
        print(f"[error] YouTube token not found: {TOKEN_FILE}")
        sys.exit(1)

    uploaded_count = 0
    for i, q_meta in enumerate(questions[:limit]):
        q = load_question(q_meta["id"])
        if not q:
            print(f"  ⚠ Question {q_meta['id']} not found with key_takeaway, skipping")
            continue

        print(f"\n[{i+1}/{min(len(questions), limit)}] {q['question'][:60]}…")

        with tempfile.TemporaryDirectory() as tmp:
            mp4 = f"{tmp}/nclex_short.mp4"

            try:
                await build_video(q, mp4, dry_run=dry_run)
            except Exception as e:
                print(f"  ✗ Video build failed: {e}")
                continue

            title = _make_title(q)
            desc  = _make_description(q, q["correct"])
            print(f"  Title: {title}")

            if dry_run:
                print(f"  [dry-run] would upload: {mp4}")
                _save_tracking(q["id"])
                uploaded_count += 1
                continue

            yt_id = _yt_upload(mp4, title, desc, TOKEN_FILE, SECRET_FILE)
            if yt_id:
                print(f"  ✅ Uploaded: https://youtu.be/{yt_id}")
                _save_tracking(q["id"], yt_id)
                uploaded_count += 1
            else:
                print(f"  ✗ Upload failed")

        if i < min(len(questions), limit) - 1:
            print(f"  Waiting {WAIT_BETWEEN}s before next upload…")
            time.sleep(WAIT_BETWEEN)

    print(f"\n{'='*50}")
    print(f"Done: {uploaded_count}/{min(len(questions), limit)} uploaded")


def main():
    parser = argparse.ArgumentParser(description="Daily NCLEX Shorts uploader")
    parser.add_argument("--limit", type=int, default=DAILY_LIMIT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.limit, args.dry_run))


if __name__ == "__main__":
    main()
