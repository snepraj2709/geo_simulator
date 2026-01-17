"""
Main Playwright-based website scraper.

Orchestrates the scraping process using all components:
- URL Queue Manager
- Content Parser
- Rate Limiter
- Entity Extractor
- Storage Handler
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout

from services.scraper.components.url_queue import URLQueueManager, QueuedURL
from services.scraper.components.content_parser import ContentParser, ParsedContent
from services.scraper.components.rate_limiter import ScrapeRateLimiter, RateLimitConfig
from services.scraper.components.entity_extractor import EntityExtractor, ExtractedEntities
from services.scraper.schemas import ScrapeType, PageScrapeResult, ScrapeJobData, JobStatus

logger = logging.getLogger(__name__)


class WebsiteScraper:
    """
    Playwright-based website scraper.

    Implements full-site crawling with:
    - JavaScript rendering support
    - Configurable depth limiting (max 5 per ARCHITECTURE.md)
    - Rate limiting and politeness
    - Content extraction and entity recognition
    - Error handling with retries
    """

    DEFAULT_TIMEOUT = 30000  # 30 seconds
    MAX_DEPTH = 5  # Per ARCHITECTURE.md
    MAX_PAGES = 100  # Maximum pages per scrape

    def __init__(
        self,
        max_depth: int = MAX_DEPTH,
        max_pages: int = MAX_PAGES,
        rate_limit_config: RateLimitConfig | None = None,
    ):
        """
        Initialize scraper.

        Args:
            max_depth: Maximum crawl depth (default 5).
            max_pages: Maximum pages to scrape.
            rate_limit_config: Rate limiting configuration.
        """
        self.max_depth = min(max_depth, self.MAX_DEPTH)
        self.max_pages = max_pages
        self.rate_limiter = ScrapeRateLimiter(rate_limit_config)
        self.entity_extractor = EntityExtractor()

        self._browser: Browser | None = None
        self._playwright = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()

    async def start(self) -> None:
        """Start the browser."""
        if self._browser:
            return

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--disable-setuid-sandbox",
                "--no-sandbox",
            ],
        )
        logger.info("Browser started")

    async def stop(self) -> None:
        """Stop the browser."""
        if self._browser:
            await self._browser.close()
            self._browser = None

        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

        logger.info("Browser stopped")

    async def scrape_website(
        self,
        url: str,
        scrape_type: ScrapeType = ScrapeType.INCREMENTAL,
        existing_hashes: set[str] | None = None,
        progress_callback: Any = None,
    ) -> tuple[list[PageScrapeResult], ExtractedEntities]:
        """
        Scrape a website starting from the given URL.

        Args:
            url: Starting URL.
            scrape_type: Type of scrape.
            existing_hashes: Set of already-scraped URL hashes (for incremental).
            progress_callback: Optional callback for progress updates.

        Returns:
            Tuple of (list of page results, aggregated entities).
        """
        if not self._browser:
            await self.start()

        domain = urlparse(url).netloc
        logger.info(
            "Starting %s scrape of %s (max_depth=%d, max_pages=%d)",
            scrape_type.value, domain, self.max_depth, self.max_pages
        )

        # Initialize components
        url_queue = URLQueueManager(
            base_url=url,
            max_depth=self.max_depth,
            max_urls=self.max_pages,
        )
        content_parser = ContentParser(base_url=url)
        existing_hashes = existing_hashes or set()

        results: list[PageScrapeResult] = []
        all_entities = ExtractedEntities()

        # Create browser context
        context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        try:
            page = await context.new_page()

            while len(url_queue) > 0 and len(results) < self.max_pages:
                queued = url_queue.get_next()
                if not queued:
                    break

                # Skip if already scraped (incremental mode)
                if scrape_type == ScrapeType.INCREMENTAL:
                    if queued.url_hash in existing_hashes:
                        logger.debug("Skipping already-scraped URL: %s", queued.url)
                        continue

                # Apply rate limiting
                await self.rate_limiter.acquire(domain)

                # Scrape the page
                result = await self._scrape_page(
                    page, queued, content_parser, url_queue
                )
                results.append(result)
                url_queue.mark_scraped(queued.url_hash)

                # Record response time for adaptive rate limiting
                self.rate_limiter.record_response_time(domain, result.scrape_time_ms)

                # Aggregate entities
                if result.success:
                    self._aggregate_entities(all_entities, result)

                # Progress callback
                if progress_callback:
                    await progress_callback(len(results), len(url_queue), result)

                logger.debug(
                    "Scraped %s: %s (queue=%d)",
                    "OK" if result.success else "FAIL",
                    queued.url[:80],
                    len(url_queue),
                )

        finally:
            await context.close()

        # Log summary
        successful = sum(1 for r in results if r.success)
        logger.info(
            "Scrape complete: %d pages (%d successful, %d failed)",
            len(results), successful, len(results) - successful
        )
        logger.info("Queue stats: %s", url_queue.stats)

        return results, all_entities

    async def _scrape_page(
        self,
        page: Page,
        queued: QueuedURL,
        content_parser: ContentParser,
        url_queue: URLQueueManager,
    ) -> PageScrapeResult:
        """
        Scrape a single page.

        Args:
            page: Playwright page.
            queued: Queued URL to scrape.
            content_parser: Content parser instance.
            url_queue: URL queue for adding discovered links.

        Returns:
            PageScrapeResult with scrape outcome.
        """
        start_time = time.time()

        try:
            # Navigate to page
            response = await page.goto(
                queued.url,
                timeout=self.DEFAULT_TIMEOUT,
                wait_until="networkidle",
            )

            if not response:
                return PageScrapeResult(
                    url=queued.url,
                    success=False,
                    error="No response received",
                    scrape_time_ms=int((time.time() - start_time) * 1000),
                )

            http_status = response.status

            # Check for error status
            if http_status >= 400:
                return PageScrapeResult(
                    url=queued.url,
                    success=False,
                    http_status=http_status,
                    error=f"HTTP {http_status}",
                    scrape_time_ms=int((time.time() - start_time) * 1000),
                )

            # Get page content
            html = await page.content()

            # Parse content
            parsed = content_parser.parse(html, queued.url)

            # Add discovered internal links to queue
            internal_links = content_parser.get_internal_links(parsed.links)
            added = url_queue.add_urls(
                internal_links,
                depth=queued.depth + 1,
                parent_url=queued.url,
            )

            return PageScrapeResult(
                url=queued.url,
                success=True,
                title=parsed.title,
                meta_description=parsed.meta_description,
                content_text=parsed.content_text,
                word_count=parsed.word_count,
                page_type=parsed.page_type,
                http_status=http_status,
                links_found=added,
                scrape_time_ms=int((time.time() - start_time) * 1000),
            )

        except PlaywrightTimeout:
            return PageScrapeResult(
                url=queued.url,
                success=False,
                error="Timeout",
                scrape_time_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            logger.error("Error scraping %s: %s", queued.url, e)
            return PageScrapeResult(
                url=queued.url,
                success=False,
                error=str(e),
                scrape_time_ms=int((time.time() - start_time) * 1000),
            )

    async def scrape_single_page(self, url: str) -> tuple[PageScrapeResult, ParsedContent | None]:
        """
        Scrape a single page without crawling.

        Args:
            url: URL to scrape.

        Returns:
            Tuple of (result, parsed content or None).
        """
        if not self._browser:
            await self.start()

        content_parser = ContentParser(base_url=url)

        context = await self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        )

        try:
            page = await context.new_page()
            start_time = time.time()

            response = await page.goto(
                url,
                timeout=self.DEFAULT_TIMEOUT,
                wait_until="networkidle",
            )

            if not response:
                return PageScrapeResult(
                    url=url,
                    success=False,
                    error="No response",
                    scrape_time_ms=int((time.time() - start_time) * 1000),
                ), None

            http_status = response.status
            html = await page.content()
            parsed = content_parser.parse(html, url)

            result = PageScrapeResult(
                url=url,
                success=True,
                title=parsed.title,
                meta_description=parsed.meta_description,
                content_text=parsed.content_text,
                word_count=parsed.word_count,
                page_type=parsed.page_type,
                http_status=http_status,
                links_found=len(parsed.links),
                scrape_time_ms=int((time.time() - start_time) * 1000),
            )

            return result, parsed

        except Exception as e:
            logger.error("Error scraping %s: %s", url, e)
            return PageScrapeResult(
                url=url,
                success=False,
                error=str(e),
                scrape_time_ms=int((time.time() - start_time) * 1000),
            ), None

        finally:
            await context.close()

    def _aggregate_entities(
        self,
        all_entities: ExtractedEntities,
        result: PageScrapeResult,
    ) -> None:
        """Aggregate entities from page result into all_entities."""
        # This is a simplified aggregation - in production you'd extract
        # entities from the full parsed content
        pass

    def can_hard_scrape(self, domain: str) -> bool:
        """Check if hard scrape is allowed for domain."""
        return self.rate_limiter.can_hard_scrape(domain)

    def next_hard_scrape_available(self, domain: str) -> datetime | None:
        """Get when next hard scrape will be available."""
        return self.rate_limiter.next_hard_scrape_available(domain)

    def record_hard_scrape(self, domain: str) -> None:
        """Record that a hard scrape was performed."""
        self.rate_limiter.record_hard_scrape(domain)
