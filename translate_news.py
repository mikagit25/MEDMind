"""
Перевод и пересаммаризация новостей.

Два режима:
  --translate   Перевести новости без переводов (63 статьи × 6 языков)
  --resummarise Пересаммаризовать 44 сырых абстракта через AI

Провайдеры (по приоритету): Cerebras → SambaNova → Groq
Cerebras самый быстрый (~900 tok/s), не тратит Groq-лимиты на AI-тьютор.
"""
import argparse
import json
import logging
import os
import re
import sys
import time

import httpx
import psycopg2
from psycopg2.extras import Json

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(message)s")
log = logging.getLogger(__name__)

DB_URL = "postgresql://medmind:medmind_secret@localhost:5432/medmind"
DB_KWARGS = dict(
    keepalives=1,
    keepalives_idle=60,
    keepalives_interval=10,
    keepalives_count=5,
    connect_timeout=30,
)


def _get_conn():
    return psycopg2.connect(DB_URL, **DB_KWARGS)

LOCALES = ["ru", "ar", "es", "de", "fr", "tr"]
LOCALE_NAMES = {
    "ru": "Russian", "ar": "Arabic", "es": "Spanish",
    "de": "German", "fr": "French", "tr": "Turkish",
}

# ── Provider configs ──────────────────────────────────────────────────────────
ENV_FILE = os.path.join(os.path.dirname(__file__), "backend", ".env.prod")

def _load_keys(prefix: str) -> list[str]:
    keys = []
    env_vars = [prefix] + [f"{prefix}_{i}" for i in range(2, 10)]
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE) as f:
            for line in f:
                line = line.strip()
                for var in env_vars:
                    if line.startswith(f"{var}="):
                        val = line.split("=", 1)[1].strip()
                        if val and val not in keys:
                            keys.append(val)
    for var in env_vars:
        val = os.environ.get(var, "")
        if val and val not in keys:
            keys.append(val)
    return keys

PROVIDERS = {
    "cerebras": {
        "url": "https://api.cerebras.ai/v1/chat/completions",
        "model": "gpt-oss-120b",
        "keys": _load_keys("CEREBRAS_API_KEY"),
    },
    "sambanova": {
        "url": "https://api.sambanova.ai/v1/chat/completions",
        "model": "Meta-Llama-3.3-70B-Instruct",
        "keys": _load_keys("SAMBANOVA_API_KEY"),
    },
    "groq": {
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "model": "llama-3.3-70b-versatile",
        # KEY_3 + KEY_4 only — KEY_1/KEY_2 reserved for user AI tutor
        "keys": [k for k in [_load_keys("GROQ_API_KEY_3"), _load_keys("GROQ_API_KEY_4")] if k for k in k],
    },
}

_key_idx: dict[str, int] = {p: 0 for p in PROVIDERS}


def _call(provider: str, system: str, user: str, max_tokens: int = 800) -> str:
    cfg = PROVIDERS[provider]
    keys = cfg["keys"]
    if not keys:
        raise ValueError(f"No keys for {provider}")
    tries = len(keys) * 2
    for attempt in range(tries):
        idx = _key_idx[provider] % len(keys)
        key = keys[idx]
        try:
            resp = httpx.post(
                cfg["url"],
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": cfg["model"],
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.2,
                },
                timeout=40,
            )
            if resp.status_code == 429:
                _key_idx[provider] = (idx + 1) % len(keys)
                time.sleep(2)
                continue
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            log.debug("%s key[%d] failed: %s", provider, idx, e)
            _key_idx[provider] = (idx + 1) % len(keys)
            time.sleep(1)
    raise RuntimeError(f"All {provider} keys exhausted")


def _ai(system: str, user: str, max_tokens: int = 800) -> str:
    """Try Cerebras → SambaNova → Groq."""
    for provider in ("cerebras", "sambanova", "groq"):
        if PROVIDERS[provider]["keys"]:
            try:
                return _call(provider, system, user, max_tokens)
            except Exception as e:
                log.warning("%s failed, trying next: %s", provider, e)
    raise RuntimeError("All providers exhausted")


# ── Translation ───────────────────────────────────────────────────────────────

TRANSLATE_TITLE_SYS = (
    "You are a professional medical translator. "
    "Translate the following medical article title from English to {lang_name}. "
    "Keep drug names, acronyms (PCR, COVID-19, RNA), and proper nouns unchanged. "
    "Return ONLY the translated title text. No quotes, no explanation."
)

TRANSLATE_SUMMARY_SYS = (
    "You are a professional medical translator. "
    "Translate the following medical summary from English to {lang_name}. "
    "Use standard medical terminology. "
    "Keep drug names, acronyms (PCR, COVID-19, RNA), and proper nouns unchanged. "
    "Return ONLY the translated summary text. No quotes, no explanation."
)

SUMMARISE_SYS = """\
You are a medical science journalist writing for healthcare professionals (doctors, residents, nurses).
Given a title and abstract, write a comprehensive summary (500-700 words) in clear, engaging English prose.
Structure (no headers, flowing paragraphs):
1. Lead paragraph: key finding in plain language, why it matters (2-3 sentences)
2. Background & context: disease burden, previous knowledge gap, why this study was needed (2-3 sentences)
3. Study design: type of study, population, setting, methodology in sufficient detail (3-4 sentences)
4. Key results: specific numbers, effect sizes, p-values, confidence intervals where available (3-4 sentences)
5. Secondary findings or subgroup analyses if mentioned (1-2 sentences)
6. Clinical significance: what this changes in practice, guideline implications (2-3 sentences)
7. Limitations and caveats (1-2 sentences)
DO NOT: copy-paste from the source, add disclaimers, mention "this article", use bullet points or headers.
Return ONLY the summary text — no title, no JSON, no markdown."""


def _translate(title: str, summary: str, locale: str) -> dict:
    lang_name = LOCALE_NAMES[locale]
    # Translate title and summary separately — avoids JSON truncation issues
    t_title = _ai(TRANSLATE_TITLE_SYS.format(lang_name=lang_name), title, max_tokens=120)
    t_summary = _ai(TRANSLATE_SUMMARY_SYS.format(lang_name=lang_name), summary, max_tokens=1000)
    return {"title": t_title.strip(), "summary": t_summary.strip()}


def _resummarise(title: str, abstract: str) -> str:
    user = f"Title: {title}\n\nAbstract:\n{abstract}"
    return _ai(SUMMARISE_SYS, user, max_tokens=1100)


# ── Main logic ────────────────────────────────────────────────────────────────

def run_translate(dry_run: bool = False):
    """Translate news articles that have no/partial translations."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, title, summary, translations
        FROM news_articles
        WHERE review_status = 'published'
        AND (translations = '{}' OR translations IS NULL)
        ORDER BY fetched_at DESC
    """)
    rows = cur.fetchall()
    conn.close()
    log.info("News articles without translations: %d", len(rows))

    ok = 0
    for i, (news_id, title, summary, existing_trans) in enumerate(rows, 1):
        if dry_run:
            log.info("[%d/%d] SKIP (dry-run): %s", i, len(rows), title[:60])
            continue
        translations = existing_trans or {}
        updated = False
        for locale in LOCALES:
            if locale in translations and translations[locale].get("title"):
                continue
            try:
                t = _translate(title, summary, locale)
                if t.get("title") and t.get("summary"):
                    translations[locale] = t
                    updated = True
                    log.info("  [%s] OK", locale)
                else:
                    log.warning("  [%s] empty result", locale)
            except Exception as e:
                log.warning("  [%s] FAILED: %s", locale, e)
            time.sleep(1.5)  # pace between locale calls
        if updated:
            conn2 = _get_conn()
            try:
                cur2 = conn2.cursor()
                cur2.execute(
                    "UPDATE news_articles SET translations = %s WHERE id = %s",
                    (Json(translations), news_id)
                )
                conn2.commit()
                ok += 1
            finally:
                conn2.close()
        log.info("[%d/%d] translated: %s", i, len(rows), title[:70])

    log.info("Done. Translated: %d / %d articles", ok, len(rows))


def run_resummarise(dry_run: bool = False):
    """Re-summarise articles where summary looks like a raw abstract or is too short."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, title, summary
        FROM news_articles
        WHERE review_status = 'published'
        AND (
            summary ILIKE 'Background%' OR
            summary ILIKE 'Purpose%' OR
            summary ILIKE 'Objective%' OR
            summary ILIKE 'Introduction%' OR
            summary ILIKE 'Methods%' OR
            length(summary) < 2000
        )
        ORDER BY fetched_at DESC
    """)
    rows = cur.fetchall()
    conn.close()
    log.info("Articles to re-summarise (raw abstract or < 2000 chars): %d", len(rows))

    ok = 0
    for i, (news_id, title, summary) in enumerate(rows, 1):
        if dry_run:
            log.info("[%d/%d] SKIP (dry-run): %s", i, len(rows), title[:60])
            continue
        try:
            new_summary = _resummarise(title, summary)
            if len(new_summary) > 500:
                conn2 = _get_conn()
                try:
                    cur2 = conn2.cursor()
                    cur2.execute(
                        "UPDATE news_articles SET summary = %s, translations = '{}' WHERE id = %s",
                        (new_summary, news_id)
                    )
                    conn2.commit()
                    ok += 1
                    log.info("[%d/%d] OK (%d chars): %s", i, len(rows), len(new_summary), title[:60])
                finally:
                    conn2.close()
            else:
                log.warning("[%d/%d] Too short, skipping: %s", i, len(rows), title[:60])
        except Exception as e:
            log.error("[%d/%d] FAILED: %s — %s", i, len(rows), title[:60], e)

    log.info("Done. Re-summarised: %d / %d articles", ok, len(rows))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--translate", action="store_true", help="Translate articles without translations")
    parser.add_argument("--resummarise", action="store_true", help="Re-summarise raw abstracts with AI")
    parser.add_argument("--all", action="store_true", help="Run both: resummarise then translate")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not any([args.translate, args.resummarise, args.all]):
        parser.print_help()
        sys.exit(1)

    providers_avail = {p: len(cfg["keys"]) for p, cfg in PROVIDERS.items() if cfg["keys"]}
    log.info("Providers: %s", providers_avail)

    if args.all or args.resummarise:
        log.info("=== PHASE 1: Re-summarise raw abstracts ===")
        run_resummarise(dry_run=args.dry_run)

    if args.all or args.translate:
        log.info("=== PHASE 2: Translate articles ===")
        run_translate(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
