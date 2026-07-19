"""
Phase 3 acceptance tests — NCLEX Readiness Score.

Verifies:
- Score appears only after 50+ answered questions (threshold_met)
- Weak category with low accuracy lands in top-3 weak_categories
- Recency weighting: recent sessions have more impact
- Difficulty weighting: hard questions count more
- Trend is sorted ascending by date
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from app.services.readiness import compute_from_sessions, READINESS_THRESHOLD


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_session(
    per_question: list[dict],
    starts_at: datetime | None = None,
    score_pct: float = 60.0,
):
    sess = MagicMock()
    sess.per_question = per_question
    sess.starts_at = starts_at or datetime.utcnow()
    sess.score_pct = score_pct
    return sess


def make_pq(
    correct: bool,
    cat: str = "pharmacological",
    difficulty: str = "medium",
) -> dict:
    return {
        "correct": correct,
        "nclex_client_needs": cat,
        "difficulty": difficulty,
    }


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_score_not_shown_below_threshold():
    """Score must be None until 50 questions are answered."""
    # 30 questions — below threshold
    pqs = [make_pq(True, "pharmacological") for _ in range(30)]
    sess = make_session(pqs)
    result = compute_from_sessions([sess])

    assert result["threshold_met"] is False
    assert result["score"] is None
    assert result["level"] is None
    assert result["questions_answered"] == 30
    assert result["questions_to_threshold"] == 20


def test_score_shown_at_threshold():
    """Score is computed once 50 questions are answered."""
    pqs = [make_pq(True, "pharmacological") for _ in range(50)]
    sess = make_session(pqs)
    result = compute_from_sessions([sess])

    assert result["threshold_met"] is True
    assert result["score"] is not None
    assert 0 <= result["score"] <= 100
    assert result["questions_answered"] == 50
    assert result["questions_to_threshold"] == 0


def test_weak_category_appears_in_top3():
    """A category answered mostly wrong should appear in weak_categories."""
    now = datetime.utcnow()

    # 10 questions on 'pharmacological' — 90% correct (strong)
    strong_pqs = [make_pq(i < 9, "pharmacological") for i in range(10)]
    # 10 questions on 'psychosocial' — 20% correct (weak!)
    weak_pqs = [make_pq(i < 2, "psychosocial") for i in range(10)]
    # 30 more questions to reach threshold
    filler_pqs = [make_pq(True, "physiological_adaptation") for _ in range(30)]

    all_pqs = strong_pqs + weak_pqs + filler_pqs
    sess = make_session(all_pqs, starts_at=now)
    result = compute_from_sessions([sess], now=now)

    assert result["threshold_met"] is True

    weak_keys = [w["key"] for w in result["weak_categories"]]
    assert "psychosocial" in weak_keys, (
        f"Expected 'psychosocial' in weak_categories, got: {weak_keys}"
    )

    # pharmacological should not be in weak (90% correct)
    assert "pharmacological" not in weak_keys


def test_weak_category_is_lowest_pct():
    """The weakest category should have the lowest pct in the breakdown."""
    now = datetime.utcnow()
    pqs = (
        [make_pq(True,  "pharmacological") for _ in range(10)] +
        [make_pq(False, "psychosocial")    for _ in range(10)] +
        [make_pq(True,  "physiological_adaptation") for _ in range(10)] +
        [make_pq(True,  "safe_effective_care")      for _ in range(20)]
    )
    sess = make_session(pqs, starts_at=now)
    result = compute_from_sessions([sess], now=now)

    assert result["threshold_met"] is True
    assert result["weak_categories"][0]["key"] == "psychosocial"
    assert result["weak_categories"][0]["pct"] == 0


def test_recency_weight_recent_sessions_dominate():
    """
    Two equal-size sessions: one old (0% correct), one recent (100% correct).
    Recent session should pull score above 50%.
    """
    now = datetime.utcnow()
    old_date = now - timedelta(days=60)
    recent_date = now - timedelta(days=2)

    # Old session: all wrong
    old_pqs = [make_pq(False, "pharmacological") for _ in range(25)]
    old_sess = make_session(old_pqs, starts_at=old_date, score_pct=0.0)

    # Recent session: all correct
    recent_pqs = [make_pq(True, "pharmacological") for _ in range(25)]
    recent_sess = make_session(recent_pqs, starts_at=recent_date, score_pct=100.0)

    result = compute_from_sessions([old_sess, recent_sess], now=now)

    assert result["threshold_met"] is True
    # Recency 0.5 for old (all wrong) vs 1.5 for recent (all correct)
    # weighted: (0 * 0.5) + (25 * 1.5) / (25 * 0.5 + 25 * 1.5) = 37.5 / 50 = 75%
    assert result["score"] > 60, f"Expected score > 60 (recent dominates), got {result['score']}"


def test_difficulty_weight_hard_counts_more():
    """Hard correct answers should boost score more than easy correct answers."""
    now = datetime.utcnow()

    # Scenario A: 50 easy correct questions
    pqs_easy = [make_pq(True, "pharmacological", "easy") for _ in range(50)]
    sess_easy = make_session(pqs_easy, starts_at=now)
    result_easy = compute_from_sessions([sess_easy], now=now)

    # Scenario B: 50 hard correct questions (same category, same date)
    pqs_hard = [make_pq(True, "pharmacological", "hard") for _ in range(50)]
    sess_hard = make_session(pqs_hard, starts_at=now)
    result_hard = compute_from_sessions([sess_hard], now=now)

    # Both should be 100% but verify the model accepts difficulty weighting without error
    assert result_easy["score"] == 100
    assert result_hard["score"] == 100

    # Scenario C: 25 easy correct + 25 hard wrong
    pqs_mixed = (
        [make_pq(True,  "pharmacological", "easy") for _ in range(25)] +
        [make_pq(False, "pharmacological", "hard") for _ in range(25)]
    )
    sess_mixed = make_session(pqs_mixed, starts_at=now)
    result_mixed = compute_from_sessions([sess_mixed], now=now)

    # Hard wrong questions weigh more, so score < 50
    # Easy correct weight = 0.8, hard wrong weight = 1.2
    # weighted_correct = 25 * 0.8 = 20; weighted_total = 25*0.8 + 25*1.2 = 50
    # score = 20/50 = 40
    assert result_mixed["score"] < 50, f"Expected score < 50, got {result_mixed['score']}"


def test_trend_sorted_ascending():
    """Trend entries must be sorted by date oldest → newest."""
    now = datetime.utcnow()
    pqs = [make_pq(True, "pharmacological") for _ in range(26)]

    sessions = [
        make_session(pqs, starts_at=now - timedelta(days=20), score_pct=60.0),
        make_session(pqs, starts_at=now - timedelta(days=5), score_pct=80.0),
        make_session(pqs, starts_at=now - timedelta(days=10), score_pct=70.0),
    ]
    result = compute_from_sessions(sessions, now=now)

    dates = [t["date"] for t in result["trend"]]
    assert dates == sorted(dates), f"Trend not sorted ascending: {dates}"


def test_disclaimer_always_present():
    """Disclaimer must be in every response."""
    pqs = [make_pq(True) for _ in range(3)]
    result = compute_from_sessions([make_session(pqs)])
    assert "disclaimer" in result
    assert len(result["disclaimer"]) > 10


def test_empty_sessions():
    """No sessions → threshold not met, no error."""
    result = compute_from_sessions([])
    assert result["threshold_met"] is False
    assert result["score"] is None
    assert result["questions_answered"] == 0
    assert result["trend"] == []
    assert result["category_breakdown"] == {}
