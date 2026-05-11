"""
Translate medical_images title + description into 6 languages.
Uses Google Translate free endpoint (same approach as article body translations).
Run inside backend container: python3 /translate_images.py

Stats: ~6,772 images × 6 languages = ~40,632 translations
Each batch: 50 images, ~0.5s → estimated ~13 minutes total
"""
import asyncio
import json
import os
import time
import urllib.request
import urllib.parse
import psycopg2
from psycopg2.extras import execute_values

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://medmind:medmind_secret@postgres:5432/medmind"
).replace("postgresql+asyncpg://", "postgresql://")

LOCALES = ["ru", "de", "fr", "es", "tr", "ar"]
BATCH   = 30   # images per iteration
DELAY   = 0.4  # seconds between Google API calls


def gtranslate(text: str, target: str) -> str:
    """Call Google Translate free endpoint."""
    if not text or not text.strip():
        return text
    url = (
        "https://translate.googleapis.com/translate_a/single"
        "?client=gtx&sl=en&tl=" + target +
        "&dt=t&q=" + urllib.parse.quote(text[:4500])
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        return "".join(part[0] for part in data[0] if part[0])
    except Exception as e:
        print(f"    translate error ({target}): {e}")
        return text


def main():
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False

    # Count what's already done
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM medical_image_translations")
        already_done = cur.fetchone()[0]

    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM medical_images WHERE is_active = true")
        total_images = cur.fetchone()[0]

    print(f"Images: {total_images} | Translations already: {already_done}")
    print(f"Target: {total_images * len(LOCALES)} total | Remaining: {total_images * len(LOCALES) - already_done}")
    print()

    # Fetch images that still need translation in at least one locale
    with conn.cursor() as cur:
        cur.execute("""
            SELECT m.id, m.title, m.description
            FROM medical_images m
            WHERE m.is_active = true
              AND (
                SELECT COUNT(DISTINCT locale)
                FROM medical_image_translations t
                WHERE t.image_id = m.id
              ) < %s
            ORDER BY m.view_count DESC
        """, (len(LOCALES),))
        rows = cur.fetchall()

    print(f"Images needing translation: {len(rows)}")

    translated = 0
    errors = 0

    for i, (img_id, title, description) in enumerate(rows):
        # Find which locales are missing for this image
        with conn.cursor() as cur:
            cur.execute(
                "SELECT locale FROM medical_image_translations WHERE image_id = %s",
                (img_id,)
            )
            done_locales = {r[0] for r in cur.fetchall()}

        missing = [loc for loc in LOCALES if loc not in done_locales]
        if not missing:
            continue

        if i % 50 == 0:
            print(f"[{i+1}/{len(rows)}] Processing image {str(img_id)[:8]}…")

        records = []
        for locale in missing:
            try:
                tr_title = gtranslate(title or "", locale)
                time.sleep(DELAY)
                tr_desc  = gtranslate(description or "", locale) if description else None
                if description:
                    time.sleep(DELAY)
                records.append((str(img_id), locale, tr_title, tr_desc))
                translated += 1
            except Exception as e:
                print(f"  ✗ {locale}: {e}")
                errors += 1

        if records:
            with conn.cursor() as cur:
                execute_values(cur, """
                    INSERT INTO medical_image_translations (image_id, locale, title, description)
                    VALUES %s
                    ON CONFLICT (image_id, locale) DO UPDATE
                      SET title = EXCLUDED.title,
                          description = EXCLUDED.description
                """, records)
            conn.commit()

        if i % 100 == 99:
            print(f"  Progress: {translated} translated, {errors} errors")

    conn.close()
    print(f"\n✅ Done. Translated: {translated}, Errors: {errors}")


if __name__ == "__main__":
    main()
