"""
Celery tasks for website scraping.

Implements async scraping tasks using the WebsiteScraper and components.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import settings
from shared.db.postgres_client import get_postgres_client
from shared.models.enums import WebsiteStatus
from shared.queue.celery_app import celery_app

from services.scraper.scraper import WebsiteScraper
from services.scraper.schemas import ScrapeType, JobStatus, ScrapeJobData
from services.scraper.components.storage_handler import StorageHandler

import logging

logger = logging.getLogger(__name__)

# In-memory job tracking (in production, use Redis)
_job_store: dict[str, ScrapeJobData] = {}


def get_job(job_id: str) -> ScrapeJobData | None:
    """Get job data by ID."""
    return _job_store.get(job_id)


def save_job(job: ScrapeJobData) -> None:
    """Save job data."""
    _job_store[str(job.job_id)] = job


async def _run_scrape(
    website_id: uuid.UUID,
    scrape_type: ScrapeType,
    job_id: uuid.UUID,
) -> dict[str, Any]:
    """
    Run the actual scraping process.

    Args:
        website_id: Website UUID to scrape.
        scrape_type: Type of scrape.
        job_id: Job ID for tracking.

    Returns:
        Result dictionary.
    """
    # Get database session
    pg_client = get_postgres_client()
    await pg_client.connect()

    try:
        async with pg_client.session() as session:
            storage = StorageHandler(session)

            # Get website
            website = await storage.get_website(website_id)
            if not website:
                raise ValueError(f"Website not found: {website_id}")

            # Update job status
            job = get_job(str(job_id))
            if job:
                job.status = JobStatus.RUNNING
                job.started_at = datetime.now(timezone.utc)
                save_job(job)

            # Update website status
            await storage.update_website_status(website_id, WebsiteStatus.SCRAPING)

            # Get existing page hashes for incremental scrape
            existing_hashes = set()
            if scrape_type == ScrapeType.INCREMENTAL:
                existing_hashes = await storage.get_existing_page_hashes(website_id)
            elif scrape_type == ScrapeType.HARD:
                # Delete existing pages for hard scrape
                await storage.delete_website_pages(website_id)

            # Create scraper and run
            async with WebsiteScraper(max_depth=website.scrape_depth) as scraper:
                # Check hard scrape cooldown
                if scrape_type == ScrapeType.HARD:
                    if not scraper.can_hard_scrape(website.domain):
                        raise ValueError(
                            f"Hard scrape cooldown active for {website.domain}"
                        )

                # Progress callback
                async def on_progress(completed: int, pending: int, result: Any) -> None:
                    job = get_job(str(job_id))
                    if job:
                        job.completed_pages = completed
                        job.total_pages = completed + pending
                        if not result.success:
                            job.failed_pages += 1
                            job.failed_urls.append(result.url)
                        else:
                            job.scraped_urls.append(result.url)
                        save_job(job)

                # Run scrape
                results, entities = await scraper.scrape_website(
                    url=website.url,
                    scrape_type=scrape_type,
                    existing_hashes=existing_hashes,
                    progress_callback=on_progress,
                )

                # Record hard scrape
                if scrape_type == ScrapeType.HARD:
                    scraper.record_hard_scrape(website.domain)

            # Store results
            pages_to_store = []
            for result in results:
                if result.success:
                    pages_to_store.append({
                        "website_id": website_id,
                        "url": result.url,
                        "title": result.title,
                        "meta_description": result.meta_description,
                        "content_text": result.content_text,
                        "word_count": result.word_count,
                        "page_type": result.page_type,
                        "http_status": result.http_status,
                    })

            if pages_to_store:
                await storage.store_pages_batch(pages_to_store)

            # Store analysis if we have entities
            if entities.products or entities.services:
                await storage.store_website_analysis(
                    website_id=website_id,
                    industry=entities.industries[0] if entities.industries else None,
                    business_model=None,
                    primary_offerings=entities.products + entities.services,
                    value_propositions=entities.benefits,
                    target_markets=None,
                    competitors_mentioned=entities.brands,
                )

            # Update website status
            now = datetime.now(timezone.utc)
            await storage.update_website_status(
                website_id,
                WebsiteStatus.COMPLETED,
                last_scraped_at=now,
                last_hard_scrape_at=now if scrape_type == ScrapeType.HARD else None,
            )

            # Update job status
            job = get_job(str(job_id))
            if job:
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.now(timezone.utc)
                save_job(job)

            successful = sum(1 for r in results if r.success)
            return {
                "status": "completed",
                "website_id": str(website_id),
                "pages_scraped": len(results),
                "pages_successful": successful,
                "pages_failed": len(results) - successful,
            }

    except Exception as e:
        logger.error("Scrape failed: %s", e)

        # Update job status
        job = get_job(str(job_id))
        if job:
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.now(timezone.utc)
            save_job(job)

        # Update website status
        try:
            async with pg_client.session() as session:
                storage = StorageHandler(session)
                await storage.update_website_status(website_id, WebsiteStatus.FAILED)
        except Exception:
            pass

        raise

    finally:
        await pg_client.disconnect()


@celery_app.task(
    bind=True,
    name="services.scraper.app.tasks.scrape_website",
    max_retries=3,
    default_retry_delay=60,
)
def scrape_website(self, website_id: str, scrape_type: str = "incremental", job_id: str = None):
    """
    Scrape a website and extract content.

    Args:
        website_id: UUID of the website to scrape.
        scrape_type: Type of scrape ('incremental' or 'hard').
        job_id: Optional job ID for tracking.
    """
    logger.info(
        "Starting website scrape: website_id=%s, scrape_type=%s, task_id=%s",
        website_id, scrape_type, self.request.id
    )

    try:
        # Generate job ID if not provided
        if not job_id:
            job_id = str(uuid.uuid4())

        # Run async scrape
        result = asyncio.run(_run_scrape(
            website_id=uuid.UUID(website_id),
            scrape_type=ScrapeType(scrape_type),
            job_id=uuid.UUID(job_id),
        ))

        logger.info(
            "Website scrape completed: website_id=%s, pages=%d",
            website_id, result.get("pages_scraped", 0)
        )

        # Trigger ICP generation after successful scrape
        celery_app.send_task(
            "services.classifier.app.tasks.generate_icps",
            args=[website_id],
            queue="classification",
        )

        return result

    except Exception as e:
        logger.error(
            "Website scrape failed: website_id=%s, error=%s",
            website_id, str(e)
        )
        raise self.retry(exc=e, countdown=60, max_retries=3)


@celery_app.task(name="services.scraper.app.tasks.scrape_page")
def scrape_page(website_id: str, url: str):
    """
    Scrape a single page.

    Args:
        website_id: UUID of the website.
        url: URL to scrape.
    """
    logger.info("Scraping page: website_id=%s, url=%s", website_id, url)

    async def _scrape():
        async with WebsiteScraper() as scraper:
            result, parsed = await scraper.scrape_single_page(url)
            return {
                "status": "completed" if result.success else "failed",
                "url": url,
                "title": result.title,
                "word_count": result.word_count,
                "page_type": result.page_type,
                "error": result.error,
            }

    return asyncio.run(_scrape())
