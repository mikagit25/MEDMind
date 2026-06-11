"""One-shot: submit all published articles to IndexNow + ping Google/Bing sitemaps."""
import asyncio
import os
import httpx
import psycopg2

DB_DSN = os.environ.get("DATABASE_URL", "postgresql://medmind:medmind_secret@localhost:5434/medmind").replace("postgresql+asyncpg://", "postgresql://")
INDEXNOW_KEY = "b58fd85c39a0441e97c1587402e9c9df"
SITE_URL = "https://medmind.pro"
SITEMAP_URL = f"{SITE_URL}/sitemap.xml"

INDEXNOW_HOSTS = [
    "https://api.indexnow.org/indexnow",
    "https://www.bing.com/indexnow",
    "https://yandex.com/indexnow",
]

SITEMAP_PINGS = [
    f"https://www.google.com/ping?sitemap={SITEMAP_URL}",
    f"https://www.bing.com/ping?sitemap={SITEMAP_URL}",
]

def get_slugs():
    conn = psycopg2.connect(DB_DSN)
    with conn.cursor() as cur:
        cur.execute("SELECT slug FROM articles WHERE is_published = true")
        slugs = [row[0] for row in cur.fetchall()]
    conn.close()
    return slugs

async def main():
    slugs = get_slugs()
    print(f"Found {len(slugs)} published articles")

    # Build URL list — include base + main translated variants
    urls = []
    for slug in slugs:
        urls.append(f"{SITE_URL}/articles/{slug}")
    # Add sitemap itself
    urls.append(SITE_URL + "/")
    urls.append(SITE_URL + "/how-it-works")
    urls.append(SITE_URL + "/articles")

    print(f"Total URLs to submit: {len(urls)}")

    payload = {
        "host": "medmind.pro",
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": urls,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        # IndexNow (Bing, Yandex, etc.)
        for endpoint in INDEXNOW_HOSTS:
            try:
                r = await client.post(endpoint, json=payload)
                print(f"IndexNow {endpoint} → {r.status_code}: {r.text[:100]}")
            except Exception as e:
                print(f"IndexNow {endpoint} FAILED: {e}")

        # Sitemap pings (Google + Bing)
        for url in SITEMAP_PINGS:
            try:
                r = await client.get(url)
                print(f"Sitemap ping → {r.status_code}: {url}")
            except Exception as e:
                print(f"Sitemap ping FAILED: {e}")

    print("Done.")

asyncio.run(main())
