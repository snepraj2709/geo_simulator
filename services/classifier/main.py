"""
Prompt Classifier Engine FastAPI Application.

Endpoints:
- POST /classify/{website_id} - Classify all prompts for a website
- GET /classifications/{website_id} - Get classifications with filtering
- GET /classify/{job_id}/status - Get classification job status
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import FastAPI, HTTPException, Depends, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config import settings
from shared.db.postgres_client import get_postgres_client
from shared.models.website import Website
from shared.models.conversation import ConversationSequence, Prompt, PromptClassification
from shared.queue.celery_app import celery_app

from services.classifier.schemas import (
    ClassifyPromptsRequest,
    ClassifyJobResponse,
    ClassificationJobStatus,
    ClassificationsListResponse,
    ClassifiedPromptResponse,
    ClassificationSummary,
    ClassificationResult,
    IntentType,
    FunnelStage,
    QueryIntent,
)
from services.classifier.classifier import get_classifications_for_website
from services.classifier.app.tasks import (
    get_job,
    save_job,
    ClassificationJobData,
    ClassificationJobStatus as JobStatus,
)

# Create FastAPI app
app = FastAPI(
    title="Prompt Classifier Engine",
    description="Classify prompts with intent metadata for accurate simulation targeting",
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
    return {"status": "healthy", "service": "classifier"}


# ==================== Classification Endpoints ====================


@app.post(
    "/classify/{website_id}",
    response_model=ClassifyJobResponse,
    status_code=202,
)
async def classify_prompts(
    website_id: uuid.UUID = Path(..., description="Website ID"),
    request: ClassifyPromptsRequest = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Classify all prompts for a website.

    Triggers async classification using LLM analysis.
    Returns a job ID for tracking progress.
    """
    request = request or ClassifyPromptsRequest()

    # Verify website exists
    result = await db.execute(
        select(Website).where(Website.id == website_id)
    )
    website = result.scalar_one_or_none()

    if not website:
        raise HTTPException(status_code=404, detail="Website not found")

    # Count prompts to classify
    prompt_count_query = (
        select(func.count(Prompt.id))
        .join(ConversationSequence)
        .where(ConversationSequence.website_id == website_id)
    )

    if request.icp_ids:
        prompt_count_query = prompt_count_query.where(
            ConversationSequence.icp_id.in_(request.icp_ids)
        )

    if not request.force_reclassify:
        # Only count unclassified prompts
        prompt_count_query = prompt_count_query.outerjoin(
            PromptClassification,
            Prompt.id == PromptClassification.prompt_id,
        ).where(PromptClassification.id.is_(None))

    result = await db.execute(prompt_count_query)
    total_prompts = result.scalar() or 0

    if total_prompts == 0 and not request.force_reclassify:
        # All prompts already classified
        return ClassifyJobResponse(
            job_id=uuid.uuid4(),
            website_id=website_id,
            status="completed",
            total_prompts=0,
            message="All prompts already classified. Use force_reclassify=true to reclassify.",
        )

    # Get actual total if force reclassify
    if request.force_reclassify:
        total_query = (
            select(func.count(Prompt.id))
            .join(ConversationSequence)
            .where(ConversationSequence.website_id == website_id)
        )
        if request.icp_ids:
            total_query = total_query.where(
                ConversationSequence.icp_id.in_(request.icp_ids)
            )
        result = await db.execute(total_query)
        total_prompts = result.scalar() or 0

    # Create job
    job_id = uuid.uuid4()
    job = ClassificationJobData(
        job_id=job_id,
        website_id=website_id,
        status=JobStatus.QUEUED,
        total_prompts=total_prompts,
        llm_provider=request.llm_provider,
    )
    save_job(job)

    # Submit Celery task
    celery_app.send_task(
        "services.classifier.app.tasks.classify_prompts_task",
        args=[
            str(website_id),
            str(job_id),
            request.force_reclassify,
            request.llm_provider,
            [str(icp_id) for icp_id in request.icp_ids] if request.icp_ids else None,
        ],
        queue="classification",
    )

    return ClassifyJobResponse(
        job_id=job_id,
        website_id=website_id,
        status="queued",
        total_prompts=total_prompts,
        message=f"Classification job queued for {total_prompts} prompts",
    )


@app.get(
    "/classify/{job_id}/status",
    response_model=ClassificationJobStatus,
)
async def get_classification_status(
    job_id: uuid.UUID = Path(..., description="Job ID"),
):
    """
    Get the status of a classification job.
    """
    job = get_job(str(job_id))

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return ClassificationJobStatus(
        job_id=job.job_id,
        website_id=job.website_id,
        status=job.status.value,
        progress=job.progress,
        total_prompts=job.total_prompts,
        classified_prompts=job.classified_prompts,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error=job.error,
    )


@app.get(
    "/classifications/{website_id}",
    response_model=ClassificationsListResponse,
)
async def get_website_classifications(
    website_id: uuid.UUID = Path(..., description="Website ID"),
    intent_type: str | None = Query(
        None,
        description="Filter by intent type (informational, evaluation, decision)",
    ),
    funnel_stage: str | None = Query(
        None,
        description="Filter by funnel stage (awareness, consideration, purchase)",
    ),
    min_buying_signal: float | None = Query(
        None,
        ge=0.0,
        le=1.0,
        description="Minimum buying signal",
    ),
    min_trust_need: float | None = Query(
        None,
        ge=0.0,
        le=1.0,
        description="Minimum trust need",
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all prompt classifications for a website.

    Returns classifications with filtering options and summary statistics.
    """
    # Verify website exists
    result = await db.execute(
        select(Website).where(Website.id == website_id)
    )
    website = result.scalar_one_or_none()

    if not website:
        raise HTTPException(status_code=404, detail="Website not found")

    # Get classifications with filters
    classifications, summary = await get_classifications_for_website(
        website_id=website_id,
        session=db,
        intent_type=intent_type,
        funnel_stage=funnel_stage,
        min_buying_signal=min_buying_signal,
        min_trust_need=min_trust_need,
    )

    return ClassificationsListResponse(
        data=classifications,
        summary=summary,
    )


@app.get("/classifications/{website_id}/summary")
async def get_classification_summary(
    website_id: uuid.UUID = Path(..., description="Website ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get classification summary statistics for a website.
    """
    # Verify website exists
    result = await db.execute(
        select(Website).where(Website.id == website_id)
    )
    website = result.scalar_one_or_none()

    if not website:
        raise HTTPException(status_code=404, detail="Website not found")

    # Get all classifications
    classifications, summary = await get_classifications_for_website(
        website_id=website_id,
        session=db,
    )

    # Add additional stats
    total_prompts_query = (
        select(func.count(Prompt.id))
        .join(ConversationSequence)
        .where(ConversationSequence.website_id == website_id)
    )
    result = await db.execute(total_prompts_query)
    total_prompts = result.scalar() or 0

    return {
        "website_id": website_id,
        "total_prompts": total_prompts,
        "classified_prompts": summary.total,
        "classification_rate": round(summary.total / total_prompts, 2) if total_prompts else 0,
        "summary": summary,
    }


@app.get("/classifications/{website_id}/by-icp")
async def get_classifications_by_icp(
    website_id: uuid.UUID = Path(..., description="Website ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get classification breakdown by ICP.
    """
    # Verify website exists
    result = await db.execute(
        select(Website).where(Website.id == website_id)
    )
    website = result.scalar_one_or_none()

    if not website:
        raise HTTPException(status_code=404, detail="Website not found")

    # Get classifications grouped by ICP
    from shared.models.icp import ICP

    icps_result = await db.execute(
        select(ICP)
        .where(ICP.website_id == website_id)
        .where(ICP.is_active == True)
    )
    icps = list(icps_result.scalars().all())

    icp_summaries = []
    for icp in icps:
        classifications, summary = await get_classifications_for_website(
            website_id=website_id,
            session=db,
        )

        # Filter to this ICP
        icp_classifications = [c for c in classifications if c.icp_id == icp.id]

        icp_summaries.append({
            "icp_id": icp.id,
            "icp_name": icp.name,
            "total_prompts": len(icp_classifications),
            "avg_buying_signal": round(
                sum(c.classification.buying_signal for c in icp_classifications) / len(icp_classifications), 3
            ) if icp_classifications else 0,
            "avg_trust_need": round(
                sum(c.classification.trust_need for c in icp_classifications) / len(icp_classifications), 3
            ) if icp_classifications else 0,
            "intent_distribution": _count_by_field(icp_classifications, "intent_type"),
            "funnel_distribution": _count_by_field(icp_classifications, "funnel_stage"),
        })

    return {
        "website_id": website_id,
        "total_icps": len(icps),
        "icps": icp_summaries,
    }


def _count_by_field(classifications: list, field: str) -> dict:
    """Count classifications by a specific field."""
    counts = {}
    for c in classifications:
        value = getattr(c.classification, field, None)
        if value:
            counts[value] = counts.get(value, 0) + 1
    return counts


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
        "services.classifier.main:app",
        host="0.0.0.0",
        port=8004,
        reload=settings.app_debug,
    )
