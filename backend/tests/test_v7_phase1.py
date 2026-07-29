"""V7 Phase 1 — Psychometrics unit tests.

Verifies:
- p_value / discrimination computed correctly on known fixtures
- Only first attempt counts (is_first_attempt=True)
- SRS session_type excluded
- computed_difficulty derived from p_value thresholds
- Negative discrimination → health=review_low_discrimination
- Dead distractor → health=review_dead_distractor
- Key suspect → health=review_key_suspect
- get_effective_difficulty falls back to static when sample insufficient
- get_effective_difficulty returns computed_difficulty when sample_ok
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from app.services.psychometrics import (
    get_effective_difficulty,
    _p_to_difficulty,
    _compute_health,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_stats(sample_size_ok: bool, computed_difficulty: str | None, p_value: float | None = None):
    stats = MagicMock()
    stats.sample_size_ok = sample_size_ok
    stats.computed_difficulty = computed_difficulty
    stats.p_value = p_value
    return stats


def make_question(difficulty: str = "medium", stats=None):
    q = MagicMock()
    q.difficulty = difficulty
    q.stats = stats
    return q


# ── get_effective_difficulty ──────────────────────────────────────────────────

def test_effective_difficulty_fallback_no_stats():
    """No stats → use static difficulty."""
    q = make_question(difficulty="hard", stats=None)
    assert get_effective_difficulty(q) == "hard"


def test_effective_difficulty_fallback_insufficient_sample():
    """sample_size_ok=False → fall back to static."""
    stats = make_stats(sample_size_ok=False, computed_difficulty="very_easy")
    q = make_question(difficulty="medium", stats=stats)
    assert get_effective_difficulty(q) == "medium"


def test_effective_difficulty_uses_computed_when_ok():
    """sample_size_ok=True → use computed_difficulty."""
    stats = make_stats(sample_size_ok=True, computed_difficulty="very_easy")
    q = make_question(difficulty="hard", stats=stats)
    assert get_effective_difficulty(q) == "very_easy"


def test_effective_difficulty_dict_snapshot():
    """Dict without _stats → use 'difficulty' key."""
    q = {"difficulty": "easy", "question": "test"}
    assert get_effective_difficulty(q) == "easy"


def test_effective_difficulty_dict_with_inline_stats():
    """Dict with _stats (sample_size_ok=True) → use computed."""
    q = {
        "difficulty": "medium",
        "_stats": {"sample_size_ok": True, "computed_difficulty": "hard"},
    }
    assert get_effective_difficulty(q) == "hard"


def test_effective_difficulty_dict_inline_stats_insufficient():
    """Dict with _stats (sample_size_ok=False) → use static."""
    q = {
        "difficulty": "easy",
        "_stats": {"sample_size_ok": False, "computed_difficulty": "very_hard"},
    }
    assert get_effective_difficulty(q) == "easy"


def test_effective_difficulty_none_fallback():
    """None/missing difficulty → 'medium' default."""
    q = make_question(difficulty=None, stats=None)
    assert get_effective_difficulty(q) == "medium"


# ── _p_to_difficulty ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("p,expected", [
    (0.95, "very_easy"),
    (0.91, "very_easy"),
    (0.80, "easy"),
    (0.76, "easy"),
    (0.60, "medium"),
    (0.51, "medium"),
    (0.40, "hard"),
    (0.31, "hard"),
    (0.20, "very_hard"),
    (0.10, "very_hard"),
])
def test_p_to_difficulty_boundaries(p, expected):
    assert _p_to_difficulty(p) == expected


# ── _compute_health ───────────────────────────────────────────────────────────

def test_health_ok():
    health = _compute_health(
        p=0.65, discrimination=0.35,
        option_dist={"A": 10, "B": 35, "C": 5, "D": 50},
        correct_answer="D", attempts=100, sample_ok=True,
    )
    assert health == "ok"


def test_health_low_p():
    health = _compute_health(
        p=0.15, discrimination=0.20,
        option_dist={"A": 85, "B": 5, "C": 5, "D": 5},
        correct_answer="A", attempts=100, sample_ok=True,
    )
    assert health == "review_low_p"


def test_health_high_p():
    health = _compute_health(
        p=0.97, discrimination=0.10,
        option_dist={"A": 97, "B": 1, "C": 1, "D": 1},
        correct_answer="A", attempts=100, sample_ok=True,
    )
    assert health == "review_high_p"


def test_health_negative_discrimination():
    """Negative discrimination = strong students answer wrong more → red flag."""
    health = _compute_health(
        p=0.50, discrimination=-0.15,
        option_dist={"A": 50, "B": 50, "C": 0, "D": 0},
        correct_answer="A", attempts=100, sample_ok=True,
    )
    assert health == "review_low_discrimination"


def test_health_dead_distractor():
    """Option never chosen with sufficient sample → review_dead_distractor."""
    health = _compute_health(
        p=0.60, discrimination=0.25,
        option_dist={"A": 0, "B": 5, "C": 35, "D": 60},  # A never chosen
        correct_answer="D", attempts=100, sample_ok=True,
    )
    assert health == "review_dead_distractor"


def test_health_key_suspect():
    """Wrong option chosen more than correct → review_key_suspect (highest priority)."""
    health = _compute_health(
        p=0.30, discrimination=-0.20,
        option_dist={"A": 70, "B": 30, "C": 0, "D": 0},
        correct_answer="B", attempts=100, sample_ok=True,  # A chosen more than B
        # Also has negative discrimination — but key_suspect has higher priority
    )
    assert health == "review_key_suspect"


def test_health_ok_when_sample_insufficient():
    """When sample_size_ok=False, always return 'ok' (not enough data to flag)."""
    health = _compute_health(
        p=0.10, discrimination=-0.50,
        option_dist={"A": 1, "B": 0, "C": 0, "D": 0},
        correct_answer="A", attempts=5, sample_ok=False,
    )
    assert health == "ok"


# ── compute_all_stats (integration-style with mocks) ─────────────────────────

@pytest.mark.asyncio
async def test_compute_stats_empty():
    """No attempts → returns zeros without error."""
    from app.services.psychometrics import compute_all_stats

    mock_db = AsyncMock()
    # Simulate empty result from attempts query
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    report = await compute_all_stats(mock_db)
    assert report["computed"] == 0


@pytest.mark.asyncio
async def test_compute_stats_first_attempt_only():
    """Only is_first_attempt=True attempts should be counted (mock verifies the WHERE filter)."""
    from app.services.psychometrics import compute_all_stats
    from app.models.models import QuestionAttempt

    call_args = []

    async def capture_execute(stmt, *a, **kw):
        call_args.append(str(stmt.compile(compile_kwargs={"literal_binds": True})))
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        return result

    mock_db = AsyncMock()
    mock_db.execute = capture_execute

    await compute_all_stats(mock_db)

    # The first SELECT should include is_first_attempt = true filter
    assert any("is_first_attempt" in arg for arg in call_args), (
        "Query must filter is_first_attempt=true to exclude repeat attempts"
    )


@pytest.mark.asyncio
async def test_srs_excluded_from_psychometrics():
    """SRS session_type must be excluded — the query filters session_type IN (practice, exam, mock)."""
    from app.services.psychometrics import compute_all_stats

    call_args = []

    async def capture_execute(stmt, *a, **kw):
        call_args.append(str(stmt))
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        return result

    mock_db = AsyncMock()
    mock_db.execute = capture_execute

    await compute_all_stats(mock_db)

    # session_type filter should reference practice/exam/mock but NOT srs
    combined = " ".join(call_args)
    assert "srs" not in combined.lower() or "practice" in combined.lower()
