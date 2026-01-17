"""
Conversation Generator Service FastAPI Application.

Endpoints:
- POST /generate-conversations/{icp_id} - Generate conversations for an ICP
- POST /generate-batch/{website_id} - Generate conversations for all ICPs
- GET /conversations/{icp_id} - Get conversations for an ICP
- GET /conversation/{conversation_id} - Get a single conversation with prompts
"""

import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Depends, Path, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.config import settings
from shared.db.postgres_client import get_postgres_client
from shared.models.icp import ICP
from shared.models.conversation import ConversationSequence, Prompt
from shared.queue.celery_app import celery_app

from services.conversation_generator.schemas import (
    ConversationGenerationRequest,
    BatchConversationRequest,
    ConversationJobResponse,
    BatchJobResponse,
    ICPConversationsResponse,
    ConversationSummary,
    ConversationDetailResponse,
    GeneratedPrompt,
)
from services.conversation_generator.generator import (
    get_conversations_for_icp,
    get_conversation_by_id,
)
from services.conversation_generator.app.tasks import (
    get_job,
    save_job,
    ConversationJobData,
    ConversationJobStatus,
)

# Create FastAPI app
app = FastAPI(
    title="Conversation Generator Service",
    description="Generate realistic conversation topics and prompts for ICPs",
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
    return {"status": "healthy", "service": "conversation_generator"}


# ==================== Conversation Generation Endpoints ====================


@app.post(
    "/generate-conversations/{icp_id}",
    response_model=ConversationJobResponse,
    status_code=202,
)
async def generate_conversations(
    icp_id: uuid.UUID = Path(..., description="ICP ID"),
    request: ConversationGenerationRequest = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate conversations for an ICP.

    Triggers async conversation generation using LLM analysis.
    Returns a job ID for tracking progress.
    """
    request = request or ConversationGenerationRequest()

    # Verify ICP exists
    result = await db.execute(
        select(ICP).where(ICP.id == icp_id)
    )
    icp = result.scalar_one_or_none()

    if not icp:
        raise HTTPException(status_code=404, detail="ICP not found")

    # Check for existing conversations if not forcing regeneration
    if not request.force_regenerate:
        existing = await get_conversations_for_icp(icp_id, db, include_prompts=False)
        if existing and len(existing) == 10:
            return ConversationJobResponse(
                job_id=uuid.uuid4(),  # Dummy job ID
                icp_id=icp_id,
                status="completed",
                message=f"Using existing {len(existing)} conversations. Set force_regenerate=true to regenerate.",
            )

    # Create job
    job_id = uuid.uuid4()
    job = ConversationJobData(
        job_id=job_id,
        icp_id=icp_id,
        website_id=icp.website_id,
        status=ConversationJobStatus.QUEUED,
        llm_provider=request.llm_provider,
    )
    save_job(job)

    # Submit Celery task
    celery_app.send_task(
        "services.conversation_generator.app.tasks.generate_conversations_task",
        args=[str(icp_id), str(job_id), request.force_regenerate, request.llm_provider],
        queue="classification",
    )

    return ConversationJobResponse(
        job_id=job_id,
        icp_id=icp_id,
        status="queued",
        message=f"Conversation generation queued for ICP: {icp.name}",
    )


@app.post(
    "/generate-batch/{website_id}",
    response_model=BatchJobResponse,
    status_code=202,
)
async def generate_batch_conversations(
    website_id: uuid.UUID = Path(..., description="Website ID"),
    request: BatchConversationRequest = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Generate conversations for all ICPs of a website.

    Triggers batch async conversation generation.
    Returns a job ID for tracking progress.
    """
    request = request or BatchConversationRequest(website_id=website_id)

    # Get all ICPs for the website
    result = await db.execute(
        select(ICP)
        .where(ICP.website_id == website_id)
        .where(ICP.is_active == True)
    )
    icps = list(result.scalars().all())

    if not icps:
        raise HTTPException(
            status_code=404,
            detail="No active ICPs found for website. Generate ICPs first.",
        )

    # Create batch job
    job_id = uuid.uuid4()
    job = ConversationJobData(
        job_id=job_id,
        icp_id=None,
        website_id=website_id,
        status=ConversationJobStatus.QUEUED,
        llm_provider=request.llm_provider,
        is_batch=True,
        total_icps=len(icps),
    )
    save_job(job)

    # Submit Celery task
    celery_app.send_task(
        "services.conversation_generator.app.tasks.generate_batch_conversations_task",
        args=[str(website_id), str(job_id), request.force_regenerate, request.llm_provider],
        queue="classification",
    )

    return BatchJobResponse(
        job_id=job_id,
        website_id=website_id,
        icp_count=len(icps),
        status="queued",
        message=f"Batch conversation generation queued for {len(icps)} ICPs",
    )


@app.get("/generate-conversations/{job_id}/status")
async def get_generation_status(
    job_id: uuid.UUID = Path(..., description="Job ID"),
):
    """
    Get the status of a conversation generation job.
    """
    job = get_job(str(job_id))

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job.job_id,
        "icp_id": job.icp_id,
        "website_id": job.website_id,
        "status": job.status.value,
        "progress": job.progress,
        "is_batch": job.is_batch,
        "total_icps": job.total_icps,
        "completed_icps": job.completed_icps,
        "conversations_generated": job.conversations_generated,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "error": job.error,
    }


# ==================== Conversation Retrieval Endpoints ====================


@app.get(
    "/conversations/{icp_id}",
    response_model=ICPConversationsResponse,
)
async def get_icp_conversations(
    icp_id: uuid.UUID = Path(..., description="ICP ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all conversations for an ICP.

    Returns summary information for each conversation.
    """
    # Verify ICP exists
    result = await db.execute(
        select(ICP).where(ICP.id == icp_id)
    )
    icp = result.scalar_one_or_none()

    if not icp:
        raise HTTPException(status_code=404, detail="ICP not found")

    # Get conversations
    conversations = await get_conversations_for_icp(icp_id, db, include_prompts=True)

    return ICPConversationsResponse(
        icp_id=icp_id,
        icp_name=icp.name,
        conversation_count=len(conversations),
        conversations=[
            ConversationSummary(
                id=conv.id,
                topic=conv.topic,
                context=conv.context,
                expected_outcome=conv.expected_outcome,
                is_core_conversation=conv.is_core_conversation,
                sequence_number=conv.sequence_number,
                prompt_count=len(conv.prompts) if conv.prompts else 0,
                created_at=conv.created_at.isoformat() if conv.created_at else "",
            )
            for conv in conversations
        ],
    )


@app.get(
    "/conversation/{conversation_id}",
    response_model=ConversationDetailResponse,
)
async def get_single_conversation(
    conversation_id: uuid.UUID = Path(..., description="Conversation ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single conversation with all its prompts.
    """
    # Get conversation with prompts
    conversation = await get_conversation_by_id(conversation_id, db)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Get ICP name
    icp_result = await db.execute(
        select(ICP).where(ICP.id == conversation.icp_id)
    )
    icp = icp_result.scalar_one_or_none()

    return ConversationDetailResponse(
        id=conversation.id,
        topic=conversation.topic,
        context=conversation.context,
        expected_outcome=conversation.expected_outcome,
        is_core_conversation=conversation.is_core_conversation,
        sequence_number=conversation.sequence_number,
        icp_id=conversation.icp_id,
        icp_name=icp.name if icp else "Unknown",
        prompts=[
            GeneratedPrompt(
                prompt_text=p.prompt_text,
                prompt_type=p.prompt_type,
                sequence_order=p.sequence_order,
                expected_response_type=None,
            )
            for p in sorted(conversation.prompts, key=lambda x: x.sequence_order)
        ],
        created_at=conversation.created_at.isoformat() if conversation.created_at else "",
        updated_at=conversation.updated_at.isoformat() if conversation.updated_at else "",
    )


@app.get("/conversations/website/{website_id}")
async def get_website_conversations(
    website_id: uuid.UUID = Path(..., description="Website ID"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all conversations for a website grouped by ICP.
    """
    # Get all ICPs for website
    icps_result = await db.execute(
        select(ICP)
        .where(ICP.website_id == website_id)
        .where(ICP.is_active == True)
        .order_by(ICP.sequence_number)
    )
    icps = list(icps_result.scalars().all())

    if not icps:
        raise HTTPException(status_code=404, detail="No ICPs found for website")

    results = []
    total_conversations = 0

    for icp in icps:
        conversations = await get_conversations_for_icp(icp.id, db, include_prompts=False)
        total_conversations += len(conversations)

        results.append({
            "icp_id": icp.id,
            "icp_name": icp.name,
            "conversation_count": len(conversations),
            "has_all_conversations": len(conversations) == 10,
        })

    return {
        "website_id": website_id,
        "total_icps": len(icps),
        "total_conversations": total_conversations,
        "expected_conversations": len(icps) * 10,
        "is_complete": total_conversations == len(icps) * 10,
        "icps": results,
    }


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
        "services.conversation_generator.main:app",
        host="0.0.0.0",
        port=8003,
        reload=settings.app_debug,
    )
