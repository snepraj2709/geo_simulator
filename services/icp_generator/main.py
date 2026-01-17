"""
ICP Generator Service FastAPI Application.

Endpoints:
- POST /generate-icps/{website_id} - Generate ICPs for a website
- GET /icps/{website_id} - Get ICPs for a website
"""

import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Depends, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import settings
from shared.db.postgres_client import get_postgres_client
from shared.models.website import Website
from shared.models.icp import ICP
from shared.queue.celery_app import celery_app

from services.icp_generator.schemas import (
    ICPGenerateRequest,
    ICPGenerateResponse,
    ICPResponse,
    ICPListResponse,
    ICPGenerationStatus,
)
from services.icp_generator.generator import get_icps_for_website
from services.icp_generator.app.tasks import get_job, save_job, ICPJobData, ICPJobStatus

# Create FastAPI app
app = FastAPI(
    title="ICP Generator Service",
    description="Generate Ideal Customer Profiles using LLM analysis",
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
    return {"status": "healthy", "service": "icp_generator"}


# ==================== ICP Endpoints ====================


@app.post(
    "/generate-icps/{website_id}",
    response_model=ICPGenerateResponse,
    status_code=202,
)
async def generate_icps(
    website_id: uuid.UUID = Path(..., description="Website ID"),
    request: ICPGenerateRequest = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate Ideal Customer Profiles for a website.

    Triggers async ICP generation using LLM analysis of website content.
    Returns a job ID for tracking progress.
    """
    request = request or ICPGenerateRequest()

    # Verify website exists
    result = await db.execute(
        select(Website).where(Website.id == website_id)
    )
    website = result.scalar_one_or_none()

    if not website:
        raise HTTPException(status_code=404, detail="Website not found")

    # Check for existing ICPs if not forcing regeneration
    if not request.force_regenerate:
        existing = await get_icps_for_website(website_id, db)
        if existing and len(existing) == 5:
            return ICPGenerateResponse(
                job_id=uuid.uuid4(),  # Dummy job ID
                website_id=website_id,
                status="completed",
                message=f"Using existing {len(existing)} ICPs. Set force_regenerate=true to regenerate.",
            )

    # Create job
    job_id = uuid.uuid4()
    job = ICPJobData(
        job_id=job_id,
        website_id=website_id,
        status=ICPJobStatus.QUEUED,
        llm_provider=request.llm_provider,
    )
    save_job(job)

    # Submit Celery task
    celery_app.send_task(
        "services.icp_generator.app.tasks.generate_icps_task",
        args=[str(website_id), str(job_id), request.force_regenerate, request.llm_provider],
        queue="classification",
    )

    return ICPGenerateResponse(
        job_id=job_id,
        website_id=website_id,
        status="queued",
        message=f"ICP generation queued for {website.domain}",
    )


@app.get(
    "/generate-icps/{job_id}/status",
    response_model=ICPGenerationStatus,
)
async def get_generation_status(
    job_id: uuid.UUID = Path(..., description="Job ID"),
):
    """
    Get the status of an ICP generation job.
    """
    job = get_job(str(job_id))

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return ICPGenerationStatus(
        job_id=job.job_id,
        website_id=job.website_id,
        status=job.status.value,
        progress=job.progress,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error=job.error,
    )


@app.get(
    "/icps/{website_id}",
    response_model=ICPListResponse,
)
async def get_website_icps(
    website_id: uuid.UUID = Path(..., description="Website ID"),
    active_only: bool = Query(True, description="Return only active ICPs"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get Ideal Customer Profiles for a website.

    Returns all ICPs (up to 5) for the specified website.
    """
    # Verify website exists
    result = await db.execute(
        select(Website).where(Website.id == website_id)
    )
    website = result.scalar_one_or_none()

    if not website:
        raise HTTPException(status_code=404, detail="Website not found")

    # Get ICPs
    icps = await get_icps_for_website(website_id, db, active_only=active_only)

    return ICPListResponse(
        website_id=website_id,
        icps=[
            ICPResponse(
                id=icp.id,
                website_id=icp.website_id,
                name=icp.name,
                description=icp.description,
                sequence_number=icp.sequence_number,
                demographics=icp.demographics,
                professional_profile=icp.professional_profile,
                pain_points=icp.pain_points,
                goals=icp.goals,
                motivations=icp.motivations,
                objections=icp.objections,
                decision_factors=icp.decision_factors,
                information_sources=icp.information_sources,
                buying_journey_stage=icp.buying_journey_stage,
                is_active=icp.is_active,
                created_at=icp.created_at,
                updated_at=icp.updated_at,
            )
            for icp in icps
        ],
        total=len(icps),
    )


@app.get(
    "/icps/{website_id}/{icp_id}",
    response_model=ICPResponse,
)
async def get_single_icp(
    website_id: uuid.UUID = Path(..., description="Website ID"),
    icp_id: uuid.UUID = Path(..., description="ICP ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single ICP by ID.
    """
    result = await db.execute(
        select(ICP).where(
            ICP.id == icp_id,
            ICP.website_id == website_id,
        )
    )
    icp = result.scalar_one_or_none()

    if not icp:
        raise HTTPException(status_code=404, detail="ICP not found")

    return ICPResponse(
        id=icp.id,
        website_id=icp.website_id,
        name=icp.name,
        description=icp.description,
        sequence_number=icp.sequence_number,
        demographics=icp.demographics,
        professional_profile=icp.professional_profile,
        pain_points=icp.pain_points,
        goals=icp.goals,
        motivations=icp.motivations,
        objections=icp.objections,
        decision_factors=icp.decision_factors,
        information_sources=icp.information_sources,
        buying_journey_stage=icp.buying_journey_stage,
        is_active=icp.is_active,
        created_at=icp.created_at,
        updated_at=icp.updated_at,
    )


@app.patch(
    "/icps/{website_id}/{icp_id}/toggle-active",
)
async def toggle_icp_active(
    website_id: uuid.UUID = Path(..., description="Website ID"),
    icp_id: uuid.UUID = Path(..., description="ICP ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Toggle the active status of an ICP.
    """
    result = await db.execute(
        select(ICP).where(
            ICP.id == icp_id,
            ICP.website_id == website_id,
        )
    )
    icp = result.scalar_one_or_none()

    if not icp:
        raise HTTPException(status_code=404, detail="ICP not found")

    icp.is_active = not icp.is_active
    await db.commit()
    await db.refresh(icp)

    return {"id": icp.id, "is_active": icp.is_active}


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
        "services.icp_generator.main:app",
        host="0.0.0.0",
        port=8002,
        reload=settings.app_debug,
    )
