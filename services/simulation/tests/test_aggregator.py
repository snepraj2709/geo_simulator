"""
Tests for the Response Aggregator component.
"""

import uuid

import pytest

from services.simulation.components.aggregator import (
    ResponseAggregator,
    ResponseNormalizer,
)
from services.simulation.schemas import (
    BeliefType,
    BrandExtractionResult,
    BrandMention,
    BrandPresenceType,
    IntentRanking,
    LLMProviderType,
    NormalizedLLMResponse,
    QueryIntentType,
)


class TestResponseAggregator:
    """Tests for ResponseAggregator."""

    @pytest.fixture
    def aggregator(self):
        """Create a test aggregator."""
        return ResponseAggregator(simulation_id=uuid.uuid4())

    @pytest.fixture
    def sample_response(self):
        """Create a sample response."""
        def _create(
            provider: LLMProviderType = LLMProviderType.OPENAI,
            brands: list[str] | None = None,
        ):
            response = NormalizedLLMResponse(
                simulation_run_id=uuid.uuid4(),
                prompt_id=uuid.uuid4(),
                provider=provider,
                model="test-model",
                response_text="Test response",
                tokens_used=100,
                latency_ms=500,
                brands_mentioned=brands or [],
            )
            return response
        return _create

    def test_add_response(self, aggregator, sample_response):
        """Test adding a response."""
        response = sample_response(brands=["Slack", "Teams"])
        aggregator.add_response(response)

        assert len(aggregator._all_responses) == 1
        assert response.prompt_id in aggregator._responses

    def test_add_multiple_responses(self, aggregator, sample_response):
        """Test adding multiple responses."""
        responses = [
            sample_response(LLMProviderType.OPENAI, ["Slack"]),
            sample_response(LLMProviderType.GOOGLE, ["Teams"]),
        ]
        aggregator.add_responses(responses)

        assert len(aggregator._all_responses) == 2

    def test_add_response_same_prompt(self, aggregator):
        """Test adding responses for the same prompt from different providers."""
        prompt_id = uuid.uuid4()

        response1 = NormalizedLLMResponse(
            simulation_run_id=uuid.uuid4(),
            prompt_id=prompt_id,
            provider=LLMProviderType.OPENAI,
            model="gpt-4o",
            response_text="OpenAI response",
            tokens_used=100,
            latency_ms=500,
            brands_mentioned=["Slack"],
        )
        response2 = NormalizedLLMResponse(
            simulation_run_id=uuid.uuid4(),
            prompt_id=prompt_id,
            provider=LLMProviderType.GOOGLE,
            model="gemini",
            response_text="Google response",
            tokens_used=80,
            latency_ms=400,
            brands_mentioned=["Teams"],
        )

        aggregator.add_response(response1)
        aggregator.add_response(response2)

        # Should be grouped under same prompt
        aggregated = aggregator.get_prompt_responses(prompt_id)
        assert aggregated is not None
        assert aggregated.provider_count == 2
        assert LLMProviderType.OPENAI in aggregated.responses
        assert LLMProviderType.GOOGLE in aggregated.responses

    def test_add_brand_extraction(self, aggregator, sample_response):
        """Test adding brand extraction results."""
        response = sample_response()
        aggregator.add_response(response)

        extraction = BrandExtractionResult(
            response_id=response.id,
            brands=[
                BrandMention(
                    brand_name="Slack",
                    normalized_name="slack",
                    presence=BrandPresenceType.RECOMMENDED,
                    position_rank=1,
                    belief_sold=BeliefType.SUPERIORITY,
                    context_snippet="Slack is the best",
                )
            ],
        )

        aggregator.add_brand_extraction(
            response.prompt_id,
            response.provider,
            extraction,
        )

        aggregated = aggregator.get_prompt_responses(response.prompt_id)
        assert len(aggregated.brand_extractions) == 1

    def test_get_provider_metrics(self, aggregator, sample_response):
        """Test getting provider metrics."""
        responses = [
            sample_response(LLMProviderType.OPENAI, ["Slack"]),
            sample_response(LLMProviderType.OPENAI, ["Teams"]),
            sample_response(LLMProviderType.GOOGLE, ["Slack"]),
        ]
        aggregator.add_responses(responses)

        metrics = aggregator.get_provider_metrics()

        openai_metrics = next(m for m in metrics if m.provider == LLMProviderType.OPENAI)
        assert openai_metrics.total_queries == 2
        assert openai_metrics.brands_mentioned == 2

        google_metrics = next(m for m in metrics if m.provider == LLMProviderType.GOOGLE)
        assert google_metrics.total_queries == 1

    def test_get_brand_metrics(self, aggregator, sample_response):
        """Test getting brand metrics."""
        responses = [
            sample_response(LLMProviderType.OPENAI, ["Slack", "Teams"]),
            sample_response(LLMProviderType.GOOGLE, ["Slack"]),
            sample_response(LLMProviderType.ANTHROPIC, ["Slack"]),
        ]
        aggregator.add_responses(responses)

        metrics = aggregator.get_brand_metrics()

        slack_metrics = next(m for m in metrics if m.normalized_name == "slack")
        assert slack_metrics.total_mentions == 3
        assert len(slack_metrics.mentions_by_provider) == 3

    def test_get_simulation_metrics(self, aggregator, sample_response):
        """Test getting comprehensive simulation metrics."""
        response = sample_response(brands=["Slack"])
        aggregator.add_response(response)

        extraction = BrandExtractionResult(
            response_id=response.id,
            brands=[
                BrandMention(
                    brand_name="Slack",
                    normalized_name="slack",
                    presence=BrandPresenceType.RECOMMENDED,
                    position_rank=1,
                    context_snippet="Test",
                )
            ],
            intent_ranking=IntentRanking(
                query_intent=QueryIntentType.COMMERCIAL,
                confidence=0.8,
            ),
        )
        aggregator.add_brand_extraction(response.prompt_id, response.provider, extraction)

        metrics = aggregator.get_simulation_metrics()

        assert metrics.simulation_id == aggregator.simulation_id
        assert len(metrics.provider_metrics) > 0
        assert len(metrics.brand_metrics) > 0
        assert metrics.total_unique_brands > 0

    def test_get_statistics(self, aggregator, sample_response):
        """Test getting summary statistics."""
        responses = [
            sample_response(LLMProviderType.OPENAI, ["Slack"]),
            sample_response(LLMProviderType.GOOGLE, ["Teams"]),
        ]
        aggregator.add_responses(responses)

        stats = aggregator.get_statistics()

        assert stats["total_responses"] == 2
        assert stats["total_prompts"] == 2
        assert stats["total_unique_brands"] == 2

    def test_get_responses_by_provider(self, aggregator, sample_response):
        """Test filtering responses by provider."""
        responses = [
            sample_response(LLMProviderType.OPENAI),
            sample_response(LLMProviderType.OPENAI),
            sample_response(LLMProviderType.GOOGLE),
        ]
        aggregator.add_responses(responses)

        openai_responses = aggregator.get_responses_by_provider(LLMProviderType.OPENAI)
        assert len(openai_responses) == 2

    def test_clear(self, aggregator, sample_response):
        """Test clearing the aggregator."""
        aggregator.add_response(sample_response())
        aggregator.clear()

        assert len(aggregator._all_responses) == 0
        assert len(aggregator._responses) == 0

    def test_all_brands_property(self, aggregator, sample_response):
        """Test getting all unique brands from aggregated responses."""
        prompt_id = uuid.uuid4()

        response1 = NormalizedLLMResponse(
            simulation_run_id=uuid.uuid4(),
            prompt_id=prompt_id,
            provider=LLMProviderType.OPENAI,
            model="gpt-4o",
            response_text="Test",
            tokens_used=100,
            latency_ms=500,
            brands_mentioned=["Slack", "Teams"],
        )
        response2 = NormalizedLLMResponse(
            simulation_run_id=uuid.uuid4(),
            prompt_id=prompt_id,
            provider=LLMProviderType.GOOGLE,
            model="gemini",
            response_text="Test",
            tokens_used=80,
            latency_ms=400,
            brands_mentioned=["Slack", "Zoom"],
        )

        aggregator.add_response(response1)
        aggregator.add_response(response2)

        aggregated = aggregator.get_prompt_responses(prompt_id)
        assert aggregated.all_brands == {"Slack", "Teams", "Zoom"}


class TestResponseNormalizer:
    """Tests for ResponseNormalizer."""

    def test_normalize_text(self):
        """Test text normalization."""
        text = "  Response with   extra   spaces\n\n\n\nand blank lines  "
        normalized = ResponseNormalizer._normalize_text(text)

        assert not normalized.startswith(" ")
        assert not normalized.endswith(" ")
        assert "\n\n\n" not in normalized

    def test_normalize_response(self):
        """Test full response normalization."""
        response = NormalizedLLMResponse(
            simulation_run_id=uuid.uuid4(),
            prompt_id=uuid.uuid4(),
            provider=LLMProviderType.OPENAI,
            model="gpt-4o",
            response_text="  Messy   response  ",
            tokens_used=100,
            latency_ms=500,
        )

        normalized = ResponseNormalizer.normalize(response)

        assert normalized.response_text == "Messy   response"
        assert normalized.id == response.id

    def test_extract_sections(self):
        """Test section extraction from structured response."""
        text = """## Overview
This is the overview section.

## Features
- Feature 1
- Feature 2

## Conclusion
Final thoughts."""

        sections = ResponseNormalizer.extract_sections(text)

        assert "overview" in sections
        assert "features" in sections
        assert "conclusion" in sections

    def test_extract_sections_no_headers(self):
        """Test section extraction when no headers present."""
        text = "Just plain text without any headers."

        sections = ResponseNormalizer.extract_sections(text)

        assert "main" in sections
        assert sections["main"] == text
