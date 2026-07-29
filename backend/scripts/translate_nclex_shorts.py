#!/usr/bin/env python3
"""
Translate EN NCLEX questions → ES / AR for YouTube Shorts.

Creates table nclex_shorts_translations on first run.
Provider chain: Groq → Cerebras → Gemini → SambaNova (key rotation within each).

Usage:
    python3 translate_nclex_shorts.py --lang es --max 20
    python3 translate_nclex_shorts.py --lang ar --max 20
    python3 translate_nclex_shorts.py --lang es --max 5 --dry-run
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import time
from pathlib import Path

import httpx
import psycopg2
import psycopg2.extras

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ENV_FILE = Path("/opt/medmind/backend/.env.prod")
DB_URL   = os.environ.get("DB_URL", "postgresql://medmind:medmind_secret@localhost:5432/medmind")

LANG_NAMES = {"es": "Spanish", "ar": "Arabic"}
DELAY = 0.3


# ── Env & key loading ─────────────────────────────────────────────────────────

def _load_env():
    if not ENV_FILE.exists():
        return
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def _g(name: str) -> str:
    return os.environ.get(name, "")


def _dedup(lst: list[str]) -> list[str]:
    seen: set = set()
    return [x for x in lst if x and x not in seen and not seen.add(x)]  # type: ignore


# Per-key cooldown for 429 handling
_rate_limited_until: dict[str, float] = {}


def _available(keys: list[str]) -> list[str]:
    now = time.time()
    return [k for k in keys if _rate_limited_until.get(k, 0) <= now]


def _mark_limited(key: str, secs: int = 60):
    _rate_limited_until[key] = time.time() + secs


def _build_providers() -> list[dict]:
    groq_keys      = _dedup([_g("GROQ_API_KEY_3"), _g("GROQ_API_KEY_4"), _g("GROQ_API_KEY_6"),
                              _g("GROQ_KEY_MODULE"), _g("GROQ_KEY_MODULE_2")])
    cerebras_keys  = _dedup([_g("CEREBRAS_API_KEY_2"), _g("CEREBRAS_API_KEY_3"),
                              _g("CEREBRAS_API_KEY_4"), _g("CEREBRAS_API_KEY_5")])
    gemini_keys    = _dedup([_g("GEMINI_API_KEY"), _g("GEMINI_API_KEY_2"),
                              _g("GEMINI_API_KEY_3"), _g("GEMINI_API_KEY_4")])
    sambanova_keys = _dedup([_g("SAMBANOVA_API_KEY_2"), _g("SAMBANOVA_API_KEY_3")])

    providers = []
    if groq_keys:
        providers.append({
            "name": "groq", "url": "https://api.groq.com/openai/v1/chat/completions",
            "model": "llama-3.3-70b-versatile", "keys": groq_keys,
        })
    if cerebras_keys:
        providers.append({
            "name": "cerebras", "url": "https://api.cerebras.ai/v1/chat/completions",
            "model": "gpt-oss-120b", "keys": cerebras_keys,
        })
    if sambanova_keys:
        providers.append({
            "name": "sambanova", "url": "https://fast-api.snova.ai/v1/chat/completions",
            "model": "Meta-Llama-3.3-70B-Instruct", "keys": sambanova_keys,
        })
    if gemini_keys:
        providers.append({
            "name": "gemini", "keys": gemini_keys,
        })
    return providers


# ── DB helpers ────────────────────────────────────────────────────────────────

def _conn():
    return psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)


CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS nclex_shorts_translations (
    id          SERIAL PRIMARY KEY,
    question_id VARCHAR(36) NOT NULL,
    lang        VARCHAR(5)  NOT NULL,
    question    TEXT        NOT NULL,
    options     JSONB       NOT NULL,
    key_takeaway TEXT       NOT NULL,
    status      VARCHAR(20) DEFAULT 'done',
    created_at  TIMESTAMP   DEFAULT NOW(),
    UNIQUE(question_id, lang)
);
"""


def ensure_table():
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(CREATE_TABLE)
        conn.commit()


def fetch_untranslated(lang: str, limit: int) -> list[dict]:
    sql = """
        SELECT q.id::text AS id, q.question, q.options, q.key_takeaway,
               q.difficulty, m.title AS module_title
        FROM mcq_questions q
        LEFT JOIN modules m ON m.id = q.module_id
        WHERE q.key_takeaway IS NOT NULL
          AND q.question_type = 'mcq'
          AND (q.exam_slugs IS NOT NULL OR m.code LIKE 'NURSE-%%')
          AND q.question ~ '^[A-Za-z]'
          AND q.question !~ '[А-яЁёА-ЯЙЮЭЫЪЬа-яёйюэыъь]'
          AND NOT EXISTS (
              SELECT 1 FROM nclex_shorts_translations t
              WHERE t.question_id = q.id::text AND t.lang = %s
          )
        ORDER BY q.created_at ASC
        LIMIT %s
    """
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (lang, limit))
        return [dict(r) for r in cur.fetchall()]


def save_translation(question_id: str, lang: str, translated: dict):
    sql = """
        INSERT INTO nclex_shorts_translations (question_id, lang, question, options, key_takeaway)
        VALUES (%s, %s, %s, %s::jsonb, %s)
        ON CONFLICT (question_id, lang) DO NOTHING
    """
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (
            question_id, lang,
            translated["question"],
            json.dumps(translated["options"]),
            translated["key_takeaway"],
        ))
        conn.commit()


# ── Translation API calls ─────────────────────────────────────────────────────

_PROMPT = """\
Translate the following NCLEX nursing exam question from English to {lang_name}.

Rules:
- Keep medical terminology accurate and professional
- Keep answer labels unchanged (A, B, C, D)
- Preserve numbers, dosages, units, and drug names exactly
- Return ONLY a valid JSON object, nothing else

Input JSON:
{json_input}

Return translated JSON with same keys: question, options (A/B/C/D), key_takeaway"""


def _parse_response(raw: str) -> dict | None:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"```[a-z]*\n?", "", raw).strip().rstrip("`").strip()
    try:
        data = json.loads(raw)
        if "question" in data and "options" in data and "key_takeaway" in data:
            return data
    except json.JSONDecodeError:
        pass
    return None


def _call_openai_compat(url: str, key: str, model: str, prompt: str) -> str | None:
    try:
        resp = httpx.post(
            url,
            headers={"Authorization": f"Bearer {key}"},
            json={"model": model, "messages": [{"role": "user", "content": prompt}],
                  "max_tokens": 600, "temperature": 0.1},
            timeout=45,
        )
        if resp.status_code == 429:
            _mark_limited(key, 65)
            return None
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        log.debug("openai-compat error [%s]: %s", url.split("/")[2], exc)
        return None


def _call_gemini(key: str, prompt: str) -> str | None:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={key}"
    try:
        resp = httpx.post(
            url,
            json={"contents": [{"parts": [{"text": prompt}]}],
                  "generationConfig": {"maxOutputTokens": 600, "temperature": 0.1}},
            timeout=45,
        )
        if resp.status_code == 429:
            _mark_limited(key, 65)
            return None
        resp.raise_for_status()
        candidates = resp.json().get("candidates", [])
        if candidates:
            return candidates[0]["content"]["parts"][0]["text"]
    except Exception as exc:
        log.debug("gemini error: %s", exc)
    return None


def _translate_one(q: dict, lang: str, providers: list[dict]) -> dict | None:
    lang_name = LANG_NAMES[lang]
    options   = q["options"] if isinstance(q["options"], dict) else json.loads(q["options"])
    payload   = {"question": q["question"], "options": options, "key_takeaway": q["key_takeaway"]}
    prompt    = _PROMPT.format(lang_name=lang_name, json_input=json.dumps(payload, ensure_ascii=False))

    for provider in providers:
        avail = _available(provider["keys"])
        if not avail:
            log.debug("provider %s: all keys rate-limited, skipping", provider["name"])
            continue

        for key in avail:
            if provider["name"] == "gemini":
                raw = _call_gemini(key, prompt)
            else:
                raw = _call_openai_compat(provider["url"], key, provider["model"], prompt)

            if raw is None:
                continue
            result = _parse_response(raw)
            if result:
                log.debug("  translated via %s", provider["name"])
                return result
            log.debug("  bad JSON from %s, trying next key", provider["name"])

    return None


# ── Main ──────────────────────────────────────────────────────────────────────

def run(lang: str, max_q: int, dry_run: bool) -> int:
    _load_env()
    providers = _build_providers()
    if not providers:
        log.error("No API keys found — check .env.prod")
        return 0

    log.info("Providers available: %s", [p["name"] for p in providers])
    ensure_table()
    questions = fetch_untranslated(lang, max_q)

    if not questions:
        log.info("Nothing to translate for lang=%s", lang)
        return 0

    log.info("Translating %d questions → %s", len(questions), LANG_NAMES[lang])
    done = 0

    for q in questions:
        log.info("  [%s] %s…", q["id"][:8], q["question"][:60])
        translated = _translate_one(q, lang, providers)
        if not translated:
            log.warning("  ✗ all providers failed, skipping")
            time.sleep(DELAY)
            continue

        if dry_run:
            log.info("  [DRY] → %s", translated["question"][:80])
        else:
            save_translation(q["id"], lang, translated)
            log.info("  ✓ saved")
        done += 1
        time.sleep(DELAY)

    log.info("Done: %d/%d translated for lang=%s", done, len(questions), lang)
    return done


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang",    required=True, choices=["es", "ar"])
    parser.add_argument("--max",     type=int, default=20)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    run(args.lang, args.max, args.dry_run)
