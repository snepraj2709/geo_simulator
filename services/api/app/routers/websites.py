"""
Website management endpoints.
"""

import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from shared.config import settings
from shared.db.redis import RedisCache
from shared.models import ConversationSequence, ICP, ScrapedPage, Website
from shared.models.enums import WebsiteStatus
from shared.queue.celery_app import celery_app

from services.api.app.dependencies import CurrentUser, CurrentWebsite, DBSession
from services.api.app.schemas.common import PaginationMeta, PaginationParams
from services.api.app.schemas.website import (
    ScrapeRequest,
    ScrapeResponse,
    WebsiteCreate,
    WebsiteListItem,
    WebsiteListResponse,
    WebsiteResponse,
    WebsiteStatsResponse,
)

router = APIRouter()


@router.post(
    "",
    response_model=WebsiteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_website(
    request: WebsiteCreate,
    current_user: CurrentUser,
    db: DBSession,
):
    """Submit a new website for tracking."""
    # Extract domain from URL
    parsed = urlparse(str(request.url))
    domain = parsed.netloc.lower()

    # Check if domain already exists for this organization
    result = await db.execute(
        select(Website).where(
            Website.organization_id == current_user.organization_id,
            Website.domain == domain,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Website with domain '{domain}' already exists",
        )

    # Create website
    website = Website(
        organization_id=current_user.organization_id,
        domain=domain,
        url=str(request.url),
        name=request.name,
        scrape_depth=request.scrape_depth,
        status=WebsiteStatus.PENDING.value,
    )
    db.add(website)
    await db.flush()

    # Trigger initial scrape
    celery_app.send_task(
        "services.scraper.app.tasks.scrape_website",
        args=[str(website.id)],
        queue="scraping",
    )

    return WebsiteResponse.model_validate(website)


@router.get(
    "",
    response_model=WebsiteListResponse,
)
async def list_websites(
    current_user: CurrentUser,
    db: DBSession,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
):
    """List all tracked websites."""
    params = PaginationParams(page=page, limit=limit)

    # Build query
    query = select(Website).where(Website.organization_id == current_user.organization_id)

    if status:
        query = query.where(Website.status == status)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Get paginated results
    query = query.offset(params.offset).limit(params.limit).order_by(Website.created_at.desc())
    result = await db.execute(query)
    websites = result.scalars().all()

    # Get counts for each website
    items = []
    for website in websites:
        icp_count = await db.scalar(
            select(func.count()).select_from(ICP).where(ICP.website_id == website.id)
        )
        conv_count = await db.scalar(
            select(func.count())
            .select_from(ConversationSequence)
            .where(ConversationSequence.website_id == website.id)
        )
        item = WebsiteListItem(
            id=website.id,
            domain=website.domain,
            url=website.url,
            name=website.name,
            status=website.status,
            last_scraped_at=website.last_scraped_at,
            icp_count=icp_count or 0,
            conversation_count=conv_count or 0,
        )
        items.append(item)

    return WebsiteListResponse(
        data=items,
        pagination=PaginationMeta.from_params(params, total),
    )


@router.get(
    "/{website_id}",
    response_model=WebsiteResponse,
)
async def get_website(
    website: CurrentWebsite,
    db: DBSession,
):
    """Get website details."""
    # Get statistics
    pages_count = await db.scalar(
        select(func.count()).select_from(ScrapedPage).where(ScrapedPage.website_id == website.id)
    )
    icp_count = await db.scalar(
        select(func.count()).select_from(ICP).where(ICP.website_id == website.id)
    )
    conv_count = await db.scalar(
        select(func.count())
        .select_from(ConversationSequence)
        .where(ConversationSequence.website_id == website.id)
    )

    response = WebsiteResponse.model_validate(website)
    response.stats = WebsiteStatsResponse(
        pages_scraped=pages_count or 0,
        icps_generated=icp_count or 0,
        conversations_generated=conv_count or 0,
        simulations_run=0,  # TODO: Add simulation count
    )

    return response


@router.post(
    "/{website_id}/scrape",
    response_model=ScrapeResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_scrape(
    request: ScrapeRequest,
    website: CurrentWebsite,
    db: DBSession,
):
    """Trigger a scrape for a website."""
    cache = RedisCache(prefix="ratelimit:scrape")

    # Check hard scrape cooldown
    if request.type == "hard":
        last_hard_scrape = website.last_hard_scrape_at
        if last_hard_scrape:
            cooldown = timedelta(days=settings.hard_scrape_cooldown_days)
            next_available = last_hard_scrape + cooldown

            if datetime.now(timezone.utc) < next_available:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "hard_scrape_limit_exceeded",
                        "message": f"Hard scrape limit reached. Next available: {next_available.isoformat()}",
                        "next_available_at": next_available.isoformat(),
                    },
                )

    # Update status
    website.status = WebsiteStatus.PENDING.value

    # Create job ID
    job_id = uuid.uuid4()

    # Trigger scrape task
    celery_app.send_task(
        "services.scraper.app.tasks.scrape_website",
        args=[str(website.id), request.type],
        task_id=str(job_id),
        queue="scraping",
    )

    # Get estimated page count
    pages_count = await db.scalar(
        select(func.count()).select_from(ScrapedPage).where(ScrapedPage.website_id == website.id)
    )

    return ScrapeResponse(
        job_id=job_id,
        status="queued",
        type=request.type,
        estimated_pages=pages_count or website.scrape_depth * 10,
    )


@router.delete(
    "/{website_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_website(
    website: CurrentWebsite,
    db: DBSession,
):
    """Delete a tracked website."""
    await db.delete(website)
    return None
