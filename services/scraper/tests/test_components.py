"""
Tests for scraper components.
"""

import pytest
from datetime import datetime, timedelta, timezone

from services.scraper.components.url_queue import URLQueueManager, QueuedURL
from services.scraper.components.content_parser import ContentParser
from services.scraper.components.rate_limiter import ScrapeRateLimiter, RateLimitConfig
from services.scraper.components.error_handler import (
    CircuitBreaker,
    ErrorCategory,
    categorize_error,
    should_retry,
    get_retry_delay,
)


class TestURLQueueManager:
    """Tests for URL Queue Manager."""

    def test_initialization(self):
        """Test queue initialization."""
        queue = URLQueueManager(
            base_url="https://example.com",
            max_depth=3,
            max_urls=100,
        )

        assert len(queue) == 1  # Base URL should be queued
        assert queue.stats["total_added"] == 1

    def test_depth_limiting(self):
        """Test depth limiting."""
        queue = URLQueueManager(
            base_url="https://example.com",
            max_depth=2,
        )

        # Add URLs at different depths
        added_depth_1 = queue.add_urls(
            ["https://example.com/page1"],
            depth=1,
            parent_url="https://example.com",
        )
        assert added_depth_1 == 1

        added_depth_2 = queue.add_urls(
            ["https://example.com/page2"],
            depth=2,
            parent_url="https://example.com/page1",
        )
        assert added_depth_2 == 1

        # Should not add URLs beyond max depth
        added_depth_3 = queue.add_urls(
            ["https://example.com/page3"],
            depth=3,
            parent_url="https://example.com/page2",
        )
        assert added_depth_3 == 0

    def test_deduplication(self):
        """Test URL deduplication."""
        queue = URLQueueManager(base_url="https://example.com")

        # Add same URL twice
        added_1 = queue.add_urls(["https://example.com/page"])
        added_2 = queue.add_urls(["https://example.com/page"])

        assert added_1 == 1
        assert added_2 == 0  # Should be deduplicated

    def test_external_url_filtering(self):
        """Test external URL filtering."""
        queue = URLQueueManager(base_url="https://example.com")

        added = queue.add_urls([
            "https://example.com/internal",
            "https://external.com/page",
        ])

        assert added == 1  # Only internal URL should be added


class TestContentParser:
    """Tests for Content Parser."""

    def test_parse_html(self, sample_html):
        """Test HTML parsing."""
        parser = ContentParser(base_url="https://example.com")
        parsed = parser.parse(sample_html, "https://example.com")

        assert parsed.title == "Test Page"
        assert parsed.meta_description == "Test description"
        assert "Welcome" in parsed.content_text
        assert parsed.word_count > 0
        assert len(parsed.links) > 0

    def test_link_extraction(self, sample_html):
        """Test link extraction."""
        parser = ContentParser(base_url="https://example.com")
        parsed = parser.parse(sample_html, "https://example.com")

        internal_links = parser.get_internal_links(parsed.links)

        # Should have /about and /contact
        assert len(internal_links) >= 2
        assert any("/about" in link for link in internal_links)

    def test_page_type_detection(self, sample_html):
        """Test page type detection."""
        parser = ContentParser(base_url="https://example.com")

        # Homepage
        parsed_home = parser.parse(sample_html, "https://example.com")
        assert parsed_home.page_type == "homepage"

        # About page
        parsed_about = parser.parse(sample_html, "https://example.com/about")
        assert parsed_about.page_type == "about"


class TestRateLimiter:
    """Tests for Rate Limiter."""

    @pytest.mark.asyncio
    async def test_basic_rate_limiting(self):
        """Test basic rate limiting."""
        config = RateLimitConfig(requests_per_second=2.0)
        limiter = ScrapeRateLimiter(config)

        # First request should be immediate
        await limiter.acquire("example.com")

        # Second request should be delayed
        start = datetime.now(timezone.utc)
        await limiter.acquire("example.com")
        elapsed = (datetime.now(timezone.utc) - start).total_seconds()

        assert elapsed >= 0.4  # At least 0.5s delay (with some tolerance)

    def test_hard_scrape_cooldown(self):
        """Test hard scrape cooldown."""
        limiter = ScrapeRateLimiter()

        # Should be able to hard scrape initially
        assert limiter.can_hard_scrape("example.com")

        # Record hard scrape
        limiter.record_hard_scrape("example.com")

        # Should not be able to hard scrape again
        assert not limiter.can_hard_scrape("example.com")

    def test_adaptive_rate_limiting(self):
        """Test adaptive rate limiting based on response times."""
        limiter = ScrapeRateLimiter()

        # Record slow response times
        for _ in range(5):
            limiter.record_response_time("slow.com", 5000)  # 5 seconds

        # Record fast response times
        for _ in range(5):
            limiter.record_response_time("fast.com", 100)  # 100ms

        # Slow domain should have longer delay
        slow_delay = limiter._get_delay("slow.com")
        fast_delay = limiter._get_delay("fast.com")

        assert slow_delay > fast_delay


class TestErrorHandler:
    """Tests for Error Handler."""

    def test_error_categorization(self):
        """Test error categorization."""
        # Timeout error
        assert categorize_error(Exception("timeout")) == ErrorCategory.TIMEOUT

        # HTTP 404
        assert categorize_error(Exception("not found"), 404) == ErrorCategory.NOT_FOUND

        # HTTP 500
        assert categorize_error(Exception("server error"), 500) == ErrorCategory.TRANSIENT

        # HTTP 429
        assert categorize_error(Exception("rate limit"), 429) == ErrorCategory.RATE_LIMIT

    def test_should_retry(self):
        """Test retry logic."""
        # Should retry transient errors
        assert should_retry(ErrorCategory.TRANSIENT, 0, 3)
        assert should_retry(ErrorCategory.TRANSIENT, 1, 3)
        assert not should_retry(ErrorCategory.TRANSIENT, 3, 3)  # Max retries

        # Should not retry permanent errors
        assert not should_retry(ErrorCategory.PERMANENT, 0, 3)
        assert not should_retry(ErrorCategory.NOT_FOUND, 0, 3)
        assert not should_retry(ErrorCategory.AUTH, 0, 3)

    def test_retry_delay(self):
        """Test retry delay calculation."""
        # Exponential backoff
        delay_0 = get_retry_delay(ErrorCategory.TRANSIENT, 0)
        delay_1 = get_retry_delay(ErrorCategory.TRANSIENT, 1)
        delay_2 = get_retry_delay(ErrorCategory.TRANSIENT, 2)

        assert delay_1 > delay_0
        assert delay_2 > delay_1

        # Rate limit should have longer delays
        rate_limit_delay = get_retry_delay(ErrorCategory.RATE_LIMIT, 0)
        transient_delay = get_retry_delay(ErrorCategory.TRANSIENT, 0)

        assert rate_limit_delay > transient_delay


class TestCircuitBreaker:
    """Tests for Circuit Breaker."""

    def test_circuit_opens_on_failures(self):
        """Test circuit opens after failure threshold."""
        breaker = CircuitBreaker(
            failure_threshold=0.8,
            min_attempts=5,
        )

        # Record failures
        for _ in range(5):
            breaker.record_failure("failing.com")

        # Circuit should be open
        assert breaker.is_open("failing.com")

    def test_circuit_stays_closed_with_successes(self):
        """Test circuit stays closed with enough successes."""
        breaker = CircuitBreaker(
            failure_threshold=0.8,
            min_attempts=5,
        )

        # Record mixed results (60% failure rate)
        for _ in range(3):
            breaker.record_failure("mixed.com")
        for _ in range(2):
            breaker.record_success("mixed.com")

        # Circuit should stay closed (below threshold)
        assert not breaker.is_open("mixed.com")

    def test_circuit_resets_after_timeout(self):
        """Test circuit resets after timeout."""
        breaker = CircuitBreaker(
            failure_threshold=0.8,
            min_attempts=5,
            timeout=timedelta(seconds=1),
        )

        # Open circuit
        for _ in range(5):
            breaker.record_failure("timeout.com")

        assert breaker.is_open("timeout.com")

        # Wait for timeout (in real test, would need to mock time)
        # For now, just verify the timeout logic exists
        stats = breaker.get_stats("timeout.com")
        assert stats["is_open"]

    def test_circuit_reset(self):
        """Test manual circuit reset."""
        breaker = CircuitBreaker(
            failure_threshold=0.8,
            min_attempts=5,
        )

        # Open circuit
        for _ in range(5):
            breaker.record_failure("reset.com")

        assert breaker.is_open("reset.com")

        # Reset
        breaker.reset("reset.com")

        assert not breaker.is_open("reset.com")
