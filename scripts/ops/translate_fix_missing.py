#!/usr/bin/env python3
"""
Targeted translation fixer:
  1. Finds articles with missing locales (no record or failed)
  2. Creates missing article_translations rows
  3. Translates and updates — retry with longer timeout + backoff

Locales: ru, de, ar, fr, es, tr (6 total)
Run inside backend container:
  docker cp translate_fix_missing.py medmind_backend:/tmp/
  docker exec -it medmind_backend python3 /tmp/translate_fix_missing.py
"""

import json, sys, time, requests, psycopg2, psycopg2.extras
from datetime import datetime

DB_DSN = "host=postgres dbname=medmind user=medmind password=medmind_secret"
LOCALES = ["ru", "de", "ar", "fr", "es", "tr"]
MYMEMORY_EMAIL = "33mikalai@gmail.com"

# Google Translate locale codes differ slightly
GOOGLE_LOCALE = {
    "ru": "ru", "de": "de", "ar": "ar",
    "fr": "fr", "es": "es", "tr": "tr",
}

def log(msg):
    print(f"[{datetime.utcnow():%H:%M:%S}] {msg}", flush=True)

# ── Translation functions ─────────────────────────────────────────────────────

def translate_google(text: str, target: str, retries=3) -> str | None:
    if not text or not text.strip():
        return None
    gl = GOOGLE_LOCALE.get(target, target)

    # Split long texts
    if len(text) > 4000:
        parts = [text[i:i+4000] for i in range(0, len(text), 4000)]
        results = []
        for part in parts:
            r = translate_google(part, target, retries)
            if r is None:
                return None
            results.append(r)
        return " ".join(results)

    for attempt in range(retries):
        try:
            r = requests.get(
                "https://translate.googleapis.com/translate_a/single",
                params={"client": "gtx", "sl": "en", "tl": gl, "dt": "t", "q": text},
                headers={"User-Agent": "Mozilla/5.0 (compatible; MedMindBot/1.0)"},
                timeout=30,
            )
            if r.status_code == 200:
                data = r.json()
                result = "".join(seg[0] for seg in data[0] if seg and seg[0])
                time.sleep(0.3)
                return result.strip() or None
            elif r.status_code in (429, 503):
                wait = 20 * (attempt + 1)
                log(f"  Rate limit {r.status_code} — sleeping {wait}s")
                time.sleep(wait)
            else:
                log(f"  Google HTTP {r.status_code}")
                time.sleep(5)
        except requests.exceptions.Timeout:
            log(f"  Timeout on attempt {attempt+1}/{retries}")
            time.sleep(10 * (attempt + 1))
        except Exception as e:
            log(f"  Google error: {e}")
            time.sleep(5)
    return None

def translate_mymemory(text: str, target: str) -> str | None:
    if not text or len(text) > 400:
        return None
    try:
        r = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": text[:400], "langpair": f"en|{target}", "de": MYMEMORY_EMAIL},
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            t = data.get("responseData", {}).get("translatedText", "")
            if t and t != text and data.get("responseStatus") == 200:
                time.sleep(0.3)
                return t.strip()
    except Exception:
        pass
    return None

def translate(text: str, target: str) -> str:
    if not text or not text.strip():
        return text
    r = translate_google(text, target)
    if r:
        return r
    r = translate_mymemory(text, target)
    if r:
        return r
    return text  # keep original as last resort

def translate_list(items: list, target: str) -> list:
    if not items:
        return items
    SEP = " |||SEP||| "
    joined = SEP.join(str(x) for x in items)
    if len(joined) > 4000:
        return [translate(str(x), target) for x in items]
    result = translate_google(joined, target)
    if result:
        parts = result.split("|||SEP|||")
        if len(parts) == len(items):
            return [p.strip() for p in parts]
    return [translate(str(x), target) for x in items]

def translate_body(body: list, target: str) -> list:
    if not body:
        return body
    body = [dict(b) for b in body]

    # Batch headings
    hidx = [i for i, b in enumerate(body) if b.get("type") in ("h2","h3","h4") and b.get("content")]
    if hidx:
        texts = [body[i].get("content","") for i in hidx]
        translated = translate_list(texts, target)
        for k, i in enumerate(hidx):
            body[i]["content"] = translated[k]

    # Paragraphs and callouts
    for i, block in enumerate(body):
        if block.get("type") in ("p","callout") and block.get("content"):
            body[i]["content"] = translate(block["content"], target)

    # Lists
    for i, block in enumerate(body):
        if block.get("type") in ("ul","ol") and block.get("items"):
            body[i]["items"] = translate_list(block["items"], target)

    # Tables
    for i, block in enumerate(body):
        if block.get("type") == "table":
            if block.get("headers"):
                body[i]["headers"] = translate_list(block["headers"], target)
            if block.get("rows"):
                body[i]["rows"] = [
                    translate_list(row, target) if isinstance(row, list) else row
                    for row in block["rows"]
                ]
    return body

def translate_faq(faq: list, target: str) -> list:
    if not faq:
        return faq
    return [{"question": translate(item.get("question",""), target),
             "answer": translate(item.get("answer",""), target)} for item in faq]

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # 1. Find all published articles
    cur.execute("""
        SELECT id, title, excerpt, body, faq
        FROM articles
        WHERE is_published = true
        ORDER BY created_at DESC
    """)
    articles = cur.fetchall()
    log(f"Total published articles: {len(articles)}")

    # 2. Find existing translations
    cur.execute("SELECT article_id, locale, status FROM article_translations")
    existing = {}
    for row in cur.fetchall():
        key = (str(row["article_id"]), row["locale"])
        existing[key] = row["status"]

    # 3. Determine what needs work
    todo = []  # (article, locale, action) where action = 'create' or 'retry'
    for art in articles:
        aid = str(art["id"])
        for locale in LOCALES:
            status = existing.get((aid, locale))
            if status is None:
                todo.append((art, locale, "create"))
            elif status == "failed":
                todo.append((art, locale, "retry"))
            # 'done' — skip

    log(f"Work to do: {len(todo)} translations ({sum(1 for _,_,a in todo if a=='create')} create, {sum(1 for _,_,a in todo if a=='retry')} retry)")

    if not todo:
        log("Nothing to do — all translations complete!")
        return

    # 4. Process each
    done_count = 0
    fail_count = 0

    for idx, (art, locale, action) in enumerate(todo, 1):
        aid = str(art["id"])
        title = art["title"]
        log(f"[{idx}/{len(todo)}] {action.upper()} {locale.upper()} — {title[:60]}")

        en_body = art.get("body") or []
        en_faq  = art.get("faq") or []
        en_title   = art.get("title", "")
        en_excerpt = art.get("excerpt", "")

        if not en_body:
            log(f"  No body — skipping")
            continue

        try:
            # Translate
            tr_title   = translate(en_title, locale)
            tr_excerpt = translate(en_excerpt, locale)
            tr_body    = translate_body(list(en_body), locale)
            tr_faq     = translate_faq(list(en_faq), locale) if en_faq else []

            now = datetime.utcnow()

            if action == "create":
                cur.execute("""
                    INSERT INTO article_translations
                        (article_id, locale, title, excerpt, body, faq,
                         status, translated_at, created_at, updated_at)
                    VALUES (%s,%s,%s,%s,%s::jsonb,%s::jsonb,
                            'done',%s,%s,%s)
                    ON CONFLICT (article_id, locale) DO UPDATE SET
                        title=EXCLUDED.title,
                        excerpt=EXCLUDED.excerpt,
                        body=EXCLUDED.body,
                        faq=EXCLUDED.faq,
                        status='done',
                        error_message=NULL,
                        translated_at=EXCLUDED.translated_at,
                        updated_at=EXCLUDED.updated_at
                """, (aid, locale, tr_title, tr_excerpt,
                      json.dumps(tr_body, ensure_ascii=False),
                      json.dumps(tr_faq, ensure_ascii=False),
                      now, now, now))
            else:  # retry
                cur.execute("""
                    UPDATE article_translations SET
                        title=%s, excerpt=%s, body=%s::jsonb, faq=%s::jsonb,
                        status='done', error_message=NULL,
                        translated_at=%s, updated_at=%s
                    WHERE article_id=%s AND locale=%s
                """, (tr_title, tr_excerpt,
                      json.dumps(tr_body, ensure_ascii=False),
                      json.dumps(tr_faq, ensure_ascii=False),
                      now, now, aid, locale))

            conn.commit()
            done_count += 1
            log(f"  ✓ OK ({locale})")

        except Exception as e:
            conn.rollback()
            fail_count += 1
            log(f"  ✗ ERROR: {e}")
            # Mark as failed in DB
            try:
                cur2 = conn.cursor()
                cur2.execute("""
                    INSERT INTO article_translations
                        (article_id, locale, title, excerpt, body, faq,
                         status, error_message, created_at, updated_at)
                    VALUES (%s,%s,%s,%s,'[]'::jsonb,'[]'::jsonb,
                            'failed',%s,NOW(),NOW())
                    ON CONFLICT (article_id, locale) DO UPDATE SET
                        status='failed', error_message=EXCLUDED.error_message,
                        updated_at=NOW()
                """, (aid, locale, en_title[:299], en_excerpt[:499] if en_excerpt else "", str(e)[:200]))
                conn.commit()
            except Exception:
                conn.rollback()

        # Polite delay between articles
        time.sleep(1)

    cur.close()
    conn.close()

    log(f"\n✅ Finished: {done_count} translated, {fail_count} failed")

    # Final stats
    conn2 = psycopg2.connect(DB_DSN)
    cur2 = conn2.cursor()
    cur2.execute("""
        SELECT locale, status, COUNT(*) cnt
        FROM article_translations
        GROUP BY locale, status ORDER BY locale, status
    """)
    log("\nFinal translation stats:")
    for row in cur2.fetchall():
        log(f"  {row[0]:4s} {row[1]:6s}: {row[2]}")
    conn2.close()

if __name__ == "__main__":
    main()
