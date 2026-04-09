"""E7: GDPR compliance — data export contains all user data; delete anonymises."""
import pytest


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def _register_and_login(client, email: str, password: str = "Str0ng!Pass") -> str:
    r = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "first_name": "GDPR",
        "last_name": "Tester",
        "consent_terms": True,
        "consent_data_processing": True,
    })
    assert r.status_code == 201, r.text
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


# ---------------------------------------------------------------------------
# GDPR Article 20 — Data export
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_export_returns_user_info(client):
    """Export document contains user's own PII fields."""
    email = "export_pii@test.medmind"
    token = await _register_and_login(client, email)

    r = await client.get(
        "/api/v1/compliance/export-data",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["user"]["email"] == email
    assert data["user"]["first_name"] == "GDPR"
    assert data["user"]["last_name"] == "Tester"


@pytest.mark.asyncio
async def test_export_has_all_required_sections(client):
    """Export document contains all GDPR-required top-level sections."""
    token = await _register_and_login(client, "export_sections@test.medmind")
    r = await client.get(
        "/api/v1/compliance/export-data",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()

    required_sections = {"user", "progress", "ai_conversations", "notes", "bookmarks",
                         "achievements", "consents", "export_generated_at"}
    for section in required_sections:
        assert section in data, f"Missing section: {section}"


@pytest.mark.asyncio
async def test_export_empty_lists_for_fresh_user(client):
    """A new user with no activity gets empty lists (not errors) in their export."""
    token = await _register_and_login(client, "export_fresh@test.medmind")
    r = await client.get(
        "/api/v1/compliance/export-data",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["progress"] == []
    assert data["ai_conversations"] == []
    assert data["notes"] == []
    assert data["bookmarks"] == []
    assert data["achievements"] == []


# ---------------------------------------------------------------------------
# GDPR Article 17 — Right to erasure
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_account_anonymises_pii(client, db_session):
    """After delete-account the user's PII is replaced with 'Deleted User'."""
    from sqlalchemy import select
    from app.models.models import User

    email = "delete_me@test.medmind"
    token = await _register_and_login(client, email)

    r = await client.post(
        "/api/v1/compliance/delete-account",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200

    # Verify in DB that PII is gone
    result = await db_session.execute(select(User).where(User.first_name == "Deleted"))
    deleted_users = result.scalars().all()
    assert len(deleted_users) >= 1

    deleted = deleted_users[0]
    assert "anonymised" in deleted.email
    assert deleted.first_name == "Deleted"
    assert deleted.last_name == "User"
    assert deleted.password_hash is None
    assert deleted.is_active is False


@pytest.mark.asyncio
async def test_deleted_account_cannot_login(client):
    """After account deletion, the user can no longer log in."""
    email = "deleted_login@test.medmind"
    password = "Str0ng!Pass"
    token = await _register_and_login(client, email, password)

    r = await client.post(
        "/api/v1/compliance/delete-account",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200

    # Attempt to login with the original credentials
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code in (401, 400), f"Expected login to fail; got {r.status_code}"


# ---------------------------------------------------------------------------
# Consent management
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_consent_update_and_retrieve(client):
    """Updating a consent type is persisted and returned on GET."""
    token = await _register_and_login(client, "consent_test@test.medmind")
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post(
        "/api/v1/compliance/consents/analytics",
        headers=headers,
        params={"granted": "true"},
    )
    assert r.status_code == 200
    assert r.json()["granted"] is True

    r = await client.get("/api/v1/compliance/consents", headers=headers)
    assert r.status_code == 200
    consents = r.json()
    analytics = next((c for c in consents if c["consent_type"] == "analytics"), None)
    assert analytics is not None
    assert analytics["granted"] is True


@pytest.mark.asyncio
async def test_consent_invalid_type_returns_400(client):
    """Unknown consent type returns 400 Bad Request."""
    token = await _register_and_login(client, "consent_bad@test.medmind")
    r = await client.post(
        "/api/v1/compliance/consents/nonexistent_type",
        headers={"Authorization": f"Bearer {token}"},
        params={"granted": "true"},
    )
    assert r.status_code == 400
