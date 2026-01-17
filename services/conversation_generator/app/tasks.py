"""
Celery tasks for conversation generation.

Implements async conversation generation using LLM analysis.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from shared.config import settings
from shared.db.postgres_client import get_postgres_client
from shared.queue.celery_app import celery_app
from shared.llm import LLMProvider, get_llm_client

from services.conversation_generator.generator import (
    ConversationGenerator,
    ConversationGenerationError,
)

import logging

logger = logging.getLogger(__name__)


# ==================== Job Tracking ====================


class ConversationJobStatus(str, Enum):
    """Status of a conversation generation job."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ConversationJobData(BaseModel):
    """Internal data structure for tracking conversation generation jobs."""
    job_id: uuid.UUID
    icp_id: uuid.UUID | None  # None for batch jobs
    website_id: uuid.UUID
    status: ConversationJobStatus
    progress: float = 0.0
    llm_provider: str | None = None
    is_batch: bool = False
    total_icps: int = 0
    completed_icps: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    conversations_generated: int = 0

    model_config = {"use_enum_values": True}


# In-memory job tracking (in production, use Redis)
_job_store: dict[str, ConversationJobData] = {}


def get_job(job_id: str) -> ConversationJobData | None:
    """Get job data by ID."""
    return _job_store.get(job_id)


def save_job(job: ConversationJobData) -> None:
    """Save job data."""
    _job_store[str(job.job_id)] = job


# ==================== Async Conversation Generation ====================


async def _run_conversation_generation(
    icp_id: uuid.UUID,
    job_id: uuid.UUID,
    force_regenerate: bool,
    llm_provider: str | None,
) -> dict[str, Any]:
    """
    Run the actual conversation generation process for a single ICP.

    Args:
        icp_id: ICP UUID.
        job_id: Job ID for tracking.
        force_regenerate: Whether to regenerate existing conversations.
        llm_provider: LLM provider to use.

    Returns:
        Result dictionary.
    """
    # Get database connection
    pg_client = get_postgres_client()
    await pg_client.connect()

    try:
        async with pg_client.session() as session:
            # Update job status
            job = get_job(str(job_id))
            if job:
                job.status = ConversationJobStatus.RUNNING
                job.started_at = datetime.now(timezone.utc)
                job.progress = 10.0
                save_job(job)

            # Create generator with specified provider
            provider = LLMProvider(llm_provider) if llm_provider else LLMProvider.OPENAI
            llm_client = get_llm_client(provider)
            generator = ConversationGenerator(llm_client=llm_client)

            # Update progress
            if job:
                job.progress = 30.0
                save_job(job)

            # Generate conversations
            conversations = await generator.generate_conversations(
                icp_id=icp_id,
                session=session,
                force_regenerate=force_regenerate,
            )

            # Update job status
            if job:
                job.status = ConversationJobStatus.COMPLETED
                job.completed_at = datetime.now(timezone.utc)
                job.progress = 100.0
                job.conversations_generated = len(conversations)
                save_job(job)

            logger.info(
                "Conversation generation completed: icp_id=%s, conversations=%d",
                icp_id,
                len(conversations),
            )

            return {
                "status": "completed",
                "icp_id": str(icp_id),
                "conversations_generated": len(conversations),
                "topics": [conv.topic for conv in conversations],
            }

    except ConversationGenerationError as e:
        logger.error("Conversation generation failed: %s", e)

        # Update job status
        job = get_job(str(job_id))
        if job:
            job.status = ConversationJobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.now(timezone.utc)
            save_job(job)

        raise

    except Exception as e:
        logger.error("Unexpected error in conversation generation: %s", e)

        # Update job status
        job = get_job(str(job_id))
        if job:
            job.status = ConversationJobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.now(timezone.utc)
            save_job(job)

        raise

    finally:
        await pg_client.disconnect()


async def _run_batch_conversation_generation(
    website_id: uuid.UUID,
    job_id: uuid.UUID,
    force_regenerate: bool,
    llm_provider: str | None,
) -> dict[str, Any]:
    """
    Run batch conversation generation for all ICPs of a website.

    Args:
        website_id: Website UUID.
        job_id: Job ID for tracking.
        force_regenerate: Whether to regenerate existing conversations.
        llm_provider: LLM provider to use.

    Returns:
        Result dictionary.
    """
    # Get database connection
    pg_client = get_postgres_client()
    await pg_client.connect()

    try:
        async with pg_client.session() as session:
            # Update job status
            job = get_job(str(job_id))
            if job:
                job.status = ConversationJobStatus.RUNNING
                job.started_at = datetime.now(timezone.utc)
                job.progress = 5.0
                save_job(job)

            # Create generator with specified provider
            provider = LLMProvider(llm_provider) if llm_provider else LLMProvider.OPENAI
            llm_client = get_llm_client(provider)
            generator = ConversationGenerator(llm_client=llm_client)

            # Generate for all ICPs
            results = await generator.generate_batch(
                website_id=website_id,
                session=session,
                force_regenerate=force_regenerate,
            )

            total_conversations = sum(len(convs) for convs in results.values())

            # Update job status
            if job:
                job.status = ConversationJobStatus.COMPLETED
                job.completed_at = datetime.now(timezone.utc)
                job.progress = 100.0
                job.completed_icps = len(results)
                job.conversations_generated = total_conversations
                save_job(job)

            logger.info(
                "Batch conversation generation completed: website_id=%s, icps=%d, conversations=%d",
                website_id,
                len(results),
                total_conversations,
            )

            return {
                "status": "completed",
                "website_id": str(website_id),
                "icps_processed": len(results),
                "total_conversations": total_conversations,
                "icp_results": {
                    str(icp_id): len(convs)
                    for icp_id, convs in results.items()
                },
            }

    except ConversationGenerationError as e:
        logger.error("Batch conversation generation failed: %s", e)

        # Update job status
        job = get_job(str(job_id))
        if job:
            job.status = ConversationJobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.now(timezone.utc)
            save_job(job)

        raise

    except Exception as e:
        logger.error("Unexpected error in batch conversation generation: %s", e)

        # Update job status
        job = get_job(str(job_id))
        if job:
            job.status = ConversationJobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.now(timezone.utc)
            save_job(job)

        raise

    finally:
        await pg_client.disconnect()


# ==================== Celery Tasks ====================


@celery_app.task(
    bind=True,
    name="services.conversation_generator.app.tasks.generate_conversations_task",
    max_retries=2,
    default_retry_delay=30,
)
def generate_conversations_task(
    self,
    icp_id: str,
    job_id: str,
    force_regenerate: bool = False,
    llm_provider: str | None = None,
):
    """
    Generate conversations for an ICP.

    Args:
        icp_id: UUID of the ICP.
        job_id: Job ID for tracking.
        force_regenerate: Whether to regenerate existing conversations.
        llm_provider: LLM provider to use (openai, anthropic).
    """
    logger.info(
        "Starting conversation generation: icp_id=%s, job_id=%s, provider=%s",
        icp_id,
        job_id,
        llm_provider,
    )

    try:
        result = asyncio.run(_run_conversation_generation(
            icp_id=uuid.UUID(icp_id),
            job_id=uuid.UUID(job_id),
            force_regenerate=force_regenerate,
            llm_provider=llm_provider,
        ))

        logger.info(
            "Conversation generation task completed: icp_id=%s, conversations=%d",
            icp_id,
            result.get("conversations_generated", 0),
        )

        return result

    except ConversationGenerationError as e:
        logger.error(
            "Conversation generation task failed: icp_id=%s, error=%s",
            icp_id,
            str(e),
        )
        # Don't retry for generation errors (likely prompt/LLM issues)
        raise

    except Exception as e:
        logger.error(
            "Conversation generation task error: icp_id=%s, error=%s",
            icp_id,
            str(e),
        )
        # Retry for other errors (network, DB, etc.)
        raise self.retry(exc=e, countdown=30, max_retries=2)


@celery_app.task(
    bind=True,
    name="services.conversation_generator.app.tasks.generate_batch_conversations_task",
    max_retries=1,
    default_retry_delay=60,
)
def generate_batch_conversations_task(
    self,
    website_id: str,
    job_id: str,
    force_regenerate: bool = False,
    llm_provider: str | None = None,
):
    """
    Generate conversations for all ICPs of a website.

    Args:
        website_id: UUID of the website.
        job_id: Job ID for tracking.
        force_regenerate: Whether to regenerate existing conversations.
        llm_provider: LLM provider to use.
    """
    logger.info(
        "Starting batch conversation generation: website_id=%s, job_id=%s",
        website_id,
        job_id,
    )

    try:
        result = asyncio.run(_run_batch_conversation_generation(
            website_id=uuid.UUID(website_id),
            job_id=uuid.UUID(job_id),
            force_regenerate=force_regenerate,
            llm_provider=llm_provider,
        ))

        logger.info(
            "Batch conversation generation completed: website_id=%s, conversations=%d",
            website_id,
            result.get("total_conversations", 0),
        )

        return result

    except ConversationGenerationError as e:
        logger.error(
            "Batch conversation generation failed: website_id=%s, error=%s",
            website_id,
            str(e),
        )
        raise

    except Exception as e:
        logger.error(
            "Batch conversation generation error: website_id=%s, error=%s",
            website_id,
            str(e),
        )
        raise self.retry(exc=e, countdown=60, max_retries=1)


@celery_app.task(name="services.conversation_generator.app.tasks.regenerate_all_conversations")
def regenerate_all_conversations_task(
    website_ids: list[str],
    llm_provider: str | None = None,
):
    """
    Regenerate conversations for multiple websites.

    Args:
        website_ids: List of website UUIDs.
        llm_provider: LLM provider to use.
    """
    logger.info("Starting bulk conversation regeneration for %d websites", len(website_ids))

    results = []
    for website_id in website_ids:
        job_id = str(uuid.uuid4())

        # Create job
        job = ConversationJobData(
            job_id=uuid.UUID(job_id),
            icp_id=None,
            website_id=uuid.UUID(website_id),
            status=ConversationJobStatus.QUEUED,
            llm_provider=llm_provider,
            is_batch=True,
        )
        save_job(job)

        # Queue individual task
        celery_app.send_task(
            "services.conversation_generator.app.tasks.generate_batch_conversations_task",
            args=[website_id, job_id, True, llm_provider],
            queue="classification",
        )

        results.append({
            "website_id": website_id,
            "job_id": job_id,
            "status": "queued",
        })

    return {
        "total": len(website_ids),
        "queued": len(results),
        "jobs": results,
    }
