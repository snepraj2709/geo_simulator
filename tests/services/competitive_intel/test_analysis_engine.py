"""
Unit tests for Competitive Analysis Engine.

Tests:
- Share of voice calculations
- Substitution pattern detection
- Competitive gap identification
- Opportunity scoring
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest

from services.competitive_intel.components.analysis_engine import (
    AnalysisEngine,
    BrandPresenceData,
    AggregatedMetrics,
)
from services.competitive_intel.schemas import (
    SubstituteInfo,
    OpportunityType,
)


class TestAggregatedMetrics:
    """Tests for AggregatedMetrics calculations."""

    def test_avg_position_with_data(self):
        """Test average position calculation with data."""
        metrics = AggregatedMetrics(
            position_sum=10.0,
            position_count=4,
        )
        assert metrics.avg_position == 2.5

    def test_avg_position_no_data(self):
        """Test average position with no data returns None."""
        metrics = AggregatedMetrics()
        assert metrics.avg_position is None

    def test_visibility_score(self):
        """Test visibility score calculation."""
        metrics = AggregatedMetrics(
            mention_count=30,
            total_responses=100,
        )
        assert metrics.visibility_score == 30.0

    def test_visibility_score_zero_responses(self):
        """Test visibility score with zero responses."""
        metrics = AggregatedMetrics(
            mention_count=0,
            total_responses=0,
        )
        assert metrics.visibility_score == 0.0

    def test_trust_score(self):
        """Test trust score calculation."""
        metrics = AggregatedMetrics(
            mention_count=100,
            trusted_count=20,
            recommendation_count=30,
        )
        assert metrics.trust_score == 50.0

    def test_recommendation_rate(self):
        """Test recommendation rate calculation."""
        metrics = AggregatedMetrics(
            mention_count=50,
            recommendation_count=15,
        )
        assert metrics.recommendation_rate == 30.0


class TestAnalysisEngineShareOfVoice:
    """Tests for share of voice calculations."""

    @pytest.fixture
    def engine(self):
        """Create analysis engine."""
        return AnalysisEngine()

    @pytest.fixture
    def sample_brand_data(self):
        """Create sample brand presence data."""
        return [
            BrandPresenceData(
                brand_id=uuid.uuid4(),
                brand_name="Brand A",
                normalized_name="brand a",
                llm_provider="openai",
                presence="recommended",
                position_rank=1,
            ),
            BrandPresenceData(
                brand_id=uuid.uuid4(),
                brand_name="Brand A",
                normalized_name="brand a",
                llm_provider="anthropic",
                presence="mentioned",
                position_rank=2,
            ),
            BrandPresenceData(
                brand_id=uuid.uuid4(),
                brand_name="Brand B",
                normalized_name="brand b",
                llm_provider="openai",
                presence="compared",
                position_rank=3,
            ),
            BrandPresenceData(
                brand_id=uuid.uuid4(),
                brand_name="Brand B",
                normalized_name="brand b",
                llm_provider="anthropic",
                presence="ignored",
                position_rank=None,
            ),
        ]

    def test_calculate_share_of_voice_basic(self, engine, sample_brand_data):
        """Test basic share of voice calculation."""
        total_by_provider = {"openai": 50, "anthropic": 50}

        result = engine.calculate_share_of_voice(
            sample_brand_data,
            total_by_provider,
        )

        assert "brand a" in result
        assert "brand b" in result

        brand_a = result["brand a"]
        assert brand_a.mention_count == 2  # recommended + mentioned
        assert brand_a.recommendation_count == 1

    def test_calculate_sov_by_provider(self, engine, sample_brand_data):
        """Test SOV by provider breakdown."""
        total_by_provider = {"openai": 50, "anthropic": 50}

        result = engine.calculate_sov_by_provider(
            sample_brand_data,
            total_by_provider,
            target_brand="brand a",
        )

        assert len(result) == 2
        providers = {r.provider for r in result}
        assert "openai" in providers
        assert "anthropic" in providers

    def test_build_sov_response(self, engine):
        """Test building SOV response."""
        aggregated = AggregatedMetrics(
            mention_count=50,
            recommendation_count=15,
            first_position_count=8,
            total_responses=100,
            position_sum=100.0,
            position_count=50,
        )

        result = engine.build_sov_response(
            brand_name="Test Brand",
            brand_id=uuid.uuid4(),
            aggregated=aggregated,
            by_provider=[],
            competitors=[],
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
        )

        assert result.brand_name == "Test Brand"
        assert result.overall_metrics.mention_count == 50
        assert result.overall_metrics.recommendation_count == 15
        assert result.period_start == date(2024, 1, 1)


class TestAnalysisEngineSubstitution:
    """Tests for substitution pattern detection."""

    @pytest.fixture
    def engine(self):
        return AnalysisEngine()

    @pytest.fixture
    def substitution_data(self):
        """Create data for substitution testing."""
        response_1 = uuid.uuid4()
        response_2 = uuid.uuid4()
        response_3 = uuid.uuid4()

        return {
            "brand_data": [
                # Response 1: Brand A present, Brand B absent
                BrandPresenceData(
                    brand_id=uuid.uuid4(),
                    brand_name="Brand A",
                    normalized_name="brand a",
                    llm_provider="openai",
                    presence="recommended",
                    position_rank=1,
                    response_id=response_1,
                ),
                # Response 2: Brand B present, Brand A absent
                BrandPresenceData(
                    brand_id=uuid.uuid4(),
                    brand_name="Brand B",
                    normalized_name="brand b",
                    llm_provider="openai",
                    presence="mentioned",
                    position_rank=1,
                    response_id=response_2,
                ),
                # Response 3: Both present
                BrandPresenceData(
                    brand_id=uuid.uuid4(),
                    brand_name="Brand A",
                    normalized_name="brand a",
                    llm_provider="anthropic",
                    presence="mentioned",
                    position_rank=1,
                    response_id=response_3,
                ),
                BrandPresenceData(
                    brand_id=uuid.uuid4(),
                    brand_name="Brand B",
                    normalized_name="brand b",
                    llm_provider="anthropic",
                    presence="mentioned",
                    position_rank=2,
                    response_id=response_3,
                ),
            ],
            "response_brands": {
                response_1: ["Brand A"],
                response_2: ["Brand B"],
                response_3: ["Brand A", "Brand B"],
            },
        }

    def test_detect_substitution_patterns(self, engine, substitution_data):
        """Test substitution pattern detection."""
        result = engine.detect_substitution_patterns(
            substitution_data["brand_data"],
            substitution_data["response_brands"],
        )

        # Brand A should have Brand B as substitute when absent
        assert "brand a" in result
        assert "brand b" in result

    def test_detect_substitution_for_target(self, engine, substitution_data):
        """Test substitution detection for specific brand."""
        result = engine.detect_substitution_patterns(
            substitution_data["brand_data"],
            substitution_data["response_brands"],
            target_brand="brand a",
        )

        assert "brand a" in result
        assert len(result) == 1

    def test_build_substitution_response(self, engine):
        """Test building substitution response."""
        substitutes = [
            SubstituteInfo(
                brand_name="Competitor",
                normalized_name="competitor",
                occurrence_count=5,
                avg_position=1.5,
                providers=["openai"],
                substitution_rate=50.0,
            ),
        ]

        result = engine.build_substitution_response(
            missing_brand="Target",
            missing_brand_id=uuid.uuid4(),
            substitutes=substitutes,
            total_absence_count=10,
        )

        assert result.missing_brand_name == "Target"
        assert result.total_absence_count == 10
        assert result.top_substitute.brand_name == "Competitor"


class TestAnalysisEngineGaps:
    """Tests for competitive gap identification."""

    @pytest.fixture
    def engine(self):
        return AnalysisEngine()

    def test_identify_visibility_gap(self, engine):
        """Test visibility gap identification."""
        tracked = AggregatedMetrics(
            mention_count=30,
            total_responses=100,
        )
        competitor = AggregatedMetrics(
            mention_count=60,
            total_responses=100,
        )

        gaps = engine.identify_competitive_gaps(
            tracked,
            {"competitor": competitor},
            [],
        )

        visibility_gaps = [g for g in gaps if g.gap_type == OpportunityType.VISIBILITY_GAP]
        assert len(visibility_gaps) >= 1

    def test_identify_recommendation_gap(self, engine):
        """Test recommendation rate gap identification."""
        tracked = AggregatedMetrics(
            mention_count=50,
            recommendation_count=5,
        )
        competitor = AggregatedMetrics(
            mention_count=50,
            recommendation_count=20,
        )

        gaps = engine.identify_competitive_gaps(
            tracked,
            {"competitor": competitor},
            [],
        )

        rec_gaps = [g for g in gaps if g.gap_type == OpportunityType.RECOMMENDATION_GAP]
        assert len(rec_gaps) >= 1


class TestAnalysisEngineOpportunities:
    """Tests for opportunity scoring."""

    @pytest.fixture
    def engine(self):
        return AnalysisEngine()

    def test_score_opportunities_from_gaps(self, engine):
        """Test opportunity scoring from gaps."""
        from services.competitive_intel.schemas import CompetitiveGap

        gaps = [
            CompetitiveGap(
                gap_type=OpportunityType.VISIBILITY_GAP,
                description="Test visibility gap",
                severity=0.8,
                competitor_name="Competitor A",
                current_value=30.0,
                target_value=60.0,
                improvement_potential=30.0,
            ),
        ]

        opportunities = engine.score_opportunities(gaps, [])

        assert len(opportunities) >= 1
        assert opportunities[0].opportunity_type == OpportunityType.VISIBILITY_GAP

    def test_calculate_overall_score(self, engine):
        """Test overall opportunity score calculation."""
        from services.competitive_intel.schemas import Opportunity

        opportunities = [
            Opportunity(
                opportunity_type=OpportunityType.VISIBILITY_GAP,
                description="Test",
                score=25.0,
                priority=1,
            ),
            Opportunity(
                opportunity_type=OpportunityType.RECOMMENDATION_GAP,
                description="Test 2",
                score=30.0,
                priority=2,
            ),
        ]

        score = engine.calculate_overall_opportunity_score(opportunities)
        assert score == 55.0

    def test_empty_opportunities_score(self, engine):
        """Test score with no opportunities."""
        score = engine.calculate_overall_opportunity_score([])
        assert score == 0.0


class TestAnalysisEngineFullAnalysis:
    """Tests for full analysis pipeline."""

    @pytest.fixture
    def engine(self):
        return AnalysisEngine()

    def test_run_full_analysis(self, engine):
        """Test complete analysis pipeline."""
        website_id = uuid.uuid4()
        tracked_brand = "Test Brand"

        brand_data = [
            BrandPresenceData(
                brand_id=uuid.uuid4(),
                brand_name=tracked_brand,
                normalized_name=tracked_brand.lower(),
                llm_provider="openai",
                presence="recommended",
                position_rank=1,
            ),
            BrandPresenceData(
                brand_id=uuid.uuid4(),
                brand_name="Competitor",
                normalized_name="competitor",
                llm_provider="openai",
                presence="mentioned",
                position_rank=2,
            ),
        ]

        result = engine.run_full_analysis(
            website_id=website_id,
            tracked_brand=tracked_brand,
            tracked_brand_id=None,
            brand_data=brand_data,
            total_responses_by_provider={"openai": 10},
            response_brands={},
        )

        assert result.website_id == website_id
        assert result.tracked_brand == tracked_brand
        assert result.share_of_voice is not None
        assert "total_brands_analyzed" in result.summary

    def test_full_analysis_empty_data(self, engine):
        """Test analysis with no data."""
        result = engine.run_full_analysis(
            website_id=uuid.uuid4(),
            tracked_brand="Empty Brand",
            tracked_brand_id=None,
            brand_data=[],
            total_responses_by_provider={},
            response_brands={},
        )

        assert result.tracked_brand == "Empty Brand"
        assert result.summary["total_brands_analyzed"] == 0
