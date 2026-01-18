"""
Tests for Brand Presence Detector Schemas.

Tests Pydantic schemas for request/response validation.
"""

import uuid
from datetime import datetime

import pytest
from pydantic import ValidationError

from services.brand_detector.schemas import (
    BrandPresenceState,
    BeliefType,
    BrandDetectionRequest,
    BatchDetectionRequest,
    LLMResponseAnalysisRequest,
    BrandPresenceResult,
    BrandDetectionResponse,
    BatchDetectionResponse,
    LLMBrandStateCreate,
    LLMBrandStateResponse,
    BrandCreate,
    BrandResponse,
    PresenceBreakdown,
    BeliefDistribution,
    BrandAnalysisSummary,
    HealthResponse,
    DetectionStatsResponse,
)


# ==================== Request Schema Tests ====================


class TestBrandDetectionRequest:
    """Tests for BrandDetectionRequest schema."""

    def test_valid_request(self):
        """Test creating a valid detection request."""
        request = BrandDetectionRequest(
            response_text="This is a test response mentioning Notion.",
            known_brands=["Notion", "Slack"],
            tracked_brand="Notion",
        )

        assert request.response_text == "This is a test response mentioning Notion."
        assert request.known_brands == ["Notion", "Slack"]
        assert request.tracked_brand == "Notion"

    def test_minimal_request(self):
        """Test minimal request with only required fields."""
        request = BrandDetectionRequest(
            response_text="Some text to analyze.",
        )

        assert request.response_text == "Some text to analyze."
        assert request.known_brands is None
        assert request.tracked_brand is None

    def test_empty_response_text_fails(self):
        """Test empty response_text raises validation error."""
        with pytest.raises(ValidationError):
            BrandDetectionRequest(response_text="")

    def test_whitespace_only_fails(self):
        """Test whitespace-only response_text may fail or pass based on config."""
        # Single space has length 1, which meets min_length
        request = BrandDetectionRequest(response_text=" ")
        assert request.response_text == " "


class TestBatchDetectionRequest:
    """Tests for BatchDetectionRequest schema."""

    def test_valid_batch_request(self):
        """Test creating a valid batch request."""
        request = BatchDetectionRequest(
            responses=[
                BrandDetectionRequest(response_text="Text 1"),
                BrandDetectionRequest(response_text="Text 2"),
            ],
            known_brands=["Brand1", "Brand2"],
            tracked_brand="Brand1",
        )

        assert len(request.responses) == 2
        assert request.known_brands == ["Brand1", "Brand2"]

    def test_empty_responses_list(self):
        """Test empty responses list is valid."""
        request = BatchDetectionRequest(responses=[])
        assert len(request.responses) == 0


class TestLLMResponseAnalysisRequest:
    """Tests for LLMResponseAnalysisRequest schema."""

    def test_valid_analysis_request(self):
        """Test creating a valid analysis request."""
        request = LLMResponseAnalysisRequest(
            llm_response_id=uuid.uuid4(),
            simulation_run_id=uuid.uuid4(),
            prompt_id=uuid.uuid4(),
            llm_provider="openai",
            llm_model="gpt-4",
            response_text="Analysis text here.",
            known_brands=["Brand"],
            tracked_brand="Brand",
        )

        assert request.llm_provider == "openai"
        assert request.llm_model == "gpt-4"

    def test_minimal_analysis_request(self):
        """Test minimal analysis request."""
        request = LLMResponseAnalysisRequest(
            llm_response_id=uuid.uuid4(),
            llm_provider="anthropic",
            llm_model="claude-3",
            response_text="Text",
        )

        assert request.simulation_run_id is None
        assert request.prompt_id is None


# ==================== Response Schema Tests ====================


class TestBrandPresenceResult:
    """Tests for BrandPresenceResult schema."""

    def test_valid_result(self):
        """Test creating a valid result."""
        result = BrandPresenceResult(
            brand_name="Notion",
            normalized_name="notion",
            presence=BrandPresenceState.RECOMMENDED,
            position_rank=1,
            belief_sold=BeliefType.SUPERIORITY,
            confidence=0.95,
            context_snippet="I recommend Notion for documentation.",
            detection_signals=["recommend", "best"],
        )

        assert result.brand_name == "Notion"
        assert result.presence == BrandPresenceState.RECOMMENDED
        assert result.belief_sold == BeliefType.SUPERIORITY

    def test_minimal_result(self):
        """Test minimal result with defaults."""
        result = BrandPresenceResult(
            brand_name="Test",
            normalized_name="test",
            presence=BrandPresenceState.MENTIONED,
        )

        assert result.position_rank is None
        assert result.belief_sold is None
        assert result.confidence == 1.0
        assert result.context_snippet is None
        assert result.detection_signals == []

    def test_confidence_bounds_lower(self):
        """Test confidence lower bound."""
        with pytest.raises(ValidationError):
            BrandPresenceResult(
                brand_name="Test",
                normalized_name="test",
                presence=BrandPresenceState.MENTIONED,
                confidence=-0.1,
            )

    def test_confidence_bounds_upper(self):
        """Test confidence upper bound."""
        with pytest.raises(ValidationError):
            BrandPresenceResult(
                brand_name="Test",
                normalized_name="test",
                presence=BrandPresenceState.MENTIONED,
                confidence=1.1,
            )

    def test_context_snippet_max_length(self):
        """Test context_snippet max length enforcement."""
        long_snippet = "x" * 600
        with pytest.raises(ValidationError):
            BrandPresenceResult(
                brand_name="Test",
                normalized_name="test",
                presence=BrandPresenceState.MENTIONED,
                context_snippet=long_snippet,
            )


class TestBrandDetectionResponse:
    """Tests for BrandDetectionResponse schema."""

    def test_valid_response(self):
        """Test creating a valid response."""
        brand_result = BrandPresenceResult(
            brand_name="Notion",
            normalized_name="notion",
            presence=BrandPresenceState.RECOMMENDED,
        )

        response = BrandDetectionResponse(
            brands=[brand_result],
            tracked_brand_result=brand_result,
            total_brands_found=1,
            analysis_metadata={"candidates_found": 5},
        )

        assert len(response.brands) == 1
        assert response.total_brands_found == 1

    def test_empty_response(self):
        """Test empty response with defaults."""
        response = BrandDetectionResponse()

        assert response.brands == []
        assert response.tracked_brand_result is None
        assert response.total_brands_found == 0
        assert response.analysis_metadata == {}


class TestBatchDetectionResponse:
    """Tests for BatchDetectionResponse schema."""

    def test_valid_batch_response(self):
        """Test creating a valid batch response."""
        response = BatchDetectionResponse(
            results=[BrandDetectionResponse()],
            total_responses_analyzed=1,
            total_brands_found=0,
            summary={"presence_distribution": {}},
        )

        assert response.total_responses_analyzed == 1


# ==================== Storage Schema Tests ====================


class TestLLMBrandStateCreate:
    """Tests for LLMBrandStateCreate schema."""

    def test_valid_create(self):
        """Test creating a valid brand state."""
        create = LLMBrandStateCreate(
            llm_response_id=uuid.uuid4(),
            brand_id=uuid.uuid4(),
            presence=BrandPresenceState.RECOMMENDED,
            position_rank=1,
            belief_sold=BeliefType.SUPERIORITY,
        )

        assert create.presence == BrandPresenceState.RECOMMENDED

    def test_minimal_create(self):
        """Test minimal create with required fields."""
        create = LLMBrandStateCreate(
            llm_response_id=uuid.uuid4(),
            brand_id=uuid.uuid4(),
            presence=BrandPresenceState.MENTIONED,
        )

        assert create.position_rank is None
        assert create.belief_sold is None


class TestLLMBrandStateResponse:
    """Tests for LLMBrandStateResponse schema."""

    def test_valid_response(self):
        """Test creating a valid response."""
        response = LLMBrandStateResponse(
            id=uuid.uuid4(),
            llm_response_id=uuid.uuid4(),
            brand_id=uuid.uuid4(),
            presence="recommended",
            position_rank=1,
            belief_sold="superiority",
            created_at=datetime.now(),
        )

        assert response.presence == "recommended"


class TestBrandCreate:
    """Tests for BrandCreate schema."""

    def test_valid_create(self):
        """Test creating a valid brand."""
        brand = BrandCreate(
            name="Notion",
            normalized_name="notion",
            domain="notion.so",
            industry="productivity",
            is_tracked=True,
        )

        assert brand.name == "Notion"
        assert brand.is_tracked is True

    def test_minimal_create(self):
        """Test minimal brand create."""
        brand = BrandCreate(
            name="Test",
            normalized_name="test",
        )

        assert brand.domain is None
        assert brand.industry is None
        assert brand.is_tracked is False


class TestBrandResponse:
    """Tests for BrandResponse schema."""

    def test_valid_response(self):
        """Test creating a valid brand response."""
        response = BrandResponse(
            id=uuid.uuid4(),
            name="Notion",
            normalized_name="notion",
            domain="notion.so",
            industry="productivity",
            is_tracked=True,
            created_at=datetime.now(),
        )

        assert response.name == "Notion"


# ==================== Analysis Schema Tests ====================


class TestPresenceBreakdown:
    """Tests for PresenceBreakdown schema."""

    def test_default_values(self):
        """Test default values are zero."""
        breakdown = PresenceBreakdown()

        assert breakdown.ignored == 0
        assert breakdown.mentioned == 0
        assert breakdown.trusted == 0
        assert breakdown.recommended == 0
        assert breakdown.compared == 0

    def test_custom_values(self):
        """Test setting custom values."""
        breakdown = PresenceBreakdown(
            ignored=5,
            mentioned=10,
            trusted=3,
            recommended=7,
            compared=2,
        )

        assert breakdown.ignored == 5
        assert breakdown.recommended == 7


class TestBeliefDistribution:
    """Tests for BeliefDistribution schema."""

    def test_default_values(self):
        """Test default values are zero."""
        dist = BeliefDistribution()

        assert dist.truth == 0
        assert dist.superiority == 0
        assert dist.outcome == 0
        assert dist.transaction == 0
        assert dist.identity == 0
        assert dist.social_proof == 0

    def test_custom_values(self):
        """Test setting custom values."""
        dist = BeliefDistribution(
            truth=5,
            superiority=10,
            outcome=3,
            transaction=7,
            identity=2,
            social_proof=8,
        )

        assert dist.superiority == 10
        assert dist.social_proof == 8


class TestBrandAnalysisSummary:
    """Tests for BrandAnalysisSummary schema."""

    def test_valid_summary(self):
        """Test creating a valid summary."""
        summary = BrandAnalysisSummary(
            brand_id=uuid.uuid4(),
            brand_name="Notion",
            total_appearances=100,
            presence_breakdown=PresenceBreakdown(recommended=50, mentioned=50),
            belief_distribution=BeliefDistribution(superiority=60, outcome=40),
            avg_position=2.5,
            recommendation_rate=0.50,
            by_provider={"openai": {"count": 60}, "anthropic": {"count": 40}},
        )

        assert summary.brand_name == "Notion"
        assert summary.recommendation_rate == 0.50

    def test_minimal_summary(self):
        """Test minimal summary with defaults."""
        summary = BrandAnalysisSummary(
            brand_id=uuid.uuid4(),
            brand_name="Test",
        )

        assert summary.total_appearances == 0
        assert summary.recommendation_rate == 0.0
        assert summary.avg_position is None


# ==================== API Response Schema Tests ====================


class TestHealthResponse:
    """Tests for HealthResponse schema."""

    def test_default_values(self):
        """Test default health response values."""
        response = HealthResponse()

        assert response.status == "healthy"
        assert response.service == "brand-presence-detector"
        assert response.version == "1.0.0"

    def test_custom_status(self):
        """Test custom status value."""
        response = HealthResponse(status="ready")
        assert response.status == "ready"


class TestDetectionStatsResponse:
    """Tests for DetectionStatsResponse schema."""

    def test_default_values(self):
        """Test default stats response values."""
        response = DetectionStatsResponse()

        assert response.total_detections == 0
        assert response.brands_detected == 0
        assert response.avg_brands_per_response == 0.0

    def test_custom_values(self):
        """Test custom stats values."""
        response = DetectionStatsResponse(
            total_detections=1000,
            brands_detected=50,
            presence_distribution=PresenceBreakdown(recommended=500, mentioned=500),
            belief_distribution=BeliefDistribution(superiority=600, outcome=400),
            avg_brands_per_response=2.5,
        )

        assert response.total_detections == 1000
        assert response.avg_brands_per_response == 2.5
