"""
Simulation endpoints.
"""

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select

from shared.models import SimulationRun, LLMResponse as LLMResponseModel
from shared.models.enums import SimulationStatus
from shared.queue.celery_app import celery_app

from services.api.app.dependencies import CurrentWebsite, DBSession
from services.api.app.schemas.common import PaginationMeta, PaginationParams

router = APIRouter()


class SimulationCreate(BaseModel):
    """Simulation creation request."""

    llm_providers: list[str] = ["openai", "google", "anthropic", "perplexity"]
    prompt_filter: dict[str, Any] | None = None


class SimulationSummary(BaseModel):
    """Simulation summary statistics."""

    brands_discovered: int = 0
    your_brand_mentions: int = 0
    your_brand_recommendations: int = 0
    top_competitors: list[dict[str, Any]] = []


class SimulationListItem(BaseModel):
    """Simulation list item."""

    id: uuid.UUID
    status: str
    total_prompts: int | None
    completed_prompts: int
    llm_providers: list[str]
    started_at: datetime | None
    completed_at: datetime | None

    class Config:
        from_attributes = True


class SimulationListResponse(BaseModel):
    """Simulation list response."""

    data: list[SimulationListItem]
    pagination: PaginationMeta


class SimulationResponse(BaseModel):
    """Simulation detail response."""

    id: uuid.UUID
    status: str
    total_prompts: int | None
    completed_prompts: int
    llm_providers: list[str]
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    summary: SimulationSummary | None = None

    class Config:
        from_attributes = True


class SimulationCreateResponse(BaseModel):
    """Simulation creation response."""

    id: uuid.UUID
    status: str
    total_prompts: int
    llm_providers: list[str]
    estimated_completion: datetime | None = None
    created_at: datetime


@router.post(
    "",
    response_model=SimulationCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_simulation(
    request: SimulationCreate,
    website: CurrentWebsite,
    db: DBSession,
):
    """Start a new LLM simulation run."""
    # Create simulation run
    simulation = SimulationRun(
        website_id=website.id,
        status=SimulationStatus.PENDING.value,
    )
    db.add(simulation)
    await db.flush()

    # Trigger simulation task
    celery_app.send_task(
        "services.simulator.app.tasks.run_simulation",
        args=[str(simulation.id), request.llm_providers, request.prompt_filter],
        task_id=str(simulation.id),
        queue="simulation",
    )

    return SimulationCreateResponse(
        id=simulation.id,
        status=simulation.status,
        total_prompts=50,  # TODO: Calculate based on filter
        llm_providers=request.llm_providers,
        created_at=simulation.created_at,
    )


@router.get(
    "",
    response_model=SimulationListResponse,
)
async def list_simulations(
    website: CurrentWebsite,
    db: DBSession,
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    """List simulation runs."""
    params = PaginationParams(page=page, limit=limit)

    # Build query
    query = select(SimulationRun).where(SimulationRun.website_id == website.id)

    if status:
        query = query.where(SimulationRun.status == status)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Get paginated results
    query = query.offset(params.offset).limit(params.limit)
    query = query.order_by(SimulationRun.created_at.desc())
    result = await db.execute(query)
    simulations = result.scalars().all()

    items = [
        SimulationListItem(
            id=sim.id,
            status=sim.status,
            total_prompts=sim.total_prompts,
            completed_prompts=sim.completed_prompts,
            llm_providers=["openai", "google", "anthropic", "perplexity"],  # TODO: Store
            started_at=sim.started_at,
            completed_at=sim.completed_at,
        )
        for sim in simulations
    ]

    return SimulationListResponse(
        data=items,
        pagination=PaginationMeta.from_params(params, total),
    )


@router.get(
    "/{simulation_id}",
    response_model=SimulationResponse,
)
async def get_simulation(
    simulation_id: uuid.UUID,
    website: CurrentWebsite,
    db: DBSession,
):
    """Get simulation details and results."""
    result = await db.execute(
        select(SimulationRun).where(
            SimulationRun.id == simulation_id,
            SimulationRun.website_id == website.id,
        )
    )
    simulation = result.scalar_one_or_none()

    if simulation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Simulation not found",
        )

    # Build summary if completed
    summary = None
    if simulation.status == SimulationStatus.COMPLETED.value:
        # TODO: Calculate actual summary from responses
        summary = SimulationSummary(
            brands_discovered=0,
            your_brand_mentions=0,
            your_brand_recommendations=0,
            top_competitors=[],
        )

    return SimulationResponse(
        id=simulation.id,
        status=simulation.status,
        total_prompts=simulation.total_prompts,
        completed_prompts=simulation.completed_prompts,
        llm_providers=["openai", "google", "anthropic", "perplexity"],
        started_at=simulation.started_at,
        completed_at=simulation.completed_at,
        created_at=simulation.created_at,
        summary=summary,
    )
