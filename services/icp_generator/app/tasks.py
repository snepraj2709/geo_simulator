"""
Celery tasks for ICP generation.

Implements async ICP generation using LLM analysis.
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

from services.icp_generator.generator import ICPGenerator, ICPGenerationError

import logging

logger = logging.getLogger(__name__)


# ==================== Job Tracking ====================


class ICPJobStatus(str, Enum):
    """Status of an ICP generation job."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ICPJobData(BaseModel):
    """Internal data structure for tracking ICP generation jobs."""
    job_id: uuid.UUID
    website_id: uuid.UUID
    status: ICPJobStatus
    progress: float = 0.0
    llm_provider: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    icps_generated: int = 0

    model_config = {"use_enum_values": True}


# In-memory job tracking (in production, use Redis)
_job_store: dict[str, ICPJobData] = {}


def get_job(job_id: str) -> ICPJobData | None:
    """Get job data by ID."""
    return _job_store.get(job_id)


def save_job(job: ICPJobData) -> None:
    """Save job data."""
    _job_store[str(job.job_id)] = job


# ==================== Async ICP Generation ====================


async def _run_icp_generation(
    website_id: uuid.UUID,
    job_id: uuid.UUID,
    force_regenerate: bool,
    llm_provider: str | None,
) -> dict[str, Any]:
    """
    Run the actual ICP generation process.

    Args:
        website_id: Website UUID.
        job_id: Job ID for tracking.
        force_regenerate: Whether to regenerate existing ICPs.
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
                job.status = ICPJobStatus.RUNNING
                job.started_at = datetime.now(timezone.utc)
                job.progress = 10.0
                save_job(job)

            # Create generator with specified provider
            provider = LLMProvider(llm_provider) if llm_provider else LLMProvider.OPENAI
            llm_client = get_llm_client(provider)
            generator = ICPGenerator(llm_client=llm_client)

            # Update progress
            if job:
                job.progress = 30.0
                save_job(job)

            # Generate ICPs
            icps = await generator.generate_icps(
                website_id=website_id,
                session=session,
                force_regenerate=force_regenerate,
            )

            # Update job status
            if job:
                job.status = ICPJobStatus.COMPLETED
                job.completed_at = datetime.now(timezone.utc)
                job.progress = 100.0
                job.icps_generated = len(icps)
                save_job(job)

            logger.info(
                "ICP generation completed: website_id=%s, icps=%d",
                website_id,
                len(icps),
            )

            return {
                "status": "completed",
                "website_id": str(website_id),
                "icps_generated": len(icps),
                "icp_names": [icp.name for icp in icps],
            }

    except ICPGenerationError as e:
        logger.error("ICP generation failed: %s", e)

        # Update job status
        job = get_job(str(job_id))
        if job:
            job.status = ICPJobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.now(timezone.utc)
            save_job(job)

        raise

    except Exception as e:
        logger.error("Unexpected error in ICP generation: %s", e)

        # Update job status
        job = get_job(str(job_id))
        if job:
            job.status = ICPJobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.now(timezone.utc)
            save_job(job)

        raise

    finally:
        await pg_client.disconnect()


# ==================== Celery Tasks ====================


@celery_app.task(
    bind=True,
    name="services.icp_generator.app.tasks.generate_icps_task",
    max_retries=2,
    default_retry_delay=30,
)
def generate_icps_task(
    self,
    website_id: str,
    job_id: str,
    force_regenerate: bool = False,
    llm_provider: str | None = None,
):
    """
    Generate ICPs for a website.

    Args:
        website_id: UUID of the website.
        job_id: Job ID for tracking.
        force_regenerate: Whether to regenerate existing ICPs.
        llm_provider: LLM provider to use (openai, anthropic).
    """
    logger.info(
        "Starting ICP generation: website_id=%s, job_id=%s, provider=%s",
        website_id,
        job_id,
        llm_provider,
    )

    try:
        result = asyncio.run(_run_icp_generation(
            website_id=uuid.UUID(website_id),
            job_id=uuid.UUID(job_id),
            force_regenerate=force_regenerate,
            llm_provider=llm_provider,
        ))

        logger.info(
            "ICP generation task completed: website_id=%s, icps=%d",
            website_id,
            result.get("icps_generated", 0),
        )

        return result

    except ICPGenerationError as e:
        logger.error(
            "ICP generation task failed: website_id=%s, error=%s",
            website_id,
            str(e),
        )
        # Don't retry for generation errors (likely prompt/LLM issues)
        raise

    except Exception as e:
        logger.error(
            "ICP generation task error: website_id=%s, error=%s",
            website_id,
            str(e),
        )
        # Retry for other errors (network, DB, etc.)
        raise self.retry(exc=e, countdown=30, max_retries=2)


@celery_app.task(name="services.icp_generator.app.tasks.regenerate_all_icps")
def regenerate_all_icps_task(website_ids: list[str], llm_provider: str | None = None):
    """
    Regenerate ICPs for multiple websites.

    Args:
        website_ids: List of website UUIDs.
        llm_provider: LLM provider to use.
    """
    logger.info("Starting bulk ICP regeneration for %d websites", len(website_ids))

    results = []
    for website_id in website_ids:
        job_id = str(uuid.uuid4())

        # Create job
        job = ICPJobData(
            job_id=uuid.UUID(job_id),
            website_id=uuid.UUID(website_id),
            status=ICPJobStatus.QUEUED,
            llm_provider=llm_provider,
        )
        save_job(job)

        # Queue individual task
        celery_app.send_task(
            "services.icp_generator.app.tasks.generate_icps_task",
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
