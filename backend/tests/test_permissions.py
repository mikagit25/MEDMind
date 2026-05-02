"""E6: Role-based access control — students cannot access admin endpoints."""
import pytest
import pytest_asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _create_user(client, email: str, password: str = "Str0ng!Pass") -> str:
    """Register a user and return their access token."""
    r = await client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "first_name": "Test",
        "last_name": "User",
        "consent_terms": True,
        "consent_data_processing": True,
    })
    assert r.status_code == 201, r.text
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


async def _make_admin(db_session, email: str):
    """Promote a user to admin role directly in the DB."""
    from sqlalchemy import select, update
    from app.models.models import User
    await db_session.execute(
        update(User).where(User.email == email).values(role="admin")
    )
    await db_session.commit()


# ---------------------------------------------------------------------------
# Student cannot access admin routes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_student_cannot_list_users(client):
    """GET /admin/users → 403 for a non-admin user."""
    token = await _create_user(client, "student_perm@test.medmind")
    r = await client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403

@pytest.mark.asyncio
async def test_student_cannot_get_audit_logs(client):
    """GET /admin/audit-logs → 403 for student."""
    token = await _create_user(client, "student_audit@test.medmind")
    r = await client.get("/api/v1/admin/audit-logs", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403

@pytest.mark.asyncio
async def test_student_cannot_generate_module(client):
    """POST /admin/modules/generate → 403 for student."""
    token = await _create_user(client, "student_gen@test.medmind")
    r = await client.post(
        "/api/v1/admin/modules/generate",
        headers={"Authorization": f"Bearer {token}"},
        json={"specialty": "cardiology", "topic": "Hypertension", "level": "intermediate"},
    )
    assert r.status_code == 403

@pytest.mark.asyncio
async def test_unauthenticated_admin_returns_401(client):
    """Admin endpoint without token returns 401."""
    r = await client.get("/api/v1/admin/users")
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Admin CAN access those routes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_can_list_users(client, db_session):
    """GET /admin/users → 200 for an admin user."""
    email = "real_admin@test.medmind"
    token = await _create_user(client, email)
    await _make_admin(db_session, email)

    # Re-login to get a fresh token with the new role
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": "Str0ng!Pass"})
    token = r.json()["access_token"]

    r = await client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    data = r.json()
    # Admin list returns paginated envelope {users: [...], total: N, ...}
    assert "users" in data
    assert isinstance(data["users"], list)


# ---------------------------------------------------------------------------
# GDPR routes require auth (own data only)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_export_data_requires_auth(client):
    """GET /compliance/export-data → 401 without token."""
    r = await client.get("/api/v1/compliance/export-data")
    assert r.status_code == 401

@pytest.mark.asyncio
async def test_delete_account_requires_auth(client):
    """POST /compliance/delete-account → 401 without token."""
    r = await client.post("/api/v1/compliance/delete-account")
    assert r.status_code == 401

@pytest.mark.asyncio
async def test_authenticated_user_can_export_own_data(client):
    """GET /compliance/export-data → 200 with valid token."""
    token = await _create_user(client, "gdpr_export@test.medmind")
    r = await client.get(
        "/api/v1/compliance/export-data",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "user" in data
    assert data["user"]["email"] == "gdpr_export@test.medmind"
