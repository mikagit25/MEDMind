"""Tests for NCLEX-style question type scoring logic.

Covers: sata (all-or-nothing + partial), ordered, calculation.
Uses the scoring logic extracted directly from progress.py for unit testing.
"""
import pytest


# ── Scoring helpers (extracted from progress.py logic) ───────────────────────

def score_sata(selected: list[str], correct: list[str], partial: bool) -> tuple[bool, float | None]:
    selected_s = sorted(s.upper() for s in selected)
    correct_s = sorted(s.upper() for s in correct)
    if partial:
        total = len(correct_s)
        right = len(set(selected_s) & set(correct_s))
        wrong = len(set(selected_s) - set(correct_s))
        raw = max(0, right - wrong) / total if total else 0
        score = round(raw, 2)
        return score >= 1.0, score
    else:
        return selected_s == correct_s, None


def score_ordered(submitted: list[str], correct: list[str]) -> bool:
    return [s.upper() for s in submitted] == [s.upper() for s in correct]


def score_calculation(value: float, expected: float, tolerance: float) -> bool:
    return abs(value - expected) <= tolerance


# ── SATA tests ────────────────────────────────────────────────────────────────

class TestSATA:
    def test_all_correct_all_or_nothing(self):
        is_correct, partial = score_sata(["A", "C", "D"], ["A", "C", "D"], partial=False)
        assert is_correct is True
        assert partial is None

    def test_all_correct_partial(self):
        is_correct, partial = score_sata(["A", "C", "D"], ["A", "C", "D"], partial=True)
        assert is_correct is True
        assert partial == 1.0

    def test_partial_correct_all_or_nothing(self):
        is_correct, partial = score_sata(["A", "C"], ["A", "C", "D"], partial=False)
        assert is_correct is False
        assert partial is None

    def test_partial_correct_with_partial_scoring(self):
        # 2 right, 0 wrong, out of 3 → 2/3
        is_correct, partial = score_sata(["A", "C"], ["A", "C", "D"], partial=True)
        assert is_correct is False
        assert partial == pytest.approx(0.67, abs=0.01)

    def test_wrong_with_extra_answers_partial_scoring(self):
        # 2 right, 1 wrong out of 3 → (2-1)/3 = 0.33
        is_correct, partial = score_sata(["A", "C", "E"], ["A", "C", "D"], partial=True)
        assert is_correct is False
        assert partial == pytest.approx(0.33, abs=0.01)

    def test_all_wrong_all_or_nothing(self):
        is_correct, partial = score_sata(["B", "E"], ["A", "C", "D"], partial=False)
        assert is_correct is False

    def test_all_wrong_partial_scoring_floor_zero(self):
        # 0 right, 2 wrong, out of 3 → max(0, -2/3) = 0
        is_correct, partial = score_sata(["B", "E"], ["A", "C", "D"], partial=True)
        assert is_correct is False
        assert partial == 0.0

    def test_case_insensitive(self):
        is_correct, _ = score_sata(["a", "c", "d"], ["A", "C", "D"], partial=False)
        assert is_correct is True

    def test_empty_selection_all_or_nothing(self):
        is_correct, _ = score_sata([], ["A", "C"], partial=False)
        assert is_correct is False

    def test_single_correct_option_sata(self):
        is_correct, _ = score_sata(["B"], ["B"], partial=False)
        assert is_correct is True

    def test_order_does_not_matter(self):
        is_correct, _ = score_sata(["D", "A", "C"], ["A", "C", "D"], partial=False)
        assert is_correct is True


# ── Ordered tests ─────────────────────────────────────────────────────────────

class TestOrdered:
    def test_correct_order(self):
        assert score_ordered(["B", "D", "A", "C"], ["B", "D", "A", "C"]) is True

    def test_wrong_order(self):
        assert score_ordered(["A", "B", "C", "D"], ["B", "D", "A", "C"]) is False

    def test_partial_order_is_wrong(self):
        assert score_ordered(["B", "D"], ["B", "D", "A", "C"]) is False

    def test_extra_items_is_wrong(self):
        assert score_ordered(["B", "D", "A", "C", "E"], ["B", "D", "A", "C"]) is False

    def test_case_insensitive(self):
        assert score_ordered(["b", "d", "a", "c"], ["B", "D", "A", "C"]) is True

    def test_single_item_correct(self):
        assert score_ordered(["A"], ["A"]) is True

    def test_single_item_wrong(self):
        assert score_ordered(["B"], ["A"]) is False

    def test_empty_matches_empty(self):
        assert score_ordered([], []) is True


# ── Calculation tests ─────────────────────────────────────────────────────────

class TestCalculation:
    def test_exact_match(self):
        assert score_calculation(10.0, 10.0, 0.01) is True

    def test_within_tolerance(self):
        assert score_calculation(10.009, 10.0, 0.01) is True

    def test_at_tolerance_boundary(self):
        assert score_calculation(10.01, 10.0, 0.01) is True

    def test_just_outside_tolerance(self):
        assert score_calculation(10.011, 10.0, 0.01) is False

    def test_below_correct_within_tolerance(self):
        assert score_calculation(9.995, 10.0, 0.01) is True

    def test_large_answer(self):
        assert score_calculation(125.0, 125.0, 0.5) is True

    def test_large_answer_off_by_tolerance(self):
        assert score_calculation(124.4, 125.0, 0.5) is False
        assert score_calculation(124.5, 125.0, 0.5) is True

    def test_float_precision(self):
        # 500/4 = 125 exactly
        assert score_calculation(125.0, 500/4, 0.1) is True

    def test_drip_rate_rounding(self):
        # gtt/min tolerance is 1.0 (whole drop rounding)
        assert score_calculation(28.0, 27.8, 1.0) is True
        assert score_calculation(27.0, 27.8, 1.0) is True
        assert score_calculation(26.0, 27.8, 1.0) is False
