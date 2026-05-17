#!/usr/bin/env python3
"""
MedMind AI — Telegram Channel Publisher

Publishes medical articles to Telegram channel.
Yandex Zen auto-imports from Telegram → no extra setup needed.

Tracking: /opt/medmind/telegram_published.json
Cron:     30 10 * * *  (10:30 UTC daily, after YouTube uploads)

Usage:
    python3 telegram_publisher.py --dry-run          # preview posts
    python3 telegram_publisher.py --limit 3          # publish 3 articles
    python3 telegram_publisher.py --slug myocardial  # publish specific article
    python3 telegram_publisher.py --lang ru          # Russian channel
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

sys.path.insert(0, "/opt/medmind")
try:
    from generate_og_image import generate_og_image as _gen_og
    _HAS_OG = True
except ImportError:
    _HAS_OG = False


def _make_og_image(article: dict, detail: dict | None) -> str:
    """Generate (or return existing) OG image URL for the article."""
    if not _HAS_OG:
        return ""
    slug     = article.get("slug", "")
    title    = (detail or article).get("title", slug)
    category = article.get("category", "diseases")
    rt       = article.get("reading_time_minutes", 8)
    try:
        return _gen_og(slug, title, category, rt)
    except Exception as e:
        print(f"  ⚠️  OG image failed: {e}")
        return ""


# ── Config ─────────────────────────────────────────────────────────────────────
BOT_TOKEN      = os.environ.get("TG_BOT_TOKEN",
                 "8657721269:AAEkhJ92vHR4K1CkA14nFcy0_bA95c38QZk")
CHANNEL_ID     = os.environ.get("TG_CHANNEL_ID", "")   # set via env or --channel arg
API_URL        = "https://medmind.pro/api/v1"
TRACKING_FILE  = Path("/opt/medmind/telegram_published.json")
DAILY_LIMIT    = 3    # posts per day (Zen prefers consistent cadence over spam)

# Category → emoji
CATEGORY_EMOJI = {
    "cardiology":          "❤️",
    "neurology":           "🧠",
    "diseases":            "🫀",
    "drugs":               "💊",
    "pharmacology":        "💊",
    "internal-medicine":   "🩺",
    "emergency":           "🚑",
    "surgery":             "✂️",
    "pediatrics":          "👶",
    "ob-gyn":              "🤰",
    "oncology":            "🎗️",
    "psychiatry":          "🧘",
    "endocrinology":       "⚗️",
    "infectious-diseases": "🦠",
    "diagnostics":         "🧪",
    "procedures":          "🔬",
    "symptoms":            "🩻",
    "nutrition":           "🥗",
    "orthopedics":         "🦴",
    "rheumatology":        "🤝",
    "hematology":          "🩸",
    "nephrology":          "🫘",
    "pulmonology":         "🫁",
    "ophthalmology":       "👁️",
    "ent":                 "👂",
    "urology":             "⚕️",
    "geriatrics":          "👴",
    "veterinary":          "🐾",
    "dermatology":         "🩹",
}

# Category → Russian label
CATEGORY_RU = {
    "cardiology":          "Кардиология",
    "neurology":           "Неврология",
    "diseases":            "Болезни",
    "drugs":               "Фармакология",
    "pharmacology":        "Фармакология",
    "internal-medicine":   "Терапия",
    "emergency":           "Скорая помощь",
    "surgery":             "Хирургия",
    "pediatrics":          "Педиатрия",
    "ob-gyn":              "Акушерство",
    "oncology":            "Онкология",
    "psychiatry":          "Психиатрия",
    "endocrinology":       "Эндокринология",
    "infectious-diseases": "Инфекции",
    "diagnostics":         "Диагностика",
    "procedures":          "Процедуры",
    "symptoms":            "Симптомы",
    "nutrition":           "Питание",
    "orthopedics":         "Ортопедия",
    "rheumatology":        "Ревматология",
    "hematology":          "Гематология",
    "nephrology":          "Нефрология",
    "pulmonology":         "Пульмонология",
    "ophthalmology":       "Офтальмология",
    "ent":                 "ЛОР",
    "urology":             "Урология",
    "geriatrics":          "Гериатрия",
    "veterinary":          "Ветеринария",
    "dermatology":         "Дерматология",
}

HASHTAGS_EN = "#MedicalEducation #Medicine #MedMindAI #USMLE #MedStudent"
HASHTAGS_RU = "#Медицина #МедицинскоеОбразование #MedMindAI #Врач #МедВуз"


# ── Tracking ───────────────────────────────────────────────────────────────────

def load_published() -> dict:
    if TRACKING_FILE.exists():
        with open(TRACKING_FILE) as f:
            return json.load(f)
    return {}

def save_published(data: dict):
    TRACKING_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TRACKING_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ── Article fetching ───────────────────────────────────────────────────────────

def fetch_articles(limit: int = 100, lang: str = "en") -> list[dict]:
    """Fetch published articles from API."""
    all_articles = []
    page = 1
    while len(all_articles) < limit:
        params = {"limit": 100, "page": page}
        if lang != "en":
            params["locale"] = lang
        try:
            r = httpx.get(f"{API_URL}/articles", params=params, timeout=15)
            if r.status_code != 200:
                break
            data = r.json()
            arts = data.get("articles", data) if isinstance(data, dict) else data
            if not arts:
                break
            all_articles.extend(arts)
            if len(arts) < 100:
                break
            page += 1
        except Exception as e:
            print(f"⚠️  API error: {e}")
            break
    return all_articles[:limit]


def fetch_article_detail(slug: str, lang: str = "en") -> dict | None:
    """Fetch full article with body. locale= returns translated title/excerpt."""
    params = {} if lang == "en" else {"locale": lang}
    try:
        r = httpx.get(f"{API_URL}/articles/{slug}", params=params, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def extract_key_points(body: list, max_points: int = 4) -> list[str]:
    """Extract H2 section headings as key points."""
    points = []
    for block in body:
        if block.get("type") == "h2":
            content = block.get("content", "").strip()
            if content and len(content) > 5:
                points.append(content)
        if len(points) >= max_points:
            break
    return points


def gtranslate(text: str, locale: str) -> str:
    """Translate text via Google Translate free API."""
    import urllib.parse, urllib.request, json as _json
    if not text or locale == "en":
        return text
    try:
        url = (
            "https://translate.googleapis.com/translate_a/single"
            "?client=gtx&sl=en&tl=" + locale
            + "&dt=t&q=" + urllib.parse.quote(text[:500])
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = _json.loads(resp.read())
        return "".join(p[0] for p in data[0] if p[0])
    except Exception:
        return text


# ── Post formatting ────────────────────────────────────────────────────────────

def format_post(article: dict, detail: dict | None, lang: str = "en") -> str:
    """Format article as Telegram-ready post with HTML markup."""
    slug     = article.get("slug", "")
    title    = article.get("title", "")
    excerpt  = article.get("excerpt", "")
    category = article.get("category", "")
    minutes  = article.get("reading_time_minutes", 0)

    emoji    = CATEGORY_EMOJI.get(category, "🩺")

    # Use translation if available
    if detail:
        title   = detail.get("title",   title)
        excerpt = detail.get("excerpt", excerpt)

    # Key points from body sections — translate if non-English
    body        = (detail or {}).get("body", [])
    key_points_en = extract_key_points(body, max_points=4)
    key_points = (
        key_points_en if lang == "en"
        else [gtranslate(pt, lang) for pt in key_points_en]
    )

    # Build URL
    if lang == "en":
        url      = f"https://medmind.pro/articles/{slug}"
        hashtags = HASHTAGS_EN
        cat_label = category.replace("-", " ").title()
        read_label = f"⏱ {minutes} min read"
        read_more  = "📖 Full article + sources:"
        subscribe  = "📚 Free medical platform: medmind.pro"
    else:
        url       = f"https://medmind.pro/articles/{slug}?lang={lang}"
        hashtags  = HASHTAGS_RU
        cat_label = CATEGORY_RU.get(category, category)
        read_label = f"⏱ {minutes} мин чтения"
        read_more  = "📖 Полная статья + источники:"
        subscribe  = "📚 Бесплатная медплатформа: medmind.pro"

    # Truncate excerpt
    if len(excerpt) > 300:
        excerpt = excerpt[:297] + "…"

    lines = [
        f"{emoji} <b>{title}</b>",
        "",
        excerpt,
    ]

    if key_points:
        lines.append("")
        for pt in key_points:
            lines.append(f"📌 {pt}")

    lines += [
        "",
        read_label,
        "",
        f"{read_more}",
        f"🔗 {url}",
        "",
        subscribe,
        "",
        hashtags,
        f"#{cat_label.replace(' ', '')}",
    ]

    return "\n".join(lines)


# ── Telegram API ───────────────────────────────────────────────────────────────

def send_message(channel_id: str, text: str, disable_preview: bool = False) -> dict | None:
    """Send message to Telegram channel. Returns response dict or None."""
    url  = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id":                  channel_id,
        "text":                     text[:4096],
        "parse_mode":               "HTML",
        "disable_web_page_preview": disable_preview,
    }
    try:
        r = httpx.post(url, json=data, timeout=15)
        result = r.json()
        if result.get("ok"):
            msg_id = result["result"]["message_id"]
            return result["result"]
        else:
            print(f"  ❌ Telegram error: {result.get('description', 'unknown')}")
            return None
    except Exception as e:
        print(f"  ❌ Request failed: {e}")
        return None


def send_photo_message(channel_id: str, photo_url: str, caption: str) -> dict | None:
    """Send photo with caption to channel."""
    url  = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    data = {
        "chat_id":    channel_id,
        "photo":      photo_url,
        "caption":    caption[:1024],
        "parse_mode": "HTML",
    }
    try:
        r = httpx.post(url, json=data, timeout=20)
        result = r.json()
        if result.get("ok"):
            return result["result"]
        # Photo failed (bad URL) — fallback to text
        return None
    except Exception:
        return None


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="MedMind Telegram Publisher")
    parser.add_argument("--channel", type=str, default=CHANNEL_ID,
                        help="Telegram channel ID or @username")
    parser.add_argument("--lang",    type=str, default="en",
                        help="Language: en | ru (default: en)")
    parser.add_argument("--limit",  type=int, default=DAILY_LIMIT,
                        help=f"Max posts per run (default: {DAILY_LIMIT})")
    parser.add_argument("--slug",   type=str, default=None,
                        help="Publish specific article slug")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview posts without sending")
    parser.add_argument("--force",   action="store_true",
                        help="Re-publish even if already published")
    args = parser.parse_args()

    channel = args.channel
    if not channel:
        print("❌ Channel ID not set. Use --channel @yourchannel or set TG_CHANNEL_ID env var")
        sys.exit(1)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    print(f"[{now}] Telegram publisher started")
    print(f"  Channel: {channel} | Lang: {args.lang} | Limit: {args.limit}")

    published = load_published()
    key_prefix = f"{channel}:{args.lang}"

    # Fetch articles
    if args.slug:
        articles = [{"slug": args.slug, "title": args.slug,
                     "excerpt": "", "category": "", "reading_time_minutes": 0}]
    else:
        articles = fetch_articles(limit=200, lang=args.lang)

    # Category priority — human medicine first, veterinary last
    PRIORITY = ["cardiology","neurology","diseases","emergency","surgery",
                "internal-medicine","pharmacology","drugs","oncology",
                "pediatrics","ob-gyn","psychiatry","endocrinology",
                "infectious-diseases","hematology","nephrology","pulmonology",
                "orthopedics","rheumatology","ophthalmology","ent","urology",
                "geriatrics","diagnostics","procedures","symptoms","nutrition",
                "dermatology","anatomy","veterinary"]

    def cat_priority(a: dict) -> int:
        cat = a.get("category", "")
        try:
            return PRIORITY.index(cat)
        except ValueError:
            return 50

    unpublished = [
        a for a in articles
        if args.force or f"{key_prefix}:{a['slug']}" not in published
    ]
    unpublished.sort(key=cat_priority)
    queue = unpublished[:args.limit]

    if not queue:
        print(f"  ✅ Nothing new to publish (all {len(published)} articles already sent)")
        return

    print(f"  Queue: {len(queue)} articles")

    success = 0
    for i, article in enumerate(queue, 1):
        slug = article["slug"]
        print(f"\n  [{i}/{len(queue)}] {slug}")

        # Fetch full article for body/key points
        detail = fetch_article_detail(slug, args.lang)

        # Format post
        post_text = format_post(article, detail, args.lang)

        if args.dry_run:
            print("  ── PREVIEW ──────────────────────────────")
            print(post_text)
            print("  ─────────────────────────────────────────")
            continue

        # Generate OG image if not yet created
        og_img_path = Path(f"/var/lib/docker/volumes/medmind_media_data/_data/og/{slug}.jpg")
        if og_img_path.exists():
            img_url = f"https://medmind.pro/media/og/{slug}.jpg"
        else:
            img_url = _make_og_image(article, detail)

        # Send with image, fallback to text
        sent = None
        if img_url:
            sent = send_photo_message(channel, img_url, post_text[:1024])
        if not sent:
            sent = send_message(channel, post_text)

        if sent:
            track_key = f"{key_prefix}:{slug}"
            published[track_key] = {
                "message_id":   sent.get("message_id"),
                "published_at": datetime.now(timezone.utc).isoformat(),
                "lang":         args.lang,
                "channel":      channel,
            }
            save_published(published)
            success += 1
            print(f"  ✅ Published (msg_id: {sent.get('message_id')})")
        else:
            print(f"  ❌ Failed")

        if i < len(queue):
            time.sleep(3)  # avoid Telegram flood limits

    print(f"\n[{now}] Done. Published: {success}/{len(queue)}")


if __name__ == "__main__":
    main()
