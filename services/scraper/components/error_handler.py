"""
Error handling utilities for the scraper service.

Provides error categorization, retry logic, and circuit breaker pattern.
"""

import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ErrorCategory(str, Enum):
    """Categories of errors for retry logic."""
    TRANSIENT = "transient"  # Temporary errors, should retry
    PERMANENT = "permanent"  # Permanent errors, don't retry
    RATE_LIMIT = "rate_limit"  # Rate limiting, backoff and retry
    TIMEOUT = "timeout"  # Timeout errors, retry with longer timeout
    AUTH = "auth"  # Authentication errors, don't retry
    NOT_FOUND = "not_found"  # 404 errors, don't retry


def categorize_error(error: Exception, http_status: int | None = None) -> ErrorCategory:
    """
    Categorize an error for retry logic.

    Args:
        error: The exception that occurred.
        http_status: HTTP status code if available.

    Returns:
        ErrorCategory for the error.
    """
    error_str = str(error).lower()

    # HTTP status-based categorization
    if http_status:
        if http_status == 404:
            return ErrorCategory.NOT_FOUND
        elif http_status == 401 or http_status == 403:
            return ErrorCategory.AUTH
        elif http_status == 429:
            return ErrorCategory.RATE_LIMIT
        elif 500 <= http_status < 600:
            return ErrorCategory.TRANSIENT
        elif 400 <= http_status < 500:
            return ErrorCategory.PERMANENT

    # Exception type-based categorization
    if "timeout" in error_str:
        return ErrorCategory.TIMEOUT
    elif "connection" in error_str or "network" in error_str:
        return ErrorCategory.TRANSIENT
    elif "rate limit" in error_str or "too many requests" in error_str:
        return ErrorCategory.RATE_LIMIT
    elif "not found" in error_str:
        return ErrorCategory.NOT_FOUND
    elif "unauthorized" in error_str or "forbidden" in error_str:
        return ErrorCategory.AUTH

    # Default to transient for unknown errors
    return ErrorCategory.TRANSIENT


def should_retry(category: ErrorCategory, attempt: int, max_retries: int = 3) -> bool:
    """
    Determine if an error should be retried.

    Args:
        category: Error category.
        attempt: Current attempt number (0-indexed).
        max_retries: Maximum number of retries.

    Returns:
        True if should retry, False otherwise.
    """
    if attempt >= max_retries:
        return False

    # Don't retry permanent errors
    if category in (ErrorCategory.PERMANENT, ErrorCategory.AUTH, ErrorCategory.NOT_FOUND):
        return False

    # Retry transient, timeout, and rate limit errors
    return category in (ErrorCategory.TRANSIENT, ErrorCategory.TIMEOUT, ErrorCategory.RATE_LIMIT)


def get_retry_delay(category: ErrorCategory, attempt: int) -> float:
    """
    Calculate retry delay with exponential backoff.

    Args:
        category: Error category.
        attempt: Current attempt number (0-indexed).

    Returns:
        Delay in seconds.
    """
    base_delay = 1.0  # 1 second base delay

    if category == ErrorCategory.RATE_LIMIT:
        # Longer delays for rate limiting
        base_delay = 5.0
    elif category == ErrorCategory.TIMEOUT:
        # Moderate delays for timeouts
        base_delay = 2.0

    # Exponential backoff: 1s, 2s, 4s, 8s, ...
    delay = base_delay * (2 ** attempt)

    # Cap at 60 seconds
    return min(delay, 60.0)


class CircuitBreaker:
    """
    Circuit breaker pattern for failing domains.

    Prevents repeated attempts to scrape domains that are consistently failing.
    """

    def __init__(
        self,
        failure_threshold: float = 0.8,  # 80% failure rate
        min_attempts: int = 5,  # Minimum attempts before opening circuit
        timeout: timedelta = timedelta(minutes=15),  # How long circuit stays open
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Failure rate threshold (0.0-1.0).
            min_attempts: Minimum attempts before circuit can open.
            timeout: How long to keep circuit open.
        """
        self.failure_threshold = failure_threshold
        self.min_attempts = min_attempts
        self.timeout = timeout

        # Track domain statistics
        self._domain_stats: dict[str, dict[str, Any]] = {}

    def record_success(self, domain: str) -> None:
        """Record a successful request for a domain."""
        if domain not in self._domain_stats:
            self._domain_stats[domain] = {
                "successes": 0,
                "failures": 0,
                "opened_at": None,
            }

        self._domain_stats[domain]["successes"] += 1

        # Reset circuit if it was open
        if self._domain_stats[domain]["opened_at"]:
            logger.info("Circuit breaker reset for domain: %s", domain)
            self._domain_stats[domain]["opened_at"] = None

    def record_failure(self, domain: str) -> None:
        """Record a failed request for a domain."""
        if domain not in self._domain_stats:
            self._domain_stats[domain] = {
                "successes": 0,
                "failures": 0,
                "opened_at": None,
            }

        self._domain_stats[domain]["failures"] += 1

        # Check if circuit should open
        stats = self._domain_stats[domain]
        total = stats["successes"] + stats["failures"]

        if total >= self.min_attempts:
            failure_rate = stats["failures"] / total

            if failure_rate >= self.failure_threshold and not stats["opened_at"]:
                stats["opened_at"] = datetime.now(timezone.utc)
                logger.warning(
                    "Circuit breaker opened for domain: %s (failure rate: %.1f%%)",
                    domain,
                    failure_rate * 100,
                )

    def is_open(self, domain: str) -> bool:
        """
        Check if circuit is open for a domain.

        Returns:
            True if circuit is open (requests should be blocked).
        """
        if domain not in self._domain_stats:
            return False

        opened_at = self._domain_stats[domain]["opened_at"]
        if not opened_at:
            return False

        # Check if timeout has passed
        if datetime.now(timezone.utc) - opened_at > self.timeout:
            # Reset circuit
            logger.info("Circuit breaker timeout expired for domain: %s", domain)
            self._domain_stats[domain]["opened_at"] = None
            self._domain_stats[domain]["successes"] = 0
            self._domain_stats[domain]["failures"] = 0
            return False

        return True

    def get_stats(self, domain: str) -> dict[str, Any]:
        """Get statistics for a domain."""
        if domain not in self._domain_stats:
            return {
                "successes": 0,
                "failures": 0,
                "failure_rate": 0.0,
                "is_open": False,
            }

        stats = self._domain_stats[domain]
        total = stats["successes"] + stats["failures"]
        failure_rate = stats["failures"] / total if total > 0 else 0.0

        return {
            "successes": stats["successes"],
            "failures": stats["failures"],
            "failure_rate": failure_rate,
            "is_open": self.is_open(domain),
            "opened_at": stats["opened_at"],
        }

    def reset(self, domain: str) -> None:
        """Reset circuit breaker for a domain."""
        if domain in self._domain_stats:
            self._domain_stats[domain] = {
                "successes": 0,
                "failures": 0,
                "opened_at": None,
            }
            logger.info("Circuit breaker manually reset for domain: %s", domain)
