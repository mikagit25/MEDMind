#!/usr/bin/env python3
"""
MedMind AI — YouTube Channel Setup

Generates and uploads:
  1. Channel banner (2560×1440) via channelBanners.insert API
  2. Channel description, keywords, country via channels.update API

Also generates (must upload manually in YouTube Studio):
  3. Channel avatar/logo (800×800) — saved to /tmp/yt_channel_art/avatar.png
     YouTube Data API v3 does not support programmatic profile picture updates.

Usage:
    python3 setup_youtube_channel.py              # generate images + upload
    python3 setup_youtube_channel.py --images-only  # just generate images
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageFont

# ── Config ─────────────────────────────────────────────────────────────────────
TOKEN_FILE    = Path(os.environ.get("YT_TOKEN",          "/opt/medmind/youtube_token.json"))
SECRET_FILE   = Path(os.environ.get("YT_CLIENT_SECRET",  "/opt/medmind/client_secret.json"))
OUTPUT_DIR    = Path("/tmp/yt_channel_art")

CHANNEL_DESCRIPTION = """\
🩺 MedMind AI — Evidence-based medical education powered by Claude AI & PubMed.

📚 What you'll find here:
• Video explanations of diseases, drugs & clinical concepts
• USMLE-style content for medical students & residents
• Cardiology, neurology, emergency medicine, pharmacology & more
• AI-powered summaries of the latest PubMed research

🌍 Available in 7 languages | 100+ modules | Clinical cases | AI Tutor

🔗 Free platform: https://medmind.pro
📖 Browse all articles: https://medmind.pro/articles

New videos added every week!

#MedicalEducation #USMLE #Medicine #MedStudent #MedMindAI #ClinicalMedicine #MedSchool\
"""

CHANNEL_KEYWORDS = (
    "medical education,USMLE,medicine,medical student,MedMind AI,"
    "clinical medicine,pharmacology,pathology,evidence based medicine,"
    "AI tutor,cardiology,neurology,emergency medicine,medschool,PubMed"
)

# ── Brand palette ──────────────────────────────────────────────────────────────
BG     = (13,  17,  23)    # #0d1117
PANEL  = (16,  21,  30)    # slightly lighter for center strip
ACCENT = (88,  166, 255)   # #58a6ff — MedMind blue
ACCENT2= (56,  139, 235)   # slightly deeper blue for cross
TEXT_C = (230, 237, 243)   # #e6edf3
MUTED  = (139, 148, 158)   # #8b949e
DIM    = (22,  32,  46)    # dot grid color

# ── Font helpers ───────────────────────────────────────────────────────────────
_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
]
_REG  = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
]

def _font(paths: list[str], size: int) -> ImageFont.FreeTypeFont:
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def fb(size: int) -> ImageFont.FreeTypeFont: return _font(_BOLD, size)
def fr(size: int) -> ImageFont.FreeTypeFont: return _font(_REG,  size)

def tw(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    return draw.textbbox((0, 0), text, font=font)[2]


# ── Channel Banner 2560×1440 ───────────────────────────────────────────────────
def make_banner() -> Path:
    """
    Design targets YouTube's safe zone (1546×423px, centered on 2560×1440).
    All critical text stays within x=[507,2053], y=[509,932].
    """
    W, H = 2560, 1440
    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # ── Background: dot grid ──────────────────────────────────────────────────
    for gx in range(40, W, 90):
        for gy in range(40, H, 90):
            draw.ellipse([gx-3, gy-3, gx+3, gy+3], fill=DIM)

    # ── Center strip panel (slightly brighter — helps readability) ────────────
    draw.rectangle([0, 450, W, 990], fill=PANEL)
    # Re-draw dots dimmer over the panel
    dim2 = (18, 26, 38)
    for gx in range(40, W, 90):
        for gy in range(450, 990, 90):
            draw.ellipse([gx-2, gy-2, gx+2, gy+2], fill=dim2)

    # ── Top & bottom accent bars ──────────────────────────────────────────────
    draw.rectangle([0, 0,   W, 8],   fill=ACCENT)
    draw.rectangle([0, H-8, W, H],   fill=ACCENT)

    # ── Vertical side accent strips (TV only, out of safe zone) ──────────────
    for xi, xe in [(0, 6), (W-6, W)]:
        draw.rectangle([xi, 8, xe, H-8], fill=(18, 34, 60))

    # ── Decorative medical crosses (outer areas, TV-only) ────────────────────
    for cx_d in [280, W-280]:
        cy_d = H // 2
        arm, thick = 70, 24
        c = (25, 45, 75)
        draw.rectangle([cx_d-arm, cy_d-thick//2, cx_d+arm, cy_d+thick//2], fill=c)
        draw.rectangle([cx_d-thick//2, cy_d-arm, cx_d+thick//2, cy_d+arm], fill=c)

    cx = W // 2   # 1280
    cy = H // 2   # 720

    # ── Small blue cross above logo (safe zone) ───────────────────────────────
    arm, thick = 38, 13
    cross_y = cy - 175
    draw.rectangle([cx-arm, cross_y-thick//2, cx+arm, cross_y+thick//2], fill=ACCENT2)
    draw.rectangle([cx-thick//2, cross_y-arm, cx+thick//2, cross_y+arm], fill=ACCENT2)

    # ── Logo: "MedMind" + "AI" ────────────────────────────────────────────────
    f_logo = fb(128)
    mm, ai = "MedMind", "AI"
    mm_w = tw(draw, mm, f_logo)
    ai_w = tw(draw, ai, f_logo)
    gap   = 16
    total = mm_w + gap + ai_w
    lx    = cx - total // 2
    ly    = cy - 125

    draw.text((lx,           ly), mm, font=f_logo, fill=TEXT_C)
    draw.text((lx + mm_w + gap, ly), ai, font=f_logo, fill=ACCENT)

    # ── Blue divider ──────────────────────────────────────────────────────────
    div_y = ly + 148
    draw.rectangle([cx - 220, div_y, cx + 220, div_y + 4], fill=ACCENT)

    # ── Tagline ───────────────────────────────────────────────────────────────
    f_tag = fr(52)
    tagline = "Evidence-based medical education"
    draw.text((cx - tw(draw, tagline, f_tag)//2, div_y + 18),
              tagline, font=f_tag, fill=MUTED)

    # ── Stats row ─────────────────────────────────────────────────────────────
    f_stat = fr(38)
    stats  = "100+ Modules   |   7 Languages   |   Claude AI   |   Free"
    draw.text((cx - tw(draw, stats, f_stat)//2, div_y + 90),
              stats, font=f_stat, fill=(100, 120, 145))

    # ── URL ───────────────────────────────────────────────────────────────────
    f_url = fb(58)
    url   = "medmind.pro"
    draw.text((cx - tw(draw, url, f_url)//2, div_y + 156),
              url, font=f_url, fill=ACCENT)

    # ── Subscribe hint (bottom strip, visible on desktop) ────────────────────
    f_sub = fr(34)
    hint  = "Subscribe for weekly medical education content"
    draw.text((cx - tw(draw, hint, f_sub)//2, H - 75),
              hint, font=f_sub, fill=(70, 85, 105))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "banner.png"
    img.save(str(path), "PNG", optimize=True)
    print(f"✅ Banner saved: {path}  ({path.stat().st_size // 1024} KB)")
    return path


# ── Channel Avatar 800×800 ─────────────────────────────────────────────────────
def make_avatar() -> Path:
    """
    Square image — YouTube displays it cropped to a circle.
    Keep all important content within the inscribed circle (radius 380px from center).
    """
    W, H  = 800, 800
    img   = Image.new("RGB", (W, H), BG)
    draw  = ImageDraw.Draw(img)
    cx, cy = W//2, H//2  # 400, 400

    # ── Background circle fill ────────────────────────────────────────────────
    margin = 14
    draw.ellipse([margin, margin, W-margin, H-margin], fill=(16, 22, 33))

    # ── Dot grid (inside circle only) ────────────────────────────────────────
    r_limit = 370
    for gx in range(50, W, 65):
        for gy in range(50, H, 65):
            if (gx-cx)**2 + (gy-cy)**2 < r_limit**2:
                draw.ellipse([gx-2, gy-2, gx+2, gy+2], fill=DIM)

    # ── Outer blue ring ───────────────────────────────────────────────────────
    draw.ellipse([margin, margin, W-margin, H-margin],
                 outline=ACCENT, width=12)

    # ── Inner thin ring ───────────────────────────────────────────────────────
    inner = margin + 22
    draw.ellipse([inner, inner, W-inner, H-inner],
                 outline=(35, 70, 130), width=2)

    # ── Medical cross (centered, blue) ────────────────────────────────────────
    arm, thick = 52, 18
    cross_cy = cy - 160
    draw.rectangle([cx-arm, cross_cy-thick//2, cx+arm, cross_cy+thick//2], fill=ACCENT2)
    draw.rectangle([cx-thick//2, cross_cy-arm, cx+thick//2, cross_cy+arm], fill=ACCENT2)
    # Small corner squares for classic medical cross look
    sq = thick // 2
    for dx in [-arm+sq//2, arm-sq//2]:
        for dy in [-thick//2, thick//2 - sq]:
            pass  # skip, looks clean without them

    # ── "MedMind" text ────────────────────────────────────────────────────────
    f_main = fb(94)
    mm = "MedMind"
    mw = tw(draw, mm, f_main)
    draw.text((cx - mw//2, cy - 95), mm, font=f_main, fill=TEXT_C)

    # ── Thin blue separator ───────────────────────────────────────────────────
    sep_y = cy + 15
    draw.rectangle([cx - 120, sep_y, cx + 120, sep_y + 3], fill=ACCENT)

    # ── "AI" in accent blue ────────────────────────────────────────────────────
    f_ai = fb(88)
    ai = "AI"
    aw = tw(draw, ai, f_ai)
    draw.text((cx - aw//2, sep_y + 12), ai, font=f_ai, fill=ACCENT)

    # ── "medmind.pro" small label ─────────────────────────────────────────────
    f_url = fr(34)
    url   = "medmind.pro"
    uw    = tw(draw, url, f_url)
    draw.text((cx - uw//2, cy + 235), url, font=f_url, fill=MUTED)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "avatar.png"
    img.save(str(path), "PNG", optimize=True)
    print(f"✅ Avatar saved: {path}  ({path.stat().st_size // 1024} KB)")
    return path


# ── YouTube API helpers ────────────────────────────────────────────────────────

def load_token() -> dict:
    if not TOKEN_FILE.exists():
        print(f"❌ Token not found: {TOKEN_FILE}")
        print("   Run: python3 /opt/medmind/backend/scripts/youtube_uploader.py --auth")
        sys.exit(1)
    with open(TOKEN_FILE) as f:
        return json.load(f)

def load_secret() -> dict:
    if not SECRET_FILE.exists():
        print(f"❌ client_secret.json not found: {SECRET_FILE}")
        sys.exit(1)
    with open(SECRET_FILE) as f:
        d = json.load(f)
    return d.get("installed") or d.get("web") or d

def save_token(token: dict):
    with open(TOKEN_FILE, "w") as f:
        json.dump(token, f, indent=2)

def get_access_token() -> str:
    token  = load_token()
    secret = load_secret()
    expires_at = token.get("expires_at", 0)
    if time.time() >= expires_at - 60:
        print("🔄 Token expired — refreshing…")
        resp = httpx.post("https://oauth2.googleapis.com/token", data={
            "client_id":     secret["client_id"],
            "client_secret": secret["client_secret"],
            "refresh_token": token["refresh_token"],
            "grant_type":    "refresh_token",
        })
        resp.raise_for_status()
        token = {**token, **resp.json()}
        token["expires_at"] = time.time() + token.get("expires_in", 3600)
        save_token(token)
        print("✅ Token refreshed")
    return token["access_token"]


def get_channel_id(access_token: str) -> str:
    """Return the channel ID for the authenticated account."""
    resp = httpx.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={"part": "snippet", "mine": "true"},
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    resp.raise_for_status()
    items = resp.json().get("items", [])
    if not items:
        print("❌ No channel found for this account")
        sys.exit(1)
    ch = items[0]
    cid   = ch["id"]
    title = ch["snippet"]["title"]
    print(f"📺 Channel: {title}  (ID: {cid})")
    return cid


def upload_banner(banner_path: Path, access_token: str) -> str:
    """Upload banner image via channelBanners.insert. Returns the banner URL."""
    print(f"\n📤 Uploading banner ({banner_path.stat().st_size // 1024} KB)…")
    with open(banner_path, "rb") as f:
        image_bytes = f.read()

    resp = httpx.post(
        "https://www.googleapis.com/upload/youtube/v3/channelBanners/insert"
        "?uploadType=media",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type":  "image/png",
            "Content-Length": str(len(image_bytes)),
        },
        content=image_bytes,
        timeout=120,
    )

    if resp.status_code not in (200, 201):
        print(f"❌ Banner upload failed: {resp.status_code}")
        print(resp.text[:500])
        sys.exit(1)

    url = resp.json().get("url", "")
    print(f"✅ Banner uploaded → {url[:80]}…")
    return url


def update_channel(
    channel_id: str,
    access_token: str,
    banner_url: str | None = None,
    description: str = "",
    keywords: str = "",
    country: str = "US",
) -> None:
    """Set channel branding: banner, description, keywords, country."""
    body: dict = {
        "id": channel_id,
        "brandingSettings": {
            "channel": {
                "description": description[:5000],
                "keywords":    keywords[:500],
                "country":     country,
            },
        },
    }
    if banner_url:
        body["brandingSettings"]["image"] = {"bannerExternalUrl": banner_url}

    print("\n✏️  Updating channel branding & description…")
    resp = httpx.put(
        "https://www.googleapis.com/youtube/v3/channels?part=brandingSettings",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type":  "application/json",
        },
        content=json.dumps(body).encode(),
        timeout=30,
    )

    if resp.status_code not in (200, 201):
        print(f"❌ Channel update failed: {resp.status_code}")
        print(resp.text[:500])
        sys.exit(1)

    print("✅ Channel branding updated")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="MedMind YouTube Channel Setup")
    parser.add_argument("--images-only", action="store_true",
                        help="Only generate images, do not upload anything")
    args = parser.parse_args()

    print("\n╔═══════════════════════════════════════╗")
    print("║  MedMind AI — YouTube Channel Setup  ║")
    print("╚═══════════════════════════════════════╝\n")

    # 1. Generate images
    print("🎨 Generating banner (2560×1440)…")
    banner_path = make_banner()

    print("\n🎨 Generating avatar (800×800)…")
    avatar_path = make_avatar()

    if args.images_only:
        print(f"\n✅ Images saved to {OUTPUT_DIR}")
        print("   Upload banner via YouTube Studio → Customization → Branding → Banner image")
        print("   Upload avatar via YouTube Studio → Customization → Branding → Profile picture")
        return

    # 2. Get valid API token
    print("\n🔑 Authenticating…")
    access_token = get_access_token()

    # 3. Identify channel
    channel_id = get_channel_id(access_token)

    # 4. Upload banner
    banner_url = upload_banner(banner_path, access_token)

    # 5. Update channel description + branding
    update_channel(
        channel_id   = channel_id,
        access_token = access_token,
        banner_url   = banner_url,
        description  = CHANNEL_DESCRIPTION,
        keywords     = CHANNEL_KEYWORDS,
        country      = "US",
    )

    print("\n╔═══════════════════════════════════════════╗")
    print("║  Channel setup complete!                 ║")
    print("╚═══════════════════════════════════════════╝")
    print(f"\n🖼️  Banner   → applied automatically")
    print(f"📝 Description → updated")
    print(f"🔑 Keywords   → updated")
    print(f"\n⚠️  AVATAR must be uploaded manually:")
    print(f"   File: {avatar_path}")
    print(f"   Go to: YouTube Studio → Customization → Branding → Profile picture → Upload")
    print(f"\n   (YouTube API does not support programmatic profile picture updates)")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))
    main()
