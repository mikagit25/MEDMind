"""Phase 12: Referral Program tests."""
import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str) -> str:
    await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "Str0ng!Pass99",
        "first_name": "Ref",
        "last_name": "Tester",
        "consent_terms": True,
        "consent_data_processing": True,
    })
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": "Str0ng!Pass99"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Auth guards ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_referral_requires_auth(client: AsyncClient):
    """GET /referral returns 401 without JWT."""
    resp = await client.get("/api/v1/referral")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_apply_referral_requires_auth(client: AsyncClient):
    """POST /referral/apply returns 401 without JWT."""
    resp = await client.post("/api/v1/referral/apply", json={"code": "ABCD1234"})
    assert resp.status_code == 401


# ── GET /referral ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_referral_info_shape(client: AsyncClient):
    """Returns referral code, url, stats."""
    token = await _register_and_login(client, "ref_info@test.medmind")
    resp = await client.get("/api/v1/referral", headers=_h(token))
    assert resp.status_code == 200
    data = resp.json()
    assert "code" in data
    assert len(data["code"]) == 8
    assert data["code"] == data["code"].upper()
    assert "referral_url" in data
    assert data["code"] in data["referral_url"]
    assert "referred_count" in data
    assert data["referred_count"] == 0
    assert "total_days_earned" in data
    assert data["total_days_earned"] == 0
    assert "reward_per_referral" in data
    assert "new_user_bonus" in data


@pytest.mark.asyncio
async def test_referral_code_is_deterministic(client: AsyncClient):
    """Same user always gets the same code."""
    token = await _register_and_login(client, "ref_determ@test.medmind")
    r1 = await client.get("/api/v1/referral", headers=_h(token))
    r2 = await client.get("/api/v1/referral", headers=_h(token))
    assert r1.json()["code"] == r2.json()["code"]


@pytest.mark.asyncio
async def test_different_users_get_different_codes(client: AsyncClient):
    """Two users get distinct codes."""
    t1 = await _register_and_login(client, "ref_u1@test.medmind")
    t2 = await _register_and_login(client, "ref_u2@test.medmind")
    c1 = (await client.get("/api/v1/referral", headers=_h(t1))).json()["code"]
    c2 = (await client.get("/api/v1/referral", headers=_h(t2))).json()["code"]
    assert c1 != c2


# ── POST /referral/apply ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_apply_own_code_returns_400(client: AsyncClient):
    """Applying own code returns 400."""
    token = await _register_and_login(client, "ref_own@test.medmind")
    own_code = (await client.get("/api/v1/referral", headers=_h(token))).json()["code"]
    resp = await client.post("/api/v1/referral/apply", json={"code": own_code}, headers=_h(token))
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_apply_nonexistent_code_returns_404(client: AsyncClient):
    """Applying a valid-format but nonexistent code returns 404."""
    token = await _register_and_login(client, "ref_nocode@test.medmind")
    resp = await client.post("/api/v1/referral/apply", json={"code": "ZZZZZZZZ"}, headers=_h(token))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_apply_invalid_format_returns_400(client: AsyncClient):
    """Applying a code that is not 8 characters returns 400."""
    token = await _register_and_login(client, "ref_fmt@test.medmind")
    resp = await client.post("/api/v1/referral/apply", json={"code": "SHORT"}, headers=_h(token))
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_successful_referral_application(client: AsyncClient):
    """User B can apply user A's code; both receive extended access."""
    token_a = await _register_and_login(client, "ref_giver@test.medmind")
    token_b = await _register_and_login(client, "ref_receiver@test.medmind")
    code_a = (await client.get("/api/v1/referral", headers=_h(token_a))).json()["code"]

    resp = await client.post("/api/v1/referral/apply", json={"code": code_a}, headers=_h(token_b))
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "message" in data

    # Referrer's count should be updated
    info_a = (await client.get("/api/v1/referral", headers=_h(token_a))).json()
    assert info_a["referred_count"] == 1
    assert info_a["total_days_earned"] == info_a["reward_per_referral"]


@pytest.mark.asyncio
async def test_apply_code_twice_returns_400(client: AsyncClient):
    """Applying a second code returns 400."""
    token_a = await _register_and_login(client, "ref_giver2@test.medmind")
    token_b = await _register_and_login(client, "ref_dbl@test.medmind")
    code_a = (await client.get("/api/v1/referral", headers=_h(token_a))).json()["code"]

    await client.post("/api/v1/referral/apply", json={"code": code_a}, headers=_h(token_b))
    resp = await client.post("/api/v1/referral/apply", json={"code": code_a}, headers=_h(token_b))
    assert resp.status_code == 400
