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

from app.main import app
from app.core.database import Base, get_db
from app.models import models  # noqa: F401 — register all models

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


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(TEST_DB_URL, echo=False)
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
async def client(engine, monkeypatch):
    """HTTP test client with DB override and fake Redis."""
    import app.core.redis_client as _rc

    fake = FakeRedis()

    async def _fake_get_redis():
        return fake

    # Patch at module level so all imports of get_redis see the fake
    monkeypatch.setattr(_rc, "get_redis", _fake_get_redis)
    # Also reset the pool so it doesn't try to reuse a stale real connection
    monkeypatch.setattr(_rc, "_redis_pool", None)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
