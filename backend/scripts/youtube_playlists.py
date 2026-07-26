#!/usr/bin/env python3
"""
MedMind AI — YouTube Playlist Manager

Creates one playlist per medical category on the MedMind AI channel.
Playlist IDs are saved to /opt/medmind/youtube_playlists.json.

Usage:
    python3 youtube_playlists.py --setup          # create all playlists
    python3 youtube_playlists.py --list           # show existing playlists
    python3 youtube_playlists.py --add VIDEO_ID CATEGORY  # add video to playlist
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx

# ── Config ─────────────────────────────────────────────────────────────────────
TOKEN_FILE    = Path(os.environ.get("YT_TOKEN",         "/opt/medmind/youtube_token.json"))
SECRET_FILE   = Path(os.environ.get("YT_CLIENT_SECRET", "/opt/medmind/client_secret.json"))
PLAYLISTS_FILE = Path(os.environ.get("YT_PLAYLISTS", "/opt/medmind/youtube_playlists.json"))

# category slug → (playlist title, description)
CATEGORY_PLAYLISTS: dict[str, tuple[str, str]] = {
    "cardiology":          ("Cardiology",                  "Heart diseases, arrhythmias, and cardiovascular medicine explained by MedMind AI."),
    "neurology":           ("Neurology",                   "Neurological conditions, brain disorders, and nervous system diseases."),
    "diseases":            ("Diseases & Conditions",       "Overview of major diseases, pathophysiology, and clinical management."),
    "drugs":               ("Pharmacology & Drugs",        "Drug mechanisms, indications, dosing, and side effects."),
    "pharmacology":        ("Pharmacology",                "Drug mechanisms, indications, dosing, and side effects."),
    "internal-medicine":   ("Internal Medicine",           "General internal medicine — systemic diseases and clinical approach."),
    "emergency":           ("Emergency Medicine",          "Emergency conditions, acute management, and critical care."),
    "pediatrics":          ("Pediatrics",                  "Childhood diseases, pediatric development, and child health."),
    "surgery":             ("Surgery",                     "Surgical conditions, techniques, and perioperative care."),
    "ob-gyn":              ("Obstetrics & Gynecology",     "Pregnancy, childbirth, and women's reproductive health."),
    "oncology":            ("Oncology",                    "Cancer biology, treatment, and clinical oncology."),
    "psychiatry":          ("Psychiatry & Mental Health",  "Mental health disorders, psychopharmacology, and therapy."),
    "endocrinology":       ("Endocrinology & Metabolism",  "Hormonal disorders, diabetes, thyroid, and metabolic diseases."),
    "infectious-diseases": ("Infectious Diseases",         "Bacteria, viruses, fungi, parasites — infections explained."),
    "diagnostics":         ("Diagnostics & Imaging",       "Lab tests, imaging studies, and diagnostic reasoning."),
    "procedures":          ("Medical Procedures",          "Clinical procedures, techniques, and step-by-step guides."),
    "symptoms":            ("Clinical Symptoms",           "Common symptoms — differential diagnosis and clinical approach."),
    "nutrition":           ("Nutrition & Lifestyle",       "Nutrition science, dietary guidelines, and preventive medicine."),
}

CATEGORY_PLAYLISTS_ES: dict[str, tuple[str, str]] = {
    "cardiology":          ("Cardiología",                 "Enfermedades del corazón, arritmias y medicina cardiovascular explicadas por MedMind AI."),
    "neurology":           ("Neurología",                  "Enfermedades neurológicas, trastornos cerebrales y del sistema nervioso."),
    "diseases":            ("Enfermedades y Condiciones",  "Principales enfermedades, fisiopatología y manejo clínico."),
    "drugs":               ("Farmacología y Medicamentos", "Mecanismos, indicaciones, dosis y efectos secundarios de los fármacos."),
    "pharmacology":        ("Farmacología",                "Mecanismos, indicaciones, dosis y efectos secundarios de los fármacos."),
    "internal-medicine":   ("Medicina Interna",            "Medicina interna general: enfermedades sistémicas y enfoque clínico."),
    "emergency":           ("Medicina de Urgencias",       "Situaciones de urgencia, manejo agudo y cuidados críticos."),
    "pediatrics":          ("Pediatría",                   "Enfermedades infantiles, desarrollo pediátrico y salud del niño."),
    "surgery":             ("Cirugía",                     "Condiciones quirúrgicas, técnicas y cuidados perioperatorios."),
    "ob-gyn":              ("Obstetricia y Ginecología",   "Embarazo, parto y salud reproductiva femenina."),
    "oncology":            ("Oncología",                   "Biología del cáncer, tratamiento y oncología clínica."),
    "psychiatry":          ("Psiquiatría y Salud Mental",  "Trastornos de salud mental, psicofarmacología y terapia."),
    "endocrinology":       ("Endocrinología y Metabolismo","Trastornos hormonales, diabetes, tiroides y enfermedades metabólicas."),
    "infectious-diseases": ("Enfermedades Infecciosas",    "Bacterias, virus, hongos, parásitos: infecciones explicadas."),
    "diagnostics":         ("Diagnóstico e Imagen",        "Análisis de laboratorio, estudios de imagen y razonamiento diagnóstico."),
    "procedures":          ("Procedimientos Médicos",      "Procedimientos clínicos, técnicas y guías paso a paso."),
    "symptoms":            ("Síntomas Clínicos",           "Síntomas comunes: diagnóstico diferencial y enfoque clínico."),
    "nutrition":           ("Nutrición y Estilo de Vida",  "Ciencia de la nutrición, guías dietéticas y medicina preventiva."),
}

PLAYLIST_DESCRIPTION_SUFFIX = {
    "en": (
        "\n\n🔗 Full articles with sources: https://medmind.pro/articles\n"
        "📚 Free medical learning platform: https://medmind.pro\n"
        "✅ 100+ modules | 7 languages | Clinical cases | AI Tutor\n"
        "#MedicalEducation #MedMindAI #USMLE"
    ),
    "es": (
        "\n\n🔗 Artículos completos: https://medmind.pro/articles\n"
        "📚 Plataforma médica gratuita: https://medmind.pro\n"
        "✅ 100+ módulos | 7 idiomas | Casos clínicos | Tutor IA\n"
        "#MedicinaEnEspañol #EducacionMedica #MedMindAI #USMLE #MIR"
    ),
}


# ── Auth helpers ───────────────────────────────────────────────────────────────

def load_token() -> dict:
    with open(TOKEN_FILE) as f:
        return json.load(f)

def load_secret() -> dict:
    with open(SECRET_FILE) as f:
        d = json.load(f)
    return d.get("installed") or d.get("web") or d

def save_token(token: dict):
    with open(TOKEN_FILE, "w") as f:
        json.dump(token, f, indent=2)

def _token_expires_at(token: dict) -> float:
    """Return unix timestamp when token expires. Handles both our format and Google-auth format."""
    if token.get("expires_at"):
        return float(token["expires_at"])
    if token.get("expiry"):
        try:
            from datetime import datetime, timezone
            dt = datetime.fromisoformat(token["expiry"].replace("Z", "+00:00"))
            return dt.timestamp()
        except Exception:
            pass
    return 0.0

def _token_credentials(token: dict, secret: dict) -> dict:
    """Return {client_id, client_secret} — prefer embedded creds from Google-auth token."""
    if token.get("client_id") and token.get("client_secret"):
        return {"client_id": token["client_id"], "client_secret": token["client_secret"]}
    return secret

def get_access_token() -> str:
    token  = load_token()
    secret = load_secret()
    if time.time() >= _token_expires_at(token) - 60:
        creds = _token_credentials(token, secret)
        resp = httpx.post("https://oauth2.googleapis.com/token", data={
            "client_id":     creds["client_id"],
            "client_secret": creds["client_secret"],
            "refresh_token": token["refresh_token"],
            "grant_type":    "refresh_token",
        })
        resp.raise_for_status()
        token = {**token, **resp.json()}
        token["expires_at"] = time.time() + token.get("expires_in", 3600)
        save_token(token)
    return token.get("access_token") or token.get("token")


# ── Playlist file helpers ──────────────────────────────────────────────────────

def load_playlists() -> dict[str, str]:
    """Load {category: playlist_id} mapping."""
    if PLAYLISTS_FILE.exists():
        try:
            content = PLAYLISTS_FILE.read_text().strip()
            return json.loads(content) if content else {}
        except (json.JSONDecodeError, ValueError):
            return {}
    return {}

def save_playlists(data: dict[str, str]):
    with open(PLAYLISTS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_playlist_id(category: str) -> str | None:
    """Return playlist_id for a given article category, or None."""
    return load_playlists().get(category)


# ── YouTube API ────────────────────────────────────────────────────────────────

def create_playlist(title: str, description: str, access_token: str) -> str | None:
    """Create a public playlist and return its ID."""
    resp = httpx.post(
        "https://www.googleapis.com/youtube/v3/playlists?part=snippet,status",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        content=json.dumps({
            "snippet": {
                "title":       title[:150],
                "description": description[:5000],
            },
            "status": {"privacyStatus": "public"},
        }).encode(),
        timeout=20,
    )
    if resp.status_code in (200, 201):
        pid = resp.json()["id"]
        print(f"  ✅ Created: '{title}' → {pid}")
        return pid
    print(f"  ❌ Failed to create '{title}': {resp.status_code} {resp.text[:200]}")
    return None


def list_channel_playlists(access_token: str) -> list[dict]:
    """Fetch all playlists on the authenticated channel."""
    playlists = []
    page_token = ""
    while True:
        params: dict = {"part": "snippet", "mine": "true", "maxResults": "50"}
        if page_token:
            params["pageToken"] = page_token
        resp = httpx.get(
            "https://www.googleapis.com/youtube/v3/playlists",
            params=params,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        playlists.extend(data.get("items", []))
        page_token = data.get("nextPageToken", "")
        if not page_token:
            break
    return playlists


def add_video_to_playlist(video_id: str, playlist_id: str, access_token: str) -> bool:
    """Add a video to a playlist. Returns True on success."""
    resp = httpx.post(
        "https://www.googleapis.com/youtube/v3/playlistItems?part=snippet",
        headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
        content=json.dumps({
            "snippet": {
                "playlistId": playlist_id,
                "resourceId": {"kind": "youtube#video", "videoId": video_id},
            }
        }).encode(),
        timeout=15,
    )
    return resp.status_code in (200, 201)


# ── Commands ───────────────────────────────────────────────────────────────────

def cmd_setup(access_token: str, lang: str = "en"):
    """Create all category playlists that don't exist yet."""
    playlists = load_playlists()
    category_map = CATEGORY_PLAYLISTS_ES if lang == "es" else CATEGORY_PLAYLISTS
    suffix = PLAYLIST_DESCRIPTION_SUFFIX.get(lang, PLAYLIST_DESCRIPTION_SUFFIX["en"])

    print("Fetching existing channel playlists…")
    existing = list_channel_playlists(access_token)
    existing_by_title = {p["snippet"]["title"]: p["id"] for p in existing}
    print(f"Found {len(existing)} existing playlists on channel")

    created = 0
    for category, (title, description) in category_map.items():
        if category in playlists:
            print(f"  ✓  '{title}' — already mapped ({playlists[category]})")
            continue
        if title in existing_by_title:
            pid = existing_by_title[title]
            playlists[category] = pid
            print(f"  ✓  '{title}' — found on channel ({pid})")
            continue
        pid = create_playlist(title, description + suffix, access_token)
        if pid:
            playlists[category] = pid
            created += 1
        time.sleep(0.5)

    save_playlists(playlists)
    print(f"\n✅ Done. {created} new playlists created. Total mapped: {len(playlists)}")
    print(f"   Saved to {PLAYLISTS_FILE}")


def cmd_list(access_token: str):
    """List all playlists currently on the channel."""
    playlists = list_channel_playlists(access_token)
    mapping   = load_playlists()
    reverse   = {v: k for k, v in mapping.items()}

    print(f"\n📋 Channel playlists ({len(playlists)} total):\n")
    for p in playlists:
        pid   = p["id"]
        title = p["snippet"]["title"]
        cat   = reverse.get(pid, "—")
        print(f"  [{cat:20s}] {title}  ({pid})")


def cmd_add(video_id: str, category: str, access_token: str):
    """Add a video to the playlist for a given category."""
    pid = get_playlist_id(category)
    if not pid:
        print(f"❌ No playlist mapped for category '{category}'")
        print("   Run --setup first")
        sys.exit(1)
    ok = add_video_to_playlist(video_id, pid, access_token)
    if ok:
        print(f"✅ Added {video_id} to playlist {pid} ({category})")
    else:
        print(f"❌ Failed to add {video_id} to playlist {pid}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="MedMind YouTube Playlist Manager")
    parser.add_argument("--setup", action="store_true", help="Create all category playlists")
    parser.add_argument("--list",  action="store_true", help="List channel playlists")
    parser.add_argument("--add",   nargs=2, metavar=("VIDEO_ID", "CATEGORY"),
                        help="Add video to playlist for category")
    parser.add_argument("--lang",  default="en", help="Language for playlist titles (en/es)")
    args = parser.parse_args()

    if not (args.setup or args.list or args.add):
        parser.print_help()
        return

    print("🔑 Authenticating…")
    access_token = get_access_token()

    if args.setup:
        cmd_setup(access_token, lang=args.lang)
    elif args.list:
        cmd_list(access_token)
    elif args.add:
        cmd_add(args.add[0], args.add[1], access_token)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    main()
