"""
MedMind AI — Article OG Image Generator

Generates a 1200×630 branded cover image for each article.
Saved to media_data volume → served at https://medmind.pro/media/og/{slug}.jpg

Usage:
    python3 generate_og_image.py --slug "headache-causes-types"
    python3 generate_og_image.py --all          # generate for all articles missing images
    python3 generate_og_image.py --all --limit 50

Can also be imported:
    from generate_og_image import generate_og_image
    url = generate_og_image(slug, title, category, reading_time_minutes)
"""
from __future__ import annotations

import argparse
import math
import os
import re
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ── Config ─────────────────────────────────────────────────────────────────────
OUTPUT_DIR = Path("/var/lib/docker/volumes/medmind_media_data/_data/og")
BASE_URL   = "https://medmind.pro/media/og"
W, H       = 1200, 630

FONTS_DIR  = Path("/usr/share/fonts/truetype/dejavu")
FONT_BOLD  = str(FONTS_DIR / "DejaVuSans-Bold.ttf")
FONT_REG   = str(FONTS_DIR / "DejaVuSans.ttf")

# ── Category colour schemes ────────────────────────────────────────────────────
CATEGORY_COLORS: dict[str, tuple[tuple, tuple, str]] = {
    # category → (bg_start, bg_end, accent_hex)
    "cardiology":        ((18, 26, 48), (80, 20, 30),   "#e74c3c"),
    "emergency":         ((30, 15, 10), (90, 30, 15),   "#e67e22"),
    "neurology":         ((20, 15, 50), (55, 25, 80),   "#9b59b6"),
    "psychiatry":        ((25, 10, 45), (60, 20, 70),   "#8e44ad"),
    "pharmacology":      ((10, 30, 55), (20, 55, 90),   "#2980b9"),
    "drugs":             ((10, 30, 55), (20, 55, 90),   "#2980b9"),
    "oncology":          ((10, 40, 45), (15, 70, 65),   "#1abc9c"),
    "hematology":        ((45, 10, 25), (80, 15, 40),   "#c0392b"),
    "infectious-diseases":((15, 35, 15),(25, 60, 25),   "#27ae60"),
    "pediatrics":        ((10, 40, 50), (20, 60, 80),   "#3498db"),
    "surgery":           ((15, 35, 20), (25, 60, 30),   "#2ecc71"),
    "procedures":        ((15, 35, 20), (25, 60, 30),   "#2ecc71"),
    "endocrinology":     ((35, 20, 10), (65, 40, 15),   "#f39c12"),
    "nutrition":         ((10, 40, 20), (20, 65, 35),   "#27ae60"),
    "orthopedics":       ((30, 25, 15), (55, 45, 20),   "#d4ac0d"),
    "dermatology":       ((35, 15, 30), (65, 25, 55),   "#af7ac5"),
    "ophthalmology":     ((10, 35, 50), (15, 60, 80),   "#5dade2"),
    "pulmonology":       ((15, 30, 45), (20, 50, 75),   "#5499c7"),
    "nephrology":        ((15, 35, 45), (20, 60, 75),   "#48c9b0"),
    "rheumatology":      ((40, 20, 20), (70, 35, 30),   "#e59866"),
    "geriatrics":        ((20, 30, 40), (35, 50, 65),   "#85929e"),
    "urology":           ((10, 30, 50), (20, 50, 80),   "#5dade2"),
    "ob-gyn":            ((40, 10, 30), (70, 20, 55),   "#f1948a"),
    "veterinary":        ((20, 35, 15), (35, 60, 25),   "#58d68d"),
    "internal-medicine": ((15, 25, 40), (25, 45, 70),   "#5499c7"),
    "diagnostics":       ((15, 25, 40), (25, 45, 70),   "#48c9b0"),
    "symptoms":          ((25, 20, 40), (45, 35, 65),   "#a569bd"),
    "diseases":          ((15, 25, 45), (25, 40, 70),   "#5499c7"),
    "ent":               ((10, 35, 40), (15, 60, 65),   "#76d7c4"),
}
DEFAULT_COLORS = ((15, 25, 45), (25, 40, 70), "#4a90d9")

CATEGORY_LABELS: dict[str, str] = {
    "cardiology": "Cardiology", "neurology": "Neurology",
    "pharmacology": "Pharmacology", "drugs": "Drugs & Medications",
    "diseases": "Diseases", "symptoms": "Symptoms",
    "emergency": "Emergency Medicine", "procedures": "Procedures",
    "oncology": "Oncology", "surgery": "Surgery",
    "psychiatry": "Psychiatry", "endocrinology": "Endocrinology",
    "infectious-diseases": "Infectious Diseases", "pediatrics": "Pediatrics",
    "nutrition": "Nutrition", "orthopedics": "Orthopedics",
    "dermatology": "Dermatology", "ophthalmology": "Ophthalmology",
    "pulmonology": "Pulmonology", "nephrology": "Nephrology",
    "rheumatology": "Rheumatology", "geriatrics": "Geriatrics",
    "urology": "Urology", "ob-gyn": "Ob & Gyn",
    "hematology": "Hematology", "veterinary": "Veterinary",
    "diagnostics": "Diagnostics", "internal-medicine": "Internal Medicine",
    "ent": "ENT",
}


def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _gradient_background(draw: ImageDraw.ImageDraw, start: tuple, end: tuple):
    """Draw a vertical gradient from start to end colour."""
    for y in range(H):
        t = y / H
        r = int(start[0] + (end[0] - start[0]) * t)
        g = int(start[1] + (end[1] - start[1]) * t)
        b = int(start[2] + (end[2] - start[2]) * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))


def _dot_pattern(draw: ImageDraw.ImageDraw, accent_rgb: tuple):
    """Subtle dot grid overlay."""
    dot_color = (*accent_rgb, 18)  # very transparent
    for x in range(0, W, 40):
        for y in range(0, H, 40):
            draw.ellipse([x-2, y-2, x+2, y+2], fill=dot_color)


def _wrap_title(title: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Word-wrap title to fit max_width pixels."""
    words = title.split()
    lines = []
    current = ""
    tmp_img = Image.new("RGB", (1, 1))
    tmp_draw = ImageDraw.Draw(tmp_img)
    for word in words:
        test = (current + " " + word).strip()
        bbox = tmp_draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines[:4]   # max 4 lines


def generate_og_image(
    slug: str,
    title: str,
    category: str,
    reading_time_minutes: int = 8,
    force: bool = False,
) -> str:
    """
    Generate a 1200×630 OG image for the article.
    Returns the public URL: https://medmind.pro/media/og/{slug}.jpg
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{slug}.jpg"
    if out_path.exists() and not force:
        return f"{BASE_URL}/{slug}.jpg"

    bg_start, bg_end, accent_hex = CATEGORY_COLORS.get(category, DEFAULT_COLORS)
    accent_rgb = _hex_to_rgb(accent_hex)

    img  = Image.new("RGB", (W, H), color=bg_start)
    draw = ImageDraw.Draw(img, "RGBA")

    # Gradient background
    _gradient_background(draw, bg_start, bg_end)

    # Dot pattern overlay
    _dot_pattern(draw, accent_rgb)

    # Accent bar at top and bottom
    draw.rectangle([0, 0, W, 6], fill=accent_rgb)
    draw.rectangle([0, H-6, W, H], fill=accent_rgb)

    # ── Logo line ──────────────────────────────────────────────────────────────
    logo_font = _load_font(FONT_BOLD, 26)
    draw.text((52, 36), "⚕", font=logo_font, fill=(*accent_rgb, 220))
    draw.text((80, 36), "MEDMIND.PRO", font=logo_font, fill=(255, 255, 255, 200))

    # ── Title ─────────────────────────────────────────────────────────────────
    title_font_size = 68
    title_font = _load_font(FONT_BOLD, title_font_size)
    max_title_w  = W - 104  # 52px padding each side
    lines = _wrap_title(title, title_font, max_title_w)

    # Shrink font if too many lines
    if len(lines) > 3:
        title_font_size = 54
        title_font = _load_font(FONT_BOLD, title_font_size)
        lines = _wrap_title(title, title_font, max_title_w)

    line_h = title_font_size + 12
    total_h = len(lines) * line_h
    y_start = (H - total_h) // 2 - 20   # slightly above centre

    for i, line in enumerate(lines):
        y = y_start + i * line_h
        # Shadow
        draw.text((54, y + 3), line, font=title_font, fill=(0, 0, 0, 120))
        # Main text
        draw.text((52, y), line, font=title_font, fill=(255, 255, 255, 245))

    # ── Bottom badges ─────────────────────────────────────────────────────────
    badge_font  = _load_font(FONT_BOLD, 24)
    badge_y     = H - 72
    padding     = 22

    # Category badge
    cat_label = CATEGORY_LABELS.get(category, category.title())
    tmp_img2  = Image.new("RGB", (1, 1))
    tmp_draw2 = ImageDraw.Draw(tmp_img2)
    cat_bbox  = tmp_draw2.textbbox((0, 0), cat_label, font=badge_font)
    cat_w     = cat_bbox[2] - cat_bbox[0] + padding * 2
    cat_h     = 36

    # Filled badge
    draw.rounded_rectangle(
        [52, badge_y, 52 + cat_w, badge_y + cat_h],
        radius=18, fill=(*accent_rgb, 230)
    )
    draw.text((52 + padding, badge_y + 6), cat_label,
              font=badge_font, fill=(255, 255, 255, 245))

    # Reading time badge (outline style)
    time_label = f"  {reading_time_minutes} min read"
    time_bbox  = tmp_draw2.textbbox((0, 0), time_label, font=badge_font)
    time_w     = time_bbox[2] - time_bbox[0] + padding * 2
    time_x     = 52 + cat_w + 16

    draw.rounded_rectangle(
        [time_x, badge_y, time_x + time_w, badge_y + cat_h],
        radius=18, fill=(255, 255, 255, 30), outline=(255, 255, 255, 100), width=1
    )
    draw.text((time_x + padding, badge_y + 6), time_label,
              font=badge_font, fill=(255, 255, 255, 200))

    # ── Decorative medical cross (right side) ─────────────────────────────────
    cx, cy, cs = W - 110, H // 2, 60
    alpha_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    alpha_draw  = ImageDraw.Draw(alpha_layer)
    cross_color = (*accent_rgb, 35)
    # Horizontal bar
    alpha_draw.rectangle([cx - cs, cy - cs//3, cx + cs, cy + cs//3], fill=cross_color)
    # Vertical bar
    alpha_draw.rectangle([cx - cs//3, cy - cs, cx + cs//3, cy + cs], fill=cross_color)
    # Circle outline
    alpha_draw.ellipse([cx - cs - 20, cy - cs - 20, cx + cs + 20, cy + cs + 20],
                       outline=(*accent_rgb, 25), width=2)
    img = Image.alpha_composite(img.convert("RGBA"), alpha_layer).convert("RGB")

    img.save(str(out_path), "JPEG", quality=90, optimize=True)
    return f"{BASE_URL}/{slug}.jpg"


def generate_for_all(limit: int = 999, force: bool = False):
    """Generate OG images for all articles in DB that are missing them."""
    import psycopg2
    DB_URL = "postgresql://medmind:medmind_secret@172.18.0.3:5432/medmind"
    conn   = psycopg2.connect(DB_URL)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT slug, title, category, reading_time_minutes
            FROM articles
            WHERE is_published = true
            ORDER BY created_at DESC
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()
    conn.close()

    done = 0
    for slug, title, category, rt in rows:
        out_path = OUTPUT_DIR / f"{slug}.jpg"
        if out_path.exists() and not force:
            continue
        url = generate_og_image(slug, title, category, rt or 8, force)
        print(f"  ✓ {slug[:50]}")
        done += 1

    print(f"\nGenerated: {done} images → {BASE_URL}/")
    return done


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MedMind OG Image Generator")
    parser.add_argument("--slug",     type=str, help="Generate for one article slug")
    parser.add_argument("--all",      action="store_true", help="Generate for all articles")
    parser.add_argument("--limit",    type=int, default=999, help="Max articles (with --all)")
    parser.add_argument("--force",    action="store_true", help="Overwrite existing images")
    parser.add_argument("--category", type=str, default=None, help="Only this category")
    args = parser.parse_args()

    if args.slug:
        # Need to look up the article from DB
        import psycopg2
        DB_URL = "postgresql://medmind:medmind_secret@172.18.0.3:5432/medmind"
        conn   = psycopg2.connect(DB_URL)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT slug, title, category, reading_time_minutes FROM articles WHERE slug=%s",
                (args.slug,)
            )
            row = cur.fetchone()
        conn.close()
        if not row:
            print(f"Article not found: {args.slug}")
            exit(1)
        slug, title, cat, rt = row
        url = generate_og_image(slug, title, cat, rt or 8, args.force)
        print(f"✓ {url}")

    elif args.all:
        import psycopg2
        DB_URL = "postgresql://medmind:medmind_secret@172.18.0.3:5432/medmind"
        conn   = psycopg2.connect(DB_URL)
        with conn.cursor() as cur:
            q = "SELECT slug, title, category, reading_time_minutes FROM articles WHERE is_published=true"
            params: list = []
            if args.category:
                q += " AND category=%s"
                params.append(args.category)
            q += " ORDER BY created_at DESC LIMIT %s"
            params.append(args.limit)
            cur.execute(q, params)
            rows = cur.fetchall()
        conn.close()

        done = 0
        for slug, title, category, rt in rows:
            out_path = OUTPUT_DIR / f"{slug}.jpg"
            if out_path.exists() and not args.force:
                continue
            url = generate_og_image(slug, title, category, rt or 8, args.force)
            print(f"  ✓ {slug[:60]}")
            done += 1
        print(f"\nDone: {done} images")

    else:
        parser.print_help()
