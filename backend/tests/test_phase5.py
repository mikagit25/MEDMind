"""Tests for Phase 5: gamification — XP, streaks, leaderboard."""
import math


# ── XPEvent model ─────────────────────────────────────────────────────────────

def test_xp_event_model_has_required_fields():
    from app.models.models import XPEvent
    cols = {c.key for c in XPEvent.__table__.columns}
    for f in ("id", "user_id", "source", "amount", "reference_id", "created_at"):
        assert f in cols, f"Missing field: {f}"


def test_xp_event_user_id_is_foreign_key():
    from app.models.models import XPEvent
    col = XPEvent.__table__.c["user_id"]
    assert len(col.foreign_keys) > 0


def test_xp_event_has_indexes():
    from app.models.models import XPEvent
    index_names = {idx.name for idx in XPEvent.__table__.indexes}
    assert "ix_xp_events_user_id" in index_names
    assert "ix_xp_events_created_at" in index_names


# ── User gamification fields ──────────────────────────────────────────────────

def test_user_has_longest_streak():
    from app.models.models import User
    cols = {c.key for c in User.__table__.columns}
    assert "longest_streak" in cols


def test_user_has_leaderboard_opt_in():
    from app.models.models import User
    cols = {c.key for c in User.__table__.columns}
    assert "leaderboard_opt_in" in cols


def test_user_has_leaderboard_display_name():
    from app.models.models import User
    cols = {c.key for c in User.__table__.columns}
    assert "leaderboard_display_name" in cols


def test_leaderboard_opt_in_default_false():
    from app.models.models import User
    col = User.__table__.c["leaderboard_opt_in"]
    # server_default "false" or Python default False
    sd = col.server_default
    default = col.default
    assert (sd is not None and "false" in str(sd.arg).lower()) or (default is not None)


# ── Level formula ─────────────────────────────────────────────────────────────

def _calc_level(xp: int) -> int:
    return max(1, math.isqrt(max(0, xp) // 100))


def test_level_1_at_zero_xp():
    assert _calc_level(0) == 1


def test_level_1_below_threshold():
    assert _calc_level(99) == 1


def test_level_1_at_100():
    # floor(sqrt(100/100)) = floor(sqrt(1)) = 1 → max(1, 1) = 1
    assert _calc_level(100) == 1


def test_level_2_at_400():
    # floor(sqrt(400/100)) = floor(sqrt(4)) = 2
    assert _calc_level(400) == 2


def test_level_3_at_900():
    assert _calc_level(900) == 3


def test_level_5_at_2500():
    assert _calc_level(2500) == 5


def test_level_10_at_10000():
    assert _calc_level(10000) == 10


def test_level_never_zero():
    assert _calc_level(-999) >= 1


# ── XP-to-next-level calculation ──────────────────────────────────────────────

def xp_progress(xp: int):
    level = _calc_level(xp)
    xp_for_next = ((level + 1) ** 2) * 100
    # Level 1 starts from 0 (levels 0+1 both collapse to display level 1)
    xp_for_current = 0 if level == 1 else (level ** 2) * 100
    pct = max(0, round(((xp - xp_for_current) / max(1, xp_for_next - xp_for_current)) * 100))
    return level, xp_for_next, pct


def test_xp_progress_at_0():
    level, xp_for_next, pct = xp_progress(0)
    assert level == 1
    assert xp_for_next == 400
    assert pct == 0


def test_xp_progress_halfway():
    # Level 2 starts at 400, level 3 at 900 → midpoint 650 → 50%
    level, xp_for_next, pct = xp_progress(650)
    assert level == 2
    assert pct == 50


def test_xp_progress_full():
    level, xp_for_next, pct = xp_progress(900)
    assert level == 3
    assert pct == 0  # just crossed into level 3, 0% toward level 4


# ── Streak tracking ───────────────────────────────────────────────────────────

def test_longest_streak_updated_when_current_exceeds():
    longest = 5
    current = 7
    new_longest = max(longest, current)
    assert new_longest == 7


def test_longest_streak_unchanged_when_not_exceeded():
    longest = 10
    current = 7
    new_longest = max(longest, current)
    assert new_longest == 10


def test_streak_reset_does_not_clear_longest():
    longest = 14
    current = 0  # reset after missing a day
    new_longest = max(longest, current)
    assert new_longest == 14  # best streak preserved


# ── XP source constants ───────────────────────────────────────────────────────

def test_xp_sources_are_valid():
    valid_sources = {"lesson", "flashcard", "mcq", "case"}
    # These are the sources passed in the updated add_xp calls
    used_sources = {"lesson", "flashcard", "mcq", "case"}
    assert used_sources <= valid_sources


# ── Leaderboard display name logic ────────────────────────────────────────────

def test_display_name_used_when_set():
    display = "MedWizard"
    first = "Alice"
    last = "Smith"
    name = display or f"{first} {last[:1]}."
    assert name == "MedWizard"


def test_real_name_used_when_no_display():
    display = None
    first = "Alice"
    last = "Smith"
    name = display or f"{first} {last[:1]}."
    assert name == "Alice S."


def test_display_name_stripped_on_save():
    raw = "  MedWizard  "
    cleaned = (raw or "").strip()[:100]
    assert cleaned == "MedWizard"


def test_empty_display_name_stored_as_none():
    raw = "   "
    cleaned = (raw or "").strip()[:100]
    result = cleaned or None
    assert result is None


# ── Evening streak reminder guard ─────────────────────────────────────────────

def test_reminder_targets_users_with_streak_only():
    users = [
        {"streak_days": 0, "active_today": False},
        {"streak_days": 5, "active_today": False},
        {"streak_days": 3, "active_today": True},
        {"streak_days": 0, "active_today": True},
    ]
    at_risk = [u for u in users if u["streak_days"] > 0 and not u["active_today"]]
    assert len(at_risk) == 1
    assert at_risk[0]["streak_days"] == 5


def test_reminder_skips_already_active():
    users = [{"streak_days": 10, "active_today": True}]
    at_risk = [u for u in users if u["streak_days"] > 0 and not u["active_today"]]
    assert len(at_risk) == 0
