#!/usr/bin/env python3
"""
MedMind AI — Daily YouTube Shorts Upload

Uploads up to DAILY_LIMIT (10) new medical image Shorts per day.
Tracking file: /opt/medmind/youtube_shorts_uploaded.json

Cron: 11 10 * * *  (10:11 UTC daily, right after regular video upload)

Usage:
    python3 youtube_shorts_daily.py
    python3 youtube_shorts_daily.py --limit 5 --dry-run
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

DAILY_LIMIT     = 2   # 4 regular + 2 Shorts = 6 total/day ≈ 9600 API units (under 10K limit)
WAIT_BETWEEN    = 30             # seconds between uploads (Shorts are smaller)
OUTPUT_DIR      = Path("/tmp/yt_shorts")
TRACKING_FILE   = Path(os.environ.get("YT_TRACKING", "/opt/medmind/youtube_shorts_uploaded.json"))
PLAYLISTS_FILE  = Path(os.environ.get("YT_PLAYLISTS", "/opt/medmind/youtube_playlists.json"))
TOKEN_FILE      = Path(os.environ.get("YT_TOKEN",          "/opt/medmind/youtube_token.json"))
SECRET_FILE     = Path(os.environ.get("YT_CLIENT_SECRET",  "/opt/medmind/client_secret_web.json"))
API_URL         = "https://medmind.pro/api/v1"

# Description templates per language
CHANNEL_DESC_SUFFIXES = {
    "en": (
        "\n\n🔗 Full articles: https://medmind.pro/articles\n"
        "📚 Free medical platform: https://medmind.pro\n"
        "#MedicalEducation #USMLE #Medicine #MedMindAI #Shorts #MedStudent"
    ),
    "es": (
        "\n\n🔗 Artículos completos: https://medmind.pro/articles\n"
        "📚 Plataforma médica gratuita: https://medmind.pro\n"
        "#EducaciónMédica #Medicina #MedMindAI #Shorts #EstudianteDeMedicina #USMLE"
    ),
    "ru": (
        "\n\n🔗 Полные статьи: https://medmind.pro/articles\n"
        "📚 Бесплатная медицинская платформа: https://medmind.pro\n"
        "#МедицинскоеОбразование #Медицина #MedMindAI #Shorts #МедицинскийСтудент"
    ),
    "de": (
        "\n\n🔗 Vollständige Artikel: https://medmind.pro/articles\n"
        "📚 Kostenlose Medizinplattform: https://medmind.pro\n"
        "#Medizin #Medizinstudent #MedMindAI #Shorts #MedicalEducation"
    ),
    "ar": (
        "\n\n🔗 المقالات الكاملة: https://medmind.pro/ar/articles\n"
        "📚 منصة طبية مجانية: https://medmind.pro/ar\n"
        "#التعليم_الطبي #الطب #MedMindAI #Shorts #طالب_طب #USMLE"
    ),
    "tr": (
        "\n\n🔗 Makaleler: https://medmind.pro/tr/articles\n"
        "📚 Ücretsiz tıp platformu: https://medmind.pro/tr\n"
        "#TıpEğitimi #Tıp #MedMindAI #Shorts #TıpÖğrencisi #USMLE"
    ),
    "fr": (
        "\n\n🔗 Articles complets: https://medmind.pro/fr/articles\n"
        "📚 Plateforme médicale gratuite: https://medmind.pro/fr\n"
        "#ÉducationMédicale #Médecine #MedMindAI #Shorts #ÉtudiantMédecine"
    ),
}

TITLE_PREFIXES = {
    "en": "🩺",
    "es": "🩺 Caso clínico:",
    "ru": "🩺 Клинический случай:",
    "de": "🩺 Klinischer Fall:",
    "ar": "🩺",
    "tr": "🩺 Klinik Vaka:",
    "fr": "🩺 Cas clinique:",
}

LEARN_ABOUT = {
    "en": "Learn about",
    "es": "Aprende sobre",
    "ru": "Изучите",
    "de": "Erfahren Sie mehr über",
    "ar": "تعرّف على",
    "tr": "Hakkında öğren",
    "fr": "Découvrez",
}

SPECIALTY_LABEL = {
    "en": "Specialty",
    "es": "Especialidad",
    "ru": "Специальность",
    "de": "Fachgebiet",
    "ar": "التخصص",
    "tr": "Uzmanlık",
    "fr": "Spécialité",
}

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.image_to_shorts import build_short, fetch_images, generate_script
from scripts.youtube_playlists import get_playlist_id, add_video_to_playlist


# ── Auth ───────────────────────────────────────────────────────────────────────

def load_token() -> dict:
    with open(TOKEN_FILE) as f: return json.load(f)

def load_secret() -> dict:
    with open(SECRET_FILE) as f:
        d = json.load(f)
    return d.get("installed") or d.get("web") or d

def save_token(t: dict):
    with open(TOKEN_FILE, "w") as f: json.dump(t, f, indent=2)

def _token_expires_at(token: dict) -> float:
    if token.get("expires_at"):
        return float(token["expires_at"])
    if token.get("expiry"):
        try:
            from datetime import timezone
            dt = datetime.fromisoformat(token["expiry"].replace("Z", "+00:00"))
            return dt.timestamp()
        except Exception:
            pass
    return 0.0

def _token_creds(token: dict, secret: dict) -> dict:
    if token.get("client_id") and token.get("client_secret"):
        return {"client_id": token["client_id"], "client_secret": token["client_secret"]}
    return secret

def _do_auth_flow(secret: dict) -> dict:
    import urllib.parse
    auth_url = (
        "https://accounts.google.com/o/oauth2/auth"
        "?response_type=code"
        f"&client_id={urllib.parse.quote(secret['client_id'])}"
        "&redirect_uri=http://localhost"
        "&scope=https://www.googleapis.com/auth/youtube.upload"
        "%20https://www.googleapis.com/auth/youtube"
        "&access_type=offline"
        "&prompt=consent"
    )
    print("\n" + "=" * 60)
    print("STEP 1: Open this URL in your browser:")
    print("=" * 60)
    print(auth_url)
    print("=" * 60)
    print("\nSTEP 2: Log in and click Allow")
    print("STEP 3: Browser goes to localhost (error is OK)")
    print("STEP 4: Copy FULL URL from address bar and paste below\n")
    raw = input("Paste the full redirect URL here: ").strip()
    if raw.startswith("http"):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(raw).query)
        code = params.get("code", [None])[0]
    else:
        code = raw
    if not code:
        print("❌ Could not extract auth code.")
        sys.exit(1)
    resp = httpx.post("https://oauth2.googleapis.com/token", data={
        "code":          code,
        "client_id":     secret["client_id"],
        "client_secret": secret["client_secret"],
        "redirect_uri":  "http://localhost",
        "grant_type":    "authorization_code",
    })
    if resp.status_code != 200:
        print(f"❌ Token exchange failed: {resp.text}")
        sys.exit(1)
    token = resp.json()
    token["expires_at"] = time.time() + token.get("expires_in", 3600)
    save_token(token)
    print("✅ Authentication successful! Token saved.")
    return token


def get_access_token() -> str:
    token  = load_token()
    secret = load_secret()
    if time.time() >= _token_expires_at(token) - 60:
        creds = _token_creds(token, secret)
        resp = httpx.post("https://oauth2.googleapis.com/token", data={
            "client_id":     creds["client_id"],
            "client_secret": creds["client_secret"],
            "refresh_token": token["refresh_token"],
            "grant_type":    "refresh_token",
        })
        if resp.status_code in (400, 401):
            print("⚠️  Refresh token revoked by Google. Re-authorizing…")
            token = _do_auth_flow(secret)
        else:
            resp.raise_for_status()
            token = {**token, **resp.json()}
            token["expires_at"] = time.time() + token.get("expires_in", 3600)
            save_token(token)
    return token.get("access_token") or token.get("token")


# ── Tracking ───────────────────────────────────────────────────────────────────

def load_uploaded() -> dict:
    if TRACKING_FILE.exists():
        with open(TRACKING_FILE) as f: return json.load(f)
    return {}

def save_uploaded(data: dict):
    TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TRACKING_FILE, "w") as f: json.dump(data, f, indent=2)


# ── YouTube upload ─────────────────────────────────────────────────────────────

TAGS_BY_LANG: dict[str, list[str]] = {
    "en": ["medical education", "USMLE", "medicine", "medmind", "shorts", "medical student", "healthcare", "clinical medicine"],
    "es": ["educación médica", "medicina", "medmind", "shorts", "estudiante de medicina", "USMLE", "salud", "medicina clínica"],
    "ru": ["медицинское образование", "медицина", "medmind", "shorts", "медицинский студент", "здравоохранение", "клиническая медицина"],
    "de": ["Medizinstudium", "Medizin", "medmind", "shorts", "Medizinstudent", "Gesundheitswesen", "klinische Medizin", "USMLE"],
    "ar": ["التعليم الطبي", "الطب", "medmind", "shorts", "طالب طب", "الرعاية الصحية", "الطب السريري", "USMLE"],
    "tr": ["tıp eğitimi", "tıp", "medmind", "shorts", "tıp öğrencisi", "sağlık", "klinik tıp", "USMLE"],
    "fr": ["éducation médicale", "médecine", "medmind", "shorts", "étudiant en médecine", "santé", "médecine clinique", "USMLE"],
}

def upload_short(mp4: Path, title: str, description: str, access_token: str, lang: str = "en") -> str | None:
    """Upload Short video. Returns video_id or None."""
    metadata = {
        "snippet": {
            "title":       title[:100],
            "description": description[:5000],
            "tags":        TAGS_BY_LANG.get(lang, TAGS_BY_LANG["en"]),
            "categoryId":  "27",   # Education
        },
        "status": {
            "privacyStatus":          "public",
            "selfDeclaredMadeForKids": False,
        },
    }

    file_size = mp4.stat().st_size
    init = httpx.post(
        "https://www.googleapis.com/upload/youtube/v3/videos"
        "?uploadType=resumable&part=snippet,status",
        headers={
            "Authorization":           f"Bearer {access_token}",
            "Content-Type":            "application/json",
            "X-Upload-Content-Type":   "video/mp4",
            "X-Upload-Content-Length": str(file_size),
        },
        content=json.dumps(metadata).encode(),
    )
    if init.status_code != 200:
        print(f"  ❌ Upload init failed: {init.status_code} {init.text[:200]}")
        return None

    upload_url = init.headers["Location"]
    CHUNK      = 5 * 1024 * 1024  # 5 MB (Shorts are small)
    uploaded   = 0

    with open(mp4, "rb") as f:
        while uploaded < file_size:
            chunk = f.read(CHUNK)
            end   = uploaded + len(chunk) - 1
            resp  = httpx.put(
                upload_url,
                headers={
                    "Authorization":  f"Bearer {access_token}",
                    "Content-Type":   "video/mp4",
                    "Content-Range":  f"bytes {uploaded}-{end}/{file_size}",
                    "Content-Length": str(len(chunk)),
                },
                content=chunk,
                timeout=120,
            )
            if resp.status_code in (200, 201):
                vid = resp.json().get("id")
                print(f"  ✅ https://youtu.be/{vid}")
                return vid
            elif resp.status_code == 308:
                uploaded = end + 1
                print(f"  Uploading… {int(uploaded*100/file_size)}%", end="\r")
            else:
                print(f"  ❌ Chunk failed: {resp.status_code}")
                return None
    return None


# ── Main ───────────────────────────────────────────────────────────────────────

async def run(limit: int, dry_run: bool, lang: str = "en"):
    now = lambda: datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    log = lambda msg: print(f"[{now()}] {msg}", flush=True)

    desc_suffix  = CHANNEL_DESC_SUFFIXES.get(lang, CHANNEL_DESC_SUFFIXES["en"])
    title_prefix = TITLE_PREFIXES.get(lang, "🩺")
    learn_about  = LEARN_ABOUT.get(lang, "Learn about")
    spec_label   = SPECIALTY_LABEL.get(lang, "Specialty")

    log(f"{'[DRY RUN] ' if dry_run else ''}Daily Shorts upload started (limit={limit}, lang={lang})")

    uploaded = load_uploaded()
    log(f"Already uploaded: {len(uploaded)} Shorts")

    # Fetch images — large pool so we always find new ones past already-uploaded batch
    all_images = fetch_images(limit=500)
    queue = [img for img in all_images if img["id"] not in uploaded][:limit]

    if not queue:
        log("✅ No new images to upload. Done.")
        return

    log(f"Queue: {len(queue)} new Shorts")

    if dry_run:
        for img in queue:
            log(f"  [DRY] {img.get('title','?')[:60]}  [{img.get('modality','')}]")
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    success = 0
    for i, img in enumerate(queue, 1):
        img_id    = img["id"]
        title     = img.get("title", "Medical Image")[:60]
        modality  = img.get("modality", "")
        specialty = img.get("specialty", "")

        log(f"\n[{i}/{len(queue)}] {title[:55]}  [{modality}]")

        mp4 = OUTPUT_DIR / f"short_{img_id[:8]}.mp4"

        try:
            script = None
            if not mp4.exists():
                script = await build_short(img, mp4, lang=lang)
                if not script:
                    log(f"  ❌ Generation failed")
                    continue
            else:
                log(f"  ♻️  Reusing existing file")
                # Generate localized script for title/description/thumbnail even
                # when the video file already exists — without this the metadata
                # falls back to the English title stored in the imaging DB.
                script = await generate_script(img, lang=lang)

            # Use Claude-generated localized title/description.
            # Fall back to template construction only if generate_script returned None.
            yt_title = (
                script.get("youtube_title") if script else None
            ) or f"{title_prefix} {title[:52]} #Shorts"
            yt_desc  = (
                script.get("youtube_description") if script else None
            ) or (
                f"{learn_about} {title} ({modality.upper()}).\n"
                f"{spec_label}: {specialty.replace('-',' ').title()}\n"
                + desc_suffix
            )

            # Refresh token before each upload
            access_token = get_access_token()
            video_id = upload_short(mp4, yt_title, yt_desc, access_token, lang=lang)

            if video_id:
                # Generate and upload thumbnail
                try:
                    from scripts.generate_thumbnail import generate_thumbnail
                    cover_url = img.get("image_url") or img.get("url")
                    thumb_path = OUTPUT_DIR / f"thumb_{img_id[:8]}.jpg"
                    # Prefer the Arabic display_title from Claude; fall back to
                    # the English DB title only when script generation failed.
                    thumb_title = (script.get("display_title") if script else None) or title
                    generate_thumbnail(
                        title=thumb_title,
                        category=specialty or modality or "diagnostics",
                        lang=lang,
                        out_path=thumb_path,
                        cover_url=cover_url,
                    )
                    thumb_data = thumb_path.read_bytes()
                    thumb_resp = httpx.post(
                        f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set"
                        f"?videoId={video_id}&uploadType=media",
                        headers={
                            "Authorization": f"Bearer {access_token}",
                            "Content-Type":  "image/jpeg",
                            "Content-Length": str(len(thumb_data)),
                        },
                        content=thumb_data,
                        timeout=60,
                    )
                    if thumb_resp.status_code in (200, 204):
                        log(f"  🖼️  Thumbnail uploaded")
                    else:
                        log(f"  ⚠️  Thumbnail upload failed: {thumb_resp.status_code}")
                    thumb_path.unlink(missing_ok=True)
                except Exception as e:
                    log(f"  ⚠️  Thumbnail skipped: {e}")

                # Try to add to relevant playlist (by specialty/modality)
                playlists = json.load(open(PLAYLISTS_FILE)) if PLAYLISTS_FILE.exists() else {}
                playlist_id = (playlists.get(specialty) or
                               playlists.get(modality) or
                               playlists.get("diagnostics"))
                if playlist_id:
                    add_video_to_playlist(video_id, playlist_id, access_token)
                    log(f"  📂 Added to playlist")

                uploaded[img_id] = {
                    "video_id":    video_id,
                    "uploaded_at": datetime.now(timezone.utc).isoformat(),
                    "title":       title,
                    "modality":    modality,
                }
                save_uploaded(uploaded)
                mp4.unlink(missing_ok=True)
                success += 1

        except Exception as e:
            log(f"  ❌ Error: {e}")

        if i < len(queue):
            log(f"  ⏳ Waiting {WAIT_BETWEEN}s…")
            await asyncio.sleep(WAIT_BETWEEN)

    log(f"\nDone. Uploaded {success}/{len(queue)} Shorts. Total: {len(uploaded)}")


def main():
    parser = argparse.ArgumentParser(description="MedMind Daily Shorts Upload")
    parser.add_argument("--limit",   type=int, default=DAILY_LIMIT)
    parser.add_argument("--lang",    type=str, default="en",
                        help="Language for titles/descriptions: en|es|ru|de (default: en)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.limit, args.dry_run, args.lang))


if __name__ == "__main__":
    main()
