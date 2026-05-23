"""
Полная настройка испанского YouTube канала MedMind AI:
  - Описание канала (SEO-оптимизированное, подробное)
  - Ключевые слова / теги
  - Язык, страна
  - Загрузка баннера через YouTube API
  - Инструкции по ручной загрузке аватара

Запуск:
    python3 setup_channel_es.py
"""
import json, httpx, time
from pathlib import Path

SECRET_FILE = "/opt/medmind/client_secret_account2.json"
TOKEN_FILE  = "/opt/medmind/youtube_token_account2.json"
AVATAR      = "/opt/medmind/channel_art/avatar_es.png"
BANNER      = "/opt/medmind/channel_art/banner_es.png"

# ── Описание канала — максимально подробное, SEO под YouTube алгоритмы ───────
DESCRIPTION = """\
🩺 MedMind AI — Educacion Medica en Espanol | Basada en Evidencia

Videos diarios de medicina clinica, farmacologia, casos clinicos e imagenes medicas generados con Claude AI + PubMed.

Cardiology, Neurologia, Farmacologia, Medicina Interna, Oncologia, Endocrinologia, Enfermedades Infecciosas, Psiquiatria, Pediatria, Cirugia, Urgencias, Radiologia, Anatomia.

Preparacion: USMLE | MIR | ENARM | EUNACOM

Para: estudiantes de medicina, residentes, medicos generales y especialistas.

Plataforma gratuita: https://medmind.pro
600+ articulos | 100+ modulos | Casos clinicos | Tutor IA | 7 idiomas

#MedicinaEnEspanol #EducacionMedica #MedMindAI #USMLE #MIR #ENARM
"""

# ── Keywords para el algoritmo de YouTube (5000 caracteres max) ──────────────
KEYWORDS = (
    '"medicina en español" "educación médica" "medmind" "MedMind AI" '
    '"USMLE" "MIR" "ENARM" "EUNACOM" "medicina" "farmacología" '
    '"cardiología" "neurología" "medicina interna" "oncología" '
    '"endocrinología" "enfermedades infecciosas" "psiquiatría" '
    '"pediatría" "cirugía" "urgencias" "radiología" '
    '"diagnóstico diferencial" "casos clínicos" "imágenes médicas" '
    '"estudiante de medicina" "residente médico" "médico general" '
    '"medicina basada en evidencia" "PubMed" "Claude AI" '
    '"anatomía" "fisiología" "histología" "patología" '
    '"shorts médicos" "medicina shorts" "farmacología clínica" '
    '"tratamiento médico" "diagnóstico médico" "enfermedades" '
    '"salud" "ciencias de la salud" "medicina comparada" '
    '"veterinaria" "enfermería" "pregrado medicina" '
    '"especialidades médicas" "board review" "medicina 2024" '
    '"aprende medicina" "clases de medicina" "medicina gratis"'
)


# ── Auth ------------------------------------------------------------──────────
def get_access_token() -> str:
    with open(TOKEN_FILE) as f:
        token = json.load(f)
    with open(SECRET_FILE) as f:
        d = json.load(f)
    secret = d.get("installed") or d.get("web") or d

    # Use credentials embedded in token (Google-auth format) if available
    client_id     = token.get("client_id")     or secret["client_id"]
    client_secret = token.get("client_secret") or secret["client_secret"]

    resp = httpx.post("https://oauth2.googleapis.com/token", data={
        "client_id":     client_id,
        "client_secret": client_secret,
        "refresh_token": token["refresh_token"],
        "grant_type":    "refresh_token",
    }, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data.get("access_token") or token.get("token")


def get_channel(access_token: str) -> dict:
    resp = httpx.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={"part": "id,snippet,statistics", "mine": "true"},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    items = resp.json().get("items", [])
    if not items:
        raise RuntimeError("Канал не найден — проверь токен")
    ch = items[0]
    print(f"✓ Канал: {ch['snippet']['title']}  (ID: {ch['id']})")
    stats = ch.get("statistics", {})
    print(f"  Subscribers: {stats.get('subscriberCount','?')} | "
          f"Views: {stats.get('viewCount','?')} | "
          f"Videos: {stats.get('videoCount','?')}")
    return ch


def _clean(text: str) -> str:
    """Strip characters rejected by YouTube API (box-drawing, special Unicode blocks)."""
    import re
    # Remove box-drawing (U+2500–U+257F) and block elements (U+2580–U+259F)
    return re.sub(r"[─-▟]", "-", text)

def update_channel_metadata(access_token: str, channel_id: str):
    """Update description, keywords, language, country."""
    desc = _clean(DESCRIPTION)
    kw   = _clean(KEYWORDS).replace('"', '')   # strip quotes from keywords
    body = {
        "id": channel_id,
        "brandingSettings": {
            "channel": {
                "title":       "MedMind AI",
                "description": desc[:5000],
                "keywords":    kw[:500],
                "country":     "ES",
            }
        },
    }
    resp = httpx.put(
        "https://www.googleapis.com/youtube/v3/channels?part=brandingSettings",
        headers={"Authorization": f"Bearer {access_token}",
                 "Content-Type": "application/json"},
        content=json.dumps(body).encode(),
        timeout=20,
    )
    if resp.status_code in (200, 204):
        print("✓ Описание, ключевые слова, страна (ES) — обновлено")
    else:
        print(f"⚠️  brandingSettings: {resp.status_code} — {resp.text[:300]}")


def upload_banner(access_token: str, channel_id: str):
    """Upload banner via resumable upload, then link to channel."""
    banner_path = Path(BANNER)
    if not banner_path.exists():
        print(f"⚠️  Баннер не найден: {BANNER}")
        return

    data      = banner_path.read_bytes()
    file_size = len(data)
    print(f"→ Загружаем баннер ({file_size // 1024} KB)…")

    # Step 1: Initiate resumable upload
    init = httpx.post(
        "https://www.googleapis.com/upload/youtube/v3/channelBanners/insert"
        "?uploadType=resumable",
        headers={
            "Authorization":           f"Bearer {access_token}",
            "Content-Type":            "application/json",
            "X-Upload-Content-Type":   "image/png",
            "X-Upload-Content-Length": str(file_size),
        },
        content=b"{}",
        timeout=20,
    )
    if init.status_code != 200:
        print(f"⚠️  Banner init failed: {init.status_code} — {init.text[:300]}")
        return

    upload_url = init.headers.get("Location", "")
    if not upload_url:
        print("⚠️  No upload URL in response")
        return

    # Step 2: Upload the image bytes
    upload_resp = httpx.put(
        upload_url,
        headers={
            "Authorization":  f"Bearer {access_token}",
            "Content-Type":   "image/png",
            "Content-Length": str(file_size),
        },
        content=data,
        timeout=120,
    )
    if upload_resp.status_code not in (200, 201):
        print(f"⚠️  Banner upload failed: {upload_resp.status_code} — {upload_resp.text[:300]}")
        return

    banner_url = upload_resp.json().get("url", "")
    print(f"✓ Баннер загружен → {banner_url[:70]}…")

    # Step 3: Link banner URL to channel
    if banner_url:
        link_resp = httpx.put(
            "https://www.googleapis.com/youtube/v3/channels?part=brandingSettings",
            headers={"Authorization": f"Bearer {access_token}",
                     "Content-Type":  "application/json"},
            content=json.dumps({
                "id": channel_id,
                "brandingSettings": {
                    "channel": {"title": "MedMind AI"},
                    "image":   {"bannerExternalUrl": banner_url},
                }
            }).encode(),
            timeout=20,
        )
        if link_resp.status_code in (200, 204):
            print("✓ Баннер привязан к каналу")
        else:
            print(f"⚠️  Banner link: {link_resp.status_code} — {link_resp.text[:200]}")


def print_final_instructions():
    print(f"""
╔══════════════════════════════════════════════════════════╗
║          ОСТАЛОСЬ СДЕЛАТЬ ВРУЧНУЮ (2 минуты)            ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  1. Открой YouTube Studio:                               ║
║     https://studio.youtube.com                           ║
║     (войди под 6035582@gmail.com)                        ║
║                                                          ║
║  2. Слева: Настройка → Брендинг                          ║
║                                                          ║
║  3. «Изображение канала» → Загрузить                     ║
║     Файл: {AVATAR}
║                                                          ║
║  4. Сохранить                                            ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    print("=" * 60)
    print("  MedMind AI — Настройка испанского канала")
    print("=" * 60)

    print("\n🔑 Получаем токен…")
    token = get_access_token()
    print("✓ Токен получен\n")

    print("📡 Получаем данные канала…")
    channel = get_channel(token)
    channel_id = channel["id"]

    print("\n📝 Обновляем метаданные канала…")
    update_channel_metadata(token, channel_id)

    print("\n🖼️  Загружаем баннер…")
    upload_banner(token, channel_id)

    print_final_instructions()

    print("✅ Настройка завершена!\n")
    print(f"   Канал: https://www.youtube.com/channel/{channel_id}")
    print(f"   Studio: https://studio.youtube.com/channel/{channel_id}/editing/images")
