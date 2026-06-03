"""
Generates a YouTube thumbnail (1280x720) for a medical article.
Called automatically after video generation.

If cover_url is provided, uses the article's Wikipedia cover image
as a right-side photo panel for much higher visual impact.
"""
from __future__ import annotations

import io
import re
import tempfile
import textwrap
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFilter, ImageFont

FONT_BOLD    = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# Arabic needs NotoSansArabic — DejaVu/Liberation don't render Arabic glyphs
ARABIC_FONTS = {
    "regular": [
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansArabicUI-Regular.ttf",
    ],
    "bold": [
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansArabic-SemiBold.ttf",
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",  # fallback
    ],
}

# Brand palette
INK   = (13,  13,  18)
WHITE = (255, 255, 255)
GREY  = (160, 160, 175)
DARK2 = (22,  22,  30)

# Category accent colors
CATEGORY_COLORS: dict[str, tuple] = {
    "cardiology":          (220, 38,  38),
    "neurology":           (124, 58, 237),
    "pharmacology":        (5,  150, 105),
    "drugs":               (5,  150, 105),
    "drug-reference":      (5,  150, 105),
    "emergency":           (234, 88,  12),
    "oncology":            (219, 39, 119),
    "psychiatry":          (79,  70, 229),
    "mental-health":       (79,  70, 229),
    "infectious-diseases": (16, 185, 129),
    "infectious-specific": (16, 185, 129),
    "surgery":             (156, 163, 175),
    "surgery-procedures":  (156, 163, 175),
    "pediatrics":          (59, 130, 246),
    "pediatrics-specific": (59, 130, 246),
    "endocrinology":       (245, 158, 11),
    "pulmonology":         (14, 165, 233),
    "nephrology":          (99, 102, 241),
    "orthopedics":         (107, 114, 128),
    "dermatology":         (236, 72,  153),
    "hematology":          (239, 68,  68),
    "rheumatology":        (168, 85, 247),
    "ob-gyn":              (244, 114, 182),
    "womens-health":       (244, 114, 182),
    "ophthalmology":       (6,  182, 212),
    "ent":                 (52, 211, 153),
    "urology":             (96, 165, 250),
    "geriatrics":          (156, 163, 175),
    "nutrition":           (132, 204, 22),
    "clinical-nutrition":  (132, 204, 22),
    "diagnostics":         (251, 191, 36),
    "diagnostics-interpretation": (251, 191, 36),
    "internal-medicine":   (99, 102, 241),
    "diseases":            (220, 38,  38),
    "procedures":          (14, 165, 233),
    "symptoms":            (251, 146, 60),
    "veterinary":          (52, 211, 153),
    "genetics":            (168, 85, 247),
    "pain-management":     (239, 68,  68),
    "radiology":           (14, 165, 233),
    "pathology":           (156, 163, 175),
    "toxicology":          (234, 88,  12),
    "palliative-care":     (107, 114, 128),
    "rehabilitation":      (59, 130, 246),
    "public-health":       (16, 185, 129),
    "preventive-medicine": (5,  150, 105),
    "sleep-medicine":      (79,  70, 229),
    "addiction-medicine":  (220, 38,  38),
    "immunology":          (14, 165, 233),
    "microbiology":        (16, 185, 129),
    "lab-medicine":        (251, 191, 36),
    "critical-care":       (234, 88,  12),
    "anesthesiology":      (107, 114, 128),
    "mens-health":         (59, 130, 246),
    "sexual-health":       (244, 114, 182),
    "occupational-medicine":(52, 211, 153),
    "biochemistry":        (168, 85, 247),
    "physiology":          (99, 102, 241),
}

LANG_LABELS: dict[str, str] = {
    "en": "MEDICAL EDUCATION",
    "es": "EDUCACIÓN MÉDICA",
    "ru": "МЕДИЦИНСКОЕ ОБРАЗОВАНИЕ",
    "de": "MEDIZINISCHE BILDUNG",
    "fr": "ÉDUCATION MÉDICALE",
    "ar": "التعليم الطبي",
    "tr": "TIP EĞİTİMİ",
}

# Category emoji icons for visual flair
CATEGORY_ICONS: dict[str, str] = {
    "cardiology": "❤️", "neurology": "🧠", "pharmacology": "💊",
    "drugs": "💊", "emergency": "🚨", "oncology": "🎗️",
    "psychiatry": "🧩", "mental-health": "🧩",
    "infectious-diseases": "🦠", "surgery": "🔬",
    "pediatrics": "👶", "endocrinology": "⚗️",
    "pulmonology": "🫁", "nephrology": "🫘",
    "dermatology": "🌡️", "hematology": "🩸",
    "rheumatology": "🦴", "ob-gyn": "🤰",
    "ophthalmology": "👁️", "nutrition": "🥗",
    "diagnostics": "📊", "internal-medicine": "🏥",
    "diseases": "🔬", "symptoms": "📋",
    "pain-management": "⚡", "radiology": "🩻",
    "pathology": "🔬", "critical-care": "🚑",
    "immunology": "🛡️", "microbiology": "🦠",
    "genetics": "🧬", "rehabilitation": "💪",
    "preventive-medicine": "🛡️", "sleep-medicine": "😴",
}


def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _load_font_for_lang(size: int, lang: str = "en", bold: bool = False) -> ImageFont.FreeTypeFont:
    """Return the correct font for the given language."""
    if lang == "ar":
        candidates = ARABIC_FONTS["bold"] if bold else ARABIC_FONTS["regular"]
        for path in candidates:
            if Path(path).exists():
                return ImageFont.truetype(path, size)
    font_path = FONT_BOLD if bold else FONT_REGULAR
    return _load_font(font_path, size)


def _prepare_arabic(text: str) -> str:
    """Reshape and apply BiDi to Arabic text so Pillow renders it correctly."""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(text))
    except ImportError:
        return text


def _fetch_cover(url: str) -> Image.Image | None:
    """Download cover image, return PIL Image or None."""
    try:
        resp = httpx.get(url, timeout=8, follow_redirects=True,
                         headers={"User-Agent": "MedMindBot/1.0"})
        if resp.status_code == 200:
            return Image.open(io.BytesIO(resp.content)).convert("RGB")
    except Exception:
        pass
    return None


def _make_photo_panel(cover: Image.Image, panel_w: int, panel_h: int) -> Image.Image:
    """Crop + resize cover image to fill the right panel."""
    src_w, src_h = cover.size
    # Scale to fill panel height
    scale = panel_h / src_h
    new_w = int(src_w * scale)
    if new_w < panel_w:
        scale = panel_w / src_w
        new_w = panel_w
        new_h = int(src_h * scale)
    else:
        new_h = panel_h

    cover = cover.resize((max(new_w, panel_w), max(new_h, panel_h)), Image.LANCZOS)
    # Center crop
    left = (cover.width  - panel_w) // 2
    top  = (cover.height - panel_h) // 2
    return cover.crop((left, top, left + panel_w, top + panel_h))


def generate_thumbnail(
    title: str,
    category: str = "diseases",
    lang: str = "en",
    reading_time: int = 0,
    out_path: Path | None = None,
    cover_url: str | None = None,
) -> Path:
    W, H = 1280, 720
    accent = CATEGORY_COLORS.get(category, (220, 38, 38))

    # ── Base canvas ──────────────────────────────────────────────────────────
    img  = Image.new("RGB", (W, H), INK)
    draw = ImageDraw.Draw(img)

    # Subtle dark gradient background (left → darker right)
    for x in range(W):
        t = x / W * 0.4
        r = int(INK[0] * (1 - t) + DARK2[0] * t)
        g = int(INK[1] * (1 - t) + DARK2[1] * t)
        b = int(INK[2] * (1 - t) + DARK2[2] * t)
        draw.line([(x, 0), (x, H)], fill=(r, g, b))

    # ── Right photo panel (if cover available) ───────────────────────────────
    PANEL_X = 640  # photo starts at midpoint
    has_photo = False

    if cover_url:
        cover = _fetch_cover(cover_url)
        if cover:
            panel = _make_photo_panel(cover, W - PANEL_X, H)
            # Gradient mask: fade photo in from left edge of panel
            fade = Image.new("L", (W - PANEL_X, H), 0)
            fade_draw = ImageDraw.Draw(fade)
            for x in range(200):
                fade_draw.line([(x, 0), (x, H)], fill=int(x / 200 * 255))
            for x in range(200, W - PANEL_X):
                fade_draw.line([(x, 0), (x, H)], fill=255)
            img.paste(panel, (PANEL_X, 0), mask=fade)

            # Dark vignette overlay on photo to improve text contrast
            overlay = Image.new("RGBA", (W - PANEL_X, H), (0, 0, 0, 0))
            ov_draw = ImageDraw.Draw(overlay)
            ov_draw.rectangle([0, 0, W - PANEL_X, H], fill=(0, 0, 0, 80))
            img.paste(overlay.convert("RGB"), (PANEL_X, 0),
                      mask=overlay.split()[3])
            has_photo = True

    if not has_photo:
        # Fallback: decorative medical cross (subtle)
        cx, cy, sz = 960, 370, 260
        draw.rectangle([cx - sz//5, cy - sz//2, cx + sz//5, cy + sz//2],
                       fill=(*accent, 20))
        draw.rectangle([cx - sz//2, cy - sz//5, cx + sz//2, cy + sz//5],
                       fill=(*accent, 20))
        # Second smaller cross
        draw.rectangle([820 - 40, 180 - 90, 820 + 40, 180 + 90],
                       fill=(*accent, 12))
        draw.rectangle([820 - 90, 180 - 40, 820 + 90, 180 + 40],
                       fill=(*accent, 12))

    # ── Left accent bar ──────────────────────────────────────────────────────
    draw.rectangle([0, 0, 10, H], fill=accent)

    # ── Top header strip ─────────────────────────────────────────────────────
    header_h = 68
    header_overlay = Image.new("RGBA", (W, header_h), (*accent, 210))
    img.paste(header_overlay.convert("RGB"), (0, 0),
              mask=header_overlay.split()[3])
    draw = ImageDraw.Draw(img)  # re-draw after paste

    is_rtl = lang == "ar"
    f_label = _load_font_for_lang(27, lang, bold=True)
    label   = LANG_LABELS.get(lang, "MEDICAL EDUCATION")
    if is_rtl:
        label = _prepare_arabic(label)
        draw.text((W - 28, 20), label, font=f_label, fill=WHITE, anchor="ra")
    else:
        draw.text((28, 20), label, font=f_label, fill=WHITE)

    # medmind.pro right-aligned (or left for RTL)
    f_url = _load_font(FONT_BOLD, 27)
    if is_rtl:
        draw.text((28, 20), "medmind.pro", font=f_url, fill=(*WHITE, 200))
    else:
        draw.text((W - 24, 20), "medmind.pro", font=f_url,
                  fill=(*WHITE, 200), anchor="ra")

    # ── Category badge ───────────────────────────────────────────────────────
    f_cat     = _load_font(FONT_BOLD, 27)
    cat_label = category.replace("-", " ").upper()
    bbox      = draw.textbbox((0, 0), cat_label, font=f_cat)
    bw        = bbox[2] - bbox[0] + 28
    badge_x   = W - 28 - bw if is_rtl else 28
    draw.rounded_rectangle([badge_x, 88, badge_x + bw, 130], radius=7, fill=accent)
    draw.text((badge_x + 14, 92), cat_label, font=f_cat, fill=WHITE)

    # ── Title ─────────────────────────────────────────────────────────────────
    f_title   = _load_font_for_lang(70, lang, bold=True)
    clean     = re.sub(r'\s+', ' ', title).strip()

    if is_rtl:
        # Arabic: reshape + bidi, wrap by pixels not chars
        ar_title = _prepare_arabic(clean)
        dummy_img = Image.new("RGB", (1, 1))
        dummy_draw = ImageDraw.Draw(dummy_img)
        words = ar_title.split()
        lines = []
        current = words[0] if words else ""
        max_px = min(580, PANEL_X - 50)
        for word in words[1:]:
            test = f"{current} {word}"
            bbox = dummy_draw.textbbox((0, 0), test, font=f_title)
            if bbox[2] <= max_px:
                current = test
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
        lines = lines[:3]
    else:
        max_chars = 20 if len(title) > 45 else 24
        lines     = textwrap.wrap(clean, width=max_chars)[:3]

    # Text shadow for readability
    y = 152
    shadow_offset = 3
    for line in lines:
        if is_rtl:
            x = min(580, PANEL_X - 50)
            draw.text((x + shadow_offset, y + shadow_offset), line,
                      font=f_title, fill=(0, 0, 0), anchor="ra")
            draw.text((x, y), line, font=f_title, fill=WHITE, anchor="ra")
        else:
            draw.text((28 + shadow_offset, y + shadow_offset), line,
                      font=f_title, fill=(0, 0, 0))
            draw.text((28, y), line, font=f_title, fill=WHITE)
        y += 86

    # ── Divider line ─────────────────────────────────────────────────────────
    if is_rtl:
        draw.rectangle([max(40, PANEL_X - 570), y + 14, min(600, PANEL_X - 40), y + 18], fill=accent)
    else:
        draw.rectangle([28, y + 14, min(600, PANEL_X - 40), y + 18], fill=accent)
    y += 38

    # ── Reading time ─────────────────────────────────────────────────────────
    f_sub = _load_font(FONT_REGULAR, 34)
    if reading_time > 0:
        rt_text = f"⏱  {reading_time} min read"
        x_rt = min(580, PANEL_X - 50) if is_rtl else 30
        anchor_rt = "ra" if is_rtl else "la"
        draw.text((x_rt, y + 6), rt_text, font=f_sub, fill=GREY, anchor=anchor_rt)

    # ── Bottom logo bar ───────────────────────────────────────────────────────
    bottom_y  = H - 82
    logo_overlay = Image.new("RGBA", (W, H - bottom_y), (0, 0, 0, 140))
    img.paste(logo_overlay.convert("RGB"), (0, bottom_y),
              mask=logo_overlay.split()[3])
    draw = ImageDraw.Draw(img)

    f_logo = _load_font(FONT_BOLD, 50)
    draw.text((28, bottom_y + 16), "Med", font=f_logo, fill=WHITE)
    med_bbox = draw.textbbox((28, bottom_y + 16), "Med", font=f_logo)
    draw.text((med_bbox[2] + 2, bottom_y + 16), "Mind AI", font=f_logo, fill=accent)

    # Right: evidence based badge
    f_badge = _load_font(FONT_REGULAR, 22)
    draw.text((W - 28, bottom_y + 20), "Evidence-Based Medicine",
              font=f_badge, fill=GREY, anchor="ra")
    draw.text((W - 28, bottom_y + 46), "medmind.pro",
              font=f_badge, fill=(*accent[:3],), anchor="ra")

    # ── Save ─────────────────────────────────────────────────────────────────
    if out_path is None:
        out_path = Path(tempfile.gettempdir()) / f"thumb_{hash(title) & 0xFFFFFF:06x}.jpg"

    img.save(str(out_path), "JPEG", quality=95)
    return out_path


if __name__ == "__main__":
    import sys
    title    = sys.argv[1] if len(sys.argv) > 1 else "Myocardial Infarction: Diagnosis and Treatment"
    category = sys.argv[2] if len(sys.argv) > 2 else "cardiology"
    lang     = sys.argv[3] if len(sys.argv) > 3 else "en"
    cover    = sys.argv[4] if len(sys.argv) > 4 else None
    out      = Path("/tmp/test_thumb.jpg")
    generate_thumbnail(title, category, lang, reading_time=8, out_path=out, cover_url=cover)
    print(f"✓ Thumbnail: {out}")
