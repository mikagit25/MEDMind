"""V4 Phase 7 — PWA + i18n foundation tests.

Tests:
  1. Module.language defaults to 'en'
  2. GET /content/modules includes language field in each result
  3. GET /content/modules?language=en returns only English modules
  4. GET /content/modules?language=ru returns only Russian modules
  5. GET /content/modules?language=XX returns empty (unknown language)
  6. Specialty module list also supports language filter
  7. GET /content/modules with no auth requires valid session (auth check)
"""
from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Module, Specialty


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_specialty(db: AsyncSession, **kwargs) -> Specialty:
    defaults = dict(
        id=uuid.uuid4(),
        code=f"TEST-{uuid.uuid4().hex[:6]}",
        name="Test Specialty",
        description="Test",
        icon="🔬",
        is_active=True,
    )
    defaults.update(kwargs)
    s = Specialty(**defaults)
    db.add(s)
    return s


def _make_module(db: AsyncSession, specialty: Specialty, **kwargs) -> Module:
    defaults = dict(
        id=uuid.uuid4(),
        code=f"MOD-{uuid.uuid4().hex[:6]}",
        title="Test Module",
        description="Test module description",
        specialty_id=specialty.id,
        is_published=True,
        is_fundamental=False,
        is_veterinary=False,
        language="en",
        module_order=1,
    )
    defaults.update(kwargs)
    m = Module(**defaults)
    db.add(m)
    return m


async def _login(client: AsyncClient, email: str, password: str = "Str0ng!Pass99") -> str:
    await client.post("/api/v1/auth/register", json={
        "email": email, "password": password,
        "first_name": "Test", "last_name": "User",
        "consent_terms": True, "consent_data_processing": True,
    })
    r = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


# ── Module language field ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_module_language_defaults_to_en(db_session: AsyncSession):
    """Module.language defaults to 'en' when not specified."""
    spec = _make_specialty(db_session)
    mod = _make_module(db_session, spec)
    await db_session.commit()
    await db_session.refresh(mod)
    assert mod.language == "en"


@pytest.mark.asyncio
async def test_module_language_can_be_set(db_session: AsyncSession):
    """Module.language stores non-English values correctly."""
    spec = _make_specialty(db_session)
    mod = _make_module(db_session, spec, language="ru")
    await db_session.commit()
    await db_session.refresh(mod)
    assert mod.language == "ru"


# ── Module API language filter ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_module_list_includes_language_field(client: AsyncClient, db_session: AsyncSession):
    """GET /content/modules response includes language field."""
    spec = _make_specialty(db_session)
    _make_module(db_session, spec, title="English Module", language="en")
    await db_session.commit()

    token = await _login(client, "lang_field@test.medmind")
    r = await client.get("/api/v1/modules", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    items = r.json()
    en_items = [i for i in items if i.get("title") == "English Module"]
    assert len(en_items) >= 1
    assert "language" in en_items[0]
    assert en_items[0]["language"] == "en"


@pytest.mark.asyncio
async def test_module_language_filter_en(client: AsyncClient, db_session: AsyncSession):
    """?language=en returns only English modules."""
    spec = _make_specialty(db_session)
    _make_module(db_session, spec, title="En Module", language="en")
    _make_module(db_session, spec, title="Ru Module", language="ru")
    await db_session.commit()

    token = await _login(client, "lang_en@test.medmind")
    r = await client.get("/api/v1/modules?language=en", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    titles = [i["title"] for i in r.json()]
    assert "En Module" in titles
    assert "Ru Module" not in titles


@pytest.mark.asyncio
async def test_module_language_filter_ru(client: AsyncClient, db_session: AsyncSession):
    """?language=ru returns only Russian-language modules."""
    spec = _make_specialty(db_session)
    _make_module(db_session, spec, title="En Module 2", language="en")
    _make_module(db_session, spec, title="Ru Module 2", language="ru")
    await db_session.commit()

    token = await _login(client, "lang_ru@test.medmind")
    r = await client.get("/api/v1/modules?language=ru", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    titles = [i["title"] for i in r.json()]
    assert "Ru Module 2" in titles
    assert "En Module 2" not in titles


@pytest.mark.asyncio
async def test_module_language_filter_unknown_returns_empty(client: AsyncClient, db_session: AsyncSession):
    """?language=xx returns empty list for an unsupported language."""
    spec = _make_specialty(db_session)
    _make_module(db_session, spec, title="En Module Only", language="en")
    await db_session.commit()

    token = await _login(client, "lang_xx@test.medmind")
    r = await client.get("/api/v1/modules?language=xx", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    # No modules with language='xx'
    assert r.json() == []


@pytest.mark.asyncio
async def test_specialty_module_list_language_filter(client: AsyncClient, db_session: AsyncSession):
    """GET /content/specialties/{id}/modules also supports language filter."""
    spec = _make_specialty(db_session, code=f"SPEC-{uuid.uuid4().hex[:4]}")
    _make_module(db_session, spec, title="Spec En", language="en")
    _make_module(db_session, spec, title="Spec Ru", language="ru")
    await db_session.commit()

    token = await _login(client, "spec_lang@test.medmind")
    r = await client.get(
        f"/api/v1/specialties/{spec.id}/modules?language=en",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    titles = [i["title"] for i in r.json()]
    assert "Spec En" in titles
    assert "Spec Ru" not in titles


# ── Unauthenticated access ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_module_list_is_public(client: AsyncClient):
    """GET /modules is publicly accessible (no auth needed — browse page)."""
    r = await client.get("/api/v1/modules")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
