"""
Website Scraper Service FastAPI Application.

Endpoints as specified in API_SPEC.md:
- POST /scrape - Submit URL for scraping
- GET /scrape/{job_id}/status - Check job status
- GET /scrape/{website_id}/content - Get scraped content
"""

import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Depends, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import settings
from shared.db.postgres_client import get_postgres_client, get_session
from shared.models.website import Website, ScrapedPage, WebsiteAnalysis
from shared.models.enums import WebsiteStatus
from shared.queue.celery_app import celery_app

from services.scraper.schemas import (
    ScrapeRequest,
    ScrapeType,
    ScrapeJobResponse,
    ScrapeJobStatusResponse,
    ScrapedContentResponse,
    ScrapedPageSummary,
    ScrapedPageDetail,
    HardScrapeLimitError,
    JobStatus,
    ScrapeJobData,
)
from services.scraper.components.rate_limiter import ScrapeRateLimiter
from services.scraper.app.tasks import get_job, save_job

# Create FastAPI app
app = FastAPI(
    title="Website Scraper Service",
    description="Web scraping service for LLM Brand Monitor",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiter for hard scrape checks
rate_limiter = ScrapeRateLimiter()


# ==================== Dependencies ====================


async def get_db() -> AsyncSession:
    """Get database session."""
    client = get_postgres_client()
    if not client.is_connected:
        await client.connect()
    async with client.session() as session:
        yield session


# ==================== Health Check ====================


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "scraper"}


# ==================== Scrape Endpoints ====================


@app.post(
    "/scrape",
    response_model=ScrapeJobResponse,
    status_code=202,
    responses={
        429: {"model": HardScrapeLimitError, "description": "Hard scrape limit exceeded"},
    },
)
async def submit_scrape(
    website_id: uuid.UUID,
    request: ScrapeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a website for scraping.

    Triggers either an incremental or hard scrape of the website.
    Hard scrapes are limited to 1 per week per website.
    """
    # Get website
    result = await db.execute(
        select(Website).where(Website.id == website_id)
    )
    website = result.scalar_one_or_none()

    if not website:
        raise HTTPException(status_code=404, detail="Website not found")

    # Check hard scrape cooldown
    if request.type == ScrapeType.HARD:
        if not rate_limiter.can_hard_scrape(website.domain):
            next_available = rate_limiter.next_hard_scrape_available(website.domain)
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "hard_scrape_limit_exceeded",
                    "message": f"Hard scrape limit reached. Next available: {next_available.isoformat()}",
                    "next_available_at": next_available.isoformat(),
                },
            )

    # Check if website is already being scraped
    if website.status == WebsiteStatus.SCRAPING.value:
        raise HTTPException(
            status_code=409,
            detail="Website is already being scraped",
        )

    # Create job
    job_id = uuid.uuid4()
    job = ScrapeJobData(
        job_id=job_id,
        website_id=website_id,
        type=request.type,
        status=JobStatus.QUEUED,
    )
    save_job(job)

    # Estimate pages based on previous scrapes
    page_count_result = await db.execute(
        select(func.count()).select_from(ScrapedPage).where(
            ScrapedPage.website_id == website_id
        )
    )
    estimated_pages = page_count_result.scalar() or website.scrape_depth * 10

    # Submit Celery task
    celery_app.send_task(
        "services.scraper.app.tasks.scrape_website",
        args=[str(website_id), request.type.value, str(job_id)],
        queue="scraping",
    )

    return ScrapeJobResponse(
        job_id=job_id,
        status=JobStatus.QUEUED,
        type=request.type,
        website_id=website_id,
        estimated_pages=estimated_pages,
        message=f"{request.type.value.title()} scrape queued for {website.domain}",
    )


@app.get(
    "/scrape/{job_id}/status",
    response_model=ScrapeJobStatusResponse,
)
async def get_scrape_status(
    job_id: uuid.UUID = Path(..., description="Scrape job ID"),
):
    """
    Get the status of a scrape job.

    Returns current progress, page counts, and any errors.
    """
    job = get_job(str(job_id))

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job.to_status_response()


@app.get(
    "/scrape/{website_id}/content",
    response_model=ScrapedContentResponse,
)
async def get_scraped_content(
    website_id: uuid.UUID = Path(..., description="Website ID"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    page_type: str | None = Query(None, description="Filter by page type"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get scraped content for a website.

    Returns paginated list of scraped pages with optional filtering.
    """
    # Verify website exists
    website_result = await db.execute(
        select(Website).where(Website.id == website_id)
    )
    website = website_result.scalar_one_or_none()

    if not website:
        raise HTTPException(status_code=404, detail="Website not found")

    # Build query
    query = select(ScrapedPage).where(ScrapedPage.website_id == website_id)

    if page_type:
        query = query.where(ScrapedPage.page_type == page_type)

    # Get total count
    count_query = select(func.count()).select_from(ScrapedPage).where(
        ScrapedPage.website_id == website_id
    )
    if page_type:
        count_query = count_query.where(ScrapedPage.page_type == page_type)

    total_result = await db.execute(count_query)
    total_pages = total_result.scalar() or 0

    # Get paginated results
    offset = (page - 1) * limit
    query = query.order_by(ScrapedPage.scraped_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    pages = result.scalars().all()

    # Get analysis if available
    analysis_result = await db.execute(
        select(WebsiteAnalysis).where(WebsiteAnalysis.website_id == website_id)
    )
    analysis = analysis_result.scalar_one_or_none()

    analysis_dict = None
    if analysis:
        analysis_dict = {
            "industry": analysis.industry,
            "business_model": analysis.business_model,
            "primary_offerings": analysis.primary_offerings,
            "value_propositions": analysis.value_propositions,
            "target_markets": analysis.target_markets,
            "competitors_mentioned": analysis.competitors_mentioned,
            "analyzed_at": analysis.analyzed_at.isoformat() if analysis.analyzed_at else None,
        }

    return ScrapedContentResponse(
        website_id=website_id,
        total_pages=total_pages,
        pages=[
            ScrapedPageSummary(
                id=p.id,
                url=p.url,
                title=p.title,
                page_type=p.page_type,
                word_count=p.word_count,
                scraped_at=p.scraped_at,
            )
            for p in pages
        ],
        analysis=analysis_dict,
    )


@app.get(
    "/scrape/{website_id}/pages/{page_id}",
    response_model=ScrapedPageDetail,
)
async def get_page_detail(
    website_id: uuid.UUID = Path(..., description="Website ID"),
    page_id: uuid.UUID = Path(..., description="Page ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed information about a scraped page.

    Returns full page content including text and metadata.
    """
    result = await db.execute(
        select(ScrapedPage).where(
            ScrapedPage.id == page_id,
            ScrapedPage.website_id == website_id,
        )
    )
    page = result.scalar_one_or_none()

    if not page:
        raise HTTPException(status_code=404, detail="Page not found")

    return ScrapedPageDetail.model_validate(page)


# ==================== Startup/Shutdown ====================


@app.on_event("startup")
async def startup_event():
    """Initialize database connection on startup."""
    client = get_postgres_client()
    await client.connect()


@app.on_event("shutdown")
async def shutdown_event():
    """Close database connection on shutdown."""
    client = get_postgres_client()
    await client.disconnect()


# ==================== Run with Uvicorn ====================


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "services.scraper.main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.app_debug,
    )
