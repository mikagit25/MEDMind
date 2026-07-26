"""
MedMind AI — YouTube Auto-Uploader

Generates MP4 from article and uploads to YouTube channel.

Setup (one-time):
    1. Put client_secret.json in /opt/medmind/
    2. Run: python3 youtube_uploader.py --auth
       → Opens browser, you login, saves token to youtube_token.json
    3. Then run normally:
       python3 youtube_uploader.py --slug atrial-fibrillation --lang en

Batch upload (top articles):
    python3 youtube_uploader.py --batch --limit 20 --lang en

Environment:
    MEDMIND_API_URL  — defaults to https://medmind.pro/api/v1
    YT_CLIENT_SECRET — path to client_secret JSON (default: /opt/medmind/client_secret.json)
    YT_TOKEN         — path to saved token (default: /opt/medmind/youtube_token.json)
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

import httpx

# ── Config ────────────────────────────────────────────────────────────────────

API_URL        = os.environ.get("MEDMIND_API_URL", "https://medmind.pro/api/v1")
CLIENT_SECRET  = Path(os.environ.get("YT_CLIENT_SECRET", "/opt/medmind/client_secret.json"))
TOKEN_FILE     = Path(os.environ.get("YT_TOKEN", "/opt/medmind/youtube_token.json"))
VIDEO_SCRIPT   = Path(__file__).parent / "article_to_video.py"

# YouTube category IDs: 27 = Education, 25 = News & Politics, 26 = Howto & Style
YT_CATEGORY    = "27"   # Education
YT_PRIVACY     = "public"   # public | unlisted | private

CHANNEL_DESCRIPTIONS = {
    "en": {
        "prefix": "🩺 MedMind AI — Evidence-based medical education powered by Claude AI & PubMed.\n\n",
        "suffix": (
            "\n\n🔗 Full article with sources: https://medmind.pro/articles/{slug}\n"
            "📚 Free medical learning platform: https://medmind.pro\n"
            "✅ 97+ modules | 7 languages | Clinical cases | AI Tutor\n\n"
            "#MedicalEducation #Medicine #MedMindAI #USMLE #MedStudent"
        ),
        "tags": ["medical education", "medicine", "medmind", "USMLE", "clinical medicine",
                 "medical student", "doctor", "healthcare", "AI tutor", "evidence based medicine"],
    },
    "es": {
        "prefix": "🩺 MedMind AI — Educación médica basada en evidencia con Claude AI y PubMed.\n\n",
        "suffix": (
            "\n\n🔗 Artículo completo con fuentes: https://medmind.pro/es/articles/{slug}\n"
            "📚 Plataforma gratuita de medicina: https://medmind.pro/es\n"
            "✅ 97+ módulos | 7 idiomas | Casos clínicos | Tutor IA\n\n"
            "#MedicinaEnEspañol #EducacionMedica #MedMindAI #USMLE #MIR #Medicina"
        ),
        "tags": ["medicina", "educación médica", "medmind", "USMLE", "MIR", "medicina clínica",
                 "estudiante de medicina", "farmacología", "tutor IA", "medicina basada en evidencia"],
    },
    "ru": {
        "prefix": "🩺 MedMind AI — Доказательное медицинское образование на основе Claude AI и PubMed.\n\n",
        "suffix": (
            "\n\n🔗 Полная статья с источниками: https://medmind.pro/ru/articles/{slug}\n"
            "📚 Бесплатная медицинская платформа: https://medmind.pro/ru\n"
            "✅ 97+ модулей | 7 языков | Клинические случаи | ИИ-тьютор\n\n"
            "#Медицина #МедицинскоеОбразование #MedMindAI #USMLE #Врач"
        ),
        "tags": ["медицина", "медицинское образование", "medmind", "врач", "клиническая медицина",
                 "медицинский студент", "ИИ тьютор", "доказательная медицина"],
    },
    "ar": {
        "prefix": "🩺 MedMind AI — التعليم الطبي المبني على الأدلة بتقنية Claude AI و PubMed.\n\n",
        "suffix": (
            "\n\n🔗 المقال الكامل مع المصادر: https://medmind.pro/ar/articles/{slug}\n"
            "📚 منصة طبية مجانية: https://medmind.pro/ar\n"
            "✅ أكثر من 97 وحدة | 7 لغات | حالات سريرية | مساعد ذكاء اصطناعي\n\n"
            "#التعليم_الطبي #الطب #MedMindAI #USMLE #طالب_طب"
        ),
        "tags": ["تعليم طبي", "الطب", "medmind", "USMLE", "الطب السريري",
                 "طالب طب", "دراسة الطب", "ذكاء اصطناعي طبي", "طب مبني على الأدلة"],
    },
    "de": {
        "prefix": "🩺 MedMind AI — Evidenzbasierte medizinische Weiterbildung mit Claude AI & PubMed.\n\n",
        "suffix": (
            "\n\n🔗 Vollständiger Artikel mit Quellen: https://medmind.pro/de/articles/{slug}\n"
            "📚 Kostenlose Medizinplattform: https://medmind.pro/de\n"
            "✅ 97+ Module | 7 Sprachen | Klinische Fälle | KI-Tutor\n\n"
            "#Medizin #Medizinstudium #MedMindAI #USMLE #Arzt #Medizinstudent"
        ),
        "tags": ["Medizin", "Medizinstudium", "medmind", "USMLE", "klinische Medizin",
                 "Medizinstudent", "Arzt", "Gesundheitswesen", "KI Tutor", "evidenzbasierte Medizin"],
    },
    "fr": {
        "prefix": "🩺 MedMind AI — Formation médicale fondée sur les preuves avec Claude AI & PubMed.\n\n",
        "suffix": (
            "\n\n🔗 Article complet avec sources: https://medmind.pro/fr/articles/{slug}\n"
            "📚 Plateforme médicale gratuite: https://medmind.pro/fr\n"
            "✅ 97+ modules | 7 langues | Cas cliniques | Tuteur IA\n\n"
            "#Médecine #ÉducationMédicale #MedMindAI #USMLE #ÉtudiantMédecine"
        ),
        "tags": ["médecine", "éducation médicale", "medmind", "USMLE", "médecine clinique",
                 "étudiant en médecine", "médecin", "santé", "tuteur IA", "médecine fondée sur les preuves"],
    },
    "tr": {
        "prefix": "🩺 MedMind AI — Claude AI & PubMed destekli kanıta dayalı tıp eğitimi.\n\n",
        "suffix": (
            "\n\n🔗 Kaynaklı tam makale: https://medmind.pro/tr/articles/{slug}\n"
            "📚 Ücretsiz tıp platformu: https://medmind.pro/tr\n"
            "✅ 97+ modül | 7 dil | Klinik vakalar | Yapay Zeka Öğretmeni\n\n"
            "#Tıp #TıpEğitimi #MedMindAI #USMLE #TıpÖğrencisi"
        ),
        "tags": ["tıp", "tıp eğitimi", "medmind", "USMLE", "klinik tıp",
                 "tıp öğrencisi", "doktor", "sağlık", "yapay zeka", "kanıta dayalı tıp"],
    },
}

CHANNEL_DESCRIPTIONS_NEWS: dict[str, dict] = {
    "en": {
        "prefix": "📰 MedMind AI — Latest medical news & research breakthroughs.\n\n",
        "suffix": (
            "\n\n🔗 Full news article: https://medmind.pro/news/{slug}\n"
            "📚 Free medical learning platform: https://medmind.pro\n"
            "✅ 97+ modules | 7 languages | Clinical cases | AI Tutor\n\n"
            "#MedicalNews #Medicine #MedMindAI #HealthNews #MedStudent #Research"
        ),
        "tags": ["medical news", "medicine", "medmind", "health news",
                 "medical research", "clinical medicine", "USMLE", "MedMindAI"],
    },
    "es": {
        "prefix": "📰 MedMind AI — Últimas noticias y avances en investigación médica.\n\n",
        "suffix": (
            "\n\n🔗 Artículo completo: https://medmind.pro/es/news/{slug}\n"
            "📚 Plataforma médica gratuita: https://medmind.pro/es\n"
            "✅ 97+ módulos | 7 idiomas | Casos clínicos | Tutor IA\n\n"
            "#NoticiasMédicas #Medicina #MedMindAI #InvestigaciónMédica #Salud"
        ),
        "tags": ["noticias médicas", "medicina", "medmind", "investigación médica",
                 "salud", "USMLE", "MIR", "MedMindAI"],
    },
    "ar": {
        "prefix": "📰 MedMind AI — آخر الأخبار والاكتشافات الطبية.\n\n",
        "suffix": (
            "\n\n🔗 المقال الكامل: https://medmind.pro/ar/news/{slug}\n"
            "📚 منصة طبية مجانية: https://medmind.pro/ar\n"
            "✅ أكثر من 97 وحدة | 7 لغات | حالات سريرية | مساعد ذكاء اصطناعي\n\n"
            "#أخبار_طبية #الطب #MedMindAI #أبحاث_طبية #طالب_طب"
        ),
        "tags": ["أخبار طبية", "الطب", "medmind", "أبحاث طبية",
                 "أخبار الصحة", "الطب السريري", "USMLE", "MedMindAI"],
    },
    "de": {
        "prefix": "📰 MedMind AI — Aktuelle Medizinnachrichten & Forschungsdurchbrüche.\n\n",
        "suffix": (
            "\n\n🔗 Vollständiger Artikel: https://medmind.pro/de/news/{slug}\n"
            "📚 Kostenlose Medizinplattform: https://medmind.pro/de\n"
            "✅ 97+ Module | 7 Sprachen | Klinische Fälle | KI-Tutor\n\n"
            "#Medizinnews #Medizin #MedMindAI #Gesundheit #Medizinstudent"
        ),
        "tags": ["Medizinnachrichten", "Medizin", "medmind", "Gesundheit",
                 "Medizinstudent", "USMLE", "MedMindAI"],
    },
    "fr": {
        "prefix": "📰 MedMind AI — Actualités médicales et avancées de la recherche.\n\n",
        "suffix": (
            "\n\n🔗 Article complet: https://medmind.pro/fr/news/{slug}\n"
            "📚 Plateforme médicale gratuite: https://medmind.pro/fr\n"
            "✅ 97+ modules | 7 langues | Cas cliniques | Tuteur IA\n\n"
            "#ActualitésMédicales #Médecine #MedMindAI #Santé #ÉtudiantMédecine"
        ),
        "tags": ["actualités médicales", "médecine", "medmind", "santé",
                 "recherche médicale", "USMLE", "MedMindAI"],
    },
    "ru": {
        "prefix": "📰 MedMind AI — Последние медицинские новости и открытия.\n\n",
        "suffix": (
            "\n\n🔗 Полная статья: https://medmind.pro/ru/news/{slug}\n"
            "📚 Бесплатная медицинская платформа: https://medmind.pro/ru\n"
            "✅ 97+ модулей | 7 языков | Клинические случаи | ИИ-тьютор\n\n"
            "#МедицинскиеНовости #Медицина #MedMindAI #Здоровье #Врач"
        ),
        "tags": ["медицинские новости", "медицина", "medmind", "здоровье",
                 "медицинские исследования", "USMLE", "MedMindAI"],
    },
    "tr": {
        "prefix": "📰 MedMind AI — Son tıp haberleri ve araştırma gelişmeleri.\n\n",
        "suffix": (
            "\n\n🔗 Tam makale: https://medmind.pro/tr/news/{slug}\n"
            "📚 Ücretsiz tıp platformu: https://medmind.pro/tr\n"
            "✅ 97+ modül | 7 dil | Klinik vakalar | Yapay Zeka Öğretmeni\n\n"
            "#TıpHaberleri #Tıp #MedMindAI #Sağlık #TıpÖğrencisi"
        ),
        "tags": ["tıp haberleri", "tıp", "medmind", "sağlık",
                 "tıp araştırması", "USMLE", "MedMindAI"],
    },
}


# ── OAuth helpers ─────────────────────────────────────────────────────────────

def load_client_secret() -> dict:
    if not CLIENT_SECRET.exists():
        print(f"❌ client_secret.json not found at {CLIENT_SECRET}")
        print("Download it from Google Cloud Console → APIs & Services → Credentials")
        sys.exit(1)
    with open(CLIENT_SECRET) as f:
        data = json.load(f)
    return data.get("installed") or data.get("web") or data


def load_token() -> dict | None:
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE) as f:
            return json.load(f)
    return None


def save_token(token: dict):
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
        json.dump(token, f, indent=2)
    print(f"✅ Token saved to {TOKEN_FILE}")


def _token_expires_at(token: dict) -> float:
    """Handle both our format (expires_at) and Google-auth format (expiry)."""
    if token.get("expires_at"):
        return float(token["expires_at"])
    if token.get("expiry"):
        try:
            import datetime as _dt
            dt = _dt.datetime.fromisoformat(token["expiry"].replace("Z", "+00:00"))
            return dt.timestamp()
        except Exception:
            pass
    return 0.0

def _token_creds(token: dict, secret: dict) -> dict:
    """Use credentials embedded in Google-auth token if present."""
    if token.get("client_id") and token.get("client_secret"):
        return {"client_id": token["client_id"], "client_secret": token["client_secret"]}
    return secret

def refresh_access_token(token: dict, secret: dict) -> dict:
    creds = _token_creds(token, secret)
    resp = httpx.post("https://oauth2.googleapis.com/token", data={
        "client_id":     creds["client_id"],
        "client_secret": creds["client_secret"],
        "refresh_token": token["refresh_token"],
        "grant_type":    "refresh_token",
    })
    if resp.status_code in (400, 401):
        # Refresh token revoked or expired — need full re-auth
        raise TokenRevokedException(resp.text)
    resp.raise_for_status()
    new_token = {**token, **resp.json()}
    save_token(new_token)
    return new_token


class TokenRevokedException(Exception):
    pass


def do_auth_flow(secret: dict) -> dict:
    """
    Headless OAuth flow — prints URL, user opens in browser,
    pastes the redirect URL (or just the code) back into terminal.
    Works on servers without a browser.
    """
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

    print("\n" + "="*60)
    print("STEP 1: Open this URL in your browser (on any device):")
    print("="*60)
    print(auth_url)
    print("="*60)
    print("\nSTEP 2: Log in with the Google account that owns MedMindAI-en")
    print("STEP 3: After clicking Allow, browser goes to localhost (will show error — that's OK)")
    print("STEP 4: Copy the FULL URL from browser address bar and paste below")
    print("        It looks like: http://localhost/?code=4/0AX4XfW...&scope=...\n")

    raw = input("Paste the full redirect URL here: ").strip()

    # Extract code from URL or accept raw code
    if raw.startswith("http"):
        params = urllib.parse.parse_qs(urllib.parse.urlparse(raw).query)
        code = params.get("code", [None])[0]
    else:
        code = raw  # user pasted just the code

    if not code:
        print("❌ Could not extract auth code. Try again.")
        sys.exit(1)

    print("Exchanging code for token…")
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


def get_valid_token() -> tuple[str, dict]:
    """Return (access_token, token_dict). Refreshes if expired."""
    secret = load_client_secret()
    token  = load_token()

    if not token:
        print("No token found. Running auth flow…")
        token = do_auth_flow(secret)

    if time.time() >= _token_expires_at(token) - 60:
        print("Token expired, refreshing…")
        try:
            token = refresh_access_token(token, secret)
            token["expires_at"] = time.time() + token.get("expires_in", 3600)
            save_token(token)
        except TokenRevokedException:
            print("⚠️  Refresh token revoked by Google. Re-authorizing…")
            token = do_auth_flow(secret)

    return token.get("access_token") or token.get("token"), token


# ── Video generation ──────────────────────────────────────────────────────────

async def generate_video(slug: str, lang: str, output_dir: Path) -> Path | None:
    """Run article_to_video.py and return path to generated MP4."""
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable, str(VIDEO_SCRIPT),
        "--slug", slug,
        "--lang", lang,
        "--output", str(output_dir),
    ]
    print(f"\n🎬 Generating video: {slug} [{lang}]")
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(VIDEO_SCRIPT.parent.parent))

    if result.returncode != 0:
        print(f"❌ Video generation failed:\n{result.stderr[-500:]}")
        return None

    # Find generated MP4
    safe_slug = slug.replace("/", "-")[:80]
    lang_suffix = "" if lang == "en" else f"_{lang}"
    mp4 = output_dir / f"{safe_slug}{lang_suffix}.mp4"
    if mp4.exists():
        print(f"✅ Video ready: {mp4} ({mp4.stat().st_size // 1_048_576} MB)")
        return mp4

    # Fallback: find any MP4
    mp4s = list(output_dir.glob("*.mp4"))
    if mp4s:
        mp4s.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return mp4s[0]

    print("❌ MP4 not found after generation")
    return None


# ── YouTube upload ────────────────────────────────────────────────────────────

def upload_thumbnail(video_id: str, thumb_path: Path, access_token: str) -> bool:
    """Upload custom thumbnail for a video."""
    try:
        data = thumb_path.read_bytes()
        resp = httpx.post(
            f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set"
            f"?videoId={video_id}&uploadType=media",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type":  "image/jpeg",
                "Content-Length": str(len(data)),
            },
            content=data,
            timeout=60,
        )
        if resp.status_code in (200, 204):
            print(f"🖼️  Thumbnail uploaded")
            return True
        else:
            print(f"  ⚠️  Thumbnail failed: {resp.status_code} {resp.text[:100]}")
            return False
    except Exception as e:
        print(f"  ⚠️  Thumbnail error: {e}")
        return False


def build_description(slug: str, excerpt: str, lang: str) -> str:
    import re
    tmpl = CHANNEL_DESCRIPTIONS.get(lang, CHANNEL_DESCRIPTIONS["en"])
    clean = re.sub(r"<[^>]+>", "", str(excerpt or ""))
    clean = clean.replace("<", "").replace(">", "").strip()
    return tmpl["prefix"] + clean + tmpl["suffix"].format(slug=slug)


def upload_to_youtube(
    mp4_path: Path,
    title: str,
    description: str,
    tags: list[str],
    access_token: str,
) -> str | None:
    """Upload MP4 to YouTube. Returns video ID on success."""
    # Step 1: initiate resumable upload
    metadata = {
        "snippet": {
            "title":       title[:100],
            "description": description[:5000],
            "tags":        tags[:500],
            "categoryId":  YT_CATEGORY,
        },
        "status": {
            "privacyStatus":          YT_PRIVACY,
            "selfDeclaredMadeForKids": False,
        },
    }

    file_size = mp4_path.stat().st_size
    init_resp = httpx.post(
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

    if init_resp.status_code != 200:
        print(f"❌ Upload init failed: {init_resp.status_code} {init_resp.text[:300]}")
        return None

    upload_url = init_resp.headers["Location"]

    # Step 2: upload file in chunks
    CHUNK = 10 * 1024 * 1024  # 10 MB chunks
    uploaded = 0

    with open(mp4_path, "rb") as f:
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
                timeout=300,
            )
            if resp.status_code in (200, 201):
                video_id = resp.json().get("id")
                print(f"✅ Uploaded! https://youtu.be/{video_id}")
                return video_id
            elif resp.status_code == 308:
                uploaded = end + 1
                pct = int(uploaded * 100 / file_size)
                print(f"   Uploading… {pct}%", end="\r")
            else:
                print(f"❌ Upload chunk failed: {resp.status_code} {resp.text[:200]}")
                return None

    return None


# ── Fetch article info ────────────────────────────────────────────────────────

def fetch_article(slug: str, lang: str = "en") -> dict | None:
    params = {"locale": lang} if lang != "en" else {}
    try:
        resp = httpx.get(f"{API_URL}/articles/{slug}", params=params, timeout=15)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"Warning: could not fetch article: {e}")
    return None


def fetch_top_slugs(limit: int = 20, lang: str = "en", page: int = 1) -> list[str]:
    try:
        resp = httpx.get(f"{API_URL}/articles", params={"limit": limit, "page": page}, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            articles = data.get("articles", data) if isinstance(data, dict) else data
            return [a["slug"] for a in articles[:limit]]
    except Exception as e:
        print(f"Warning: could not fetch articles list: {e}")
    return []


# ── Main ──────────────────────────────────────────────────────────────────────

def add_to_playlist(video_id: str, playlist_id: str, access_token: str) -> bool:
    """Add an uploaded video to a YouTube playlist."""
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
    if resp.status_code in (200, 201):
        return True
    print(f"  ⚠️  Playlist add failed: {resp.status_code} {resp.text[:100]}")
    return False


async def process_one(
    slug: str,
    lang: str,
    access_token: str,
    output_dir: Path,
    delete_after: bool = True,
    playlist_id: str | None = None,
) -> str | None:
    """Generate and upload one video. Returns video_id on success."""
    import tempfile
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        from generate_thumbnail import generate_thumbnail
        _thumb_available = True
    except ImportError:
        _thumb_available = False

    article = fetch_article(slug, lang)
    if not article:
        print(f"⚠️  Could not fetch article '{slug}', skipping")
        return None

    title        = article.get("title", slug)
    excerpt      = article.get("excerpt", "")
    category     = article.get("category", "diseases")
    reading_time = article.get("reading_time_minutes", 0)
    cover_url    = article.get("cover_image") or article.get("cover_image_url")
    tags         = CHANNEL_DESCRIPTIONS.get(lang, CHANNEL_DESCRIPTIONS["en"])["tags"] + [category]

    # Generate video
    mp4 = await generate_video(slug, lang, output_dir)
    if not mp4:
        return None

    # Refresh token right before upload — video generation can take 10+ min
    access_token, _ = get_valid_token()

    # Upload video
    description = build_description(slug, excerpt, lang)
    video_id    = upload_to_youtube(mp4, title, description, tags, access_token)

    if video_id:
        # Generate and upload thumbnail
        if _thumb_available:
            thumb_path = output_dir / f"{slug[:60]}_thumb.jpg"
            try:
                generate_thumbnail(title, category, lang, reading_time,
                                   out_path=thumb_path, cover_url=cover_url)
                upload_thumbnail(video_id, thumb_path, access_token)
                thumb_path.unlink(missing_ok=True)
            except Exception as e:
                print(f"  ⚠️  Thumbnail skipped: {e}")

        if delete_after:
            mp4.unlink(missing_ok=True)
            print(f"🗑️  Local file deleted")
        if playlist_id:
            ok = add_to_playlist(video_id, playlist_id, access_token)
            if ok:
                print(f"📂 Added to playlist")

    return video_id


async def process_news_one(
    slug: str,
    lang: str,
    access_token: str,
    output_dir: Path,
    delete_after: bool = True,
    playlist_id: str | None = None,
) -> str | None:
    """Generate and upload one news video. Returns video_id on success."""
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        from news_to_video import build_news_video, fetch_news_article
    except ImportError as e:
        print(f"  ❌ news_to_video import failed: {e}")
        return None

    _thumb_available = False
    try:
        from generate_thumbnail import generate_thumbnail
        _thumb_available = True
    except ImportError:
        pass

    news = fetch_news_article(slug, lang)
    if not news:
        print(f"⚠️  Could not fetch news '{slug}', skipping")
        return None

    title    = news.get("title", slug)
    category = news.get("category", "diseases")
    summary  = news.get("summary", "")
    tags_raw = news.get("tags") or []
    tmpl     = CHANNEL_DESCRIPTIONS_NEWS.get(lang, CHANNEL_DESCRIPTIONS_NEWS["en"])
    tags     = tmpl["tags"] + ([category] if category not in tmpl["tags"] else []) + tags_raw[:5]

    # Generate video
    safe_slug = "".join(c if c.isalnum() or c in "-_" else "_" for c in slug)
    suffix    = f"_{lang}" if lang != "en" else ""
    mp4       = output_dir / f"news_{safe_slug}{suffix}.mp4"
    print(f"  Generating news video for '{slug}' [{lang}]…")
    await build_news_video(news, mp4, lang)
    if not mp4.exists():
        print("❌ Video file not created")
        return None

    # Refresh token right before upload — video generation can take several minutes
    access_token, _ = get_valid_token()

    # Build YouTube description
    description = (
        tmpl["prefix"]
        + summary[:600]
        + ("…" if len(summary) > 600 else "")
        + tmpl["suffix"].format(slug=slug)
    )

    # Upload
    video_id = upload_to_youtube(mp4, title, description, tags, access_token)

    if video_id:
        if _thumb_available:
            thumb_path = output_dir / f"news_thumb_{safe_slug}.jpg"
            try:
                generate_thumbnail(title, category, lang,
                                   out_path=thumb_path, cover_url=None)
                upload_thumbnail(video_id, thumb_path, access_token)
                thumb_path.unlink(missing_ok=True)
            except Exception as e:
                print(f"  ⚠️  Thumbnail skipped: {e}")

        if delete_after:
            mp4.unlink(missing_ok=True)
            print("🗑️  Local file deleted")

        if playlist_id:
            if add_to_playlist(video_id, playlist_id, access_token):
                print("📂 Added to playlist")

    return video_id


async def main():
    parser = argparse.ArgumentParser(description="MedMind YouTube Uploader")
    parser.add_argument("--auth",   action="store_true", help="Run OAuth flow to get token")
    parser.add_argument("--slug",   type=str, help="Single article slug to upload")
    parser.add_argument("--lang",   type=str, default="en", help="Language code (en|ru|de|fr|es|tr|ar)")
    parser.add_argument("--batch",  action="store_true", help="Upload top N articles")
    parser.add_argument("--limit",  type=int, default=10, help="Number of articles in batch")
    parser.add_argument("--page",   type=int, default=1, help="Page of articles to fetch (for multi-account)")
    parser.add_argument("--output", type=str, default="/tmp/medmind_videos", help="Video output dir")
    parser.add_argument("--keep",   action="store_true", help="Keep MP4 after upload")
    args = parser.parse_args()

    secret = load_client_secret()
    print(f"✅ client_secret.json loaded (client_id: {secret.get('client_id','?')[:30]}…)")

    if args.auth:
        token = do_auth_flow(secret)
        token["expires_at"] = time.time() + token.get("expires_in", 3600)
        save_token(token)
        print("\nNow run the upload command without --auth")
        return

    access_token, _ = get_valid_token()
    output_dir = Path(args.output)

    if args.slug:
        await process_one(args.slug, args.lang, access_token, output_dir, delete_after=not args.keep)

    elif args.batch:
        slugs = fetch_top_slugs(args.limit, args.lang, args.page)
        if not slugs:
            # Fallback: hardcoded top medical topics
            slugs = [
                "infective-endocarditis-understanding-bacterial-heart-valve-infections",
                "rheumatic-heart-disease-pathophysiology-clinical-management",
                "cardiac-syncope-mechanisms-recognition-and-clinical-management",
                "brugada-syndrome-genetics-diagnosis-and-management",
                "pulmonary-hypertension-pathophysiology-diagnosis-and-management",
                "long-qt-syndrome-understanding-cardiac-arrhythmia-risk",
                "wolff-parkinson-white-syndrome-pathophysiology-and-clinical-management",
                "aortic-regurgitation-pathophysiology-diagnosis-and-management",
                "cardiac-tamponade-pathophysiology-clinical-presentation-and-management",
                "tricuspid-regurgitation-pathophysiology-diagnosis-and-management",
            ][:args.limit]

        print(f"\n📋 Batch: {len(slugs)} videos [{args.lang}]\n")
        for i, slug in enumerate(slugs, 1):
            print(f"\n[{i}/{len(slugs)}] {slug}")
            await process_one(slug, args.lang, access_token, output_dir, delete_after=not args.keep)
            if i < len(slugs):
                print("⏳ Waiting 30s before next upload…")
                await asyncio.sleep(30)  # YouTube rate limit
    else:
        parser.print_help()


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    asyncio.run(main())
