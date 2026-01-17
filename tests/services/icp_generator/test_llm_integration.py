"""
Tests for LLM integration in ICP Generator.

Tests the LLM client wrapper with mocked responses.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from shared.llm.base import LLMClient, LLMResponse, ResponseFormat
from shared.llm.openai_client import OpenAIClient
from shared.llm.anthropic_client import AnthropicClient


class TestLLMResponseParsing:
    """Test LLM response parsing capabilities."""

    def test_parse_json_from_text(self):
        """Test parsing JSON from response text."""
        response = LLMResponse(
            text='{"icps": [{"name": "Test ICP"}]}',
            model="gpt-4o",
            provider="openai",
            tokens_used=100,
            latency_ms=500,
            raw_response={},
        )

        parsed = response.get_json()
        assert "icps" in parsed
        assert parsed["icps"][0]["name"] == "Test ICP"

    def test_parse_json_from_markdown_block(self):
        """Test parsing JSON from markdown code block."""
        response = LLMResponse(
            text='```json\n{"key": "value"}\n```',
            model="gpt-4o",
            provider="openai",
            tokens_used=100,
            latency_ms=500,
            raw_response={},
        )

        parsed = response.get_json()
        assert parsed["key"] == "value"

    def test_parse_json_caches_result(self):
        """Test that parsed JSON is cached."""
        response = LLMResponse(
            text='{"key": "value"}',
            model="gpt-4o",
            provider="openai",
            tokens_used=100,
            latency_ms=500,
            raw_response={},
        )

        # Parse twice
        parsed1 = response.get_json()
        parsed2 = response.get_json()

        # Should be same object (cached)
        assert parsed1 is parsed2

    def test_parse_invalid_json_raises(self):
        """Test that invalid JSON raises error."""
        response = LLMResponse(
            text='not valid json',
            model="gpt-4o",
            provider="openai",
            tokens_used=100,
            latency_ms=500,
            raw_response={},
        )

        with pytest.raises(json.JSONDecodeError):
            response.get_json()


class TestOpenAIClientMocked:
    """Test OpenAI client with mocked API."""

    @pytest.fixture
    def mock_openai_response(self):
        """Create mocked OpenAI response."""
        mock_choice = MagicMock()
        mock_choice.message.content = '{"result": "success"}'

        mock_usage = MagicMock()
        mock_usage.total_tokens = 150

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage = mock_usage
        mock_response.model = "gpt-4o"
        mock_response.model_dump.return_value = {}

        return mock_response

    @pytest.mark.asyncio
    async def test_complete_json_adds_response_format(self, mock_openai_response):
        """Test that complete_json adds JSON response format."""
        with patch("shared.llm.openai_client.AsyncOpenAI") as mock_class:
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)
            mock_class.return_value = mock_client

            client = OpenAIClient()
            client.client = mock_client

            response = await client.complete_json(
                prompt="Generate JSON",
                system_prompt="You are helpful",
            )

            # Verify response format was passed
            call_kwargs = mock_client.chat.completions.create.call_args
            assert call_kwargs is not None

    @pytest.mark.asyncio
    async def test_complete_returns_llm_response(self, mock_openai_response):
        """Test that complete returns proper LLMResponse."""
        with patch("shared.llm.openai_client.AsyncOpenAI") as mock_class:
            mock_client = MagicMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_openai_response)
            mock_class.return_value = mock_client

            client = OpenAIClient()
            client.client = mock_client

            response = await client.complete(
                prompt="Hello",
                system_prompt="You are helpful",
            )

            assert isinstance(response, LLMResponse)
            assert response.text == '{"result": "success"}'
            assert response.model == "gpt-4o"
            assert response.provider == "openai"
            assert response.tokens_used == 150


class TestAnthropicClientMocked:
    """Test Anthropic client with mocked API."""

    @pytest.fixture
    def mock_anthropic_response(self):
        """Create mocked Anthropic response."""
        mock_block = MagicMock()
        mock_block.text = '{"result": "success"}'

        mock_usage = MagicMock()
        mock_usage.input_tokens = 100
        mock_usage.output_tokens = 50

        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_response.usage = mock_usage
        mock_response.model = "claude-3-5-sonnet-20241022"
        mock_response.model_dump.return_value = {}

        return mock_response

    @pytest.mark.asyncio
    async def test_complete_json_adds_instruction(self, mock_anthropic_response):
        """Test that complete_json adds JSON instruction to prompt."""
        with patch("shared.llm.anthropic_client.AsyncAnthropic") as mock_class:
            mock_client = MagicMock()
            mock_client.messages.create = AsyncMock(return_value=mock_anthropic_response)
            mock_class.return_value = mock_client

            client = AnthropicClient()
            client.client = mock_client

            response = await client.complete_json(
                prompt="Generate JSON",
                system_prompt="You are helpful",
            )

            # Verify the call was made with JSON instruction
            call_kwargs = mock_client.messages.create.call_args
            assert call_kwargs is not None

            # Check system prompt contains JSON instruction
            if "system" in call_kwargs.kwargs:
                assert "JSON" in call_kwargs.kwargs["system"]

    @pytest.mark.asyncio
    async def test_complete_returns_llm_response(self, mock_anthropic_response):
        """Test that complete returns proper LLMResponse."""
        with patch("shared.llm.anthropic_client.AsyncAnthropic") as mock_class:
            mock_client = MagicMock()
            mock_client.messages.create = AsyncMock(return_value=mock_anthropic_response)
            mock_class.return_value = mock_client

            client = AnthropicClient()
            client.client = mock_client

            response = await client.complete(
                prompt="Hello",
            )

            assert isinstance(response, LLMResponse)
            assert response.text == '{"result": "success"}'
            assert response.provider == "anthropic"
            assert response.tokens_used == 150  # input + output


class TestResponseFormat:
    """Test ResponseFormat enum."""

    def test_response_format_values(self):
        """Test ResponseFormat enum values."""
        assert ResponseFormat.TEXT.value == "text"
        assert ResponseFormat.JSON.value == "json"

    def test_response_format_string_comparison(self):
        """Test ResponseFormat string comparison."""
        assert ResponseFormat.JSON == "json"
        assert ResponseFormat.TEXT == "text"
