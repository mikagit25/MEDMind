"""
MedMind AI — Channel Art Generator (ES)

Banner: 2560×1440 px
  YouTube safe zone (desktop): center 1235×338 px
  YouTube safe zone (tablet):  center 1855×423 px
  All branding stays inside the tablet safe zone.

Avatar: 800×800 px
"""
from PIL import Image, ImageDraw, ImageFont
import os, math

FONT_BOLD    = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
OUT_DIR      = "/opt/medmind/channel_art"
os.makedirs(OUT_DIR, exist_ok=True)

# ── Palette ─────────────────────────────────────────────────────────────────
NAVY      = (8,  16,  40)    # deep navy bg
NAVY2     = (12, 24,  58)    # slightly lighter navy
BLUE_MID  = (20, 60, 140)    # mid blue for glow
RED       = (220, 38,  38)   # brand red
WHITE     = (255, 255, 255)
GREY_HI   = (210, 220, 240)  # off-white subtitle
GREY_MID  = (140, 160, 200)  # secondary text
TEAL      = (32, 178, 170)   # accent


def fnt(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def vgrad(draw, x0, y0, x1, y1, top, bot):
    """Vertical gradient fill."""
    h = y1 - y0
    if h <= 0:
        return
    for i in range(h):
        t = i / h
        r = int(top[0] + (bot[0]-top[0])*t)
        g = int(top[1] + (bot[1]-top[1])*t)
        b = int(top[2] + (bot[2]-top[2])*t)
        draw.line([(x0, y0+i), (x1, y0+i)], fill=(r, g, b))


def hgrad(draw, x0, y0, x1, y1, left, right):
    """Horizontal gradient fill."""
    w = x1 - x0
    if w <= 0:
        return
    for i in range(w):
        t = i / w
        r = int(left[0] + (right[0]-left[0])*t)
        g = int(left[1] + (right[1]-left[1])*t)
        b = int(left[2] + (right[2]-left[2])*t)
        draw.line([(x0+i, y0), (x0+i, y1)], fill=(r, g, b))


def radial_glow(img, cx, cy, radius, color, strength=0.35):
    """Soft radial glow by blending a circle into the image."""
    import struct
    overlay = Image.new("RGB", img.size, (0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    steps = 18
    for i in range(steps, 0, -1):
        r = int(radius * i / steps)
        alpha = strength * (1 - i/steps)**1.5
        c = tuple(int(ch * alpha) for ch in color)
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=c)
    # Additive blend
    result = Image.blend(img, Image.fromarray(
        __import__('numpy').clip(
            __import__('numpy').array(img, dtype='int32') +
            __import__('numpy').array(overlay, dtype='int32'),
            0, 255
        ).astype('uint8')
    ), 1.0)
    return result


def draw_cross(draw, cx, cy, size, color):
    h = size // 3
    draw.rectangle([cx-h, cy-size//2, cx+h, cy+size//2], fill=color)
    draw.rectangle([cx-size//2, cy-h, cx+size//2, cy+h],  fill=color)


# ── BANNER 2560×1440 ─────────────────────────────────────────────────────────
def make_banner():
    W, H = 2560, 1440
    img  = Image.new("RGB", (W, H), NAVY)
    draw = ImageDraw.Draw(img)

    # ── Background gradient ───────────────────────────────────────────────────
    vgrad(draw, 0, 0, W, H, NAVY, NAVY2)

    # ── Soft blue glow behind center text ─────────────────────────────────────
    # Approximate glow with concentric dark-to-blue rectangles
    cx, cy = W//2, H//2
    for step in range(30, 0, -1):
        alpha = (step / 30) ** 2 * 0.6
        gw = int(1400 * step / 30)
        gh = int(600  * step / 30)
        r = int(NAVY[0] + (BLUE_MID[0]-NAVY[0]) * alpha)
        g = int(NAVY[1] + (BLUE_MID[1]-NAVY[1]) * alpha)
        b = int(NAVY[2] + (BLUE_MID[2]-NAVY[2]) * alpha)
        draw.ellipse([cx-gw, cy-gh, cx+gw, cy+gh], fill=(r,g,b))

    # ── Subtle hex/grid decoration (very faint) ────────────────────────────────
    grid_color = (18, 30, 70)
    # Vertical lines
    for x in range(0, W, 80):
        draw.line([(x, 0), (x, H)], fill=grid_color, width=1)
    # Horizontal lines
    for y in range(0, H, 80):
        draw.line([(0, y), (W, y)], fill=grid_color, width=1)

    # Re-draw glow over grid (cleaner look)
    for step in range(25, 0, -1):
        alpha = (step / 25) ** 1.8 * 0.5
        gw = int(1200 * step / 25)
        gh = int(500  * step / 25)
        r = int(NAVY[0] + (BLUE_MID[0]-NAVY[0]) * alpha)
        g = int(NAVY[1] + (BLUE_MID[1]-NAVY[1]) * alpha)
        b = int(NAVY[2] + (BLUE_MID[2]-NAVY[2]) * alpha)
        draw.ellipse([cx-gw, cy-gh, cx+gw, cy+gh], fill=(r,g,b))

    # ── Fonts ──────────────────────────────────────────────────────────────────
    f_logo  = fnt(FONT_BOLD,    300)   # "MedMind"
    f_ai    = fnt(FONT_BOLD,    160)   # "AI"
    f_tag   = fnt(FONT_BOLD,     56)   # tagline — smaller to fit safe zone
    f_url   = fnt(FONT_REGULAR,  46)   # URL

    # ── "MedMind" logo — CENTERED ─────────────────────────────────────────────
    med_bbox  = draw.textbbox((0, 0), "Med",     font=f_logo)
    mind_bbox = draw.textbbox((0, 0), "Mind",    font=f_logo)
    ai_bbox   = draw.textbbox((0, 0), "AI",      font=f_ai)

    med_w   = med_bbox[2]  - med_bbox[0]
    mind_w  = mind_bbox[2] - mind_bbox[0]
    ai_w    = ai_bbox[2]   - ai_bbox[0]
    logo_h  = med_bbox[3]  - med_bbox[1]

    total_w = med_w + mind_w + 30 + ai_w   # Med + Mind + gap + AI
    x_logo  = (W - total_w) // 2
    y_logo  = cy - logo_h // 2 - 80

    # Shadow (offset by 6px)
    draw.text((x_logo + 6,          y_logo + 6), "Med",  font=f_logo, fill=(0, 5, 20))
    draw.text((x_logo + med_w + 6,  y_logo + 6), "Mind", font=f_logo, fill=(0, 5, 20))

    # Main text
    draw.text((x_logo,         y_logo), "Med",  font=f_logo, fill=WHITE)
    draw.text((x_logo + med_w, y_logo), "Mind", font=f_logo, fill=RED)

    # "AI" badge — right of "Mind", vertically centered
    ai_x = x_logo + med_w + mind_w + 30
    ai_y = y_logo + logo_h - (ai_bbox[3] - ai_bbox[1]) - 10  # bottom-aligned
    draw.text((ai_x + 3, ai_y + 3), "AI", font=f_ai, fill=(0, 5, 20))   # shadow
    draw.text((ai_x,     ai_y),     "AI", font=f_ai, fill=TEAL)

    # ── Red underline under full logo ─────────────────────────────────────────
    line_y = y_logo + logo_h + 18
    draw.rectangle([x_logo, line_y, x_logo + total_w, line_y + 8], fill=RED)

    # ── Tagline (two lines, fits inside desktop safe zone 1235px) ─────────────
    tag1 = "Educacion Medica en Espanol"
    tag2 = "Basada en Evidencia  |  medmind.pro"
    t1_w = draw.textbbox((0, 0), tag1, font=f_tag)[2]
    t2_w = draw.textbbox((0, 0), tag2, font=f_tag)[2]

    # shadows
    draw.text(((W-t1_w)//2+2, line_y+26+2), tag1, font=f_tag, fill=(0,5,20))
    draw.text(((W-t2_w)//2+2, line_y+90+2), tag2, font=f_tag, fill=(0,5,20))
    # text
    draw.text(((W-t1_w)//2, line_y+26), tag1, font=f_tag, fill=GREY_HI)
    draw.text(((W-t2_w)//2, line_y+90), tag2, font=f_tag, fill=GREY_MID)

    # ── Corner decorations (inside tablet safe zone) ──────────────────────────
    # Left medical cross
    draw_cross(draw, cx - 900, cy, 60, (RED[0], RED[1], RED[2], ))
    # Right medical cross
    draw_cross(draw, cx + 900, cy, 60, RED)

    # Teal accent dots
    for dx in [-950, -880, 950, 880]:
        for dy in [-60, 60]:
            draw.ellipse([cx+dx-4, cy+dy-4, cx+dx+4, cy+dy+4], fill=TEAL)

    # ── Fade edges to pure navy ────────────────────────────────────────────────
    fade_w = 280
    for i in range(fade_w):
        alpha = (fade_w - i) / fade_w
        c = tuple(int(NAVY[k] * alpha + NAVY2[k] * (1-alpha)) for k in range(3))
        # Left edge
        draw.line([(i, 0), (i, H)], fill=c)
        # Right edge
        draw.line([(W-1-i, 0), (W-1-i, H)], fill=c)

    out = f"{OUT_DIR}/banner_es.png"
    img.save(out, "PNG", optimize=True)
    print(f"✓ Banner saved: {out}  ({os.path.getsize(out)//1024} KB)")
    return out


# ── AVATAR 800×800 ────────────────────────────────────────────────────────────
def make_avatar():
    W, H = 800, 800
    img  = Image.new("RGB", (W, H), NAVY)
    draw = ImageDraw.Draw(img)

    # Gradient background
    vgrad(draw, 0, 0, W, H, NAVY, NAVY2)

    # Central glow
    cx, cy = W//2, H//2
    for step in range(22, 0, -1):
        alpha = (step / 22) ** 2 * 0.55
        r_val = int(340 * step / 22)
        r = int(NAVY[0] + (BLUE_MID[0]-NAVY[0]) * alpha)
        g = int(NAVY[1] + (BLUE_MID[1]-NAVY[1]) * alpha)
        b = int(NAVY[2] + (BLUE_MID[2]-NAVY[2]) * alpha)
        draw.ellipse([cx-r_val, cy-r_val, cx+r_val, cy+r_val], fill=(r,g,b))

    # Outer ring
    draw.ellipse([24, 24, W-24, H-24], outline=(40, 70, 140), width=4)

    # Fonts
    f_big  = fnt(FONT_BOLD, 200)   # "MM"
    f_logo = fnt(FONT_BOLD, 100)   # "MedMind"
    f_sub  = fnt(FONT_BOLD,  54)   # "AI · Español"

    # Large "MM" initials in top area
    mm_bbox = draw.textbbox((0,0), "MM", font=f_big)
    mm_w = mm_bbox[2] - mm_bbox[0]
    mm_h = mm_bbox[3] - mm_bbox[1]
    mm_x = (W - mm_w) // 2
    mm_y = 140

    # Shadow
    draw.text((mm_x+5, mm_y+5), "M",        font=f_big, fill=(0,5,20))
    draw.text((mm_x+5 + mm_w//2, mm_y+5), "M", font=f_big, fill=(0,5,20))
    # "M" white, "M" red
    draw.text((mm_x,           mm_y), "M", font=f_big, fill=WHITE)
    draw.text((mm_x + mm_w//2, mm_y), "M", font=f_big, fill=RED)

    # Red divider line
    div_y = mm_y + mm_h + 20
    draw.rectangle([(W-360)//2, div_y, (W+360)//2, div_y+6], fill=RED)

    # "MedMind" below
    logo_bbox = draw.textbbox((0,0), "MedMind", font=f_logo)
    logo_w = logo_bbox[2] - logo_bbox[0]
    lx = (W - logo_w) // 2
    ly = div_y + 22

    med_w = draw.textbbox((0,0), "Med", font=f_logo)[2]
    draw.text((lx+3,       ly+3), "Med",  font=f_logo, fill=(0,5,20))
    draw.text((lx+med_w+3, ly+3), "Mind", font=f_logo, fill=(0,5,20))
    draw.text((lx,         ly),   "Med",  font=f_logo, fill=GREY_HI)
    draw.text((lx+med_w,   ly),   "Mind", font=f_logo, fill=RED)

    # "AI | Español"
    sub_text = "AI  |  Espanol"
    sub_w    = draw.textbbox((0,0), sub_text, font=f_sub)[2]
    sub_y    = ly + logo_bbox[3] - logo_bbox[1] + 18
    draw.text(((W-sub_w)//2, sub_y), sub_text, font=f_sub, fill=TEAL)

    out = f"{OUT_DIR}/avatar_es.png"
    img.save(out, "PNG")
    print(f"✓ Avatar saved: {out}  ({os.path.getsize(out)//1024} KB)")
    return out


if __name__ == "__main__":
    try:
        import numpy  # optional, for glow
    except ImportError:
        pass
    print("Generating channel art…")
    make_avatar()
    make_banner()
    print("\nDone. Files in:", OUT_DIR)
