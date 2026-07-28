#!/usr/bin/env python3
"""
MedMind AI — Daily Spanish NCLEX Q&A Shorts (ES channel)

Reads translated questions from nclex_shorts_translations (lang='es'),
renders 9:16 video, uploads to the Spanish YouTube account.

Tracking: /opt/medmind/youtube_shorts_nclex_es_uploaded.json
Cron:     10 12 * * *  (12:10 UTC)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import psycopg2
import psycopg2.extras

sys.path.insert(0, str(Path(__file__).parent))
from nclex_to_shorts import build_video, _save_tracking  # noqa: E402

DAILY_LIMIT  = 4
WAIT_BETWEEN = 45
LANG         = "es"
TTS_VOICE    = "es-US-PalomaNeural"

TOKEN_FILE   = Path(os.environ.get("YT_TOKEN",         "/opt/medmind/youtube_token_account2.json"))
SECRET_FILE  = Path(os.environ.get("YT_CLIENT_SECRET", "/opt/medmind/client_secret_account2_web.json"))
TRACKING_FILE = Path(os.environ.get("YT_NCLEX_ES_TRACKING",
                                    "/opt/medmind/youtube_shorts_nclex_es_uploaded.json"))

DB_URL = os.environ.get("DB_URL", "postgresql://medmind:medmind_secret@localhost:5432/medmind")

HASHTAGS = (
    "#NCLEX #EnfermeriaEstudiante #EnfermeriaEducacion #MedMindAI "
    "#ExamenEnfermeria #Shorts #Enfermeria #EstudioMedicina"
)


def _load_tracking() -> set[str]:
    if TRACKING_FILE.exists():
        try:
            data = json.loads(TRACKING_FILE.read_text())
            return set(data.get("uploaded", []))
        except Exception:
            pass
    return set()


def _save_es_tracking(question_id: str, yt_id: str | None = None):
    data: dict = {"uploaded": [], "details": {}}
    if TRACKING_FILE.exists():
        try:
            data = json.loads(TRACKING_FILE.read_text())
        except Exception:
            pass
    uploaded = list(data.get("uploaded", []))
    if question_id not in uploaded:
        uploaded.append(question_id)
    data["uploaded"] = uploaded
    if yt_id:
        data.setdefault("details", {})[question_id] = {"yt_id": yt_id}
    TRACKING_FILE.write_text(json.dumps(data, indent=2))


def fetch_questions(limit: int) -> list[dict]:
    uploaded = _load_tracking()
    sql = """
        SELECT t.question_id AS id, t.question, t.options, t.key_takeaway,
               q.correct, q.difficulty, m.title AS module_title
        FROM nclex_shorts_translations t
        JOIN mcq_questions q ON q.id::text = t.question_id
        LEFT JOIN modules m ON m.id = q.module_id
        WHERE t.lang = %s AND t.status = 'done'
        ORDER BY t.created_at ASC
        LIMIT %s
    """
    with psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (LANG, limit * 3))
            rows = [dict(r) for r in cur.fetchall()]
    return [r for r in rows if r["id"] not in uploaded][:limit]


def _yt_upload(mp4: str, title: str, description: str) -> str | None:
    try:
        import google.oauth2.credentials
        import googleapiclient.discovery
        import googleapiclient.http
    except ImportError:
        print("[error] google-api-python-client not installed")
        return None

    creds_data    = json.loads(TOKEN_FILE.read_text())
    client_id     = creds_data.get("client_id")
    client_secret = creds_data.get("client_secret")
    if (not client_id or not client_secret) and SECRET_FILE.exists():
        raw = json.loads(SECRET_FILE.read_text())
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
            "title":      title[:100],
            "description": description[:4900],
            "tags":       ["nclex", "enfermería", "examen enfermeria", "nursing student",
                           "medmind", "medicina", "shorts", "estudio medicina"],
            "categoryId": "27",
        },
        "status": {
            "privacyStatus":            "public",
            "selfDeclaredMadeForKids":  False,
        },
    }
    media = googleapiclient.http.MediaFileUpload(mp4, chunksize=-1, resumable=True, mimetype="video/mp4")
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        _, response = req.next_chunk()
    vid_id = response.get("id")

    # Refresh token if updated
    orig = creds_data.get("access_token") or creds_data.get("token")
    if creds.token and creds.token != orig:
        creds_data["access_token"] = creds.token
        creds_data["expires_at"] = time.time() + 3600
        TOKEN_FILE.write_text(json.dumps(creds_data, indent=2))
    return vid_id


def _make_title(q: dict) -> str:
    diff = q.get("difficulty", "medium").capitalize()
    module = (q.get("module_title") or "NCLEX")[:40]
    return f"🩺 Reto NCLEX: {module} ({diff}) #Shorts"[:100]


def _make_description(q: dict) -> str:
    opts = q["options"] if isinstance(q["options"], dict) else json.loads(q["options"])
    return (
        f"¿Puedes responder esta pregunta de NCLEX?\n\n"
        f"❓ {q['question'][:200]}\n\n"
        f"A) {opts.get('A', '')}\n"
        f"B) {opts.get('B', '')}\n"
        f"C) {opts.get('C', '')}\n"
        f"D) {opts.get('D', '')}\n\n"
        f"✅ Respuesta: {q['correct']}\n\n"
        f"💡 {q['key_takeaway'][:300]}\n\n"
        f"Practica más de 1,000 preguntas NCLEX GRATIS en:\n"
        f"🔗 https://medmind.pro/nclex\n\n"
        f"{HASHTAGS}"
    )


async def run(limit: int, dry_run: bool):
    questions = fetch_questions(limit)
    if not questions:
        print("✅ No new ES NCLEX questions to upload today.")
        return

    print(f"📋 Found {len(questions)} question(s) for ES channel (limit={limit})")

    if not TOKEN_FILE.exists() and not dry_run:
        print(f"[error] Token not found: {TOKEN_FILE}")
        sys.exit(1)

    uploaded_count = 0
    for i, q in enumerate(questions[:limit]):
        print(f"\n[{i+1}/{min(len(questions), limit)}] {q['question'][:60]}…")

        with tempfile.TemporaryDirectory() as tmp:
            mp4 = f"{tmp}/nclex_es_short.mp4"
            try:
                await build_video(q, mp4, dry_run=dry_run, lang=LANG, tts_voice=TTS_VOICE)
            except Exception as e:
                print(f"  ✗ Video build failed: {e}")
                continue

            title = _make_title(q)
            desc  = _make_description(q)
            print(f"  Title: {title}")

            if dry_run:
                print(f"  [dry-run] would upload")
                _save_es_tracking(q["id"])
                uploaded_count += 1
                continue

            yt_id = _yt_upload(mp4, title, desc)
            if yt_id:
                print(f"  ✅ Uploaded: https://youtu.be/{yt_id}")
                _save_es_tracking(q["id"], yt_id)
                uploaded_count += 1
            else:
                print(f"  ✗ Upload failed")

        if i < min(len(questions), limit) - 1:
            print(f"  Waiting {WAIT_BETWEEN}s…")
            time.sleep(WAIT_BETWEEN)

    print(f"\n{'='*50}")
    print(f"Done: {uploaded_count}/{min(len(questions), limit)} uploaded to ES channel")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit",   type=int, default=DAILY_LIMIT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(run(args.limit, args.dry_run))


if __name__ == "__main__":
    main()
