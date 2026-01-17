"""
URL Queue Manager component.

Manages the queue of URLs to be scraped for a website,
handling prioritization, deduplication, and depth tracking.
"""

import hashlib
import logging
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from urllib.parse import urljoin, urlparse

logger = logging.getLogger(__name__)


class URLPriority(str, Enum):
    """URL scraping priority levels."""
    HIGH = "high"      # Homepage, key landing pages
    MEDIUM = "medium"  # Product/service pages
    LOW = "low"        # Blog posts, less important pages


@dataclass
class QueuedURL:
    """A URL in the scrape queue."""
    url: str
    depth: int
    priority: URLPriority = URLPriority.MEDIUM
    parent_url: str | None = None
    url_hash: str = field(default="", init=False)

    def __post_init__(self):
        """Compute URL hash after initialization."""
        self.url_hash = self._compute_hash(self.url)

    @staticmethod
    def _compute_hash(url: str) -> str:
        """Compute SHA-256 hash of URL."""
        normalized = url.lower().rstrip("/")
        return hashlib.sha256(normalized.encode()).hexdigest()


class URLQueueManager:
    """
    Manages URL queue for website scraping.

    Features:
    - Priority-based URL queuing
    - URL deduplication via hashing
    - Depth tracking
    - Domain filtering
    """

    def __init__(
        self,
        base_url: str,
        max_depth: int = 5,
        max_urls: int = 100,
        allowed_domains: list[str] | None = None,
    ):
        """
        Initialize URL Queue Manager.

        Args:
            base_url: The starting URL for the scrape.
            max_depth: Maximum crawl depth (default 5 per ARCHITECTURE.md).
            max_urls: Maximum number of URLs to queue.
            allowed_domains: List of allowed domains to crawl.
        """
        self.base_url = base_url
        self.max_depth = max_depth
        self.max_urls = max_urls

        parsed = urlparse(base_url)
        self.base_domain = parsed.netloc
        self.allowed_domains = allowed_domains or [self.base_domain]

        # Priority queues
        self._high_priority: deque[QueuedURL] = deque()
        self._medium_priority: deque[QueuedURL] = deque()
        self._low_priority: deque[QueuedURL] = deque()

        # Track seen URLs
        self._seen_hashes: set[str] = set()
        self._scraped_hashes: set[str] = set()

        # Statistics
        self._stats = {
            "total_queued": 0,
            "total_scraped": 0,
            "duplicates_skipped": 0,
            "depth_exceeded": 0,
            "domain_filtered": 0,
        }

        # Add the base URL
        self.add_url(base_url, depth=0, priority=URLPriority.HIGH)

    @property
    def stats(self) -> dict[str, int]:
        """Get queue statistics."""
        return {
            **self._stats,
            "pending_high": len(self._high_priority),
            "pending_medium": len(self._medium_priority),
            "pending_low": len(self._low_priority),
            "total_pending": len(self),
        }

    def __len__(self) -> int:
        """Return number of pending URLs."""
        return (
            len(self._high_priority) +
            len(self._medium_priority) +
            len(self._low_priority)
        )

    def add_url(
        self,
        url: str,
        depth: int,
        priority: URLPriority = URLPriority.MEDIUM,
        parent_url: str | None = None,
    ) -> bool:
        """
        Add a URL to the queue.

        Args:
            url: URL to add.
            depth: Current crawl depth.
            priority: URL priority level.
            parent_url: URL that linked to this one.

        Returns:
            True if URL was added, False if skipped.
        """
        # Normalize URL
        url = self._normalize_url(url)
        if not url:
            return False

        # Check depth limit
        if depth > self.max_depth:
            self._stats["depth_exceeded"] += 1
            return False

        # Check domain
        if not self._is_allowed_domain(url):
            self._stats["domain_filtered"] += 1
            return False

        # Check for duplicates
        queued = QueuedURL(url=url, depth=depth, priority=priority, parent_url=parent_url)
        if queued.url_hash in self._seen_hashes:
            self._stats["duplicates_skipped"] += 1
            return False

        # Check max URLs limit
        if len(self._seen_hashes) >= self.max_urls:
            logger.debug("Max URLs limit reached: %d", self.max_urls)
            return False

        # Add to appropriate queue
        self._seen_hashes.add(queued.url_hash)
        self._stats["total_queued"] += 1

        if priority == URLPriority.HIGH:
            self._high_priority.append(queued)
        elif priority == URLPriority.LOW:
            self._low_priority.append(queued)
        else:
            self._medium_priority.append(queued)

        logger.debug(
            "Queued URL: %s (depth=%d, priority=%s)",
            url, depth, priority.value
        )
        return True

    def add_urls(
        self,
        urls: list[str],
        depth: int,
        parent_url: str | None = None,
    ) -> int:
        """
        Add multiple URLs to the queue.

        Args:
            urls: List of URLs to add.
            depth: Current crawl depth.
            parent_url: URL that linked to these.

        Returns:
            Number of URLs successfully added.
        """
        added = 0
        for url in urls:
            priority = self._determine_priority(url)
            if self.add_url(url, depth, priority, parent_url):
                added += 1
        return added

    def get_next(self) -> QueuedURL | None:
        """
        Get the next URL to scrape (highest priority first).

        Returns:
            Next URL to scrape or None if queue is empty.
        """
        if self._high_priority:
            return self._high_priority.popleft()
        if self._medium_priority:
            return self._medium_priority.popleft()
        if self._low_priority:
            return self._low_priority.popleft()
        return None

    def mark_scraped(self, url_hash: str) -> None:
        """Mark a URL as scraped."""
        self._scraped_hashes.add(url_hash)
        self._stats["total_scraped"] += 1

    def is_scraped(self, url: str) -> bool:
        """Check if a URL has been scraped."""
        url_hash = QueuedURL._compute_hash(url)
        return url_hash in self._scraped_hashes

    def _normalize_url(self, url: str) -> str | None:
        """
        Normalize a URL for consistent handling.

        Args:
            url: URL to normalize.

        Returns:
            Normalized URL or None if invalid.
        """
        if not url:
            return None

        # Handle relative URLs
        if not url.startswith(("http://", "https://")):
            url = urljoin(self.base_url, url)

        # Parse and validate
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return None

            # Remove fragments
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            if parsed.query:
                normalized += f"?{parsed.query}"

            # Remove trailing slash for consistency
            normalized = normalized.rstrip("/")

            return normalized

        except Exception:
            return None

    def _is_allowed_domain(self, url: str) -> bool:
        """Check if URL domain is allowed."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()

            for allowed in self.allowed_domains:
                allowed = allowed.lower()
                if domain == allowed or domain.endswith(f".{allowed}"):
                    return True

            return False
        except Exception:
            return False

    def _determine_priority(self, url: str) -> URLPriority:
        """
        Determine URL priority based on path patterns.

        Args:
            url: URL to prioritize.

        Returns:
            Priority level for the URL.
        """
        path = urlparse(url).path.lower()

        # High priority patterns
        high_patterns = [
            "/",              # Homepage
            "/pricing",
            "/features",
            "/products",
            "/services",
            "/solutions",
            "/platform",
            "/about",
            "/contact",
        ]
        if path in high_patterns or path == "":
            return URLPriority.HIGH

        # Low priority patterns
        low_patterns = [
            "/blog",
            "/news",
            "/press",
            "/careers",
            "/jobs",
            "/legal",
            "/privacy",
            "/terms",
            "/sitemap",
        ]
        for pattern in low_patterns:
            if pattern in path:
                return URLPriority.LOW

        return URLPriority.MEDIUM

    def get_all_pending(self) -> list[QueuedURL]:
        """Get all pending URLs without removing them."""
        return (
            list(self._high_priority) +
            list(self._medium_priority) +
            list(self._low_priority)
        )

    def clear(self) -> None:
        """Clear all queues and reset state."""
        self._high_priority.clear()
        self._medium_priority.clear()
        self._low_priority.clear()
        self._seen_hashes.clear()
        self._scraped_hashes.clear()
        self._stats = {
            "total_queued": 0,
            "total_scraped": 0,
            "duplicates_skipped": 0,
            "depth_exceeded": 0,
            "domain_filtered": 0,
        }
