"""
MedMind AI — Medical News → YouTube Video

Generates a branded 1920×1080 MP4 from a published news article.
Reuses rendering infrastructure from article_to_video.py.

Usage:
    python3 news_to_video.py --slug some-news-slug --lang en
    python3 news_to_video.py --slug some-news-slug --lang ar
"""
from __future__ import annotations

import asyncio
import re
import sys
import tempfile
from pathlib import Path

import httpx
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
from article_to_video import (
    W, H, FPS,
    BG_COLOR, ACCENT, TEXT_COLOR, MUTED_COLOR,
    CATEGORY_COLORS, RTL_LANGS, LANG_RATE, LANG_VOICE,
    fonts, fonts_bold, prepare_text, wrap_text,
    synthesize, _bg, _logo, _footer,
    OUTRO_TEXT,
)

API_URL = "https://medmind.pro/api/v1"

# Per-language labels
NEWS_BADGE: dict[str, str] = {
    "en": "MEDICAL NEWS",
    "es": "NOTICIAS MÉDICAS",
    "ar": "أخبار طبية",
    "de": "MEDIZIN NEWS",
    "fr": "ACTUALITÉS MÉDICALES",
    "ru": "МЕД. НОВОСТИ",
    "tr": "TIP HABERİ",
}
SOURCE_LABEL: dict[str, str] = {
    "en": "Source",  "es": "Fuente",    "ar": "المصدر",
    "de": "Quelle",  "fr": "Source",    "ru": "Источник",
    "tr": "Kaynak",
}
INTRO_TTS: dict[str, str] = {
    "en": "Medical news from {source}. {title}.",
    "es": "Noticias médicas de {source}. {title}.",
    "ar": "أخبار طبية من {source}. {title}.",
    "de": "Medizinische Nachrichten von {source}. {title}.",
    "fr": "Actualités médicales de {source}. {title}.",
    "ru": "Медицинские новости от {source}. {title}.",
    "tr": "{source} kaynaklı tıp haberleri. {title}.",
}


# ── Slide renderers ───────────────────────────────────────────────────────────

def render_news_title_slide(news: dict, lang: str = "en") -> np.ndarray:
    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)
    _bg(draw)
    _logo(draw)
    _footer(draw)

    is_rtl = lang in RTL_LANGS
    x_left   = W - 60 if is_rtl else 60
    x_right  = 60     if is_rtl else W - 60
    anc_l    = "ra"   if is_rtl else "la"
    anc_r    = "la"   if is_rtl else "ra"

    # Language flag (non-English)
    if lang != "en":
        flag = {"ru": "🇷🇺", "de": "🇩🇪", "fr": "🇫🇷",
                "es": "🇪🇸", "tr": "🇹🇷", "ar": "🇸🇦"}.get(lang, "")
        f_flag = fonts(22)
        draw.text((x_right, 44), f"{flag} {lang.upper()}", font=f_flag,
                  fill=MUTED_COLOR, anchor=anc_r)

    # "MEDICAL NEWS" badge (red)
    badge = NEWS_BADGE.get(lang, "MEDICAL NEWS")
    if is_rtl:
        badge = prepare_text(badge, lang)
    f_badge = fonts_bold(24)
    bw = draw.textbbox((0, 0), badge, font=f_badge)[2] + 24
    bx = W - 60 - bw if is_rtl else 60
    draw.rounded_rectangle([bx, 100, bx + bw, 136], radius=6, fill=(220, 38, 38))
    draw.text((bx + 12, 108), badge, font=f_badge, fill=(255, 255, 255))

    # Title
    title = prepare_text(news.get("title", ""), lang)
    f_title = fonts_bold(64, lang)
    lines = wrap_text(title, f_title, W - 120, lang)[:3]
    y = 164
    for line in lines:
        draw.text((x_left, y), line, font=f_title, fill=TEXT_COLOR, anchor=anc_l)
        y += 80

    # Divider
    y += 12
    dl, dr = (W - 260, W - 60) if is_rtl else (60, 260)
    draw.rectangle([dl, y, dr, y + 3], fill=ACCENT)
    y += 26

    # Source name
    source = news.get("source_name", "")
    if source:
        src_lbl = SOURCE_LABEL.get(lang, "Source")
        src_text = prepare_text(f"{src_lbl}: {source}", lang)
        f_src = fonts(32, lang)
        for line in wrap_text(src_text, f_src, W - 120, lang)[:2]:
            draw.text((x_left, y), line, font=f_src, fill=MUTED_COLOR, anchor=anc_l)
            y += 46

    return np.array(img)


def render_news_body_slide(text: str, index: int, total: int,
                            category: str, lang: str = "en") -> np.ndarray:
    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)
    _bg(draw)
    _logo(draw, small=True)
    _footer(draw)

    is_rtl = lang in RTL_LANGS
    x_left  = W - 60 if is_rtl else 60
    x_right = 60     if is_rtl else W - 60
    anc_l   = "ra"   if is_rtl else "la"
    anc_r   = "la"   if is_rtl else "ra"

    # Progress indicator
    f_prog = fonts(22)
    draw.text((x_right, 44), f"{index}/{total}", font=f_prog,
              fill=MUTED_COLOR, anchor=anc_r)

    # Category accent bar
    color = CATEGORY_COLORS.get(category, ACCENT)
    cl, cr = (W - 200, W - 60) if is_rtl else (60, 200)
    draw.rectangle([cl, 100, cr, 103], fill=color)

    # Body text
    prepared = prepare_text(text, lang)
    f_body = fonts(38, lang)
    lines = wrap_text(prepared, f_body, W - 120, lang)[:8]
    y = 130
    for line in lines:
        draw.text((x_left, y), line, font=f_body, fill=TEXT_COLOR, anchor=anc_l)
        y += 56

    return np.array(img)


def render_news_outro_slide(lang: str = "en") -> np.ndarray:
    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)
    _bg(draw)
    _footer(draw)

    cx = W // 2
    f_logo = fonts_bold(80)
    draw.text((cx, 320), "MedMind", font=f_logo, fill=TEXT_COLOR, anchor="mm")
    bbox = draw.textbbox((0, 0), "MedMind", font=f_logo)
    lw = bbox[2] - bbox[0]
    draw.text((cx + lw // 2 + 10, 320), "AI", font=f_logo, fill=ACCENT, anchor="lm")

    f_sub = fonts(36, lang)
    draw.text((cx, 390), "AI-powered medical education", font=f_sub,
              fill=MUTED_COLOR, anchor="mm")
    draw.rectangle([cx - 120, 440, cx + 120, 443], fill=ACCENT)

    f_url = fonts_bold(42)
    draw.text((cx, 540), "medmind.pro/news", font=f_url, fill=ACCENT, anchor="mm")

    cta = OUTRO_TEXT.get(lang, OUTRO_TEXT["en"])
    f_cta = fonts(28, lang)
    y = 630
    for line in wrap_text(prepare_text(cta, lang), f_cta, W - 200, lang)[:3]:
        draw.text((cx, y), line, font=f_cta, fill=MUTED_COLOR, anchor="mm")
        y += 42

    return np.array(img)


# ── Summary splitter ──────────────────────────────────────────────────────────

def split_summary(summary: str, max_chars: int = 550) -> list[str]:
    """Split summary into slide-sized chunks, respecting sentence boundaries."""
    sentences = re.split(r'(?<=[.!?])\s+', summary.strip())
    chunks: list[str] = []
    current = ""
    for sent in sentences:
        if not current:
            current = sent
        elif len(current) + 1 + len(sent) <= max_chars:
            current += " " + sent
        else:
            chunks.append(current)
            current = sent
    if current:
        chunks.append(current)
    # Force-split any overlong chunk at a word boundary
    result: list[str] = []
    for chunk in chunks:
        while len(chunk) > max_chars:
            part = chunk[:max_chars]
            cut = part.rfind(" ")
            if cut > max_chars // 2:
                part = part[:cut]
            result.append(part)
            chunk = chunk[len(part):].lstrip()
        if chunk:
            result.append(chunk)
    return result or [summary[:max_chars]]


# ── Video assembly ────────────────────────────────────────────────────────────

async def build_news_video(
    news: dict,
    output_path: Path,
    lang: str = "en",
) -> None:
    try:
        from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
    except ImportError:
        print("  [error] moviepy not installed")
        sys.exit(1)

    title   = news.get("title", "Medical News")
    source  = news.get("source_name", "MedMind")
    summary = news.get("summary", "")
    category = news.get("category", "diseases")
    voice   = LANG_VOICE.get(lang, LANG_VOICE["en"])
    rate    = LANG_RATE.get(lang, "+0%")
    chunks  = split_summary(summary)

    clips: list = []
    audio_clips: list = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        idx = 0

        # 1. Title slide
        print("  Rendering news title slide…", end=" ", flush=True)
        title_img  = render_news_title_slide(news, lang)
        intro_tmpl = INTRO_TTS.get(lang, INTRO_TTS["en"])
        title_tts  = intro_tmpl.format(source=source, title=title)
        title_audio = str(tmp / f"audio_{idx:03}.mp3")
        dur = await synthesize(title_tts, title_audio, voice, rate=rate)
        print(f"{dur:.1f}s")
        aclip = AudioFileClip(title_audio)
        audio_clips.append(aclip)
        clips.append(ImageClip(title_img).set_duration(dur + 0.3).set_audio(aclip))
        idx += 1

        # 2. Body slides (one per chunk)
        total = len(chunks)
        for i, chunk in enumerate(chunks, 1):
            print(f"  [{i}/{total}] body slide…", end=" ", flush=True)
            body_img   = render_news_body_slide(chunk, i, total, category, lang)
            body_audio = str(tmp / f"audio_{idx:03}.mp3")
            dur = await synthesize(chunk, body_audio, voice, rate=rate)
            print(f"{dur:.1f}s")
            aclip = AudioFileClip(body_audio)
            audio_clips.append(aclip)
            clips.append(ImageClip(body_img).set_duration(dur + 0.5).set_audio(aclip))
            idx += 1

        # 3. Outro slide
        print("  Rendering outro slide…", end=" ", flush=True)
        outro_img   = render_news_outro_slide(lang)
        outro_text  = OUTRO_TEXT.get(lang, OUTRO_TEXT["en"])
        outro_audio = str(tmp / f"audio_{idx:03}.mp3")
        dur = await synthesize(outro_text, outro_audio, voice, rate=rate)
        print(f"{dur:.1f}s")
        aclip = AudioFileClip(outro_audio)
        audio_clips.append(aclip)
        clips.append(ImageClip(outro_img).set_duration(dur + 1.0).set_audio(aclip))

        # 4. Assemble
        print(f"\n  Assembling {len(clips)} clips → {output_path.name}")
        final = concatenate_videoclips(clips, method="chain")
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
        for a in audio_clips:
            a.close()


# ── API helpers ───────────────────────────────────────────────────────────────

def fetch_news_article(slug: str, lang: str = "en") -> dict | None:
    params = {} if lang == "en" else {"locale": lang}
    try:
        resp = httpx.get(f"{API_URL}/news/{slug}", params=params, timeout=15)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"  ⚠️  fetch_news_article '{slug}': {e}")
    return None


def fetch_news_slugs(limit: int = 50, lang: str = "en") -> list[dict]:
    """Return list of {slug, category} for published news, newest first."""
    params: dict = {"limit": limit, "offset": 0}
    if lang != "en":
        params["locale"] = lang
    try:
        resp = httpx.get(f"{API_URL}/news", params=params, timeout=15)
        if resp.status_code == 200:
            return [
                {"slug": n["slug"], "category": n.get("category", "general-medicine")}
                for n in resp.json()
            ]
    except Exception as e:
        print(f"  ⚠️  fetch_news_slugs: {e}")
    return []


# ── CLI (for manual testing) ──────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MedMind news → multilingual YouTube video")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--lang", default="en", choices=list(LANG_VOICE.keys()))
    parser.add_argument("--output", default="/tmp/yt_news")
    args = parser.parse_args()

    news = fetch_news_article(args.slug, args.lang)
    if not news:
        print(f"❌ News article '{args.slug}' not found")
        sys.exit(1)

    print(f"Title : {news['title']}")
    print(f"Source: {news['source_name']}")
    output = Path(args.output) / f"{args.slug}_{args.lang}.mp4"
    asyncio.run(build_news_video(news, output, args.lang))
    print(f"\n✅ Saved: {output}")
