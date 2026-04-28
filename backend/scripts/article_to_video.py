"""
MedMind AI — Article to Video converter (multilingual).

Converts a published article into a branded MP4 video suitable for YouTube.
Supports all 7 platform languages via Edge TTS (free, no API key needed).

Pipeline:
  1. Fetch article (+ translation if --lang != en) from backend API
  2. Split into title + sections
  3. Synthesize speech via Edge TTS for the chosen language
  4. Render branded 1920×1080 slides via Pillow
  5. Assemble audio + slides → MP4 via moviepy + ffmpeg

Usage:
    # English (default)
    python -m scripts.article_to_video --slug myocardial-infarction

    # Russian
    python -m scripts.article_to_video --slug myocardial-infarction --lang ru

    # German with male voice
    python -m scripts.article_to_video --slug diabetes-mellitus --lang de --voice de-DE-ConradNeural

    # Generate ALL available language videos for one article
    python -m scripts.article_to_video --slug atrial-fibrillation --all-langs

    # Custom output directory
    python -m scripts.article_to_video --slug pneumonia --lang es --output ~/Desktop/videos

Install dependencies first:
    pip install -r requirements_video.txt
    brew install ffmpeg          # macOS
    apt install ffmpeg           # Linux/Ubuntu

    # For Arabic RTL text rendering (optional):
    pip install arabic-reshaper python-bidi

Supported languages and default voices:
    en  English   en-US-AriaNeural       (US female)
    ru  Russian   ru-RU-SvetlanaNeural   (female)
    de  German    de-DE-KatjaNeural      (female)
    fr  French    fr-FR-DeniseNeural     (female)
    es  Spanish   es-ES-ElviraNeural     (female)
    tr  Turkish   tr-TR-EmelNeural       (female)
    ar  Arabic    ar-SA-ZariyahNeural    (female) — needs arabic-reshaper
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Any

import httpx
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# ── Config ────────────────────────────────────────────────────────────────────
API_BASE     = os.getenv("API_BASE",       "http://localhost:8000/api/v1")
ADMIN_EMAIL  = os.getenv("ADMIN_EMAIL",    "admin@medmind.ai")
ADMIN_PASS   = os.getenv("ADMIN_PASSWORD", "adminpass123")
OUTPUT_DIR   = Path(os.getenv("VIDEO_OUTPUT", "output/videos"))

# ── Language → default Edge TTS voice ─────────────────────────────────────────
LANG_VOICE: dict[str, str] = {
    "en": "en-US-AriaNeural",
    "ru": "ru-RU-SvetlanaNeural",
    "de": "de-DE-KatjaNeural",
    "fr": "fr-FR-DeniseNeural",
    "es": "es-ES-ElviraNeural",
    "tr": "tr-TR-EmelNeural",
    "ar": "ar-SA-ZariyahNeural",
}

# Male voice alternatives (use --voice to override)
LANG_VOICE_MALE: dict[str, str] = {
    "en": "en-US-GuyNeural",
    "ru": "ru-RU-DmitryNeural",
    "de": "de-DE-ConradNeural",
    "fr": "fr-FR-HenriNeural",
    "es": "es-ES-AlvaroNeural",
    "tr": "tr-TR-AhmetNeural",
    "ar": "ar-SA-HamedNeural",
}

# Right-to-left languages
RTL_LANGS = {"ar", "he", "fa"}

# Outro CTA text per language
OUTRO_TEXT: dict[str, str] = {
    "en": "Thank you for watching. For the full article visit MedMind AI at medmind dot pro. Like and subscribe for more evidence-based medical content.",
    "ru": "Спасибо за просмотр. Полную статью читайте на MedMind AI — medmind точка pro. Подписывайтесь для новых медицинских материалов.",
    "de": "Vielen Dank fürs Zuschauen. Den vollständigen Artikel finden Sie auf MedMind AI unter medmind punkt pro. Abonnieren Sie für weitere medizinische Inhalte.",
    "fr": "Merci d'avoir regardé. Retrouvez l'article complet sur MedMind AI à medmind point pro. Abonnez-vous pour plus de contenu médical.",
    "es": "Gracias por ver este video. Lee el artículo completo en MedMind AI en medmind punto pro. Suscríbete para más contenido médico.",
    "tr": "İzlediğiniz için teşekkürler. Tam makaleyi MedMind AI'da okuyun: medmind nokta pro. Daha fazla tıbbi içerik için abone olun.",
    "ar": "شكراً لمشاهدتكم. اقرأ المقال كاملاً على MedMind AI على medmind.pro. اشترك لمزيد من المحتوى الطبي.",
}

# Per-language font paths (Unicode fonts for non-Latin scripts)
UNICODE_FONT_PATHS = [
    "/Library/Fonts/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
]

# Video dimensions
W, H = 1920, 1080
FPS  = 24

# ── Brand colours ─────────────────────────────────────────────────────────────
BG_COLOR      = (13,  17,  23)    # #0d1117 — near-black
SURFACE_COLOR = (22,  27,  34)    # #161b22 — card surface
ACCENT        = (88,  166, 255)   # #58a6ff — MedMind blue
TEXT_COLOR    = (230, 237, 243)   # #e6edf3 — bright white
MUTED_COLOR   = (139, 148, 158)   # #8b949e — grey
LINE_COLOR    = (48,  54,  61)    # #30363d — divider

CATEGORY_COLORS: dict[str, tuple[int,int,int]] = {
    "diseases":          (239, 68,  68),   # red
    "drugs":             (168, 85,  247),  # purple
    "cardiology":        (239, 68,  68),
    "neurology":         (59,  130, 246),  # blue
    "emergency":         (249, 115, 22),   # orange
    "procedures":        (20,  184, 166),  # teal
    "oncology":          (236, 72,  153),  # pink
    "psychiatry":        (139, 92,  246),  # violet
    "endocrinology":     (245, 158, 11),   # amber
    "infectious-diseases":(34,  197, 94),  # green
    "pediatrics":        (251, 146, 60),   # orange-light
    "surgery":           (156, 163, 175),  # grey
    "nutrition":         (74,  222, 128),  # green-light
    "diagnostics":       (56,  189, 248),  # sky
    "symptoms":          (251, 191, 36),   # yellow
}

# ── Font discovery ─────────────────────────────────────────────────────────────
FONT_SEARCH_PATHS = [
    # macOS
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial.ttf",
    # Linux
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
]
FONT_BOLD_PATHS = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def _find_font(paths: list[str], size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def fonts(size: int, lang: str = "en") -> ImageFont.FreeTypeFont:
    # Non-Latin scripts need a Unicode-capable font
    if lang in ("ar", "ru", "tr"):
        paths = UNICODE_FONT_PATHS + FONT_SEARCH_PATHS
    else:
        paths = FONT_SEARCH_PATHS
    return _find_font(paths, size)


def fonts_bold(size: int, lang: str = "en") -> ImageFont.FreeTypeFont:
    if lang in ("ar", "ru", "tr"):
        paths = UNICODE_FONT_PATHS + FONT_BOLD_PATHS
    else:
        paths = FONT_BOLD_PATHS
    return _find_font(paths, size)


def prepare_text(text: str, lang: str) -> str:
    """Apply RTL reshaping for Arabic so Pillow renders it correctly."""
    if lang not in RTL_LANGS:
        return text
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(text))
    except ImportError:
        # arabic-reshaper not installed — text will render but may look garbled
        return text


# ── Text wrapping ─────────────────────────────────────────────────────────────

def wrap_text(text: str, font: Any, max_width: int, lang: str = "en") -> list[str]:
    """Wrap text to fit within max_width pixels. RTL languages wrap word-by-word."""
    text = prepare_text(text, lang)
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    dummy = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(dummy)
    for word in words[1:]:
        test = f"{current} {word}"
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] <= max_width:
            current = test
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


# ── Article body → text sections ──────────────────────────────────────────────

def parse_sections(article: dict) -> list[dict]:
    """Convert article body blocks into (heading, text, bullets) sections."""
    body: list[dict] = article.get("body") or []
    sections: list[dict] = []
    current: dict | None = None

    for block in body:
        btype = block.get("type", "")

        if btype == "h2":
            if current:
                sections.append(current)
            current = {"heading": block.get("content", ""), "paragraphs": [], "bullets": []}

        elif btype == "p":
            content = block.get("content", "")
            if content:
                if current is None:
                    current = {"heading": "", "paragraphs": [], "bullets": []}
                current["paragraphs"].append(content)

        elif btype == "ul":
            items = block.get("items", [])
            if items:
                if current is None:
                    current = {"heading": "", "paragraphs": [], "bullets": []}
                current["bullets"].extend(items[:6])  # max 6 bullets per slide

        elif btype == "callout":
            content = block.get("content", "")
            if content and current is not None:
                current["paragraphs"].append(f"Note: {content}")

    if current:
        sections.append(current)

    return sections


def section_tts_text(section: dict) -> str:
    """Build the spoken text for one section."""
    parts = []
    if section["heading"]:
        parts.append(section["heading"] + ".")
    for p in section["paragraphs"][:2]:   # first 2 paragraphs only
        parts.append(p)
    if section["bullets"]:
        parts.append("Key points: " + ". ".join(section["bullets"][:4]))
    return "  ".join(parts)


# ── Edge TTS ──────────────────────────────────────────────────────────────────

async def synthesize(text: str, path: str, voice: str) -> float:
    """Generate MP3 via Edge TTS. Returns duration in seconds (estimated)."""
    try:
        import edge_tts
    except ImportError:
        print("  [error] edge-tts not installed. Run: pip install edge-tts")
        sys.exit(1)

    # Limit text length to avoid timeouts
    text = text[:2000]
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(path)

    # Estimate duration: ~150 words/min for natural speech
    words = len(text.split())
    return max(3.0, words / 150 * 60)


# ── Slide rendering ───────────────────────────────────────────────────────────

def _bg(draw: ImageDraw.ImageDraw) -> None:
    """Fill background and add subtle gradient strip at top."""
    draw.rectangle([0, 0, W, H], fill=BG_COLOR)
    # Top accent bar
    draw.rectangle([0, 0, W, 4], fill=ACCENT)


def _logo(draw: ImageDraw.ImageDraw, small: bool = False) -> None:
    """Draw MedMind AI wordmark in top-left corner."""
    size = 28 if small else 32
    f = fonts_bold(size)
    draw.text((60, 40), "MedMind", font=f, fill=TEXT_COLOR)
    bbox = draw.textbbox((60, 40), "MedMind", font=f)
    draw.text((bbox[2] + 4, 40), "AI", font=f, fill=ACCENT)


def _footer(draw: ImageDraw.ImageDraw) -> None:
    """Draw medmind.pro URL at bottom right."""
    f = fonts(22)
    draw.text((W - 60, H - 50), "medmind.pro", font=f, fill=MUTED_COLOR, anchor="rm")
    draw.rectangle([0, H - 4, W, H], fill=ACCENT)


def _category_badge(draw: ImageDraw.ImageDraw, category: str) -> None:
    color = CATEGORY_COLORS.get(category, ACCENT)
    label = category.replace("-", " ").title()
    f = fonts_bold(22)
    bbox = draw.textbbox((0, 0), label, font=f)
    bw = bbox[2] - bbox[0] + 32
    bh = bbox[3] - bbox[1] + 14
    x, y = 60, 120
    draw.rounded_rectangle([x, y, x + bw, y + bh], radius=6,
                            fill=(*color, 30), outline=(*color, 180), width=1)
    draw.text((x + 16, y + 7), label, font=f, fill=color)


def render_title_slide(article: dict, lang: str = "en") -> np.ndarray:
    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)
    _bg(draw)
    _logo(draw)
    _category_badge(draw, article.get("category", ""))
    _footer(draw)

    # Language badge (non-English only)
    if lang != "en":
        flag = {"ru": "🇷🇺", "de": "🇩🇪", "fr": "🇫🇷", "es": "🇪🇸", "tr": "🇹🇷", "ar": "🇸🇦"}.get(lang, "")
        f_lang = fonts(22)
        draw.text((W - 60, 44), f"{flag} {lang.upper()}", font=f_lang, fill=MUTED_COLOR, anchor="rm")

    # Title
    title = prepare_text(article.get("title", ""), lang)
    f_title = fonts_bold(68, lang)
    max_w = W - 120
    lines = wrap_text(title, f_title, max_w, lang)[:3]
    y = 200
    for line in lines:
        x = W - 60 if lang in RTL_LANGS else 60
        anchor = "ra" if lang in RTL_LANGS else "la"
        draw.text((x, y), line, font=f_title, fill=TEXT_COLOR, anchor=anchor)
        y += 84

    # Divider
    y += 10
    draw.rectangle([60, y, 260, y + 3], fill=ACCENT)
    y += 30

    # Excerpt
    excerpt = prepare_text(article.get("excerpt", ""), lang)
    f_exc = fonts(36, lang)
    exc_lines = wrap_text(excerpt, f_exc, max_w, lang)[:4]
    for line in exc_lines:
        x = W - 60 if lang in RTL_LANGS else 60
        anchor = "ra" if lang in RTL_LANGS else "la"
        draw.text((x, y), line, font=f_exc, fill=MUTED_COLOR, anchor=anchor)
        y += 50

    return np.array(img)


def render_section_slide(section: dict, index: int, total: int,
                          category: str, lang: str = "en") -> np.ndarray:
    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)
    _bg(draw)
    _logo(draw, small=True)
    _footer(draw)

    is_rtl = lang in RTL_LANGS
    x_left = W - 60 if is_rtl else 60
    x_right = 60 if is_rtl else W - 60
    anchor_l = "ra" if is_rtl else "la"
    anchor_r = "la" if is_rtl else "ra"

    # Progress indicator
    f_prog = fonts(22)
    draw.text((x_right, 44), f"{index}/{total}", font=f_prog, fill=MUTED_COLOR, anchor=anchor_r)

    # Section heading
    heading = prepare_text(section.get("heading", ""), lang)
    color = CATEGORY_COLORS.get(category, ACCENT)
    if heading:
        f_h = fonts_bold(56, lang)
        h_lines = wrap_text(heading, f_h, W - 120, lang)[:2]
        y = 130
        for line in h_lines:
            draw.text((x_left, y), line, font=f_h, fill=TEXT_COLOR, anchor=anchor_l)
            y += 70
        draw.rectangle([60, y + 8, 200, y + 11], fill=color)
        y += 40
    else:
        y = 130

    # Paragraphs
    f_p = fonts(34, lang)
    para_text = prepare_text(" ".join(section.get("paragraphs", [])[:1]), lang)
    if para_text:
        p_lines = wrap_text(para_text, f_p, W - 120, lang)[:5]
        for line in p_lines:
            draw.text((x_left, y), line, font=f_p, fill=TEXT_COLOR, anchor=anchor_l)
            y += 48
        y += 12

    # Bullet points
    bullets = section.get("bullets", [])
    if bullets:
        f_b = fonts(32, lang)
        for bullet in bullets[:5]:
            b_text = prepare_text(bullet, lang)
            b_lines = wrap_text(b_text, f_b, W - 120, lang)
            if b_lines:
                dot_x = W - 74 if is_rtl else 60
                draw.ellipse([dot_x, y + 12, dot_x + 14, y + 26], fill=color)
                text_x = W - 90 if is_rtl else 90
                draw.text((text_x, y), b_lines[0], font=f_b, fill=TEXT_COLOR, anchor=anchor_l)
                for extra in b_lines[1:]:
                    y += 42
                    draw.text((text_x, y), extra, font=f_b, fill=MUTED_COLOR, anchor=anchor_l)
            y += 52

    return np.array(img)


def render_outro_slide(article: dict, lang: str = "en") -> np.ndarray:
    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)
    _bg(draw)
    _footer(draw)

    cx = W // 2
    f_logo = fonts_bold(80)
    draw.text((cx, 320), "MedMind", font=f_logo, fill=TEXT_COLOR, anchor="mm")
    bbox = draw.textbbox((0, 0), "MedMind", font=f_logo)
    logo_w = bbox[2] - bbox[0]
    f_ai = fonts_bold(80)
    draw.text((cx + logo_w // 2 + 10, 320), "AI", font=f_ai, fill=ACCENT, anchor="lm")

    f_sub = fonts(36, lang)
    draw.text((cx, 390), "AI-powered medical education", font=f_sub, fill=MUTED_COLOR, anchor="mm")

    draw.rectangle([cx - 120, 440, cx + 120, 443], fill=ACCENT)

    f_url = fonts_bold(42)
    draw.text((cx, 540), "medmind.pro/articles", font=f_url, fill=ACCENT, anchor="mm")

    # Outro CTA in native language
    cta = OUTRO_TEXT.get(lang, OUTRO_TEXT["en"])
    f_cta = fonts(28, lang)
    cta_lines = wrap_text(prepare_text(cta, lang), f_cta, W - 200, lang)[:3]
    y = 630
    for line in cta_lines:
        draw.text((cx, y), line, font=f_cta, fill=MUTED_COLOR, anchor="mm")
        y += 42

    return np.array(img)


# ── Video assembly ────────────────────────────────────────────────────────────

async def build_video(
    article: dict,
    sections: list[dict],
    voice: str,
    output_path: Path,
    lang: str = "en",
) -> None:
    try:
        from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
    except ImportError:
        print("  [error] moviepy not installed. Run: pip install moviepy==1.0.3")
        sys.exit(1)

    clips = []
    category = article.get("category", "")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        clip_index = 0

        # ── 1. Title slide ────────────────────────────────────────────────────
        print("  Rendering title slide…", end=" ", flush=True)
        title_img = render_title_slide(article, lang)
        title_text = f"{article.get('title', '')}. {article.get('excerpt', '')}"
        title_audio = str(tmp / f"audio_{clip_index:03}.mp3")
        duration = await synthesize(title_text, title_audio, voice)
        print(f"{duration:.1f}s")
        clip = (ImageClip(title_img)
                .set_duration(duration + 0.3)
                .set_audio(AudioFileClip(title_audio)))
        clips.append(clip)
        clip_index += 1

        # ── 2. Section slides ─────────────────────────────────────────────────
        total = len(sections)
        for i, section in enumerate(sections, 1):
            heading = section.get("heading") or f"Part {i}"
            print(f"  [{i}/{total}] {heading[:50]}…", end=" ", flush=True)
            slide_img = render_section_slide(section, i, total, category, lang)
            text = section_tts_text(section)
            audio_path = str(tmp / f"audio_{clip_index:03}.mp3")
            duration = await synthesize(text, audio_path, voice)
            print(f"{duration:.1f}s")
            clip = (ImageClip(slide_img)
                    .set_duration(duration + 0.5)
                    .set_audio(AudioFileClip(audio_path)))
            clips.append(clip)
            clip_index += 1

        # ── 3. Outro slide ────────────────────────────────────────────────────
        print("  Rendering outro slide…", end=" ", flush=True)
        outro_img = render_outro_slide(article, lang)
        outro_text = OUTRO_TEXT.get(lang, OUTRO_TEXT["en"])
        outro_audio = str(tmp / f"audio_{clip_index:03}.mp3")
        duration = await synthesize(outro_text, outro_audio, voice)
        print(f"{duration:.1f}s")
        outro_clip = (ImageClip(outro_img)
                      .set_duration(duration + 1.0)
                      .set_audio(AudioFileClip(outro_audio)))
        clips.append(outro_clip)

        # ── 4. Concatenate & export ───────────────────────────────────────────
        print(f"\n  Assembling {len(clips)} clips → {output_path.name}")
        final = concatenate_videoclips(clips, method="compose")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        final.write_videofile(
            str(output_path),
            fps=FPS,
            codec="libx264",
            audio_codec="aac",
            preset="fast",
            threads=4,
            logger=None,
        )
        final.close()
        for c in clips:
            c.close()


# ── API helpers ───────────────────────────────────────────────────────────────

async def get_token(client: httpx.AsyncClient) -> str:
    r = await client.post(
        f"{API_BASE}/auth/login",
        data={"username": ADMIN_EMAIL, "password": ADMIN_PASS},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    if r.status_code != 200:
        raise RuntimeError(f"Login failed: {r.status_code}")
    return r.json()["access_token"]


async def fetch_article(slug: str, token: str, client: httpx.AsyncClient,
                        lang: str = "en") -> dict:
    """Fetch article. If lang != en, attempts to fetch translated version."""
    params = {} if lang == "en" else {"locale": lang}
    r = await client.get(f"{API_BASE}/articles/{slug}", params=params, timeout=20)
    if r.status_code == 200:
        return r.json()
    # Try admin endpoint (includes drafts)
    r = await client.get(
        f"{API_BASE}/articles/admin/list",
        params={"search": slug, "limit": 5},
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )
    if r.status_code == 200:
        items = r.json()
        items = items if isinstance(items, list) else items.get("articles", [])
        for a in items:
            if a.get("slug") == slug:
                return a
    raise RuntimeError(f"Article '{slug}' not found")


async def fetch_available_locales(slug: str, client: httpx.AsyncClient) -> list[str]:
    """Return list of translation locales available for this article."""
    r = await client.get(f"{API_BASE}/articles/{slug}/available-locales", timeout=10)
    if r.status_code == 200:
        return r.json().get("locales", [])
    return []


# ── Main ──────────────────────────────────────────────────────────────────────

async def make_video_for_lang(
    slug: str, lang: str, voice: str,
    output_dir: Path, token: str, client: httpx.AsyncClient,
) -> None:
    """Generate one video for a given slug + language."""
    print(f"\n── Language: {lang.upper()} ─────────────────────────")
    article = await fetch_article(slug, token, client, lang)

    title = article.get("title", slug)
    print(f"  Title   : {title}")
    print(f"  Category: {article.get('category', '?')}")
    print(f"  Voice   : {voice}")

    sections = parse_sections(article)
    print(f"  Sections: {len(sections)}")

    if not sections:
        print("  [warn] No sections found — skipping.")
        return

    safe_slug = "".join(c if c.isalnum() or c in "-_" else "_" for c in slug)
    suffix = f"_{lang}" if lang != "en" else ""
    output_path = output_dir / f"{safe_slug}{suffix}.mp4"

    print("\nGenerating audio and rendering slides…")
    await build_video(article, sections, voice, output_path, lang)

    size_mb = output_path.stat().st_size / 1_048_576
    print(f"\nSaved: {output_path.name} ({size_mb:.1f} MB)")
    print("YouTube upload tips:")
    print(f"  Title : {title} | MedMind AI")
    kw = ", ".join((article.get("keywords") or [])[:6])
    print(f"  Tags  : {kw}, medical education, medmind")
    print(f"  URL   : https://medmind.pro/articles/{slug}{'?lang=' + lang if lang != 'en' else ''}")


async def main() -> None:
    parser = argparse.ArgumentParser(description="MedMind article → multilingual YouTube video")
    parser.add_argument("--slug",      required=True, help="Article slug, e.g. myocardial-infarction")
    parser.add_argument("--lang",      default="en",
                        choices=list(LANG_VOICE.keys()),
                        help="Language (default: en)")
    parser.add_argument("--all-langs", action="store_true",
                        help="Generate videos for all available translations")
    parser.add_argument("--voice",     default="",
                        help="Override Edge TTS voice (default: auto per language)")
    parser.add_argument("--male",      action="store_true",
                        help="Use male voice instead of default female")
    parser.add_argument("--output",    default=str(OUTPUT_DIR),
                        help="Output directory (default: output/videos)")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nMedMind Article → Video (multilingual)")
    print(f"  Slug      : {args.slug}")
    print(f"  All langs : {args.all_langs}")
    print(f"  Output    : {output_dir}")

    async with httpx.AsyncClient(timeout=30) as client:
        token = await get_token(client)

        if args.all_langs:
            # Fetch available translation locales
            locales = await fetch_available_locales(args.slug, client)
            langs_to_gen = ["en"] + [l for l in locales if l != "en"]
            print(f"  Available : {', '.join(langs_to_gen)}\n")
        else:
            langs_to_gen = [args.lang]

        for lang in langs_to_gen:
            if args.voice:
                voice = args.voice
            elif args.male:
                voice = LANG_VOICE_MALE.get(lang, LANG_VOICE[lang])
            else:
                voice = LANG_VOICE.get(lang, LANG_VOICE["en"])

            await make_video_for_lang(args.slug, lang, voice, output_dir, token, client)

    print(f"\nAll done! Videos saved to: {output_dir}")


if __name__ == "__main__":
    asyncio.run(main())
