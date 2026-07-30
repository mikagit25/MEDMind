"""Bank-Scale B3 — Build generation queue from coverage deficits.

Reads the current question bank counts per exam × category, computes deficits
against volume targets, and inserts GenerationQueue rows for each deficit.

Usage:
  python -m app.scripts.plan_generation                     # all exams
  python -m app.scripts.plan_generation nclex_rn snle       # specific exams
  python -m app.scripts.plan_generation --dry-run           # print plan, no DB writes
  python -m app.scripts.plan_generation --min-deficit 20    # skip small deficits

Volume targets (B3.4):
  nclex_rn  2000 | snle 1200 | dha 900 | qchp 500 | haad 500 | kpss 500

SNLE weights corrected 2026-07-30 from SCFHS Applicant Guide 2024:
  Adult Nursing 40% | Maternal-Child Nursing 30% | Nursing Fundamentals 20%
  | Nursing Management & Leadership 10%
  Mapped to NCLEX categories (which is how MCQQuestion.nclex_client_needs is tagged).
"""
from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime

from sqlalchemy import func, select

from app.core.database import AsyncSessionLocal
from app.models.models import GenerationQueue, MCQQuestion

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

# ── Volume targets per exam (B3.4) ────────────────────────────────────────────

VOLUME_TARGETS: dict[str, int] = {
    "nclex_rn": 2000,
    "snle":     1200,
    "dha":       900,
    "qchp":      500,
    "haad":      500,
    "kpss":      500,
}

# Default blueprint weights (NCLEX-RN 2023, public categories only, no text copied)
_NCLEX_RN_WEIGHTS: dict[str, float] = {
    "management_of_care":       17.0,
    "pharmacological":          15.0,
    "physiological_adaptation": 14.0,
    "reduction_risk":           12.0,
    "safe_effective_care":      12.0,
    "health_promotion":          9.0,
    "psychosocial":              9.0,
    "basic_care":                9.0,
}

# SNLE blueprint weights (SCFHS Applicant Guide 2024, verified 2026-07-30).
# Official categories: Adult Nursing 40% | Maternal-Child 30% | Fundamentals 20% | Management 10%
# Mapped to NCLEX nclex_client_needs tags used in question tagging:
_SNLE_WEIGHTS: dict[str, float] = {
    # Adult Nursing (40%): medical-surgical, critical care, pharmacology
    "physiological_adaptation": 20.0,
    "pharmacological":          12.0,
    "reduction_risk":            8.0,
    # Maternal-Child Nursing (30%): OB, newborn, pediatrics — approximated via these NCLEX cats
    "health_promotion":         16.0,
    "basic_care":               14.0,
    # Nursing Fundamentals (20%): fundamentals + safety
    "safe_effective_care":      12.0,
    "psychosocial":              8.0,
    # Nursing Management & Leadership (10%)
    "management_of_care":       10.0,
}

# Per-exam override: exams with officially verified blueprints use specific weights;
# others fall back to _NCLEX_RN_WEIGHTS as best approximation.
EXAM_BLUEPRINT_WEIGHTS: dict[str, dict[str, float]] = {
    "nclex_rn": _NCLEX_RN_WEIGHTS,
    "snle":     _SNLE_WEIGHTS,
    # DHA, QCHP, HAAD, KPSS: official blueprints not yet verified — using NCLEX-RN approximation
}

# Public alias for tests and downstream code
BLUEPRINT_WEIGHTS = _NCLEX_RN_WEIGHTS

# Question type mix targets (%) per exam
TYPE_MIX: dict[str, dict[str, float]] = {
    "nclex_rn": {"mcq": 55.0, "sata": 30.0, "ordered": 8.0, "calculation": 7.0},
    "snle":     {"mcq": 75.0, "sata": 15.0, "ordered": 5.0, "calculation": 5.0},
    "dha":      {"mcq": 80.0, "sata": 10.0, "ordered": 5.0, "calculation": 5.0},
    "qchp":     {"mcq": 80.0, "sata": 10.0, "ordered": 5.0, "calculation": 5.0},
    "haad":     {"mcq": 80.0, "sata": 10.0, "ordered": 5.0, "calculation": 5.0},
    "kpss":     {"mcq": 90.0, "sata":  5.0, "ordered": 2.5, "calculation": 2.5},
}

# Difficulty targets (%) — bank should skew medium/hard per NCLEX design
DIFFICULTY_PRIORITY: list[str] = ["medium", "hard", "easy"]


def _exam_weights(exam_slug: str) -> dict[str, float]:
    """Return blueprint weights for an exam, falling back to NCLEX-RN."""
    return EXAM_BLUEPRINT_WEIGHTS.get(exam_slug, _NCLEX_RN_WEIGHTS)


def _target_count(exam_slug: str, category: str, q_type: str) -> int:
    total = VOLUME_TARGETS.get(exam_slug, 500)
    weights = _exam_weights(exam_slug)
    cat_weight = weights.get(category, 100.0 / len(weights))
    type_mix = TYPE_MIX.get(exam_slug, {"mcq": 70.0, "sata": 20.0, "ordered": 5.0, "calculation": 5.0})
    type_weight = type_mix.get(q_type, 0.0)
    return max(1, round(total * cat_weight / 100.0 * type_weight / 100.0))


async def get_bank_counts(db) -> dict[str, dict[str, dict[str, int]]]:
    """Return counts as {exam_slug: {category: {q_type: count}}}."""
    import json as _json
    from sqlalchemy import select as _sel
    rows = await db.execute(
        _sel(
            MCQQuestion.exam_slugs,
            MCQQuestion.nclex_client_needs,
            MCQQuestion.question_type,
        ).where(MCQQuestion.status == "active")
    )
    counts: dict[str, dict[str, dict[str, int]]] = {}
    for row in rows:
        slugs = row.exam_slugs or []
        if isinstance(slugs, str):
            try:
                slugs = _json.loads(slugs)
            except Exception:
                slugs = []
        cat = row.nclex_client_needs or "uncategorized"
        qtype = row.question_type or "mcq"
        for exam in slugs:
            counts.setdefault(exam, {}).setdefault(cat, {})[qtype] = (
                counts.get(exam, {}).get(cat, {}).get(qtype, 0) + 1
            )
    return counts


async def build_plan(
    exam_slugs: list[str] | None = None,
    min_deficit: int = 5,
    dry_run: bool = False,
) -> list[dict]:
    """Compute deficit per exam × category × type, return plan list."""
    target_exams = exam_slugs or list(VOLUME_TARGETS.keys())
    plan: list[dict] = []

    async with AsyncSessionLocal() as db:
        counts = await get_bank_counts(db)

        for exam in target_exams:
            exam_counts = counts.get(exam, {})
            for category, cat_weight in _exam_weights(exam).items():
                cat_counts = exam_counts.get(category, {})
                for q_type in ["mcq", "sata", "ordered", "calculation"]:
                    target = _target_count(exam, category, q_type)
                    actual = cat_counts.get(q_type, 0)
                    deficit = max(0, target - actual)
                    if deficit < min_deficit:
                        continue
                    entry = {
                        "exam_slug": exam,
                        "nclex_category": category,
                        "question_type": q_type,
                        "target_difficulty": "medium",
                        "count_requested": deficit,
                        "target": target,
                        "actual": actual,
                    }
                    plan.append(entry)
                    logger.info(
                        "[%s] %s/%s  target=%d  actual=%d  deficit=%d",
                        exam, category, q_type, target, actual, deficit,
                    )

        if not dry_run:
            for entry in plan:
                db.add(GenerationQueue(
                    exam_slug=entry["exam_slug"],
                    nclex_category=entry["nclex_category"],
                    question_type=entry["question_type"],
                    target_difficulty=entry["target_difficulty"],
                    count_requested=entry["count_requested"],
                    status="pending",
                    created_at=datetime.utcnow(),
                ))
            await db.commit()
            logger.info("Inserted %d generation tasks into queue", len(plan))

    return plan


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry_run = "--dry-run" in sys.argv
    min_def = 5
    for a in sys.argv[1:]:
        if a.startswith("--min-deficit="):
            min_def = int(a.split("=")[1])

    # args without -- flags are exam slugs
    exam_filter = [a for a in args if a] or None

    plan = asyncio.run(build_plan(exam_filter, min_deficit=min_def, dry_run=dry_run))

    print("\n=== Generation Plan ===")
    if not plan:
        print("  No deficits above threshold.")
    else:
        total = sum(e["count_requested"] for e in plan)
        for e in plan:
            print(
                f"  {e['exam_slug']:12} {e['nclex_category']:30} "
                f"{e['question_type']:12} "
                f"target={e['target']:4}  actual={e['actual']:4}  deficit={e['count_requested']:4}"
            )
        print(f"\n  TOTAL questions to generate: {total}")
        if dry_run:
            print("  (dry-run — nothing written to DB)")
