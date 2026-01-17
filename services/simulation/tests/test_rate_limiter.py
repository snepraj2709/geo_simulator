"""
Tests for the Rate Limiter component.
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from services.simulation.components.rate_limiter import (
    SimulationRateLimiter,
    TokenBucket,
    get_simulation_rate_limiter,
)
from services.simulation.schemas import LLMProviderType


class TestTokenBucket:
    """Tests for TokenBucket."""

    @pytest.fixture
    def bucket(self):
        """Create a test bucket."""
        return TokenBucket(
            key="test:bucket",
            capacity=10,
            refill_rate=1.0,
            refill_interval=1,
            redis_client=None,  # Local-only
        )

    @pytest.mark.asyncio
    async def test_acquire_success(self, bucket):
        """Test successful token acquisition."""
        result = await bucket.acquire(1)

        assert result.allowed is True
        assert result.remaining == 9
        assert result.retry_after is None

    @pytest.mark.asyncio
    async def test_acquire_multiple(self, bucket):
        """Test acquiring multiple tokens."""
        result = await bucket.acquire(5)

        assert result.allowed is True
        assert result.remaining == 5

    @pytest.mark.asyncio
    async def test_acquire_exceeds_capacity(self, bucket):
        """Test when request exceeds remaining capacity."""
        # Drain the bucket
        await bucket.acquire(10)

        # Try to acquire more
        result = await bucket.acquire(1)

        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after is not None

    @pytest.mark.asyncio
    async def test_token_refill(self, bucket):
        """Test that tokens are refilled over time."""
        import asyncio

        # Drain the bucket
        await bucket.acquire(10)
        assert (await bucket.acquire(1)).allowed is False

        # Wait for refill
        await asyncio.sleep(1.1)

        # Should have 1 token now
        result = await bucket.acquire(1)
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_get_info(self, bucket):
        """Test getting bucket info."""
        await bucket.acquire(3)

        info = await bucket.get_info()

        assert info["key"] == "test:bucket"
        assert info["capacity"] == 10
        assert info["current_tokens"] == 7


class TestTokenBucketWithRedis:
    """Tests for TokenBucket with Redis backend."""

    @pytest.fixture
    def bucket_with_redis(self, mock_redis_client):
        """Create a bucket with mock Redis."""
        return TokenBucket(
            key="test:bucket:redis",
            capacity=10,
            refill_rate=1.0,
            refill_interval=1,
            redis_client=mock_redis_client,
        )

    @pytest.mark.asyncio
    async def test_acquire_with_redis(self, bucket_with_redis, mock_redis_client):
        """Test token acquisition with Redis."""
        mock_redis_client.hgetall = AsyncMock(return_value={})

        result = await bucket_with_redis.acquire(1)

        assert result.allowed is True
        assert mock_redis_client.hset.called

    @pytest.mark.asyncio
    async def test_redis_fallback_on_error(self, bucket_with_redis, mock_redis_client):
        """Test fallback to local when Redis fails."""
        mock_redis_client.hgetall = AsyncMock(side_effect=Exception("Redis error"))

        # Should fall back to local rate limiting
        result = await bucket_with_redis.acquire(1)

        assert result.allowed is True


class TestSimulationRateLimiter:
    """Tests for SimulationRateLimiter."""

    @pytest.fixture
    def rate_limiter(self):
        """Create a test rate limiter."""
        return SimulationRateLimiter()

    @pytest.fixture
    def user_id(self):
        return uuid.uuid4()

    @pytest.fixture
    def org_id(self):
        return uuid.uuid4()

    @pytest.mark.asyncio
    async def test_check_simulation_limit(self, rate_limiter, user_id, org_id):
        """Test simulation rate limiting."""
        # First 5 should be allowed (default limit)
        for i in range(5):
            result = await rate_limiter.check_simulation_limit(user_id, org_id)
            assert result.allowed is True

        # 6th should be blocked
        result = await rate_limiter.check_simulation_limit(user_id, org_id)
        assert result.allowed is False
        assert result.retry_after is not None

    @pytest.mark.asyncio
    async def test_check_provider_limit(self, rate_limiter, org_id):
        """Test provider-specific rate limiting."""
        # Should allow up to the provider's limit
        result = await rate_limiter.check_provider_limit(
            org_id,
            LLMProviderType.OPENAI,
        )
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_different_orgs_separate_limits(self, rate_limiter, user_id):
        """Test that different orgs have separate limits."""
        org1 = uuid.uuid4()
        org2 = uuid.uuid4()

        # Exhaust org1's limit
        for _ in range(5):
            await rate_limiter.check_simulation_limit(user_id, org1)

        # org2 should still have tokens
        result = await rate_limiter.check_simulation_limit(user_id, org2)
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_check_daily_token_limit(self, rate_limiter, org_id):
        """Test daily token limit checking."""
        result = await rate_limiter.check_daily_token_limit(
            org_id,
            LLMProviderType.OPENAI,
            tokens=1000,
        )
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_get_rate_limit_info(self, rate_limiter, org_id):
        """Test getting rate limit info."""
        # Make some requests first
        await rate_limiter.check_simulation_limit(uuid.uuid4(), org_id)
        await rate_limiter.check_provider_limit(org_id, LLMProviderType.OPENAI)

        infos = await rate_limiter.get_rate_limit_info(org_id)

        assert isinstance(infos, list)

    @pytest.mark.asyncio
    async def test_wait_for_limit_allowed(self, rate_limiter, user_id, org_id):
        """Test wait_for_limit when allowed."""
        result = await rate_limiter.check_simulation_limit(user_id, org_id)

        waited = await rate_limiter.wait_for_limit(result)
        assert waited is True

    @pytest.mark.asyncio
    async def test_wait_for_limit_blocked(self, rate_limiter, user_id, org_id):
        """Test wait_for_limit when blocked."""
        # Exhaust the limit
        for _ in range(5):
            await rate_limiter.check_simulation_limit(user_id, org_id)

        result = await rate_limiter.check_simulation_limit(user_id, org_id)

        # With max_wait of 0, should return False immediately
        waited = await rate_limiter.wait_for_limit(result, max_wait_seconds=0)
        assert waited is False


class TestGlobalRateLimiter:
    """Tests for global rate limiter instance."""

    def test_get_simulation_rate_limiter(self):
        """Test getting global rate limiter."""
        limiter1 = get_simulation_rate_limiter()
        limiter2 = get_simulation_rate_limiter()

        assert limiter1 is limiter2
        assert isinstance(limiter1, SimulationRateLimiter)
