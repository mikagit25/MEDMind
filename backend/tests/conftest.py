"""Shared pytest fixtures for MedMind backend tests."""
import asyncio
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# Use SQLite in-memory for tests — no Postgres needed
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-ci-only-32chars!!")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-for-ci-only")

# ── SQLite compatibility: remap Postgres-only types to JSON/TEXT ──────────────
# Must happen before any model imports so the compilers are registered first.
import json as _json
import sqlite3 as _sqlite3
from sqlalchemy.ext.compiler import compiles  # noqa: E402
from sqlalchemy.dialects.postgresql import ARRAY, JSONB  # noqa: E402
from sqlalchemy.dialects.postgresql import UUID as PG_UUID  # noqa: E402

# Register global adapters so SQLite can bind Python list/dict values (used by
# JSONB/ARRAY columns). Without these, INSERT/UPDATE raises ProgrammingError:
# "type 'list' is not supported".
_sqlite3.register_adapter(list, _json.dumps)
_sqlite3.register_adapter(dict, _json.dumps)


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(element, compiler, **kw):
    return "JSON"


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"


@compiles(PG_UUID, "sqlite")
def _compile_uuid_sqlite(element, compiler, **kw):
    return "VARCHAR(36)"


from app.main import app  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.models import models  # noqa: F401,E402 — register all models

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


# ---------------------------------------------------------------------------
# Fake Redis — avoids real network calls in tests
# ---------------------------------------------------------------------------

class _FakePipeline:
    def __init__(self, store: dict):
        self._store = store
        self._ops: list = []

    async def incr(self, key: str):
        self._ops.append(("incr", key))
        return self

    async def expire(self, key: str, seconds: int):
        self._ops.append(("expire", key, seconds))
        return self

    async def execute(self):
        results = []
        for op in self._ops:
            if op[0] == "incr":
                self._store[op[1]] = int(self._store.get(op[1], 0)) + 1
                results.append(self._store[op[1]])
            elif op[0] == "expire":
                results.append(True)
        return results


class FakeRedis:
    """Minimal in-memory Redis stub for tests."""

    def __init__(self):
        self._store: dict = {}

    async def get(self, key: str):
        return self._store.get(key)

    async def set(self, key: str, value, ex: int = None):
        self._store[key] = str(value)

    async def setex(self, key: str, seconds: int, value):
        self._store[key] = str(value)

    async def getdel(self, key: str):
        return self._store.pop(key, None)

    async def delete(self, key: str):
        self._store.pop(key, None)

    async def incr(self, key: str):
        self._store[key] = int(self._store.get(key, 0)) + 1
        return self._store[key]

    async def decr(self, key: str):
        self._store[key] = int(self._store.get(key, 0)) - 1
        return self._store[key]

    async def expire(self, key: str, seconds: int):
        return True

    def pipeline(self):
        return _FakePipeline(self._store)

    async def aclose(self):
        pass


# ---------------------------------------------------------------------------
# Fixtures — all function-scoped so each test gets a clean DB + event loop
# ---------------------------------------------------------------------------

@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def fake_redis():
    """Shared in-memory Redis stub for a single test."""
    return FakeRedis()


@pytest.fixture(autouse=True)
def _patch_all_redis(monkeypatch, fake_redis):
    """Globally replace every get_redis reference with FakeRedis for all tests.
    Also disable APScheduler so it doesn't acquire event-loop state across tests.
    """
    import app.core.redis_client as _rc
    import app.api.v1.routes.ai as _ai
    import app.api.v1.routes.auth as _auth
    import app.api.v1.routes.public_content as _pub
    import app.api.v1.routes.symptoms as _sym
    import app.api.v1.routes.product_analytics as _pa
    import app.core.cache as _cache
    import app.core.feature_flags as _ff
    import app.core.freemium as _freemium
    import app.services.scheduler as _sched

    _f = fake_redis

    async def _fake_get_redis():
        return _f

    monkeypatch.setattr(_rc, "get_redis", _fake_get_redis)
    monkeypatch.setattr(_rc, "_redis_pool", None)
    monkeypatch.setattr(_ai, "get_redis", _fake_get_redis)
    monkeypatch.setattr(_auth, "get_redis", _fake_get_redis)
    monkeypatch.setattr(_pub, "get_redis", _fake_get_redis)
    monkeypatch.setattr(_sym, "get_redis", _fake_get_redis)
    monkeypatch.setattr(_pa, "get_redis", _fake_get_redis)
    monkeypatch.setattr(_cache, "get_redis", _fake_get_redis)
    monkeypatch.setattr(_ff, "get_redis", _fake_get_redis)
    monkeypatch.setattr(_freemium, "get_redis", _fake_get_redis)
    # Disable scheduler — it binds to the event loop and breaks across tests
    monkeypatch.setattr(_sched, "start_scheduler", lambda: None)
    monkeypatch.setattr(_sched, "stop_scheduler", lambda: None)


def _register_sqlite_functions(dbapi_conn, _rec):
    """Register PostgreSQL-compatible functions on SQLite connections used in tests."""
    import datetime as _dt

    def date_trunc(part: str, val: str) -> str | None:
        if val is None:
            return None
        try:
            d = _dt.datetime.fromisoformat(str(val))
            if part == "week":
                start = d - _dt.timedelta(days=d.weekday())
                return start.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            if part == "day":
                return d.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
            if part == "month":
                return d.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
            return val
        except Exception:
            return val

    dbapi_conn.create_function("date_trunc", 2, date_trunc)


@pytest_asyncio.fixture
async def engine():
    from sqlalchemy import event as _sa_event

    eng = create_async_engine(
        TEST_DB_URL, echo=False,
        connect_args={"detect_types": _sqlite3.PARSE_DECLTYPES | _sqlite3.PARSE_COLNAMES},
    )
    _sa_event.listen(eng.sync_engine, "connect", _register_sqlite_functions)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine):
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(engine):
    """HTTP test client with in-memory DB. Redis already patched by _patch_all_redis."""
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin_client(engine):
    """HTTP test client authenticated as an admin user."""
    from sqlalchemy import update as _upd

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Register + login
        email = f"admin_fixture_{id(ac)}@test.com"
        r = await ac.post("/api/v1/auth/register", json={
            "email": email, "password": "Admin!Pass99",
            "first_name": "Admin", "last_name": "Test",
            "consent_terms": True, "consent_data_processing": True,
        })
        assert r.status_code == 201, r.text
        r = await ac.post("/api/v1/auth/login", json={"email": email, "password": "Admin!Pass99"})
        token = r.json()["access_token"]

        # Elevate to admin via DB
        me = await ac.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        from app.models.models import User as _User
        import uuid as _uuid
        user_id = _uuid.UUID(me.json()["id"])
        async with session_factory() as session:
            await session.execute(_upd(_User).where(_User.id == user_id).values(role="admin"))
            await session.commit()

        ac.headers.update({"Authorization": f"Bearer {token}"})
        yield ac

    app.dependency_overrides.clear()
