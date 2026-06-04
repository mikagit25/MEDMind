"""
MedMind AI — Medical Image → YouTube Shorts

Pipeline per image:
  1. Fetch image info from API (title, description, modality, image_url)
  2. Download image from Wikimedia/source
  3. Claude generates 30-sec narration + 4 key points
  4. Edge TTS synthesises MP3
  5. Pillow renders 1080×1920 vertical frame
  6. moviepy assembles → MP4
  7. Upload to YouTube as Short (#Shorts)

Usage:
    python3 image_to_shorts.py --image-id UUID
    python3 image_to_shorts.py --batch 10 --dry-run
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ── Config ─────────────────────────────────────────────────────────────────────
API_URL  = os.getenv("API_BASE", "https://medmind.pro/api/v1")
W, H     = 1080, 1920          # 9:16 vertical
FPS      = 24
IMG_H    = 880                 # image panel height (top)
TEXT_Y0  = IMG_H + 30          # content panel start

# ── Brand palette ──────────────────────────────────────────────────────────────
BG     = (13,  17,  23)
PANEL  = (18,  24,  34)
ACCENT = (88,  166, 255)
TEXT_C = (230, 237, 243)
MUTED  = (139, 148, 158)
DIM    = (22,  32,  46)

MODALITY_COLORS = {
    "histology":  (168, 85,  247),
    "xray":       (56,  189, 248),
    "ct":         (56,  189, 248),
    "mri":        (34,  197, 94),
    "ultrasound": (245, 158, 11),
    "ecg":        (239, 68,  68),
    "anatomy":    (88,  166, 255),
    "photograph": (251, 191, 36),
    "diagram":    (88,  166, 255),
}

# ── Language / voice config ────────────────────────────────────────────────────
LANG_VOICE: dict[str, str] = {
    "en": "en-US-AriaNeural",
    "ru": "ru-RU-SvetlanaNeural",
    "de": "de-DE-KatjaNeural",
    "fr": "fr-FR-DeniseNeural",
    "es": "es-ES-ElviraNeural",
    "tr": "tr-TR-EmelNeural",
    "ar": "ar-EG-SalmaNeural",
}
LANG_RATE: dict[str, str] = {
    "en": "+0%",
    "ru": "-5%",
    "de": "-5%",
    "fr": "-5%",
    "es": "-5%",
    "tr": "-5%",
    "ar": "-15%",
}
LANG_NAME: dict[str, str] = {
    "en": "English",
    "ru": "Russian",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "tr": "Turkish",
    "ar": "Arabic",
}
RTL_LANGS = {"ar", "he", "fa"}

# ── Font helpers ───────────────────────────────────────────────────────────────
_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
_REG  = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]
_ARABIC_BOLD = [
    "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
]
_ARABIC_REG = [
    "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
]

def _font(paths, size):
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def _font_for(lang: str, bold: bool, size: int):
    if lang in RTL_LANGS:
        return _font(_ARABIC_BOLD if bold else _ARABIC_REG, size)
    return _font(_BOLD if bold else _REG, size)

def fb(s): return _font(_BOLD, s)
def fr(s): return _font(_REG,  s)

def tw(draw, text, font):
    return draw.textbbox((0, 0), text, font=font)[2]

def wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        if tw(draw, test, font) <= max_w:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = w
    if cur: lines.append(cur)
    return lines

def _prepare_arabic(text: str) -> str:
    """Reshape + bidi-reorder Arabic text for correct Pillow rendering."""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(text))
    except Exception:
        return text


# ── Image download ─────────────────────────────────────────────────────────────

async def download_image(url: str) -> Image.Image | None:
    """Download image from URL. Returns PIL Image or None on failure."""
    if not url:
        return None
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=20) as client:
            r = await client.get(url, headers={"User-Agent": "MedMindBot/1.0"})
            if r.status_code != 200:
                return None
            img = Image.open(BytesIO(r.content)).convert("RGB")
            return img
    except Exception as e:
        print(f"  ⚠️  Image download failed: {e}")
        return None


def fit_image(img: Image.Image, box_w: int, box_h: int) -> Image.Image:
    """Scale image to fill box_w × box_h, crop to exact size (cover)."""
    iw, ih = img.size
    scale = max(box_w / iw, box_h / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    img = img.resize((nw, nh), Image.LANCZOS)
    # Center-crop
    left = (nw - box_w) // 2
    top  = (nh - box_h) // 2
    return img.crop((left, top, left + box_w, top + box_h))


# ── Claude script generation ───────────────────────────────────────────────────

def _get_anthropic_key() -> str:
    """Read API key: env var → .env.shorts file → app config."""
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if key:
        return key
    env_file = Path("/opt/medmind/.env.shorts")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("ANTHROPIC_API_KEY="):
                return line.split("=", 1)[1].strip()
    try:
        from app.core.config import settings
        return settings.ANTHROPIC_API_KEY
    except Exception:
        return ""


_FALLBACK_TEMPLATES: dict[str, dict[str, str]] = {
    "en": {
        "intro":     "Here's a {context}: {title}.",
        "cta":       "Understanding this helps clinicians make accurate diagnoses. Follow MedMind AI for more medical education.",
        "sig":       "Clinical significance",
        "yt_learn":  "Learn about {title} in this quick medical education Short.",
        "yt_ref":    "Visual clinical reference for medical students and professionals.",
        "yt_link":   "\n\n🔗 Full library: https://medmind.pro/articles\n#MedicalEducation #USMLE #Medicine #MedMindAI #Shorts",
    },
    "ar": {
        "intro":     "إليك {context}: {title}.",
        "cta":       "فهم هذا يساعد الأطباء على إجراء تشخيصات دقيقة. تابع MedMind AI لمزيد من التعليم الطبي.",
        "sig":       "الأهمية السريرية",
        "yt_learn":  "تعرّف على {title} في هذا الفيديو القصير للتعليم الطبي.",
        "yt_ref":    "مرجع سريري مرئي لطلاب الطب والمهنيين.",
        "yt_link":   "\n\n🔗 المكتبة الكاملة: https://medmind.pro/ar/articles\n#التعليم_الطبي #الطب #MedMindAI #Shorts #USMLE",
    },
    "es": {
        "intro":     "Aquí tienes una {context}: {title}.",
        "cta":       "Comprender esto ayuda a los médicos a hacer diagnósticos precisos. Sigue MedMind AI para más educación médica.",
        "sig":       "Relevancia clínica",
        "yt_learn":  "Aprende sobre {title} en este Short de educación médica.",
        "yt_ref":    "Referencia clínica visual para estudiantes y profesionales de la medicina.",
        "yt_link":   "\n\n🔗 Biblioteca completa: https://medmind.pro/es/articles\n#EducaciónMédica #Medicina #MedMindAI #Shorts #USMLE",
    },
    "ru": {
        "intro":     "Перед вами {context}: {title}.",
        "cta":       "Понимание этого помогает врачам ставить точные диагнозы. Подписывайтесь на MedMind AI.",
        "sig":       "Клиническое значение",
        "yt_learn":  "Изучите {title} в этом коротком видео по медицинскому образованию.",
        "yt_ref":    "Визуальный клинический справочник для студентов и специалистов.",
        "yt_link":   "\n\n🔗 Полная библиотека: https://medmind.pro/ru/articles\n#МедицинскоеОбразование #Медицина #MedMindAI #Shorts #USMLE",
    },
    "de": {
        "intro":     "Hier ist eine {context}: {title}.",
        "cta":       "Das Verständnis hilft Klinikern, genaue Diagnosen zu stellen. Folge MedMind AI.",
        "sig":       "Klinische Bedeutung",
        "yt_learn":  "Lerne über {title} in diesem kurzen Medizin-Short.",
        "yt_ref":    "Visuelles klinisches Nachschlagewerk für Medizinstudenten und Fachleute.",
        "yt_link":   "\n\n🔗 Vollständige Bibliothek: https://medmind.pro/de/articles\n#Medizin #Medizinstudent #MedMindAI #Shorts #USMLE",
    },
    "fr": {
        "intro":     "Voici une {context}: {title}.",
        "cta":       "Comprendre cela aide les cliniciens à poser des diagnostics précis. Suivez MedMind AI.",
        "sig":       "Signification clinique",
        "yt_learn":  "Découvrez {title} dans ce Short d'éducation médicale.",
        "yt_ref":    "Référence clinique visuelle pour étudiants en médecine et professionnels.",
        "yt_link":   "\n\n🔗 Bibliothèque complète: https://medmind.pro/fr/articles\n#ÉducationMédicale #Médecine #MedMindAI #Shorts #USMLE",
    },
    "tr": {
        "intro":     "İşte bir {context}: {title}.",
        "cta":       "Bunu anlamak klinisyenlerin doğru teşhis koymasına yardımcı olur. MedMind AI'ı takip edin.",
        "sig":       "Klinik önemi",
        "yt_learn":  "Bu kısa tıp eğitimi videosunda {title} hakkında bilgi edinin.",
        "yt_ref":    "Tıp öğrencileri ve profesyoneller için görsel klinik başvuru kaynağı.",
        "yt_link":   "\n\n🔗 Tam kütüphane: https://medmind.pro/tr/articles\n#TıpEğitimi #Tıp #MedMindAI #Shorts #USMLE",
    },
}

def _generate_script_fallback(image_info: dict, lang: str = "en") -> dict:
    """Template-based script generation — no API required."""
    t = _FALLBACK_TEMPLATES.get(lang, _FALLBACK_TEMPLATES["en"])

    title       = image_info.get("title", "Medical Image")
    description = (image_info.get("description") or "").strip()
    modality    = image_info.get("modality", "")
    specialty   = image_info.get("specialty", "")

    display_title = title[:48]

    context = f"{modality} image" if modality else "medical image"
    if specialty:
        context += f" from {specialty}"

    desc_short = description[:200] if description else ""
    spoken_text = (
        t["intro"].format(context=context, title=title) + " "
        + (desc_short + " " if desc_short else "")
        + t["cta"]
    )[:400]

    def trunc(s: str, n: int) -> str:
        return (s[:n-1] + "…") if len(s) > n else s

    if description:
        sentences = [s.strip() for s in description.split(".") if len(s.strip()) > 10]
        key_points = [trunc(s, 38) for s in sentences[:3]]
    else:
        key_points = []
    if len(key_points) < 4:
        key_points.append(f"{specialty or t['sig']}")

    yt_title  = trunc(f"🔬 {title} #Shorts", 65)
    yt_ref = desc_short[:120] if description else t["yt_ref"]
    yt_desc = (
        t["yt_learn"].format(title=title) + " " + yt_ref
        + t["yt_link"]
    )
    return {
        "display_title":       display_title,
        "spoken_text":         spoken_text,
        "key_points":          key_points[:4],
        "youtube_title":       yt_title,
        "youtube_description": yt_desc,
    }


async def generate_script(image_info: dict, lang: str = "en") -> dict | None:
    """Generate narration + key points. Tries Claude first, falls back to template."""
    title       = image_info.get("title", "")[:200]
    description = (image_info.get("description") or "")[:600]
    modality    = image_info.get("modality", "")
    specialty   = image_info.get("specialty", "")
    lang_name   = LANG_NAME.get(lang, "English")

    link_suffix = _FALLBACK_TEMPLATES.get(lang, _FALLBACK_TEMPLATES["en"])["yt_link"]

    api_key = _get_anthropic_key()
    if api_key:
        try:
            import anthropic as _ant
            prompt = f"""You are creating a 30-second YouTube Shorts script about a medical image.
IMPORTANT: Generate ALL text content in {lang_name}. The entire response must be in {lang_name}.

Image details:
Title: {title}
Modality: {modality} | Specialty: {specialty}
Description: {description}

Return ONLY valid JSON, no other text:
{{
  "display_title": "Catchy short title in {lang_name}, max 48 characters",
  "spoken_text": "Natural 30-second narration (~75 words) in {lang_name}. Start with what we're looking at, then 2-3 key clinical findings, end with why it matters. Conversational but accurate.",
  "key_points": [
    "Finding 1 in {lang_name} (max 38 chars)",
    "Finding 2 in {lang_name} (max 38 chars)",
    "Finding 3 in {lang_name} (max 38 chars)",
    "Clinical significance in {lang_name} (max 38 chars)"
  ],
  "youtube_title": "Engaging title with 1 emoji in {lang_name}, max 65 chars, include #Shorts",
  "youtube_description": "2 sentences in {lang_name} explaining what viewers will learn. End with: {link_suffix}"
}}"""
            client = _ant.AsyncAnthropic(api_key=api_key)
            msg    = await client.messages.create(
                model      = "claude-haiku-4-5-20251001",
                max_tokens = 700,
                messages   = [{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"): raw = raw[4:]
            return json.loads(raw)
        except Exception as e:
            if "credit" in str(e).lower() or "balance" in str(e).lower():
                print(f"  ⚠️  Claude API unavailable (no credits) — using template")
            else:
                print(f"  ⚠️  Claude failed ({e}) — using template")

    print(f"  📋 Using template script")
    return _generate_script_fallback(image_info, lang=lang)


# ── Edge TTS ───────────────────────────────────────────────────────────────────

async def synthesize(text: str, path: str, voice: str = "en-US-AriaNeural", rate: str = "+0%") -> float:
    """Generate MP3. Returns actual duration in seconds."""
    try:
        import edge_tts
    except ImportError:
        print("  [error] edge-tts not installed")
        sys.exit(1)

    communicate = edge_tts.Communicate(text[:1200], voice, rate=rate)
    await communicate.save(path)
    try:
        from moviepy.editor import AudioFileClip as _AFC
        with _AFC(path) as a:
            return max(2.0, a.duration)
    except Exception:
        return max(10.0, len(text.split()) / 150 * 60)


# ── Slide rendering ────────────────────────────────────────────────────────────

def render_shorts_frame(
    image_info: dict,
    script:     dict,
    img_pil:    Image.Image | None,
    lang:       str = "en",
) -> np.ndarray:
    modality  = image_info.get("modality", "").lower()
    mod_color = MODALITY_COLORS.get(modality, ACCENT)

    # ── Full-bleed background image ───────────────────────────────────────────
    if img_pil:
        bg = fit_image(img_pil, W, H)
    else:
        bg = Image.new("RGB", (W, H), (20, 28, 40))
        _d = ImageDraw.Draw(bg)
        _d.text((W//2, H//3), modality.upper() or "MEDICAL IMAGE",
                font=fb(64), fill=DIM, anchor="mm")

    frame_np  = np.array(bg, dtype=np.float32)
    bg_color  = np.array(BG,  dtype=np.float32)

    # Top strip: 55% dark blend so logo/badge is always readable
    TOP_STRIP = 90
    frame_np[:TOP_STRIP] = frame_np[:TOP_STRIP] * 0.45 + bg_color * 0.55

    # Bottom gradient: transparent → 90% dark (text area)
    GRAD_START = 1080
    grad_rows  = H - GRAD_START
    alphas     = np.linspace(0.0, 0.90, grad_rows, dtype=np.float32).reshape(grad_rows, 1, 1)
    frame_np[GRAD_START:] = frame_np[GRAD_START:] * (1 - alphas) + bg_color * alphas

    frame = Image.fromarray(frame_np.astype(np.uint8))
    draw  = ImageDraw.Draw(frame)

    # ── Top bar ───────────────────────────────────────────────────────────────
    draw.rectangle([0, 0, W, 5], fill=ACCENT)

    f_logo = fb(30)
    draw.text((28, 20), "MedMind", font=f_logo, fill=TEXT_C)
    bb = draw.textbbox((28, 20), "MedMind", font=f_logo)
    draw.text((bb[2]+6, 20), "AI", font=f_logo, fill=ACCENT)

    # Modality badge (top right)
    f_badge = fb(22)
    badge   = modality.upper() or "MED"
    bw      = tw(draw, badge, f_badge) + 28
    draw.rounded_rectangle([W-bw-16, 14, W-16, 56], radius=8,
                           fill=mod_color, outline=mod_color, width=1)
    draw.text((W - bw//2 - 16, 35), badge, font=f_badge, fill=(10, 14, 20), anchor="mm")

    # ── Text area (bottom portion over dark gradient) ─────────────────────────
    y   = GRAD_START + 40
    pad = 44
    is_rtl = lang in RTL_LANGS

    # Display title
    f_title = _font_for(lang, bold=True, size=52)
    title   = script.get("display_title", image_info.get("title", ""))[:50]
    t_lines = wrap(draw, title, f_title, W - pad*2)[:2]
    for line in t_lines:
        if is_rtl:
            draw.text((W - pad, y), _prepare_arabic(line), font=f_title, fill=TEXT_C, anchor="ra")
        else:
            draw.text((pad, y), line, font=f_title, fill=TEXT_C)
        y += 64
    y += 10

    # Accent divider
    if is_rtl:
        draw.rectangle([W - pad - 110, y, W - pad, y+3], fill=ACCENT)
    else:
        draw.rectangle([pad, y, pad+110, y+3], fill=ACCENT)
    y += 20

    # Key points
    f_pt  = _font_for(lang, bold=False, size=36)
    dot_r = 7
    for point in script.get("key_points", [])[:4]:
        if not point:
            continue
        if is_rtl:
            draw.ellipse([W - pad - dot_r*2, y+12, W - pad, y+12+dot_r*2], fill=mod_color)
            pt_lines = wrap(draw, point, f_pt, W - pad*2 - 32)[:2]
            for ln in pt_lines:
                draw.text((W - pad - dot_r*2 - 14, y), _prepare_arabic(ln),
                          font=f_pt, fill=TEXT_C, anchor="ra")
                y += 48
        else:
            draw.ellipse([pad, y+12, pad+dot_r*2, y+12+dot_r*2], fill=mod_color)
            pt_lines = wrap(draw, point, f_pt, W - pad*2 - 32)[:2]
            for ln in pt_lines:
                draw.text((pad + dot_r*2 + 14, y), ln, font=f_pt, fill=TEXT_C)
                y += 48
        y += 8

    # Specialty label (muted, small)
    spec = (image_info.get("specialty") or "").replace("-", " ").title()
    if spec:
        f_spec = _font_for(lang, bold=False, size=27)
        if is_rtl:
            draw.text((W - pad, y + 12), _prepare_arabic(spec), font=f_spec, fill=MUTED, anchor="ra")
        else:
            draw.text((pad, y + 12), spec, font=f_spec, fill=MUTED)

    # ── Bottom bar ─────────────────────────────────────────────────────────────
    draw.text((W//2, H - 52), "medmind.pro", font=fb(30), fill=ACCENT, anchor="mm")
    draw.rectangle([0, H-5, W, H], fill=ACCENT)

    return np.array(frame)


# ── Assemble video ─────────────────────────────────────────────────────────────

async def build_short(
    image_info: dict,
    output_path: Path,
    voice: str | None = None,
    lang: str = "en",
) -> bool:
    """Generate one Short MP4. Returns True on success."""
    try:
        from moviepy.editor import ImageClip, AudioFileClip
    except ImportError:
        print("  [error] moviepy not installed")
        sys.exit(1)

    if voice is None:
        voice = LANG_VOICE.get(lang, LANG_VOICE["en"])
    rate = LANG_RATE.get(lang, "+0%")

    print(f"  📝 Generating script [{lang}]…")
    script = await generate_script(image_info, lang=lang)
    if not script:
        return False

    print(f"  🎙️  TTS: {script.get('spoken_text','')[:60]}…")
    with tempfile.TemporaryDirectory() as tmp:
        audio_path = str(Path(tmp) / "audio.mp3")
        duration   = await synthesize(script["spoken_text"], audio_path, voice, rate=rate)
        print(f"  ⏱️  Duration: {duration:.1f}s")

        print(f"  🖼️  Downloading image…")
        img_pil = await download_image(
            image_info.get("image_url") or image_info.get("thumbnail_url") or ""
        )

        print(f"  🎨 Rendering frame…")
        frame = render_shorts_frame(image_info, script, img_pil, lang=lang)

        print(f"  🎬 Assembling MP4…")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        aclip = AudioFileClip(audio_path)
        clip  = ImageClip(frame).set_duration(duration + 1.0).set_audio(aclip)
        clip.write_videofile(
            str(output_path),
            fps          = FPS,
            codec        = "libx264",
            audio_codec  = "aac",
            preset       = "fast",
            threads      = 4,
            logger       = None,
        )
        clip.close()
        aclip.close()

    size_mb = output_path.stat().st_size / 1_048_576
    print(f"  ✅ {output_path.name} ({size_mb:.1f} MB, {duration:.0f}s)")
    return True


# ── API helpers ────────────────────────────────────────────────────────────────

def fetch_images(limit: int = 100, offset: int = 0) -> list[dict]:
    """Fetch medical images from the API via pagination. Prefer clinical modalities, filter junk."""
    prefer = {"xray", "ct", "mri", "ecg", "histology", "ultrasound", "endoscopy",
              "fundus", "dermoscopy", "diagram", "angiography", "nuclear"}
    _JUNK_WORDS = {
        "ferret", "skull", "vertebrat", "textbook", "electronic resource",
        "putorius", "mustela", "furo", "mav-usp", "book", "cover",
        "specimen", "fossil", "museum",
    }

    def is_clinical(img: dict) -> bool:
        combined = ((img.get("title") or "") + " " + (img.get("description") or "")).lower()
        return not any(w in combined for w in _JUNK_WORDS)

    def sort_key(img: dict) -> tuple:
        modality = img.get("modality", "").lower()
        has_desc = 1 if img.get("description") else 0
        return (0 if modality in prefer else 1, -has_desc)

    all_imgs: list[dict] = []
    page_size = 100
    page_offset = 0
    max_fetch = 800  # paginate up to 800 images so we always find new ones

    try:
        while len(all_imgs) < max_fetch:
            resp = httpx.get(
                f"{API_URL}/imaging",
                params={"limit": page_size, "offset": page_offset},
                timeout=20,
            )
            if resp.status_code != 200:
                break
            data = resp.json()
            page = data if isinstance(data, list) else data.get("images", [])
            if not page:
                break
            all_imgs.extend(page)
            if len(page) < page_size:
                break
            page_offset += page_size

        imgs = [i for i in all_imgs if is_clinical(i)]
        imgs.sort(key=sort_key)
        return imgs[:limit]
    except Exception as e:
        print(f"⚠️  Could not fetch images: {e}")
    return []


# ── Main ───────────────────────────────────────────────────────────────────────

async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Medical Image → YouTube Shorts")
    parser.add_argument("--image-id", help="Specific image UUID")
    parser.add_argument("--batch",    type=int, default=1, help="Number of Shorts to generate")
    parser.add_argument("--output",   default="/tmp/yt_shorts", help="Output directory")
    parser.add_argument("--dry-run",  action="store_true")
    parser.add_argument("--voice",    default="en-US-AriaNeural")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.image_id:
        resp = httpx.get(f"{API_URL}/imaging/{args.image_id}", timeout=15)
        if resp.status_code != 200:
            print(f"❌ Image not found: {args.image_id}")
            sys.exit(1)
        images = [resp.json()]
    else:
        images = fetch_images(limit=args.batch * 3)[:args.batch]

    print(f"\n🎬 Generating {len(images)} Short(s)…\n")

    for i, img in enumerate(images, 1):
        title = img.get("title", "?")[:60]
        print(f"[{i}/{len(images)}] {title}")
        print(f"  Modality: {img.get('modality','')} | Specialty: {img.get('specialty','')}")

        if args.dry_run:
            print("  [DRY RUN] Skipping generation")
            continue

        out = output_dir / f"short_{img['id'][:8]}.mp4"
        if out.exists():
            print("  ✓ Already exists, skipping")
            continue

        ok = await build_short(img, out, args.voice)
        if not ok:
            print("  ❌ Failed")
        print()

    print(f"Done. Output: {output_dir}")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    asyncio.run(main())
