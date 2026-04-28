"""
MedMind AI — Article to Video converter.

Converts a published article into a branded MP4 video suitable for YouTube.

Pipeline:
  1. Fetch article from backend API
  2. Split into title + sections
  3. Synthesize speech for each section via Edge TTS (free, no API key)
  4. Render branded slide images via Pillow
  5. Assemble audio + slides into MP4 via moviepy + ffmpeg

Usage:
    python -m scripts.article_to_video --slug myocardial-infarction
    python -m scripts.article_to_video --slug diabetes-mellitus --voice en-GB-SoniaNeural
    python -m scripts.article_to_video --slug atrial-fibrillation --output ~/Desktop/videos

Install dependencies first:
    pip install edge-tts moviepy==1.0.3 pillow numpy
    brew install ffmpeg          # macOS
    # OR: apt install ffmpeg     # Linux/Ubuntu server

Available voices (recommended):
    en-US-AriaNeural   — US female, natural (default)
    en-US-GuyNeural    — US male, deep
    en-GB-SoniaNeural  — British female, professional
    en-AU-NatashaNeural — Australian female
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


def fonts(size: int) -> ImageFont.FreeTypeFont:
    return _find_font(FONT_SEARCH_PATHS, size)


def fonts_bold(size: int) -> ImageFont.FreeTypeFont:
    return _find_font(FONT_BOLD_PATHS, size)


# ── Text wrapping ─────────────────────────────────────────────────────────────

def wrap_text(text: str, font: Any, max_width: int) -> list[str]:
    """Wrap text to fit within max_width pixels."""
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


def render_title_slide(article: dict) -> np.ndarray:
    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)
    _bg(draw)
    _logo(draw)
    _category_badge(draw, article.get("category", ""))
    _footer(draw)

    # Title
    title = article.get("title", "")
    f_title = fonts_bold(68)
    max_w = W - 120
    lines = wrap_text(title, f_title, max_w)[:3]
    y = 200
    for line in lines:
        draw.text((60, y), line, font=f_title, fill=TEXT_COLOR)
        y += 84

    # Divider
    y += 10
    draw.rectangle([60, y, 260, y + 3], fill=ACCENT)
    y += 30

    # Excerpt
    excerpt = article.get("excerpt", "")
    f_exc = fonts(36)
    exc_lines = wrap_text(excerpt, f_exc, max_w)[:4]
    for line in exc_lines:
        draw.text((60, y), line, font=f_exc, fill=MUTED_COLOR)
        y += 50

    return np.array(img)


def render_section_slide(section: dict, index: int, total: int, category: str) -> np.ndarray:
    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)
    _bg(draw)
    _logo(draw, small=True)
    _footer(draw)

    # Progress indicator
    f_prog = fonts(22)
    draw.text((W - 60, 44), f"{index}/{total}", font=f_prog, fill=MUTED_COLOR, anchor="rm")

    # Section heading
    heading = section.get("heading", "")
    color = CATEGORY_COLORS.get(category, ACCENT)
    if heading:
        f_h = fonts_bold(56)
        h_lines = wrap_text(heading, f_h, W - 120)[:2]
        y = 130
        for line in h_lines:
            draw.text((60, y), line, font=f_h, fill=TEXT_COLOR)
            y += 70
        draw.rectangle([60, y + 8, 200, y + 11], fill=color)
        y += 40
    else:
        y = 130

    # Paragraphs
    f_p = fonts(34)
    para_text = " ".join(section.get("paragraphs", [])[:1])  # first paragraph
    if para_text:
        p_lines = wrap_text(para_text, f_p, W - 120)[:5]
        for line in p_lines:
            draw.text((60, y), line, font=f_p, fill=TEXT_COLOR)
            y += 48
        y += 12

    # Bullet points
    bullets = section.get("bullets", [])
    if bullets:
        f_b = fonts(32)
        for bullet in bullets[:5]:
            b_lines = wrap_text(bullet, f_b, W - 120)
            if b_lines:
                draw.ellipse([60, y + 12, 74, y + 26], fill=color)
                draw.text((90, y), b_lines[0], font=f_b, fill=TEXT_COLOR)
                for extra in b_lines[1:]:
                    y += 42
                    draw.text((90, y), extra, font=f_b, fill=MUTED_COLOR)
            y += 52

    return np.array(img)


def render_outro_slide(article: dict) -> np.ndarray:
    img = Image.new("RGB", (W, H), BG_COLOR)
    draw = ImageDraw.Draw(img)
    _bg(draw)
    _footer(draw)

    # Center logo large
    cx = W // 2
    f_logo = fonts_bold(80)
    draw.text((cx, 320), "MedMind", font=f_logo, fill=TEXT_COLOR, anchor="mm")
    bbox = draw.textbbox((0, 0), "MedMind", font=f_logo)
    logo_w = bbox[2] - bbox[0]
    f_ai = fonts_bold(80)
    draw.text((cx + logo_w // 2 + 10, 320), "AI", font=f_ai, fill=ACCENT, anchor="lm")

    f_sub = fonts(36)
    draw.text((cx, 390), "AI-powered medical education", font=f_sub, fill=MUTED_COLOR, anchor="mm")

    # Divider
    draw.rectangle([cx - 120, 440, cx + 120, 443], fill=ACCENT)

    # CTA lines
    f_cta = fonts(32)
    draw.text((cx, 510), "Read the full article at:", font=f_cta, fill=MUTED_COLOR, anchor="mm")
    f_url = fonts_bold(42)
    draw.text((cx, 570), "medmind.pro/articles", font=f_url, fill=ACCENT, anchor="mm")

    f_sub2 = fonts(30)
    draw.text((cx, 660), "Like & Subscribe for more evidence-based medical content", font=f_sub2, fill=MUTED_COLOR, anchor="mm")

    return np.array(img)


# ── Video assembly ────────────────────────────────────────────────────────────

async def build_video(
    article: dict,
    sections: list[dict],
    voice: str,
    output_path: Path,
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
        title_img = render_title_slide(article)
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
            slide_img = render_section_slide(section, i, total, category)
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
        outro_img = render_outro_slide(article)
        outro_text = (
            f"Thank you for watching this MedMind AI medical education video about "
            f"{article.get('title', 'this topic')}. "
            "For the full article and more evidence-based medical content, "
            "visit medmind dot pro. "
            "Like and subscribe for more."
        )
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


async def fetch_article(slug: str, token: str, client: httpx.AsyncClient) -> dict:
    r = await client.get(f"{API_BASE}/articles/{slug}", timeout=20)
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


# ── Main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    parser = argparse.ArgumentParser(description="MedMind article → YouTube video")
    parser.add_argument("--slug",    required=True, help="Article slug, e.g. myocardial-infarction")
    parser.add_argument("--voice",   default="en-US-AriaNeural",
                        help="Edge TTS voice (default: en-US-AriaNeural)")
    parser.add_argument("--output",  default=str(OUTPUT_DIR),
                        help="Output directory (default: output/videos)")
    parser.add_argument("--preview", action="store_true",
                        help="Render smaller 960x540 preview (faster)")
    args = parser.parse_args()

    output_dir = Path(args.output)

    print(f"\nMedMind Article → Video")
    print(f"  Slug  : {args.slug}")
    print(f"  Voice : {args.voice}")
    print(f"  Output: {output_dir}\n")

    async with httpx.AsyncClient(timeout=30) as client:
        token = await get_token(client)
        print(f"Fetching article '{args.slug}'…")
        article = await fetch_article(args.slug, token, client)

    title = article.get("title", args.slug)
    print(f"  Title   : {title}")
    print(f"  Category: {article.get('category', '?')}")

    sections = parse_sections(article)
    print(f"  Sections: {len(sections)}\n")

    if not sections:
        print("[warn] No sections found in article body. Nothing to generate.")
        return

    # Safe filename from title
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in args.slug)
    output_path = output_dir / f"{safe}.mp4"

    print("Generating audio and rendering slides…")
    await build_video(article, sections, args.voice, output_path)

    size_mb = output_path.stat().st_size / 1_048_576
    print(f"\nDone! Video saved to: {output_path} ({size_mb:.1f} MB)")
    print("\nYouTube upload tips:")
    print(f"  Title      : {title} | MedMind AI")
    kw = ", ".join((article.get("keywords") or [])[:8])
    print(f"  Tags       : {kw}, medical education, medmind")
    print(f"  Description: {article.get('excerpt', '')[:200]}")
    print(f"  URL in desc: https://medmind.pro/articles/{args.slug}")


if __name__ == "__main__":
    asyncio.run(main())
