"""
Auto-indexing service — notifies search engines and AI crawlers when content is published.

Protocols supported:
  - IndexNow (Bing, Yandex, Seznam, Naver — instant notification)
  - Google Sitemap ping
  - Bing Sitemap ping
"""
import asyncio
import logging
from typing import Optional

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)

SITE_URL      = "https://medmind.pro"
SITEMAP_URL   = f"{SITE_URL}/sitemap.xml"
INDEXNOW_KEY  = getattr(settings, "INDEXNOW_KEY", "")

# IndexNow-compatible engines
INDEXNOW_HOSTS = [
    "https://api.indexnow.org/indexnow",
    "https://www.bing.com/indexnow",
    "https://yandex.com/indexnow",
]

# Note: Google and Bing sitemap ping endpoints were deprecated in 2023.
# Google now crawls updated sitemaps automatically via Search Console.
# Use IndexNow for Bing — it's their preferred real-time notification method.


async def _ping_indexnow(urls: list[str]) -> None:
    """Submit URLs to IndexNow — notifies Bing, Yandex, Seznam, Naver simultaneously."""
    if not INDEXNOW_KEY:
        log.debug("INDEXNOW_KEY not set — skipping IndexNow ping")
        return
    if not urls:
        return

    payload = {
        "host": "medmind.pro",
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": urls[:100],  # IndexNow allows up to 10 000, but keep it sane
    }

    async with httpx.AsyncClient(timeout=10) as client:
        for endpoint in INDEXNOW_HOSTS:
            try:
                r = await client.post(endpoint, json=payload)
                if r.status_code in (200, 202):
                    log.info("IndexNow %s → %d URLs → %s OK", endpoint, len(urls), r.status_code)
                else:
                    log.warning("IndexNow %s → %d (body: %s)", endpoint, r.status_code, r.text[:200])
            except Exception as e:
                log.warning("IndexNow %s failed: %s", endpoint, e)


async def notify_article_published(slug: str, extra_slugs: Optional[list[str]] = None) -> None:
    """
    Call this whenever an article (or batch of articles) becomes publicly available.
    Fires IndexNow + sitemap pings concurrently in a background task.
    """
    urls = [f"{SITE_URL}/articles/{slug}"]
    for s in (extra_slugs or []):
        urls.append(f"{SITE_URL}/articles/{s}")

    # Add translated variants (?lang=xx) so they get crawled too
    locales = ["ru", "de", "fr", "es", "tr", "ar"]
    lang_urls = [f"{SITE_URL}/articles/{slug}?lang={loc}" for loc in locales]
    all_urls = urls + lang_urls

    log.info("Auto-indexing %d URLs for slug '%s'", len(all_urls), slug)
    await _ping_indexnow(all_urls)


async def notify_urls(urls: list[str]) -> None:
    """Generic: submit any list of URLs to IndexNow."""
    await _ping_indexnow(urls)
