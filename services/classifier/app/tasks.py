"""
Celery tasks for prompt classification.

Implements async prompt classification using LLM analysis.
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

from services.classifier.classifier import PromptClassifier, ClassificationError

import logging

logger = logging.getLogger(__name__)


# ==================== Job Tracking ====================


class ClassificationJobStatus(str, Enum):
    """Status of a classification job."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ClassificationJobData(BaseModel):
    """Internal data structure for tracking classification jobs."""
    job_id: uuid.UUID
    website_id: uuid.UUID
    status: ClassificationJobStatus
    progress: float = 0.0
    total_prompts: int = 0
    classified_prompts: int = 0
    llm_provider: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None

    model_config = {"use_enum_values": True}


# In-memory job tracking (in production, use Redis)
_job_store: dict[str, ClassificationJobData] = {}


def get_job(job_id: str) -> ClassificationJobData | None:
    """Get job data by ID."""
    return _job_store.get(job_id)


def save_job(job: ClassificationJobData) -> None:
    """Save job data."""
    _job_store[str(job.job_id)] = job


# ==================== Async Classification ====================


async def _run_classification(
    website_id: uuid.UUID,
    job_id: uuid.UUID,
    force_reclassify: bool,
    llm_provider: str | None,
    icp_ids: list[str] | None,
) -> dict[str, Any]:
    """
    Run the actual classification process.

    Args:
        website_id: Website UUID.
        job_id: Job ID for tracking.
        force_reclassify: Whether to reclassify existing classifications.
        llm_provider: LLM provider to use.
        icp_ids: Optional list of ICP IDs to filter.

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
                job.status = ClassificationJobStatus.RUNNING
                job.started_at = datetime.now(timezone.utc)
                job.progress = 5.0
                save_job(job)

            # Create classifier with specified provider
            provider = LLMProvider(llm_provider) if llm_provider else LLMProvider.OPENAI
            llm_client = get_llm_client(provider)
            classifier = PromptClassifier(llm_client=llm_client)

            # Update progress
            if job:
                job.progress = 10.0
                save_job(job)

            # Convert ICP IDs
            icp_uuids = [uuid.UUID(icp_id) for icp_id in icp_ids] if icp_ids else None

            # Classify prompts
            classifications = await classifier.classify_website_prompts(
                website_id=website_id,
                session=session,
                force_reclassify=force_reclassify,
                icp_ids=icp_uuids,
            )

            # Update job status
            if job:
                job.status = ClassificationJobStatus.COMPLETED
                job.completed_at = datetime.now(timezone.utc)
                job.progress = 100.0
                job.classified_prompts = len(classifications)
                save_job(job)

            logger.info(
                "Classification completed: website_id=%s, prompts=%d",
                website_id,
                len(classifications),
            )

            return {
                "status": "completed",
                "website_id": str(website_id),
                "prompts_classified": len(classifications),
            }

    except ClassificationError as e:
        logger.error("Classification failed: %s", e)

        # Update job status
        job = get_job(str(job_id))
        if job:
            job.status = ClassificationJobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.now(timezone.utc)
            save_job(job)

        raise

    except Exception as e:
        logger.error("Unexpected error in classification: %s", e)

        # Update job status
        job = get_job(str(job_id))
        if job:
            job.status = ClassificationJobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.now(timezone.utc)
            save_job(job)

        raise

    finally:
        await pg_client.disconnect()


# ==================== Celery Tasks ====================


@celery_app.task(
    bind=True,
    name="services.classifier.app.tasks.classify_prompts_task",
    max_retries=2,
    default_retry_delay=30,
)
def classify_prompts_task(
    self,
    website_id: str,
    job_id: str,
    force_reclassify: bool = False,
    llm_provider: str | None = None,
    icp_ids: list[str] | None = None,
):
    """
    Classify all prompts for a website.

    Args:
        website_id: UUID of the website.
        job_id: Job ID for tracking.
        force_reclassify: Whether to reclassify existing classifications.
        llm_provider: LLM provider to use (openai, anthropic).
        icp_ids: Optional list of ICP IDs to filter.
    """
    logger.info(
        "Starting classification: website_id=%s, job_id=%s, provider=%s",
        website_id,
        job_id,
        llm_provider,
    )

    try:
        result = asyncio.run(_run_classification(
            website_id=uuid.UUID(website_id),
            job_id=uuid.UUID(job_id),
            force_reclassify=force_reclassify,
            llm_provider=llm_provider,
            icp_ids=icp_ids,
        ))

        logger.info(
            "Classification task completed: website_id=%s, prompts=%d",
            website_id,
            result.get("prompts_classified", 0),
        )

        return result

    except ClassificationError as e:
        logger.error(
            "Classification task failed: website_id=%s, error=%s",
            website_id,
            str(e),
        )
        # Don't retry for classification errors (likely LLM issues)
        raise

    except Exception as e:
        logger.error(
            "Classification task error: website_id=%s, error=%s",
            website_id,
            str(e),
        )
        # Retry for other errors (network, DB, etc.)
        raise self.retry(exc=e, countdown=30, max_retries=2)


@celery_app.task(name="services.classifier.app.tasks.reclassify_all_prompts")
def reclassify_all_prompts_task(
    website_ids: list[str],
    llm_provider: str | None = None,
):
    """
    Reclassify prompts for multiple websites.

    Args:
        website_ids: List of website UUIDs.
        llm_provider: LLM provider to use.
    """
    logger.info("Starting bulk reclassification for %d websites", len(website_ids))

    results = []
    for website_id in website_ids:
        job_id = str(uuid.uuid4())

        # Create job
        job = ClassificationJobData(
            job_id=uuid.UUID(job_id),
            website_id=uuid.UUID(website_id),
            status=ClassificationJobStatus.QUEUED,
            llm_provider=llm_provider,
        )
        save_job(job)

        # Queue individual task
        celery_app.send_task(
            "services.classifier.app.tasks.classify_prompts_task",
            args=[website_id, job_id, True, llm_provider, None],
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
