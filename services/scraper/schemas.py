"""
Pydantic schemas for the scraper service API.

Based on API_SPEC.md scraper endpoints.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class ScrapeType(str, Enum):
    """Type of scrape operation."""
    INCREMENTAL = "incremental"
    HARD = "hard"


class JobStatus(str, Enum):
    """Status of a scrape job."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ==================== Request Schemas ====================


class ScrapeRequest(BaseModel):
    """Request to start a scrape job."""
    type: ScrapeType = Field(
        default=ScrapeType.INCREMENTAL,
        description="Type of scrape: 'incremental' or 'hard'",
    )

    model_config = ConfigDict(use_enum_values=True)


class SubmitUrlRequest(BaseModel):
    """Request to submit a URL for scraping."""
    url: HttpUrl = Field(..., description="URL to scrape")
    website_id: uuid.UUID | None = Field(
        default=None,
        description="Optional website ID to associate with",
    )
    depth: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Maximum crawl depth (1-10)",
    )


# ==================== Response Schemas ====================


class ScrapeJobResponse(BaseModel):
    """Response for a scrape job submission."""
    job_id: uuid.UUID
    status: JobStatus
    type: ScrapeType
    website_id: uuid.UUID
    estimated_pages: int | None = None
    message: str | None = None

    model_config = ConfigDict(use_enum_values=True)


class ScrapeJobStatusResponse(BaseModel):
    """Response for scrape job status check."""
    job_id: uuid.UUID
    status: JobStatus
    type: ScrapeType
    website_id: uuid.UUID
    total_pages: int
    completed_pages: int
    failed_pages: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    progress_percent: float = 0.0

    model_config = ConfigDict(use_enum_values=True)

    @property
    def is_complete(self) -> bool:
        return self.status in (JobStatus.COMPLETED, JobStatus.FAILED)


class ScrapedPageSummary(BaseModel):
    """Summary of a scraped page."""
    id: uuid.UUID
    url: str
    title: str | None
    page_type: str | None
    word_count: int | None
    scraped_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScrapedPageDetail(BaseModel):
    """Detailed view of a scraped page."""
    id: uuid.UUID
    url: str
    url_hash: str
    title: str | None
    meta_description: str | None
    content_text: str | None
    content_html_path: str | None
    word_count: int | None
    page_type: str | None
    http_status: int | None
    scraped_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ScrapedContentResponse(BaseModel):
    """Response for website scraped content."""
    website_id: uuid.UUID
    total_pages: int
    pages: list[ScrapedPageSummary]
    analysis: dict[str, Any] | None = None


class HardScrapeLimitError(BaseModel):
    """Error response when hard scrape limit is exceeded."""
    error: str = "hard_scrape_limit_exceeded"
    message: str
    next_available_at: datetime


# ==================== Internal Schemas ====================


class ScrapeJobData(BaseModel):
    """Internal data structure for tracking scrape jobs."""
    job_id: uuid.UUID
    website_id: uuid.UUID
    type: ScrapeType
    status: JobStatus
    total_pages: int = 0
    completed_pages: int = 0
    failed_pages: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    scraped_urls: list[str] = Field(default_factory=list)
    failed_urls: list[str] = Field(default_factory=list)

    model_config = ConfigDict(use_enum_values=True)

    def to_status_response(self) -> ScrapeJobStatusResponse:
        """Convert to status response."""
        progress = 0.0
        if self.total_pages > 0:
            progress = (self.completed_pages / self.total_pages) * 100

        return ScrapeJobStatusResponse(
            job_id=self.job_id,
            status=self.status,
            type=self.type,
            website_id=self.website_id,
            total_pages=self.total_pages,
            completed_pages=self.completed_pages,
            failed_pages=self.failed_pages,
            started_at=self.started_at,
            completed_at=self.completed_at,
            error=self.error,
            progress_percent=round(progress, 1),
        )


class PageScrapeResult(BaseModel):
    """Result of scraping a single page."""
    url: str
    success: bool
    title: str | None = None
    meta_description: str | None = None
    content_text: str | None = None
    word_count: int = 0
    page_type: str = "unknown"
    http_status: int | None = None
    error: str | None = None
    links_found: int = 0
    scrape_time_ms: int = 0
