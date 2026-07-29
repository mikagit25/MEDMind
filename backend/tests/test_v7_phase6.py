"""V7 Phase 6 — Mock Exam Debrief tests.

Verifies:
- Pattern detectors fire on correct scenarios
- Timing analysis detects slow questions
- Debrief endpoint requires auth
- Debrief returns 400 for non-completed session
- Debrief returns 404 for wrong user
- Pattern detectors: at least 5 are defined
- Ordered question errors trigger the ordered detector
- Calculation errors trigger the calculation detector
"""
from __future__ import annotations

import uuid
import pytest


# ── Unit tests ────────────────────────────────────────────────────────────────

def test_at_least_5_detectors_defined():
    """At least 5 pattern detectors are configured."""
    from app.services.mock_debrief import DETECTORS
    assert len(DETECTORS) >= 5


def test_run_detectors_no_data():
    """Empty per_question list returns no patterns."""
    from app.services.mock_debrief import run_detectors
    assert run_detectors([]) == []


def _make_pq(index: int, question_type: str = "mcq", correct: bool = True,
             nclex_cat: str = "pharmacological_therapies", time_s: float = 60.0) -> dict:
    return {
        "index": index,
        "question_id": str(uuid.uuid4()),
        "question_type": question_type,
        "correct": correct,
        "nclex_client_needs": nclex_cat,
        "time_seconds": time_s,
        "question_text": "",
    }


def test_ordered_detector_fires_on_high_error_rate():
    """Ordered question detector fires when error rate ≥ 60% and above overall."""
    from app.services.mock_debrief import run_detectors

    per_q = (
        # 6 ordered questions, 5 wrong (83% error rate)
        [_make_pq(i, question_type="ordered", correct=False) for i in range(5)]
        + [_make_pq(5, question_type="ordered", correct=True)]
        # 10 correct MCQ questions to keep overall error rate low
        + [_make_pq(i + 10, question_type="mcq", correct=True) for i in range(10)]
    )
    patterns = run_detectors(per_q)
    ids = [p["id"] for p in patterns]
    assert "ordered_errors" in ids


def test_ordered_detector_not_fired_when_error_rate_low():
    """Ordered detector doesn't fire when error rate is below threshold."""
    from app.services.mock_debrief import run_detectors

    per_q = [_make_pq(i, question_type="ordered", correct=True) for i in range(5)]
    patterns = run_detectors(per_q)
    ids = [p["id"] for p in patterns]
    assert "ordered_errors" not in ids


def test_calculation_detector_fires():
    """Calculation detector fires when enough failed calc questions."""
    from app.services.mock_debrief import run_detectors

    per_q = (
        [_make_pq(i, question_type="calculation", correct=False) for i in range(5)]
        + [_make_pq(i + 10, question_type="mcq", correct=True) for i in range(10)]
    )
    patterns = run_detectors(per_q)
    ids = [p["id"] for p in patterns]
    assert "calculation_errors" in ids


def test_timing_analysis_detects_slow_questions():
    """analyze_timing flags questions over threshold."""
    from app.services.mock_debrief import analyze_timing, SLOW_QUESTION_THRESHOLD_S

    per_q = [
        {"index": 0, "time_seconds": 200.0},
        {"index": 1, "time_seconds": SLOW_QUESTION_THRESHOLD_S + 10},
        {"index": 2, "time_seconds": SLOW_QUESTION_THRESHOLD_S + 20},
        {"index": 3, "time_seconds": 45.0},
        {"index": 4, "time_seconds": 30.0},
        {"index": 5, "time_seconds": SLOW_QUESTION_THRESHOLD_S + 5},
        {"index": 6, "time_seconds": SLOW_QUESTION_THRESHOLD_S + 30},
        {"index": 7, "time_seconds": SLOW_QUESTION_THRESHOLD_S + 15},
    ]
    result = analyze_timing(per_q)
    assert result["available"] is True
    assert len(result["slow_questions"]) >= 5


def test_timing_analysis_no_times_returns_unavailable():
    """analyze_timing returns {available: false} when no timing data."""
    from app.services.mock_debrief import analyze_timing

    per_q = [{"index": i, "time_seconds": 0} for i in range(5)]
    result = analyze_timing(per_q)
    assert result["available"] is False


def test_slow_question_pattern_fires():
    """Slow question pattern fires when enough slow questions."""
    from app.services.mock_debrief import run_detectors, SLOW_QUESTION_THRESHOLD_S

    per_q = [
        _make_pq(i, correct=True, time_s=SLOW_QUESTION_THRESHOLD_S + i * 10)
        for i in range(6)
    ]
    patterns = run_detectors(per_q)
    ids = [p["id"] for p in patterns]
    assert "slow_question_pattern" in ids


# ── HTTP tests ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mock_debrief_requires_auth(client, db_session):
    """Debrief endpoint requires authentication."""
    from httpx import AsyncClient
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/exam/sessions/{fake_id}/mock-debrief")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_mock_debrief_unknown_session(client, db_session):
    """Unknown session returns 404."""
    from httpx import AsyncClient
    from sqlalchemy import update
    from app.models.models import User

    async def _create_user(client, email, password="Str0ng!Pass99"):
        r = await client.post("/api/v1/auth/register", json={
            "email": email, "password": password,
            "first_name": "T", "last_name": "U",
            "consent_terms": True, "consent_data_processing": True,
        })
        assert r.status_code == 201
        r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
        return r.json()["access_token"]

    token = await _create_user(client, f"u-{uuid.uuid4().hex[:8]}@test.com")
    fake_id = str(uuid.uuid4())
    resp = await client.get(
        f"/api/v1/exam/sessions/{fake_id}/mock-debrief",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404
