#!/usr/bin/env python3
"""
Multi-provider article body translator.
Priority order:
  1. DeepL Free API       (500K chars/month — set DEEPL_API_KEY)
  2. Microsoft Translator (2M chars/month free — set MS_TRANSLATOR_KEY)
  3. Google Translate     (unofficial endpoint, no key, ~0.5s/request)
  4. MyMemory API         (free, 10K words/day without key; set MYMEMORY_EMAIL for 50K)
  5. Ollama               (local fallback, slowest)

Crash-safe: resumes from /opt/medmind/body_translation_progress.txt
Estimated time with Google Translate endpoint: ~8-12 hours for all 1130 pairs.

Usage:
  nohup python3 /opt/medmind/translate_api.py >> /opt/medmind/translate_api.log 2>&1 &
  tail -f /opt/medmind/translate_api.log
"""

import json, os, re, sys, time
import requests
import psycopg2, psycopg2.extras
from datetime import datetime

DB_DSN   = "host=localhost dbname=medmind user=medmind password=medmind_secret"
PROGRESS = "/opt/medmind/body_translation_progress.txt"
OLLAMA   = "http://localhost:11434"
MODEL    = "qwen3:8b"

DEEPL_KEY      = os.getenv("DEEPL_API_KEY", "")
MS_KEY         = os.getenv("MS_TRANSLATOR_KEY", "")
MYMEMORY_EMAIL = os.getenv("MYMEMORY_EMAIL", "")

LANG_NAMES = {"ru": "Russian", "de": "German", "fr": "French", "es": "Spanish", "tr": "Turkish"}

DEEPL_CODES = {"ru": "RU", "de": "DE", "fr": "FR", "es": "ES", "tr": "TR"}
MS_CODES    = {"ru": "ru", "de": "de", "fr": "fr", "es": "es", "tr": "tr"}
MM_CODES    = {"ru": "en|ru", "de": "en|de", "fr": "en|fr", "es": "en|es", "tr": "en|tr"}

def log(msg):
    print(f"[{datetime.utcnow():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)

def load_done():
    if not os.path.exists(PROGRESS):
        return set()
    with open(PROGRESS) as f:
        return {l.strip() for l in f if l.strip()}

def mark_done(aid, locale):
    with open(PROGRESS, "a") as f:
        f.write(f"{aid}:{locale}\n")


# ── Provider: Google Translate (unofficial, no key needed) ─────────────────────

_google_errors = 0

def translate_google_free(text: str, lang: str) -> str | None:
    global _google_errors
    if not text.strip() or _google_errors >= 5:
        return None
    # Split long texts (max ~4800 chars)
    if len(text) > 4800:
        parts = [text[i:i+4800] for i in range(0, len(text), 4800)]
        results = []
        for part in parts:
            r = translate_google_free(part, lang)
            if r is None:
                return None
            results.append(r)
        return " ".join(results)
    try:
        r = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={"client": "gtx", "sl": "en", "tl": lang, "dt": "t", "q": text},
            headers={"User-Agent": "Mozilla/5.0 (compatible; MedMind/1.0)"},
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            result = "".join(seg[0] for seg in data[0] if seg and seg[0])
            _google_errors = 0
            time.sleep(0.25)  # gentle rate limiting
            return result.strip() or None
        if r.status_code in (429, 503):
            log(f"Google free rate limit (HTTP {r.status_code}), sleeping 30s")
            time.sleep(30)
            _google_errors += 1
        else:
            _google_errors += 1
    except Exception as e:
        log(f"Google free error: {e}")
        _google_errors += 1
    return None


def translate_google_free_list(items: list, lang: str) -> list | None:
    """Translate a list joined as a numbered format for fewer API calls."""
    if not items:
        return items
    # Join with separators Google doesn't change
    joined = "\n||||\n".join(items)
    if len(joined) > 4800:
        # Too long — translate individually
        results = []
        for item in items:
            r = translate_google_free(item, lang)
            results.append(r if r else item)
        return results
    result = translate_google_free(joined, lang)
    if result is None:
        return None
    parts = result.split("\n||||\n")
    if len(parts) == len(items):
        return [p.strip() for p in parts]
    # Separator got mangled — fall back to individual
    return [translate_google_free(item, lang) or item for item in items]


# ── Provider: DeepL Free ───────────────────────────────────────────────────────

def translate_deepl(text: str, lang: str) -> str | None:
    if not DEEPL_KEY or not text.strip():
        return None
    try:
        r = requests.post(
            "https://api-free.deepl.com/v2/translate",
            data={"auth_key": DEEPL_KEY, "text": text,
                  "source_lang": "EN", "target_lang": DEEPL_CODES[lang]},
            timeout=15,
        )
        if r.status_code == 200:
            return r.json()["translations"][0]["text"]
        if r.status_code == 429:
            time.sleep(60)
    except Exception as e:
        log(f"DeepL error: {e}")
    return None


def translate_deepl_list(items: list, lang: str) -> list | None:
    if not DEEPL_KEY:
        return None
    try:
        r = requests.post(
            "https://api-free.deepl.com/v2/translate",
            data={"auth_key": DEEPL_KEY, "text": items,
                  "source_lang": "EN", "target_lang": DEEPL_CODES[lang]},
            timeout=20,
        )
        if r.status_code == 200:
            txs = r.json()["translations"]
            if len(txs) == len(items):
                return [t["text"] for t in txs]
    except Exception as e:
        log(f"DeepL batch error: {e}")
    return None


# ── Provider: Microsoft Translator ─────────────────────────────────────────────

def translate_ms_list(items: list, lang: str) -> list | None:
    if not MS_KEY:
        return None
    try:
        r = requests.post(
            "https://api.cognitive.microsofttranslator.com/translate",
            params={"api-version": "3.0", "from": "en", "to": MS_CODES[lang]},
            headers={"Ocp-Apim-Subscription-Key": MS_KEY,
                     "Content-Type": "application/json",
                     "Ocp-Apim-Subscription-Region": "global"},
            json=[{"text": t} for t in items],
            timeout=20,
        )
        if r.status_code == 200:
            results = [item["translations"][0]["text"] for item in r.json()]
            return results if len(results) == len(items) else None
    except Exception as e:
        log(f"MS error: {e}")
    return None

def translate_ms(text: str, lang: str) -> str | None:
    result = translate_ms_list([text], lang)
    return result[0] if result else None


# ── Provider: MyMemory ─────────────────────────────────────────────────────────

_mm_chars = 0
_mm_date  = None

def translate_mymemory(text: str, lang: str) -> str | None:
    global _mm_chars, _mm_date
    if not text.strip():
        return None
    today = datetime.utcnow().date()
    if _mm_date != today:
        _mm_date, _mm_chars = today, 0
    limit = 250_000 if MYMEMORY_EMAIL else 50_000
    if _mm_chars >= limit:
        return None
    if len(text) > 480:
        parts = [text[i:i+480] for i in range(0, len(text), 480)]
        results = [translate_mymemory(p, lang) for p in parts]
        return " ".join(r for r in results if r) or None
    try:
        params = {"q": text, "langpair": MM_CODES[lang]}
        if MYMEMORY_EMAIL:
            params["de"] = MYMEMORY_EMAIL
        r = requests.get("https://api.mymemory.translated.net/get",
                         params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data.get("responseStatus") == 200:
                _mm_chars += len(text)
                time.sleep(0.3)
                return data["responseData"]["translatedText"]
            if "LIMIT" in str(data.get("responseStatus", "")):
                _mm_chars = limit
    except Exception as e:
        log(f"MyMemory error: {e}")
    return None


# ── Provider: Ollama (local fallback) ─────────────────────────────────────────

def translate_ollama(text: str, lang: str) -> str | None:
    if not text.strip():
        return text
    try:
        r = requests.post(f"{OLLAMA}/api/chat", json={
            "model": MODEL,
            "messages": [
                {"role": "system",
                 "content": f"/no_think\nTranslate to {LANG_NAMES[lang]}. Output ONLY the translation."},
                {"role": "user", "content": text},
            ],
            "stream": False, "think": False,
            "options": {"temperature": 0.1, "num_predict": 400},
        }, timeout=120)
        raw = r.json()["message"]["content"]
        return re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip() or None
    except Exception:
        return None


# ── Unified translate ──────────────────────────────────────────────────────────

def translate(text: str, lang: str) -> str:
    if not text or not text.strip():
        return text
    for fn in [translate_deepl, translate_ms, translate_google_free,
               translate_mymemory, translate_ollama]:
        result = fn(text, lang)
        if result and result.strip():
            return result
    return text


def translate_list(items: list, lang: str) -> list:
    if not items:
        return items
    # Try batch providers first
    result = translate_deepl_list(items, lang)
    if result:
        return result
    result = translate_ms_list(items, lang)
    if result:
        return result
    result = translate_google_free_list(items, lang)
    if result:
        return result
    # Item by item
    return [translate(item, lang) for item in items]


# ── Block translation ──────────────────────────────────────────────────────────

def translate_body(body: list, lang: str) -> list:
    if not body:
        return body
    body = [dict(b) for b in body]  # shallow copy

    # Batch headings
    hidx = [i for i, b in enumerate(body) if b.get("type") in ("h2", "h3", "h4")]
    if hidx:
        texts = [body[i].get("content", "") for i in hidx]
        translated = translate_list(texts, lang)
        for k, i in enumerate(hidx):
            body[i]["content"] = translated[k]

    # Paragraphs and callouts
    for i, block in enumerate(body):
        if block.get("type") in ("p", "callout") and block.get("content"):
            body[i]["content"] = translate(block["content"], lang)

    # Lists
    for i, block in enumerate(body):
        if block.get("type") in ("ul", "ol") and block.get("items"):
            body[i]["items"] = translate_list(block["items"], lang)

    # Tables
    for i, block in enumerate(body):
        if block.get("type") == "table":
            if block.get("headers"):
                body[i]["headers"] = translate_list(block["headers"], lang)
            body[i]["rows"] = [
                translate_list(row, lang) if isinstance(row, list) else row
                for row in block.get("rows", [])
            ]

    return body


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    log("=== Multi-provider translator started ===")
    providers_active = []
    if DEEPL_KEY:   providers_active.append("DeepL")
    if MS_KEY:      providers_active.append("Microsoft")
    providers_active.append("GoogleTranslate(free)")
    providers_active.append(f"MyMemory({'50K/day' if MYMEMORY_EMAIL else '10K/day'})")
    providers_active.append("Ollama(fallback)")
    log(f"Providers: {' → '.join(providers_active)}")
    if MYMEMORY_EMAIL:
        log(f"MyMemory email: {MYMEMORY_EMAIL}")

    done = load_done()
    log(f"Already done: {len(done)} pairs")

    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT at.article_id::text, at.locale, at.body, a.title as eng_title
        FROM article_translations at
        JOIN articles a ON a.id = at.article_id
        WHERE at.locale IN ('ru','de','fr','es','tr')
          AND a.is_published = true
        ORDER BY at.locale, a.published_at DESC NULLS LAST
    """)
    rows = cur.fetchall()
    cur.close()

    todo = [r for r in rows if f"{r['article_id']}:{r['locale']}" not in done]
    log(f"Total pairs: {len(rows)} | Remaining: {len(todo)}")

    # Estimate: ~15s per article with Google Translate, vs ~20 min with Ollama
    est_h = len(todo) * 15 / 3600
    log(f"Estimated time: ~{est_h:.1f} hours ({est_h/24:.1f} days) using Google Translate")

    errors_in_row = 0
    for n, row in enumerate(todo, 1):
        aid    = row["article_id"]
        locale = row["locale"]
        body   = list(row["body"])
        title  = (row["eng_title"] or "")[:55]

        log(f"[{n}/{len(todo)}] {locale} | {title}")
        t0 = time.time()

        try:
            translated = translate_body(body, locale)
            upd = conn.cursor()
            upd.execute(
                "UPDATE article_translations SET body=%s, updated_at=NOW() "
                "WHERE article_id=%s AND locale=%s",
                (json.dumps(translated, ensure_ascii=False), aid, locale)
            )
            conn.commit()
            mark_done(aid, locale)
            elapsed = time.time() - t0
            log(f"  OK {len(body)} blocks in {elapsed:.0f}s")
            errors_in_row = 0
        except Exception as e:
            conn.rollback()
            log(f"  FAIL: {e}")
            errors_in_row += 1
            if errors_in_row >= 5:
                log("5 errors in a row — sleeping 60s before continuing")
                time.sleep(60)
                errors_in_row = 0

    conn.close()
    log("=== All done! ===")


if __name__ == "__main__":
    main()
