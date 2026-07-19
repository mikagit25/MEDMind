"""
NCLEX Readiness Score

Computes a weighted practice-accuracy score (0–100) that integrates:
  - NCLEX category weights (official NCLEX-RN test plan distribution)
  - Recency bias: last 7 days × 1.5, last 30 days × 1.0, older × 0.5
  - Difficulty adjustment: easy × 0.8, medium × 1.0, hard × 1.2

Minimum 50 answered questions before a score is shown (too few questions
produce a misleading estimate).

Legal note: the score is always presented as an *estimate* based on
practice performance, never as a probability of passing the NCLEX exam.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# ── Category configuration ────────────────────────────────────────────────────

# NCLEX-RN test plan category weights (2023 test plan, normalized)
# Source: https://www.ncsbn.org/test-plans.page
CATEGORY_WEIGHTS: dict[str, float] = {
    "safe_effective_care":           0.32,  # Management of Care + Safety & Infection
    "safe_effective_care_environment": 0.32,
    "safety":                        0.32,
    "health_promotion":              0.09,
    "health_promotion_and_maintenance": 0.09,
    "psychosocial":                  0.09,
    "psychosocial_integrity":        0.09,
    "psychological":                 0.09,
    "basic_care":                    0.09,
    "basic_care_and_comfort":        0.09,
    "pharmacological":               0.16,
    "pharmacological_therapies":     0.16,
    "reduction_risk":                0.12,
    "reduction_of_risk":             0.12,
    "reduction_of_risk_potential":   0.12,
    "physiological_adaptation":      0.14,
    "physiological":                 0.14,
    "physiological_integrity":       0.14,
}

DEFAULT_CATEGORY_WEIGHT = 0.10  # for unknown categories

DIFFICULTY_WEIGHTS: dict[str, float] = {
    "easy":   0.8,
    "medium": 1.0,
    "hard":   1.2,
}

READINESS_THRESHOLD = 50  # min answered questions before showing score

LEVELS = [
    (75, "high",          "High"),
    (62, "passing_range", "Passing Range"),
    (55, "borderline",    "Borderline"),
    (0,  "below_passing", "Below Passing"),
]

DISCLAIMER = (
    "Readiness estimate based on your practice performance. "
    "Not a prediction of NCLEX exam outcome."
)

# ── Alias normalization (matches exam.py) ─────────────────────────────────────

_ALIAS: dict[str, str] = {
    "safe_effective_care_environment": "safe_effective_care",
    "safety":                          "safe_effective_care",
    "health_promotion_and_maintenance": "health_promotion",
    "psychosocial_integrity":          "psychosocial",
    "psychological":                   "psychosocial",
    "communication":                   "psychosocial",
    "basic_care_and_comfort":          "basic_care",
    "pharmacological_therapies":       "pharmacological",
    "reduction_of_risk":               "reduction_risk",
    "reduction_of_risk_potential":     "reduction_risk",
    "physiological":                   "physiological_adaptation",
    "physiological_integrity":         "physiological_adaptation",
}

CANONICAL_LABELS: dict[str, str] = {
    "safe_effective_care":       "Safe & Effective Care Environment",
    "health_promotion":          "Health Promotion & Maintenance",
    "psychosocial":              "Psychosocial Integrity",
    "basic_care":                "Basic Care & Comfort",
    "pharmacological":           "Pharmacological & Parenteral Therapies",
    "reduction_risk":            "Reduction of Risk Potential",
    "physiological_adaptation":  "Physiological Adaptation",
}


def _normalize(cat: str) -> str:
    return _ALIAS.get(cat, cat)


def _recency_weight(session_date: datetime, now: datetime) -> float:
    age_days = (now - session_date).total_seconds() / 86400
    if age_days <= 7:
        return 1.5
    if age_days <= 30:
        return 1.0
    return 0.5


def _difficulty_weight(difficulty: str | None) -> float:
    return DIFFICULTY_WEIGHTS.get((difficulty or "medium").lower(), 1.0)


def _category_weight(cat: str) -> float:
    return CATEGORY_WEIGHTS.get(cat, DEFAULT_CATEGORY_WEIGHT)


# ── Core computation ──────────────────────────────────────────────────────────

def compute_from_sessions(sessions: list[Any], now: datetime | None = None) -> dict:
    """
    Compute readiness from a list of ExamSession ORM objects.
    Each session must have: per_question (list), starts_at (datetime).

    Returns a readiness dict even if threshold not met (threshold_met=False).
    """
    if now is None:
        now = datetime.utcnow()

    # Per-category accumulators: {cat: {"w_correct": float, "w_total": float, "count": int}}
    cat_stats: dict[str, dict] = {}
    total_answered = 0
    weighted_correct = 0.0
    weighted_total = 0.0

    # Trend: one entry per session (session-level score for the chart)
    trend: list[dict] = []

    for sess in sessions:
        pqs = sess.per_question or []
        if not pqs:
            continue

        recency = _recency_weight(sess.starts_at, now)
        sess_correct = sum(1 for pq in pqs if pq.get("correct"))
        sess_total = len(pqs)

        trend.append({
            "date": sess.starts_at.date().isoformat(),
            "score_pct": sess.score_pct,
            "correct": sess_correct,
            "total": sess_total,
        })

        for pq in pqs:
            raw_cat = pq.get("nclex_client_needs") or ""
            cat = _normalize(raw_cat) if raw_cat else ""
            diff = pq.get("difficulty") or "medium"
            is_correct = bool(pq.get("correct", False))

            cat_w = _category_weight(cat) if cat else DEFAULT_CATEGORY_WEIGHT
            diff_w = _difficulty_weight(diff)
            combined_w = recency * cat_w * diff_w

            weighted_total += combined_w
            if is_correct:
                weighted_correct += combined_w

            total_answered += 1

            if cat:
                if cat not in cat_stats:
                    cat_stats[cat] = {"w_correct": 0.0, "w_total": 0.0, "count": 0}
                cat_stats[cat]["w_total"] += recency * diff_w
                if is_correct:
                    cat_stats[cat]["w_correct"] += recency * diff_w
                cat_stats[cat]["count"] += 1

    threshold_met = total_answered >= READINESS_THRESHOLD
    questions_to_threshold = max(0, READINESS_THRESHOLD - total_answered)

    # Overall score
    score = round((weighted_correct / weighted_total * 100)) if weighted_total > 0 else 0

    # Level
    level_key = "below_passing"
    level_label = "Below Passing"
    for threshold, key, label in LEVELS:
        if score >= threshold:
            level_key = key
            level_label = label
            break

    # Category breakdown
    category_breakdown: dict[str, dict] = {}
    for cat, s in cat_stats.items():
        pct = round(s["w_correct"] / s["w_total"] * 100) if s["w_total"] > 0 else 0
        category_breakdown[cat] = {
            "label": CANONICAL_LABELS.get(cat, cat.replace("_", " ").title()),
            "pct": pct,
            "count": s["count"],
        }

    # Top-3 weak categories: below 75% with ≥5 questions, sorted by worst first
    weak_categories = sorted(
        [
            {"key": k, **v}
            for k, v in category_breakdown.items()
            if v["count"] >= 5 and v["pct"] < 75
        ],
        key=lambda x: x["pct"],
    )[:3]

    # Trend sorted ascending by date (last 30 days, max 30 entries)
    trend_sorted = sorted(trend, key=lambda x: x["date"])[-30:]

    return {
        "score": score if threshold_met else None,
        "level": level_key if threshold_met else None,
        "level_label": level_label if threshold_met else None,
        "threshold_met": threshold_met,
        "questions_answered": total_answered,
        "questions_to_threshold": questions_to_threshold,
        "category_breakdown": category_breakdown,
        "weak_categories": weak_categories,
        "trend": trend_sorted,
        "disclaimer": DISCLAIMER,
    }


async def compute_readiness(user_id: UUID, db: AsyncSession) -> dict:
    """Load user's completed NCLEX sessions and compute readiness."""
    from app.models.models import ExamSession  # local import to avoid circular

    result = await db.execute(
        select(ExamSession)
        .where(
            ExamSession.user_id == user_id,
            ExamSession.status == "completed",
            ExamSession.mode_id.like("nclex_%"),
        )
        .order_by(ExamSession.starts_at.asc())
    )
    sessions = result.scalars().all()
    return compute_from_sessions(sessions)


async def get_cached_readiness(user_id: UUID, db: AsyncSession) -> dict:
    """Return readiness from Redis cache (1-hour TTL) or compute fresh."""
    from app.core.cache import get_cached, set_cached

    cache_key = f"readiness:{user_id}"
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached

    data = await compute_readiness(user_id, db)
    await set_cached(cache_key, data, ttl=3600)
    return data


async def invalidate_readiness_cache(user_id: UUID) -> None:
    """Call after a session completes to force recompute on next request."""
    from app.core.cache import invalidate

    await invalidate(f"readiness:{user_id}*")
