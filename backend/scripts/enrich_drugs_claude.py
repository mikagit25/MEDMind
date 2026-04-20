"""
Claude Drug Enrichment Script
==============================
Re-generates structured drug data for records with missing/poor fields using Claude.

Targets drugs where:
  - adverse_effects = {} or NULL  (21 drugs)
  - mechanism IS NULL or < 50 chars (24 drugs)
  - dosing = {} or NULL (1 drug)

Usage (from backend/):
    python -m scripts.enrich_drugs_claude --dry-run      # print output, no DB write
    python -m scripts.enrich_drugs_claude --limit 5      # first N drugs
    python -m scripts.enrich_drugs_claude                # all that need enrichment
    python -m scripts.enrich_drugs_claude --field mech   # only fix mechanism
"""

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from pathlib import Path
from uuid import UUID

import asyncpg
import anthropic

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

CLAUDE_MODEL = "claude-haiku-4-5-20251001"  # cheap + fast for structured data

ENRICH_PROMPT = """\
You are a clinical pharmacology expert. Return ONLY valid JSON — no prose, no markdown fences.

Drug: {name}
Generic name: {generic_name}
Drug class: {drug_class}

Generate the following JSON object with ALL fields populated:
{{
  "mechanism": "<2-3 sentence mechanism of action>",
  "adverse_effects": {{
    "common": ["effect1", "effect2", "..."],
    "serious": ["effect1", "effect2", "..."],
    "rare": ["effect1", "effect2"]
  }},
  "dosing": {{
    "Oral (adult, typical)": "<dose and frequency>",
    "IV (if applicable)": "<dose or omit key if not applicable>"
  }},
  "monitoring": ["parameter1", "parameter2"],
  "interactions": ["key interaction 1 (brief)", "key interaction 2 (brief)"]
}}

Rules:
- mechanism: plain prose, no bullet points, 2-3 sentences max
- adverse_effects: each array should have 3-8 items, each a short phrase (not a sentence)
- dosing: only include routes that are clinically common for this drug
- monitoring: 2-5 items, short phrases
- interactions: 3-6 most important interactions, each ≤ 15 words
- All strings must be plain text, no markdown
"""


def extract_json(text: str) -> dict:
    """Extract JSON from Claude response, handling code fences."""
    text = text.strip()
    # Remove markdown fences
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.M)
    text = re.sub(r"\s*```$", "", text, flags=re.M)
    text = text.strip()
    return json.loads(text)


async def enrich_drug(
    client: anthropic.Anthropic,
    drug: dict,
    fix_fields: set[str],
) -> dict | None:
    """Call Claude to enrich a drug record. Returns dict with updated fields."""
    prompt = ENRICH_PROMPT.format(
        name=drug["name"],
        generic_name=drug["generic_name"] or drug["name"],
        drug_class=drug["drug_class"] or "Unknown",
    )

    try:
        msg = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text
        data = extract_json(raw)
    except (json.JSONDecodeError, Exception) as e:
        log.error("  → Claude parse error: %s", e)
        return None

    # Only return fields that need fixing
    result = {}
    if "mechanism" in fix_fields and data.get("mechanism"):
        result["mechanism"] = data["mechanism"]
    if "adverse_effects" in fix_fields and data.get("adverse_effects"):
        result["adverse_effects"] = data["adverse_effects"]
    if "dosing" in fix_fields and data.get("dosing"):
        result["dosing"] = data["dosing"]
    if data.get("monitoring"):
        result["monitoring"] = data["monitoring"]
    if data.get("interactions"):
        result["interactions"] = data["interactions"]

    return result


async def run(args: argparse.Namespace) -> None:
    db_url = os.environ["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("ANTHROPIC_API_KEY not set")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    conn: asyncpg.Connection | None = None
    if not args.dry_run:
        conn = await asyncpg.connect(db_url)

    # Build field filter
    fix_fields: set[str] = set()
    if args.field in (None, "all", "mech"):
        fix_fields.add("mechanism")
    if args.field in (None, "all", "ae"):
        fix_fields.add("adverse_effects")
    if args.field in (None, "all", "dose"):
        fix_fields.add("dosing")

    # Query drugs that need enrichment
    conditions = []
    if "mechanism" in fix_fields:
        conditions.append("(mechanism IS NULL OR LENGTH(mechanism) < 50)")
    if "adverse_effects" in fix_fields:
        conditions.append("(adverse_effects IS NULL OR adverse_effects::text = '{}')")
    if "dosing" in fix_fields:
        conditions.append("(dosing IS NULL OR dosing::text = '{}')")

    where = " OR ".join(conditions) if conditions else "TRUE"
    limit_clause = f"LIMIT {args.limit}" if args.limit else ""

    if conn:
        rows = await conn.fetch(
            f"SELECT id, name, generic_name, drug_class, mechanism, adverse_effects, dosing "
            f"FROM drugs WHERE {where} ORDER BY name {limit_clause}"
        )
    else:
        # Dry run — fetch from DB anyway to show which drugs would be enriched
        tmp_conn = await asyncpg.connect(db_url)
        rows = await tmp_conn.fetch(
            f"SELECT id, name, generic_name, drug_class, mechanism, adverse_effects, dosing "
            f"FROM drugs WHERE {where} ORDER BY name {limit_clause}"
        )
        await tmp_conn.close()

    log.info("Found %d drugs needing enrichment (fields: %s)", len(rows), fix_fields)

    stats = {"updated": 0, "skipped": 0, "error": 0}

    for i, row in enumerate(rows, 1):
        drug = dict(row)
        drug_id = drug["id"]
        log.info("[%d/%d] %s", i, len(rows), drug["name"])

        # Determine what actually needs fixing for this drug
        needs: set[str] = set()
        if "mechanism" in fix_fields and (not drug["mechanism"] or len(drug["mechanism"]) < 50):
            needs.add("mechanism")
        if "adverse_effects" in fix_fields:
            ae = drug["adverse_effects"]
            if not ae or ae == {} or ae == "{}":
                needs.add("adverse_effects")
        if "dosing" in fix_fields:
            d = drug["dosing"]
            if not d or d == {} or d == "{}":
                needs.add("dosing")

        if not needs:
            log.info("  → skip (data already OK)")
            stats["skipped"] += 1
            continue

        log.info("  → enriching fields: %s", needs)
        enriched = await enrich_drug(client, drug, needs)

        if not enriched:
            stats["error"] += 1
            continue

        if args.dry_run:
            print(json.dumps({"drug": drug["name"], "enriched": enriched}, indent=2, ensure_ascii=False))
            stats["updated"] += 1
        else:
            # Build UPDATE statement dynamically
            set_parts = []
            values = []
            idx = 1
            if "mechanism" in enriched:
                set_parts.append(f"mechanism = ${idx}")
                values.append(enriched["mechanism"])
                idx += 1
            if "adverse_effects" in enriched:
                set_parts.append(f"adverse_effects = ${idx}::jsonb")
                values.append(json.dumps(enriched["adverse_effects"]))
                idx += 1
            if "dosing" in enriched:
                set_parts.append(f"dosing = ${idx}::jsonb")
                values.append(json.dumps(enriched["dosing"]))
                idx += 1
            if "monitoring" in enriched:
                set_parts.append(f"monitoring = ${idx}")
                values.append(enriched["monitoring"])
                idx += 1
            if "interactions" in enriched:
                set_parts.append(f"interactions = ${idx}")
                values.append(enriched["interactions"])
                idx += 1

            set_parts.append(f"updated_at = NOW()")
            values.append(str(drug_id))

            sql = f"UPDATE drugs SET {', '.join(set_parts)} WHERE id = ${idx}"
            try:
                await conn.execute(sql, *values)
                log.info("  → updated [%s]", drug["name"])
                stats["updated"] += 1
            except Exception as e:
                log.error("  → DB error: %s", e)
                stats["error"] += 1

        # Small delay to respect API rate limits
        await asyncio.sleep(0.5)

    if conn:
        await conn.close()

    log.info(
        "Done. updated=%d  skipped=%d  errors=%d",
        stats["updated"], stats["skipped"], stats["error"],
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich drug records using Claude API")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print enriched data without writing to DB")
    parser.add_argument("--limit", type=int, metavar="N",
                        help="Process at most N drugs")
    parser.add_argument("--field", choices=["all", "mech", "ae", "dose"],
                        help="Which field(s) to fix: mech=mechanism, ae=adverse_effects, dose=dosing")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
