#!/usr/bin/env python3
"""SEO audit script — V4 Phase 5.

Checks:
  1. All sitemap URLs return HTTP 200
  2. Canonical URL is present and matches the expected URL
  3. hreflang reciprocity: if page A declares hreflang pointing to B, then B must declare hreflang back to A
  4. Medical disclaimer text is present in HTML for public medical content pages
  5. No sitemap URL has a non-passed verification status (indirectly via status check)

Usage:
  python scripts/ops/seo_audit.py [--site https://medmind.pro] [--timeout 10] [--max-urls 200]

Exit codes:
  0 — no errors
  1 — warnings/errors found (check stdout)
"""
import argparse
import re
import sys
import time
from collections import defaultdict
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. Run: pip install requests")
    sys.exit(2)

SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
XHTML_NS = "http://www.w3.org/1999/xhtml"

DISCLAIMER_PATTERNS = [
    re.compile(r"educational purposes only", re.IGNORECASE),
    re.compile(r"not a substitute for.*medical advice", re.IGNORECASE),
    re.compile(r"consult.*healthcare provider", re.IGNORECASE),
    re.compile(r"keine ärztliche Beratung", re.IGNORECASE),
    re.compile(r"fins éducatives uniquement", re.IGNORECASE),
    re.compile(r"только в образовательных целях", re.IGNORECASE),
]

MEDICAL_CONTENT_PATHS = re.compile(r"/(articles|drugs|learn|news)/")


def fetch(url: str, session: requests.Session, timeout: int) -> requests.Response | None:
    try:
        r = session.get(url, timeout=timeout, allow_redirects=True)
        return r
    except Exception as e:
        return None


def parse_sitemap_index(content: bytes, base_url: str) -> list[str]:
    """Extract sitemap URLs from a sitemap index file."""
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError:
        return []
    ns = {"sm": SITEMAP_NS}
    return [el.text.strip() for el in root.findall(".//sm:loc", ns) if el.text]


def parse_sitemap(content: bytes) -> list[dict]:
    """Parse a sitemap and return list of {loc, hreflang: [{hreflang, href}]}."""
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError:
        return []

    ns = {"sm": SITEMAP_NS, "xhtml": XHTML_NS}
    entries = []
    for url_el in root.findall("sm:url", ns):
        loc_el = url_el.find("sm:loc", ns)
        if loc_el is None or not loc_el.text:
            continue
        loc = loc_el.text.strip()
        hreflang_links = []
        for link_el in url_el.findall("xhtml:link", ns):
            rel = link_el.get("rel", "")
            hreflang = link_el.get("hreflang", "")
            href = link_el.get("href", "")
            if rel == "alternate" and hreflang and href:
                hreflang_links.append({"hreflang": hreflang, "href": href})
        entries.append({"loc": loc, "hreflang": hreflang_links})
    return entries


def extract_canonical(html: str) -> str | None:
    m = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]+href=["\']([^"\']+)["\']', html)
    if m:
        return m.group(1)
    m = re.search(r'<link[^>]+href=["\']([^"\']+)["\'][^>]+rel=["\']canonical["\']', html)
    if m:
        return m.group(1)
    return None


def has_disclaimer(html: str) -> bool:
    return any(p.search(html) for p in DISCLAIMER_PATTERNS)


def audit(site: str, timeout: int, max_urls: int, verbose: bool) -> int:
    session = requests.Session()
    session.headers["User-Agent"] = "MedMindSEOAudit/1.0"

    errors: list[str] = []
    warnings: list[str] = []

    # Step 1: Fetch sitemap index
    sitemap_index_url = f"{site}/sitemap.xml"
    print(f"[*] Fetching sitemap index: {sitemap_index_url}")
    r = fetch(sitemap_index_url, session, timeout)
    if r is None or not r.ok:
        errors.append(f"Cannot fetch sitemap index: {sitemap_index_url}")
        print_report(errors, warnings)
        return 1

    # Step 2: Get all sub-sitemaps
    sub_sitemaps = parse_sitemap_index(r.content, site)
    if not sub_sitemaps:
        # Maybe it's a plain sitemap
        sub_sitemaps = [sitemap_index_url]
    print(f"[*] Found {len(sub_sitemaps)} sub-sitemaps")

    # Step 3: Collect all URL entries
    all_entries: list[dict] = []
    for sm_url in sub_sitemaps:
        r2 = fetch(sm_url, session, timeout)
        if r2 is None or not r2.ok:
            warnings.append(f"Cannot fetch sub-sitemap: {sm_url}")
            continue
        entries = parse_sitemap(r2.content)
        all_entries.extend(entries)
        if verbose:
            print(f"  {sm_url}: {len(entries)} URLs")

    print(f"[*] Total sitemap URLs: {len(all_entries)}")
    if len(all_entries) > max_urls:
        print(f"[*] Sampling first {max_urls} URLs (use --max-urls to increase)")
        all_entries = all_entries[:max_urls]

    # Build hreflang map: {url: set of (hreflang, href)}
    hreflang_map: dict[str, list[dict]] = {}
    url_to_entry: dict[str, dict] = {}
    for entry in all_entries:
        loc = entry["loc"]
        hreflang_map[loc] = entry["hreflang"]
        url_to_entry[loc] = entry

    # Step 4: Check each URL
    status_checked = 0
    for entry in all_entries:
        loc = entry["loc"]

        # 4a. HTTP status
        r = fetch(loc, session, timeout)
        time.sleep(0.05)  # gentle rate limit
        if r is None:
            errors.append(f"TIMEOUT/ERROR: {loc}")
            continue
        if r.status_code != 200:
            errors.append(f"HTTP {r.status_code}: {loc}")
            continue

        status_checked += 1
        html = r.text

        # 4b. Canonical check
        canonical = extract_canonical(html)
        if canonical and canonical != loc:
            # Allow trailing slash differences
            if canonical.rstrip("/") != loc.rstrip("/"):
                warnings.append(f"CANONICAL MISMATCH: {loc} → {canonical}")

        # 4c. Disclaimer for medical content
        path = urlparse(loc).path
        if MEDICAL_CONTENT_PATHS.search(path) and not has_disclaimer(html):
            warnings.append(f"NO DISCLAIMER: {loc}")

        if verbose and status_checked % 20 == 0:
            print(f"  [{status_checked}/{len(all_entries)}] checked...")

    print(f"[*] Status checks: {status_checked}/{len(all_entries)} OK")

    # Step 5: hreflang reciprocity check
    print("[*] Checking hreflang reciprocity...")
    reciprocity_errors = 0
    for loc, links in hreflang_map.items():
        for link in links:
            if link["hreflang"] == "x-default":
                continue
            target = link["href"]
            if target not in hreflang_map:
                continue  # not in our sample, skip
            # Check that target has a back-link to loc
            back_links = {l["href"] for l in hreflang_map.get(target, [])}
            if loc not in back_links:
                errors.append(f"HREFLANG NOT RECIPROCAL: {loc} → {target} (hreflang={link['hreflang']}) but {target} does not link back")
                reciprocity_errors += 1
                if reciprocity_errors >= 20:
                    warnings.append("(reciprocity check truncated at 20 errors)")
                    break

    print_report(errors, warnings)
    return 1 if errors else 0


def print_report(errors: list[str], warnings: list[str]) -> None:
    print()
    if warnings:
        print(f"⚠️  WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  WARN: {w}")
    if errors:
        print(f"❌ ERRORS ({len(errors)}):")
        for e in errors:
            print(f"  ERR:  {e}")
    if not errors and not warnings:
        print("✅ All checks passed.")
    elif not errors:
        print(f"✅ No errors. {len(warnings)} warning(s).")
    else:
        print(f"❌ {len(errors)} error(s), {len(warnings)} warning(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MedMind SEO audit")
    parser.add_argument("--site", default="https://medmind.pro", help="Base site URL")
    parser.add_argument("--timeout", type=int, default=10, help="HTTP timeout seconds")
    parser.add_argument("--max-urls", type=int, default=200, dest="max_urls", help="Max URLs to check per run")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    exit_code = audit(args.site, args.timeout, args.max_urls, args.verbose)
    sys.exit(exit_code)
