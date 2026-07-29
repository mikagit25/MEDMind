"""Bank-Scale B1 — Seed verified content sources into content_sources table.

License verification date: 2026-07-29. Each entry was checked manually.
Run:  python -m app.scripts.seed_content_sources
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.database import AsyncSessionLocal
from app.models.models import ContentSource

logger = logging.getLogger(__name__)

VERIFIED_AT = "2026-07-29"

# fmt: off
SOURCES: list[dict] = [
    # ── Public domain / CC BY (text_reuse_allowed=True) ──────────────────────
    {
        "slug": "medlineplus_topics",
        "title": "MedlinePlus — Health Topic Summaries",
        "publisher": "U.S. National Library of Medicine (NLM)",
        "url": "https://medlineplus.gov/",
        "license": "public domain (US gov)",
        "license_url": "https://medlineplus.gov/copyright.html",
        "text_reuse_allowed": True,
        "attribution_template": "Source: MedlinePlus, U.S. National Library of Medicine. {url}",
        "source_type": "gov_health",
        "verified_at": VERIFIED_AT,
        "notes": (
            "Health topic summary pages are US federal government work = public domain. "
            "A.D.A.M. Medical Encyclopedia and drug monographs on MedlinePlus are copyrighted "
            "by third parties — use medlineplus_adam slug for those (text_reuse_allowed=False)."
        ),
    },
    {
        "slug": "cdc",
        "title": "Centers for Disease Control and Prevention (CDC)",
        "publisher": "U.S. Department of Health and Human Services / CDC",
        "url": "https://www.cdc.gov/",
        "license": "public domain (US gov)",
        "license_url": "https://www.usa.gov/government-copyright",
        "text_reuse_allowed": True,
        "attribution_template": "Source: Centers for Disease Control and Prevention (CDC). {url}",
        "source_type": "gov_health",
        "verified_at": VERIFIED_AT,
        "notes": (
            "US federal government works are not copyrightable under 17 U.S.C. § 105. "
            "Do not imply CDC endorsement of MedMind or any specific product. "
            "Attribution required per CDC courtesy guidelines."
        ),
    },
    # ── NC / ND / Unclear → facts only (text_reuse_allowed=False) ────────────
    {
        "slug": "statpearls",
        "title": "StatPearls — Clinical Reference",
        "publisher": "StatPearls Publishing / NCBI Bookshelf",
        "url": "https://www.ncbi.nlm.nih.gov/books/NBK430685/",
        "license": "CC BY-NC-ND 4.0",
        "license_url": "https://creativecommons.org/licenses/by-nc-nd/4.0/",
        "text_reuse_allowed": False,
        "attribution_template": None,
        "source_type": "reference",
        "verified_at": VERIFIED_AT,
        "notes": (
            "CC BY-NC-ND 4.0: NC = no commercial use; ND = no derivatives. "
            "Use as factual basis only — do not reproduce or paraphrase text. "
            "Verified on chapter page: https://www.ncbi.nlm.nih.gov/books/NBK430685/"
        ),
    },
    {
        "slug": "who",
        "title": "World Health Organization — Publications",
        "publisher": "World Health Organization (WHO)",
        "url": "https://www.who.int/publications",
        "license": "CC BY-NC-SA 3.0 IGO",
        "license_url": "https://www.who.int/about/policies/publishing/copyright",
        "text_reuse_allowed": False,
        "attribution_template": None,
        "source_type": "guideline",
        "verified_at": VERIFIED_AT,
        "notes": (
            "CC BY-NC-SA 3.0 IGO: NC = no commercial use without explicit WHO permission. "
            "Formal permission request required for commercial reuse of text. "
            "Facts, statistics, and clinical guidance from WHO docs may be used as factual basis."
        ),
    },
    {
        "slug": "nice_guidelines",
        "title": "NICE Clinical Guidelines",
        "publisher": "National Institute for Health and Care Excellence (NICE)",
        "url": "https://www.nice.org.uk/guidance",
        "license": "unclear",
        "license_url": "https://www.nice.org.uk/about/who-we-are/policies-and-procedures/nice-website-terms-and-conditions",
        "text_reuse_allowed": False,
        "attribution_template": None,
        "source_type": "guideline",
        "verified_at": VERIFIED_AT,
        "notes": (
            "License page returned 403 during verification on 2026-07-29. "
            "NICE is a UK public body — likely Open Government Licence (OGL) but unconfirmed. "
            "Treat as unclear until manually verified. Facts-only until confirmed."
        ),
    },
    {
        "slug": "medlineplus_adam",
        "title": "MedlinePlus — A.D.A.M. Medical Encyclopedia",
        "publisher": "A.D.A.M., Inc. (via NLM/MedlinePlus)",
        "url": "https://medlineplus.gov/encyclopedia.html",
        "license": "copyrighted (A.D.A.M., Inc.)",
        "license_url": "https://medlineplus.gov/copyright.html",
        "text_reuse_allowed": False,
        "attribution_template": None,
        "source_type": "reference",
        "verified_at": VERIFIED_AT,
        "notes": (
            "A.D.A.M. Medical Encyclopedia articles and drug monographs on MedlinePlus "
            "are copyrighted by A.D.A.M., Inc. — not public domain. "
            "Facts-only; no text reproduction without licensing from A.D.A.M."
        ),
    },
    # ── Official exam blueprints (facts/structure only) ───────────────────────
    {
        "slug": "ncsbn_nclex_rn",
        "title": "NCLEX-RN Test Plan (Next Generation NCLEX)",
        "publisher": "National Council of State Boards of Nursing (NCSBN)",
        "url": "https://www.ncsbn.org/nclex/nclex-test-plans.page",
        "license": "copyright NCSBN",
        "license_url": "https://www.ncsbn.org/nclex/nclex-test-plans.page",
        "text_reuse_allowed": False,
        "attribution_template": None,
        "source_type": "official_exam_blueprint",
        "verified_at": VERIFIED_AT,
        "notes": (
            "NCSBN Test Plan is publicly downloadable for exam candidates but remains "
            "copyright NCSBN. Category names, weights, and domain structure are factual "
            "and non-copyrightable — safe to use as blueprint. "
            "Do not reproduce test plan text verbatim."
        ),
    },
    {
        "slug": "scfhs_snle",
        "title": "SNLE — Saudi Nursing Licensing Exam Blueprint",
        "publisher": "Saudi Commission for Health Specialties (SCFHS)",
        "url": "https://scfhs.org.sa/",
        "license": "unclear (government publication)",
        "license_url": None,
        "text_reuse_allowed": False,
        "attribution_template": None,
        "source_type": "official_exam_blueprint",
        "verified_at": VERIFIED_AT,
        "notes": (
            "SCFHS is a Saudi government body. Blueprint categories and weights are "
            "publicly distributed to exam candidates. No explicit open license found. "
            "Use structure/categories as factual basis only."
        ),
    },
    {
        "slug": "dha_blueprint",
        "title": "DHA Nursing Licensing Exam Blueprint",
        "publisher": "Dubai Health Authority (DHA)",
        "url": "https://www.dha.gov.ae/en/HealthProfessionals/Licensing",
        "license": "unclear (government publication)",
        "license_url": None,
        "text_reuse_allowed": False,
        "attribution_template": None,
        "source_type": "official_exam_blueprint",
        "verified_at": VERIFIED_AT,
        "notes": "DHA government blueprint — categories and domain weights used as structural facts.",
    },
    {
        "slug": "qchp_blueprint",
        "title": "QCHP Nursing Licensing Exam Blueprint",
        "publisher": "Qatar Council for Healthcare Practitioners (QCHP)",
        "url": "https://www.qchp.org.qa/en/Licensing",
        "license": "unclear (government publication)",
        "license_url": None,
        "text_reuse_allowed": False,
        "attribution_template": None,
        "source_type": "official_exam_blueprint",
        "verified_at": VERIFIED_AT,
        "notes": "QCHP government blueprint — categories and domain weights used as structural facts.",
    },
]
# fmt: on


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        inserted = 0
        skipped = 0
        for src in SOURCES:
            existing = await db.get(ContentSource, src["slug"])
            if existing:
                skipped += 1
                continue
            db.add(ContentSource(**src))
            inserted += 1
        await db.commit()
        print(f"ContentSource seed: {inserted} inserted, {skipped} already existed.")


if __name__ == "__main__":
    asyncio.run(seed())
