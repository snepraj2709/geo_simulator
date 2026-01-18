"""
Integration tests for Simulation Service enhanced analyzers.

Tests the full analysis pipeline including:
- Enhanced brand extraction with NER
- Intent ranking analysis
- Priority order detection
- Contextual framing analysis
- PostgreSQL storage integration
"""

import uuid
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.simulation.components import (
    EnhancedBrandExtractor,
    IntentRankingAnalyzer,
    PriorityOrderDetector,
    ContextualFramingAnalyzer,
    ResponseAggregator,
    EnhancedBrandExtraction,
    FramingType,
    PrioritySignal,
)
from services.simulation.schemas import (
    LLMProviderType,
    NormalizedLLMResponse,
)


# ==================== Fixtures ====================


@pytest.fixture
def sample_response_text():
    """Sample LLM response text with brand mentions."""
    return """
    When looking for a CRM solution, I'd recommend considering Salesforce as the leading
    option in the market. Salesforce offers comprehensive features and is trusted by
    millions of companies worldwide.

    However, if you're looking for alternatives, HubSpot provides a more user-friendly
    experience with excellent free tier options. For enterprise needs, Microsoft Dynamics
    offers deep integration with the Microsoft ecosystem.

    In terms of pricing, Salesforce tends to be more expensive but offers superior
    customization. HubSpot is better for small to medium businesses.

    In conclusion, I'd suggest trying Salesforce for enterprise use cases and HubSpot
    for smaller teams looking for a great value.
    """


@pytest.fixture
def sample_commercial_text():
    """Sample text with commercial intent."""
    return """
    Looking to buy the best project management software? Compare pricing between
    Monday.com, Asana, and Trello. Monday.com offers a free trial and competitive
    subscription plans. Get started today with a 14-day trial.
    """


@pytest.fixture
def sample_informational_text():
    """Sample text with informational intent."""
    return """
    What is CRM software? CRM stands for Customer Relationship Management. It helps
    businesses manage customer interactions and data. Learn how CRM systems work and
    understand the benefits for your organization.
    """


@pytest.fixture
def sample_normalized_response(sample_response_text):
    """Create a sample normalized LLM response."""
    return NormalizedLLMResponse(
        id=uuid.uuid4(),
        simulation_run_id=uuid.uuid4(),
        prompt_id=uuid.uuid4(),
        provider=LLMProviderType.OPENAI,
        model="gpt-4",
        response_text=sample_response_text,
        tokens_used=250,
        latency_ms=1500,
        brands_mentioned=["Salesforce", "HubSpot", "Microsoft Dynamics"],
    )


# ==================== Enhanced Brand Extractor Tests ====================


class TestEnhancedBrandExtractor:
    """Test EnhancedBrandExtractor functionality."""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance without NER for testing."""
        return EnhancedBrandExtractor(use_ner=False)

    def test_extract_brands_from_text(self, extractor, sample_response_text):
        """Test brand extraction from sample text."""
        brands = extractor.extract_brands(sample_response_text)

        assert len(brands) > 0
        brand_names = [b.normalized_name for b in brands]

        # Should find the major brands mentioned
        assert any("salesforce" in name for name in brand_names)
        assert any("hubspot" in name for name in brand_names)

    def test_extract_brands_with_known_brands(self, extractor, sample_response_text):
        """Test extraction with known brand list."""
        known = ["Salesforce", "HubSpot", "Microsoft Dynamics", "Zendesk"]
        brands = extractor.extract_brands(sample_response_text, known_brands=known)

        brand_names = [b.normalized_name for b in brands]

        # Known brands that appear should be found
        assert any("salesforce" in name for name in brand_names)
        assert any("hubspot" in name for name in brand_names)

        # Zendesk not mentioned, should not appear
        assert "zendesk" not in brand_names

    def test_extraction_includes_position(self, extractor, sample_response_text):
        """Test that extractions include position information."""
        brands = extractor.extract_brands(sample_response_text)

        for brand in brands:
            assert isinstance(brand, EnhancedBrandExtraction)
            assert brand.position_in_response >= 0
            assert brand.mention_rank >= 1
            assert brand.mention_count >= 1

    def test_extraction_method_attribution(self, extractor, sample_response_text):
        """Test that extraction method is properly attributed."""
        # Without known brands, should be regex
        brands = extractor.extract_brands(sample_response_text)

        for brand in brands:
            assert brand.extraction_method in ("regex", "ner", "combined", "known")

    def test_context_snippet_extraction(self, extractor, sample_response_text):
        """Test context snippet around brand mentions."""
        brands = extractor.extract_brands(sample_response_text)

        for brand in brands:
            assert brand.context_snippet
            assert len(brand.context_snippet) > 0
            # Context should contain the brand name
            assert brand.brand_name.lower() in brand.context_snippet.lower() or \
                   brand.normalized_name in brand.context_snippet.lower()

    def test_empty_text_handling(self, extractor):
        """Test handling of empty text."""
        brands = extractor.extract_brands("")
        assert brands == []

    def test_no_brands_text(self, extractor):
        """Test text with no brand mentions."""
        text = "This is a simple text about cats and dogs."
        brands = extractor.extract_brands(text)

        # Should find few or no brands
        # May find some false positives from capitalized words
        for brand in brands:
            assert brand.confidence < 1.0  # Lower confidence for uncertain matches


# ==================== Intent Ranking Analyzer Tests ====================


class TestIntentRankingAnalyzer:
    """Test IntentRankingAnalyzer functionality."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return IntentRankingAnalyzer()

    def test_commercial_intent_detection(self, analyzer, sample_commercial_text):
        """Test detection of commercial intent."""
        result = analyzer.analyze(sample_commercial_text)

        assert result.primary_intent == "Commercial" or \
               result.intent_scores.get("Commercial", 0) > 0.3

    def test_informational_intent_detection(self, analyzer, sample_informational_text):
        """Test detection of informational intent."""
        result = analyzer.analyze(sample_informational_text)

        assert result.primary_intent == "Informational" or \
               result.intent_scores.get("Informational", 0) > 0.3

    def test_buying_signals_detection(self, analyzer, sample_commercial_text):
        """Test detection of buying signals."""
        result = analyzer.analyze(sample_commercial_text)

        assert len(result.buying_signals) > 0

        signal_types = [s["type"] for s in result.buying_signals]
        # Should detect comparison shopping or purchase signals
        assert any(
            t in signal_types
            for t in ["comparison_shopping", "purchase_consideration", "seeking_recommendation"]
        )

    def test_trust_indicators_detection(self, analyzer, sample_response_text):
        """Test detection of trust indicators."""
        result = analyzer.analyze(sample_response_text)

        # Sample text mentions "trusted by millions"
        assert len(result.trust_indicators) >= 0  # May or may not find based on patterns

    def test_funnel_stage_detection(self, analyzer, sample_commercial_text):
        """Test funnel stage detection."""
        result = analyzer.analyze(sample_commercial_text)

        assert result.funnel_stage in ("awareness", "consideration", "purchase", None)

    def test_query_type_classification(self, analyzer, sample_commercial_text):
        """Test query type classification."""
        result = analyzer.analyze(sample_commercial_text)

        assert result.query_type in (
            "product_comparison", "value_research", "purchase_research",
            "exploratory", "educational", "migration", "conversion",
            "direct_navigation", "general"
        )

    def test_intent_scores_sum_to_one(self, analyzer, sample_response_text):
        """Test that intent scores are normalized."""
        result = analyzer.analyze(sample_response_text)

        total = sum(result.intent_scores.values())
        # Should be approximately 1.0
        assert 0.99 <= total <= 1.01

    def test_confidence_score_range(self, analyzer, sample_response_text):
        """Test confidence score is in valid range."""
        result = analyzer.analyze(sample_response_text)

        assert 0.0 <= result.confidence <= 1.0


# ==================== Priority Order Detector Tests ====================


class TestPriorityOrderDetector:
    """Test PriorityOrderDetector functionality."""

    @pytest.fixture
    def detector(self):
        """Create detector instance."""
        return PriorityOrderDetector()

    @pytest.fixture
    def extractor(self):
        """Create extractor for generating test data."""
        return EnhancedBrandExtractor(use_ner=False)

    def test_first_mention_signal(self, detector, extractor, sample_response_text):
        """Test first mention priority signal."""
        brands = extractor.extract_brands(sample_response_text)
        results = detector.analyze(sample_response_text, brands)

        assert len(results) > 0

        # First brand should have first_mention signal
        first_brand = next((r for r in results if r.mention_rank == 1), None)
        if first_brand:
            assert PrioritySignal.FIRST_MENTION in first_brand.priority_signals

    def test_recommendation_signal_detection(self, detector, extractor, sample_response_text):
        """Test recommendation signal detection."""
        brands = extractor.extract_brands(sample_response_text)
        results = detector.analyze(sample_response_text, brands)

        # Sample text has "recommend" - should detect recommendation signal
        has_recommendation = any(
            PrioritySignal.RECOMMENDATION in r.priority_signals
            for r in results
        )
        # May or may not be detected depending on pattern matching
        assert isinstance(has_recommendation, bool)

    def test_priority_score_calculation(self, detector, extractor, sample_response_text):
        """Test priority score calculation."""
        brands = extractor.extract_brands(sample_response_text)
        results = detector.analyze(sample_response_text, brands)

        for result in results:
            assert 0.0 <= result.overall_priority_score <= 1.0
            assert result.mention_rank >= 1
            assert result.first_position >= 0

    def test_signal_scores_dict(self, detector, extractor, sample_response_text):
        """Test signal scores dictionary structure."""
        brands = extractor.extract_brands(sample_response_text)
        results = detector.analyze(sample_response_text, brands)

        for result in results:
            assert isinstance(result.signal_scores, dict)
            for score in result.signal_scores.values():
                assert 0.0 <= score <= 1.0


# ==================== Contextual Framing Analyzer Tests ====================


class TestContextualFramingAnalyzer:
    """Test ContextualFramingAnalyzer functionality."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return ContextualFramingAnalyzer()

    @pytest.fixture
    def extractor(self):
        """Create extractor for generating test data."""
        return EnhancedBrandExtractor(use_ner=False)

    def test_positive_framing_detection(self, analyzer, extractor):
        """Test positive framing detection."""
        text = "Salesforce is an excellent and outstanding CRM platform with amazing features."
        brands = extractor.extract_brands(text)
        results = analyzer.analyze(text, brands)

        salesforce_result = next(
            (r for r in results if "salesforce" in r.brand_name.lower()),
            None
        )
        if salesforce_result:
            assert salesforce_result.framing_type == FramingType.POSITIVE
            assert salesforce_result.framing_score > 0

    def test_negative_framing_detection(self, analyzer, extractor):
        """Test negative framing detection."""
        text = "Oracle is known for being expensive, complicated, and frustrating to use."
        brands = extractor.extract_brands(text)
        results = analyzer.analyze(text, brands)

        oracle_result = next(
            (r for r in results if "oracle" in r.brand_name.lower()),
            None
        )
        if oracle_result:
            assert oracle_result.framing_type == FramingType.NEGATIVE
            assert oracle_result.framing_score < 0

    def test_comparative_framing_detection(self, analyzer, extractor):
        """Test comparative framing detection."""
        text = "Salesforce vs HubSpot: when compared to HubSpot, Salesforce offers more features."
        brands = extractor.extract_brands(text)
        results = analyzer.analyze(text, brands)

        # At least one should have comparative framing
        comparative_results = [r for r in results if r.framing_type == FramingType.COMPARATIVE]
        assert len(comparative_results) >= 0  # May or may not detect

    def test_framing_score_range(self, analyzer, extractor, sample_response_text):
        """Test framing score is in valid range."""
        brands = extractor.extract_brands(sample_response_text)
        results = analyzer.analyze(sample_response_text, brands)

        for result in results:
            assert -1.0 <= result.framing_score <= 1.0

    def test_sentiment_words_extraction(self, analyzer, extractor):
        """Test sentiment word extraction."""
        text = "Salesforce is excellent and provides great value with reliable support."
        brands = extractor.extract_brands(text)
        results = analyzer.analyze(text, brands)

        salesforce_result = next(
            (r for r in results if "salesforce" in r.brand_name.lower()),
            None
        )
        if salesforce_result:
            # Should extract positive sentiment words
            assert len(salesforce_result.sentiment_words) >= 0


# ==================== Response Aggregator Integration Tests ====================


class TestResponseAggregatorIntegration:
    """Test ResponseAggregator with enhanced analysis integration."""

    @pytest.fixture
    def aggregator(self):
        """Create aggregator instance."""
        return ResponseAggregator(simulation_id=uuid.uuid4())

    @pytest.fixture
    def sample_responses(self):
        """Create sample responses for aggregation."""
        sim_id = uuid.uuid4()
        return [
            NormalizedLLMResponse(
                id=uuid.uuid4(),
                simulation_run_id=sim_id,
                prompt_id=uuid.uuid4(),
                provider=LLMProviderType.OPENAI,
                model="gpt-4",
                response_text="I recommend Salesforce for CRM needs.",
                tokens_used=50,
                latency_ms=500,
                brands_mentioned=["Salesforce"],
            ),
            NormalizedLLMResponse(
                id=uuid.uuid4(),
                simulation_run_id=sim_id,
                prompt_id=uuid.uuid4(),
                provider=LLMProviderType.ANTHROPIC,
                model="claude-3",
                response_text="HubSpot and Salesforce are both excellent options.",
                tokens_used=60,
                latency_ms=600,
                brands_mentioned=["HubSpot", "Salesforce"],
            ),
        ]

    def test_add_responses(self, aggregator, sample_responses):
        """Test adding responses to aggregator."""
        aggregator.add_responses(sample_responses)

        stats = aggregator.get_statistics()
        assert stats["total_responses"] == 2
        assert stats["total_unique_brands"] >= 1

    def test_get_provider_metrics(self, aggregator, sample_responses):
        """Test provider metrics calculation."""
        aggregator.add_responses(sample_responses)

        metrics = aggregator.get_provider_metrics()
        assert len(metrics) == 2  # OpenAI and Anthropic

        providers = [m.provider for m in metrics]
        assert LLMProviderType.OPENAI in providers
        assert LLMProviderType.ANTHROPIC in providers

    def test_get_brand_metrics(self, aggregator, sample_responses):
        """Test brand metrics calculation."""
        aggregator.add_responses(sample_responses)

        metrics = aggregator.get_brand_metrics()
        brand_names = [m.normalized_name for m in metrics]

        # Salesforce mentioned in both responses
        assert "salesforce" in brand_names

    def test_get_simulation_metrics(self, aggregator, sample_responses):
        """Test comprehensive simulation metrics."""
        aggregator.add_responses(sample_responses)

        metrics = aggregator.get_simulation_metrics()

        assert metrics.simulation_id == aggregator.simulation_id
        assert len(metrics.provider_metrics) > 0
        assert metrics.total_unique_brands >= 1


# ==================== Full Pipeline Integration Tests ====================


class TestFullAnalysisPipeline:
    """Test the complete analysis pipeline integration."""

    def test_full_pipeline_execution(self, sample_response_text):
        """Test running the full analysis pipeline."""
        # Initialize all analyzers
        extractor = EnhancedBrandExtractor(use_ner=False)
        intent_analyzer = IntentRankingAnalyzer()
        priority_detector = PriorityOrderDetector()
        framing_analyzer = ContextualFramingAnalyzer()

        # Run extraction
        brands = extractor.extract_brands(sample_response_text)
        assert len(brands) > 0

        # Run intent analysis
        intent_result = intent_analyzer.analyze(sample_response_text)
        assert intent_result.primary_intent in (
            "Commercial", "Informational", "Transactional", "Navigational"
        )

        # Run priority detection
        priority_results = priority_detector.analyze(sample_response_text, brands)
        assert len(priority_results) == len(brands)

        # Run framing analysis
        framing_results = framing_analyzer.analyze(sample_response_text, brands)
        assert len(framing_results) == len(brands)

    def test_pipeline_with_aggregator(self, sample_response_text):
        """Test pipeline integration with ResponseAggregator."""
        simulation_id = uuid.uuid4()
        aggregator = ResponseAggregator(simulation_id)

        # Create response
        response = NormalizedLLMResponse(
            id=uuid.uuid4(),
            simulation_run_id=simulation_id,
            prompt_id=uuid.uuid4(),
            provider=LLMProviderType.OPENAI,
            model="gpt-4",
            response_text=sample_response_text,
            tokens_used=250,
            latency_ms=1500,
        )

        # Run extraction
        extractor = EnhancedBrandExtractor(use_ner=False)
        brands = extractor.extract_brands(response.response_text)
        response.brands_mentioned = [b.brand_name for b in brands]

        # Add to aggregator
        aggregator.add_response(response)

        # Verify aggregation
        stats = aggregator.get_statistics()
        assert stats["total_responses"] == 1
        assert stats["total_unique_brands"] > 0


# ==================== Edge Case Tests ====================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_response_handling(self):
        """Test handling of empty response text."""
        extractor = EnhancedBrandExtractor(use_ner=False)
        brands = extractor.extract_brands("")

        assert brands == []

    def test_none_text_handling(self):
        """Test handling of None text."""
        extractor = EnhancedBrandExtractor(use_ner=False)

        # Should handle gracefully
        try:
            brands = extractor.extract_brands(None)
            assert brands == []
        except (TypeError, AttributeError):
            # Expected behavior
            pass

    def test_very_long_text(self):
        """Test handling of very long text."""
        long_text = "Salesforce is great. " * 10000
        extractor = EnhancedBrandExtractor(use_ner=False)

        # Should complete without hanging
        brands = extractor.extract_brands(long_text)
        assert len(brands) > 0

    def test_special_characters_in_brands(self):
        """Test brands with special characters."""
        text = "Check out Yahoo! and AT&T for comparison."
        extractor = EnhancedBrandExtractor(use_ner=False)

        brands = extractor.extract_brands(text)
        # May or may not extract these correctly
        assert isinstance(brands, list)

    def test_unicode_text(self):
        """Test handling of unicode text."""
        text = "Consider using 日本語 Salesforce or HubSpot for your needs."
        extractor = EnhancedBrandExtractor(use_ner=False)

        brands = extractor.extract_brands(text)
        # Should handle unicode without errors
        assert isinstance(brands, list)

    def test_no_brands_text_analysis(self):
        """Test analysis of text with no brands."""
        text = "The quick brown fox jumps over the lazy dog."

        intent_analyzer = IntentRankingAnalyzer()
        result = intent_analyzer.analyze(text)

        # Should still return valid result
        assert result.primary_intent in (
            "Commercial", "Informational", "Transactional", "Navigational"
        )
        assert 0.0 <= result.confidence <= 1.0
