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


# ── Multi-key rotation manager ───────────────────────────────────────────────────

class KeyRotator:
    """Rotates through multiple Groq API keys when rate limits are hit.

    Strategy:
    - Tracks per-key exhaustion (daily limit hit = skip until tomorrow)
    - On 429: switch immediately to next key, no waiting
    - On token rate limit (tpm): brief pause then retry same key
    - When ALL keys exhausted: wait until next day reset (rare)
    """

    def __init__(self, keys: list[str]):
        self.keys = [k for k in keys if k]
        self.idx = 0
        self.exhausted: set[int] = set()   # indices of daily-limit-hit keys
        self.requests: dict[int, int] = {i: 0 for i in range(len(keys))}

    @property
    def current(self) -> str:
        return self.keys[self.idx]

    @property
    def active_count(self) -> int:
        return len(self.keys) - len(self.exhausted)

    def rotate(self, exhausted: bool = False) -> str | None:
        """Switch to next available key. Returns key or None if all exhausted."""
        if exhausted:
            self.exhausted.add(self.idx)
            log.warning("  Key %d/%d daily limit reached — marking exhausted",
                        self.idx + 1, len(self.keys))

        # Find next non-exhausted key
        for _ in range(len(self.keys)):
            self.idx = (self.idx + 1) % len(self.keys)
            if self.idx not in self.exhausted:
                log.info("  Switched to key %d/%d", self.idx + 1, len(self.keys))
                return self.current

        return None  # all keys exhausted

    def record(self):
        self.requests[self.idx] = self.requests.get(self.idx, 0) + 1

    def status(self) -> str:
        parts = []
        for i, k in enumerate(self.keys):
            tag = "✓" if i not in self.exhausted else "✗"
            parts.append(f"key{i+1}:{tag}({self.requests.get(i,0)}req)")
        return " | ".join(parts)

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


def generate_with_groq(topic: str, category: str, model: str, rotator: "KeyRotator") -> dict | None:
    """Call Groq API with automatic key rotation on rate limits."""
    prompt = ARTICLE_PROMPT.format(topic=topic, category=category)

    for attempt in range(len(rotator.keys) + 1):
        if rotator.active_count == 0:
            log.error("All Groq keys exhausted for today. Stopping.")
            return None

        api_key = rotator.current
        try:
            resp = httpx.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
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
                body = resp.json().get("error", {})
                err_msg = body.get("message", "")
                retry_after = int(resp.headers.get("retry-after", "0"))

                # Daily limit hit → rotate to next key permanently
                if "rate_limit_exceeded" in err_msg.lower() and retry_after > 3600:
                    next_key = rotator.rotate(exhausted=True)
                    if next_key is None:
                        log.error("All keys daily-limited. Stopping.")
                        return None
                    continue

                # Token-per-minute limit → brief pause, retry same key
                if retry_after and retry_after < 120:
                    log.warning("  TPM limit — waiting %ds (key %d/%d)",
                                retry_after, rotator.idx + 1, len(rotator.keys))
                    time.sleep(retry_after + 1)
                    continue

                # Generic 429 → try next key
                log.warning("  429 rate limit — switching key [%s]", err_msg[:60])
                next_key = rotator.rotate(exhausted=False)
                if next_key is None:
                    return None
                continue

            if resp.status_code == 401:
                log.error("  Key %d invalid — switching", rotator.idx + 1)
                rotator.rotate(exhausted=True)
                continue

            if resp.status_code != 200:
                log.error("Groq error %s: %s", resp.status_code, resp.text[:200])
                return None

            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            log.info("  Tokens: %d (completion: %d) [key %d/%d]",
                     usage.get("total_tokens", 0), usage.get("completion_tokens", 0),
                     rotator.idx + 1, len(rotator.keys))

            rotator.record()
            result = _parse_output(content)
            if not result:
                log.error("Parse failed for '%s' — preview: %s", topic, content[:300])
            return result

        except httpx.TimeoutException:
            log.error("Groq timeout for '%s' (key %d)", topic, rotator.idx + 1)
            return None
        except Exception as e:
            log.error("Groq call failed: %s", e)
            return None

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

    # ── Load all API keys (supports multi-key rotation) ────────────────────────
    keys: list[str] = []

    # 1. From --key argument
    if args.key:
        keys.extend([k.strip() for k in args.key.split(",") if k.strip()])

    # 2. From environment variables GROQ_API_KEY, GROQ_API_KEY_2, _3, _4 ...
    env_vars = ["GROQ_API_KEY"] + [f"GROQ_API_KEY_{i}" for i in range(2, 10)]
    for var in env_vars:
        val = os.environ.get(var, "")
        if val and val not in keys:
            keys.append(val)

    # 3. From backend/.env.prod
    env_file = os.path.join(os.path.dirname(__file__), "backend", ".env.prod")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                for var in env_vars:
                    if line.startswith(f"{var}="):
                        val = line.split("=", 1)[1].strip()
                        if val and val not in keys:
                            keys.append(val)

    if not keys:
        print("\n❌  No GROQ_API_KEY configured!")
        print("Add to /opt/medmind/backend/.env.prod: GROQ_API_KEY=gsk_xxx")
        print("Multiple keys: GROQ_API_KEY_2=gsk_yyy  GROQ_API_KEY_3=gsk_zzz\n")
        sys.exit(1)

    # ── Verify keys ────────────────────────────────────────────────────────────
    valid_keys = []
    for k in keys:
        try:
            test = httpx.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"},
                json={"model": args.model, "messages": [{"role": "user", "content": "OK"}], "max_tokens": 2},
                timeout=10,
            )
            if test.status_code == 200:
                valid_keys.append(k)
                log.info("  ✓ Key %d/%d valid: %s...", len(valid_keys), len(keys), k[:20])
            else:
                log.warning("  ✗ Key invalid: %s... (%s)", k[:20], test.status_code)
        except Exception as e:
            log.warning("  ✗ Key check failed: %s... (%s)", k[:20], e)

    if not valid_keys:
        print("\n❌  No valid Groq API keys found.\n")
        sys.exit(1)

    rotator = KeyRotator(valid_keys)
    log.info("Groq Article Generator | model=%s | limit=%d | keys=%d",
             args.model, args.limit, len(valid_keys))

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

            # Generate via Groq (with key rotation)
            t0 = time.time()
            data = generate_with_groq(topic, category, args.model, rotator)
            elapsed = time.time() - t0

            if rotator.active_count == 0:
                log.error("All Groq API keys exhausted. Stopping.")
                break

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
    log.info("Done. Generated: %d | Skipped: %d | Errors: %d", count, skipped, errors)
    log.info("Key usage: %s", rotator.status())


if __name__ == "__main__":
    main()
