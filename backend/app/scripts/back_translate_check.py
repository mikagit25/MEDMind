"""V4 Phase 2 — Back-translation spot-check script.

Samples 5% of article translations, back-translates to English via Google Translate,
and uses Haiku to assess semantic similarity with the original.

Usage:
    cd backend
    python -m app.scripts.back_translate_check [--lang ru] [--sample 5] [--dry-run]

Flags:
    --lang      ISO locale to check (default: all configured locales)
    --sample    Percentage of translations to sample (default: 5)
    --dry-run   Print results without updating DB
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
import urllib.parse
import urllib.request
from datetime import datetime

from sqlalchemy import select, update

from app.core.database import get_db_session
from app.models.models import Article, ArticleTranslation
from app.services.content_verifier import _get_client, _article_to_text

logger = logging.getLogger(__name__)

LOCALES = ["ru", "ar", "tr", "de", "fr", "es"]

SIMILARITY_THRESHOLD = 0.70  # Haiku score below this → flag as problematic


def _gtranslate_back(text: str, src_lang: str) -> str:
    """Translate text from src_lang back to English."""
    if not text or not text.strip():
        return text
    try:
        url = (
            "https://translate.googleapis.com/translate_a/single"
            "?client=gtx&sl=" + src_lang
            + "&tl=en&dt=t&q=" + urllib.parse.quote(text[:3000])
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read())
        return "".join(part[0] for part in data[0] if part[0])
    except Exception as exc:
        logger.warning("back-translate failed for lang=%s: %s", src_lang, exc)
        return ""


async def _semantic_similarity(original: str, back_translated: str) -> float:
    """Ask Haiku to score semantic similarity 0.0–1.0."""
    client = _get_client()
    prompt = (
        "Score the semantic similarity between these two medical texts on a scale of 0.0 to 1.0, "
        "where 1.0 means identical meaning and 0.0 means completely different meaning.\n\n"
        f"ORIGINAL:\n{original[:1500]}\n\n"
        f"BACK-TRANSLATION:\n{back_translated[:1500]}\n\n"
        'Return ONLY a JSON object: {"score": <float>, "note": "<one sentence>"}'
    )
    try:
        resp = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}],
        )
        data = json.loads(resp.content[0].text.strip())
        return float(data.get("score", 0.5)), data.get("note", "")
    except Exception as exc:
        logger.warning("similarity scoring failed: %s", exc)
        return 0.5, ""


async def run_check(lang: str | None, sample_pct: int, dry_run: bool) -> None:
    langs_to_check = [lang] if lang else LOCALES
    results = []

    async with get_db_session() as db:
        for locale in langs_to_check:
            rows = (await db.execute(
                select(ArticleTranslation, Article.title)
                .join(Article, Article.id == ArticleTranslation.article_id)
                .where(
                    ArticleTranslation.locale == locale,
                    ArticleTranslation.status == "done",
                )
                .order_by(ArticleTranslation.article_id)
            )).all()

            if not rows:
                logger.info("No translations found for locale=%s", locale)
                continue

            sample_size = max(1, int(len(rows) * sample_pct / 100))
            sample = random.sample(rows, min(sample_size, len(rows)))
            logger.info("Checking %d/%d translations for locale=%s", len(sample), len(rows), locale)

            for tr, article_title in sample:
                # Get original English body
                orig_article = (await db.execute(
                    select(Article).where(Article.id == tr.article_id)
                )).scalar_one_or_none()
                if not orig_article:
                    continue

                original_text = _article_to_text(orig_article.body or [])
                if not original_text.strip():
                    continue

                # Pick one paragraph for back-translation (keep tokens manageable)
                paragraphs = [p for p in original_text.split(". ") if len(p) > 80]
                if not paragraphs:
                    continue
                para = random.choice(paragraphs[:10])

                # Find the same paragraph in translation
                tr_text = _article_to_text(tr.body or [])
                # Just use the full translated excerpt for back-translation
                back = _gtranslate_back(tr_text[:1500], locale)
                if not back:
                    continue

                score, note = await _semantic_similarity(original_text[:1500], back)
                flagged = score < SIMILARITY_THRESHOLD

                result = {
                    "locale": locale,
                    "article_id": str(tr.article_id),
                    "article_title": article_title,
                    "similarity_score": score,
                    "note": note,
                    "flagged": flagged,
                    "checked_at": datetime.utcnow().isoformat(),
                }
                results.append(result)
                logger.info(
                    "[%s] %s — score=%.2f%s",
                    locale,
                    article_title[:60],
                    score,
                    " ⚠ FLAGGED" if flagged else "",
                )

                if flagged and not dry_run:
                    await db.execute(
                        update(ArticleTranslation)
                        .where(
                            ArticleTranslation.article_id == tr.article_id,
                            ArticleTranslation.locale == locale,
                        )
                        .values(translation_verification_status="failed")
                    )

        if not dry_run:
            await db.commit()

    # Print summary
    flagged = [r for r in results if r["flagged"]]
    print(f"\n=== Back-Translation Check Summary ===")
    print(f"Checked: {len(results)}  |  Flagged: {len(flagged)}")
    if flagged:
        print("\nFlagged translations:")
        for r in flagged:
            print(f"  [{r['locale']}] {r['article_title'][:60]} — score={r['similarity_score']:.2f} — {r['note']}")
    print(f"\nDry-run: {dry_run}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Back-translation spot-check for V4 Phase 2")
    parser.add_argument("--lang", help="Locale to check (default: all)", default=None)
    parser.add_argument("--sample", type=int, default=5, help="Percentage to sample (default: 5)")
    parser.add_argument("--dry-run", action="store_true", help="Don't update DB")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    asyncio.run(run_check(args.lang, args.sample, args.dry_run))


if __name__ == "__main__":
    main()
