"""Redis response cache utilities.

Simple decorator-based cache for FastAPI route results.
Keys are based on route + parameters. TTL defaults to 5 minutes.

Usage:
    from app.core.cache import cache_response, invalidate

    @router.get("/specialties")
    async def list_specialties(...):
        cached = await cache_response("specialties", ttl=300)
        if cached is not None:
            return cached
        result = ... # expensive DB query
        await cache_response("specialties", value=result, ttl=300)
        return result
"""
import json
import logging
from typing import Any

from app.core.redis_client import get_redis

logger = logging.getLogger(__name__)

_MISS = object()   # sentinel for "not in cache"


async def get_cached(key: str) -> Any:
    """Return cached value or None if not found / Redis unavailable."""
    try:
        redis = await get_redis()
        raw = await redis.get(f"cache:{key}")
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        logger.debug("Cache get failed for %s: %s", key, e)
        return None


async def set_cached(key: str, value: Any, ttl: int = 300) -> None:
    """Store value in Redis with TTL seconds. Silently ignores errors."""
    try:
        redis = await get_redis()
        await redis.setex(f"cache:{key}", ttl, json.dumps(value, default=str))
    except Exception as e:
        logger.debug("Cache set failed for %s: %s", key, e)


async def invalidate(pattern: str) -> None:
    """Delete all cache keys matching pattern (e.g. 'specialties*')."""
    try:
        redis = await get_redis()
        keys = await redis.keys(f"cache:{pattern}")
        if keys:
            await redis.delete(*keys)
    except Exception as e:
        logger.debug("Cache invalidate failed for %s: %s", pattern, e)
