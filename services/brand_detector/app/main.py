"""
Brand Presence Detector FastAPI Application.

Provides REST API endpoints for brand presence detection,
classification, and analysis.
"""

from contextlib import asynccontextmanager
from typing import Annotated
import uuid

from fastapi import FastAPI, HTTPException, Depends, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import settings
from shared.db.postgres import get_db
from shared.db.postgres_client import get_async_session
from shared.models import Brand, LLMBrandState, LLMResponse
from shared.utils.logging import setup_logging, get_logger

from services.brand_detector.schemas import (
    BrandDetectionRequest,
    BrandDetectionResponse,
    BatchDetectionRequest,
    BatchDetectionResponse,
    LLMResponseAnalysisRequest,
    LLMBrandStateCreate,
    LLMBrandStateResponse,
    BrandPresenceResult,
    BrandPresenceState,
    BeliefType,
    HealthResponse,
    DetectionStatsResponse,
    PresenceBreakdown,
    BeliefDistribution,
    BrandAnalysisSummary,
)
from services.brand_detector.components import BrandPresenceClassifier

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    setup_logging()
    logger.info("Brand Presence Detector starting up")
    yield
    logger.info("Brand Presence Detector shutting down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Brand Presence Detector",
        description="Analyzes LLM responses to determine brand positioning state",
        version="1.0.0",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    return app


app = create_app()

# Initialize classifier (singleton)
classifier = BrandPresenceClassifier()


# Dependency for database session
async def get_db_session() -> AsyncSession:
    """Get database session."""
    async with get_async_session() as session:
        yield session


DBSession = Annotated[AsyncSession, Depends(get_db_session)]


# ==================== Health Endpoints ====================


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
)
async def health_check():
    """Health check endpoint."""
    return HealthResponse()


@app.get(
    "/ready",
    response_model=HealthResponse,
    tags=["Health"],
)
async def readiness_check():
    """Readiness check endpoint."""
    return HealthResponse(status="ready")


# ==================== Detection Endpoints ====================


@app.post(
    "/detect",
    response_model=BrandDetectionResponse,
    tags=["Detection"],
    summary="Detect brand presence in text",
    description="""
    Analyzes text to detect brands and classify their presence state.

    Presence states:
    - **ignored**: Brand not mentioned at all
    - **mentioned**: Brand name appears but without context
    - **trusted**: Brand cited as authority without sales push
    - **recommended**: Brand with clear call-to-action
    - **compared**: Brand in neutral evaluation context

    Rule: One dominant state per brand per answer.
    """,
)
async def detect_brands(request: BrandDetectionRequest):
    """Detect brand presence in text."""
    result = classifier.detect_brands(
        text=request.response_text,
        known_brands=request.known_brands,
        tracked_brand=request.tracked_brand,
    )

    return result


@app.post(
    "/detect/batch",
    response_model=BatchDetectionResponse,
    tags=["Detection"],
    summary="Batch detect brand presence",
)
async def batch_detect_brands(request: BatchDetectionRequest):
    """Detect brand presence in multiple texts."""
    results = []
    total_brands = 0

    for item in request.responses:
        result = classifier.detect_brands(
            text=item.response_text,
            known_brands=request.known_brands or item.known_brands,
            tracked_brand=request.tracked_brand or item.tracked_brand,
        )
        results.append(result)
        total_brands += result.total_brands_found

    # Build summary
    presence_counts = {state: 0 for state in BrandPresenceState}
    for result in results:
        for brand in result.brands:
            presence_counts[brand.presence] += 1

    return BatchDetectionResponse(
        results=results,
        total_responses_analyzed=len(results),
        total_brands_found=total_brands,
        summary={
            "presence_distribution": {k.value: v for k, v in presence_counts.items()},
        },
    )


@app.post(
    "/analyze",
    response_model=BrandDetectionResponse,
    tags=["Analysis"],
    summary="Analyze LLM response and store results",
    description="Analyzes an LLM response for brand presence and stores the results.",
)
async def analyze_llm_response(
    request: LLMResponseAnalysisRequest,
    db: DBSession,
):
    """Analyze LLM response and store brand presence data."""
    # Detect brands
    detection = classifier.detect_brands(
        text=request.response_text,
        known_brands=request.known_brands,
        tracked_brand=request.tracked_brand,
    )

    # Store results
    for brand_result in detection.brands:
        # Get or create brand record
        brand_query = await db.execute(
            select(Brand).where(Brand.normalized_name == brand_result.normalized_name)
        )
        brand_record = brand_query.scalar_one_or_none()

        if not brand_record:
            brand_record = Brand(
                name=brand_result.brand_name,
                normalized_name=brand_result.normalized_name,
                is_tracked=(
                    request.tracked_brand and
                    brand_result.normalized_name == request.tracked_brand.lower()
                ),
            )
            db.add(brand_record)
            await db.flush()

        # Create brand state record
        state_record = LLMBrandState(
            llm_response_id=request.llm_response_id,
            brand_id=brand_record.id,
            presence=brand_result.presence.value,
            position_rank=brand_result.position_rank,
            belief_sold=brand_result.belief_sold.value if brand_result.belief_sold else None,
        )
        db.add(state_record)

    await db.commit()

    return detection


# ==================== Brand State Endpoints ====================


@app.get(
    "/brands/{brand_id}/presence",
    response_model=BrandAnalysisSummary,
    tags=["Brands"],
    summary="Get brand presence analysis",
)
async def get_brand_presence_analysis(
    brand_id: uuid.UUID,
    db: DBSession,
):
    """Get presence analysis for a specific brand."""
    # Get brand
    brand = await db.scalar(select(Brand).where(Brand.id == brand_id))
    if not brand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand not found",
        )

    # Get presence breakdown
    presence_counts = {}
    for presence_type in BrandPresenceState:
        count = await db.scalar(
            select(func.count())
            .select_from(LLMBrandState)
            .where(
                LLMBrandState.brand_id == brand_id,
                LLMBrandState.presence == presence_type.value,
            )
        )
        presence_counts[presence_type.value] = count or 0

    # Get belief distribution
    belief_counts = {}
    for belief_type in BeliefType:
        count = await db.scalar(
            select(func.count())
            .select_from(LLMBrandState)
            .where(
                LLMBrandState.brand_id == brand_id,
                LLMBrandState.belief_sold == belief_type.value,
            )
        )
        belief_counts[belief_type.value] = count or 0

    # Get average position
    avg_position = await db.scalar(
        select(func.avg(LLMBrandState.position_rank))
        .where(
            LLMBrandState.brand_id == brand_id,
            LLMBrandState.position_rank.isnot(None),
        )
    )

    # Calculate total and recommendation rate
    total = sum(presence_counts.values())
    rec_rate = presence_counts.get("recommended", 0) / total if total > 0 else 0

    return BrandAnalysisSummary(
        brand_id=brand_id,
        brand_name=brand.name,
        total_appearances=total,
        presence_breakdown=PresenceBreakdown(**presence_counts),
        belief_distribution=BeliefDistribution(**belief_counts),
        avg_position=float(avg_position) if avg_position else None,
        recommendation_rate=rec_rate,
    )


@app.get(
    "/responses/{response_id}/brands",
    response_model=list[LLMBrandStateResponse],
    tags=["Responses"],
    summary="Get brand states for a response",
)
async def get_response_brand_states(
    response_id: uuid.UUID,
    db: DBSession,
):
    """Get all brand states for an LLM response."""
    result = await db.execute(
        select(LLMBrandState)
        .where(LLMBrandState.llm_response_id == response_id)
        .order_by(LLMBrandState.position_rank)
    )
    states = result.scalars().all()

    return [LLMBrandStateResponse.model_validate(s) for s in states]


@app.post(
    "/responses/{response_id}/brands",
    response_model=list[LLMBrandStateResponse],
    status_code=status.HTTP_201_CREATED,
    tags=["Responses"],
    summary="Create brand states for a response",
)
async def create_response_brand_states(
    response_id: uuid.UUID,
    states: list[LLMBrandStateCreate],
    db: DBSession,
):
    """Create brand state records for an LLM response."""
    created = []

    for state_data in states:
        state = LLMBrandState(
            llm_response_id=response_id,
            brand_id=state_data.brand_id,
            presence=state_data.presence.value,
            position_rank=state_data.position_rank,
            belief_sold=state_data.belief_sold.value if state_data.belief_sold else None,
        )
        db.add(state)
        await db.flush()
        created.append(state)

    await db.commit()

    return [LLMBrandStateResponse.model_validate(s) for s in created]


# ==================== Statistics Endpoints ====================


@app.get(
    "/stats",
    response_model=DetectionStatsResponse,
    tags=["Statistics"],
    summary="Get detection statistics",
)
async def get_detection_stats(
    db: DBSession,
):
    """Get overall detection statistics."""
    # Count total states
    total = await db.scalar(
        select(func.count()).select_from(LLMBrandState)
    ) or 0

    # Count unique brands
    brands_count = await db.scalar(
        select(func.count(func.distinct(LLMBrandState.brand_id)))
    ) or 0

    # Get presence distribution
    presence_counts = {}
    for presence_type in BrandPresenceState:
        count = await db.scalar(
            select(func.count())
            .select_from(LLMBrandState)
            .where(LLMBrandState.presence == presence_type.value)
        )
        presence_counts[presence_type.value] = count or 0

    # Get belief distribution
    belief_counts = {}
    for belief_type in BeliefType:
        count = await db.scalar(
            select(func.count())
            .select_from(LLMBrandState)
            .where(LLMBrandState.belief_sold == belief_type.value)
        )
        belief_counts[belief_type.value] = count or 0

    # Calculate average brands per response
    response_count = await db.scalar(
        select(func.count(func.distinct(LLMBrandState.llm_response_id)))
    ) or 1
    avg_per_response = total / response_count if response_count > 0 else 0

    return DetectionStatsResponse(
        total_detections=total,
        brands_detected=brands_count,
        presence_distribution=PresenceBreakdown(**presence_counts),
        belief_distribution=BeliefDistribution(**belief_counts),
        avg_brands_per_response=avg_per_response,
    )


# ==================== Run Function ====================


def run():
    """Run the application with uvicorn."""
    import uvicorn

    uvicorn.run(
        "services.brand_detector.app.main:app",
        host="0.0.0.0",
        port=8003,
        reload=settings.is_development,
    )


if __name__ == "__main__":
    run()
