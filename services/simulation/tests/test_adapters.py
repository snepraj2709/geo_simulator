"""
Tests for the LLM Provider Adapters.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.simulation.components.adapters import (
    AnthropicAdapter,
    BaseLLMAdapter,
    GoogleAdapter,
    LLMAdapterFactory,
    OpenAIAdapter,
    PerplexityAdapter,
)
from services.simulation.schemas import (
    LLMProviderType,
    LLMQueryRequest,
    LLMQueryResponse,
)


class TestOpenAIAdapter:
    """Tests for OpenAIAdapter."""

    @pytest.fixture
    def adapter(self, mock_openai_client):
        """Create an adapter with mocked client."""
        adapter = OpenAIAdapter()
        adapter._client = mock_openai_client
        return adapter

    @pytest.mark.asyncio
    async def test_query_success(self, adapter, mock_openai_client):
        """Test successful query."""
        from shared.llm.base import LLMResponse as BaseLLMResponse

        mock_openai_client.complete = AsyncMock(
            return_value=BaseLLMResponse(
                text="Test response with Asana and Trello",
                model="gpt-4o",
                provider="openai",
                tokens_used=100,
                latency_ms=500,
            )
        )

        response = await adapter.query(
            LLMQueryRequest(
                prompt_text="What are the best project management tools?",
                provider=LLMProviderType.OPENAI,
            )
        )

        assert response.success is True
        assert response.provider == LLMProviderType.OPENAI
        assert "Test response" in response.response_text
        assert response.tokens_used == 100

    @pytest.mark.asyncio
    async def test_query_failure_with_retry(self, adapter, mock_openai_client):
        """Test that failed queries are retried."""
        mock_openai_client.complete = AsyncMock(side_effect=Exception("API Error"))

        response = await adapter.query(
            LLMQueryRequest(
                prompt_text="Test prompt",
                provider=LLMProviderType.OPENAI,
            )
        )

        # After all retries fail, should return error response
        assert response.success is False
        assert response.error is not None
        assert "API Error" in response.error

    @pytest.mark.asyncio
    async def test_get_metrics(self, adapter, mock_openai_client):
        """Test metrics collection."""
        from shared.llm.base import LLMResponse as BaseLLMResponse

        mock_openai_client.complete = AsyncMock(
            return_value=BaseLLMResponse(
                text="Response",
                model="gpt-4o",
                provider="openai",
                tokens_used=50,
                latency_ms=200,
            )
        )

        # Make some queries
        for _ in range(3):
            await adapter.query(
                LLMQueryRequest(
                    prompt_text="Test",
                    provider=LLMProviderType.OPENAI,
                )
            )

        metrics = adapter.get_metrics()

        assert metrics["total_requests"] == 3
        assert metrics["successful_requests"] == 3
        assert metrics["total_tokens"] == 150
        assert metrics["avg_tokens"] == 50

    @pytest.mark.asyncio
    async def test_health_check(self, adapter, mock_openai_client):
        """Test health check."""
        mock_openai_client.health_check = AsyncMock(return_value=True)

        result = await adapter.health_check()
        assert result is True


class TestLLMAdapterFactory:
    """Tests for LLMAdapterFactory."""

    def test_get_adapter_openai(self):
        """Test getting OpenAI adapter."""
        with patch("services.simulation.components.adapters.get_llm_client"):
            adapter = LLMAdapterFactory.get_adapter(LLMProviderType.OPENAI)
            assert isinstance(adapter, OpenAIAdapter)
            assert adapter.provider == LLMProviderType.OPENAI

    def test_get_adapter_google(self):
        """Test getting Google adapter."""
        with patch("services.simulation.components.adapters.get_llm_client"):
            adapter = LLMAdapterFactory.get_adapter(LLMProviderType.GOOGLE)
            assert isinstance(adapter, GoogleAdapter)
            assert adapter.provider == LLMProviderType.GOOGLE

    def test_get_adapter_anthropic(self):
        """Test getting Anthropic adapter."""
        with patch("services.simulation.components.adapters.get_llm_client"):
            adapter = LLMAdapterFactory.get_adapter(LLMProviderType.ANTHROPIC)
            assert isinstance(adapter, AnthropicAdapter)
            assert adapter.provider == LLMProviderType.ANTHROPIC

    def test_get_adapter_perplexity(self):
        """Test getting Perplexity adapter."""
        with patch("services.simulation.components.adapters.get_llm_client"):
            adapter = LLMAdapterFactory.get_adapter(LLMProviderType.PERPLEXITY)
            assert isinstance(adapter, PerplexityAdapter)
            assert adapter.provider == LLMProviderType.PERPLEXITY

    def test_get_adapter_with_custom_model(self):
        """Test getting adapter with custom model."""
        with patch("services.simulation.components.adapters.get_llm_client"):
            LLMAdapterFactory.clear_cache()
            adapter = LLMAdapterFactory.get_adapter(
                LLMProviderType.OPENAI,
                model="gpt-4-turbo",
            )
            assert adapter.model == "gpt-4-turbo"

    def test_get_adapter_caching(self):
        """Test that adapters are cached."""
        with patch("services.simulation.components.adapters.get_llm_client"):
            LLMAdapterFactory.clear_cache()
            adapter1 = LLMAdapterFactory.get_adapter(LLMProviderType.OPENAI)
            adapter2 = LLMAdapterFactory.get_adapter(LLMProviderType.OPENAI)
            assert adapter1 is adapter2

    def test_get_adapters_for_providers(self):
        """Test getting multiple adapters."""
        with patch("services.simulation.components.adapters.get_llm_client"):
            LLMAdapterFactory.clear_cache()
            adapters = LLMAdapterFactory.get_adapters_for_providers([
                LLMProviderType.OPENAI,
                LLMProviderType.GOOGLE,
            ])
            assert len(adapters) == 2

    @pytest.mark.asyncio
    async def test_health_check_all(self):
        """Test health checking all providers."""
        with patch("services.simulation.components.adapters.get_llm_client") as mock:
            client = AsyncMock()
            client.health_check = AsyncMock(return_value=True)
            mock.return_value = client

            LLMAdapterFactory.clear_cache()

            with patch.object(LLMAdapterFactory, "get_available_adapters") as mock_available:
                adapter = OpenAIAdapter()
                adapter._client = client
                mock_available.return_value = [adapter]

                results = await LLMAdapterFactory.health_check_all()
                assert isinstance(results, dict)

    def test_clear_cache(self):
        """Test clearing the adapter cache."""
        with patch("services.simulation.components.adapters.get_llm_client"):
            LLMAdapterFactory.get_adapter(LLMProviderType.OPENAI)
            assert len(LLMAdapterFactory._instances) > 0

            LLMAdapterFactory.clear_cache()
            assert len(LLMAdapterFactory._instances) == 0
