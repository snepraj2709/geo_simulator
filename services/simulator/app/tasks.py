"""
Celery tasks for LLM simulation.
"""

from typing import Any

from celery import shared_task

from shared.queue.celery_app import celery_app
from shared.utils.logging import get_logger

logger = get_logger(__name__)


@celery_app.task(bind=True, name="services.simulator.app.tasks.run_simulation")
def run_simulation(
    self,
    simulation_id: str,
    llm_providers: list[str],
    prompt_filter: dict[str, Any] | None = None,
):
    """
    Run a full LLM simulation.

    Args:
        simulation_id: UUID of the simulation run.
        llm_providers: List of LLM providers to query.
        prompt_filter: Optional filter for prompts.
    """
    logger.info(
        "Starting simulation",
        simulation_id=simulation_id,
        providers=llm_providers,
    )

    try:
        # TODO: Implement simulation logic
        # 1. Fetch prompts based on filter
        # 2. For each prompt, query all providers in parallel
        # 3. Store responses
        # 4. Trigger brand analysis

        logger.info(
            "Simulation completed",
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


@celery_app.task(name="services.simulator.app.tasks.query_llm")
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
    logger.info(
        "Querying LLM",
        simulation_id=simulation_id,
        prompt_id=prompt_id,
        provider=provider,
    )

    # TODO: Implement LLM query
    # 1. Get LLM client
    # 2. Send prompt
    # 3. Store response
    # 4. Extract brands mentioned

    return {
        "status": "completed",
        "prompt_id": prompt_id,
        "provider": provider,
    }
