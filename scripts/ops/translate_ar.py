#!/usr/bin/env python3
"""
Arabic article translator — finishes pending AR translations.
Translates title, excerpt, and body blocks.

Usage (inside backend container):
  docker cp translate_ar.py medmind_backend:/tmp/
  docker exec -d medmind_backend python3 /tmp/translate_ar.py
  docker exec medmind_backend tail -f /tmp/translate_ar.log
"""

import json, sys, time, signal
import requests
import psycopg2, psycopg2.extras
from datetime import datetime

DB_DSN   = "host=postgres dbname=medmind user=medmind password=medmind_secret"
PROGRESS = "/tmp/progress_ar.txt"
LOG_FILE = "/tmp/translate_ar.log"

MYMEMORY_EMAIL = "33mikalai@gmail.com"

_log_fh = open(LOG_FILE, "a", buffering=1)

def log(msg):
    line = f"[{datetime.utcnow():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    _log_fh.write(line + "\n")

def load_done():
    try:
        with open(PROGRESS) as f:
            return {l.strip() for l in f if l.strip()}
    except FileNotFoundError:
        return set()

def mark_done(aid):
    with open(PROGRESS, "a") as f:
        f.write(f"{aid}\n")
        f.flush()


# ── Google Translate (unofficial, no key needed) ──────────────────────────────

_google_errors = 0

def translate_google(text: str) -> str | None:
    global _google_errors
    if not text or not text.strip() or _google_errors >= 5:
        return None
    if len(text) > 4800:
        parts = [text[i:i+4800] for i in range(0, len(text), 4800)]
        results = []
        for part in parts:
            r = translate_google(part)
            if r is None:
                return None
            results.append(r)
        return " ".join(results)
    try:
        r = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "en", "tl": "ar", "dt": "t", "q": text},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=20,
        )
        if r.status_code == 200:
            data = r.json()
            result = "".join(seg[0] for seg in data[0] if seg and seg[0])
            _google_errors = 0
            time.sleep(0.3)
            return result.strip() or None
        if r.status_code in (429, 503):
            log(f"Google rate-limit HTTP {r.status_code}, sleeping 30s")
            time.sleep(30)
            _google_errors += 1
        else:
            _google_errors += 1
            log(f"Google HTTP {r.status_code}")
    except Exception as e:
        log(f"Google error: {e}")
        _google_errors += 1
    return None


def translate_mymemory(text: str) -> str | None:
    if not text or not text.strip():
        return None
    try:
        params = {"q": text[:500], "langpair": "en|ar"}
        if MYMEMORY_EMAIL:
            params["de"] = MYMEMORY_EMAIL
        r = requests.get(
            "https://api.mymemory.translated.net/get",
            params=params,
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            translated = data.get("responseData", {}).get("translatedText", "")
            if translated and translated != text and data.get("responseStatus") == 200:
                time.sleep(0.2)
                return translated.strip()
    except Exception as e:
        log(f"MyMemory error: {e}")
    return None


def translate(text: str) -> str:
    if not text or not text.strip():
        return text
    result = translate_google(text)
    if result:
        return result
    result = translate_mymemory(text)
    if result:
        return result
    return text  # fallback: keep original


def translate_list(items: list) -> list:
    """Translate list items using batch separator trick."""
    if not items:
        return items
    SEP = " |||SEP||| "
    joined = SEP.join(str(x) for x in items)
    if len(joined) > 4500:
        return [translate(str(x)) for x in items]
    result = translate_google(joined)
    if result:
        parts = result.split("|||SEP|||")
        if len(parts) == len(items):
            return [p.strip() for p in parts]
    return [translate(str(x)) for x in items]


def translate_body(body: list) -> list:
    if not body:
        return body
    body = [dict(b) for b in body]

    # Batch headings
    hidx = [i for i, b in enumerate(body) if b.get("type") in ("h2", "h3", "h4")]
    if hidx:
        texts = [body[i].get("content", "") for i in hidx]
        translated = translate_list(texts)
        for k, i in enumerate(hidx):
            body[i]["content"] = translated[k]

    # Paragraphs and callouts
    for i, block in enumerate(body):
        if block.get("type") in ("p", "callout") and block.get("content"):
            body[i]["content"] = translate(block["content"])

    # Lists
    for i, block in enumerate(body):
        if block.get("type") in ("ul", "ol") and block.get("items"):
            body[i]["items"] = translate_list(block["items"])

    # Tables
    for i, block in enumerate(body):
        if block.get("type") == "table":
            if block.get("headers"):
                body[i]["headers"] = translate_list(block["headers"])
            body[i]["rows"] = [
                translate_list(row) if isinstance(row, list) else row
                for row in block.get("rows", [])
            ]

    return body


def main():
    log("=== Arabic translator started ===")
    log(f"MyMemory email: {MYMEMORY_EMAIL}")

    done = load_done()
    log(f"Already done: {len(done)} articles")

    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT at.article_id::text, at.body,
               a.title as eng_title,
               a.excerpt as eng_excerpt
        FROM article_translations at
        JOIN articles a ON a.id = at.article_id
        WHERE at.locale = 'ar'
          AND at.status = 'pending'
          AND a.is_published = true
        ORDER BY a.published_at DESC NULLS LAST
    """)
    rows = cur.fetchall()
    cur.close()

    todo = rows  # status='pending' already filters done ones
    log(f"Pending AR articles: {len(rows)} | Remaining: {len(todo)}")
    est_m = len(todo) * 20 / 60
    log(f"Estimated: ~{est_m:.0f} minutes")

    errors_in_row = 0
    for n, row in enumerate(todo, 1):
        aid  = row["article_id"]
        body = list(row["body"] or [])
        eng_title   = (row["eng_title"] or "")
        eng_excerpt = (row["eng_excerpt"] or "")
        preview     = eng_title[:50]

        log(f"[{n}/{len(todo)}] {preview}")
        t0 = time.time()

        try:
            # Translate title and excerpt
            ar_title   = translate(eng_title)
            ar_excerpt = translate(eng_excerpt)

            # Translate body
            ar_body = translate_body(body)

            upd = conn.cursor()
            upd.execute(
                """UPDATE article_translations
                   SET title=%s, excerpt=%s, body=%s,
                       status='done', translated_at=NOW(), updated_at=NOW()
                   WHERE article_id=%s AND locale='ar'""",
                (ar_title, ar_excerpt,
                 json.dumps(ar_body, ensure_ascii=False), aid)
            )
            conn.commit()
            mark_done(aid)
            elapsed = time.time() - t0
            log(f"  OK: title={ar_title[:40]}… ({len(body)} blocks, {elapsed:.0f}s)")
            errors_in_row = 0
        except Exception as e:
            conn.rollback()
            log(f"  FAIL: {e}")
            errors_in_row += 1
            if errors_in_row >= 5:
                log("5 errors in a row — sleeping 60s")
                time.sleep(60)
                errors_in_row = 0

    conn.close()
    log("=== Arabic translation complete! ===")


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    main()
