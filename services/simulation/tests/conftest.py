"""
Pytest fixtures for LLM Simulation Service tests.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.simulation.schemas import (
    LLMProviderType,
    LLMQueryResponse,
    NormalizedLLMResponse,
    PromptQueueItem,
)


@pytest.fixture
def mock_llm_response():
    """Create a mock LLM response."""
    def _create(
        provider: LLMProviderType = LLMProviderType.OPENAI,
        text: str = "Here are some project management tools: Asana is great for teams, Monday.com offers visual workflows, and Trello is perfect for simple boards.",
        model: str = "gpt-4o",
        tokens: int = 150,
        latency: int = 500,
    ):
        return LLMQueryResponse(
            provider=provider,
            model=model,
            response_text=text,
            tokens_used=tokens,
            latency_ms=latency,
            success=True,
        )
    return _create


@pytest.fixture
def mock_normalized_response():
    """Create a mock normalized LLM response."""
    def _create(
        provider: LLMProviderType = LLMProviderType.OPENAI,
        text: str = "I recommend Slack for team communication. Microsoft Teams is also a great alternative.",
    ):
        return NormalizedLLMResponse(
            simulation_run_id=uuid.uuid4(),
            prompt_id=uuid.uuid4(),
            provider=provider,
            model="gpt-4o",
            response_text=text,
            tokens_used=100,
            latency_ms=500,
        )
    return _create


@pytest.fixture
def mock_prompt_item():
    """Create a mock prompt queue item."""
    def _create(
        prompt_text: str = "What are the best project management tools?",
        priority: int = 0,
    ):
        return PromptQueueItem(
            prompt_id=uuid.uuid4(),
            prompt_text=prompt_text,
            website_id=uuid.uuid4(),
            priority=priority,
        )
    return _create


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client."""
    client = AsyncMock()
    client.is_connected = True
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    client.hset = AsyncMock(return_value=1)
    client.hget = AsyncMock(return_value=None)
    client.hgetall = AsyncMock(return_value={})
    client.hdel = AsyncMock(return_value=1)
    client.delete = AsyncMock(return_value=1)
    client.expire = AsyncMock(return_value=True)
    client.client = AsyncMock()
    client.client.sadd = AsyncMock(return_value=1)
    return client


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    with patch("services.simulation.components.adapters.get_llm_client") as mock:
        client = AsyncMock()
        client.complete = AsyncMock()
        client.health_check = AsyncMock(return_value=True)
        mock.return_value = client
        yield client


@pytest.fixture
def mock_all_llm_clients():
    """Create mocks for all LLM clients."""
    responses = {
        LLMProviderType.OPENAI: "OpenAI recommends Notion for documentation.",
        LLMProviderType.GOOGLE: "Gemini suggests Google Workspace for collaboration.",
        LLMProviderType.ANTHROPIC: "Claude thinks Basecamp is excellent for projects.",
        LLMProviderType.PERPLEXITY: "Perplexity found that ClickUp is popular.",
    }

    with patch("services.simulation.components.adapters.get_llm_client") as mock:
        def get_client(provider, model=None):
            client = AsyncMock()

            async def mock_complete(*args, **kwargs):
                from shared.llm.base import LLMResponse as BaseLLMResponse
                return BaseLLMResponse(
                    text=responses.get(provider, "Default response"),
                    model=model or "test-model",
                    provider=provider.value if hasattr(provider, "value") else str(provider),
                    tokens_used=100,
                    latency_ms=500,
                )

            client.complete = mock_complete
            client.health_check = AsyncMock(return_value=True)
            return client

        mock.side_effect = get_client
        yield mock


@pytest.fixture
def sample_responses_with_brands():
    """Sample responses containing brand mentions."""
    return [
        {
            "provider": LLMProviderType.OPENAI,
            "text": "For project management, I highly recommend Asana. It's the best choice for teams. You might also consider Monday.com or Trello as alternatives.",
        },
        {
            "provider": LLMProviderType.GOOGLE,
            "text": "Notion is a trusted platform for documentation. Confluence is another popular option used by many enterprises.",
        },
        {
            "provider": LLMProviderType.ANTHROPIC,
            "text": "Slack is the leading communication tool. Microsoft Teams offers similar features and is ideal for companies already using Office 365.",
        },
        {
            "provider": LLMProviderType.PERPLEXITY,
            "text": "According to recent data, GitHub is the most widely used version control platform. GitLab and Bitbucket are also popular alternatives.",
        },
    ]
