"""
Rate Limiter component.

Implements rate limiting for scraping operations to respect
website policies and prevent abuse.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limiting configuration."""
    requests_per_second: float = 1.0
    requests_per_minute: int = 30
    min_delay_ms: int = 500
    max_delay_ms: int = 3000
    hard_scrape_cooldown_days: int = 7


class ScrapeRateLimiter:
    """
    Rate limiter for web scraping operations.

    Features:
    - Per-domain rate limiting
    - Adaptive delays based on response times
    - Hard scrape cooldown enforcement (1 per week per domain)
    - Burst protection
    """

    def __init__(self, config: RateLimitConfig | None = None):
        """
        Initialize rate limiter.

        Args:
            config: Rate limiting configuration.
        """
        self.config = config or RateLimitConfig()

        # Track request timestamps per domain
        self._domain_requests: dict[str, list[float]] = {}

        # Track last hard scrape per domain
        self._hard_scrapes: dict[str, datetime] = {}

        # Adaptive delay tracking
        self._response_times: dict[str, list[float]] = {}

        # Current delay per domain
        self._current_delays: dict[str, float] = {}

    async def acquire(self, domain: str) -> None:
        """
        Acquire rate limit permission for a domain.

        Blocks until request is allowed.

        Args:
            domain: Domain to rate limit.
        """
        delay = self._calculate_delay(domain)

        if delay > 0:
            logger.debug("Rate limiting: waiting %.2fs for %s", delay, domain)
            await asyncio.sleep(delay)

        # Record request
        now = time.time()
        if domain not in self._domain_requests:
            self._domain_requests[domain] = []

        self._domain_requests[domain].append(now)

        # Clean old entries (keep last minute)
        cutoff = now - 60
        self._domain_requests[domain] = [
            t for t in self._domain_requests[domain] if t > cutoff
        ]

    def record_response_time(self, domain: str, response_time_ms: float) -> None:
        """
        Record response time for adaptive rate limiting.

        Args:
            domain: Domain of the request.
            response_time_ms: Response time in milliseconds.
        """
        if domain not in self._response_times:
            self._response_times[domain] = []

        self._response_times[domain].append(response_time_ms)

        # Keep last 10 response times
        self._response_times[domain] = self._response_times[domain][-10:]

        # Adjust delay based on response times
        self._adjust_delay(domain)

    def can_hard_scrape(self, domain: str) -> bool:
        """
        Check if hard scrape is allowed for domain.

        Hard scrapes are limited to 1 per week per domain.

        Args:
            domain: Domain to check.

        Returns:
            True if hard scrape is allowed.
        """
        last_scrape = self._hard_scrapes.get(domain)
        if not last_scrape:
            return True

        cooldown = timedelta(days=self.config.hard_scrape_cooldown_days)
        return datetime.now(timezone.utc) - last_scrape >= cooldown

    def next_hard_scrape_available(self, domain: str) -> datetime | None:
        """
        Get when next hard scrape will be available.

        Args:
            domain: Domain to check.

        Returns:
            DateTime when hard scrape is available, or None if available now.
        """
        last_scrape = self._hard_scrapes.get(domain)
        if not last_scrape:
            return None

        cooldown = timedelta(days=self.config.hard_scrape_cooldown_days)
        next_available = last_scrape + cooldown

        if datetime.now(timezone.utc) >= next_available:
            return None

        return next_available

    def record_hard_scrape(self, domain: str) -> None:
        """
        Record a hard scrape for cooldown tracking.

        Args:
            domain: Domain that was hard scraped.
        """
        self._hard_scrapes[domain] = datetime.now(timezone.utc)
        logger.info("Recorded hard scrape for %s", domain)

    def _calculate_delay(self, domain: str) -> float:
        """Calculate delay needed before next request."""
        now = time.time()
        requests = self._domain_requests.get(domain, [])

        if not requests:
            return 0

        # Check requests per minute limit
        recent_minute = [t for t in requests if t > now - 60]
        if len(recent_minute) >= self.config.requests_per_minute:
            # Wait until oldest request expires
            oldest = min(recent_minute)
            return max(0, oldest + 60 - now)

        # Check requests per second limit
        last_request = requests[-1]
        min_interval = 1.0 / self.config.requests_per_second
        time_since_last = now - last_request

        if time_since_last < min_interval:
            base_delay = min_interval - time_since_last
        else:
            base_delay = 0

        # Apply domain-specific adaptive delay
        adaptive_delay = self._current_delays.get(domain, 0)

        # Return max of base delay and adaptive delay
        total_delay = max(base_delay, adaptive_delay / 1000)  # Convert ms to seconds

        # Ensure within configured bounds
        min_delay = self.config.min_delay_ms / 1000
        max_delay = self.config.max_delay_ms / 1000

        return max(min_delay, min(total_delay, max_delay))

    def _adjust_delay(self, domain: str) -> None:
        """Adjust delay based on response times."""
        times = self._response_times.get(domain, [])
        if not times:
            return

        avg_response = sum(times) / len(times)

        # If responses are slow, increase delay
        if avg_response > 2000:  # > 2 seconds
            self._current_delays[domain] = self.config.max_delay_ms
        elif avg_response > 1000:  # > 1 second
            self._current_delays[domain] = 1500
        elif avg_response > 500:
            self._current_delays[domain] = 1000
        else:
            self._current_delays[domain] = self.config.min_delay_ms

    def get_stats(self, domain: str) -> dict[str, Any]:
        """Get rate limiting stats for a domain."""
        now = time.time()
        requests = self._domain_requests.get(domain, [])
        recent_minute = [t for t in requests if t > now - 60]

        return {
            "requests_last_minute": len(recent_minute),
            "requests_limit": self.config.requests_per_minute,
            "current_delay_ms": self._current_delays.get(domain, self.config.min_delay_ms),
            "avg_response_time_ms": (
                sum(self._response_times.get(domain, [])) /
                len(self._response_times.get(domain, [1]))
            ),
            "can_hard_scrape": self.can_hard_scrape(domain),
            "next_hard_scrape": self.next_hard_scrape_available(domain),
        }

    def reset(self, domain: str | None = None) -> None:
        """
        Reset rate limiting state.

        Args:
            domain: Specific domain to reset, or None for all.
        """
        if domain:
            self._domain_requests.pop(domain, None)
            self._response_times.pop(domain, None)
            self._current_delays.pop(domain, None)
        else:
            self._domain_requests.clear()
            self._response_times.clear()
            self._current_delays.clear()
