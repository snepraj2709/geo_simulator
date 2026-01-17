"""
Website schemas.
"""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl

from services.api.app.schemas.common import PaginationMeta


class WebsiteCreate(BaseModel):
    """Website creation request."""

    url: HttpUrl
    name: str | None = Field(default=None, max_length=255)
    scrape_depth: int = Field(default=3, ge=1, le=10)


class WebsiteAnalysisResponse(BaseModel):
    """Website analysis data."""

    industry: str | None
    business_model: str | None
    primary_offerings: list[dict[str, Any]] | None
    value_propositions: list[str] | None

    class Config:
        from_attributes = True


class WebsiteStatsResponse(BaseModel):
    """Website statistics."""

    pages_scraped: int = 0
    icps_generated: int = 0
    conversations_generated: int = 0
    simulations_run: int = 0


class WebsiteResponse(BaseModel):
    """Website response."""

    id: uuid.UUID
    domain: str
    url: str
    name: str | None
    description: str | None
    status: str
    scrape_depth: int
    last_scraped_at: datetime | None
    last_hard_scrape_at: datetime | None
    created_at: datetime
    analysis: WebsiteAnalysisResponse | None = None
    stats: WebsiteStatsResponse | None = None

    class Config:
        from_attributes = True


class WebsiteListItem(BaseModel):
    """Website list item."""

    id: uuid.UUID
    domain: str
    url: str
    name: str | None
    status: str
    last_scraped_at: datetime | None
    icp_count: int = 0
    conversation_count: int = 0

    class Config:
        from_attributes = True


class WebsiteListResponse(BaseModel):
    """Website list response."""

    data: list[WebsiteListItem]
    pagination: PaginationMeta


class ScrapeRequest(BaseModel):
    """Scrape trigger request."""

    type: Literal["incremental", "hard"] = "incremental"


class ScrapeResponse(BaseModel):
    """Scrape trigger response."""

    job_id: uuid.UUID
    status: str
    type: str
    estimated_pages: int | None = None
