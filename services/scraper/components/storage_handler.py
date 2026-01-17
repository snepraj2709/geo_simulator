"""
Storage Handler component.

Handles storing scraped content to PostgreSQL and S3.
"""

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import settings
from shared.models.website import ScrapedPage, Website, WebsiteAnalysis
from shared.models.enums import WebsiteStatus

logger = logging.getLogger(__name__)


class StorageHandler:
    """
    Handles storage of scraped content.

    Features:
    - PostgreSQL storage for page metadata
    - S3 storage for raw HTML content
    - Upsert support for incremental updates
    - Batch operations for efficiency
    """

    def __init__(self, session: AsyncSession, s3_client: Any = None):
        """
        Initialize Storage Handler.

        Args:
            session: SQLAlchemy async session.
            s3_client: Optional S3 client for HTML storage.
        """
        self.session = session
        self.s3_client = s3_client
        self.s3_bucket = settings.s3_bucket

    async def get_website(self, website_id: uuid.UUID) -> Website | None:
        """
        Get website by ID.

        Args:
            website_id: Website UUID.

        Returns:
            Website or None if not found.
        """
        result = await self.session.execute(
            select(Website).where(Website.id == website_id)
        )
        return result.scalar_one_or_none()

    async def update_website_status(
        self,
        website_id: uuid.UUID,
        status: WebsiteStatus,
        last_scraped_at: datetime | None = None,
        last_hard_scrape_at: datetime | None = None,
    ) -> None:
        """
        Update website status.

        Args:
            website_id: Website UUID.
            status: New status.
            last_scraped_at: Last scrape timestamp.
            last_hard_scrape_at: Last hard scrape timestamp.
        """
        values = {"status": status.value}
        if last_scraped_at:
            values["last_scraped_at"] = last_scraped_at
        if last_hard_scrape_at:
            values["last_hard_scrape_at"] = last_hard_scrape_at

        await self.session.execute(
            update(Website).where(Website.id == website_id).values(**values)
        )
        await self.session.commit()

    async def store_page(
        self,
        website_id: uuid.UUID,
        url: str,
        title: str | None,
        meta_description: str | None,
        content_text: str,
        word_count: int,
        page_type: str,
        http_status: int,
        raw_html: str | None = None,
    ) -> ScrapedPage:
        """
        Store a scraped page.

        Uses upsert to handle incremental scrapes.

        Args:
            website_id: Parent website UUID.
            url: Page URL.
            title: Page title.
            meta_description: Meta description.
            content_text: Extracted text content.
            word_count: Word count.
            page_type: Type of page.
            http_status: HTTP status code.
            raw_html: Optional raw HTML for S3 storage.

        Returns:
            Stored ScrapedPage.
        """
        url_hash = self._compute_url_hash(url)
        now = datetime.now(timezone.utc)

        # Store HTML to S3 if provided
        html_path = None
        if raw_html and self.s3_client:
            html_path = await self._store_html_to_s3(website_id, url_hash, raw_html)

        # Upsert page data
        stmt = insert(ScrapedPage).values(
            id=uuid.uuid4(),
            website_id=website_id,
            url=url,
            url_hash=url_hash,
            title=title,
            meta_description=meta_description,
            content_text=content_text,
            content_html_path=html_path,
            word_count=word_count,
            page_type=page_type,
            http_status=http_status,
            scraped_at=now,
        )

        stmt = stmt.on_conflict_do_update(
            constraint="uq_scraped_pages_website_url",
            set_={
                "title": stmt.excluded.title,
                "meta_description": stmt.excluded.meta_description,
                "content_text": stmt.excluded.content_text,
                "content_html_path": stmt.excluded.content_html_path,
                "word_count": stmt.excluded.word_count,
                "page_type": stmt.excluded.page_type,
                "http_status": stmt.excluded.http_status,
                "scraped_at": stmt.excluded.scraped_at,
            },
        ).returning(ScrapedPage)

        result = await self.session.execute(stmt)
        await self.session.commit()

        return result.scalar_one()

    async def store_pages_batch(
        self,
        pages: list[dict[str, Any]],
    ) -> int:
        """
        Store multiple pages in a batch.

        Args:
            pages: List of page data dictionaries.

        Returns:
            Number of pages stored.
        """
        if not pages:
            return 0

        now = datetime.now(timezone.utc)
        values = []

        for page in pages:
            values.append({
                "id": uuid.uuid4(),
                "website_id": page["website_id"],
                "url": page["url"],
                "url_hash": self._compute_url_hash(page["url"]),
                "title": page.get("title"),
                "meta_description": page.get("meta_description"),
                "content_text": page.get("content_text", ""),
                "content_html_path": page.get("content_html_path"),
                "word_count": page.get("word_count", 0),
                "page_type": page.get("page_type", "unknown"),
                "http_status": page.get("http_status", 200),
                "scraped_at": now,
            })

        stmt = insert(ScrapedPage).values(values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_scraped_pages_website_url",
            set_={
                "title": stmt.excluded.title,
                "meta_description": stmt.excluded.meta_description,
                "content_text": stmt.excluded.content_text,
                "content_html_path": stmt.excluded.content_html_path,
                "word_count": stmt.excluded.word_count,
                "page_type": stmt.excluded.page_type,
                "http_status": stmt.excluded.http_status,
                "scraped_at": stmt.excluded.scraped_at,
            },
        )

        await self.session.execute(stmt)
        await self.session.commit()

        return len(values)

    async def store_website_analysis(
        self,
        website_id: uuid.UUID,
        industry: str | None,
        business_model: str | None,
        primary_offerings: list[dict[str, Any]] | None,
        value_propositions: list[str] | None,
        target_markets: list[str] | None,
        competitors_mentioned: list[str] | None,
    ) -> WebsiteAnalysis:
        """
        Store website analysis results.

        Args:
            website_id: Website UUID.
            industry: Detected industry.
            business_model: Business model type.
            primary_offerings: Products/services.
            value_propositions: Value props.
            target_markets: Target markets.
            competitors_mentioned: Competitor brands.

        Returns:
            Stored WebsiteAnalysis.
        """
        now = datetime.now(timezone.utc)

        stmt = insert(WebsiteAnalysis).values(
            id=uuid.uuid4(),
            website_id=website_id,
            industry=industry,
            business_model=business_model,
            primary_offerings=primary_offerings,
            value_propositions=value_propositions,
            target_markets=target_markets,
            competitors_mentioned=competitors_mentioned,
            analyzed_at=now,
        )

        stmt = stmt.on_conflict_do_update(
            index_elements=["website_id"],
            set_={
                "industry": stmt.excluded.industry,
                "business_model": stmt.excluded.business_model,
                "primary_offerings": stmt.excluded.primary_offerings,
                "value_propositions": stmt.excluded.value_propositions,
                "target_markets": stmt.excluded.target_markets,
                "competitors_mentioned": stmt.excluded.competitors_mentioned,
                "analyzed_at": stmt.excluded.analyzed_at,
            },
        ).returning(WebsiteAnalysis)

        result = await self.session.execute(stmt)
        await self.session.commit()

        return result.scalar_one()

    async def get_existing_page_hashes(
        self,
        website_id: uuid.UUID,
    ) -> set[str]:
        """
        Get URL hashes of existing pages for incremental scrape.

        Args:
            website_id: Website UUID.

        Returns:
            Set of URL hashes.
        """
        result = await self.session.execute(
            select(ScrapedPage.url_hash).where(ScrapedPage.website_id == website_id)
        )
        return {row[0] for row in result.fetchall()}

    async def get_page_count(self, website_id: uuid.UUID) -> int:
        """
        Get count of pages for a website.

        Args:
            website_id: Website UUID.

        Returns:
            Page count.
        """
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.count()).select_from(ScrapedPage).where(
                ScrapedPage.website_id == website_id
            )
        )
        return result.scalar() or 0

    async def delete_website_pages(self, website_id: uuid.UUID) -> int:
        """
        Delete all pages for a website (for hard scrape).

        Args:
            website_id: Website UUID.

        Returns:
            Number of pages deleted.
        """
        from sqlalchemy import delete

        result = await self.session.execute(
            delete(ScrapedPage).where(ScrapedPage.website_id == website_id)
        )
        await self.session.commit()

        return result.rowcount

    def _compute_url_hash(self, url: str) -> str:
        """Compute SHA-256 hash of URL."""
        normalized = url.lower().rstrip("/")
        return hashlib.sha256(normalized.encode()).hexdigest()

    async def _store_html_to_s3(
        self,
        website_id: uuid.UUID,
        url_hash: str,
        html: str,
    ) -> str:
        """
        Store raw HTML to S3.

        Args:
            website_id: Website UUID.
            url_hash: URL hash for path.
            html: Raw HTML content.

        Returns:
            S3 path.
        """
        path = f"scraped-content/{website_id}/{url_hash}/raw.html"

        try:
            await self.s3_client.put_object(
                Bucket=self.s3_bucket,
                Key=path,
                Body=html.encode("utf-8"),
                ContentType="text/html",
            )
            return path
        except Exception as e:
            logger.error("Failed to store HTML to S3: %s", e)
            return None
