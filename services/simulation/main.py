"""
LLM Simulation Service - FastAPI Application.

Provides REST API endpoints for running LLM simulations,
querying responses, and managing brand extraction.
"""

import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from shared.config import settings
from shared.db.redis_client import get_redis_client
from shared.utils.logging import get_logger

from services.simulation.components.adapters import LLMAdapterFactory
from services.simulation.components.rate_limiter import (
    SimulationRateLimiter,
    get_simulation_rate_limiter,
)
from services.simulation.schemas import (
    BrandExtractionResult,
    LLMProviderType,
    NormalizedLLMResponse,
    PromptFilter,
    RateLimitInfo,
    SimulationMetrics,
    SimulationProgress,
    SimulationResult,
)

logger = get_logger(__name__)


# ==================== Request/Response Models ====================


class SimulationCreateRequest(BaseModel):
    """Request to create a new simulation."""

    website_id: uuid.UUID
    llm_providers: list[LLMProviderType] = Field(
        default=[
            LLMProviderType.OPENAI,
            LLMProviderType.GOOGLE,
            LLMProviderType.ANTHROPIC,
            LLMProviderType.PERPLEXITY,
        ]
    )
    prompt_filter: PromptFilter | None = None


class SimulationCreateResponse(BaseModel):
    """Response after creating a simulation."""

    id: uuid.UUID
    status: str
    total_prompts: int
    llm_providers: list[str]
    estimated_completion: datetime | None = None
    created_at: datetime


class SimulationStatusResponse(BaseModel):
    """Response with simulation status."""

    id: uuid.UUID
    status: str
    total_prompts: int
    completed_prompts: int
    failed_prompts: int
    progress_percent: float
    started_at: datetime | None
    estimated_remaining_seconds: int | None


class LLMResponseListResponse(BaseModel):
    """Paginated list of LLM responses."""

    data: list[NormalizedLLMResponse]
    total: int
    page: int
    limit: int
    has_next: bool


class BrandExtractionListResponse(BaseModel):
    """List of brand extractions."""

    data: list[BrandExtractionResult]
    total: int


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    providers: dict[str, bool]


class ProviderHealthResponse(BaseModel):
    """Provider health check response."""

    provider: str
    available: bool
    model: str | None = None
    latency_ms: int | None = None


class RateLimitResponse(BaseModel):
    """Rate limit information response."""

    limits: list[RateLimitInfo]


class QueryRequest(BaseModel):
    """Single LLM query request."""

    prompt: str
    provider: LLMProviderType
    model: str | None = None
    temperature: float = 0.7
    max_tokens: int = 2048


class QueryResponse(BaseModel):
    """Single LLM query response."""

    provider: str
    model: str
    response_text: str
    tokens_used: int
    latency_ms: int
    brands_mentioned: list[str] = Field(default_factory=list)


# ==================== Application Lifecycle ====================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting LLM Simulation Service")

    # Initialize Redis connection
    redis = get_redis_client()
    try:
        await redis.connect()
        logger.info("Redis connected")
    except Exception as e:
        logger.warning("Redis connection failed, rate limiting will use local state", error=str(e))

    yield

    # Cleanup
    if redis.is_connected:
        await redis.disconnect()

    logger.info("LLM Simulation Service stopped")


# ==================== Application ====================


app = FastAPI(
    title="LLM Simulation Service",
    description="Service for running parallel LLM queries and brand extraction",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else ["https://llmbrandmonitor.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== Health Endpoints ====================


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check service health and provider availability."""
    provider_health = await LLMAdapterFactory.health_check_all()

    return HealthResponse(
        status="healthy",
        version="0.1.0",
        providers=provider_health,
    )


@app.get("/health/providers", response_model=list[ProviderHealthResponse])
async def check_providers():
    """Check health of each LLM provider."""
    responses = []

    for provider in LLMProviderType:
        try:
            adapter = LLMAdapterFactory.get_adapter(provider)
            available = await adapter.health_check()
            responses.append(
                ProviderHealthResponse(
                    provider=provider.value,
                    available=available,
                    model=adapter.model if available else None,
                )
            )
        except Exception as e:
            responses.append(
                ProviderHealthResponse(
                    provider=provider.value,
                    available=False,
                )
            )

    return responses


# ==================== Simulation Endpoints ====================


@app.post(
    "/simulations",
    response_model=SimulationCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_simulation(request: SimulationCreateRequest):
    """
    Start a new LLM simulation run.

    This queues a simulation job that will:
    1. Fetch prompts based on the filter
    2. Query all specified LLM providers
    3. Extract brands from responses
    4. Store results for analysis
    """
    # Check rate limit (mock user/org for standalone service)
    rate_limiter = get_simulation_rate_limiter()
    user_id = uuid.uuid4()  # Would come from auth in real implementation
    org_id = uuid.uuid4()  # Would come from auth in real implementation

    limit_result = await rate_limiter.check_simulation_limit(user_id, org_id)
    if not limit_result.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limit_exceeded",
                "message": f"Simulation limit reached. Try again after {limit_result.retry_after} seconds.",
                "retry_after": limit_result.retry_after,
            },
        )

    # Create simulation (in real implementation, this would trigger a Celery task)
    simulation_id = uuid.uuid4()

    return SimulationCreateResponse(
        id=simulation_id,
        status="queued",
        total_prompts=50,  # Would be calculated based on filter
        llm_providers=[p.value for p in request.llm_providers],
        created_at=datetime.utcnow(),
    )


@app.get("/simulations/{simulation_id}", response_model=SimulationStatusResponse)
async def get_simulation_status(simulation_id: uuid.UUID):
    """Get the status of a simulation run."""
    # In real implementation, this would query the database
    # For now, return mock data
    return SimulationStatusResponse(
        id=simulation_id,
        status="running",
        total_prompts=50,
        completed_prompts=25,
        failed_prompts=0,
        progress_percent=50.0,
        started_at=datetime.utcnow(),
        estimated_remaining_seconds=120,
    )


@app.get("/simulations/{simulation_id}/responses", response_model=LLMResponseListResponse)
async def get_simulation_responses(
    simulation_id: uuid.UUID,
    provider: LLMProviderType | None = None,
    prompt_id: uuid.UUID | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    """Get LLM responses for a simulation run."""
    # In real implementation, this would query the database
    return LLMResponseListResponse(
        data=[],
        total=0,
        page=page,
        limit=limit,
        has_next=False,
    )


@app.get("/simulations/{simulation_id}/metrics", response_model=SimulationMetrics)
async def get_simulation_metrics(simulation_id: uuid.UUID):
    """Get comprehensive metrics for a simulation run."""
    # In real implementation, this would aggregate from stored data
    return SimulationMetrics(
        simulation_id=simulation_id,
        provider_metrics=[],
        brand_metrics=[],
        intent_distribution={},
        total_unique_brands=0,
    )


@app.get("/simulations/{simulation_id}/brands", response_model=BrandExtractionListResponse)
async def get_simulation_brands(simulation_id: uuid.UUID):
    """Get brand extractions for a simulation run."""
    return BrandExtractionListResponse(
        data=[],
        total=0,
    )


# ==================== Query Endpoints ====================


@app.post("/query", response_model=QueryResponse)
async def query_llm(request: QueryRequest):
    """
    Query a single LLM provider directly.

    Useful for testing prompts before running full simulations.
    """
    from services.simulation.components.brand_extractor import BrandExtractor
    from services.simulation.schemas import LLMQueryRequest

    try:
        adapter = LLMAdapterFactory.get_adapter(request.provider, request.model)
        response = await adapter.query(
            LLMQueryRequest(
                prompt_text=request.prompt,
                provider=request.provider,
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
        )

        # Extract brands
        extractor = BrandExtractor()
        normalized = NormalizedLLMResponse(
            simulation_run_id=uuid.uuid4(),
            prompt_id=uuid.uuid4(),
            provider=request.provider,
            model=response.model,
            response_text=response.response_text,
            tokens_used=response.tokens_used,
            latency_ms=response.latency_ms,
        )
        extraction = await extractor.extract(normalized)

        return QueryResponse(
            provider=response.provider.value,
            model=response.model,
            response_text=response.response_text,
            tokens_used=response.tokens_used,
            latency_ms=response.latency_ms,
            brands_mentioned=[b.normalized_name for b in extraction.brands],
        )

    except Exception as e:
        logger.error("Query failed", provider=request.provider.value, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "query_failed", "message": str(e)},
        )


@app.post("/query/parallel", response_model=list[QueryResponse])
async def query_llm_parallel(
    prompt: str,
    providers: list[LLMProviderType] | None = None,
):
    """
    Query multiple LLM providers in parallel.

    Returns responses from all specified providers.
    """
    import asyncio
    from services.simulation.schemas import LLMQueryRequest

    if providers is None:
        providers = list(LLMProviderType)

    async def query_provider(provider: LLMProviderType) -> QueryResponse | None:
        try:
            adapter = LLMAdapterFactory.get_adapter(provider)
            response = await adapter.query(
                LLMQueryRequest(
                    prompt_text=prompt,
                    provider=provider,
                )
            )
            return QueryResponse(
                provider=response.provider.value,
                model=response.model,
                response_text=response.response_text,
                tokens_used=response.tokens_used,
                latency_ms=response.latency_ms,
            )
        except Exception as e:
            logger.warning("Parallel query failed", provider=provider.value, error=str(e))
            return None

    results = await asyncio.gather(*[query_provider(p) for p in providers])
    return [r for r in results if r is not None]


# ==================== Rate Limit Endpoints ====================


@app.get("/rate-limits", response_model=RateLimitResponse)
async def get_rate_limits():
    """Get current rate limit status."""
    rate_limiter = get_simulation_rate_limiter()
    # Mock org ID for standalone service
    org_id = uuid.uuid4()

    limits = await rate_limiter.get_rate_limit_info(org_id)
    return RateLimitResponse(limits=limits)


# ==================== Run Application ====================


def run():
    """Run the application with uvicorn."""
    import uvicorn

    uvicorn.run(
        "services.simulation.main:app",
        host=settings.api_host,
        port=8001,  # Different port from main API
        reload=settings.is_development,
        workers=1 if settings.is_development else 4,
    )


if __name__ == "__main__":
    run()
