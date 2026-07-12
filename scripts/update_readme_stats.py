#!/usr/bin/env python3
"""Update README.md stats between <!-- stats:start --> and <!-- stats:end --> markers.

Usage:
    python scripts/update_readme_stats.py                         # production
    STATS_URL=http://localhost:8000/api/v1/public/stats python scripts/update_readme_stats.py
"""
import re
import sys
import json
import urllib.request
from pathlib import Path

STATS_URL = __import__("os").environ.get(
    "STATS_URL", "https://medmind.pro/api/v1/public/stats"
)
README = Path(__file__).parent.parent / "README.md"


def fetch_stats() -> dict:
    with urllib.request.urlopen(STATS_URL, timeout=10) as r:
        return json.loads(r.read())


def update_readme(stats: dict) -> bool:
    drugs      = stats.get("drugs", 0)
    modules    = stats.get("modules", 0)
    articles   = stats.get("articles", 0)
    flashcards = stats.get("flashcards", 0)
    langs      = stats.get("languages", 7)

    new_line = (
        f"AI-powered learning with **{drugs} drugs**, **{modules} clinical modules**, "
        f"**{articles:,} articles**, **{flashcards:,} flashcards** in **{langs} languages** "
        f"— and a patient-friendly mode that explains medicine in plain language."
    )

    text = README.read_text()
    pattern = r"(<!-- stats:start -->).*?(<!-- stats:end -->)"
    replacement = f"\\1\n{new_line}\n\\2"
    new_text, count = re.subn(pattern, replacement, text, flags=re.DOTALL)

    if count == 0:
        print("ERROR: markers <!-- stats:start/end --> not found in README.md", file=sys.stderr)
        return False

    if new_text == text:
        print("README stats already up to date.")
        return True

    README.write_text(new_text)
    print(f"README updated: {drugs} drugs, {modules} modules, {articles:,} articles, {flashcards:,} flashcards, {langs} languages")
    return True


if __name__ == "__main__":
    try:
        stats = fetch_stats()
    except Exception as e:
        print(f"ERROR fetching stats: {e}", file=sys.stderr)
        sys.exit(1)

    success = update_readme(stats)
    sys.exit(0 if success else 1)
