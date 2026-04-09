"""E3: SM-2 spaced-repetition algorithm correctness tests."""
import pytest
from app.api.v1.routes.progress import calculate_sm2


# SM-2 reference constants
MIN_EF = 1.3
DEFAULT_EF = 2.5


class TestSM2Algorithm:
    # -----------------------------------------------------------------------
    # Interval logic
    # -----------------------------------------------------------------------

    def test_quality_below_3_resets_interval_to_1(self):
        """Failed recall (quality < 3) always resets the interval to 1 day."""
        for q in (0, 1, 2):
            _, interval = calculate_sm2(DEFAULT_EF, 6, q)
            assert interval == 1, f"Expected interval=1 for quality={q}"

    def test_first_correct_gives_6_day_interval(self):
        """First successful recall (interval ≤ 1) jumps to a 6-day interval."""
        _, interval = calculate_sm2(DEFAULT_EF, 1, 4)
        assert interval == 6

    def test_subsequent_correct_multiplies_by_ef(self):
        """After the first successful review, interval = round(prev_interval * EF)."""
        ef, interval = calculate_sm2(DEFAULT_EF, 6, 5)
        expected = round(6 * ef)
        # We only check the interval here — ef may have changed
        _, computed_interval = calculate_sm2(DEFAULT_EF, 6, 5)
        assert computed_interval == round(6 * calculate_sm2(DEFAULT_EF, 6, 5)[0])

    def test_interval_grows_over_successive_correct_reviews(self):
        """Successive perfect reviews produce monotonically increasing intervals."""
        ef, interval = DEFAULT_EF, 1
        prev_interval = 0
        for _ in range(5):
            ef, interval = calculate_sm2(ef, interval, 5)  # perfect recall
            assert interval > prev_interval, "Interval should grow with each correct review"
            prev_interval = interval

    # -----------------------------------------------------------------------
    # Ease-factor adjustment
    # -----------------------------------------------------------------------

    def test_perfect_quality_increases_ef(self):
        """Quality 5 (perfect) increases ease factor."""
        ef_before = DEFAULT_EF
        new_ef, _ = calculate_sm2(ef_before, 6, 5)
        assert new_ef > ef_before

    def test_poor_quality_decreases_ef(self):
        """Quality 2 (fail) decreases ease factor."""
        ef_before = DEFAULT_EF
        new_ef, _ = calculate_sm2(ef_before, 6, 2)
        assert new_ef < ef_before

    def test_ef_never_falls_below_minimum(self):
        """EF floor is 1.3 — repeated bad reviews can't drop below it."""
        ef = MIN_EF
        for _ in range(10):
            ef, _ = calculate_sm2(ef, 6, 0)  # worst quality
            assert ef >= MIN_EF, f"EF dropped below minimum: {ef}"

    def test_quality_3_slightly_decreases_ef(self):
        """Quality 3 (bare pass) slightly decreases EF (-0.14 for default EF=2.5).
        The SM-2 formula makes quality 5 the only fully-positive outcome.
        """
        ef_before = DEFAULT_EF
        new_ef, _ = calculate_sm2(ef_before, 6, 3)
        # EF decreases but stays above minimum
        assert new_ef < ef_before
        assert new_ef >= MIN_EF

    # -----------------------------------------------------------------------
    # Return-type / sanity
    # -----------------------------------------------------------------------

    def test_returns_tuple_of_float_and_int(self):
        new_ef, new_interval = calculate_sm2(DEFAULT_EF, 1, 4)
        assert isinstance(new_ef, float)
        assert isinstance(new_interval, int)

    def test_interval_is_always_positive(self):
        """Interval must be at least 1 day for all possible inputs."""
        for ef in (1.3, 2.0, 2.5, 3.0):
            for interval in (1, 6, 30):
                for quality in range(6):
                    _, iv = calculate_sm2(ef, interval, quality)
                    assert iv >= 1, f"Got interval={iv} for quality={quality}"
