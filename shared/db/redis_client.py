"""
Redis client with connection pooling and caching utilities.

This module provides a robust Redis client with:
- Async connection pooling
- Health check capabilities
- JSON serialization for complex objects
- TTL-based caching utilities
- Graceful shutdown handling
"""

import json
import logging
from typing import Any

import redis.asyncio as redis
from redis.asyncio import ConnectionPool, Redis

from shared.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Redis client with connection pooling and caching utilities.

    Provides async Redis access with connection pooling,
    health checks, and JSON serialization.

    Usage:
        client = RedisClient()
        await client.connect()

        await client.set("key", {"data": "value"}, ttl=3600)
        data = await client.get("key")

        await client.disconnect()
    """

    def __init__(
        self,
        redis_url: str | None = None,
        pool_size: int | None = None,
        decode_responses: bool = True,
    ):
        """
        Initialize Redis client.

        Args:
            redis_url: Redis connection URL. Defaults to settings.
            pool_size: Maximum number of connections in pool. Defaults to settings.
            decode_responses: Whether to decode byte responses to strings.
        """
        self._redis_url = redis_url or str(settings.redis_url)
        self._pool_size = pool_size or settings.redis_pool_size
        self._decode_responses = decode_responses

        self._pool: ConnectionPool | None = None
        self._client: Redis | None = None
        self._is_connected = False

    @property
    def client(self) -> Redis:
        """Get the Redis client."""
        if self._client is None:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._client

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._is_connected

    async def connect(self) -> None:
        """
        Establish Redis connection with connection pool.

        Raises:
            redis.RedisError: If connection fails.
        """
        if self._is_connected:
            logger.warning("Redis client already connected")
            return

        logger.info(
            "Connecting to Redis with pool_size=%d",
            self._pool_size,
        )

        try:
            self._pool = ConnectionPool.from_url(
                self._redis_url,
                max_connections=self._pool_size,
                decode_responses=self._decode_responses,
            )

            self._client = Redis(connection_pool=self._pool)

            # Verify connection
            await self._client.ping()

            self._is_connected = True
            logger.info("Redis connection established successfully")

        except redis.RedisError as e:
            logger.error("Failed to connect to Redis: %s", e)
            raise

    async def disconnect(self) -> None:
        """
        Close Redis connections and dispose of the connection pool.
        """
        if not self._is_connected:
            return

        logger.info("Disconnecting from Redis")

        if self._client:
            await self._client.aclose()
            self._client = None

        if self._pool:
            await self._pool.disconnect()
            self._pool = None

        self._is_connected = False
        logger.info("Redis connection closed")

    async def health_check(self) -> dict[str, Any]:
        """
        Perform Redis health check.

        Returns:
            dict: Health status including connection info.
        """
        try:
            await self.client.ping()
            info = await self.client.info("clients")
            return {
                "status": "healthy",
                "connected_clients": info.get("connected_clients", 0),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }

    # ==================== Caching Utilities ====================

    async def get(self, key: str) -> Any | None:
        """
        Get a value from cache.

        Args:
            key: Cache key.

        Returns:
            Cached value or None if not found.
        """
        value = await self.client.get(key)
        if value is None:
            return None

        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
    ) -> bool:
        """
        Set a value in cache.

        Args:
            key: Cache key.
            value: Value to cache (will be JSON-serialized if not a string).
            ttl: Time-to-live in seconds. None for no expiration.

        Returns:
            True if successful.
        """
        if not isinstance(value, str):
            value = json.dumps(value, default=str)

        if ttl:
            return await self.client.setex(key, ttl, value)
        else:
            return await self.client.set(key, value)

    async def delete(self, key: str) -> int:
        """
        Delete a key from cache.

        Args:
            key: Cache key.

        Returns:
            Number of keys deleted (0 or 1).
        """
        return await self.client.delete(key)

    async def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: Glob-style pattern (e.g., "user:*").

        Returns:
            Number of keys deleted.
        """
        keys = []
        async for key in self.client.scan_iter(match=pattern):
            keys.append(key)

        if not keys:
            return 0

        return await self.client.delete(*keys)

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists.

        Args:
            key: Cache key.

        Returns:
            True if key exists.
        """
        return await self.client.exists(key) > 0

    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set expiration on an existing key.

        Args:
            key: Cache key.
            ttl: Time-to-live in seconds.

        Returns:
            True if expiration was set.
        """
        return await self.client.expire(key, ttl)

    async def ttl(self, key: str) -> int:
        """
        Get remaining TTL for a key.

        Args:
            key: Cache key.

        Returns:
            TTL in seconds, -1 if no TTL, -2 if key doesn't exist.
        """
        return await self.client.ttl(key)

    # ==================== Hash Operations ====================

    async def hget(self, name: str, key: str) -> Any | None:
        """
        Get a field from a hash.

        Args:
            name: Hash name.
            key: Field key.

        Returns:
            Field value or None.
        """
        value = await self.client.hget(name, key)
        if value is None:
            return None

        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    async def hset(self, name: str, key: str, value: Any) -> int:
        """
        Set a field in a hash.

        Args:
            name: Hash name.
            key: Field key.
            value: Field value.

        Returns:
            1 if new field, 0 if updated.
        """
        if not isinstance(value, str):
            value = json.dumps(value, default=str)
        return await self.client.hset(name, key, value)

    async def hgetall(self, name: str) -> dict[str, Any]:
        """
        Get all fields from a hash.

        Args:
            name: Hash name.

        Returns:
            Dictionary of field-value pairs.
        """
        data = await self.client.hgetall(name)
        result = {}
        for key, value in data.items():
            try:
                result[key] = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                result[key] = value
        return result

    async def hdel(self, name: str, *keys: str) -> int:
        """
        Delete fields from a hash.

        Args:
            name: Hash name.
            keys: Field keys to delete.

        Returns:
            Number of fields deleted.
        """
        return await self.client.hdel(name, *keys)

    # ==================== List Operations ====================

    async def lpush(self, key: str, *values: Any) -> int:
        """
        Push values to the left of a list.

        Args:
            key: List key.
            values: Values to push.

        Returns:
            Length of list after push.
        """
        serialized = [
            json.dumps(v, default=str) if not isinstance(v, str) else v
            for v in values
        ]
        return await self.client.lpush(key, *serialized)

    async def rpush(self, key: str, *values: Any) -> int:
        """
        Push values to the right of a list.

        Args:
            key: List key.
            values: Values to push.

        Returns:
            Length of list after push.
        """
        serialized = [
            json.dumps(v, default=str) if not isinstance(v, str) else v
            for v in values
        ]
        return await self.client.rpush(key, *serialized)

    async def lrange(self, key: str, start: int, end: int) -> list[Any]:
        """
        Get a range of elements from a list.

        Args:
            key: List key.
            start: Start index.
            end: End index (-1 for all).

        Returns:
            List of elements.
        """
        values = await self.client.lrange(key, start, end)
        result = []
        for value in values:
            try:
                result.append(json.loads(value))
            except (json.JSONDecodeError, TypeError):
                result.append(value)
        return result

    async def llen(self, key: str) -> int:
        """
        Get the length of a list.

        Args:
            key: List key.

        Returns:
            Length of list.
        """
        return await self.client.llen(key)

    # ==================== Counter Operations ====================

    async def incr(self, key: str, amount: int = 1) -> int:
        """
        Increment a counter.

        Args:
            key: Counter key.
            amount: Amount to increment by.

        Returns:
            New counter value.
        """
        return await self.client.incrby(key, amount)

    async def decr(self, key: str, amount: int = 1) -> int:
        """
        Decrement a counter.

        Args:
            key: Counter key.
            amount: Amount to decrement by.

        Returns:
            New counter value.
        """
        return await self.client.decrby(key, amount)


# Global client instance
_client: RedisClient | None = None


def get_redis_client() -> RedisClient:
    """
    Get the global Redis client instance.

    Returns:
        RedisClient: The global client instance.
    """
    global _client
    if _client is None:
        _client = RedisClient()
    return _client


async def get_cache() -> RedisClient:
    """
    FastAPI dependency for getting the Redis client.

    Yields:
        RedisClient: Redis client instance.
    """
    client = get_redis_client()
    if not client.is_connected:
        await client.connect()
    return client
