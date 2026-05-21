"""
Translate drug data to 6 languages using Google Translate (free, no key).
Stores translations in drugs.translations JSONB column.

Each drug gets: drug_class, mechanism, indications, contraindications,
                adverse_effects keys, black_box_warning translated.

Usage:
    python3 translate_drugs.py                    # all drugs without translations
    python3 translate_drugs.py --force            # re-translate all
    python3 translate_drugs.py --limit 50         # first N drugs
    python3 translate_drugs.py --lang ru          # only Russian

Run in background:
    nohup python3 translate_drugs.py > /tmp/drug_translate.log 2>&1 &
"""
import argparse
import json
import logging
import sys
import os
import time

import psycopg2

sys.path.insert(0, os.path.dirname(__file__))
from generate_articles_ollama import DB_URL, gtranslate

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

LOCALES = ["ru", "ar", "de", "fr", "es", "tr"]


def translate_list(items: list, locale: str) -> list:
    if not items:
        return []
    result = []
    for item in items:
        if isinstance(item, str) and item.strip():
            tr = gtranslate(item, locale)
            result.append(tr if tr else item)
            time.sleep(0.2)
        else:
            result.append(item)
    return result


def translate_dict_keys(d: dict, locale: str) -> dict:
    """Translate only the keys of a dict (e.g. adverse_effects categories)."""
    if not d:
        return {}
    result = {}
    for k, v in d.items():
        tr_key = gtranslate(k, locale) if k else k
        time.sleep(0.15)
        if isinstance(v, list):
            tr_val = translate_list(v, locale)
        else:
            tr_val = v
        result[tr_key or k] = tr_val
    return result


def translate_drug(drug_id: str, name: str, drug_class: str | None,
                   mechanism: str | None, indications: list | None,
                   contraindications: list | None, adverse_effects: dict | None,
                   black_box_warning: str | None,
                   locales: list[str]) -> dict:
    """Returns translations dict: {locale: {field: value}}."""
    translations = {}
    for locale in locales:
        log.info("  [%s] %s…", locale, name[:40])
        t: dict = {}

        if drug_class:
            t["drug_class"] = gtranslate(drug_class, locale) or drug_class
            time.sleep(0.2)

        if mechanism:
            t["mechanism"] = gtranslate(mechanism, locale) or mechanism
            time.sleep(0.3)

        if indications:
            t["indications"] = translate_list(indications, locale)

        if contraindications:
            t["contraindications"] = translate_list(contraindications, locale)

        if adverse_effects:
            t["adverse_effects"] = translate_dict_keys(adverse_effects, locale)

        if black_box_warning:
            t["black_box_warning"] = gtranslate(black_box_warning, locale) or black_box_warning
            time.sleep(0.3)

        translations[locale] = t
        time.sleep(0.5)

    return translations


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force",  action="store_true", help="Re-translate all drugs")
    parser.add_argument("--limit",  type=int, default=0)
    parser.add_argument("--lang",   type=str, default=None, help="Single locale (e.g. ru)")
    args = parser.parse_args()

    locales = [args.lang] if args.lang else LOCALES

    conn = psycopg2.connect(DB_URL)
    with conn.cursor() as cur:
        if args.force:
            cur.execute("""
                SELECT id, name, drug_class, mechanism, indications,
                       contraindications, adverse_effects, black_box_warning
                FROM drugs ORDER BY name
            """)
        else:
            cur.execute("""
                SELECT id, name, drug_class, mechanism, indications,
                       contraindications, adverse_effects, black_box_warning
                FROM drugs
                WHERE translations IS NULL OR translations = '{}'::jsonb
                ORDER BY name
            """)
        rows = cur.fetchall()

    if args.limit:
        rows = rows[:args.limit]

    log.info("Translating %d drugs into %s…", len(rows), locales)
    done = errors = 0

    for row in rows:
        drug_id, name, drug_class, mechanism, indications, \
            contraindications, adverse_effects, black_box_warning = row

        log.info("[%d/%d] %s", done + 1, len(rows), name)
        try:
            # Load existing translations (if partial, only add missing locales)
            with conn.cursor() as cur:
                cur.execute("SELECT translations FROM drugs WHERE id=%s", (drug_id,))
                existing_json = cur.fetchone()[0] or {}
            existing = existing_json if isinstance(existing_json, dict) else {}

            missing_locales = [l for l in locales if l not in existing]
            if not missing_locales and not args.force:
                log.info("  Already translated, skipping")
                done += 1
                continue

            new_translations = translate_drug(
                drug_id, name, drug_class, mechanism, indications,
                contraindications, adverse_effects, black_box_warning,
                missing_locales if not args.force else locales
            )
            merged = {**existing, **new_translations}

            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE drugs SET translations=%s::jsonb WHERE id=%s",
                    (json.dumps(merged, ensure_ascii=False), drug_id)
                )
            conn.commit()
            log.info("  ✓ Translated into %s", list(new_translations.keys()))
            done += 1

        except Exception as e:
            conn.rollback()
            log.error("  ✗ Failed: %s", e)
            errors += 1

        time.sleep(0.5)

    conn.close()
    log.info("Done. Translated: %d | Errors: %d", done, errors)


if __name__ == "__main__":
    main()
