"""
Redis connection and utilities.
"""

from contextlib import asynccontextmanager
from typing import Any

import redis.asyncio as redis
from redis.asyncio import ConnectionPool, Redis

from shared.config import settings

# Connection pool
_pool: ConnectionPool | None = None


async def get_redis_pool() -> ConnectionPool:
    """Get or create Redis connection pool."""
    global _pool
    if _pool is None:
        _pool = ConnectionPool.from_url(
            str(settings.redis_url),
            max_connections=settings.redis_pool_size,
            decode_responses=True,
        )
    return _pool


async def get_redis() -> Redis:
    """Get Redis client instance."""
    pool = await get_redis_pool()
    return Redis(connection_pool=pool)


@asynccontextmanager
async def get_redis_context():
    """Context manager for Redis operations."""
    client = await get_redis()
    try:
        yield client
    finally:
        await client.close()


async def close_redis() -> None:
    """Close Redis connection pool."""
    global _pool
    if _pool is not None:
        await _pool.disconnect()
        _pool = None


class RedisCache:
    """High-level Redis cache interface."""

    def __init__(self, prefix: str = "cache"):
        self.prefix = prefix

    def _key(self, key: str) -> str:
        return f"{self.prefix}:{key}"

    async def get(self, key: str) -> Any | None:
        """Get value from cache."""
        async with get_redis_context() as client:
            value = await client.get(self._key(key))
            return value

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """Set value in cache with optional TTL."""
        async with get_redis_context() as client:
            return await client.set(self._key(key), value, ex=ttl)

    async def delete(self, key: str) -> int:
        """Delete key from cache."""
        async with get_redis_context() as client:
            return await client.delete(self._key(key))

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        async with get_redis_context() as client:
            return await client.exists(self._key(key)) > 0

    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment counter."""
        async with get_redis_context() as client:
            return await client.incrby(self._key(key), amount)

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on key."""
        async with get_redis_context() as client:
            return await client.expire(self._key(key), ttl)


class RateLimiter:
    """Redis-based rate limiter."""

    def __init__(self, prefix: str = "ratelimit"):
        self.prefix = prefix

    def _key(self, identifier: str, window: str) -> str:
        return f"{self.prefix}:{identifier}:{window}"

    async def is_allowed(
        self,
        identifier: str,
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        """
        Check if request is allowed under rate limit.

        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        import time

        window = str(int(time.time()) // window_seconds)
        key = self._key(identifier, window)

        async with get_redis_context() as client:
            pipe = client.pipeline()
            pipe.incr(key)
            pipe.expire(key, window_seconds)
            results = await pipe.execute()

            current = results[0]
            remaining = max(0, limit - current)

            return current <= limit, remaining
