#!/usr/bin/env python3
"""
Generate cover images for MedMind articles that lack them.

Uses Together.ai FLUX.1-schnell to create professional medical illustrations.
Each image is saved with full EXIF + XMP metadata (title, description,
copyright, source URL) so Google Images can verify and attribute the image
to medmind.pro — helping the site appear in image search results.

Image metadata embedded:
  EXIF: ImageDescription, Copyright, Artist, XPTitle, XPComment
  XMP:  dc:title, dc:description, dc:rights, dc:source, photoshop:Credit,
        xmpRights:WebStatement (site URL)

Usage:
  # Run from /opt/medmind on the host (not inside Docker)
  TOGETHER_API_KEY=$(cat /opt/kids_channel/credentials/together_api_key.txt) \\
    python3 backend/scripts/generate_article_images.py --limit 50

  python3 ... --category oncology --limit 100   # specific category
  python3 ... --dry-run --limit 20              # preview prompts only
  python3 ... --slug some-article-slug          # single article
  python3 ... --overwrite                       # regenerate existing

API key:  /opt/kids_channel/credentials/together_api_key.txt
Model:    black-forest-labs/FLUX.1-schnell  (~$0.0003/image)
Output:   Docker volume → served at https://medmind.pro/media/articles/{slug}.jpg
"""

import argparse
import io
import os
import struct
import sys
import time
from pathlib import Path

import httpx
from PIL import Image
import piexif
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

# ── Config ────────────────────────────────────────────────────────────────────

SITE_URL          = "https://medmind.pro"
TOGETHER_KEY_FILE = Path("/opt/kids_channel/credentials/together_api_key.txt")
TOGETHER_URL      = "https://api.together.xyz/v1/images/generations"
TOGETHER_MODEL    = "black-forest-labs/FLUX.1-schnell"

DOCKER_VOL_DIR    = Path("/var/lib/docker/volumes/medmind_media_data/_data/articles")
MEDIA_DIR         = Path("/app/data/media/articles")   # inside Docker container
MEDIA_URL_PREFIX  = "/media/articles"

_raw_db_url = os.environ.get(
    "DATABASE_URL",
    "postgresql://medmind:medmind_secret@localhost:5432/medmind"
)
DATABASE_URL = _raw_db_url.replace("+asyncpg", "").replace("@postgres:", "@localhost:")

# ── Medical image style ───────────────────────────────────────────────────────

STYLE = (
    "clean professional medical illustration, "
    "photorealistic 3D render, soft blue and white clinical color palette, "
    "high detail, no text, no labels, no watermarks, "
    "modern healthcare aesthetics, 16:9 format"
)

CATEGORY_CONTEXT: dict[str, str] = {
    "cardiology":                 "human heart anatomy, cardiovascular system",
    "cardiology-advanced":        "advanced cardiac imaging echocardiogram heart monitor",
    "neurology":                  "human brain neuroscience illustration",
    "neurology-advanced":         "advanced brain MRI neural network microscopy",
    "pharmacology":               "pharmaceutical pills and molecular structures",
    "drug-reference":             "medication bottles laboratory glassware",
    "drugs":                      "medication tablets capsules pharmaceutical",
    "oncology":                   "cancer cell immunotherapy research laboratory",
    "infectious-diseases":        "virus bacteria microscopy pathology",
    "infectious-specific":        "virus bacteria microscopy pathology",
    "surgery-procedures":         "surgical instruments operating room",
    "surgery":                    "surgical team operating room sterile instruments",
    "diagnostics":                "medical diagnostic equipment laboratory",
    "diagnostics-interpretation": "ECG MRI scan radiology reading",
    "procedures":                 "medical procedure clinical equipment",
    "ob-gyn":                     "maternal fetal medicine clinical ultrasound monitor hospital equipment",
    "pediatrics":                 "pediatric medicine children healthcare",
    "pediatrics-specific":        "pediatric specialist children clinical examination",
    "endocrinology":              "endocrine glands hormone system anatomy",
    "symptoms":                   "human body clinical symptoms anatomy",
    "psychiatry":                 "mental health brain psychology illustration",
    "mental-health":              "mental health mindfulness calm brain illustration",
    "pulmonology":                "lungs respiratory system anatomy",
    "gastroenterology":           "gastrointestinal tract digestive system anatomy",
    "nephrology":                 "kidney renal anatomy urinary system",
    "rheumatology":               "joints arthritis musculoskeletal system",
    "hematology":                 "blood cells hematology microscopy",
    "dermatology":                "skin dermatology cross-section anatomy",
    "ophthalmology":              "eye anatomy ophthalmology retina",
    "orthopedics":                "bone joint orthopedic anatomy",
    "emergency":                  "emergency medicine critical care resuscitation",
    "veterinary":                 "veterinary medicine animal anatomy",
    "immunology":                 "immune system cells antibody illustration",
    "allergy-immunology":         "immune system allergy cells antibody illustration",
    "genetics":                   "DNA helix genetics chromosome",
    "pathology":                  "pathology tissue microscopy slide",
    "internal-medicine":          "clinical medicine anatomy illustration",
    "geriatrics":                 "elderly care gerontology clinical medicine",
    "radiology":                  "radiology MRI CT scan imaging equipment",
    "diseases":                   "medical disease clinical anatomy illustration",
    "sports-medicine":            "sports medicine athlete injury rehabilitation",
    "rehabilitation":             "physical therapy rehabilitation exercise clinical",
    "palliative-care":            "compassionate palliative care hospital serene",
    "toxicology":                 "toxicology chemical molecular poison antidote laboratory",
    "public-health":              "public health epidemiology population medicine",
    "critical-care":              "intensive care unit ICU ventilator monitors",
    "anesthesiology":             "anesthesia equipment operating room monitors",
    "biochemistry":               "biochemistry molecular biology laboratory",
    "clinical-nutrition":         "clinical nutrition food vitamins supplements",
    "clinical-syndromes":         "clinical syndrome medical anatomy illustration",
    "addiction-medicine":         "addiction medicine neuroscience brain pathways",
    "lab-medicine":               "laboratory medicine blood test tubes centrifuge",
    "mens-health":                "men healthcare clinical anatomy illustration",
    "microbiology":               "microbiology bacteria culture laboratory microscope",
    "nutrition":                  "nutrition healthy food vitamins minerals",
    "occupational-medicine":      "occupational medicine workplace safety equipment",
    "pain-management":            "pain management neurology anatomy spine",
    "physiology":                 "human physiology anatomy organ systems",
    "preventive-medicine":        "preventive medicine vaccination health screening",
    "sexual-health":              "sexual health clinical anatomy medical illustration",
    "sleep-medicine":             "sleep medicine polysomnography brain waves monitor",
    "travel-medicine":            "travel medicine vaccination globe health",
    "urology":                    "urology kidney bladder anatomy clinical",
    "womens-health":              "women healthcare clinical anatomy illustration",
    "immunology":                 "immune system cells antibody T-cell B-cell",
}


def build_prompt(title: str, category: str) -> str:
    cat_context = CATEGORY_CONTEXT.get(category, "medical healthcare clinical anatomy")
    words = title.split()[:8]
    short_title = " ".join(words)
    return f"{short_title}, {cat_context}, {STYLE}"


# ── Metadata embedding ────────────────────────────────────────────────────────

def _build_xmp(title: str, description: str, article_url: str) -> str:
    """Build XMP packet — Google reads this for image attribution."""
    copyright_str = f"© MedMind AI — {SITE_URL}"
    credit = f"MedMind AI ({SITE_URL})"

    # Escape XML special chars
    def esc(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    return (
        '<?xpacket begin="\xef\xbb\xbf" id="W5M0MpCehiHzreSzNTczkc9d"?>'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
        '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
        '<rdf:Description rdf:about=""'
        ' xmlns:dc="http://purl.org/dc/elements/1.1/"'
        ' xmlns:xmpRights="http://ns.adobe.com/xap/1.0/rights/"'
        ' xmlns:photoshop="http://ns.adobe.com/photoshop/1.0/"'
        ' xmlns:xmp="http://ns.adobe.com/xap/1.0/">'
        f'<dc:title><rdf:Alt><rdf:li xml:lang="x-default">{esc(title)}</rdf:li></rdf:Alt></dc:title>'
        f'<dc:description><rdf:Alt><rdf:li xml:lang="x-default">{esc(description)}</rdf:li></rdf:Alt></dc:description>'
        f'<dc:rights><rdf:Alt><rdf:li xml:lang="x-default">{esc(copyright_str)}</rdf:li></rdf:Alt></dc:rights>'
        f'<dc:source>{esc(article_url)}</dc:source>'
        f'<dc:publisher><rdf:Bag><rdf:li>{esc(SITE_URL)}</rdf:li></rdf:Bag></dc:publisher>'
        f'<xmpRights:WebStatement>{esc(article_url)}</xmpRights:WebStatement>'
        '<xmpRights:Marked>True</xmpRights:Marked>'
        f'<photoshop:Credit>{esc(credit)}</photoshop:Credit>'
        f'<photoshop:Source>{esc(SITE_URL)}</photoshop:Source>'
        '</rdf:Description>'
        '</rdf:RDF>'
        '</x:xmpmeta>'
        '<?xpacket end="w"?>'
    )


def _inject_xmp(jpeg_bytes: bytes, xmp_str: str) -> bytes:
    """Insert XMP APP1 segment right after JPEG SOI marker."""
    xmp_header = b"http://ns.adobe.com/xap/1.0/\x00"
    payload = xmp_header + xmp_str.encode("utf-8")
    length = len(payload) + 2  # +2 for the length field itself
    chunk = b"\xff\xe1" + struct.pack(">H", length) + payload
    return jpeg_bytes[:2] + chunk + jpeg_bytes[2:]


def embed_metadata(
    raw_jpeg: bytes,
    title: str,
    description: str,
    article_url: str,
) -> bytes:
    """
    Embed EXIF + XMP metadata into JPEG bytes.
    - EXIF: ImageDescription, Copyright, Artist (read by basic viewers)
    - XMP:  dc:title, dc:description, dc:rights, dc:source, xmpRights:WebStatement
            (read by Google Images for attribution and site verification)
    """
    copyright_str = f"© MedMind AI — {SITE_URL}"
    artist_str    = f"MedMind AI Editorial ({SITE_URL})"

    # ── EXIF ──────────────────────────────────────────────────────────────────
    try:
        img = Image.open(io.BytesIO(raw_jpeg))

        # UTF-16LE for Windows XP tags (XPTitle, XPComment, XPAuthor)
        def utf16le(s: str) -> bytes:
            return s.encode("utf-16-le") + b"\x00\x00"

        exif_dict: dict = {
            "0th": {
                piexif.ImageIFD.ImageDescription: description[:500].encode("utf-8", errors="replace"),
                piexif.ImageIFD.Copyright:        copyright_str.encode("utf-8", errors="replace"),
                piexif.ImageIFD.Artist:           artist_str.encode("utf-8", errors="replace"),
                piexif.ImageIFD.XPTitle:          utf16le(title[:100]),
                piexif.ImageIFD.XPComment:        utf16le(f"{description[:200]} {article_url}"),
                piexif.ImageIFD.XPAuthor:         utf16le("MedMind AI"),
                # Software tag — shows generator
                piexif.ImageIFD.Software:         b"MedMind AI Image Pipeline",
            },
            "Exif": {
                # UserComment — arbitrary string, not language-coded
                piexif.ExifIFD.UserComment: (
                    b"ASCII\x00\x00\x00" +
                    f"Source: {article_url}".encode("ascii", errors="replace")
                ),
            },
            "GPS":  {},
            "1st":  {},
        }
        exif_bytes = piexif.dump(exif_dict)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=92, exif=exif_bytes)
        jpeg_with_exif = buf.getvalue()
    except Exception as e:
        print(f"    ⚠ EXIF embed failed ({e}), using raw bytes")
        jpeg_with_exif = raw_jpeg

    # ── XMP (injected after EXIF) ─────────────────────────────────────────────
    try:
        xmp = _build_xmp(title, description, article_url)
        final = _inject_xmp(jpeg_with_exif, xmp)
    except Exception as e:
        print(f"    ⚠ XMP inject failed ({e}), using EXIF-only")
        final = jpeg_with_exif

    return final


# ── Together.ai ───────────────────────────────────────────────────────────────

def load_key() -> str:
    if TOGETHER_KEY_FILE.exists():
        return TOGETHER_KEY_FILE.read_text().strip()
    key = os.environ.get("TOGETHER_API_KEY", "")
    if key:
        return key
    sys.exit(
        f"Together.ai key not found at {TOGETHER_KEY_FILE}\n"
        "Set TOGETHER_API_KEY env var or place key in that file."
    )


def generate_image(prompt: str, key: str) -> bytes | None:
    """Call Together.ai FLUX.1-schnell and return raw JPEG bytes."""
    try:
        r = httpx.post(
            TOGETHER_URL,
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model":  TOGETHER_MODEL,
                "prompt": prompt,
                "width":  1280,
                "height": 720,
                "steps":  4,
                "n":      1,
            },
            timeout=90,
        )
        if r.status_code != 200:
            try:
                msg = r.json().get("error", {}).get("message", r.text[:120])
            except Exception:
                msg = r.text[:120]
            print(f"    ✗ Together error {r.status_code}: {msg}")
            return None

        item = r.json()["data"][0]
        import base64
        b64 = item.get("b64_json")
        if b64:
            return base64.b64decode(b64)
        url = item.get("url")
        if url:
            img_r = httpx.get(url, timeout=30)
            if img_r.status_code == 200:
                return img_r.content

    except Exception as e:
        print(f"    ✗ Request failed: {e}")
    return None


# ── DB ────────────────────────────────────────────────────────────────────────

def get_articles(
    session: Session,
    limit: int,
    category: str | None,
    slug: str | None,
    overwrite: bool,
) -> list[dict]:
    filters = ["is_published = true"]
    params: dict = {}
    if not overwrite:
        filters.append("cover_image IS NULL")
    if category:
        filters.append("category = :category")
        params["category"] = category
    if slug:
        filters.append("slug = :slug")
        params["slug"] = slug
    where = " AND ".join(filters)
    rows = session.execute(
        text(
            f"SELECT id, slug, title, category, excerpt "
            f"FROM articles WHERE {where} ORDER BY RANDOM() LIMIT :limit"
        ),
        {**params, "limit": limit},
    ).fetchall()
    return [dict(r._mapping) for r in rows]


def save_cover_image(session: Session, article_id: str, image_url: str) -> None:
    session.execute(
        text("UPDATE articles SET cover_image = :url WHERE id = :id"),
        {"url": image_url, "id": article_id},
    )
    session.commit()


# ── Media dir ─────────────────────────────────────────────────────────────────

def resolve_media_dir() -> Path:
    """Resolve the media directory — Docker volume on host takes priority."""
    if DOCKER_VOL_DIR.parent.exists():
        DOCKER_VOL_DIR.mkdir(parents=True, exist_ok=True)
        return DOCKER_VOL_DIR
    if MEDIA_DIR.parent.exists():
        MEDIA_DIR.mkdir(parents=True, exist_ok=True)
        return MEDIA_DIR
    fallback = Path("./data/media/articles")
    fallback.mkdir(parents=True, exist_ok=True)
    print(f"WARNING: saving to local {fallback} — images won't be served!")
    return fallback


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate cover images for MedMind articles via Together.ai FLUX"
    )
    parser.add_argument("--limit",     type=int,   default=20,   help="Max articles per run (default 20)")
    parser.add_argument("--category",  type=str,   default=None, help="Filter by category slug")
    parser.add_argument("--slug",      type=str,   default=None, help="Single article by slug")
    parser.add_argument("--dry-run",   action="store_true",      help="Show prompts only, no generation")
    parser.add_argument("--overwrite", action="store_true",      help="Regenerate even if image exists")
    parser.add_argument("--delay",     type=float, default=1.5,  help="Seconds between API calls (default 1.5)")
    args = parser.parse_args()

    key       = load_key()
    media_dir = resolve_media_dir()
    engine    = create_engine(DATABASE_URL)

    print(f"Media dir: {media_dir}")

    with Session(engine) as session:
        articles = get_articles(session, args.limit, args.category, args.slug, args.overwrite)

    if not articles:
        print("✓ No articles found needing images.")
        return

    print(f"Found {len(articles)} articles to process\n")

    success = failed = skipped = 0

    with Session(engine) as session:
        for i, art in enumerate(articles, 1):
            slug     = art["slug"]
            title    = art["title"]
            category = art["category"]
            excerpt  = (art["excerpt"] or "")[:300]

            prompt      = build_prompt(title, category)
            article_url = f"{SITE_URL}/articles/{slug}"

            print(f"[{i}/{len(articles)}] {title[:70]}")
            print(f"  category: {category}")
            print(f"  url:      {article_url}")
            print(f"  prompt:   {prompt[:100]}…")

            if args.dry_run:
                print("  [dry-run]\n")
                skipped += 1
                continue

            out_file  = media_dir / f"{slug}.jpg"
            image_url = f"{MEDIA_URL_PREFIX}/{slug}.jpg"

            if out_file.exists() and not args.overwrite:
                save_cover_image(session, art["id"], image_url)
                print(f"  ✓ Exists → DB updated\n")
                success += 1
                continue

            raw = generate_image(prompt, key)
            if raw is None:
                print("  ✗ Generation failed\n")
                failed += 1
            else:
                # Embed metadata before saving
                final = embed_metadata(raw, title, excerpt or title, article_url)
                out_file.write_bytes(final)
                save_cover_image(session, art["id"], image_url)
                size_kb = len(final) // 1024
                print(f"  ✓ {size_kb} KB saved + EXIF/XMP → {image_url}\n")
                success += 1

            if i < len(articles):
                time.sleep(args.delay)

    print("─" * 60)
    print(f"Done: {success} saved, {skipped} dry-run, {failed} failed")
    if failed:
        print("Re-run to retry failed articles (still NULL in DB)")


if __name__ == "__main__":
    main()
