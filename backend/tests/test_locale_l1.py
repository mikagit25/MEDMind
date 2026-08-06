"""Locale L1 — Jurisdiction profiles and rules: model integrity + API.

Verifies:
- JurisdictionProfile model: create, retrieve, status field
- JurisdictionRule model: create, needs_human default, uniqueness constraint
- GET /admin/jurisdictions — requires admin, returns list
- GET /admin/jurisdictions/{slug} — returns profile with rules
- PATCH /admin/jurisdictions/rules/{id} — enforces source_url when verified
- POST /admin/jurisdictions/{slug}/request-human-review — returns count
"""
from __future__ import annotations

import uuid
import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.models import JurisdictionProfile, JurisdictionRule


# ── Helpers ───────────────────────────────────────────────────────────────────

def _profile(**kw) -> JurisdictionProfile:
    defaults = dict(
        slug="test_sa",
        country="Saudi Arabia",
        regulator="SCFHS",
        exam_slugs=["snle"],
        locale_primary="ar",
        units_system="SI",
        status="unverified",
    )
    defaults.update(kw)
    return JurisdictionProfile(**defaults)


def _rule(profile_slug: str, **kw) -> JurisdictionRule:
    defaults = dict(
        id=uuid.uuid4(),
        profile_slug=profile_slug,
        domain="scope_of_practice",
        rule_key="test_rule_rn_iv",
        statement="RNs may administer IV medications under SCFHS supervision.",
        status="needs_human",
        divergence_from_us=True,
    )
    defaults.update(kw)
    return JurisdictionRule(**defaults)


# ── Unit: model persistence ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_jurisdiction_profile_create(db_session, client):
    p = _profile()
    db_session.add(p)
    await db_session.commit()

    result = await db_session.execute(
        select(JurisdictionProfile).where(JurisdictionProfile.slug == "test_sa")
    )
    fetched = result.scalar_one_or_none()
    assert fetched is not None
    assert fetched.regulator == "SCFHS"
    assert fetched.units_system == "SI"
    assert fetched.status == "unverified"


@pytest.mark.asyncio
async def test_jurisdiction_rule_defaults_needs_human(db_session, client):
    p = _profile()
    db_session.add(p)
    await db_session.commit()

    r = _rule("test_sa")
    db_session.add(r)
    await db_session.commit()

    result = await db_session.execute(
        select(JurisdictionRule).where(JurisdictionRule.id == r.id)
    )
    fetched = result.scalar_one_or_none()
    assert fetched is not None
    assert fetched.status == "needs_human"
    assert fetched.source_url is None


@pytest.mark.asyncio
async def test_jurisdiction_rule_divergence_flag(db_session, client):
    p = _profile()
    db_session.add(p)
    await db_session.commit()

    r = _rule("test_sa", divergence_from_us=True)
    db_session.add(r)
    await db_session.commit()

    result = await db_session.execute(
        select(JurisdictionRule).where(JurisdictionRule.id == r.id)
    )
    fetched = result.scalar_one_or_none()
    assert fetched.divergence_from_us is True


@pytest.mark.asyncio
async def test_jurisdiction_rule_uniqueness(db_session, client):
    """Duplicate profile_slug+domain+rule_key should fail."""
    from sqlalchemy.exc import IntegrityError

    p = _profile()
    db_session.add(p)
    await db_session.commit()

    r1 = _rule("test_sa", id=uuid.uuid4(), rule_key="same_key")
    r2 = _rule("test_sa", id=uuid.uuid4(), rule_key="same_key")
    db_session.add(r1)
    await db_session.commit()

    db_session.add(r2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


# ── API: auth guard ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_jurisdictions_requires_admin(client):
    r = await client.get("/api/v1/admin/jurisdictions")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_jurisdiction_detail_requires_admin(client):
    r = await client.get("/api/v1/admin/jurisdictions/sa")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_patch_jurisdiction_rule_requires_admin(client):
    fake_id = str(uuid.uuid4())
    r = await client.patch(
        f"/api/v1/admin/jurisdictions/rules/{fake_id}",
        json={"status": "verified", "source_url": "https://example.com"},
    )
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_request_human_review_requires_admin(client):
    r = await client.post("/api/v1/admin/jurisdictions/sa/request-human-review")
    assert r.status_code in (401, 403)


# ── API: admin can list profiles ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_jurisdictions_admin_ok(admin_client):
    r = await admin_client.get("/api/v1/admin/jurisdictions")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_get_jurisdiction_detail_404(admin_client):
    r = await admin_client.get("/api/v1/admin/jurisdictions/nonexistent_slug_xyz")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_request_human_review_404_unknown(admin_client):
    r = await admin_client.post("/api/v1/admin/jurisdictions/nonexistent/request-human-review")
    assert r.status_code == 404


# ── API: rule patch enforces source_url for verified ─────────────────────────

@pytest.mark.asyncio
async def test_patch_rule_verified_without_source_url_raises_422(admin_client, db_session):
    p = _profile(slug="patch_test_sa")
    db_session.add(p)
    r = _rule("patch_test_sa", id=uuid.uuid4(), rule_key="patch_rule_key")
    db_session.add(r)
    await db_session.commit()

    resp = await admin_client.patch(
        f"/api/v1/admin/jurisdictions/rules/{r.id}",
        json={"status": "verified"},  # no source_url
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_patch_rule_statement_update(admin_client, db_session):
    p = _profile(slug="patch_stmt_sa")
    db_session.add(p)
    r = _rule("patch_stmt_sa", id=uuid.uuid4(), rule_key="stmt_rule")
    db_session.add(r)
    await db_session.commit()

    new_statement = "Updated regulatory statement for testing."
    resp = await admin_client.patch(
        f"/api/v1/admin/jurisdictions/rules/{r.id}",
        json={"statement": new_statement},
    )
    assert resp.status_code == 200
    data = resp.json()
    # Response is {"ok": True, "rule_id": ..., "status": ...}
    assert data["ok"] is True
    assert data["status"] == "needs_human"


@pytest.mark.asyncio
async def test_patch_rule_patch_nonexistent_404(admin_client):
    resp = await admin_client.patch(
        f"/api/v1/admin/jurisdictions/rules/{uuid.uuid4()}",
        json={"statement": "test"},
    )
    assert resp.status_code == 404
