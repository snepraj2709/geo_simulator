"""
Rate Limiter.

Implements rate limiting for LLM API calls and simulation requests
per DEPLOYMENT.md configuration. Uses Redis for distributed rate limiting.
"""

import asyncio
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from shared.config import settings
from shared.db.redis_client import RedisClient, get_redis_client
from shared.utils.logging import get_logger

from services.simulation.schemas import LLMProviderType, RateLimitConfig, RateLimitInfo

logger = get_logger(__name__)


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    allowed: bool
    remaining: int
    reset_at: datetime
    retry_after: int | None = None  # Seconds until retry allowed


class TokenBucket:
    """
    Token bucket rate limiter with Redis backend.

    Implements a token bucket algorithm for rate limiting with:
    - Configurable capacity and refill rate
    - Redis persistence for distributed systems
    - Graceful degradation without Redis
    """

    def __init__(
        self,
        key: str,
        capacity: int,
        refill_rate: float,
        refill_interval: int = 1,
        redis_client: RedisClient | None = None,
    ):
        """
        Initialize the token bucket.

        Args:
            key: Redis key for this bucket.
            capacity: Maximum tokens in the bucket.
            refill_rate: Tokens to add per interval.
            refill_interval: Interval in seconds for refill.
            redis_client: Optional Redis client.
        """
        self.key = key
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.refill_interval = refill_interval
        self._redis = redis_client

        # Local fallback
        self._local_tokens = float(capacity)
        self._local_last_update = time.time()
        self._lock = asyncio.Lock()

    async def _get_redis(self) -> RedisClient | None:
        """Get Redis client, connecting if necessary."""
        if self._redis is None:
            self._redis = get_redis_client()

        if not self._redis.is_connected:
            try:
                await self._redis.connect()
            except Exception as e:
                logger.warning(
                    "Redis connection failed, using local rate limiting",
                    error=str(e),
                )
                return None

        return self._redis

    async def acquire(self, tokens: int = 1) -> RateLimitResult:
        """
        Attempt to acquire tokens from the bucket.

        Args:
            tokens: Number of tokens to acquire.

        Returns:
            RateLimitResult indicating success or failure.
        """
        redis = await self._get_redis()

        if redis:
            return await self._acquire_redis(redis, tokens)
        else:
            return await self._acquire_local(tokens)

    async def _acquire_redis(
        self,
        redis: RedisClient,
        tokens: int,
    ) -> RateLimitResult:
        """Acquire tokens using Redis."""
        now = time.time()
        bucket_key = f"ratelimit:{self.key}"

        try:
            # Get current state
            data = await redis.hgetall(bucket_key)

            if data:
                current_tokens = float(data.get("tokens", self.capacity))
                last_update = float(data.get("last_update", now))
            else:
                current_tokens = float(self.capacity)
                last_update = now

            # Calculate refill
            elapsed = now - last_update
            refill_amount = (elapsed / self.refill_interval) * self.refill_rate
            current_tokens = min(self.capacity, current_tokens + refill_amount)

            # Check if we can acquire
            if current_tokens >= tokens:
                current_tokens -= tokens
                allowed = True
            else:
                allowed = False

            # Update Redis
            await redis.hset(bucket_key, "tokens", str(current_tokens))
            await redis.hset(bucket_key, "last_update", str(now))
            await redis.expire(bucket_key, 3600)  # 1 hour TTL

            # Calculate reset time
            if allowed:
                remaining = int(current_tokens)
                reset_at = datetime.utcnow() + timedelta(seconds=self.refill_interval)
                retry_after = None
            else:
                remaining = 0
                tokens_needed = tokens - current_tokens
                wait_seconds = (tokens_needed / self.refill_rate) * self.refill_interval
                reset_at = datetime.utcnow() + timedelta(seconds=wait_seconds)
                retry_after = int(wait_seconds) + 1

            return RateLimitResult(
                allowed=allowed,
                remaining=remaining,
                reset_at=reset_at,
                retry_after=retry_after,
            )

        except Exception as e:
            logger.error(
                "Redis rate limit error, falling back to local",
                error=str(e),
            )
            return await self._acquire_local(tokens)

    async def _acquire_local(self, tokens: int) -> RateLimitResult:
        """Acquire tokens using local state (fallback)."""
        async with self._lock:
            now = time.time()

            # Calculate refill
            elapsed = now - self._local_last_update
            refill_amount = (elapsed / self.refill_interval) * self.refill_rate
            self._local_tokens = min(self.capacity, self._local_tokens + refill_amount)
            self._local_last_update = now

            # Check if we can acquire
            if self._local_tokens >= tokens:
                self._local_tokens -= tokens
                return RateLimitResult(
                    allowed=True,
                    remaining=int(self._local_tokens),
                    reset_at=datetime.utcnow() + timedelta(seconds=self.refill_interval),
                )
            else:
                tokens_needed = tokens - self._local_tokens
                wait_seconds = (tokens_needed / self.refill_rate) * self.refill_interval
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_at=datetime.utcnow() + timedelta(seconds=wait_seconds),
                    retry_after=int(wait_seconds) + 1,
                )

    async def get_info(self) -> dict[str, Any]:
        """Get current bucket info."""
        redis = await self._get_redis()

        if redis:
            try:
                data = await redis.hgetall(f"ratelimit:{self.key}")
                return {
                    "key": self.key,
                    "capacity": self.capacity,
                    "current_tokens": float(data.get("tokens", self.capacity)),
                    "refill_rate": self.refill_rate,
                    "refill_interval": self.refill_interval,
                }
            except Exception:
                pass

        return {
            "key": self.key,
            "capacity": self.capacity,
            "current_tokens": self._local_tokens,
            "refill_rate": self.refill_rate,
            "refill_interval": self.refill_interval,
        }


class SimulationRateLimiter:
    """
    Rate limiter specifically for simulation operations.

    Implements limits per DEPLOYMENT.md:
    - Per-user API rate limits
    - Simulation triggers: 5 requests/hour
    - LLM API cost controls per organization/provider
    """

    def __init__(
        self,
        redis_client: RedisClient | None = None,
    ):
        """
        Initialize the rate limiter.

        Args:
            redis_client: Optional Redis client for distributed limiting.
        """
        self._redis = redis_client
        self._buckets: dict[str, TokenBucket] = {}

        # Default limits from settings
        self._simulation_limit = settings.rate_limit_simulation  # 5/hour
        self._read_limit = settings.rate_limit_read  # 100/minute
        self._write_limit = settings.rate_limit_write  # 30/minute

        # Per-provider limits
        self._provider_limits = {
            LLMProviderType.OPENAI: RateLimitConfig(
                requests_per_minute=60,
                requests_per_hour=1000,
                tokens_per_minute=100000,
                concurrent_requests=10,
            ),
            LLMProviderType.GOOGLE: RateLimitConfig(
                requests_per_minute=60,
                requests_per_hour=1000,
                tokens_per_minute=100000,
                concurrent_requests=10,
            ),
            LLMProviderType.ANTHROPIC: RateLimitConfig(
                requests_per_minute=50,
                requests_per_hour=500,
                tokens_per_minute=80000,
                concurrent_requests=5,
            ),
            LLMProviderType.PERPLEXITY: RateLimitConfig(
                requests_per_minute=20,
                requests_per_hour=200,
                tokens_per_minute=50000,
                concurrent_requests=3,
            ),
        }

    def _get_bucket(
        self,
        key: str,
        capacity: int,
        refill_rate: float,
        refill_interval: int = 1,
    ) -> TokenBucket:
        """Get or create a token bucket."""
        if key not in self._buckets:
            self._buckets[key] = TokenBucket(
                key=key,
                capacity=capacity,
                refill_rate=refill_rate,
                refill_interval=refill_interval,
                redis_client=self._redis,
            )
        return self._buckets[key]

    async def check_simulation_limit(
        self,
        user_id: uuid.UUID,
        organization_id: uuid.UUID,
    ) -> RateLimitResult:
        """
        Check if a simulation can be triggered.

        Limit: 5 simulations per hour per organization.

        Args:
            user_id: User UUID.
            organization_id: Organization UUID.

        Returns:
            RateLimitResult.
        """
        key = f"simulation:{organization_id}"
        bucket = self._get_bucket(
            key=key,
            capacity=self._simulation_limit,
            refill_rate=self._simulation_limit,
            refill_interval=3600,  # 1 hour
        )
        return await bucket.acquire()

    async def check_provider_limit(
        self,
        organization_id: uuid.UUID,
        provider: LLMProviderType,
    ) -> RateLimitResult:
        """
        Check if an LLM provider can be queried.

        Args:
            organization_id: Organization UUID.
            provider: LLM provider type.

        Returns:
            RateLimitResult.
        """
        config = self._provider_limits.get(provider)
        if not config:
            return RateLimitResult(
                allowed=True,
                remaining=999,
                reset_at=datetime.utcnow(),
            )

        key = f"llm:{organization_id}:{provider.value}"
        bucket = self._get_bucket(
            key=key,
            capacity=config.requests_per_minute,
            refill_rate=config.requests_per_minute,
            refill_interval=60,
        )
        return await bucket.acquire()

    async def check_daily_token_limit(
        self,
        organization_id: uuid.UUID,
        provider: LLMProviderType,
        tokens: int,
    ) -> RateLimitResult:
        """
        Check daily token limit for a provider.

        Args:
            organization_id: Organization UUID.
            provider: LLM provider type.
            tokens: Number of tokens to consume.

        Returns:
            RateLimitResult.
        """
        config = self._provider_limits.get(provider)
        if not config:
            return RateLimitResult(
                allowed=True,
                remaining=999999,
                reset_at=datetime.utcnow(),
            )

        # Daily limit = tokens_per_minute * 60 * 24
        daily_limit = config.tokens_per_minute * 60 * 24

        key = f"tokens:{organization_id}:{provider.value}:daily"
        bucket = self._get_bucket(
            key=key,
            capacity=daily_limit,
            refill_rate=daily_limit,
            refill_interval=86400,  # 24 hours
        )
        return await bucket.acquire(tokens)

    async def get_rate_limit_info(
        self,
        organization_id: uuid.UUID,
        provider: LLMProviderType | None = None,
    ) -> list[RateLimitInfo]:
        """
        Get current rate limit info for an organization.

        Args:
            organization_id: Organization UUID.
            provider: Optional specific provider.

        Returns:
            List of RateLimitInfo objects.
        """
        infos = []

        # Simulation limit
        sim_key = f"simulation:{organization_id}"
        if sim_key in self._buckets:
            bucket_info = await self._buckets[sim_key].get_info()
            infos.append(
                RateLimitInfo(
                    provider="simulation",
                    limit=int(bucket_info["capacity"]),
                    remaining=int(bucket_info["current_tokens"]),
                    reset_at=datetime.utcnow() + timedelta(hours=1),
                    is_limited=bucket_info["current_tokens"] < 1,
                )
            )

        # Provider limits
        providers = [provider] if provider else list(self._provider_limits.keys())
        for p in providers:
            key = f"llm:{organization_id}:{p.value}"
            if key in self._buckets:
                bucket_info = await self._buckets[key].get_info()
                infos.append(
                    RateLimitInfo(
                        provider=p.value,
                        limit=int(bucket_info["capacity"]),
                        remaining=int(bucket_info["current_tokens"]),
                        reset_at=datetime.utcnow() + timedelta(minutes=1),
                        is_limited=bucket_info["current_tokens"] < 1,
                    )
                )

        return infos

    async def wait_for_limit(
        self,
        result: RateLimitResult,
        max_wait_seconds: int = 60,
    ) -> bool:
        """
        Wait for rate limit to reset.

        Args:
            result: Rate limit result.
            max_wait_seconds: Maximum time to wait.

        Returns:
            True if wait completed, False if exceeded max wait.
        """
        if result.allowed:
            return True

        if result.retry_after and result.retry_after <= max_wait_seconds:
            logger.info(
                "Waiting for rate limit reset",
                retry_after=result.retry_after,
            )
            await asyncio.sleep(result.retry_after)
            return True

        return False


# Global rate limiter instance
_rate_limiter: SimulationRateLimiter | None = None


def get_simulation_rate_limiter() -> SimulationRateLimiter:
    """Get the global simulation rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = SimulationRateLimiter()
    return _rate_limiter
