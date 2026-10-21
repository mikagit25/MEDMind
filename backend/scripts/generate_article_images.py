#!/usr/bin/env python3
"""
Fetch cover images for MedMind articles that lack them.

Uses Pexels API (free, no cost) to find professional medical stock photos.
Each image is saved with full EXIF + XMP metadata (title, description,
copyright, source URL) so Google Images can verify and attribute the image
to medmind.pro — helping the site appear in image search results.

Image metadata embedded:
  EXIF: ImageDescription, Copyright, Artist, XPTitle, XPComment
  XMP:  dc:title, dc:description, dc:rights, dc:source, photoshop:Credit,
        xmpRights:WebStatement (site URL)

Usage:
  python3 backend/scripts/generate_article_images.py --limit 50
  python3 ... --category oncology --limit 100   # specific category
  python3 ... --dry-run --limit 20              # preview queries only
  python3 ... --slug some-article-slug          # single article
  python3 ... --overwrite                       # re-fetch existing

API key:  PEXELS_API_KEY env var (or from backend/.env)
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

SITE_URL         = "https://medmind.pro"
PEXELS_URL       = "https://api.pexels.com/v1/search"

DOCKER_VOL_DIR   = Path("/var/lib/docker/volumes/medmind_media_data/_data/articles")
MEDIA_DIR        = Path("/app/data/media/articles")   # inside Docker container
MEDIA_URL_PREFIX = "/media/articles"

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

CATEGORY_QUERIES: dict[str, list[str]] = {
    "cardiology":                 ["cardiology heart doctor", "cardiac surgery hospital", "heart stethoscope medical"],
    "cardiology-advanced":        ["echocardiogram heart monitor", "cardiac catheterization", "cardiologist hospital"],
    "neurology":                  ["neurology brain scan", "neurologist hospital", "brain MRI doctor"],
    "neurology-advanced":         ["brain MRI scan", "neurosurgery hospital", "neurological examination"],
    "pharmacology":               ["pharmacy medicine pills", "pharmacist medication", "pills capsules medical"],
    "drug-reference":             ["medication pharmacy", "pills medicine bottles", "pharmacist laboratory"],
    "drugs":                      ["medicine tablets pills", "pharmacy medication", "drug capsules"],
    "oncology":                   ["oncology cancer treatment", "chemotherapy hospital", "cancer research laboratory"],
    "infectious-diseases":        ["infectious disease hospital", "microbiology laboratory", "bacteria microscope"],
    "infectious-specific":        ["infection control hospital", "microbiology lab test", "virus research"],
    "surgery-procedures":         ["surgery operating room", "surgeon hospital", "surgical instruments"],
    "surgery":                    ["surgeon operating room", "surgical team hospital", "laparoscopy surgery"],
    "diagnostics":                ["medical diagnostics laboratory", "blood test tubes", "diagnostic equipment hospital"],
    "diagnostics-interpretation": ["radiology doctor reading scan", "MRI scan medical", "ECG monitor hospital"],
    "procedures":                 ["medical procedure hospital", "doctor patient clinical", "medical equipment"],
    "ob-gyn":                     ["gynecology ultrasound pregnancy", "obstetrics hospital delivery", "prenatal care doctor"],
    "pediatrics":                 ["pediatrics children hospital", "pediatrician child doctor", "children healthcare"],
    "pediatrics-specific":        ["pediatric specialist child", "children hospital doctor", "pediatric care"],
    "endocrinology":              ["endocrinology doctor", "diabetes blood glucose", "thyroid ultrasound"],
    "symptoms":                   ["patient doctor hospital examination", "clinical examination", "doctor diagnosis"],
    "psychiatry":                 ["psychiatry mental health doctor", "therapy session counseling", "mental health clinic"],
    "mental-health":              ["mental health therapy", "counseling psychologist", "mindfulness meditation"],
    "pulmonology":                ["lungs pulmonology doctor", "chest X-ray respiratory", "asthma inhaler lungs"],
    "gastroenterology":           ["gastroenterology endoscopy", "digestive medicine hospital", "gastroscopy procedure"],
    "nephrology":                 ["nephrology kidney doctor", "dialysis kidney treatment", "kidney ultrasound"],
    "rheumatology":               ["rheumatology arthritis joints", "joint pain hands doctor", "physiotherapy joints"],
    "hematology":                 ["hematology blood laboratory", "blood smear microscope", "blood test doctor"],
    "dermatology":                ["dermatology skin doctor", "dermatologist examination", "skin care medical"],
    "ophthalmology":              ["ophthalmology eye doctor", "eye examination slit lamp", "retinal examination"],
    "orthopedics":                ["orthopedics bone surgery", "X-ray bone fracture", "orthopedic surgeon"],
    "emergency":                  ["emergency room hospital", "emergency medicine doctor", "ambulance emergency"],
    "veterinary":                 ["veterinarian animal clinic", "vet doctor animal", "veterinary examination"],
    "immunology":                 ["immunology laboratory research", "vaccine injection doctor", "immune system research"],
    "allergy-immunology":         ["allergy test doctor", "allergy clinic treatment", "immunology hospital"],
    "genetics":                   ["genetics DNA laboratory", "genetic research scientist", "DNA sequencing lab"],
    "pathology":                  ["pathology laboratory microscope", "tissue biopsy laboratory", "pathologist microscope"],
    "internal-medicine":          ["internal medicine doctor examination", "physician hospital rounds", "clinical medicine"],
    "geriatrics":                 ["elderly care doctor hospital", "geriatric patient care", "senior healthcare"],
    "radiology":                  ["radiology MRI machine hospital", "radiologist reading scan", "CT scan machine"],
    "diseases":                   ["disease treatment hospital doctor", "medical diagnosis clinic", "clinical examination"],
    "sports-medicine":            ["sports medicine physiotherapy", "athlete injury rehabilitation", "sports physical therapy"],
    "rehabilitation":             ["rehabilitation physical therapy", "physiotherapy exercise", "recovery hospital"],
    "palliative-care":            ["palliative care patient hospital", "hospice compassionate care", "nurse patient comfort"],
    "toxicology":                 ["toxicology laboratory research", "poison control laboratory", "chemical laboratory safety"],
    "public-health":              ["public health vaccination", "epidemiology research", "health screening community"],
    "critical-care":              ["intensive care unit ICU", "critical care ventilator hospital", "ICU nurse monitors"],
    "anesthesiology":             ["anesthesia operating room", "anesthesiologist surgery", "surgery monitors anesthesia"],
    "biochemistry":               ["biochemistry laboratory research", "molecular biology scientist", "lab chemistry"],
    "clinical-nutrition":         ["clinical nutrition dietitian", "healthy food nutrition", "diet consultation doctor"],
    "clinical-syndromes":         ["clinical examination doctor", "medical syndrome hospital", "physician diagnosis"],
    "addiction-medicine":         ["addiction recovery therapy", "rehabilitation addiction treatment", "counseling recovery"],
    "lab-medicine":               ["medical laboratory blood test", "lab technician test tubes", "clinical laboratory"],
    "mens-health":                ["men health doctor checkup", "male health clinic", "men healthcare examination"],
    "microbiology":               ["microbiology laboratory culture", "microscope bacteria scientist", "lab microbiology"],
    "nutrition":                  ["healthy nutrition food", "dietitian consultation", "vitamins supplements health"],
    "occupational-medicine":      ["occupational health workplace safety", "worker health examination", "occupational therapy"],
    "pain-management":            ["pain management doctor", "physical therapy pain", "spine doctor back pain"],
    "physiology":                 ["human anatomy physiology", "medical physiology doctor", "organ anatomy clinical"],
    "preventive-medicine":        ["preventive medicine vaccination", "health screening doctor", "medical checkup prevention"],
    "sexual-health":              ["sexual health clinic doctor", "reproductive health medical", "health consultation"],
    "sleep-medicine":             ["sleep study polysomnography", "sleep clinic patient", "sleep disorder doctor"],
    "travel-medicine":            ["travel vaccination clinic", "travel medicine doctor", "vaccine travel health"],
    "urology":                    ["urology doctor hospital", "urologist examination", "kidney bladder doctor"],
    "womens-health":              ["women health doctor gynecology", "womens healthcare clinic", "gynecologist examination"],
}

FALLBACK_QUERIES = ["doctor hospital medical", "healthcare clinic", "medical professional hospital"]


def get_pexels_image(category: str, key: str) -> bytes | None:
    """Search Pexels for a landscape medical photo matching the category."""
    queries = CATEGORY_QUERIES.get(category, FALLBACK_QUERIES)
    for query in queries:
        try:
            resp = httpx.get(
                PEXELS_URL,
                headers={"Authorization": key},
                params={"query": query, "per_page": 5, "orientation": "landscape"},
                timeout=15,
            )
            if resp.status_code != 200:
                continue
            photos = resp.json().get("photos", [])
            if not photos:
                continue
            photo_url = photos[0]["src"].get("large2x") or photos[0]["src"].get("original")
            img_resp = httpx.get(photo_url, timeout=30, follow_redirects=True)
            if img_resp.status_code == 200:
                # Convert to JPEG
                img = Image.open(io.BytesIO(img_resp.content)).convert("RGB")
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=92)
                return buf.getvalue()
        except Exception as e:
            print(f"    ✗ Pexels error for '{query}': {e}")
            continue
    return None


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


def load_pexels_key() -> str:
    key = os.environ.get("PEXELS_API_KEY", "")
    if not key:
        # Try loading from backend .env
        env_file = Path(__file__).parent.parent / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("PEXELS_API_KEY="):
                    key = line.split("=", 1)[1].strip()
                    break
    if not key:
        sys.exit("PEXELS_API_KEY not set. Add it to backend/.env or export as env var.")
    return key


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
        description="Fetch cover images for MedMind articles via Pexels (free stock photos)"
    )
    parser.add_argument("--limit",     type=int,   default=20,   help="Max articles per run (default 20)")
    parser.add_argument("--category",  type=str,   default=None, help="Filter by category slug")
    parser.add_argument("--slug",      type=str,   default=None, help="Single article by slug")
    parser.add_argument("--dry-run",   action="store_true",      help="Show prompts only, no generation")
    parser.add_argument("--overwrite", action="store_true",      help="Regenerate even if image exists")
    parser.add_argument("--delay",     type=float, default=1.5,  help="Seconds between API calls (default 1.5)")
    args = parser.parse_args()

    key       = load_pexels_key()
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

            queries     = CATEGORY_QUERIES.get(category, FALLBACK_QUERIES)
            article_url = f"{SITE_URL}/articles/{slug}"

            print(f"[{i}/{len(articles)}] {title[:70]}")
            print(f"  category: {category}")
            print(f"  query:    {queries[0]}")

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

            raw = get_pexels_image(category, key)
            if raw is None:
                print("  ✗ Pexels fetch failed\n")
                failed += 1
            else:
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
