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

# ── Font helpers ───────────────────────────────────────────────────────────────
_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]
_REG  = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]

def _font(paths, size):
    for p in paths:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

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


async def generate_script(image_info: dict) -> dict | None:
    """Call Claude Haiku to generate narration + key points for the image."""
    import anthropic as _ant

    api_key = _get_anthropic_key()
    if not api_key:
        print("  ❌ ANTHROPIC_API_KEY not found")
        return None

    title       = image_info.get("title", "")[:200]
    description = (image_info.get("description") or "")[:600]
    modality    = image_info.get("modality", "")
    specialty   = image_info.get("specialty", "")

    prompt = f"""You are creating a 30-second YouTube Shorts script about a medical image.

Image details:
Title: {title}
Modality: {modality} | Specialty: {specialty}
Description: {description}

Generate educational content. Return ONLY valid JSON, no other text:
{{
  "display_title": "Catchy short title, max 48 characters",
  "spoken_text": "Natural 30-second narration (~75 words). Start with what we're looking at, then 2-3 key clinical findings, end with why it matters. Conversational but accurate.",
  "key_points": [
    "Finding 1 (max 38 chars)",
    "Finding 2 (max 38 chars)",
    "Finding 3 (max 38 chars)",
    "Clinical significance (max 38 chars)"
  ],
  "youtube_title": "Engaging title with 1 emoji, max 65 chars, include #Shorts",
  "youtube_description": "2 sentences explaining what viewers will learn. End with: \\n\\n🔗 Full library: https://medmind.pro/articles\\n#MedicalEducation #USMLE #Medicine #MedMindAI #Shorts"
}}"""

    try:
        client = _ant.AsyncAnthropic(api_key=api_key)
        msg    = await client.messages.create(
            model      = "claude-haiku-4-5-20251001",
            max_tokens = 600,
            messages   = [{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"): raw = raw[4:]
        return json.loads(raw)
    except Exception as e:
        print(f"  ❌ Script generation failed: {e}")
        return None


# ── Edge TTS ───────────────────────────────────────────────────────────────────

async def synthesize(text: str, path: str, voice: str = "en-US-AriaNeural") -> float:
    """Generate MP3. Returns actual duration in seconds."""
    try:
        import edge_tts
    except ImportError:
        print("  [error] edge-tts not installed")
        sys.exit(1)

    communicate = edge_tts.Communicate(text[:1200], voice)
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
) -> np.ndarray:
    frame  = Image.new("RGB", (W, H), BG)
    draw   = ImageDraw.Draw(frame)

    modality = image_info.get("modality", "").lower()
    mod_color = MODALITY_COLORS.get(modality, ACCENT)

    # ── Image panel ───────────────────────────────────────────────────────────
    if img_pil:
        fitted = fit_image(img_pil, W, IMG_H)
        frame.paste(fitted, (0, 0))
    else:
        # Placeholder when image unavailable
        draw.rectangle([0, 0, W, IMG_H], fill=(20, 28, 40))
        f = fb(48)
        msg = modality.upper() or "MEDICAL IMAGE"
        draw.text((W//2, IMG_H//2), msg, font=f, fill=DIM, anchor="mm")

    # Gradient overlay: transparent at top → opaque at bottom of image panel
    for y in range(IMG_H - 200, IMG_H):
        alpha = int(255 * (y - (IMG_H - 200)) / 200)
        draw.line([(0, y), (W, y)], fill=tuple([*BG, alpha])[:3])

    # Dark fade at very bottom of image
    for y in range(IMG_H - 60, IMG_H):
        draw.line([(0, y), (W, y)], fill=BG)

    # ── Top bar ───────────────────────────────────────────────────────────────
    draw.rectangle([0, 0, W, 6], fill=ACCENT)

    # Logo
    f_logo = fb(30)
    draw.text((28, 20), "MedMind", font=f_logo, fill=TEXT_C)
    bb = draw.textbbox((28, 20), "MedMind", font=f_logo)
    draw.text((bb[2]+6, 20), "AI", font=f_logo, fill=ACCENT)

    # Modality badge (top right)
    f_badge = fb(22)
    badge   = modality.upper() or "MED"
    bw      = tw(draw, badge, f_badge) + 28
    draw.rounded_rectangle([W-bw-16, 16, W-16, 56], radius=8,
                            fill=(*mod_color, 30), outline=(*mod_color, 180), width=1)
    draw.text((W - bw//2 - 16, 36), badge, font=f_badge, fill=mod_color, anchor="mm")

    # ── Content panel (below image) ───────────────────────────────────────────
    draw.rectangle([0, IMG_H, W, H], fill=BG)

    # Thin colored top border of content area
    draw.rectangle([0, IMG_H, W, IMG_H+3], fill=mod_color)

    y = IMG_H + 28
    pad = 40

    # Display title
    f_title = fb(46)
    title   = script.get("display_title", image_info.get("title", ""))[:50]
    t_lines = wrap(draw, title, f_title, W - pad*2)[:2]
    for line in t_lines:
        draw.text((pad, y), line, font=f_title, fill=TEXT_C)
        y += 58
    y += 8

    # Blue divider
    draw.rectangle([pad, y, pad+120, y+3], fill=ACCENT)
    y += 18

    # Key points
    f_pt = fr(34)
    dot_r = 6
    for point in script.get("key_points", [])[:4]:
        if not point: continue
        # Dot
        draw.ellipse([pad, y+10, pad+dot_r*2, y+10+dot_r*2], fill=mod_color)
        # Text
        pt_lines = wrap(draw, point, f_pt, W - pad*2 - 28)[:2]
        for ln in pt_lines:
            draw.text((pad + dot_r*2 + 12, y), ln, font=f_pt, fill=TEXT_C)
            y += 44
        y += 6

    # Specialty badge
    spec = (image_info.get("specialty") or "").replace("-", " ").title()
    if spec:
        f_spec = fr(26)
        draw.text((pad, y + 14), spec, font=f_spec, fill=MUTED)

    # ── Bottom bar ─────────────────────────────────────────────────────────────
    f_url = fb(30)
    url_y = H - 52
    draw.text((W//2, url_y), "medmind.pro", font=f_url, fill=ACCENT, anchor="mm")
    draw.rectangle([0, H-6, W, H], fill=ACCENT)

    return np.array(frame)


# ── Assemble video ─────────────────────────────────────────────────────────────

async def build_short(
    image_info: dict,
    output_path: Path,
    voice: str = "en-US-AriaNeural",
) -> bool:
    """Generate one Short MP4. Returns True on success."""
    try:
        from moviepy.editor import ImageClip, AudioFileClip
    except ImportError:
        print("  [error] moviepy not installed")
        sys.exit(1)

    print(f"  📝 Generating script…")
    script = await generate_script(image_info)
    if not script:
        return False

    print(f"  🎙️  TTS: {script.get('spoken_text','')[:60]}…")
    with tempfile.TemporaryDirectory() as tmp:
        audio_path = str(Path(tmp) / "audio.mp3")
        duration   = await synthesize(script["spoken_text"], audio_path, voice)
        print(f"  ⏱️  Duration: {duration:.1f}s")

        print(f"  🖼️  Downloading image…")
        img_pil = await download_image(
            image_info.get("image_url") or image_info.get("thumbnail_url") or ""
        )

        print(f"  🎨 Rendering frame…")
        frame = render_shorts_frame(image_info, script, img_pil)

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
    """Fetch medical images from the API. Prefer clear educational modalities."""
    prefer = {"histology", "xray", "ct", "mri", "ecg", "anatomy", "diagram", "ultrasound"}
    try:
        resp = httpx.get(f"{API_URL}/imaging", params={"limit": limit}, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            imgs = data if isinstance(data, list) else data.get("images", [])
            # Sort: preferred modalities first
            imgs.sort(key=lambda x: (0 if x.get("modality","") in prefer else 1))
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
