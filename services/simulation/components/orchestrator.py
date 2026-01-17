"""
Parallel LLM Query Orchestrator.

Manages parallel execution of LLM queries across multiple providers,
handling concurrency limits, rate limiting, and result aggregation.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from shared.config import settings
from shared.utils.logging import get_logger

from services.simulation.components.adapters import BaseLLMAdapter, LLMAdapterFactory
from services.simulation.components.prompt_queue import PromptQueue
from services.simulation.schemas import (
    LLMProviderType,
    LLMQueryRequest,
    LLMQueryResponse,
    NormalizedLLMResponse,
    PromptQueueItem,
    SimulationProgress,
)

logger = get_logger(__name__)


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator."""

    max_concurrent_prompts: int = 5
    max_concurrent_per_provider: int = 10
    query_timeout_seconds: int = 120
    batch_size: int = 10
    progress_callback_interval: int = 5  # Callback every N prompts


@dataclass
class QueryTask:
    """Represents a single query task."""

    prompt_item: PromptQueueItem
    provider: LLMProviderType
    adapter: BaseLLMAdapter
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class QueryResult:
    """Result of a query task."""

    prompt_id: uuid.UUID
    provider: LLMProviderType
    response: LLMQueryResponse
    success: bool
    error: str | None = None


class ParallelLLMOrchestrator:
    """
    Orchestrates parallel LLM queries across multiple providers.

    Features:
    - Parallel execution with configurable concurrency
    - Per-provider rate limiting
    - Progress tracking and callbacks
    - Error handling and retry coordination
    - Graceful shutdown support

    Usage:
        orchestrator = ParallelLLMOrchestrator(
            simulation_id=sim_id,
            providers=[LLMProviderType.OPENAI, LLMProviderType.GOOGLE],
        )
        results = await orchestrator.run(prompt_queue)
    """

    def __init__(
        self,
        simulation_id: uuid.UUID,
        providers: list[LLMProviderType],
        config: OrchestratorConfig | None = None,
        progress_callback: Callable[[SimulationProgress], None] | None = None,
    ):
        """
        Initialize the orchestrator.

        Args:
            simulation_id: UUID of the simulation run.
            providers: List of LLM providers to query.
            config: Orchestrator configuration.
            progress_callback: Optional callback for progress updates.
        """
        self.simulation_id = simulation_id
        self.providers = providers
        self.config = config or OrchestratorConfig()
        self.progress_callback = progress_callback

        # Get adapters for each provider
        self.adapters = {
            provider: LLMAdapterFactory.get_adapter(provider)
            for provider in providers
        }

        # Semaphores for concurrency control
        self._prompt_semaphore = asyncio.Semaphore(self.config.max_concurrent_prompts)
        self._provider_semaphores = {
            provider: asyncio.Semaphore(self.config.max_concurrent_per_provider)
            for provider in providers
        }

        # State tracking
        self._is_running = False
        self._is_cancelled = False
        self._start_time: datetime | None = None
        self._total_prompts = 0
        self._completed_prompts = 0
        self._failed_prompts = 0
        self._results: list[NormalizedLLMResponse] = []

        # Locks
        self._results_lock = asyncio.Lock()
        self._stats_lock = asyncio.Lock()

    @property
    def is_running(self) -> bool:
        """Check if the orchestrator is running."""
        return self._is_running

    async def run(
        self,
        prompt_queue: PromptQueue,
    ) -> list[NormalizedLLMResponse]:
        """
        Run the orchestrator on the given prompt queue.

        Args:
            prompt_queue: Queue of prompts to process.

        Returns:
            List of normalized LLM responses.
        """
        self._is_running = True
        self._is_cancelled = False
        self._start_time = datetime.utcnow()
        self._results = []
        self._completed_prompts = 0
        self._failed_prompts = 0

        # Get initial queue stats
        queue_stats = await prompt_queue.get_stats()
        self._total_prompts = queue_stats["pending"] + queue_stats["processing"]

        logger.info(
            "Starting orchestrator",
            simulation_id=str(self.simulation_id),
            total_prompts=self._total_prompts,
            providers=[p.value for p in self.providers],
        )

        try:
            # Process prompts in batches
            while not prompt_queue.is_empty and not self._is_cancelled:
                batch = await prompt_queue.get_batch(self.config.batch_size)
                if not batch:
                    break

                await self._process_batch(batch, prompt_queue)

                # Report progress
                if (
                    self._completed_prompts % self.config.progress_callback_interval == 0
                    and self.progress_callback
                ):
                    await self._report_progress()

            # Final progress report
            await self._report_progress()

            logger.info(
                "Orchestrator completed",
                simulation_id=str(self.simulation_id),
                completed=self._completed_prompts,
                failed=self._failed_prompts,
                total_responses=len(self._results),
            )

            return self._results

        except Exception as e:
            logger.error(
                "Orchestrator failed",
                simulation_id=str(self.simulation_id),
                error=str(e),
            )
            raise

        finally:
            self._is_running = False

    async def _process_batch(
        self,
        batch: list[PromptQueueItem],
        prompt_queue: PromptQueue,
    ) -> None:
        """
        Process a batch of prompts.

        Args:
            batch: List of prompt items to process.
            prompt_queue: The prompt queue for marking completion.
        """
        # Create tasks for all prompt-provider combinations
        tasks = []
        for prompt_item in batch:
            for provider in self.providers:
                task = asyncio.create_task(
                    self._process_prompt_for_provider(
                        prompt_item,
                        provider,
                        prompt_queue,
                    )
                )
                tasks.append(task)

        # Wait for all tasks to complete
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _process_prompt_for_provider(
        self,
        prompt_item: PromptQueueItem,
        provider: LLMProviderType,
        prompt_queue: PromptQueue,
    ) -> None:
        """
        Process a single prompt for a single provider.

        Args:
            prompt_item: The prompt to process.
            provider: The provider to query.
            prompt_queue: The prompt queue for marking completion.
        """
        adapter = self.adapters[provider]
        provider_semaphore = self._provider_semaphores[provider]

        async with self._prompt_semaphore:
            async with provider_semaphore:
                try:
                    # Execute query with timeout
                    response = await asyncio.wait_for(
                        adapter.query(
                            LLMQueryRequest(
                                prompt_text=prompt_item.prompt_text,
                                provider=provider,
                            )
                        ),
                        timeout=self.config.query_timeout_seconds,
                    )

                    if response.success:
                        # Create normalized response
                        normalized = NormalizedLLMResponse(
                            simulation_run_id=self.simulation_id,
                            prompt_id=prompt_item.prompt_id,
                            provider=provider,
                            model=response.model,
                            response_text=response.response_text,
                            tokens_used=response.tokens_used,
                            latency_ms=response.latency_ms,
                        )

                        async with self._results_lock:
                            self._results.append(normalized)

                        logger.debug(
                            "Prompt processed successfully",
                            prompt_id=str(prompt_item.prompt_id),
                            provider=provider.value,
                        )
                    else:
                        logger.warning(
                            "Prompt query failed",
                            prompt_id=str(prompt_item.prompt_id),
                            provider=provider.value,
                            error=response.error,
                        )

                except asyncio.TimeoutError:
                    logger.error(
                        "Prompt query timed out",
                        prompt_id=str(prompt_item.prompt_id),
                        provider=provider.value,
                        timeout=self.config.query_timeout_seconds,
                    )

                except Exception as e:
                    logger.error(
                        "Prompt processing failed",
                        prompt_id=str(prompt_item.prompt_id),
                        provider=provider.value,
                        error=str(e),
                    )

        # Update completion stats (once per prompt, not per provider)
        # This is called for the first provider only
        if provider == self.providers[0]:
            async with self._stats_lock:
                self._completed_prompts += 1
            await prompt_queue.mark_completed(prompt_item.prompt_id)

    async def _report_progress(self) -> None:
        """Report current progress via callback."""
        if not self.progress_callback:
            return

        elapsed = (
            (datetime.utcnow() - self._start_time).total_seconds()
            if self._start_time
            else 0
        )

        # Estimate remaining time
        estimated_remaining = None
        if self._completed_prompts > 0 and elapsed > 0:
            rate = self._completed_prompts / elapsed
            remaining = self._total_prompts - self._completed_prompts
            estimated_remaining = int(remaining / rate) if rate > 0 else None

        progress = SimulationProgress(
            simulation_id=self.simulation_id,
            status="running",
            total_prompts=self._total_prompts,
            completed_prompts=self._completed_prompts,
            failed_prompts=self._failed_prompts,
            estimated_remaining_seconds=estimated_remaining,
        )

        try:
            self.progress_callback(progress)
        except Exception as e:
            logger.warning(
                "Progress callback failed",
                error=str(e),
            )

    async def cancel(self) -> None:
        """Cancel the orchestrator run."""
        self._is_cancelled = True
        logger.info(
            "Orchestrator cancellation requested",
            simulation_id=str(self.simulation_id),
        )

    def get_metrics(self) -> dict[str, Any]:
        """Get orchestrator metrics."""
        adapter_metrics = {
            provider.value: adapter.get_metrics()
            for provider, adapter in self.adapters.items()
        }

        return {
            "simulation_id": str(self.simulation_id),
            "is_running": self._is_running,
            "total_prompts": self._total_prompts,
            "completed_prompts": self._completed_prompts,
            "failed_prompts": self._failed_prompts,
            "total_responses": len(self._results),
            "providers": [p.value for p in self.providers],
            "adapter_metrics": adapter_metrics,
        }

    def reset_metrics(self) -> None:
        """Reset all metrics."""
        for adapter in self.adapters.values():
            adapter.reset_metrics()


class OrchestratorPool:
    """
    Pool of orchestrators for managing multiple concurrent simulations.

    Provides centralized management of orchestrators with:
    - Concurrent simulation limits
    - Resource allocation
    - Monitoring and metrics
    """

    def __init__(self, max_concurrent_simulations: int = 5):
        """
        Initialize the orchestrator pool.

        Args:
            max_concurrent_simulations: Maximum concurrent simulations.
        """
        self.max_concurrent = max_concurrent_simulations
        self._orchestrators: dict[uuid.UUID, ParallelLLMOrchestrator] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent_simulations)
        self._lock = asyncio.Lock()

    async def create_orchestrator(
        self,
        simulation_id: uuid.UUID,
        providers: list[LLMProviderType],
        config: OrchestratorConfig | None = None,
        progress_callback: Callable[[SimulationProgress], None] | None = None,
    ) -> ParallelLLMOrchestrator:
        """
        Create a new orchestrator in the pool.

        Args:
            simulation_id: Simulation UUID.
            providers: LLM providers to use.
            config: Orchestrator configuration.
            progress_callback: Progress callback function.

        Returns:
            The created orchestrator.
        """
        async with self._lock:
            if simulation_id in self._orchestrators:
                raise ValueError(f"Orchestrator already exists: {simulation_id}")

            orchestrator = ParallelLLMOrchestrator(
                simulation_id=simulation_id,
                providers=providers,
                config=config,
                progress_callback=progress_callback,
            )

            self._orchestrators[simulation_id] = orchestrator
            return orchestrator

    async def run_orchestrator(
        self,
        simulation_id: uuid.UUID,
        prompt_queue: PromptQueue,
    ) -> list[NormalizedLLMResponse]:
        """
        Run an orchestrator with pool-level concurrency control.

        Args:
            simulation_id: Simulation UUID.
            prompt_queue: Queue of prompts to process.

        Returns:
            List of normalized responses.
        """
        orchestrator = self._orchestrators.get(simulation_id)
        if orchestrator is None:
            raise ValueError(f"Orchestrator not found: {simulation_id}")

        async with self._semaphore:
            try:
                return await orchestrator.run(prompt_queue)
            finally:
                async with self._lock:
                    self._orchestrators.pop(simulation_id, None)

    async def cancel_orchestrator(self, simulation_id: uuid.UUID) -> None:
        """Cancel a running orchestrator."""
        orchestrator = self._orchestrators.get(simulation_id)
        if orchestrator:
            await orchestrator.cancel()

    def get_active_simulations(self) -> list[uuid.UUID]:
        """Get list of active simulation IDs."""
        return list(self._orchestrators.keys())

    def get_pool_stats(self) -> dict[str, Any]:
        """Get pool statistics."""
        return {
            "max_concurrent": self.max_concurrent,
            "active_simulations": len(self._orchestrators),
            "available_slots": self.max_concurrent - len(self._orchestrators),
        }
