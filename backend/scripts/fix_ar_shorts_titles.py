#!/usr/bin/env python3
"""
Fix Arabic titles/descriptions for already-uploaded Shorts on the AR channel.

Reads youtube_shorts_uploaded_ar.json, fetches image info for each entry,
generates proper Arabic title/description via Groq/llama-3.3-70b (KEY_3),
then calls YouTube videos.update to patch the metadata.

Usage:
    python3 fix_ar_shorts_titles.py
    python3 fix_ar_shorts_titles.py --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from pathlib import Path

import httpx

TRACKING_FILE = Path("/opt/medmind/youtube_shorts_uploaded_ar.json")
TOKEN_FILE    = Path("/opt/medmind/youtube_token_ar.json")
SECRET_FILE   = Path("/opt/medmind/client_secret_account3_web.json")
ENV_FILE      = Path("/opt/medmind/backend/.env")
API_URL       = "https://medmind.pro/api/v1"

TAGS_AR = [
    "التعليم الطبي", "الطب", "medmind", "shorts",
    "طالب طب", "الرعاية الصحية", "الطب السريري", "USMLE",
]

DESC_SUFFIX_AR = (
    "\n\n🔗 المقالات الكاملة: https://medmind.pro/ar/articles\n"
    "📚 منصة طبية مجانية: https://medmind.pro/ar\n"
    "#التعليم_الطبي #الطب #MedMindAI #Shorts #طالب_طب #USMLE"
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _load_env_key(name: str) -> str:
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line.startswith(f"{name}="):
                return line.split("=", 1)[1].strip()
    return os.environ.get(name, "")


# ── Groq Arabic generation ─────────────────────────────────────────────────────

def _call_groq(groq_key: str, prompt: str) -> dict | None:
    """Single Groq API call. Returns parsed dict or None."""
    resp = httpx.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {groq_key}",
            "Content-Type":  "application/json",
        },
        json={
            "model":       "llama-3.3-70b-versatile",
            "messages":    [{"role": "user", "content": prompt}],
            "max_tokens":  300,
            "temperature": 0.3,
        },
        timeout=30,
    )
    resp.raise_for_status()
    raw = resp.json()["choices"][0]["message"]["content"].strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw.strip())


def generate_arabic_metadata(image_info: dict) -> dict | None:
    """Generate Arabic YouTube title + description using Groq KEY_3/KEY_4."""
    title     = image_info.get("title", "Medical Image")[:120]
    desc      = (image_info.get("description") or "")[:400]
    modality  = image_info.get("modality", "")
    specialty = image_info.get("specialty", "")

    prompt = (
        "You are creating YouTube metadata for a medical image Short.\n"
        "Generate ONLY in Arabic. Return ONLY valid JSON, no other text.\n\n"
        f"Image:\nTitle: {title}\n"
        f"Modality: {modality} | Specialty: {specialty}\n"
        f"Description: {desc}\n\n"
        "JSON:\n"
        '{\n'
        '  "youtube_title": "Arabic title with 1 emoji, max 60 chars, include #Shorts",\n'
        '  "youtube_description": "1-2 Arabic sentences about what viewers will learn"\n'
        '}'
    )

    for key_name in ("GROQ_API_KEY_3", "GROQ_API_KEY_4"):
        groq_key = _load_env_key(key_name)
        if not groq_key:
            continue
        for attempt in range(3):
            try:
                data = _call_groq(groq_key, prompt)
                return {
                    "youtube_title":       data.get("youtube_title", ""),
                    "youtube_description": data.get("youtube_description", "") + DESC_SUFFIX_AR,
                }
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    wait = 20 * (attempt + 1)
                    print(f"  ⏳ Rate limit on {key_name}, waiting {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"  ⚠️  Groq {key_name} error: {e}")
                    break
            except Exception as e:
                print(f"  ⚠️  Groq {key_name} error: {e}")
                break
        # If rate limit exhausted on this key, try next key immediately

    print("  ⚠️  All Groq keys exhausted")
    return None


# ── Auth ───────────────────────────────────────────────────────────────────────

def load_token() -> dict:
    with open(TOKEN_FILE) as f:
        return json.load(f)

def save_token(t: dict):
    with open(TOKEN_FILE, "w") as f:
        json.dump(t, f, indent=2)

def load_secret() -> dict:
    with open(SECRET_FILE) as f:
        d = json.load(f)
    return d.get("web") or d.get("installed") or d

def get_access_token() -> str:
    token  = load_token()
    secret = load_secret()
    expires_at = float(token.get("expires_at") or 0)
    if time.time() >= expires_at - 60:
        creds = {
            "client_id":     token.get("client_id") or secret["client_id"],
            "client_secret": token.get("client_secret") or secret["client_secret"],
        }
        resp = httpx.post("https://oauth2.googleapis.com/token", data={
            **creds,
            "refresh_token": token["refresh_token"],
            "grant_type":    "refresh_token",
        })
        resp.raise_for_status()
        token = {**token, **resp.json()}
        token["expires_at"] = time.time() + token.get("expires_in", 3600)
        save_token(token)
    return token.get("access_token") or token.get("token")


# ── YouTube update ─────────────────────────────────────────────────────────────

def update_video(video_id: str, title: str, description: str, access_token: str) -> bool:
    body = {
        "id": video_id,
        "snippet": {
            "title":                title[:100],
            "description":          description[:5000],
            "tags":                 TAGS_AR,
            "categoryId":           "27",
            "defaultLanguage":      "ar",
            "defaultAudioLanguage": "ar",
        },
    }
    resp = httpx.put(
        "https://www.googleapis.com/youtube/v3/videos?part=snippet",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type":  "application/json",
        },
        content=json.dumps(body).encode(),
        timeout=30,
    )
    if resp.status_code == 200:
        return True
    print(f"    ❌ Update failed {resp.status_code}: {resp.text[:300]}")
    return False


# ── Fetch image info ───────────────────────────────────────────────────────────

def fetch_image_info(image_id: str) -> dict | None:
    try:
        resp = httpx.get(f"{API_URL}/imaging/{image_id}", timeout=15)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"    ⚠️  API error: {e}")
    return None


# ── Main ───────────────────────────────────────────────────────────────────────

async def run(dry_run: bool, skip: int = 0):
    if not TRACKING_FILE.exists():
        print("❌ Tracking file not found:", TRACKING_FILE)
        return

    uploaded: dict = json.loads(TRACKING_FILE.read_text())
    items = list(uploaded.items())
    if skip:
        items = items[skip:]
        print(f"Skipping first {skip} entries (already updated)")
    print(f"Processing {len(items)} AR Shorts\n")

    success = 0
    for i, (image_id, entry) in enumerate(items, 1):
        video_id  = entry["video_id"]
        old_title = entry.get("title", "?")

        print(f"[{i}/{len(uploaded)}] https://youtu.be/{video_id}")
        print(f"  Old title: {old_title}")

        image_info = fetch_image_info(image_id)
        if not image_info:
            print(f"  ⚠️  Image not found in API, skipping")
            continue

        meta = generate_arabic_metadata(image_info)
        if not meta or not meta.get("youtube_title"):
            print("  ⚠️  Could not generate Arabic title, skipping")
            continue

        new_title = meta["youtube_title"]
        new_desc  = meta["youtube_description"]
        print(f"  New title: {new_title}")

        if dry_run:
            print("  [DRY RUN] Skipped")
            success += 1
            continue

        access_token = get_access_token()
        if update_video(video_id, new_title, new_desc, access_token):
            print("  ✅ Updated")
            success += 1

        if i < len(uploaded):
            await asyncio.sleep(10)

    print(f"\nDone. Updated {success}/{len(items)} videos.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview changes without updating YouTube")
    parser.add_argument("--skip", type=int, default=0,
                        help="Skip first N entries (already updated)")
    args = parser.parse_args()
    asyncio.run(run(args.dry_run, args.skip))


if __name__ == "__main__":
    main()
