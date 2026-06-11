#!/usr/bin/env python3
"""
Background article body translator.
Translates body JSONB blocks (5 languages, skip ar) using Ollama qwen3:8b.
Crash-safe via progress file. Resumes where it left off.

Usage:
  nohup python3 /opt/medmind/translate_bodies.py >> /opt/medmind/translate_bodies.log 2>&1 &
Check:
  tail -f /opt/medmind/translate_bodies.log
"""

import json, os, sys, time, re, requests, psycopg2, psycopg2.extras
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────
DB_DSN    = "host=localhost dbname=medmind user=medmind password=medmind_secret"
OLLAMA    = "http://localhost:11434"
MODEL     = "qwen3:8b"
TIMEOUT   = 150          # seconds per Ollama call
DELAY     = 2            # seconds between articles
PROGRESS  = "/opt/medmind/body_translation_progress.txt"

LANG_NAMES = {"ru":"Russian","de":"German","fr":"French","es":"Spanish","tr":"Turkish"}

def log(msg):
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

# ── Progress ──────────────────────────────────────────────────────────────────
def load_done():
    if not os.path.exists(PROGRESS):
        return set()
    with open(PROGRESS) as f:
        return {l.strip() for l in f if l.strip()}

def mark_done(aid, locale):
    with open(PROGRESS, "a") as f:
        f.write(f"{aid}:{locale}\n")

# ── Ollama helpers ─────────────────────────────────────────────────────────────
def _call(system_prompt, user_text, num_predict=500):
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system",  "content": "/no_think\n" + system_prompt},
            {"role": "user",    "content": user_text},
        ],
        "stream": False, "think": False,
        "options": {"temperature": 0.1, "num_predict": num_predict},
    }
    r = requests.post(f"{OLLAMA}/api/chat", json=payload, timeout=TIMEOUT)
    raw = r.json()["message"]["content"]
    return re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

def _strip_fence(raw):
    if raw.startswith("```"):
        lines = raw.split("\n")
        end = -1 if lines[-1].strip() == "```" else len(lines)
        return "\n".join(lines[1:end]).strip()
    return raw

def tr_text(text, lang):
    """Translate a single string."""
    if not text or not text.strip():
        return text
    sys_p = (f"Translate the following medical text to {LANG_NAMES[lang]}. "
             f"Output ONLY the translation, no extra text.")
    try:
        return _call(sys_p, text, num_predict=400)
    except Exception as e:
        log(f"  tr_text error: {e}")
        return text

def tr_list(items, lang):
    """Translate a list of strings in one Ollama call."""
    if not items:
        return items
    sys_p = (f"Translate this JSON array to {LANG_NAMES[lang]}. "
             f"Output ONLY valid JSON array with the same number of elements.")
    try:
        raw = _call(sys_p, json.dumps(items, ensure_ascii=False), num_predict=700)
        raw = _strip_fence(raw)
        result = json.loads(raw)
        if isinstance(result, list) and len(result) == len(items):
            return result
    except Exception as e:
        log(f"  tr_list error: {e}")
    return items

# ── Block translation ──────────────────────────────────────────────────────────
def translate_body(body, lang):
    """Translate all blocks. Batches headings for speed."""
    if not body:
        return body

    HEADING_TYPES = {"h2", "h3", "h4"}

    # Pass 1: batch all headings in one call
    hidx = [i for i, b in enumerate(body) if b.get("type") in HEADING_TYPES]
    if hidx:
        htexts = [body[i].get("content", "") for i in hidx]
        translated = tr_list(htexts, lang)
        for k, i in enumerate(hidx):
            body[i] = dict(body[i])
            body[i]["content"] = translated[k]

    # Pass 2: paragraphs and callouts individually
    for i, block in enumerate(body):
        btype = block.get("type", "")
        if btype in ("p", "callout") and block.get("content"):
            body[i] = dict(block)
            body[i]["content"] = tr_text(block["content"], lang)

    # Pass 3: lists (each list in one batch call)
    for i, block in enumerate(body):
        if block.get("type") in ("ul", "ol") and block.get("items"):
            body[i] = dict(block)
            body[i]["items"] = tr_list(block["items"], lang)

    # Pass 4: tables
    for i, block in enumerate(body):
        if block.get("type") == "table":
            body[i] = dict(block)
            if block.get("headers"):
                body[i]["headers"] = tr_list(block["headers"], lang)
            rows_out = []
            for row in block.get("rows", []):
                rows_out.append(tr_list(row, lang) if isinstance(row, list) and row else row)
            body[i]["rows"] = rows_out

    return body

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    log("=== Body translator started. Model: " + MODEL + " ===")
    log("Progress file: " + PROGRESS)

    done = load_done()
    log(f"Already done: {len(done)} pairs")

    try:
        requests.get(f"{OLLAMA}/api/tags", timeout=5)
        log("Ollama: reachable")
    except Exception:
        log("ERROR: Ollama not reachable")
        sys.exit(1)

    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT at.article_id::text, at.locale, at.body,
               a.title as eng_title
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
    # Rough estimate: ~38 blocks/article, ~15s avg with batching, +DELAY
    est_h = len(todo) * 38 * 15 / 3600
    log(f"Estimated: ~{est_h:.0f} hours (~{est_h/24:.1f} days)")

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
            log(f"  OK {len(body)} blocks in {time.time()-t0:.0f}s")
        except Exception as e:
            conn.rollback()
            log(f"  FAIL: {e}")

        time.sleep(DELAY)

    conn.close()
    log("=== All done! ===")

if __name__ == "__main__":
    main()
