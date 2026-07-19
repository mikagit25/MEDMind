"""Deterministic study plan generator for NCLEX/exam prep.

Rules (no AI):
- 15 min/day → 10 questions/session  ("practice")
- 30 min/day → 20 questions/session  ("practice")
- 60 min/day → 40 questions/session  ("practice")
- Mock exams at exam-21d, exam-14d, exam-4d             ("mock_exam")
- Rest day at exam-1d                                    ("rest")
- Review sessions on Sundays (if not already a mock)    ("review")
- Everything else is "practice"
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from typing import Any, List


_QUESTIONS_BY_MINUTES = {15: 10, 30: 20, 60: 40}
_MOCK_OFFSETS = {21, 14, 4}   # days before exam


def _questions_for_minutes(minutes: int) -> int:
    return _QUESTIONS_BY_MINUTES.get(minutes, max(10, minutes // 3))


def generate_plan(
    exam_date: date,
    daily_minutes: int,
    start_date: date | None = None,
) -> List[dict[str, Any]]:
    """Return a list of task dicts, one per calendar day from start_date to exam_date (inclusive).

    Each dict:
        date        : "YYYY-MM-DD"
        task_type   : "practice" | "mock_exam" | "review" | "rest"
        questions   : int (0 for rest)
        day_number  : 1-based index from start
        days_to_exam: calendar days remaining until exam
    """
    today = start_date or date.today()
    if exam_date <= today:
        return []

    days: List[dict[str, Any]] = []
    current = today
    day_number = 1

    while current <= exam_date:
        days_to_exam = (exam_date - current).days

        if days_to_exam == 0:
            # Exam day itself — not a study day
            days.append({
                "date": current.isoformat(),
                "task_type": "exam_day",
                "questions": 0,
                "day_number": day_number,
                "days_to_exam": 0,
            })
        elif days_to_exam == 1:
            days.append({
                "date": current.isoformat(),
                "task_type": "rest",
                "questions": 0,
                "day_number": day_number,
                "days_to_exam": days_to_exam,
            })
        elif days_to_exam in _MOCK_OFFSETS:
            days.append({
                "date": current.isoformat(),
                "task_type": "mock_exam",
                "questions": 75,
                "day_number": day_number,
                "days_to_exam": days_to_exam,
            })
        elif current.weekday() == 6:  # Sunday
            days.append({
                "date": current.isoformat(),
                "task_type": "review",
                "questions": _questions_for_minutes(daily_minutes) // 2,
                "day_number": day_number,
                "days_to_exam": days_to_exam,
            })
        else:
            days.append({
                "date": current.isoformat(),
                "task_type": "practice",
                "questions": _questions_for_minutes(daily_minutes),
                "day_number": day_number,
                "days_to_exam": days_to_exam,
            })

        current += timedelta(days=1)
        day_number += 1

    return days


def get_today_task(plan: List[dict]) -> dict | None:
    today_str = date.today().isoformat()
    for task in plan:
        if task["date"] == today_str:
            return task
    return None


def get_week_tasks(plan: List[dict], reference_date: date | None = None) -> List[dict]:
    """Return the 7-day window starting from reference_date (default: today)."""
    ref = reference_date or date.today()
    end = ref + timedelta(days=6)
    return [
        t for t in plan
        if ref.isoformat() <= t["date"] <= end.isoformat()
    ]


def compute_progress(
    plan: List[dict],
    completed_dates: List[str],
) -> dict[str, Any]:
    """Compute plan progress stats."""
    total = len([t for t in plan if t["task_type"] not in ("exam_day",)])
    done = len([d for d in completed_dates if any(t["date"] == d for t in plan)])
    pct = round(done / total * 100) if total > 0 else 0
    return {
        "total_days": total,
        "completed_days": done,
        "completion_pct": pct,
    }
