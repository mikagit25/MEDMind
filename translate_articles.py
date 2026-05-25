"""
Batch article translation using Google Translate (free).

Translates articles that:
  - Have no translation (title == original English)
  - Have English body (body identical to original — old pipeline bug)
  - Have NULL or empty body

Run on host (uses 172.18.0.3:5432):
    python3 /opt/medmind/translate_articles.py
    python3 /opt/medmind/translate_articles.py --force      # re-translate all
    python3 /opt/medmind/translate_articles.py --limit 50
    python3 /opt/medmind/translate_articles.py --locale ru  # one locale only
    python3 /opt/medmind/translate_articles.py --body-only  # fix bodies only
"""
import json
import os
import time
import urllib.parse
import urllib.request
import psycopg2

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://medmind:medmind_secret@172.18.0.3:5432/medmind"
).replace("postgresql+asyncpg://", "postgresql://")

LOCALES = ["ru", "de", "fr", "es", "tr", "ar"]
DELAY   = 0.3   # seconds between Google Translate calls


# ── Google Translate ───────────────────────────────────────────────────────────

def gtranslate(text: str, locale: str) -> str:
    """Google Translate free endpoint. Returns translated text or original on error."""
    if not text or not text.strip():
        return text
    try:
        url = (
            "https://translate.googleapis.com/translate_a/single"
            "?client=gtx&sl=en&tl=" + locale
            + "&dt=t&q=" + urllib.parse.quote(text[:4500])
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        return "".join(part[0] for part in data[0] if part[0])
    except Exception as e:
        print(f"    translate error ({locale}): {e}")
        return text


def translate_blocks(blocks: list, locale: str) -> list:
    """Translate all body blocks, preserving structure."""
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
            nb["items"] = []
            for item in items:
                nb["items"].append(gtranslate(item, locale))
                time.sleep(DELAY * 0.5)
        elif btype == "table":
            nb["headers"] = [gtranslate(h, locale) for h in block.get("headers", [])]
            nb["rows"] = [
                [gtranslate(c, locale) for c in row]
                for row in block.get("rows", [])
            ]
            time.sleep(DELAY)
        result.append(nb)
    return result


def translate_article(title: str, excerpt: str, body: list, locale: str) -> dict:
    """Translate one article to one locale."""
    tr_title   = gtranslate(title, locale)
    time.sleep(DELAY)
    tr_excerpt = gtranslate(excerpt, locale)
    time.sleep(DELAY)
    tr_body    = translate_blocks(body, locale)
    return {"title": tr_title, "excerpt": tr_excerpt, "body": tr_body}


def translate_body_only(body: list, locale: str) -> list:
    """Translate just the body blocks (title/excerpt already translated)."""
    return translate_blocks(body, locale)


# ── DB helpers ─────────────────────────────────────────────────────────────────

def needs_body_translation(conn, article_id: str, locale: str, orig_body_text: str) -> bool:
    """Return True if this locale's body is still the original English."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT body::text FROM article_translations WHERE article_id=%s AND locale=%s",
            (str(article_id), locale)
        )
        row = cur.fetchone()
        if not row:
            return True  # no translation exists
        existing_body_text = row[0] or "[]"
        # Body is English if identical to original, or empty
        return existing_body_text in ("[]", "null", "") or existing_body_text == orig_body_text


def upsert_translation(conn, article_id: str, locale: str,
                       title: str, excerpt: str, body: list):
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
            title, excerpt,
            json.dumps(body, ensure_ascii=False)
        ))
    conn.commit()


def update_body_only(conn, article_id: str, locale: str, body: list):
    """Update only the body of an existing translation."""
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE article_translations
               SET body = %s::jsonb, status = 'done'
             WHERE article_id = %s AND locale = %s
        """, (
            json.dumps(body, ensure_ascii=False),
            str(article_id), locale
        ))
    conn.commit()


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--force",     action="store_true",
                        help="Re-translate everything, including already translated")
    parser.add_argument("--limit",     type=int, default=9999,
                        help="Max articles to process")
    parser.add_argument("--locale",    type=str, default=None,
                        help="Only this locale (e.g. ru)")
    parser.add_argument("--body-only", action="store_true",
                        help="Only fix bodies where title is already translated")
    args = parser.parse_args()

    locales = [args.locale] if args.locale else LOCALES

    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False

    # Select articles that need work
    with conn.cursor() as cur:
        if args.force:
            cur.execute("""
                SELECT a.id, a.title, a.excerpt, a.body, a.body::text as body_text
                FROM articles a
                WHERE a.is_published = true
                ORDER BY a.created_at DESC
                LIMIT %s
            """, (args.limit,))
        else:
            # Pick articles where at least one locale needs work:
            # - title not translated (= original English title)
            # - body NULL / empty
            # - body identical to original English body (old pipeline bug)
            cur.execute("""
                SELECT a.id, a.title, a.excerpt, a.body, a.body::text as body_text
                FROM articles a
                WHERE a.is_published = true
                  AND EXISTS (
                    SELECT 1 FROM article_translations t
                    WHERE t.article_id = a.id
                      AND (
                           t.title = a.title
                        OR t.body IS NULL
                        OR t.body::text = '[]'
                        OR t.body::text = a.body::text
                      )
                  )
                ORDER BY a.created_at DESC
                LIMIT %s
            """, (args.limit,))
        rows = cur.fetchall()

    total = len(rows)
    print(f"Articles to process: {total}")
    print(f"Locales: {locales}")
    print(f"Mode: {'force' if args.force else 'body-only' if args.body_only else 'smart'}")
    avg_blocks = 15
    est_sec = total * len(locales) * avg_blocks * DELAY
    print(f"Estimated time: ~{int(est_sec // 60)} min\n")

    done = 0
    errors = 0

    for i, (article_id, title, excerpt, body, body_text) in enumerate(rows):
        print(f"[{i+1}/{total}] {title[:65]}")

        body_list = body if isinstance(body, list) else (json.loads(body) if body else [])

        # Fetch existing translations for this article
        with conn.cursor() as cur:
            cur.execute("""
                SELECT locale, title, body::text
                FROM article_translations
                WHERE article_id = %s
            """, (str(article_id),))
            existing = {r[0]: {"title": r[1], "body_text": r[2] or "[]"} for r in cur.fetchall()}

        for locale in locales:
            ex = existing.get(locale)

            # Determine what needs to be done
            title_translated = ex is not None and ex["title"] != title
            body_translated  = (
                ex is not None
                and ex["body_text"] not in ("[]", "null", "")
                and ex["body_text"] != body_text
            )

            if not args.force:
                if title_translated and body_translated:
                    continue  # Nothing to do

            print(f"  → {locale}", end=" ", flush=True)
            try:
                if not args.force and title_translated and not body_translated:
                    # Title/excerpt already translated — only fix the body
                    print("(body only)…", end=" ", flush=True)
                    tr_body = translate_body_only(body_list, locale)
                    update_body_only(conn, str(article_id), locale, tr_body)
                else:
                    # Translate everything (new or stale record)
                    tr = translate_article(title, excerpt, body_list, locale)
                    upsert_translation(conn, str(article_id), locale,
                                       tr["title"], tr["excerpt"], tr["body"])
                print("✓")
                done += 1
            except Exception as e:
                print(f"✗ {e}")
                conn.rollback()
                errors += 1

        if (i + 1) % 20 == 0:
            print(f"\n  Progress: {done} done, {errors} errors\n")

    conn.close()
    print(f"\n✅ Done. Translated: {done}, Errors: {errors}")


if __name__ == "__main__":
    main()
