"""
MedMind Topic Discovery — автоматически генерирует новые темы через Groq API.

Сохраняет в topics_extra.json, который подхватывают оба генератора
(generate_articles_groq.py и generate_articles_gemini.py).

Использование:
    python3 discover_topics.py                         # 50 тем на каждую категорию
    python3 discover_topics.py --per-category 100      # 100 тем на категорию
    python3 discover_topics.py --categories cardiology neurology  # только эти
    python3 discover_topics.py --new-categories        # придумать новые категории
    python3 discover_topics.py --target 5000           # генерировать пока не достигнем цели

Run in background:
    nohup python3 discover_topics.py --per-category 80 > /tmp/discover.log 2>&1 &
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

sys.path.insert(0, os.path.dirname(__file__))
from generate_articles_ollama import TOPICS as BASE_TOPICS, DB_URL, slugify
from generate_articles_gemini import NEW_TOPICS, ALL_TOPICS, topic_key, STOP

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

GROQ_URL    = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL  = "llama-3.3-70b-versatile"
EXTRA_FILE  = os.path.join(os.path.dirname(__file__), "topics_extra.json")

DISCOVERY_PROMPT = """\
You are building a comprehensive medical education database similar to UpToDate and StatPearls.
Your task: generate exactly {n} unique, high-value medical article topics for the "{category}" category.

Requirements:
- Each topic = specific clinical condition / drug / syndrome / procedure / diagnostic approach
- Must be commonly searched by medical students, residents, and physicians
- Include specific medical terminology: drug names, eponyms, scoring systems, criteria names
- Avoid generic titles like "Overview of..." or "Introduction to..."
- Each topic should generate a 2500-word clinical article
- NO numbering, NO bullet points, NO extra text — just one topic per line

Topics to AVOID (already exist):
{existing_sample}

Generate exactly {n} NEW unique topics for "{category}" (one per line):"""

CATEGORY_DISCOVERY_PROMPT = """\
You are building a comprehensive medical education database.
Suggest {n} NEW medical specialties or topic categories not in this list:
{existing_categories}

Requirements:
- Each category should support 50+ unique article topics
- Focus on high-traffic medical searches
- Can be subspecialties, cross-cutting themes, or emerging fields
- Format: slug|Full Name (e.g. "sports-medicine|Sports Medicine")
- One category per line, no extra text

Generate {n} new medical categories:"""


def load_groq_keys() -> list[str]:
    keys = []
    env_vars = ["GROQ_API_KEY_3", "GROQ_API_KEY_4", "GROQ_API_KEY_5"]
    env_file = os.path.join(os.path.dirname(__file__), "..", "..", "backend", ".env.prod")
    if os.path.exists(env_file):
        with open(env_file) as f:
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


def call_groq(prompt: str, keys: list[str], max_tokens: int = 2000) -> str | None:
    """Call Groq with key rotation. Waits until midnight UTC if all keys exhausted."""
    import datetime as _dt
    exhausted: set[int] = set()

    while True:
        # All keys daily-exhausted → sleep until Groq reset
        if len(exhausted) >= len(keys):
            now = _dt.datetime.utcnow()
            tomorrow = (now + _dt.timedelta(days=1)).replace(
                hour=0, minute=2, second=0, microsecond=0)
            wait_sec = int((tomorrow - now).total_seconds())
            h, m = wait_sec // 3600, (wait_sec % 3600) // 60
            log.info("All Groq keys exhausted — sleeping %dh %dm until %s UTC (discovery pause)",
                     h, m, tomorrow.strftime("%H:%M"))
            time.sleep(wait_sec)
            exhausted.clear()
            log.info("Groq daily limits reset — resuming topic discovery")

        for i, key in enumerate(keys):
            if i in exhausted:
                continue
            try:
                resp = httpx.post(
                    GROQ_URL,
                    headers={"Authorization": f"Bearer {key}",
                             "Content-Type": "application/json"},
                    json={"model": GROQ_MODEL,
                          "messages": [{"role": "user", "content": prompt}],
                          "max_tokens": max_tokens, "temperature": 0.7},
                    timeout=60,
                )
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"]

                if resp.status_code == 429:
                    retry = int(resp.headers.get("retry-after", "0") or "0")
                    err_msg = ""
                    try:
                        err_msg = resp.json().get("error", {}).get("message", "")
                    except Exception:
                        pass
                    is_daily = (retry > 3600 or "per day" in err_msg.lower())
                    if is_daily:
                        log.warning("  Key %d/%d daily limit", i + 1, len(keys))
                        exhausted.add(i)
                        continue
                    # Temporary RPM — wait and retry same key
                    wait = min(retry + 1, 60) if retry else 10
                    log.warning("  Key %d/%d RPM — waiting %ds", i + 1, len(keys), wait)
                    time.sleep(wait)
                    # retry same key once
                    resp2 = httpx.post(
                        GROQ_URL,
                        headers={"Authorization": f"Bearer {key}",
                                 "Content-Type": "application/json"},
                        json={"model": GROQ_MODEL,
                              "messages": [{"role": "user", "content": prompt}],
                              "max_tokens": max_tokens, "temperature": 0.7},
                        timeout=60,
                    )
                    if resp2.status_code == 200:
                        return resp2.json()["choices"][0]["message"]["content"]
                else:
                    log.warning("  Groq %s: %s", resp.status_code, resp.text[:100])

            except Exception as e:
                log.warning("  Groq error (key %d): %s", i + 1, e)

        # If we get here without returning, all non-exhausted keys failed → retry outer while
        if len(exhausted) < len(keys):
            time.sleep(5)  # brief pause before next round


def load_extra_topics() -> dict[str, list[str]]:
    if os.path.exists(EXTRA_FILE):
        with open(EXTRA_FILE) as f:
            return json.load(f)
    return {}


def save_extra_topics(extra: dict[str, list[str]]):
    with open(EXTRA_FILE, "w") as f:
        json.dump(extra, f, indent=2, ensure_ascii=False)


def load_db_keys(conn) -> set[str]:
    """Load first-2-word keys from DB — same logic as generators."""
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


def build_all_known_topics() -> dict[str, set[str]]:
    """All topics currently known (hardcoded + extra file)."""
    extra = load_extra_topics()
    all_known: dict[str, set[str]] = {}
    for cat, topics in ALL_TOPICS.items():
        all_known[cat] = {topic_key(t) for t in topics}
    for cat, topics in extra.items():
        all_known.setdefault(cat, set()).update(topic_key(t) for t in topics)
    return all_known


def discover_for_category(category: str, existing_topics: list[str],
                          n: int, keys: list[str]) -> list[str]:
    """Ask Groq to generate n new topics for a category."""
    # Show up to 20 existing topics so Groq knows what to avoid
    sample = "\n".join(existing_topics[:20]) if existing_topics else "none"
    prompt = DISCOVERY_PROMPT.format(
        n=n, category=category, existing_sample=sample
    )
    log.info("  Discovering %d topics for '%s'...", n, category)
    raw = call_groq(prompt, keys, max_tokens=min(n * 25, 3000))
    if not raw:
        log.warning("  Failed to get topics for '%s'", category)
        return []

    # Parse one topic per line, clean up numbering/bullets
    topics = []
    for line in raw.strip().splitlines():
        line = re.sub(r"^[\d\.\-\*\•\s]+", "", line).strip()
        line = re.sub(r"\*+", "", line).strip()
        if len(line) > 10 and len(line) < 150:
            topics.append(line)

    log.info("  Got %d topics from Groq for '%s'", len(topics), category)
    return topics


def discover_new_categories(existing_slugs: list[str], n: int,
                            keys: list[str]) -> list[tuple[str, str]]:
    """Ask Groq to suggest entirely new medical categories."""
    prompt = CATEGORY_DISCOVERY_PROMPT.format(
        n=n,
        existing_categories="\n".join(existing_slugs)
    )
    raw = call_groq(prompt, keys, max_tokens=1000)
    if not raw:
        return []
    cats = []
    for line in raw.strip().splitlines():
        line = line.strip()
        if "|" in line:
            parts = line.split("|", 1)
            slug = re.sub(r"[^a-z0-9\-]", "", parts[0].strip().lower())
            name = parts[1].strip()
            if slug and name and slug not in existing_slugs:
                cats.append((slug, name))
    return cats


def main():
    parser = argparse.ArgumentParser(description="MedMind Topic Discovery via Groq")
    parser.add_argument("--per-category",  type=int, default=50,
                        help="New topics to discover per category (default: 50)")
    parser.add_argument("--categories",    nargs="+", default=None,
                        help="Only these categories (default: all)")
    parser.add_argument("--new-categories",action="store_true",
                        help="Also discover entirely new categories")
    parser.add_argument("--target",        type=int, default=0,
                        help="Keep discovering until DB has this many articles")
    parser.add_argument("--rounds",        type=int, default=1,
                        help="Discovery rounds (default 1; use with --target)")
    args = parser.parse_args()

    keys = load_groq_keys()
    if not keys:
        print("❌  No GROQ_API_KEY found in backend/.env.prod")
        sys.exit(1)
    log.info("Loaded %d Groq keys", len(keys))

    conn = psycopg2.connect(DB_URL)
    db_keys = load_db_keys(conn)
    log.info("DB has %d existing article keys", len(db_keys))

    if args.target:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM articles WHERE is_published=true")
            current = cur.fetchone()[0]
        if current >= args.target:
            log.info("Already at %d articles (target %d) — nothing to do", current, args.target)
            conn.close()
            return
        log.info("Current: %d articles, target: %d, need: %d more", current, args.target, args.target - current)

    extra = load_extra_topics()
    all_known = build_all_known_topics()
    total_new = 0

    # ── Discover new categories ────────────────────────────────────────────────
    if args.new_categories:
        log.info("Discovering new medical categories...")
        existing_slugs = list(ALL_TOPICS.keys()) + list(extra.keys())
        new_cats = discover_new_categories(existing_slugs, 20, keys)
        log.info("Discovered %d new categories: %s",
                 len(new_cats), [s for s, _ in new_cats])
        for slug, name in new_cats:
            if slug not in extra:
                extra[slug] = []
                all_known[slug] = set()
                log.info("  Added category: %s (%s)", slug, name)

    # ── Discover topics per category ───────────────────────────────────────────
    categories = args.categories or list(ALL_TOPICS.keys()) + \
                 [c for c in extra.keys() if c not in ALL_TOPICS]

    for round_num in range(args.rounds):
        if args.rounds > 1:
            log.info("=== Round %d/%d ===", round_num + 1, args.rounds)

        for cat in categories:
            # Existing topics for this category (to tell Groq what to avoid)
            existing_in_cat = list(ALL_TOPICS.get(cat, [])) + list(extra.get(cat, []))

            new_topics = discover_for_category(
                cat, existing_in_cat, args.per_category, keys
            )

            # Filter: deduplicate against all known topics + DB
            added = 0
            for t in new_topics:
                key2 = topic_key(t)
                if key2 not in all_known.get(cat, set()) and key2 not in db_keys:
                    # Also check cross-category collision
                    already = any(key2 in keys_set for keys_set in all_known.values())
                    if not already:
                        extra.setdefault(cat, []).append(t)
                        all_known.setdefault(cat, set()).add(key2)
                        added += 1

            log.info("  '%s': +%d new topics (filtered from %d raw)",
                     cat, added, len(new_topics))
            total_new += added

            # Save after each category (crash-safe)
            save_extra_topics(extra)
            time.sleep(1)  # Small pause between Groq calls

        log.info("Round %d done. Total new topics discovered: %d",
                 round_num + 1, total_new)

    conn.close()

    # ── Summary ────────────────────────────────────────────────────────────────
    log.info("=" * 60)
    log.info("Discovery complete!")
    log.info("topics_extra.json: %d categories, %d total topics",
             len(extra), sum(len(v) for v in extra.values()))
    log.info("Grand total topics (hardcoded + discovered): %d",
             sum(len(v) for v in ALL_TOPICS.values()) +
             sum(len(v) for v in extra.values()))
    log.info("Restart generators to pick up new topics.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
