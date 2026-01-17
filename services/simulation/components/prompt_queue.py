"""
Prompt Queue Component.

Manages the queue of prompts to be processed by the LLM Simulation Layer.
Supports priority-based ordering, retry logic, and Redis-backed persistence.
"""

import asyncio
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from heapq import heappop, heappush
from typing import Any

from shared.config import settings
from shared.db.redis_client import RedisClient, get_redis_client
from shared.utils.logging import get_logger

from services.simulation.schemas import (
    PromptClassificationData,
    PromptQueueItem,
)

logger = get_logger(__name__)


@dataclass(order=True)
class PrioritizedPrompt:
    """Wrapper for priority queue ordering."""

    priority: int
    timestamp: float
    item: PromptQueueItem = field(compare=False)

    @classmethod
    def from_queue_item(cls, item: PromptQueueItem) -> "PrioritizedPrompt":
        """Create a prioritized prompt from a queue item."""
        # Negative priority for max-heap behavior (higher priority first)
        return cls(
            priority=-item.priority,
            timestamp=datetime.utcnow().timestamp(),
            item=item,
        )


class PromptQueue:
    """
    Manages a queue of prompts for LLM simulation.

    Features:
    - Priority-based ordering (higher priority prompts processed first)
    - Retry logic for failed prompts
    - Optional Redis persistence for durability
    - Batch operations for efficiency
    - Async iteration support

    Usage:
        queue = PromptQueue(simulation_id)
        await queue.add(prompt_item)
        async for item in queue:
            # Process item
            await queue.mark_completed(item.prompt_id)
    """

    def __init__(
        self,
        simulation_id: uuid.UUID,
        redis_client: RedisClient | None = None,
        use_redis: bool = True,
    ):
        """
        Initialize the prompt queue.

        Args:
            simulation_id: UUID of the simulation run.
            redis_client: Optional Redis client for persistence.
            use_redis: Whether to use Redis for persistence.
        """
        self.simulation_id = simulation_id
        self._redis = redis_client
        self._use_redis = use_redis

        # In-memory priority queue
        self._queue: list[PrioritizedPrompt] = []
        self._lock = asyncio.Lock()

        # Tracking sets
        self._pending: set[uuid.UUID] = set()
        self._processing: set[uuid.UUID] = set()
        self._completed: set[uuid.UUID] = set()
        self._failed: set[uuid.UUID] = set()

        # Redis keys
        self._redis_key_prefix = f"simulation:{simulation_id}:queue"
        self._pending_key = f"{self._redis_key_prefix}:pending"
        self._processing_key = f"{self._redis_key_prefix}:processing"
        self._completed_key = f"{self._redis_key_prefix}:completed"
        self._failed_key = f"{self._redis_key_prefix}:failed"

    @property
    def size(self) -> int:
        """Get the number of pending items in the queue."""
        return len(self._queue)

    @property
    def total_pending(self) -> int:
        """Get total pending items including those in processing."""
        return len(self._pending)

    @property
    def total_processing(self) -> int:
        """Get total items currently being processed."""
        return len(self._processing)

    @property
    def total_completed(self) -> int:
        """Get total completed items."""
        return len(self._completed)

    @property
    def total_failed(self) -> int:
        """Get total failed items."""
        return len(self._failed)

    @property
    def is_empty(self) -> bool:
        """Check if the queue is empty."""
        return len(self._queue) == 0

    async def _get_redis(self) -> RedisClient | None:
        """Get Redis client, connecting if necessary."""
        if not self._use_redis:
            return None

        if self._redis is None:
            self._redis = get_redis_client()

        if not self._redis.is_connected:
            await self._redis.connect()

        return self._redis

    async def add(self, item: PromptQueueItem) -> None:
        """
        Add a prompt to the queue.

        Args:
            item: The prompt queue item to add.
        """
        async with self._lock:
            if item.prompt_id in self._pending or item.prompt_id in self._processing:
                logger.debug(
                    "Prompt already in queue",
                    prompt_id=str(item.prompt_id),
                )
                return

            prioritized = PrioritizedPrompt.from_queue_item(item)
            heappush(self._queue, prioritized)
            self._pending.add(item.prompt_id)

            # Persist to Redis
            redis = await self._get_redis()
            if redis:
                await redis.hset(
                    self._pending_key,
                    str(item.prompt_id),
                    item.model_dump_json(),
                )

            logger.debug(
                "Added prompt to queue",
                prompt_id=str(item.prompt_id),
                priority=item.priority,
                queue_size=self.size,
            )

    async def add_batch(self, items: list[PromptQueueItem]) -> int:
        """
        Add multiple prompts to the queue.

        Args:
            items: List of prompt queue items to add.

        Returns:
            Number of items actually added.
        """
        added = 0
        for item in items:
            if item.prompt_id not in self._pending and item.prompt_id not in self._processing:
                await self.add(item)
                added += 1
        return added

    async def get(self) -> PromptQueueItem | None:
        """
        Get the next prompt from the queue.

        Returns:
            The next prompt item, or None if queue is empty.
        """
        async with self._lock:
            if not self._queue:
                return None

            prioritized = heappop(self._queue)
            item = prioritized.item

            # Move from pending to processing
            self._pending.discard(item.prompt_id)
            self._processing.add(item.prompt_id)

            # Update Redis
            redis = await self._get_redis()
            if redis:
                await redis.hdel(self._pending_key, str(item.prompt_id))
                await redis.hset(
                    self._processing_key,
                    str(item.prompt_id),
                    item.model_dump_json(),
                )

            logger.debug(
                "Retrieved prompt from queue",
                prompt_id=str(item.prompt_id),
                remaining=self.size,
            )

            return item

    async def get_batch(self, batch_size: int = 10) -> list[PromptQueueItem]:
        """
        Get multiple prompts from the queue.

        Args:
            batch_size: Maximum number of items to retrieve.

        Returns:
            List of prompt items.
        """
        items = []
        for _ in range(min(batch_size, self.size)):
            item = await self.get()
            if item is None:
                break
            items.append(item)
        return items

    async def mark_completed(self, prompt_id: uuid.UUID) -> None:
        """
        Mark a prompt as completed.

        Args:
            prompt_id: UUID of the completed prompt.
        """
        async with self._lock:
            if prompt_id in self._processing:
                self._processing.discard(prompt_id)
                self._completed.add(prompt_id)

                redis = await self._get_redis()
                if redis:
                    await redis.hdel(self._processing_key, str(prompt_id))
                    await redis.client.sadd(self._completed_key, str(prompt_id))

                logger.debug(
                    "Marked prompt as completed",
                    prompt_id=str(prompt_id),
                )

    async def mark_failed(
        self,
        prompt_id: uuid.UUID,
        error: str | None = None,
        retry: bool = True,
    ) -> bool:
        """
        Mark a prompt as failed, optionally retrying.

        Args:
            prompt_id: UUID of the failed prompt.
            error: Error message if any.
            retry: Whether to retry the prompt.

        Returns:
            True if the prompt was re-queued for retry.
        """
        async with self._lock:
            if prompt_id not in self._processing:
                return False

            # Get the item from Redis if available
            redis = await self._get_redis()
            item_data = None
            if redis:
                item_data = await redis.hget(self._processing_key, str(prompt_id))

            self._processing.discard(prompt_id)

            if item_data and retry:
                item = PromptQueueItem.model_validate_json(item_data)
                if item.retry_count < item.max_retries:
                    # Re-queue with incremented retry count
                    item.retry_count += 1
                    item.priority -= 1  # Lower priority for retries
                    await self.add(item)

                    logger.warning(
                        "Re-queued failed prompt for retry",
                        prompt_id=str(prompt_id),
                        retry_count=item.retry_count,
                        error=error,
                    )
                    return True

            # Mark as permanently failed
            self._failed.add(prompt_id)
            if redis:
                await redis.hdel(self._processing_key, str(prompt_id))
                await redis.client.sadd(self._failed_key, str(prompt_id))

            logger.error(
                "Marked prompt as failed",
                prompt_id=str(prompt_id),
                error=error,
            )
            return False

    async def requeue_processing(self) -> int:
        """
        Re-queue all items currently in processing state.

        Useful for recovering from crashes or timeouts.

        Returns:
            Number of items re-queued.
        """
        redis = await self._get_redis()
        if not redis:
            return 0

        processing_items = await redis.hgetall(self._processing_key)
        count = 0

        for prompt_id_str, item_data in processing_items.items():
            try:
                item = PromptQueueItem.model_validate_json(item_data)
                prompt_id = uuid.UUID(prompt_id_str)

                self._processing.discard(prompt_id)
                await self.add(item)
                count += 1
            except Exception as e:
                logger.error(
                    "Failed to requeue processing item",
                    prompt_id=prompt_id_str,
                    error=str(e),
                )

        return count

    async def clear(self) -> None:
        """Clear all items from the queue."""
        async with self._lock:
            self._queue.clear()
            self._pending.clear()
            self._processing.clear()
            self._completed.clear()
            self._failed.clear()

            redis = await self._get_redis()
            if redis:
                await redis.delete(self._pending_key)
                await redis.delete(self._processing_key)
                await redis.delete(self._completed_key)
                await redis.delete(self._failed_key)

    async def get_stats(self) -> dict[str, Any]:
        """Get queue statistics."""
        return {
            "simulation_id": str(self.simulation_id),
            "queue_size": self.size,
            "pending": self.total_pending,
            "processing": self.total_processing,
            "completed": self.total_completed,
            "failed": self.total_failed,
            "total": self.total_pending + self.total_processing + self.total_completed + self.total_failed,
        }

    async def __aiter__(self) -> AsyncIterator[PromptQueueItem]:
        """Async iterator for processing queue items."""
        while True:
            item = await self.get()
            if item is None:
                break
            yield item

    def __len__(self) -> int:
        """Return the size of the queue."""
        return self.size
