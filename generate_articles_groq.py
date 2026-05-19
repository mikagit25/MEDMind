"""
MedMind AI — Fast Article Generator via Groq API (FREE)

Speed:  ~700 tok/s → ~7 sec/article → 1000+ articles/day on free tier
Model:  llama-3.3-70b-versatile (default) | llama-3.1-8b-instant (faster, weaker)
Limits: 14,400 req/day free | 6,000 tokens/min rate limit

Get your free key: https://console.groq.com (takes 1 minute)
Set key:  export GROQ_API_KEY=gsk_...
      OR add to /opt/medmind/backend/.env.prod: GROQ_API_KEY=gsk_...

Usage:
    python3 generate_articles_groq.py --limit 50
    python3 generate_articles_groq.py --category cardiology --limit 25
    python3 generate_articles_groq.py --dry-run          # preview topics only
    python3 generate_articles_groq.py --list-models       # show available models

Run in background:
    nohup python3 generate_articles_groq.py --limit 200 > /tmp/groq_gen.log 2>&1 &
"""
import argparse
import json
import logging
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime

import httpx
import psycopg2

# ── Import TOPICS from Ollama script (same topic list, no duplication) ─────────
sys.path.insert(0, os.path.dirname(__file__))
from generate_articles_ollama import (
    TOPICS, SCHEMA_MAP, INDEXNOW_KEY, DB_URL, LOCALES,
    slugify, text_to_blocks, calc_reading_time, save_article,
    save_translations, notify_indexnow, gtranslate, translate_blocks,
)

try:
    from fetch_article_image import fetch_cover_image as _fetch_cover_image
    _HAS_COVER = True
except ImportError:
    _HAS_COVER = False

try:
    from generate_og_image import generate_og_image as _gen_og_image
    _HAS_OG = True
except ImportError:
    _HAS_OG = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── Groq config ─────────────────────────────────────────────────────────────────
GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODELS = {
    "llama-3.3-70b-versatile": {"rpm": 30,  "tpm": 6_000,   "rpd": 14_400, "desc": "Best quality (default)"},
    "llama-3.1-8b-instant":    {"rpm": 30,  "tpm": 20_000,  "rpd": 14_400, "desc": "Fastest, good quality"},
    "gemma2-9b-it":            {"rpm": 30,  "tpm": 15_000,  "rpd": 14_400, "desc": "Google Gemma 2"},
    "mixtral-8x7b-32768":      {"rpm": 30,  "tpm": 5_000,   "rpd": 14_400, "desc": "Mixtral, large context"},
}
DEFAULT_MODEL = "llama-3.3-70b-versatile"

# ── Article prompt (same structured format — no JSON escaping issues) ───────────
ARTICLE_PROMPT = """\
You are a senior clinician writing an authoritative medical reference comparable to UpToDate or StatPearls.
Audience: medical students, residents, and practicing physicians.

Topic: {topic}
Category: {category}

Write a COMPREHENSIVE article of 2500-3000 words with SPECIFIC clinical details: exact drug doses, \
diagnostic criteria, lab thresholds, guideline recommendations (AHA/ACC/ESC/WHO/NICE).

Use EXACTLY this output format:

TITLE: [Clinical title, max 85 characters]
EXCERPT: [3 sentences: clinical significance, key mechanism, main management]
ARTICLE_START

## Key Points
List 7-9 critical clinical facts ("- " prefix). Each: one specific fact with numbers/doses/criteria.

## Overview and Epidemiology
Definition, incidence/prevalence, demographics, major risk factors. (250 words)

## Pathophysiology
Mechanisms, molecular basis, disease progression. (300 words)

## Clinical Presentation
Symptoms, physical signs, typical/atypical, red flags. (250 words)

## Diagnosis
Criteria with SPECIFIC values, lab workup, imaging, scoring systems (Wells, CURB-65, etc). (300 words)

## Management and Treatment
First-line therapy: SPECIFIC drug names, doses, duration, monitoring. Second-line options.
Special populations: pregnancy, CKD, elderly, hepatic impairment. Reference guidelines. (500 words)

## Complications and Prognosis
Complications with incidence rates, prognostic factors, referral criteria. (200 words)

## Special Populations and Considerations
Pediatric, geriatric, pregnancy, comorbidities, drug interactions. (200 words)

## Clinical Pearls
List 6-8 USMLE-style teaching points ("- " prefix). Classic associations, pitfalls.

ARTICLE_END

Rules: state facts DIRECTLY with numbers. No references section. Complete full-length sections."""


def _parse_output(content: str) -> dict | None:
    """Parse structured delimiter output — no JSON parsing issues."""
    title_m = re.search(r"^TITLE:\s*(.+)$", content, re.MULTILINE)
    if not title_m:
        return None
    title = title_m.group(1).strip().strip('"')

    excerpt_m = re.search(
        r"^EXCERPT:\s*(.+?)(?=\nARTICLE_START|\n\n## |\nARTICLE_END)",
        content, re.MULTILINE | re.DOTALL
    )
    excerpt = excerpt_m.group(1).strip() if excerpt_m else ""

    body_m = re.search(r"ARTICLE_START\s*\n(.*?)(?:ARTICLE_END|$)", content, re.DOTALL)
    if not body_m:
        body_m2 = re.search(r"(## Key Points.*)", content, re.DOTALL)
        body_text = body_m2.group(1).strip() if body_m2 else ""
    else:
        body_text = body_m.group(1).strip()

    if not body_text or len(body_text) < 400:
        return None

    return {"title": title, "excerpt": excerpt, "body_text": body_text}


def generate_with_groq(topic: str, category: str, model: str, api_key: str) -> dict | None:
    """Call Groq API to generate article. Returns dict with title/excerpt/body_text."""
    prompt = ARTICLE_PROMPT.format(topic=topic, category=category)
    try:
        resp = httpx.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 4096,
                "temperature": 0.3,
                "top_p": 0.9,
            },
            timeout=120,
        )

        if resp.status_code == 429:
            # Rate limit — extract retry-after
            retry = int(resp.headers.get("retry-after", "60"))
            log.warning("  Rate limited — waiting %ds", retry)
            time.sleep(retry + 2)
            return generate_with_groq(topic, category, model, api_key)  # retry once

        if resp.status_code != 200:
            log.error("Groq error %s: %s", resp.status_code, resp.text[:200])
            return None

        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        tokens_used = data.get("usage", {}).get("total_tokens", 0)
        log.info("  Tokens: %d (completion: %d)",
                 tokens_used, data.get("usage", {}).get("completion_tokens", 0))

        result = _parse_output(content)
        if not result:
            log.error("Parse failed for '%s' — preview: %s", topic, content[:300])
        return result

    except httpx.TimeoutException:
        log.error("Groq timeout for '%s'", topic)
        return None
    except Exception as e:
        log.error("Groq call failed for '%s': %s", topic, e)
        return None


def main():
    parser = argparse.ArgumentParser(description="MedMind Groq Article Generator (FREE, fast)")
    parser.add_argument("--limit",      type=int, default=20, help="Max articles to generate")
    parser.add_argument("--model",      type=str, default=DEFAULT_MODEL, help="Groq model name")
    parser.add_argument("--category",   type=str, default=None, help="Only this category")
    parser.add_argument("--dry-run",    action="store_true", help="Show topics without generating")
    parser.add_argument("--list-models",action="store_true", help="Show available Groq models")
    parser.add_argument("--delay",      type=float, default=2.0, help="Seconds between articles")
    parser.add_argument("--key",        type=str, default=None, help="Groq API key (or set GROQ_API_KEY env)")
    args = parser.parse_args()

    if args.list_models:
        print("\nAvailable Groq models (free tier):\n")
        for name, info in GROQ_MODELS.items():
            print(f"  {name}")
            print(f"    {info['desc']}")
            print(f"    {info['rpd']} req/day · {info['tpm']} tok/min · {info['rpm']} rpm\n")
        return

    if args.dry_run:
        total = 0
        for cat, topics in TOPICS.items():
            if args.category and cat != args.category:
                continue
            print(f"\n{cat.upper()} ({len(topics)})")
            for t in topics:
                print(f"  - {t}")
            total += len(topics)
        print(f"\nTotal: {total} topics")
        return

    # Get API key
    api_key = args.key or os.environ.get("GROQ_API_KEY") or ""
    if not api_key:
        # Try to load from backend .env.prod
        env_file = os.path.join(os.path.dirname(__file__), "backend", ".env.prod")
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    if line.startswith("GROQ_API_KEY="):
                        api_key = line.split("=", 1)[1].strip()
                        break

    if not api_key or api_key == "":
        print("\n❌  GROQ_API_KEY not set!")
        print("\n1. Go to https://console.groq.com → API Keys → Create key")
        print("2. Add to /opt/medmind/backend/.env.prod:")
        print("   GROQ_API_KEY=gsk_xxxxxxxxxxxx")
        print("\nOr pass directly:")
        print("   python3 generate_articles_groq.py --key gsk_xxxxxxxxxxxx --limit 50\n")
        sys.exit(1)

    log.info("Groq Article Generator | model=%s | limit=%d", args.model, args.limit)

    # Test API key
    test = httpx.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": args.model, "messages": [{"role": "user", "content": "Say OK"}], "max_tokens": 5},
        timeout=15,
    )
    if test.status_code == 401:
        print("\n❌  Invalid API key. Check your GROQ_API_KEY.\n")
        sys.exit(1)
    elif test.status_code == 200:
        log.info("API key verified ✓")
    else:
        log.warning("API test returned %s — continuing anyway", test.status_code)

    conn = psycopg2.connect(DB_URL)
    count = errors = skipped = 0

    STOP = {"and", "the", "of", "in", "with", "vs", "versus", "its", "for",
            "or", "a", "an", "to", "from", "on", "at", "by", "as"}

    for category, topics in TOPICS.items():
        if args.category and category != args.category:
            continue
        if count >= args.limit:
            break

        for topic in topics:
            if count >= args.limit:
                break

            log.info("[%d/%d] %s / %s", count + 1, args.limit, category, topic)

            # Smart pre-check: skip if similar article exists
            words = [w for w in re.split(r"[\s\-]+", topic.lower()) if w not in STOP]
            key2 = slugify(" ".join(words[:2]))

            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM articles WHERE slug LIKE %s LIMIT 1", (key2 + "%",))
                if cur.fetchone():
                    log.info("  -- Skipped (keyword '%s' exists)", key2)
                    skipped += 1
                    continue
                slug_pre = slugify(topic)[:50]
                cur.execute("SELECT 1 FROM articles WHERE slug LIKE %s LIMIT 1", (slug_pre + "%",))
                if cur.fetchone():
                    log.info("  -- Skipped (topic slug exists)")
                    skipped += 1
                    continue

            # Generate via Groq
            t0 = time.time()
            data = generate_with_groq(topic, category, args.model, api_key)
            elapsed = time.time() - t0

            if not data or not data.get("title") or not data.get("body_text"):
                log.warning("  ✗ Generation failed (%.1fs)", elapsed)
                errors += 1
                continue

            title   = data["title"]
            excerpt = data.get("excerpt", "")
            body    = text_to_blocks(data["body_text"])
            slug    = slugify(title)

            log.info("  Generated: '%s' (%.1fs, %d blocks)", title[:60], elapsed, len(body))

            article_id = str(uuid.uuid4())
            saved = save_article(conn, article_id, slug, title, excerpt, body, category)
            if not saved:
                alt_slug = slugify(f"{title} {category}")[:90]
                saved = save_article(conn, article_id, alt_slug, title, excerpt, body, category)
            if not saved:
                log.info("  -- Slug conflict, skipping")
                skipped += 1
                continue

            # Translate to 6 locales
            n_tr = save_translations(conn, article_id, title, excerpt, body)
            log.info("  ✓ Published + %d translations | %s", n_tr, slug)

            # Cover image from Wikipedia
            if _HAS_COVER:
                try:
                    cover_url = _fetch_cover_image(title, category)
                    if cover_url:
                        with conn.cursor() as cur:
                            cur.execute("UPDATE articles SET cover_image=%s WHERE id=%s",
                                        (cover_url, article_id))
                        conn.commit()
                        log.info("  🖼  Cover: %s", cover_url[:60])
                except Exception as e:
                    log.warning("  Cover failed: %s", e)

            # OG image
            if _HAS_OG:
                try:
                    _gen_og_image(slug, title, category, calc_reading_time(body))
                except Exception:
                    pass

            notify_indexnow(slug)
            count += 1
            time.sleep(args.delay)

    conn.close()
    model_info = GROQ_MODELS.get(args.model, {})
    log.info("Done. Generated: %d | Skipped: %d | Errors: %d", count, skipped, errors)
    log.info("Used ~%d tokens (~%d requests) of %d daily free requests",
             count * 3000, count, model_info.get("rpd", 14400))


if __name__ == "__main__":
    main()
