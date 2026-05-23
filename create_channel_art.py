"""
Генерирует аватар и баннер для испанского YouTube канала MedMind AI.
Avatar: 800x800px (PNG)
Banner: 2560x1440px (PNG) — YouTube требует минимум 2048x1152
"""
from PIL import Image, ImageDraw, ImageFont
import os, math

FONT_BOLD    = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
OUT_DIR      = "/opt/medmind/channel_art"
os.makedirs(OUT_DIR, exist_ok=True)

# ── Brand palette ────────────────────────────────────────────────────────────
BG_DARK  = (10, 12, 20)        # deep night blue-black
BG_MID   = (18, 22, 38)        # panel bg
RED      = (220, 38,  38)      # brand red
RED_SOFT = (180, 30,  30)      # darker red
BLUE     = (37, 99,  235)      # accent blue
TEAL     = (20, 184, 166)      # medical teal
WHITE    = (255, 255, 255)
GREY_HI  = (200, 210, 230)     # high-visibility grey
GREY_MID = (130, 145, 170)     # mid grey
GREY_LO  = (60,  68,  90)      # subtle grey


def fnt(path: str, size: int):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def gradient_rect(draw, x0, y0, x1, y1, c_from, c_to, axis="x"):
    """Fill rectangle with linear gradient."""
    steps = (x1 - x0) if axis == "x" else (y1 - y0)
    if steps <= 0:
        return
    for i in range(steps):
        t = i / steps
        r = int(c_from[0] + (c_to[0] - c_from[0]) * t)
        g = int(c_from[1] + (c_to[1] - c_from[1]) * t)
        b = int(c_from[2] + (c_to[2] - c_from[2]) * t)
        if axis == "x":
            draw.line([(x0 + i, y0), (x0 + i, y1)], fill=(r, g, b))
        else:
            draw.line([(x0, y0 + i), (x1, y0 + i)], fill=(r, g, b))


def draw_cross(draw, cx, cy, size, color, width=0):
    h = size // 3
    draw.rectangle([cx - h, cy - size // 2, cx + h, cy + size // 2], fill=color)
    draw.rectangle([cx - size // 2, cy - h, cx + size // 2, cy + h],  fill=color)


def draw_ekg(draw, x_start, y_base, width, color, amplitude=60, lw=3):
    """Draw a simple EKG / pulse line."""
    segs = [
        (0.00, 0), (0.08, 0), (0.10, -5), (0.12, 5), (0.14, 0),
        (0.30, 0), (0.35, -amplitude), (0.40, amplitude * 1.8),
        (0.45, -amplitude * 0.6), (0.50, 0),
        (0.55, 0), (0.57, -amplitude * 0.3), (0.60, 0),
        (0.75, 0), (0.77, -5), (0.79, 5), (0.81, 0), (1.00, 0),
    ]
    points = [(x_start + int(t * width), int(y_base + dy)) for t, dy in segs]
    for i in range(len(points) - 1):
        for j in range(lw):
            draw.line([points[i], points[i + 1]], fill=color, width=1)


def draw_dots_grid(draw, x0, y0, cols, rows, spacing, color):
    """Decorative dot grid."""
    for r in range(rows):
        for c in range(cols):
            x = x0 + c * spacing
            y = y0 + r * spacing
            draw.ellipse([x - 1, y - 1, x + 1, y + 1], fill=color)


# ── AVATAR 800×800 ────────────────────────────────────────────────────────────
def make_avatar():
    W, H = 800, 800
    img  = Image.new("RGB", (W, H), BG_DARK)
    draw = ImageDraw.Draw(img)

    # Background gradient (top-left corner)
    gradient_rect(draw, 0, 0, W, H // 2, BG_DARK, BG_MID, axis="y")

    # Outer ring
    ring = 20
    draw.ellipse([ring, ring, W - ring, H - ring], outline=RED, width=4)

    # Inner subtle ring
    draw.ellipse([ring + 16, ring + 16, W - ring - 16, H - ring - 16],
                 outline=GREY_LO, width=1)

    # Medical cross (top-center)
    draw_cross(draw, W // 2, 165, 90, RED)

    # Dot decorations around cross
    for angle_deg in range(0, 360, 45):
        angle = math.radians(angle_deg)
        r = 130
        cx = W // 2 + int(r * math.cos(angle))
        cy = 165 + int(r * math.sin(angle))
        draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=TEAL)

    # "MedMind" — two-color logo
    f_brand = fnt(FONT_BOLD, 148)
    f_sub   = fnt(FONT_BOLD,  68)
    f_tag   = fnt(FONT_REGULAR, 38)

    # Measure "Med"
    bbox_med = draw.textbbox((0, 0), "Med", font=f_brand)
    med_w    = bbox_med[2] - bbox_med[0]
    total_w  = draw.textbbox((0, 0), "MedMind", font=f_brand)[2]
    x_start  = (W - total_w) // 2

    draw.text((x_start,          310), "Med",  font=f_brand, fill=WHITE)
    draw.text((x_start + med_w,  310), "Mind", font=f_brand, fill=RED)

    # "AI" sub
    ai_w = draw.textbbox((0, 0), "AI", font=f_sub)[2]
    draw.text(((W - ai_w) // 2, 475), "AI", font=f_sub, fill=TEAL)

    # Red underline
    draw.rectangle([(W - total_w) // 2, 468, (W + total_w) // 2, 472], fill=RED)

    # Tagline
    tag = "Educación Médica"
    tag_w = draw.textbbox((0, 0), tag, font=f_tag)[2]
    draw.text(((W - tag_w) // 2, 570), tag, font=f_tag, fill=GREY_MID)

    tag2 = "Basada en Evidencia"
    tag2_w = draw.textbbox((0, 0), tag2, font=f_tag)[2]
    draw.text(((W - tag2_w) // 2, 615), tag2, font=f_tag, fill=GREY_LO)

    # Mini EKG bottom
    draw_ekg(draw, 80, 710, 640, TEAL, amplitude=25, lw=2)

    out = f"{OUT_DIR}/avatar_es.png"
    img.save(out, "PNG")
    print(f"✓ Avatar → {out}")
    return out


# ── BANNER 2560×1440 ──────────────────────────────────────────────────────────
def make_banner():
    W, H = 2560, 1440
    img  = Image.new("RGB", (W, H), BG_DARK)
    draw = ImageDraw.Draw(img)

    # ── Background layers ─────────────────────────────────────────────────────
    # Full gradient top→bottom
    gradient_rect(draw, 0, 0, W, H, BG_DARK, BG_MID, axis="y")

    # Right panel — darker overlay
    gradient_rect(draw, 1700, 0, W, H, BG_MID, (8, 10, 18), axis="x")

    # Dot grid decoration (background texture)
    draw_dots_grid(draw, 60, 60, 25, 20, 55, (25, 30, 50))

    # ── Decorative EKG line ────────────────────────────────────────────────────
    draw_ekg(draw, 100, 1280, 1500, TEAL, amplitude=55, lw=3)

    # ── Left red accent bar ────────────────────────────────────────────────────
    gradient_rect(draw, 0, 0, 8, H, RED, RED_SOFT, axis="y")

    # ── Vertical separator ─────────────────────────────────────────────────────
    gradient_rect(draw, 1698, 80, 1702, H - 80, GREY_LO, BG_DARK, axis="y")

    # ── Medical cross (top-right corner) ──────────────────────────────────────
    draw_cross(draw, 2460, 110, 110, RED)
    draw_cross(draw, 2350, 210,  40, GREY_LO)

    # Teal circle decoration
    draw.ellipse([2200, 1200, 2500, 1430], outline=TEAL, width=2)
    draw.ellipse([2240, 1220, 2460, 1410], outline=GREY_LO, width=1)

    # ── Fonts ──────────────────────────────────────────────────────────────────
    f_logo  = fnt(FONT_BOLD,    240)   # "MedMind"
    f_ai    = fnt(FONT_BOLD,    130)   # "AI"
    f_sub   = fnt(FONT_BOLD,     80)   # "Canal Español"
    f_head  = fnt(FONT_BOLD,     66)   # section heading
    f_body  = fnt(FONT_REGULAR,  52)   # features
    f_stat  = fnt(FONT_BOLD,    110)   # stat numbers
    f_stlab = fnt(FONT_REGULAR,  46)   # stat labels
    f_url   = fnt(FONT_BOLD,     56)   # URL

    # ── LOGO ─────────────────────────────────────────────────────────────────
    bbox_med = draw.textbbox((0, 0), "Med", font=f_logo)
    med_w    = bbox_med[2] - bbox_med[0]

    draw.text((110, 110), "Med",  font=f_logo, fill=WHITE)
    draw.text((110 + med_w, 110), "Mind", font=f_logo, fill=RED)

    # "AI" badge
    ai_x = 110 + draw.textbbox((0, 0), "MedMind", font=f_logo)[2] + 30
    draw.text((ai_x, 170), "AI", font=f_ai, fill=TEAL)

    # ── Tagline ────────────────────────────────────────────────────────────────
    draw.text((115, 380), "Canal Español", font=f_sub, fill=GREY_HI)

    # Red horizontal rule
    draw.rectangle([110, 490, 1600, 497], fill=RED)

    # Main tagline
    draw.text((110, 520), "Educación Médica Basada en Evidencia", font=f_head, fill=WHITE)
    draw.text((110, 610), "Generado con Claude AI · PubMed · Guías Clínicas", font=f_body, fill=GREY_MID)

    # ── Feature list ──────────────────────────────────────────────────────────
    features = [
        (TEAL,  "▸  Cardioloǵıa, Neurología, Farmacología"),
        (TEAL,  "▸  Casos clínicos y diagnóstico diferencial"),
        (TEAL,  "▸  Imágenes médicas: Rx, TAC, RMN, ECG"),
        (TEAL,  "▸  Preparación USMLE · MIR · ENARM"),
        (TEAL,  "▸  Shorts médicos diarios"),
    ]
    y = 730
    for color, text in features:
        draw.text((120, y), text, font=f_body, fill=color)
        y += 80

    # ── URL banner ─────────────────────────────────────────────────────────────
    draw.rectangle([110, 1140, 750, 1150], fill=GREY_LO)
    draw.text((110, 1165), "medmind.pro", font=f_url, fill=WHITE)
    draw.text((110, 1260), "Plataforma gratuita • 7 idiomas", font=f_body, fill=GREY_MID)

    # ── Stats (right panel) ────────────────────────────────────────────────────
    stats = [
        ("600+",  "Artículos"),
        ("100+",  "Módulos"),
        ("1500+", "Imágenes"),
        ("Free",  "Plataforma"),
    ]
    x_stat = 1780
    y_stat = 160
    row_h  = 300

    for i, (val, label) in enumerate(stats):
        y0 = y_stat + i * row_h
        # Accent line left of stat
        gradient_rect(draw, x_stat - 12, y0, x_stat - 6, y0 + 140, RED, TEAL, axis="y")
        draw.text((x_stat, y0),       val,   font=f_stat,  fill=WHITE)
        draw.text((x_stat, y0 + 120), label, font=f_stlab, fill=GREY_MID)
        # Subtle divider
        draw.rectangle([x_stat, y0 + 185, x_stat + 600, y0 + 188], fill=GREY_LO)

    out = f"{OUT_DIR}/banner_es.png"
    img.save(out, "PNG")
    print(f"✓ Banner → {out}")
    return out


if __name__ == "__main__":
    print("=== MedMind AI — Channel Art Generator (ES) ===\n")
    avatar = make_avatar()
    banner = make_banner()
    size_av = os.path.getsize(avatar) // 1024
    size_bn = os.path.getsize(banner) // 1024
    print(f"\n✅ Done!")
    print(f"   Avatar: {avatar}  ({size_av} KB)")
    print(f"   Banner: {banner}  ({size_bn} KB)")
