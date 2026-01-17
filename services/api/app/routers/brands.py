"""
Brand analysis endpoints.
"""

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select

from shared.models import Brand, LLMBrandState

from services.api.app.dependencies import CurrentWebsite, DBSession
from services.api.app.schemas.common import PaginationMeta, PaginationParams

router = APIRouter()


class BrandStats(BaseModel):
    """Brand statistics."""

    total_mentions: int = 0
    recommendations: int = 0
    comparisons: int = 0
    avg_position: float | None = None


class BrandListItem(BaseModel):
    """Brand list item."""

    id: uuid.UUID
    name: str
    domain: str | None
    is_tracked: bool
    stats: BrandStats

    class Config:
        from_attributes = True


class BrandListResponse(BaseModel):
    """Brand list response."""

    data: list[BrandListItem]
    pagination: PaginationMeta


class PresenceBreakdown(BaseModel):
    """Brand presence breakdown."""

    ignored: int = 0
    mentioned: int = 0
    trusted: int = 0
    recommended: int = 0
    compared: int = 0


class ProviderStats(BaseModel):
    """Per-provider statistics."""

    mentions: int = 0
    recommendations: int = 0
    avg_position: float | None = None


class BeliefDistribution(BaseModel):
    """Belief type distribution."""

    truth: int = 0
    superiority: int = 0
    outcome: int = 0
    transaction: int = 0
    identity: int = 0
    social_proof: int = 0


class BrandAnalysisResponse(BaseModel):
    """Brand analysis response."""

    brand: BrandListItem
    presence_breakdown: PresenceBreakdown
    by_llm_provider: dict[str, ProviderStats]
    belief_distribution: BeliefDistribution


class TrackBrandRequest(BaseModel):
    """Track brand request."""

    brand_id: uuid.UUID


class TrackBrandResponse(BaseModel):
    """Track brand response."""

    id: uuid.UUID
    name: str
    is_tracked: bool


@router.get(
    "",
    response_model=BrandListResponse,
)
async def list_brands(
    website: CurrentWebsite,
    db: DBSession,
    is_tracked: bool | None = Query(default=None),
    min_mentions: int = Query(default=0, ge=0),
    search: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    """List all brands discovered for a website."""
    params = PaginationParams(page=page, limit=limit)

    # Build query - get brands from LLM responses for this website
    query = select(Brand)

    if is_tracked is not None:
        query = query.where(Brand.is_tracked == is_tracked)

    if search:
        query = query.where(Brand.name.ilike(f"%{search}%"))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Get paginated results
    query = query.offset(params.offset).limit(params.limit)
    query = query.order_by(Brand.name)
    result = await db.execute(query)
    brands = result.scalars().all()

    # Get stats for each brand
    items = []
    for brand in brands:
        # Count mentions
        mention_count = await db.scalar(
            select(func.count())
            .select_from(LLMBrandState)
            .where(LLMBrandState.brand_id == brand.id)
        ) or 0

        if mention_count < min_mentions:
            continue

        # Count recommendations
        rec_count = await db.scalar(
            select(func.count())
            .select_from(LLMBrandState)
            .where(
                LLMBrandState.brand_id == brand.id,
                LLMBrandState.presence == "recommended",
            )
        ) or 0

        # Count comparisons
        comp_count = await db.scalar(
            select(func.count())
            .select_from(LLMBrandState)
            .where(
                LLMBrandState.brand_id == brand.id,
                LLMBrandState.presence == "compared",
            )
        ) or 0

        # Average position
        avg_pos = await db.scalar(
            select(func.avg(LLMBrandState.position_rank))
            .where(
                LLMBrandState.brand_id == brand.id,
                LLMBrandState.position_rank.isnot(None),
            )
        )

        items.append(
            BrandListItem(
                id=brand.id,
                name=brand.name,
                domain=brand.domain,
                is_tracked=brand.is_tracked,
                stats=BrandStats(
                    total_mentions=mention_count,
                    recommendations=rec_count,
                    comparisons=comp_count,
                    avg_position=float(avg_pos) if avg_pos else None,
                ),
            )
        )

    return BrandListResponse(
        data=items,
        pagination=PaginationMeta.from_params(params, total),
    )


@router.post(
    "/track",
    response_model=TrackBrandResponse,
)
async def track_brand(
    request: TrackBrandRequest,
    website: CurrentWebsite,
    db: DBSession,
):
    """Mark a brand as tracked (your brand)."""
    result = await db.execute(select(Brand).where(Brand.id == request.brand_id))
    brand = result.scalar_one_or_none()

    if brand is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found",
        )

    brand.is_tracked = True

    return TrackBrandResponse(
        id=brand.id,
        name=brand.name,
        is_tracked=brand.is_tracked,
    )


@router.get(
    "/{brand_id}/analysis",
    response_model=BrandAnalysisResponse,
)
async def get_brand_analysis(
    brand_id: uuid.UUID,
    website: CurrentWebsite,
    db: DBSession,
):
    """Get detailed brand analysis."""
    result = await db.execute(select(Brand).where(Brand.id == brand_id))
    brand = result.scalar_one_or_none()

    if brand is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found",
        )

    # Get presence breakdown
    presence_counts = {}
    for presence_type in ["ignored", "mentioned", "trusted", "recommended", "compared"]:
        count = await db.scalar(
            select(func.count())
            .select_from(LLMBrandState)
            .where(
                LLMBrandState.brand_id == brand.id,
                LLMBrandState.presence == presence_type,
            )
        )
        presence_counts[presence_type] = count or 0

    # Get belief distribution
    belief_counts = {}
    for belief_type in ["truth", "superiority", "outcome", "transaction", "identity", "social_proof"]:
        count = await db.scalar(
            select(func.count())
            .select_from(LLMBrandState)
            .where(
                LLMBrandState.brand_id == brand.id,
                LLMBrandState.belief_sold == belief_type,
            )
        )
        belief_counts[belief_type] = count or 0

    # Build brand item
    total_mentions = sum(presence_counts.values())
    brand_item = BrandListItem(
        id=brand.id,
        name=brand.name,
        domain=brand.domain,
        is_tracked=brand.is_tracked,
        stats=BrandStats(
            total_mentions=total_mentions,
            recommendations=presence_counts.get("recommended", 0),
            comparisons=presence_counts.get("compared", 0),
        ),
    )

    return BrandAnalysisResponse(
        brand=brand_item,
        presence_breakdown=PresenceBreakdown(**presence_counts),
        by_llm_provider={},  # TODO: Implement per-provider stats
        belief_distribution=BeliefDistribution(**belief_counts),
    )
