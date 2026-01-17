"""
Celery tasks for LLM simulation.

Implements background tasks for running simulations, processing prompts,
and analyzing responses.
"""

import uuid
from datetime import datetime
from typing import Any

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from shared.models import SimulationRun, LLMResponse as LLMResponseModel, Prompt
from shared.models.enums import SimulationStatus
from shared.queue.celery_app import celery_app
from shared.db.postgres_client import get_async_session
from shared.utils.logging import get_logger

from services.simulation.components import (
    BrandExtractor,
    ParallelLLMOrchestrator,
    PromptQueue,
    PromptQueueItem,
    ResponseAggregator,
)
from services.simulation.components.orchestrator import OrchestratorConfig
from services.simulation.components.rate_limiter import get_simulation_rate_limiter
from services.simulation.schemas import LLMProviderType, PromptFilter

logger = get_logger(__name__)


@celery_app.task(bind=True, name="services.simulation.app.tasks.run_simulation")
def run_simulation(
    self,
    simulation_id: str,
    llm_providers: list[str],
    prompt_filter: dict[str, Any] | None = None,
):
    """
    Run a full LLM simulation.

    This is the main entry point for simulation tasks. It:
    1. Fetches prompts based on filter
    2. Queries all specified providers in parallel
    3. Extracts brands from responses
    4. Stores results and triggers analysis

    Args:
        simulation_id: UUID of the simulation run.
        llm_providers: List of LLM provider names.
        prompt_filter: Optional filter for prompts.
    """
    import asyncio

    logger.info(
        "Starting simulation task",
        simulation_id=simulation_id,
        providers=llm_providers,
    )

    try:
        # Run the async simulation logic
        asyncio.run(
            _run_simulation_async(
                simulation_id=uuid.UUID(simulation_id),
                llm_providers=[LLMProviderType(p) for p in llm_providers],
                prompt_filter=PromptFilter(**prompt_filter) if prompt_filter else None,
            )
        )

        logger.info(
            "Simulation completed successfully",
            simulation_id=simulation_id,
        )

        # Trigger brand analysis
        celery_app.send_task(
            "services.analyzer.app.tasks.analyze_simulation",
            args=[simulation_id],
            queue="analysis",
        )

        return {"status": "completed", "simulation_id": simulation_id}

    except Exception as e:
        logger.error(
            "Simulation failed",
            simulation_id=simulation_id,
            error=str(e),
        )
        raise self.retry(exc=e, countdown=60, max_retries=3)


async def _run_simulation_async(
    simulation_id: uuid.UUID,
    llm_providers: list[LLMProviderType],
    prompt_filter: PromptFilter | None = None,
):
    """
    Async implementation of the simulation logic.

    Args:
        simulation_id: UUID of the simulation run.
        llm_providers: List of LLM providers to query.
        prompt_filter: Optional filter for prompts.
    """
    async with get_async_session() as db:
        # Update simulation status
        result = await db.execute(
            select(SimulationRun).where(SimulationRun.id == simulation_id)
        )
        simulation = result.scalar_one_or_none()

        if simulation is None:
            raise ValueError(f"Simulation not found: {simulation_id}")

        simulation.status = SimulationStatus.RUNNING.value
        simulation.started_at = datetime.utcnow()
        await db.commit()

        try:
            # Fetch prompts
            prompts = await _fetch_prompts(db, simulation.website_id, prompt_filter)

            if not prompts:
                logger.warning("No prompts found for simulation", simulation_id=str(simulation_id))
                simulation.status = SimulationStatus.COMPLETED.value
                simulation.completed_at = datetime.utcnow()
                simulation.total_prompts = 0
                simulation.completed_prompts = 0
                await db.commit()
                return

            # Update total prompts
            simulation.total_prompts = len(prompts)
            await db.commit()

            # Build prompt queue
            prompt_queue = PromptQueue(simulation_id, use_redis=True)
            for prompt in prompts:
                await prompt_queue.add(
                    PromptQueueItem(
                        prompt_id=prompt.id,
                        prompt_text=prompt.prompt_text,
                        conversation_id=prompt.conversation_id,
                        website_id=simulation.website_id,
                    )
                )

            # Create orchestrator
            orchestrator = ParallelLLMOrchestrator(
                simulation_id=simulation_id,
                providers=llm_providers,
                config=OrchestratorConfig(
                    max_concurrent_prompts=5,
                    max_concurrent_per_provider=10,
                ),
                progress_callback=lambda p: _update_progress(db, simulation_id, p),
            )

            # Run orchestration
            responses = await orchestrator.run(prompt_queue)

            # Aggregate responses
            aggregator = ResponseAggregator(simulation_id)
            aggregator.add_responses(responses)

            # Extract brands
            extractor = BrandExtractor()
            extractions = await extractor.extract_batch(responses)

            # Add extractions to aggregator
            for response, extraction in zip(responses, extractions):
                aggregator.add_brand_extraction(
                    response.prompt_id,
                    response.provider,
                    extraction,
                )

            # Store responses in database
            for response in responses:
                db_response = LLMResponseModel(
                    simulation_run_id=simulation_id,
                    prompt_id=response.prompt_id,
                    llm_provider=response.provider.value,
                    llm_model=response.model,
                    response_text=response.response_text,
                    response_tokens=response.tokens_used,
                    latency_ms=response.latency_ms,
                    brands_mentioned=response.brands_mentioned,
                )
                db.add(db_response)

            # Update simulation status
            simulation.status = SimulationStatus.COMPLETED.value
            simulation.completed_at = datetime.utcnow()
            simulation.completed_prompts = len(prompts)
            await db.commit()

            # Log metrics
            metrics = aggregator.get_statistics()
            logger.info(
                "Simulation metrics",
                simulation_id=str(simulation_id),
                total_responses=metrics["total_responses"],
                unique_brands=metrics["total_unique_brands"],
            )

        except Exception as e:
            simulation.status = SimulationStatus.FAILED.value
            simulation.completed_at = datetime.utcnow()
            await db.commit()
            raise


async def _fetch_prompts(
    db,
    website_id: uuid.UUID,
    prompt_filter: PromptFilter | None,
) -> list[Prompt]:
    """Fetch prompts for simulation based on filter."""
    query = (
        select(Prompt)
        .join(Prompt.conversation)
        .where(Prompt.conversation.has(website_id=website_id))
    )

    if prompt_filter:
        if prompt_filter.icp_ids:
            query = query.where(
                Prompt.conversation.has(
                    icp_id.in_(prompt_filter.icp_ids)
                )
            )

        if prompt_filter.core_only:
            query = query.where(
                Prompt.conversation.has(is_core_conversation=True)
            )

    result = await db.execute(query)
    return list(result.scalars().all())


def _update_progress(db, simulation_id: uuid.UUID, progress):
    """Update simulation progress in database."""
    import asyncio

    async def _update():
        async with get_async_session() as session:
            result = await session.execute(
                select(SimulationRun).where(SimulationRun.id == simulation_id)
            )
            simulation = result.scalar_one_or_none()
            if simulation:
                simulation.completed_prompts = progress.completed_prompts
                await session.commit()

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(_update())
        else:
            asyncio.run(_update())
    except Exception as e:
        logger.warning("Failed to update progress", error=str(e))


@celery_app.task(name="services.simulation.app.tasks.query_llm")
def query_llm(
    simulation_id: str,
    prompt_id: str,
    provider: str,
    prompt_text: str,
):
    """
    Query a single LLM provider.

    Args:
        simulation_id: UUID of the simulation run.
        prompt_id: UUID of the prompt.
        provider: LLM provider name.
        prompt_text: The prompt text to send.
    """
    import asyncio

    logger.info(
        "Querying LLM",
        simulation_id=simulation_id,
        prompt_id=prompt_id,
        provider=provider,
    )

    try:
        result = asyncio.run(
            _query_llm_async(
                simulation_id=uuid.UUID(simulation_id),
                prompt_id=uuid.UUID(prompt_id),
                provider=LLMProviderType(provider),
                prompt_text=prompt_text,
            )
        )

        return {
            "status": "completed",
            "prompt_id": prompt_id,
            "provider": provider,
            "response_length": len(result["response_text"]),
        }

    except Exception as e:
        logger.error(
            "LLM query failed",
            prompt_id=prompt_id,
            provider=provider,
            error=str(e),
        )
        return {
            "status": "failed",
            "prompt_id": prompt_id,
            "provider": provider,
            "error": str(e),
        }


async def _query_llm_async(
    simulation_id: uuid.UUID,
    prompt_id: uuid.UUID,
    provider: LLMProviderType,
    prompt_text: str,
) -> dict[str, Any]:
    """Async implementation of single LLM query."""
    from services.simulation.components.adapters import LLMAdapterFactory
    from services.simulation.schemas import LLMQueryRequest

    adapter = LLMAdapterFactory.get_adapter(provider)
    response = await adapter.query(
        LLMQueryRequest(
            prompt_text=prompt_text,
            provider=provider,
        )
    )

    # Store response
    async with get_async_session() as db:
        db_response = LLMResponseModel(
            simulation_run_id=simulation_id,
            prompt_id=prompt_id,
            llm_provider=provider.value,
            llm_model=response.model,
            response_text=response.response_text,
            response_tokens=response.tokens_used,
            latency_ms=response.latency_ms,
        )
        db.add(db_response)
        await db.commit()

    return {
        "response_text": response.response_text,
        "tokens_used": response.tokens_used,
        "latency_ms": response.latency_ms,
    }


@celery_app.task(name="services.simulation.app.tasks.extract_brands")
def extract_brands(simulation_id: str, response_id: str):
    """
    Extract brands from an LLM response.

    Args:
        simulation_id: UUID of the simulation run.
        response_id: UUID of the LLM response.
    """
    import asyncio

    logger.info(
        "Extracting brands",
        simulation_id=simulation_id,
        response_id=response_id,
    )

    try:
        asyncio.run(
            _extract_brands_async(
                simulation_id=uuid.UUID(simulation_id),
                response_id=uuid.UUID(response_id),
            )
        )

        return {
            "status": "completed",
            "response_id": response_id,
        }

    except Exception as e:
        logger.error(
            "Brand extraction failed",
            response_id=response_id,
            error=str(e),
        )
        return {
            "status": "failed",
            "response_id": response_id,
            "error": str(e),
        }


async def _extract_brands_async(
    simulation_id: uuid.UUID,
    response_id: uuid.UUID,
):
    """Async implementation of brand extraction."""
    from services.simulation.schemas import NormalizedLLMResponse

    async with get_async_session() as db:
        result = await db.execute(
            select(LLMResponseModel).where(LLMResponseModel.id == response_id)
        )
        db_response = result.scalar_one_or_none()

        if db_response is None:
            raise ValueError(f"Response not found: {response_id}")

        # Create normalized response
        normalized = NormalizedLLMResponse(
            id=db_response.id,
            simulation_run_id=simulation_id,
            prompt_id=db_response.prompt_id,
            provider=LLMProviderType(db_response.llm_provider),
            model=db_response.llm_model,
            response_text=db_response.response_text,
            tokens_used=db_response.response_tokens or 0,
            latency_ms=db_response.latency_ms or 0,
        )

        # Extract brands
        extractor = BrandExtractor()
        extraction = await extractor.extract(normalized)

        # Update response with brands
        db_response.brands_mentioned = [b.normalized_name for b in extraction.brands]
        await db.commit()

        logger.info(
            "Brands extracted",
            response_id=str(response_id),
            brands_found=len(extraction.brands),
        )
