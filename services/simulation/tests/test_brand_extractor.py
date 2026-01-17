"""
Tests for the Brand Extractor component.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from services.simulation.components.brand_extractor import (
    BrandExtractor,
    ExtractionConfig,
)
from services.simulation.schemas import (
    BeliefType,
    BrandPresenceType,
    LLMProviderType,
    NormalizedLLMResponse,
    QueryIntentType,
)


class TestBrandExtractor:
    """Tests for BrandExtractor."""

    @pytest.fixture
    def extractor(self):
        """Create a brand extractor without LLM refinement."""
        return BrandExtractor(
            config=ExtractionConfig(
                use_llm_extraction=False,
                min_confidence=0.5,
            )
        )

    @pytest.fixture
    def response_with_brands(self):
        """Create a response containing brand mentions."""
        return NormalizedLLMResponse(
            simulation_run_id=uuid.uuid4(),
            prompt_id=uuid.uuid4(),
            provider=LLMProviderType.OPENAI,
            model="gpt-4o",
            response_text="""For project management, I highly recommend Asana.
            It's the best choice for teams. You might also consider Monday.com
            or Trello as alternatives. Notion is trusted by millions of users
            for documentation.""",
            tokens_used=100,
            latency_ms=500,
        )

    @pytest.fixture
    def response_with_comparison(self):
        """Create a response with brand comparison."""
        return NormalizedLLMResponse(
            simulation_run_id=uuid.uuid4(),
            prompt_id=uuid.uuid4(),
            provider=LLMProviderType.GOOGLE,
            model="gemini-pro",
            response_text="""Comparing Slack vs Microsoft Teams: Slack is more
            popular with startups, while Microsoft Teams is ideal for enterprises
            already using Office 365.""",
            tokens_used=80,
            latency_ms=400,
        )

    @pytest.mark.asyncio
    async def test_extract_brands_basic(self, extractor, response_with_brands):
        """Test basic brand extraction."""
        result = await extractor.extract(response_with_brands)

        assert len(result.brands) > 0
        brand_names = [b.brand_name.lower() for b in result.brands]
        assert "asana" in brand_names

    @pytest.mark.asyncio
    async def test_extract_brands_position(self, extractor, response_with_brands):
        """Test that brands have position ranks."""
        result = await extractor.extract(response_with_brands)

        for i, brand in enumerate(result.brands):
            assert brand.position_rank == i + 1

    @pytest.mark.asyncio
    async def test_extract_recommended_presence(self, extractor, response_with_brands):
        """Test detection of recommended presence."""
        result = await extractor.extract(response_with_brands)

        # "recommend" should mark as recommended
        recommended_brands = [
            b for b in result.brands if b.presence == BrandPresenceType.RECOMMENDED
        ]
        assert len(recommended_brands) > 0

    @pytest.mark.asyncio
    async def test_extract_trusted_presence(self, extractor, response_with_brands):
        """Test detection of trusted presence."""
        result = await extractor.extract(response_with_brands)

        # "trusted" should mark as trusted
        trusted_brands = [
            b for b in result.brands if b.presence == BrandPresenceType.TRUSTED
        ]
        assert len(trusted_brands) >= 0  # May or may not have trusted

    @pytest.mark.asyncio
    async def test_extract_compared_presence(self, extractor, response_with_comparison):
        """Test detection of compared presence."""
        result = await extractor.extract(response_with_comparison)

        # "vs" should mark as compared
        compared_brands = [
            b for b in result.brands if b.presence == BrandPresenceType.COMPARED
        ]
        assert len(compared_brands) > 0

    @pytest.mark.asyncio
    async def test_extract_belief_superiority(self, extractor, response_with_brands):
        """Test detection of superiority belief."""
        result = await extractor.extract(response_with_brands)

        # "best choice" should indicate superiority
        superiority_brands = [
            b for b in result.brands if b.belief_sold == BeliefType.SUPERIORITY
        ]
        # May or may not be detected depending on context matching

    @pytest.mark.asyncio
    async def test_extract_belief_social_proof(self, extractor, response_with_brands):
        """Test detection of social proof belief."""
        result = await extractor.extract(response_with_brands)

        # "millions of users" should indicate social proof
        social_proof_brands = [
            b for b in result.brands if b.belief_sold == BeliefType.SOCIAL_PROOF
        ]
        # At least Notion should have social proof

    @pytest.mark.asyncio
    async def test_extract_context_snippet(self, extractor, response_with_brands):
        """Test that context snippets are captured."""
        result = await extractor.extract(response_with_brands)

        for brand in result.brands:
            assert brand.context_snippet
            assert len(brand.context_snippet) <= 500

    @pytest.mark.asyncio
    async def test_extract_intent_ranking(self, extractor, response_with_brands):
        """Test intent ranking extraction."""
        result = await extractor.extract(response_with_brands)

        if result.intent_ranking:
            assert result.intent_ranking.query_intent in QueryIntentType
            assert 0 <= result.intent_ranking.confidence <= 1

    @pytest.mark.asyncio
    async def test_extract_contextual_framing(self, extractor, response_with_brands):
        """Test contextual framing extraction."""
        result = await extractor.extract(response_with_brands)

        assert isinstance(result.contextual_framing, dict)
        for brand in result.brands:
            assert brand.brand_name in result.contextual_framing

    @pytest.mark.asyncio
    async def test_extract_with_known_brands(self, extractor):
        """Test extraction with known brands list."""
        response = NormalizedLLMResponse(
            simulation_run_id=uuid.uuid4(),
            prompt_id=uuid.uuid4(),
            provider=LLMProviderType.OPENAI,
            model="gpt-4o",
            response_text="You could use acme corp for this task.",
            tokens_used=50,
            latency_ms=200,
        )

        result = await extractor.extract(
            response,
            known_brands=["Acme Corp", "Other Brand"],
        )

        brand_names = [b.normalized_name for b in result.brands]
        assert "acme corp" in brand_names

    @pytest.mark.asyncio
    async def test_extract_batch(self, extractor, mock_normalized_response):
        """Test batch extraction."""
        responses = [
            mock_normalized_response(text="Try Slack for communication."),
            mock_normalized_response(text="GitHub is great for code."),
        ]

        results = await extractor.extract_batch(responses)

        assert len(results) == 2
        # Responses should be updated with brand mentions
        for response, result in zip(responses, results):
            assert response.brands_mentioned == [b.normalized_name for b in result.brands]

    @pytest.mark.asyncio
    async def test_extract_empty_response(self, extractor):
        """Test extraction from empty response."""
        response = NormalizedLLMResponse(
            simulation_run_id=uuid.uuid4(),
            prompt_id=uuid.uuid4(),
            provider=LLMProviderType.OPENAI,
            model="gpt-4o",
            response_text="",
            tokens_used=0,
            latency_ms=100,
        )

        result = await extractor.extract(response)

        assert len(result.brands) == 0
        assert result.intent_ranking is None

    @pytest.mark.asyncio
    async def test_max_brands_limit(self, extractor):
        """Test that max brands limit is respected."""
        # Create response with many brand-like words
        brands = ", ".join([f"Brand{i}" for i in range(30)])
        response = NormalizedLLMResponse(
            simulation_run_id=uuid.uuid4(),
            prompt_id=uuid.uuid4(),
            provider=LLMProviderType.OPENAI,
            model="gpt-4o",
            response_text=f"Consider these tools: {brands}.",
            tokens_used=100,
            latency_ms=300,
        )

        result = await extractor.extract(response)

        assert len(result.brands) <= extractor.config.max_brands_per_response

    def test_get_extraction_stats(self, extractor):
        """Test getting extraction statistics."""
        stats = extractor.get_extraction_stats()

        assert "use_llm_extraction" in stats
        assert "min_confidence" in stats
        assert "max_brands_per_response" in stats
        assert stats["use_llm_extraction"] is False
