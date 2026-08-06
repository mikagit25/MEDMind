"""L2.2 — Audit Gulf exam questions for jurisdiction-sensitive content.

Classifies MCQ questions tagged to Gulf exams using:
1. Rule-based detector (regex + keyword sets, fast, no API calls)
2. Sets jurisdiction_sensitive=True for matches
3. Sets origin='nclex_mapped' for questions with NCLEX origin and Gulf slugs
4. Generates a report of what was flagged and why

Quarantine effect: exam.py query layer already filters
jurisdiction_sensitive=True AND jurisdiction_verified_for is empty
from Gulf sessions — quarantine is in the query, not this script.

Run:
    docker exec medmind_backend python3 -m app.scripts.audit_jurisdiction_sensitivity
    docker exec medmind_backend python3 -m app.scripts.audit_jurisdiction_sensitivity --dry-run
    docker exec medmind_backend python3 -m app.scripts.audit_jurisdiction_sensitivity --report-only
"""
from __future__ import annotations

import asyncio
import argparse
import json
import logging
import re
from datetime import datetime
from typing import Optional

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.models import MCQQuestion

log = logging.getLogger(__name__)

# ── Jurisdiction-sensitive signal patterns ────────────────────────────────────

# US-specific legal/regulatory references that don't apply in the Gulf
US_REGULATORY_PATTERNS = re.compile(
    r"\b("
    r"HIPAA|HITECH|Joint Commission|OSHA|ADA|EMTALA|OBRA|"
    r"Department of Health and Human Services|CMS|Medicare|Medicaid|"
    r"Board of Registered Nursing|California Board|State Board of Nursing"
    r")\b",
    re.IGNORECASE,
)

# US emergency number
US_911_PATTERN = re.compile(r"\b911\b")

# US-only agencies/bodies
US_AGENCY_PATTERNS = re.compile(
    r"\b("
    r"CDC|FDA|DEA|JCAHO|TJC|ACOG|AHA guidelines|ANA Code|"
    r"Nurse Practice Act"
    r")\b",
    re.IGNORECASE,
)

# Non-SI units (Gulf uses SI exclusively)
NON_SI_UNIT_PATTERNS = re.compile(
    r"\b("
    r"mg/dL|mg/dl|lb|lbs|pound|pounds|Fahrenheit|°F|"
    r"fl oz|fluid ounce|ounce|inch|inches|feet|foot|mile|"
    r"mmHg(?!\s*[=<>])|gr\b"
    r")\b",
    re.IGNORECASE,
)

# Scope of practice signals (what a nurse may/may NOT do autonomously)
SCOPE_PATTERNS = re.compile(
    r"\b("
    r"nurse can independently|nurse may independently|"
    r"within the nurse.s scope|outside the nurse.s scope|"
    r"scope of practice|delegat(e|ion|ing)|"
    r"nurse practitioner prescrib|NP prescrib|"
    r"autonomous.*prescrib|prescrib.*independ"
    r")\b",
    re.IGNORECASE,
)

# Consent / decision-making signals
CONSENT_PATTERNS = re.compile(
    r"\b("
    r"informed consent|who must consent|legal guardian|power of attorney|"
    r"advance directive|living will|POLST|MOLST|"
    r"patient refuses|patient declines|right to refuse|"
    r"Jehovah.s Witness|minor consent|emancipated minor|"
    r"surrogate decision"
    r")\b",
    re.IGNORECASE,
)

# End-of-life signals
EOL_PATTERNS = re.compile(
    r"\b("
    r"do not resuscitate|DNR|DNAR|do not attempt|"
    r"withdrawal of.*treatment|withhold.*treatment|"
    r"comfort measures only|CMO|"
    r"euthanasia|physician.*assisted|MAID|"
    r"palliative sedation|terminal sedation"
    r")\b",
    re.IGNORECASE,
)

# Documentation / mandatory reporting signals
DOCUMENTATION_PATTERNS = re.compile(
    r"\b("
    r"mandatory report|mandated report|reportable disease|"
    r"incident report|sentinel event|"
    r"HIPAA violation|breach notification|"
    r"suspected abuse.*report|report.*suspected abuse"
    r")\b",
    re.IGNORECASE,
)

# Cultural / religious care signals (context-dependent in Gulf)
CULTURAL_PATTERNS = re.compile(
    r"\b("
    r"Ramadan|halal|haram|pork|gelatin|alcohol.*medication|"
    r"prayer time|hijab|gender.*separate|same.gender.*care|"
    r"male.*nurse.*female|female.*nurse.*male|chaperone"
    r")\b",
    re.IGNORECASE,
)

# US trade drug names (Gulf uses generic names; trade names may differ or not be registered)
# This is a small representative set — a full pharmacopoeia list would be maintained separately
US_TRADE_DRUG_PATTERNS = re.compile(
    r"\b("
    r"Tylenol|Advil|Motrin|Benadryl|Zofran|Narcan|EpiPen|"
    r"Prilosec|Nexium|Lipitor|Zocor|Plavix|Coumadin|Warfarin brand"
    r")\b",
    re.IGNORECASE,
)

ALL_PATTERNS: dict[str, re.Pattern] = {
    "us_regulatory": US_REGULATORY_PATTERNS,
    "us_911": US_911_PATTERN,
    "us_agency": US_AGENCY_PATTERNS,
    "non_si_units": NON_SI_UNIT_PATTERNS,
    "scope_of_practice": SCOPE_PATTERNS,
    "consent": CONSENT_PATTERNS,
    "end_of_life": EOL_PATTERNS,
    "documentation_reporting": DOCUMENTATION_PATTERNS,
    "cultural_religious": CULTURAL_PATTERNS,
    "us_trade_drug": US_TRADE_DRUG_PATTERNS,
}

GULF_SLUGS = {"snle", "dha", "haad", "doh", "qchp", "omsb", "nhra", "moh_kw"}


def _question_text(q: MCQQuestion) -> str:
    """Collect all text fields for pattern matching."""
    parts = [q.question or ""]
    if isinstance(q.options, dict):
        parts.extend(str(v) for v in q.options.values())
    elif isinstance(q.options, list):
        parts.extend(str(o) for o in q.options)
    if q.explanation:
        parts.append(q.explanation)
    if q.key_takeaway:
        parts.append(q.key_takeaway)
    return " ".join(parts)


def _classify(text: str) -> tuple[bool, list[str]]:
    """Return (is_sensitive, [triggered_domains])."""
    triggered = []
    for domain, pattern in ALL_PATTERNS.items():
        if pattern.search(text):
            triggered.append(domain)
    return bool(triggered), triggered


def _is_gulf_question(q: MCQQuestion) -> bool:
    slugs = set(q.exam_slugs or [])
    return bool(slugs & GULF_SLUGS)


async def run(
    dry_run: bool = False,
    report_only: bool = False,
    batch_size: int = 200,
) -> dict:
    async with AsyncSessionLocal() as db:
        # Fetch all MCQ questions that appear in Gulf exams
        result = await db.execute(
            select(MCQQuestion).where(MCQQuestion.status == "active")
        )
        all_questions = result.scalars().all()

    gulf_questions = [q for q in all_questions if _is_gulf_question(q)]
    log.info("Total active questions: %d | Gulf-tagged: %d", len(all_questions), len(gulf_questions))

    newly_sensitive = 0
    newly_cleared = 0
    origin_tagged = 0
    domain_counts: dict[str, int] = {}
    flagged_sample: list[dict] = []

    async with AsyncSessionLocal() as db:
        for q in gulf_questions:
            text = _question_text(q)
            is_sensitive, triggered = _classify(text)

            changed = False

            # Tag origin for Gulf-tagged questions coming from NCLEX mapping
            if q.origin is None and q.nclex_client_needs is not None:
                if not report_only and not dry_run:
                    q_obj = await db.get(MCQQuestion, q.id)
                    if q_obj:
                        q_obj.origin = "nclex_mapped"
                        changed = True
                origin_tagged += 1

            if is_sensitive:
                newly_sensitive += 1
                for d in triggered:
                    domain_counts[d] = domain_counts.get(d, 0) + 1

                if len(flagged_sample) < 50:
                    flagged_sample.append({
                        "id": str(q.id),
                        "question_preview": (q.question or "")[:120],
                        "triggered_domains": triggered,
                    })

                if not report_only and not dry_run:
                    q_obj = await db.get(MCQQuestion, q.id)
                    if q_obj and not q_obj.jurisdiction_sensitive:
                        q_obj.jurisdiction_sensitive = True
                        q_obj.jurisdiction_audit_at = datetime.utcnow()
                        q_obj.jurisdiction_audit_notes = json.dumps(triggered)
                        changed = True
            else:
                # Clear stale flags (question was edited to remove sensitive content)
                if q.jurisdiction_sensitive:
                    newly_cleared += 1
                    if not report_only and not dry_run:
                        q_obj = await db.get(MCQQuestion, q.id)
                        if q_obj:
                            q_obj.jurisdiction_sensitive = False
                            q_obj.jurisdiction_audit_at = datetime.utcnow()
                            q_obj.jurisdiction_audit_notes = "cleared by re-audit"
                            changed = True

        if not report_only and not dry_run:
            await db.commit()

    report = {
        "gulf_questions_audited": len(gulf_questions),
        "jurisdiction_sensitive_flagged": newly_sensitive,
        "quarantined": newly_sensitive,  # all sensitive with empty jurisdiction_verified_for
        "cleared": newly_cleared,
        "origin_tagged": origin_tagged,
        "domain_breakdown": domain_counts,
        "flagged_sample": flagged_sample,
        "dry_run": dry_run,
        "report_only": report_only,
        "audited_at": datetime.utcnow().isoformat(),
    }
    return report


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Classify but don't write")
    parser.add_argument("--report-only", action="store_true", help="Only read, don't write anything")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    report = await run(dry_run=args.dry_run, report_only=args.report_only)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
