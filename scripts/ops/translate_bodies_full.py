#!/usr/bin/env python3
"""
Full article body translator — ru, de, fr, es, tr.
Translates ALL body blocks (headings, paragraphs, lists, tables, callouts)
using Google Translate, with MyMemory fallback.

Runs INSIDE backend container (host=postgres):
  docker cp translate_bodies_full.py medmind_backend:/tmp/
  docker exec -d medmind_backend python3 /tmp/translate_bodies_full.py
  docker exec medmind_backend tail -f /tmp/translate_full.log

Progress is saved to /tmp/progress_<locale>.txt — safe to restart.
"""

import json
import sys
import time
import signal
import requests
import psycopg2
import psycopg2.extras
from datetime import datetime

DB_DSN   = "host=postgres dbname=medmind user=medmind password=medmind_secret"
LOG_FILE = "/tmp/translate_full.log"
MYMEMORY_EMAIL = "33mikalai@gmail.com"

# Languages to process (Arabic already done)
LOCALES = ["ru", "de", "fr", "es", "tr"]

_log_fh = open(LOG_FILE, "a", buffering=1)
_running = True


def _sig(sig, frame):
    global _running
    _running = False
    log("Signal received — stopping after current article")

signal.signal(signal.SIGTERM, _sig)
signal.signal(signal.SIGINT, _sig)


def log(msg: str):
    line = f"[{datetime.utcnow():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    _log_fh.write(line + "\n")


def progress_file(locale: str) -> str:
    return f"/tmp/progress_full_{locale}.txt"


def load_done(locale: str) -> set:
    try:
        with open(progress_file(locale)) as f:
            return {l.strip() for l in f if l.strip()}
    except FileNotFoundError:
        return set()


def mark_done(locale: str, article_id: str):
    with open(progress_file(locale), "a") as f:
        f.write(f"{article_id}\n")
        f.flush()


# ── Google Translate ───────────────────────────────────────────────────────────

_google_errors = 0
_rate_limit_backoff = 0


def translate_google(text: str, target: str) -> str | None:
    global _google_errors, _rate_limit_backoff
    if not text or not text.strip():
        return None
    if _google_errors >= 8:
        return None

    # Split long texts
    if len(text) > 4500:
        parts = [text[i:i+4500] for i in range(0, len(text), 4500)]
        results = []
        for part in parts:
            r = translate_google(part, target)
            if r is None:
                return None
            results.append(r)
        return " ".join(results)

    if _rate_limit_backoff > 0:
        time.sleep(_rate_limit_backoff)
        _rate_limit_backoff = 0

    try:
        r = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "en", "tl": target, "dt": "t", "q": text},
            headers={"User-Agent": "Mozilla/5.0 (compatible; MedMindBot/1.0)"},
            timeout=20,
        )
        if r.status_code == 200:
            data = r.json()
            result = "".join(seg[0] for seg in data[0] if seg and seg[0])
            _google_errors = 0
            time.sleep(0.25)  # polite delay — ~4 req/sec
            return result.strip() or None
        elif r.status_code in (429, 503):
            wait = min(60, 15 * (1 + _google_errors))
            log(f"Google rate-limit ({r.status_code}) — sleeping {wait}s")
            time.sleep(wait)
            _google_errors += 1
        else:
            log(f"Google HTTP {r.status_code} for target={target}")
            _google_errors += 1
    except Exception as e:
        log(f"Google error: {e}")
        _google_errors += 1
    return None


def translate_mymemory(text: str, target: str) -> str | None:
    if not text or not text.strip() or len(text) > 500:
        return None
    try:
        r = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": text[:500], "langpair": f"en|{target}", "de": MYMEMORY_EMAIL},
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            translated = data.get("responseData", {}).get("translatedText", "")
            if translated and translated != text and data.get("responseStatus") == 200:
                time.sleep(0.2)
                return translated.strip()
    except Exception as e:
        pass
    return None


def translate(text: str, target: str) -> str:
    if not text or not text.strip():
        return text
    result = translate_google(text, target)
    if result:
        return result
    # Fallback: MyMemory (short texts only)
    result = translate_mymemory(text, target)
    if result:
        return result
    return text  # keep original as last resort


def translate_list(items: list, target: str) -> list:
    """Batch translate list items using separator trick."""
    if not items:
        return items
    SEP = " |||SEP||| "
    joined = SEP.join(str(x) for x in items)
    if len(joined) > 4500:
        return [translate(str(x), target) for x in items]
    result = translate_google(joined, target)
    if result:
        parts = result.split("|||SEP|||")
        if len(parts) == len(items):
            return [p.strip() for p in parts]
    # Fallback: translate individually
    return [translate(str(x), target) for x in items]


def translate_body(body: list, target: str) -> list:
    """Translate all blocks in an article body."""
    if not body:
        return body
    body = [dict(b) for b in body]

    # Batch headings (h2, h3, h4) for efficiency
    hidx = [i for i, b in enumerate(body) if b.get("type") in ("h2", "h3", "h4") and b.get("content")]
    if hidx:
        texts = [body[i].get("content", "") for i in hidx]
        translated = translate_list(texts, target)
        for k, i in enumerate(hidx):
            body[i]["content"] = translated[k]

    # Paragraphs and callouts (individually — usually long)
    for i, block in enumerate(body):
        if block.get("type") in ("p", "callout") and block.get("content"):
            body[i]["content"] = translate(block["content"], target)

    # Unordered / ordered lists
    for i, block in enumerate(body):
        if block.get("type") in ("ul", "ol") and block.get("items"):
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


# ── FAQ translation ────────────────────────────────────────────────────────────

def translate_faq(faq: list, target: str) -> list:
    if not faq:
        return faq
    result = []
    for item in faq:
        q = translate(item.get("question", ""), target)
        a = translate(item.get("answer", ""), target)
        result.append({"question": q, "answer": a})
    return result


# ── Main processing ────────────────────────────────────────────────────────────

def process_locale(conn, locale: str):
    global _google_errors
    done_ids = load_done(locale)
    _google_errors = 0

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Get all published articles with their English body
    cur.execute("""
        SELECT a.id, a.title, a.excerpt, a.body, a.faq,
               at.title as tr_title, at.excerpt as tr_excerpt,
               at.body as tr_body
        FROM articles a
        JOIN article_translations at ON at.article_id = a.id AND at.locale = %s
        WHERE a.is_published = true AND a.review_status = 'published'
        ORDER BY a.published_at DESC
    """, (locale,))
    articles = cur.fetchall()

    total = len(articles)
    translated = 0
    skipped = 0
    failed = 0

    log(f"[{locale.upper()}] Starting — {total} articles, {len(done_ids)} already done")

    for idx, art in enumerate(articles, 1):
        if not _running:
            log(f"[{locale.upper()}] Stopped by signal after {translated} articles")
            break

        aid = str(art["id"])

        if aid in done_ids:
            skipped += 1
            continue

        en_body = art.get("body") or []
        en_faq  = art.get("faq") or []
        if not en_body:
            mark_done(locale, aid)
            skipped += 1
            continue

        # Check if body is ALREADY translated (first block differs from English)
        tr_body = art.get("tr_body") or []
        if tr_body and len(tr_body) > 0:
            first_en  = (en_body[0].get("content") or "") if en_body else ""
            first_tr  = (tr_body[0].get("content") or "") if tr_body else ""
            # If first block content differs — body was already translated
            if first_tr and first_tr != first_en and len(first_tr) > 20:
                mark_done(locale, aid)
                skipped += 1
                continue

        t0 = time.time()
        try:
            new_body = translate_body(en_body, locale)
            new_faq  = translate_faq(en_faq, locale)
            elapsed  = time.time() - t0

            # Update translation record
            cur2 = conn.cursor()
            cur2.execute("""
                UPDATE article_translations
                SET body = %s::jsonb,
                    faq  = %s::jsonb,
                    status = 'done',
                    updated_at = NOW()
                WHERE article_id = %s AND locale = %s
            """, (
                json.dumps(new_body, ensure_ascii=False),
                json.dumps(new_faq,  ensure_ascii=False),
                art["id"],
                locale,
            ))
            conn.commit()
            mark_done(locale, aid)
            translated += 1

            blocks_count = len(new_body)
            log(f"[{locale.upper()}] [{idx}/{total}] {art['title'][:55]} — {blocks_count} blocks, {elapsed:.1f}s")

            # Reset google errors on success streak
            if translated % 10 == 0:
                _google_errors = max(0, _google_errors - 1)

        except Exception as e:
            conn.rollback()
            failed += 1
            log(f"[{locale.upper()}] FAILED [{idx}/{total}] {art['title'][:40]}: {e}")

    log(f"[{locale.upper()}] DONE — translated={translated}, skipped={skipped}, failed={failed}")


def main():
    log("=" * 60)
    log(f"Article Body Translator — locales: {', '.join(LOCALES)}")
    log("=" * 60)

    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = False

    # Count total work
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM articles WHERE is_published=true AND review_status='published'")
    total_articles = cur.fetchone()[0]
    log(f"Total published articles: {total_articles}")
    log(f"Total translation jobs: {total_articles * len(LOCALES)}")
    log(f"Estimated time: {total_articles * len(LOCALES) * 15 / 60:.0f} min (at 15s/article/locale)")
    log("")

    for locale in LOCALES:
        if not _running:
            break
        log(f"{'='*20} Starting locale: {locale.upper()} {'='*20}")
        try:
            process_locale(conn, locale)
        except Exception as e:
            log(f"[{locale.upper()}] FATAL: {e}")

    conn.close()
    log("All locales completed.")
    _log_fh.close()


if __name__ == "__main__":
    main()
