"""
MedMind Universal Article Generator — поддерживает любой OpenAI-совместимый API.

Поддерживаемые провайдеры (все бесплатные):
  groq        — api.groq.com            14400 req/day, 700 tok/s
  cerebras    — api.cerebras.ai         ~1000 req/day, 900 tok/s (САМЫЙ БЫСТРЫЙ)
  openrouter  — openrouter.ai           200 req/day на free моделях
  sambanova   — api.sambanova.ai        бесплатный tier, 600 tok/s
  together    — api.together.xyz        $25 кредитов при регистрации
  ollama      — localhost:11434         без лимитов, локально

Получение ключей:
  Cerebras:   https://inference.cerebras.ai   → Sign Up → API Keys
  OpenRouter: https://openrouter.ai           → Sign In → Keys
  SambaNova:  https://cloud.sambanova.ai      → Get Started → API Key
  Together:   https://api.together.xyz        → Sign Up ($25 free)

Добавить в backend/.env.prod:
  CEREBRAS_API_KEY=csk-xxx
  OPENROUTER_API_KEY=sk-or-v1-xxx
  SAMBANOVA_API_KEY=xxx
  TOGETHER_API_KEY=xxx

Использование:
  python3 generate_articles_universal.py --provider cerebras --limit 200
  python3 generate_articles_universal.py --provider openrouter --limit 100
  python3 generate_articles_universal.py --provider sambanova
  python3 generate_articles_universal.py --list-providers

Run in background:
  nohup python3 generate_articles_universal.py --provider cerebras --limit 10000 > /tmp/cerebras.log 2>&1 &
  nohup python3 generate_articles_universal.py --provider openrouter --limit 10000 > /tmp/openrouter.log 2>&1 &
"""
import argparse
import json
import logging
import os
import re
import sys
import time
import uuid
from datetime import datetime, timedelta

import httpx
import psycopg2

sys.path.insert(0, os.path.dirname(__file__))
from generate_articles_ollama import (
    DB_URL, slugify, text_to_blocks, calc_reading_time,
    save_article, update_article, save_translations, notify_indexnow,
)
from generate_articles_gemini import ALL_TOPICS, topic_key, STOP, _EXTRA_FILE

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

# ── Provider registry ─────────────────────────────────────────────────────────
PROVIDERS = {
    "cerebras": {
        "base_url":   "https://api.cerebras.ai/v1/chat/completions",
        "env_vars":   ["CEREBRAS_API_KEY"] + [f"CEREBRAS_API_KEY_{i}" for i in range(2, 10)],
        "models":     ["qwen-3-235b-a22b-instruct-2507", "gpt-oss-120b", "llama3.1-8b"],
        "default":    "qwen-3-235b-a22b-instruct-2507",
        "rpd":        1000,
        "rpm":        30,
        "speed":      "~900 tok/s, 235B model (highest quality)",
        "register":   "https://inference.cerebras.ai",
    },
    "openrouter": {
        "base_url":   "https://openrouter.ai/api/v1/chat/completions",
        "env_vars":   ["OPENROUTER_API_KEY"] + [f"OPENROUTER_API_KEY_{i}" for i in range(2, 10)],
        "models":     [
            "meta-llama/llama-3.3-70b-instruct:free",
            "google/gemma-3-27b-it:free",
            "qwen/qwq-32b:free",
            "mistralai/mistral-7b-instruct:free",
        ],
        "default":    "meta-llama/llama-3.3-70b-instruct:free",
        "rpd":        200,
        "rpm":        20,
        "speed":      "~300 tok/s",
        "register":   "https://openrouter.ai",
    },
    "sambanova": {
        "base_url":   "https://api.sambanova.ai/v1/chat/completions",
        "env_vars":   ["SAMBANOVA_API_KEY"] + [f"SAMBANOVA_API_KEY_{i}" for i in range(2, 10)],
        "models":     ["Meta-Llama-3.3-70B-Instruct", "Meta-Llama-3.1-8B-Instruct"],
        "default":    "Meta-Llama-3.3-70B-Instruct",
        "rpd":        1000,
        "rpm":        30,
        "speed":      "~600 tok/s",
        "register":   "https://cloud.sambanova.ai",
    },
    "together": {
        "base_url":   "https://api.together.xyz/v1/chat/completions",
        "env_vars":   ["TOGETHER_API_KEY"] + [f"TOGETHER_API_KEY_{i}" for i in range(2, 10)],
        "models":     [
            "meta-llama/Meta-Llama-3.3-70B-Instruct-Turbo",
            "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
        ],
        "default":    "meta-llama/Meta-Llama-3.3-70B-Instruct-Turbo",
        "rpd":        99999,  # credit-based, not req/day
        "rpm":        60,
        "speed":      "~400 tok/s",
        "register":   "https://api.together.xyz ($25 free credit)",
    },
    "groq": {
        "base_url":   "https://api.groq.com/openai/v1/chat/completions",
        "env_vars":   ["GROQ_API_KEY"] + [f"GROQ_API_KEY_{i}" for i in range(2, 10)],
        "models":     ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"],
        "default":    "llama-3.3-70b-versatile",
        "rpd":        14400,
        "rpm":        30,
        "speed":      "~700 tok/s",
        "register":   "https://console.groq.com",
    },
}

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
Criteria with SPECIFIC values, lab workup, imaging, scoring systems. (300 words)

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


# ── Universal KeyRotator ──────────────────────────────────────────────────────

class KeyRotator:
    def __init__(self, keys: list[str], provider_name: str):
        self.keys = keys
        self.provider = provider_name
        self.idx = 0
        self.exhausted: set[int] = set()
        self.requests: dict[int, int] = {i: 0 for i in range(len(keys))}

    @property
    def current(self) -> str:
        return self.keys[self.idx]

    @property
    def active_count(self) -> int:
        return len(self.keys) - len(self.exhausted)

    def rotate(self, exhausted: bool = False) -> bool:
        if exhausted:
            self.exhausted.add(self.idx)
            log.warning("  [%s] Key %d/%d daily limit — marking exhausted",
                        self.provider, self.idx + 1, len(self.keys))
        for _ in range(len(self.keys)):
            self.idx = (self.idx + 1) % len(self.keys)
            if self.idx not in self.exhausted:
                log.info("  Switched to key %d/%d", self.idx + 1, len(self.keys))
                return True
        return False

    def wait_for_reset(self):
        now = datetime.utcnow()
        tomorrow = (now + timedelta(days=1)).replace(
            hour=0, minute=2, second=0, microsecond=0)
        wait_sec = int((tomorrow - now).total_seconds())
        h, m = wait_sec // 3600, (wait_sec % 3600) // 60
        log.info("=" * 60)
        log.info("[%s] ALL KEYS EXHAUSTED — sleeping %dh %dm until %s UTC",
                 self.provider, h, m, tomorrow.strftime("%H:%M"))
        log.info("Status: %s", self.status())
        log.info("=" * 60)
        time.sleep(wait_sec)
        self.exhausted.clear()
        self.idx = 0
        log.info("[%s] Limits reset — resuming with all %d keys", self.provider, len(self.keys))

    def record(self):
        self.requests[self.idx] = self.requests.get(self.idx, 0) + 1

    def status(self) -> str:
        parts = [f"key{i+1}:{'✓' if i not in self.exhausted else '✗'}({self.requests.get(i,0)}r)"
                 for i in range(len(self.keys))]
        return " | ".join(parts)


def generate_article(topic: str, category: str, model: str,
                     base_url: str, rotator: KeyRotator) -> dict | None:
    """Universal OpenAI-compatible API call with key rotation."""
    prompt = ARTICLE_PROMPT.format(topic=topic, category=category)
    consecutive_429 = 0

    while True:
        if rotator.active_count == 0:
            rotator.wait_for_reset()
            consecutive_429 = 0

        headers = {
            "Authorization": f"Bearer {rotator.current}",
            "Content-Type": "application/json",
        }
        # OpenRouter requires HTTP-Referer
        if "openrouter" in base_url:
            headers["HTTP-Referer"] = "https://medmind.pro"
            headers["X-Title"] = "MedMind AI"

        try:
            resp = httpx.post(
                base_url,
                headers=headers,
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 4096,
                    "temperature": 0.3,
                },
                timeout=120,
            )

            if resp.status_code == 429:
                consecutive_429 += 1
                retry_after = int(resp.headers.get("retry-after", "0") or "0")
                err_msg = ""
                try:
                    err_msg = resp.json().get("error", {}).get("message", "")
                except Exception:
                    err_msg = resp.text[:200]

                is_daily = (retry_after > 3600 or
                            "per day" in err_msg.lower() or
                            "quota" in err_msg.lower() and "PerDay" in err_msg or
                            "exceeded" in err_msg.lower() and retry_after > 300)
                if is_daily:
                    rotator.rotate(exhausted=True)
                    consecutive_429 = 0
                    continue

                if retry_after and retry_after < 120:
                    log.warning("  Rate limit — waiting %ds", retry_after + 1)
                    time.sleep(retry_after + 1)
                    consecutive_429 = 0
                    continue

                if consecutive_429 >= len(rotator.keys):
                    wait = min(60, consecutive_429 * 5)
                    log.warning("  All keys rate-limited — backing off %ds", wait)
                    time.sleep(wait)
                    consecutive_429 = 0
                    continue

                log.warning("  429 — switching key")
                time.sleep(3)
                rotator.rotate(exhausted=False)
                continue

            consecutive_429 = 0

            if resp.status_code in (401, 403):
                log.error("  Key %d invalid — switching", rotator.idx + 1)
                rotator.rotate(exhausted=True)
                continue

            if resp.status_code == 503:
                log.warning("  503 overloaded — waiting 20s")
                time.sleep(20)
                continue

            if resp.status_code != 200:
                log.error("  API error %s: %s", resp.status_code, resp.text[:200])
                return None

            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            log.info("  Tokens: %d in / %d out [key %d/%d]",
                     usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0),
                     rotator.idx + 1, len(rotator.keys))

            rotator.record()
            result = _parse_output(content)
            if not result:
                log.error("  Parse failed — preview: %s", content[:200])
            return result

        except httpx.TimeoutException:
            log.error("  Timeout (key %d)", rotator.idx + 1)
            return None
        except Exception as e:
            log.error("  API call failed: %s", e)
            return None


def load_keys(provider_cfg: dict) -> list[str]:
    keys: list[str] = []
    env_file = os.path.join(os.path.dirname(__file__), "backend", ".env.prod")
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                for var in provider_cfg["env_vars"]:
                    if line.startswith(f"{var}="):
                        val = line.split("=", 1)[1].strip()
                        if val and val not in keys:
                            keys.append(val)
    for var in provider_cfg["env_vars"]:
        val = os.environ.get(var, "")
        if val and val not in keys:
            keys.append(val)
    return keys


def load_existing_keys(conn) -> set[str]:
    existing = set()
    with conn.cursor() as cur:
        cur.execute("SELECT slug, title FROM articles WHERE is_published = true")
        for slug, title in cur.fetchall():
            parts = [w for w in slug.split("-") if w not in STOP and len(w) > 1]
            if parts:
                existing.add("-".join(parts[:2]))
            words = [w for w in re.split(r"[\s\-]+", title.lower()) if w not in STOP and len(w) > 1]
            if words:
                existing.add("-".join(words[:2]))
    return existing


def main():
    parser = argparse.ArgumentParser(description="MedMind Universal Article Generator")
    parser.add_argument("--provider",    default="cerebras",
                        choices=list(PROVIDERS.keys()),
                        help="API provider (default: cerebras)")
    parser.add_argument("--model",       default=None, help="Override model name")
    parser.add_argument("--limit",       type=int, default=10000)
    parser.add_argument("--category",    default=None)
    parser.add_argument("--delay",       type=float, default=2.0)
    parser.add_argument("--no-phase2",   action="store_true")
    parser.add_argument("--dry-run",     action="store_true")
    parser.add_argument("--list-providers", action="store_true")
    args = parser.parse_args()

    if args.list_providers:
        print("\nAvailable providers:\n")
        for name, cfg in PROVIDERS.items():
            print(f"  {name:<12} {cfg['speed']:<25} {cfg['rpd']} req/day  {cfg['register']}")
        print("\nAdd keys to backend/.env.prod:")
        for name, cfg in PROVIDERS.items():
            print(f"  {cfg['env_vars'][0]}=your_key_here")
        print()
        return

    provider_cfg = PROVIDERS[args.provider]
    model = args.model or provider_cfg["default"]
    base_url = provider_cfg["base_url"]

    keys = load_keys(provider_cfg)
    if not keys:
        print(f"\n❌  No API keys for '{args.provider}'!")
        print(f"Register at: {provider_cfg['register']}")
        print(f"Add to backend/.env.prod: {provider_cfg['env_vars'][0]}=your_key\n")
        sys.exit(1)

    # Validate keys
    valid_keys = []
    for k in keys:
        try:
            headers = {"Authorization": f"Bearer {k}", "Content-Type": "application/json"}
            if "openrouter" in base_url:
                headers["HTTP-Referer"] = "https://medmind.pro"
            test = httpx.post(base_url, headers=headers,
                              json={"model": model,
                                    "messages": [{"role": "user", "content": "OK"}],
                                    "max_tokens": 3},
                              timeout=15)
            if test.status_code in (200, 429, 404):
                # 404 = model not found (key is valid, wrong model name)
                # 429 = rate-limited (key valid)
                # 200 = active
                valid_keys.append(k)
                status = {200: "active", 429: "rate-limited", 404: "valid/model-check"}.get(test.status_code, "unknown")
                log.info("  ✓ Key %d/%d valid (%s): %s...", len(valid_keys), len(keys), status, k[:20])
            else:
                log.warning("  ✗ Key invalid: %s... (HTTP %s)", k[:20], test.status_code)
        except Exception as e:
            log.warning("  ✗ Key check failed: %s... (%s)", k[:20], e)

    if not valid_keys:
        print(f"\n❌  No valid keys for '{args.provider}'.\n")
        sys.exit(1)

    rotator = KeyRotator(valid_keys, args.provider)
    log.info("Provider: %s | Model: %s | Keys: %d | Speed: %s",
             args.provider, model, len(valid_keys), provider_cfg["speed"])

    conn = psycopg2.connect(DB_URL)

    # Smart pre-filter
    log.info("Pre-loading existing articles from DB...")
    existing_keys = load_existing_keys(conn)
    log.info("DB has %d existing article keys", len(existing_keys))

    # Load extra topics
    all_topics = dict(ALL_TOPICS)
    if os.path.exists(_EXTRA_FILE):
        with open(_EXTRA_FILE) as f:
            for cat, topics in json.load(f).items():
                all_topics.setdefault(cat, [])
                seen = {t.lower() for t in all_topics[cat]}
                for t in topics:
                    if t.lower() not in seen:
                        all_topics[cat].append(t)
                        seen.add(t.lower())

    pending = []
    for cat, topics in all_topics.items():
        if args.category and cat != args.category:
            continue
        for topic in topics:
            if topic_key(topic) not in existing_keys:
                pending.append((cat, topic))

    log.info("Pending topics: %d", len(pending))

    if args.dry_run:
        by_cat: dict[str, int] = {}
        for cat, _ in pending:
            by_cat[cat] = by_cat.get(cat, 0) + 1
        for cat, n in sorted(by_cat.items(), key=lambda x: -x[1])[:15]:
            print(f"  {cat:<30} {n} pending")
        print(f"\n  Total: {len(pending)} topics")
        conn.close()
        return

    count = errors = skipped = 0
    generated_keys: set[str] = set()

    for category, topic in pending:
        if count >= args.limit:
            break
        if topic_key(topic) in generated_keys:
            continue

        log.info("[%d/%d] %s / %s", count + 1, args.limit, category, topic)

        t0 = time.time()
        data = generate_article(topic, category, model, base_url, rotator)
        elapsed = time.time() - t0

        if not data or not data.get("title") or not data.get("body_text"):
            errors += 1
            continue

        title   = data["title"]
        excerpt = data.get("excerpt", "")
        body    = text_to_blocks(data["body_text"])
        slug    = slugify(title)

        log.info("  Generated: '%s' (%.1fs, %d blocks)", title[:55], elapsed, len(body))

        article_id = str(uuid.uuid4())
        saved = save_article(conn, article_id, slug, title, excerpt, body, category)
        if not saved:
            saved = save_article(conn, article_id, slugify(f"{title} {category}")[:90],
                                 title, excerpt, body, category)
        if not saved:
            skipped += 1
            continue

        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE articles SET generated_by=%s WHERE id=%s",
                            (args.provider, article_id))
            conn.commit()
        except Exception:
            conn.rollback()

        generated_keys.add(topic_key(topic))
        n_tr = save_translations(conn, article_id, title, excerpt, body)
        log.info("  ✓ Published + %d translations | %s", n_tr, slug)

        if _HAS_COVER:
            try:
                cover_url = _fetch_cover_image(title, category)
                if cover_url:
                    with conn.cursor() as cur:
                        cur.execute("UPDATE articles SET cover_image=%s WHERE id=%s",
                                    (cover_url, article_id))
                    conn.commit()
            except Exception:
                pass

        if _HAS_OG:
            try:
                _gen_og_image(slug, title, category, calc_reading_time(body))
            except Exception:
                pass

        notify_indexnow(slug)
        count += 1
        time.sleep(args.delay)

    log.info("Phase 1 done. Generated: %d | Skipped: %d | Errors: %d", count, skipped, errors)

    # Phase 2: regenerate shallow articles
    if not args.no_phase2:
        log.info("Phase 2: regenerating shallow articles (reading_time <= 3 min)...")
        regen_count = regen_errors = 0
        while True:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, title, excerpt, category FROM articles
                    WHERE reading_time_minutes <= 3 AND is_published = true
                    ORDER BY created_at ASC LIMIT 50
                """)
                rows = cur.fetchall()
            if not rows:
                break
            for art_id, art_title, art_excerpt, art_cat in rows:
                data = generate_article(art_title, art_cat, model, base_url, rotator)
                if not data or not data.get("body_text"):
                    regen_errors += 1
                    continue
                new_body = text_to_blocks(data["body_text"])
                if update_article(conn, art_id, data.get("title") or art_title,
                                  data.get("excerpt") or art_excerpt, new_body):
                    save_translations(conn, art_id, data.get("title") or art_title,
                                      data.get("excerpt") or art_excerpt, new_body)
                    regen_count += 1
                time.sleep(args.delay)
        log.info("Phase 2 done. Regenerated: %d | Errors: %d", regen_count, regen_errors)

    conn.close()
    log.info("All done. Key usage: %s", rotator.status())


if __name__ == "__main__":
    main()
