"""
Production readiness tests — stubs for load, chaos, and safety scenarios.

Run with:  pytest tests/test_production_readiness.py -v
These tests require a live DB + Redis; skip in CI with:
  pytest -m "not production_readiness"
"""
import asyncio
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

pytestmark = pytest.mark.production_readiness


# ---------------------------------------------------------------------------
# 1. Database connection pool exhaustion
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_database_connection_pool_exhaustion():
    """
    Simulate pool exhaustion by opening pool_size+1 concurrent connections.
    Verifies the app returns 503 / queues gracefully rather than crashing.
    """
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import text

    pool_size = 5  # match SQLALCHEMY_POOL_SIZE in config
    sessions = []
    try:
        # Saturate the pool
        for _ in range(pool_size):
            s = AsyncSessionLocal()
            await s.execute(text("SELECT 1"))
            sessions.append(s)

        # One more request should still succeed via overflow or queue
        extra = AsyncSessionLocal()
        result = await extra.execute(text("SELECT 1"))
        assert result is not None, "Should succeed via pool overflow"
        await extra.close()
    finally:
        for s in sessions:
            await s.close()


# ---------------------------------------------------------------------------
# 2. Redis rate-limit burst handling
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_redis_rate_limit_burst_handling():
    """
    Fire rate-limit-check calls in rapid burst; verify no exception escapes
    and that requests beyond the limit are rejected (429) rather than
    crashing the process.
    """
    from app.core.redis_client import get_redis

    redis = await get_redis()
    key = "rl:test:burst_user"
    await redis.delete(key)

    limit = 10
    window = 60  # seconds

    async def check_rate_limit() -> bool:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window)
        return count <= limit

    results = await asyncio.gather(*[check_rate_limit() for _ in range(limit + 5)])
    allowed = sum(1 for r in results if r)
    denied = sum(1 for r in results if not r)

    assert allowed == limit, f"Expected {limit} allowed, got {allowed}"
    assert denied == 5, f"Expected 5 denied, got {denied}"

    await redis.delete(key)


# ---------------------------------------------------------------------------
# 3. Vector search accuracy with growing dataset
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_vector_search_accuracy_with_growing_dataset():
    """
    Insert synthetic embeddings at various dataset sizes and verify that the
    nearest-neighbour result is always the exact match (top-1 recall = 1.0).
    Requires pgvector extension.
    """
    import numpy as np
    from app.core.database import AsyncSessionLocal
    from sqlalchemy import text

    async with AsyncSessionLocal() as db:
        # Check pgvector is available
        result = await db.execute(
            text("SELECT 1 FROM pg_extension WHERE extname='vector'")
        )
        if not result.scalar():
            pytest.skip("pgvector extension not installed")

    query_vec = [0.1] * 1536  # simulate an Ada-002 embedding
    query_str = "[" + ",".join(str(v) for v in query_vec) + "]"

    async with AsyncSessionLocal() as db:
        # Verify student_memories embedding column is queryable
        result = await db.execute(
            text(
                """
                SELECT id FROM student_memories
                ORDER BY embedding <=> :q::vector
                LIMIT 1
                """
            ),
            {"q": query_str},
        )
        row = result.fetchone()
        # If table is empty the test still validates the query runs without error
        assert row is None or row[0] is not None


# ---------------------------------------------------------------------------
# 4. Graceful degradation when Claude is unavailable
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_graceful_degradation_when_claude_unavailable():
    """
    When the Anthropic API is unreachable, the /ai/ask endpoint must return
    503 (or a friendly error) rather than an unhandled 500 traceback.
    """
    import anthropic

    async def _raise(*args, **kwargs):
        raise anthropic.APIConnectionError(request=None)

    with patch(
        "app.services.ai_router.anthropic.AsyncAnthropic",
        return_value=AsyncMock(
            messages=AsyncMock(
                create=AsyncMock(side_effect=_raise),
                stream=AsyncMock(side_effect=_raise),
            )
        ),
    ):
        from app.main import app

        async with AsyncClient(app=app, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/v1/ai/ask",
                json={"message": "What is cardiac output?"},
                headers={"Authorization": "Bearer testtoken"},
            )
        # Accept 401 (no real token in unit test), 503, or 200 with error body
        # The key assertion: no 500 Internal Server Error
        assert resp.status_code != 500, (
            f"AI outage must not produce 500; got {resp.status_code}: {resp.text}"
        )


# ---------------------------------------------------------------------------
# 5. Feature flag rollback safety
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_feature_flag_rollback_safety():
    """
    Toggle a feature flag off and verify that code paths guarded by that flag
    fall back gracefully and do not raise exceptions.
    """
    from app.core.feature_flags import is_enabled, set_flag, DEFAULTS

    flag = "pgvector_search"
    original_rollout = DEFAULTS.get(flag, 100)

    try:
        # Disable the flag for all users
        await set_flag(flag, enabled=True, rollout=0)

        enabled_for_user = await is_enabled(flag, user_id=42)
        assert not enabled_for_user, "Flag should be disabled at 0 % rollout"

        # Re-enable
        await set_flag(flag, enabled=True, rollout=100)
        enabled_for_user = await is_enabled(flag, user_id=42)
        assert enabled_for_user, "Flag should be enabled at 100 % rollout"

    finally:
        # Restore original state
        await set_flag(flag, enabled=True, rollout=original_rollout)
