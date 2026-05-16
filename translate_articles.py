"""
Batch article translation using Google Translate (free).

Translates articles that:
  - Have no translation (title == original English)
  - Have English body (body not translated)

Run inside backend container:
    python3 /translate_articles.py
    python3 /translate_articles.py --force   # re-translate all
    python3 /translate_articles.py --limit 50

Stats:
  ~439 articles × 6 locales
  ~0.25s per block × ~15 blocks = ~4s per locale per article
  ~24s per article × 439 = ~3 hours total
"""
import asyncio
import json
import os
import time
import urllib.parse
import urllib.request
import psycopg2
from psycopg2.extras import execute_values

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://medmind:medmind_secret@postgres:5432/medmind"
).replace("postgresql+asyncpg://", "postgresql://")

LOCALES = ["ru", "de", "fr", "es", "tr", "ar"]
DELAY   = 0.25  # seconds between Google Translate calls


def gtranslate(text: str, locale: str) -> str:
    """Google Translate free endpoint."""
    if not text or not text.strip():
        return text
    try:
        url = (
            "https://translate.googleapis.com/translate_a/single"
            "?client=gtx&sl=en&tl=" + locale
            + "&dt=t&q=" + urllib.parse.quote(text[:4500])
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read())
        return "".join(part[0] for part in data[0] if part[0])
    except Exception as e:
        print(f"    translate error ({locale}): {e}")
        return text


def translate_blocks(blocks: list, locale: str) -> list:
    """Translate all body blocks."""
    result = []
    for block in blocks:
        btype = block.get("type", "")
        nb = dict(block)
        if btype in ("h2", "h3", "p", "callout"):
            if block.get("content"):
                nb["content"] = gtranslate(block["content"], locale)
                time.sleep(DELAY)
        elif btype == "ul":
            items = block.get("items", [])
            new_items = []
            for item in items:
                new_items.append(gtranslate(item, locale))
                time.sleep(DELAY * 0.5)
            nb["items"] = new_items
        elif btype == "table":
            nb["headers"] = [gtranslate(h, locale) for h in block.get("headers", [])]
            nb["rows"]    = [
                [gtranslate(c, locale) for c in row]
                for row in block.get("rows", [])
            ]
            time.sleep(DELAY)
        result.append(nb)
    return result


def translate_article(article_id: str, title: str, excerpt: str,
                      body: list, locale: str) -> dict:
    """Translate one article to one locale. Returns dict with translated fields."""
    tr_title   = gtranslate(title,   locale)
    time.sleep(DELAY)
    tr_excerpt = gtranslate(excerpt, locale)
    time.sleep(DELAY)
    tr_body    = translate_blocks(body, locale)
    return {"title": tr_title, "excerpt": tr_excerpt, "body": tr_body}


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true",
                        help="Re-translate even already translated articles")
    parser.add_argument("--limit", type=int, default=9999,
                        help="Max articles to process")
    parser.add_argument("--locale", type=str, default=None,
                        help="Only this locale (e.g. ru)")
    args = parser.parse_args()

    locales = [args.locale] if args.locale else LOCALES

    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False

    with conn.cursor() as cur:
        if args.force:
            cur.execute("""
                SELECT a.id, a.title, a.excerpt, a.body
                FROM articles a
                WHERE a.is_published = true
                ORDER BY a.created_at DESC
                LIMIT %s
            """, (args.limit,))
        else:
            # Articles where ANY locale has title = original (not translated)
            cur.execute("""
                SELECT a.id, a.title, a.excerpt, a.body
                FROM articles a
                WHERE a.is_published = true
                  AND EXISTS (
                    SELECT 1 FROM article_translations t
                    WHERE t.article_id = a.id
                      AND (t.title = a.title OR t.body IS NULL OR t.body::text = '[]')
                  )
                ORDER BY a.created_at DESC
                LIMIT %s
            """, (args.limit,))
        rows = cur.fetchall()

    total = len(rows)
    print(f"Articles to process: {total}")
    print(f"Locales: {locales}")
    print(f"Estimated time: ~{total * len(locales) * 30 // 60} minutes\n")

    done = 0
    errors = 0

    for i, (article_id, title, excerpt, body) in enumerate(rows):
        print(f"[{i+1}/{total}] {title[:60]}")

        body_list = body if isinstance(body, list) else (json.loads(body) if body else [])

        # Find which locales still need translation for this article
        with conn.cursor() as cur:
            cur.execute(
                "SELECT locale, title FROM article_translations WHERE article_id = %s",
                (str(article_id),)
            )
            existing = {r[0]: r[1] for r in cur.fetchall()}

        for locale in locales:
            existing_title = existing.get(locale)
            # Skip if already properly translated (unless --force)
            if not args.force and existing_title and existing_title != title:
                continue

            print(f"  → {locale}…", end=" ", flush=True)
            try:
                tr = translate_article(str(article_id), title, excerpt, body_list, locale)
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO article_translations
                            (article_id, locale, title, excerpt, body, status)
                        VALUES (%s, %s, %s, %s, %s::jsonb, 'done')
                        ON CONFLICT (article_id, locale) DO UPDATE
                          SET title   = EXCLUDED.title,
                              excerpt = EXCLUDED.excerpt,
                              body    = EXCLUDED.body,
                              status  = 'done'
                    """, (
                        str(article_id), locale,
                        tr["title"], tr["excerpt"],
                        json.dumps(tr["body"], ensure_ascii=False)
                    ))
                conn.commit()
                print("✓")
                done += 1
            except Exception as e:
                print(f"✗ {e}")
                conn.rollback()
                errors += 1

        if (i + 1) % 10 == 0:
            print(f"\n  Progress: {done} translations done, {errors} errors\n")

    conn.close()
    print(f"\n✅ Done. Translated: {done}, Errors: {errors}")


if __name__ == "__main__":
    main()
