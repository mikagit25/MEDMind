"""Phase 11: Personalized Exam Study Planner tests."""
import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str) -> str:
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Str0ng!Pass99",
        "first_name": "Exam",
        "last_name": "Planner",
        "consent_terms": True,
        "consent_data_processing": True,
    })
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": "Str0ng!Pass99"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _future_date(days: int = 90) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


FAKE_PLAN_JSON = """{
  "weeks": [
    {
      "week": 1,
      "theme": "Cardiology Foundations",
      "modules": [{"module_id": "", "title": "Cardiology", "sessions": 2}],
      "daily_hours": 2.0,
      "milestone": "Understand basic cardiac physiology and ECG interpretation"
    },
    {
      "week": 2,
      "theme": "Pulmonology & Critical Care",
      "modules": [{"module_id": "", "title": "Pulmonology", "sessions": 3}],
      "daily_hours": 2.0,
      "milestone": "Master respiratory failure management"
    }
  ],
  "tip": "Use active recall over passive reading — self-testing is 3x more effective."
}"""


# ── Auth guard ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_exam_plan_requires_auth(client: AsyncClient):
    """Returns 401 without JWT."""
    resp = await client.post("/api/v1/student/exam-prep/plan", json={
        "exam_type": "usmle_step2",
        "exam_date": _future_date(90),
        "daily_hours": 2,
    })
    assert resp.status_code == 401


# ── Validation ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_exam_plan_past_date_returns_422(client: AsyncClient):
    """Past exam_date returns 422."""
    token = await _register_and_login(client, "plan_past@test.medmind")
    with patch("app.services.ai_router.call_claude_structured", new=AsyncMock(return_value=(FAKE_PLAN_JSON, "claude-haiku-4-5-20251001"))):
        resp = await client.post("/api/v1/student/exam-prep/plan", json={
            "exam_type": "usmle_step2",
            "exam_date": "2020-01-01",
            "daily_hours": 2,
        }, headers=_h(token))
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_exam_plan_invalid_date_format(client: AsyncClient):
    """Invalid date format returns 422."""
    token = await _register_and_login(client, "plan_fmt@test.medmind")
    resp = await client.post("/api/v1/student/exam-prep/plan", json={
        "exam_type": "usmle_step2",
        "exam_date": "not-a-date",
        "daily_hours": 2,
    }, headers=_h(token))
    assert resp.status_code == 422


# ── Happy path ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_exam_plan_returns_plan(client: AsyncClient):
    """Valid request returns an exam plan with weeks."""
    token = await _register_and_login(client, "plan_happy@test.medmind")
    with patch("app.services.ai_router.call_claude_structured", new=AsyncMock(return_value=(FAKE_PLAN_JSON, "claude-haiku-4-5-20251001"))):
        resp = await client.post("/api/v1/student/exam-prep/plan", json={
            "exam_type": "usmle_step2",
            "exam_date": _future_date(90),
            "daily_hours": 2,
        }, headers=_h(token))

    assert resp.status_code == 200
    data = resp.json()
    assert data["exam_type"] == "usmle_step2"
    assert data["exam_label"] == "USMLE Step 2 CK"
    assert data["days_remaining"] > 0
    assert isinstance(data["weeks"], list)
    assert len(data["weeks"]) >= 1
    assert "tip" in data


@pytest.mark.asyncio
async def test_exam_plan_week_structure(client: AsyncClient):
    """Each week has week number, theme, modules, daily_hours, milestone."""
    token = await _register_and_login(client, "plan_struct@test.medmind")
    with patch("app.services.ai_router.call_claude_structured", new=AsyncMock(return_value=(FAKE_PLAN_JSON, "claude-haiku-4-5-20251001"))):
        resp = await client.post("/api/v1/student/exam-prep/plan", json={
            "exam_type": "nclex_rn",
            "exam_date": _future_date(60),
            "daily_hours": 3,
        }, headers=_h(token))

    assert resp.status_code == 200
    for week in resp.json()["weeks"]:
        assert "week" in week
        assert "theme" in week
        assert "modules" in week
        assert "daily_hours" in week
        assert "milestone" in week


@pytest.mark.asyncio
async def test_exam_plan_all_exam_types(client: AsyncClient):
    """All supported exam types are accepted."""
    token = await _register_and_login(client, "plan_types@test.medmind")
    exam_types = ["usmle_step1", "usmle_step2", "usmle_step3", "nclex_rn", "nclex_pn", "ukmla", "plab", "custom"]
    for exam_type in exam_types:
        with patch("app.services.ai_router.call_claude_structured", new=AsyncMock(return_value=(FAKE_PLAN_JSON, "claude-haiku-4-5-20251001"))):
            resp = await client.post("/api/v1/student/exam-prep/plan", json={
                "exam_type": exam_type,
                "exam_date": _future_date(120),
                "daily_hours": 2,
            }, headers=_h(token))
        assert resp.status_code == 200, f"Failed for exam_type={exam_type}: {resp.text}"


@pytest.mark.asyncio
async def test_exam_plan_days_remaining(client: AsyncClient):
    """days_remaining reflects the distance to exam_date."""
    token = await _register_and_login(client, "plan_days@test.medmind")
    target_days = 120
    with patch("app.services.ai_router.call_claude_structured", new=AsyncMock(return_value=(FAKE_PLAN_JSON, "claude-haiku-4-5-20251001"))):
        resp = await client.post("/api/v1/student/exam-prep/plan", json={
            "exam_type": "usmle_step1",
            "exam_date": _future_date(target_days),
            "daily_hours": 2,
        }, headers=_h(token))
    assert resp.status_code == 200
    # Allow ±1 day for timing
    assert abs(resp.json()["days_remaining"] - target_days) <= 1
