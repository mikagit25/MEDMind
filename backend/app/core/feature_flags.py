"""Redis-backed feature flag system.

Flags are stored as Redis hashes: `feature_flags:{flag_name}` → {"enabled": "1", "rollout": "100"}
rollout is 0-100 (percentage of users to enable for).

Usage:
    from app.core.feature_flags import is_enabled
    if await is_enabled("pgvector_search"):
        # use vector search
"""
import hashlib
from app.core.redis_client import get_redis

FLAG_PREFIX = "feature_flag:"

# In-memory override — used when Redis is unavailable (tests, cold start)
_MEM_FLAGS: dict[str, dict] = {}

# Default flag values (fallback when Redis is unavailable)
DEFAULTS: dict[str, bool] = {
    "pgvector_search": False,      # semantic vector search (requires pgvector)
    "ai_memory": True,             # long-term AI memory extraction
    "pdf_export": True,            # CPD/CME PDF export
    "ugc_flashcards": True,        # user-generated flashcards
    "posthog_analytics": True,     # PostHog tracking
    "sentry_monitoring": True,     # Sentry error reporting
    "imaging_library": True,       # medical imaging library
    "anatomy_3d": True,            # 3D anatomy viewers
}


async def is_enabled(flag: str, user_id: str | None = None) -> bool:
    """Check if a feature flag is enabled, optionally for a specific user (percentage rollout)."""
    try:
        redis = await get_redis()
        raw = await redis.hgetall(f"{FLAG_PREFIX}{flag}")
        if not raw:
            # Check in-memory override first, then defaults
            mem = _MEM_FLAGS.get(flag)
            if mem is not None:
                raw = {"enabled": "1" if mem["enabled"] else "0", "rollout": str(mem["rollout"])}
            else:
                return DEFAULTS.get(flag, False)

        if raw.get("enabled", "0") != "1":
            return False

        rollout = int(raw.get("rollout", "100"))
        if rollout >= 100:
            return True
        if rollout <= 0:
            return False

        # Deterministic percentage rollout: hash(flag + user_id) mod 100
        if user_id:
            h = int(hashlib.md5(f"{flag}:{user_id}".encode()).hexdigest(), 16)
            return (h % 100) < rollout

        return False
    except Exception:
        # Redis unavailable → check in-memory override, then defaults
        mem = _MEM_FLAGS.get(flag)
        if mem is not None:
            if not mem["enabled"]:
                return False
            rollout = mem["rollout"]
            if rollout >= 100:
                return True
            if rollout <= 0:
                return False
            if user_id:
                h = int(hashlib.md5(f"{flag}:{user_id}".encode()).hexdigest(), 16)
                return (h % 100) < rollout
            return False
        return DEFAULTS.get(flag, False)


async def set_flag(flag: str, enabled: bool, rollout: int = 100) -> None:
    """Set a feature flag value in Redis, with in-memory fallback."""
    rollout = max(0, min(100, rollout))
    _MEM_FLAGS[flag] = {"enabled": enabled, "rollout": rollout}
    try:
        redis = await get_redis()
        await redis.hset(f"{FLAG_PREFIX}{flag}", mapping={
            "enabled": "1" if enabled else "0",
            "rollout": str(rollout),
        })
    except Exception:
        pass  # already saved in _MEM_FLAGS above


async def list_flags() -> dict[str, dict]:
    """Return all flags with their current values."""
    redis = await get_redis()
    result = {}
    for flag, default in DEFAULTS.items():
        raw = await redis.hgetall(f"{FLAG_PREFIX}{flag}")
        if raw:
            result[flag] = {
                "enabled": raw.get("enabled") == "1",
                "rollout": int(raw.get("rollout", "100")),
                "source": "redis",
            }
        else:
            result[flag] = {"enabled": default, "rollout": 100, "source": "default"}
    return result
