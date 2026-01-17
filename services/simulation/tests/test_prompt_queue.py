"""
Tests for the Prompt Queue component.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from services.simulation.components.prompt_queue import PromptQueue
from services.simulation.schemas import PromptQueueItem


class TestPromptQueue:
    """Tests for PromptQueue."""

    @pytest.fixture
    def queue(self, mock_redis_client):
        """Create a test queue."""
        return PromptQueue(
            simulation_id=uuid.uuid4(),
            redis_client=mock_redis_client,
            use_redis=False,  # Use local-only for most tests
        )

    @pytest.fixture
    def queue_with_redis(self, mock_redis_client):
        """Create a test queue with Redis."""
        return PromptQueue(
            simulation_id=uuid.uuid4(),
            redis_client=mock_redis_client,
            use_redis=True,
        )

    @pytest.mark.asyncio
    async def test_add_item(self, queue, mock_prompt_item):
        """Test adding an item to the queue."""
        item = mock_prompt_item()
        await queue.add(item)

        assert queue.size == 1
        assert queue.total_pending == 1
        assert item.prompt_id in queue._pending

    @pytest.mark.asyncio
    async def test_add_duplicate_item(self, queue, mock_prompt_item):
        """Test that duplicate items are not added."""
        item = mock_prompt_item()
        await queue.add(item)
        await queue.add(item)  # Try to add same item again

        assert queue.size == 1
        assert queue.total_pending == 1

    @pytest.mark.asyncio
    async def test_get_item(self, queue, mock_prompt_item):
        """Test getting an item from the queue."""
        item = mock_prompt_item()
        await queue.add(item)

        retrieved = await queue.get()

        assert retrieved is not None
        assert retrieved.prompt_id == item.prompt_id
        assert queue.size == 0
        assert queue.total_processing == 1

    @pytest.mark.asyncio
    async def test_get_from_empty_queue(self, queue):
        """Test getting from an empty queue returns None."""
        result = await queue.get()
        assert result is None

    @pytest.mark.asyncio
    async def test_priority_ordering(self, queue, mock_prompt_item):
        """Test that higher priority items are retrieved first."""
        low_priority = mock_prompt_item(priority=0)
        high_priority = mock_prompt_item(priority=10)

        await queue.add(low_priority)
        await queue.add(high_priority)

        # Should get high priority first
        first = await queue.get()
        assert first.priority == 10

        second = await queue.get()
        assert second.priority == 0

    @pytest.mark.asyncio
    async def test_mark_completed(self, queue, mock_prompt_item):
        """Test marking an item as completed."""
        item = mock_prompt_item()
        await queue.add(item)
        await queue.get()  # Move to processing

        await queue.mark_completed(item.prompt_id)

        assert queue.total_processing == 0
        assert queue.total_completed == 1
        assert item.prompt_id in queue._completed

    @pytest.mark.asyncio
    async def test_mark_failed_with_retry(self, queue_with_redis, mock_redis_client):
        """Test marking an item as failed with retry."""
        item = PromptQueueItem(
            prompt_id=uuid.uuid4(),
            prompt_text="Test prompt",
            website_id=uuid.uuid4(),
            retry_count=0,
            max_retries=3,
        )

        # Setup mock to return item data
        mock_redis_client.hget = AsyncMock(return_value=item.model_dump_json())

        await queue_with_redis.add(item)
        await queue_with_redis.get()  # Move to processing

        # Mark as failed with retry
        retried = await queue_with_redis.mark_failed(
            item.prompt_id,
            error="Test error",
            retry=True,
        )

        assert retried is True
        assert queue_with_redis.size == 1  # Item re-queued

    @pytest.mark.asyncio
    async def test_mark_failed_max_retries(self, queue_with_redis, mock_redis_client):
        """Test that item is not retried after max retries."""
        item = PromptQueueItem(
            prompt_id=uuid.uuid4(),
            prompt_text="Test prompt",
            website_id=uuid.uuid4(),
            retry_count=3,
            max_retries=3,
        )

        mock_redis_client.hget = AsyncMock(return_value=item.model_dump_json())

        await queue_with_redis.add(item)
        await queue_with_redis.get()

        retried = await queue_with_redis.mark_failed(
            item.prompt_id,
            error="Test error",
            retry=True,
        )

        assert retried is False
        assert queue_with_redis.total_failed == 1

    @pytest.mark.asyncio
    async def test_get_batch(self, queue, mock_prompt_item):
        """Test getting multiple items at once."""
        items = [mock_prompt_item() for _ in range(5)]
        for item in items:
            await queue.add(item)

        batch = await queue.get_batch(batch_size=3)

        assert len(batch) == 3
        assert queue.size == 2
        assert queue.total_processing == 3

    @pytest.mark.asyncio
    async def test_clear(self, queue, mock_prompt_item):
        """Test clearing the queue."""
        items = [mock_prompt_item() for _ in range(3)]
        for item in items:
            await queue.add(item)

        await queue.clear()

        assert queue.size == 0
        assert queue.total_pending == 0
        assert queue.total_processing == 0
        assert queue.total_completed == 0
        assert queue.total_failed == 0

    @pytest.mark.asyncio
    async def test_get_stats(self, queue, mock_prompt_item):
        """Test getting queue statistics."""
        item = mock_prompt_item()
        await queue.add(item)
        await queue.get()
        await queue.mark_completed(item.prompt_id)

        stats = await queue.get_stats()

        assert stats["queue_size"] == 0
        assert stats["pending"] == 0
        assert stats["processing"] == 0
        assert stats["completed"] == 1
        assert stats["failed"] == 0

    @pytest.mark.asyncio
    async def test_async_iteration(self, queue, mock_prompt_item):
        """Test async iteration over queue items."""
        items = [mock_prompt_item() for _ in range(3)]
        for item in items:
            await queue.add(item)

        retrieved = []
        async for item in queue:
            retrieved.append(item)

        assert len(retrieved) == 3
        assert queue.is_empty
