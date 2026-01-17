"""
Tests for Prompt Classifier schemas.

Tests Pydantic models and validation logic for classification schemas.
"""

import uuid
import pytest
from datetime import datetime

from services.classifier.schemas import (
    IntentType,
    FunnelStage,
    QueryIntent,
    UserIntent,
    ClassificationResult,
    PromptClassificationInput,
    PromptClassificationOutput,
    BatchClassificationInput,
    ClassifyPromptsRequest,
    ClassificationFilter,
    ClassificationSummary,
    LLMClassificationResponse,
)


class TestUserIntent:
    """Tests for UserIntent schema."""

    def test_valid_user_intent(self):
        """Test creating a valid UserIntent."""
        intent = UserIntent(
            intent_type=IntentType.EVALUATION,
            funnel_stage=FunnelStage.CONSIDERATION,
            buying_signal=0.65,
            trust_need=0.70,
        )
        assert intent.intent_type == IntentType.EVALUATION
        assert intent.buying_signal == 0.65

    def test_user_intent_string_enum_coercion(self):
        """Test that string values are coerced to enum."""
        intent = UserIntent(
            intent_type="evaluation",
            funnel_stage="consideration",
            buying_signal=0.5,
            trust_need=0.5,
        )
        # Values are stored as enum values due to use_enum_values config
        assert intent.intent_type == "evaluation"

    def test_buying_signal_validation(self):
        """Test buying signal must be 0.0-1.0."""
        with pytest.raises(ValueError):
            UserIntent(
                intent_type=IntentType.INFORMATIONAL,
                funnel_stage=FunnelStage.AWARENESS,
                buying_signal=1.5,
                trust_need=0.5,
            )

    def test_trust_need_validation(self):
        """Test trust need must be 0.0-1.0."""
        with pytest.raises(ValueError):
            UserIntent(
                intent_type=IntentType.INFORMATIONAL,
                funnel_stage=FunnelStage.AWARENESS,
                buying_signal=0.5,
                trust_need=-0.1,
            )


class TestClassificationResult:
    """Tests for ClassificationResult schema."""

    def test_extends_user_intent(self):
        """Test ClassificationResult extends UserIntent."""
        result = ClassificationResult(
            intent_type=IntentType.DECISION,
            funnel_stage=FunnelStage.PURCHASE,
            buying_signal=0.90,
            trust_need=0.85,
            query_intent=QueryIntent.COMMERCIAL,
            confidence_score=0.95,
            reasoning="User is ready to purchase.",
        )
        assert result.query_intent == QueryIntent.COMMERCIAL
        assert result.confidence_score == 0.95

    def test_optional_fields(self):
        """Test optional fields default correctly."""
        result = ClassificationResult(
            intent_type=IntentType.INFORMATIONAL,
            funnel_stage=FunnelStage.AWARENESS,
            buying_signal=0.20,
            trust_need=0.30,
        )
        assert result.query_intent is None
        assert result.confidence_score == 0.0
        assert result.reasoning is None


class TestPromptClassificationInput:
    """Tests for PromptClassificationInput schema."""

    def test_valid_input(self):
        """Test creating a valid input."""
        input_data = PromptClassificationInput(
            prompt_id=uuid.uuid4(),
            prompt_text="What are the best project management tools?",
            conversation_topic="Tool evaluation",
            icp_name="Product Manager",
        )
        assert len(input_data.prompt_text) > 0

    def test_prompt_text_min_length(self):
        """Test prompt text minimum length validation."""
        with pytest.raises(ValueError):
            PromptClassificationInput(
                prompt_id=uuid.uuid4(),
                prompt_text="Hi",  # Too short
            )


class TestBatchClassificationInput:
    """Tests for BatchClassificationInput schema."""

    def test_valid_batch(self):
        """Test creating a valid batch input."""
        batch = BatchClassificationInput(
            prompts=[
                PromptClassificationInput(
                    prompt_id=uuid.uuid4(),
                    prompt_text="First prompt to classify",
                ),
                PromptClassificationInput(
                    prompt_id=uuid.uuid4(),
                    prompt_text="Second prompt to classify",
                ),
            ]
        )
        assert len(batch.prompts) == 2

    def test_batch_min_length(self):
        """Test batch must have at least 1 prompt."""
        with pytest.raises(ValueError):
            BatchClassificationInput(prompts=[])

    def test_batch_max_length(self):
        """Test batch max is 100 prompts."""
        prompts = [
            PromptClassificationInput(
                prompt_id=uuid.uuid4(),
                prompt_text=f"Prompt number {i} for testing batch limits",
            )
            for i in range(101)
        ]
        with pytest.raises(ValueError):
            BatchClassificationInput(prompts=prompts)


class TestClassifyPromptsRequest:
    """Tests for ClassifyPromptsRequest schema."""

    def test_default_values(self):
        """Test default values are set correctly."""
        request = ClassifyPromptsRequest()
        assert request.force_reclassify is False
        assert request.llm_provider is None
        assert request.icp_ids is None

    def test_with_filters(self):
        """Test request with filters."""
        icp_id = uuid.uuid4()
        request = ClassifyPromptsRequest(
            force_reclassify=True,
            llm_provider="anthropic",
            icp_ids=[icp_id],
        )
        assert request.force_reclassify is True
        assert request.llm_provider == "anthropic"
        assert icp_id in request.icp_ids


class TestClassificationFilter:
    """Tests for ClassificationFilter schema."""

    def test_all_filters(self):
        """Test filter with all options."""
        filter_obj = ClassificationFilter(
            intent_type=IntentType.EVALUATION,
            funnel_stage=FunnelStage.CONSIDERATION,
            min_buying_signal=0.5,
            max_buying_signal=0.9,
            min_trust_need=0.4,
            max_trust_need=0.8,
            icp_id=uuid.uuid4(),
        )
        assert filter_obj.intent_type == IntentType.EVALUATION
        assert filter_obj.min_buying_signal == 0.5

    def test_signal_bounds_validation(self):
        """Test signal bounds are validated."""
        with pytest.raises(ValueError):
            ClassificationFilter(min_buying_signal=1.5)

        with pytest.raises(ValueError):
            ClassificationFilter(max_trust_need=-0.1)


class TestClassificationSummary:
    """Tests for ClassificationSummary schema."""

    def test_summary_structure(self):
        """Test summary structure."""
        summary = ClassificationSummary(
            total=50,
            by_intent_type={
                "informational": 15,
                "evaluation": 25,
                "decision": 10,
            },
            by_funnel_stage={
                "awareness": 12,
                "consideration": 28,
                "purchase": 10,
            },
            by_query_intent={
                "Commercial": 30,
                "Informational": 15,
                "Transactional": 5,
            },
            avg_buying_signal=0.58,
            avg_trust_need=0.72,
        )
        assert summary.total == 50
        assert summary.by_intent_type["evaluation"] == 25


class TestLLMClassificationResponse:
    """Tests for LLMClassificationResponse schema."""

    def test_valid_response(self):
        """Test parsing a valid response."""
        response = LLMClassificationResponse(
            intent_type="evaluation",
            funnel_stage="consideration",
            buying_signal=0.65,
            trust_need=0.70,
            query_intent="Commercial",
            reasoning="User is evaluating options.",
        )
        assert response.intent_type == "evaluation"

    def test_intent_type_normalization_uppercase(self):
        """Test intent type is normalized from uppercase."""
        response = LLMClassificationResponse(
            intent_type="EVALUATION",
            funnel_stage="consideration",
            buying_signal=0.5,
            trust_need=0.5,
        )
        assert response.intent_type == "evaluation"

    def test_intent_type_normalization_with_whitespace(self):
        """Test intent type is trimmed."""
        response = LLMClassificationResponse(
            intent_type="  evaluation  ",
            funnel_stage="consideration",
            buying_signal=0.5,
            trust_need=0.5,
        )
        assert response.intent_type == "evaluation"

    def test_query_intent_normalization(self):
        """Test query intent normalization."""
        response = LLMClassificationResponse(
            intent_type="evaluation",
            funnel_stage="consideration",
            buying_signal=0.5,
            trust_need=0.5,
            query_intent="commercial",  # lowercase
        )
        assert response.query_intent == "Commercial"

    def test_query_intent_mapping(self):
        """Test query intent common variations are mapped."""
        response = LLMClassificationResponse(
            intent_type="evaluation",
            funnel_stage="consideration",
            buying_signal=0.5,
            trust_need=0.5,
            query_intent="info",
        )
        assert response.query_intent == "Informational"

    def test_to_classification_result_conversion(self):
        """Test conversion to ClassificationResult."""
        response = LLMClassificationResponse(
            intent_type="decision",
            funnel_stage="purchase",
            buying_signal=0.90,
            trust_need=0.85,
            query_intent="Transactional",
            reasoning="Ready to buy.",
        )
        result = response.to_classification_result()

        assert isinstance(result, ClassificationResult)
        assert result.intent_type == IntentType.DECISION
        assert result.funnel_stage == FunnelStage.PURCHASE
        assert result.query_intent == QueryIntent.TRANSACTIONAL
        assert result.confidence_score == 0.85  # Default for LLM
        assert result.reasoning == "Ready to buy."
