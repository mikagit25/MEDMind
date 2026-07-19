"""Unit tests for V6 Phase 4 — Study Plan generator (deterministic rules, no AI)."""
from datetime import date, timedelta
import pytest

from app.services.study_planner import (
    generate_plan,
    get_today_task,
    get_week_tasks,
    compute_progress,
)


def _exam_in(days: int) -> date:
    return date.today() + timedelta(days=days)


def _start() -> date:
    return date.today()


# ── generate_plan ──────────────────────────────────────────────────────────────

def test_plan_includes_exam_day():
    exam = _exam_in(30)
    plan = generate_plan(exam, 30, _start())
    exam_tasks = [t for t in plan if t["task_type"] == "exam_day"]
    assert len(exam_tasks) == 1
    assert exam_tasks[0]["date"] == exam.isoformat()


def test_rest_day_at_exam_minus_1():
    exam = _exam_in(30)
    plan = generate_plan(exam, 30, _start())
    rest_date = (exam - timedelta(days=1)).isoformat()
    rest_tasks = [t for t in plan if t["date"] == rest_date]
    assert len(rest_tasks) == 1
    assert rest_tasks[0]["task_type"] == "rest"
    assert rest_tasks[0]["questions"] == 0


def test_mock_exams_at_minus_21_14_4():
    exam = _exam_in(30)
    plan = generate_plan(exam, 30, _start())
    mock_dates = {(exam - timedelta(days=d)).isoformat() for d in (21, 14, 4)}
    actual_mocks = {t["date"] for t in plan if t["task_type"] == "mock_exam"}
    # All expected mock dates that fall within the plan window should be mocks
    for d in mock_dates:
        if d >= _start().isoformat():
            assert d in actual_mocks, f"Expected mock exam on {d}"


def test_mock_exam_has_75_questions():
    exam = _exam_in(30)
    plan = generate_plan(exam, 30, _start())
    for t in plan:
        if t["task_type"] == "mock_exam":
            assert t["questions"] == 75


def test_practice_questions_by_minutes():
    exam = _exam_in(60)
    for minutes, expected_q in [(15, 10), (30, 20), (60, 40)]:
        plan = generate_plan(exam, minutes, _start())
        practice = [t for t in plan if t["task_type"] == "practice"]
        assert len(practice) > 0
        for t in practice:
            assert t["questions"] == expected_q, \
                f"Expected {expected_q}q for {minutes}min, got {t['questions']}"


def test_review_day_on_sunday():
    # Find a Sunday within the next 60 days
    exam = _exam_in(60)
    plan = generate_plan(exam, 30, _start())
    for t in plan:
        d = date.fromisoformat(t["date"])
        if d.weekday() == 6:  # Sunday
            # Unless it's a mock/rest/exam day, should be review
            if t["task_type"] not in ("mock_exam", "rest", "exam_day"):
                assert t["task_type"] == "review"


def test_plan_length_matches_date_range():
    exam = _exam_in(14)
    plan = generate_plan(exam, 30, _start())
    expected = 15  # today through exam_day inclusive
    assert len(plan) == expected


def test_empty_plan_if_exam_in_past():
    exam = date.today() - timedelta(days=1)
    plan = generate_plan(exam, 30, _start())
    assert plan == []


def test_empty_plan_if_exam_today():
    plan = generate_plan(date.today(), 30, _start())
    assert plan == []


# ── get_today_task ─────────────────────────────────────────────────────────────

def test_get_today_task_finds_today():
    exam = _exam_in(30)
    plan = generate_plan(exam, 30, _start())
    task = get_today_task(plan)
    assert task is not None
    assert task["date"] == date.today().isoformat()


# ── get_week_tasks ─────────────────────────────────────────────────────────────

def test_week_tasks_returns_7_days():
    exam = _exam_in(30)
    plan = generate_plan(exam, 30, _start())
    week = get_week_tasks(plan)
    assert len(week) == 7


# ── compute_progress ───────────────────────────────────────────────────────────

def test_progress_zero_initially():
    exam = _exam_in(30)
    plan = generate_plan(exam, 30, _start())
    prog = compute_progress(plan, [])
    assert prog["completed_days"] == 0
    assert prog["completion_pct"] == 0


def test_progress_100_when_all_done():
    exam = _exam_in(3)
    plan = generate_plan(exam, 30, _start())
    all_dates = [t["date"] for t in plan if t["task_type"] != "exam_day"]
    prog = compute_progress(plan, all_dates)
    assert prog["completion_pct"] == 100
