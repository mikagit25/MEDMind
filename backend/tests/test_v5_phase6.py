"""V5 Phase 6 — Certificate tests.

Coverage:
- POST /certificates/issue/{module_id}: auth, module not found, not completed, success, idempotent
- GET  /certificates/my: shape, populated
- GET  /certificates/verify/{code}: valid (with/without name), invalid 404
- GET  /certificates/{id}/download: PDF bytes, content-type, wrong user 404
- PATCH /certificates/{id}/hide-name: toggles, wrong user 404
"""
from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Certificate, Module, UserProgress

pytestmark = pytest.mark.anyio


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _reg(client: AsyncClient, email: str) -> tuple[str, str]:
    r = await client.post("/api/v1/auth/register", json={
        "email": email, "password": "Str0ng!Pass99",
        "first_name": "Cert", "last_name": "Tester",
        "role": "student",
        "consent_terms": True, "consent_data_processing": True,
    })
    assert r.status_code == 201, r.text
    body = r.json()
    return body["access_token"], body["user"]["id"]


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _make_completed_module(db: AsyncSession, user_id: str) -> str:
    """Create a published module + 100% UserProgress; return module_id."""
    mod = Module(
        title=f"Cert Module {uuid.uuid4().hex[:4]}",
        code=f"CERT-{uuid.uuid4().hex[:4]}",
        is_published=True,
        is_fundamental=True,
        duration_hours=2.0,
    )
    db.add(mod)
    await db.flush()

    progress = UserProgress(
        user_id=uuid.UUID(user_id),
        module_id=mod.id,
        completion_percent=100,
        mcq_score=85.0,
        lessons_completed=[],
    )
    db.add(progress)
    await db.commit()
    await db.refresh(mod)
    return str(mod.id)


async def _make_incomplete_module(db: AsyncSession, user_id: str) -> str:
    """Create module with 50% progress and low score — not eligible."""
    mod = Module(
        title=f"Incomplete {uuid.uuid4().hex[:4]}",
        code=f"INC-{uuid.uuid4().hex[:4]}",
        is_published=True,
        is_fundamental=True,
    )
    db.add(mod)
    await db.flush()

    progress = UserProgress(
        user_id=uuid.UUID(user_id),
        module_id=mod.id,
        completion_percent=50,
        mcq_score=40.0,
        lessons_completed=[],
    )
    db.add(progress)
    await db.commit()
    return str(mod.id)


# ── Tests: issue ──────────────────────────────────────────────────────────────

async def test_issue_requires_auth(client: AsyncClient):
    r = await client.post(f"/api/v1/certificates/issue/{uuid.uuid4()}")
    assert r.status_code == 401


async def test_issue_module_not_found(client: AsyncClient, db_session: AsyncSession):
    token, _ = await _reg(client, "cert_404@test.com")
    r = await client.post(f"/api/v1/certificates/issue/{uuid.uuid4()}", headers=_h(token))
    assert r.status_code == 404


async def test_issue_not_completed(client: AsyncClient, db_session: AsyncSession):
    token, uid = await _reg(client, "cert_incomplete@test.com")
    mod_id = await _make_incomplete_module(db_session, uid)
    r = await client.post(f"/api/v1/certificates/issue/{mod_id}", headers=_h(token))
    assert r.status_code == 422


async def test_issue_success(client: AsyncClient, db_session: AsyncSession):
    token, uid = await _reg(client, "cert_ok@test.com")
    mod_id = await _make_completed_module(db_session, uid)
    r = await client.post(f"/api/v1/certificates/issue/{mod_id}", headers=_h(token))
    assert r.status_code == 201
    body = r.json()
    assert body["already_issued"] is False
    assert "verification_code" in body
    assert len(body["verification_code"]) == 24
    assert "id" in body
    assert "issued_at" in body
    assert body["score"] == 85.0
    assert "linkedin_url" in body


async def test_issue_idempotent(client: AsyncClient, db_session: AsyncSession):
    token, uid = await _reg(client, "cert_idem@test.com")
    mod_id = await _make_completed_module(db_session, uid)
    r1 = await client.post(f"/api/v1/certificates/issue/{mod_id}", headers=_h(token))
    r2 = await client.post(f"/api/v1/certificates/issue/{mod_id}", headers=_h(token))
    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r2.json()["already_issued"] is True
    assert r1.json()["verification_code"] == r2.json()["verification_code"]


async def test_issue_via_score_threshold(client: AsyncClient, db_session: AsyncSession):
    """Score ≥ 70% alone is sufficient for cert even if completion < 100%."""
    token, uid = await _reg(client, "cert_score@test.com")
    mod = Module(
        title=f"ScoreMod {uuid.uuid4().hex[:4]}",
        code=f"SC-{uuid.uuid4().hex[:4]}",
        is_published=True,
        is_fundamental=True,
    )
    db_session.add(mod)
    await db_session.flush()
    prog = UserProgress(
        user_id=uuid.UUID(uid),
        module_id=mod.id,
        completion_percent=60,
        mcq_score=75.0,
        lessons_completed=[],
    )
    db_session.add(prog)
    await db_session.commit()
    r = await client.post(f"/api/v1/certificates/issue/{str(mod.id)}", headers=_h(token))
    assert r.status_code == 201


# ── Tests: my list ────────────────────────────────────────────────────────────

async def test_my_requires_auth(client: AsyncClient):
    r = await client.get("/api/v1/certificates/my")
    assert r.status_code == 401


async def test_my_empty(client: AsyncClient, db_session: AsyncSession):
    token, _ = await _reg(client, "cert_myempty@test.com")
    r = await client.get("/api/v1/certificates/my", headers=_h(token))
    assert r.status_code == 200
    assert r.json()["total"] == 0
    assert r.json()["certificates"] == []


async def test_my_populated(client: AsyncClient, db_session: AsyncSession):
    token, uid = await _reg(client, "cert_mypop@test.com")
    mod_id = await _make_completed_module(db_session, uid)
    await client.post(f"/api/v1/certificates/issue/{mod_id}", headers=_h(token))
    r = await client.get("/api/v1/certificates/my", headers=_h(token))
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    c = body["certificates"][0]
    assert c["module_id"] == mod_id
    assert "verification_code" in c
    assert "duration_hours" in c


# ── Tests: verify (public) ────────────────────────────────────────────────────

async def test_verify_invalid_code(client: AsyncClient):
    r = await client.get("/api/v1/certificates/verify/INVALIDCODE000")
    assert r.status_code == 404


async def test_verify_valid_shows_name(client: AsyncClient, db_session: AsyncSession):
    token, uid = await _reg(client, "cert_ver@test.com")
    mod_id = await _make_completed_module(db_session, uid)
    issue_r = await client.post(f"/api/v1/certificates/issue/{mod_id}", headers=_h(token))
    code = issue_r.json()["verification_code"]

    r = await client.get(f"/api/v1/certificates/verify/{code}")
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] is True
    assert body["name"] is not None   # name visible by default
    assert "module_title" in body
    assert "issued_at" in body


async def test_verify_hide_name(client: AsyncClient, db_session: AsyncSession):
    token, uid = await _reg(client, "cert_hide@test.com")
    mod_id = await _make_completed_module(db_session, uid)
    issue_r = await client.post(f"/api/v1/certificates/issue/{mod_id}", headers=_h(token))
    body = issue_r.json()
    code = body["verification_code"]
    cert_id = body["id"]

    # Opt out of name display
    r_hide = await client.patch(f"/api/v1/certificates/{cert_id}/hide-name", headers=_h(token))
    assert r_hide.status_code == 200
    assert r_hide.json()["hide_name"] is True

    # Verify should hide name
    r_ver = await client.get(f"/api/v1/certificates/verify/{code}")
    assert r_ver.json()["name"] is None


# ── Tests: download ───────────────────────────────────────────────────────────

async def test_download_requires_auth(client: AsyncClient):
    r = await client.get(f"/api/v1/certificates/{uuid.uuid4()}/download")
    assert r.status_code == 401


async def test_download_wrong_user_404(client: AsyncClient, db_session: AsyncSession):
    tok_a, uid_a = await _reg(client, "cert_dl_a@test.com")
    tok_b, _ = await _reg(client, "cert_dl_b@test.com")
    mod_id = await _make_completed_module(db_session, uid_a)
    issue_r = await client.post(f"/api/v1/certificates/issue/{mod_id}", headers=_h(tok_a))
    cert_id = issue_r.json()["id"]

    r = await client.get(f"/api/v1/certificates/{cert_id}/download", headers=_h(tok_b))
    assert r.status_code == 404


async def test_download_pdf(client: AsyncClient, db_session: AsyncSession):
    token, uid = await _reg(client, "cert_pdf@test.com")
    mod_id = await _make_completed_module(db_session, uid)
    issue_r = await client.post(f"/api/v1/certificates/issue/{mod_id}", headers=_h(token))
    cert_id = issue_r.json()["id"]

    r = await client.get(f"/api/v1/certificates/{cert_id}/download", headers=_h(token))
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:4] == b"%PDF"   # valid PDF magic bytes
    assert len(r.content) > 1000      # not empty


# ── Tests: hide-name toggle ───────────────────────────────────────────────────

async def test_hide_name_toggle(client: AsyncClient, db_session: AsyncSession):
    token, uid = await _reg(client, "cert_toggle@test.com")
    mod_id = await _make_completed_module(db_session, uid)
    issue_r = await client.post(f"/api/v1/certificates/issue/{mod_id}", headers=_h(token))
    cert_id = issue_r.json()["id"]

    r1 = await client.patch(f"/api/v1/certificates/{cert_id}/hide-name", headers=_h(token))
    assert r1.json()["hide_name"] is True
    r2 = await client.patch(f"/api/v1/certificates/{cert_id}/hide-name", headers=_h(token))
    assert r2.json()["hide_name"] is False


async def test_hide_name_wrong_user(client: AsyncClient, db_session: AsyncSession):
    tok_a, uid_a = await _reg(client, "cert_hn_a@test.com")
    tok_b, _ = await _reg(client, "cert_hn_b@test.com")
    mod_id = await _make_completed_module(db_session, uid_a)
    issue_r = await client.post(f"/api/v1/certificates/issue/{mod_id}", headers=_h(tok_a))
    cert_id = issue_r.json()["id"]

    r = await client.patch(f"/api/v1/certificates/{cert_id}/hide-name", headers=_h(tok_b))
    assert r.status_code == 404
