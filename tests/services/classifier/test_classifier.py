"""
Tests for Prompt Classifier Engine.

Tests classification logic with mocked LLM responses.
"""

import json
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from decimal import Decimal

from services.classifier.classifier import (
    PromptClassifier,
    ClassificationError,
    _build_classification_summary,
)
from services.classifier.schemas import (
    IntentType,
    FunnelStage,
    QueryIntent,
    ClassificationResult,
    ClassifiedPromptResponse,
    LLMClassificationResponse,
    PromptClassificationInput,
)
from services.classifier.prompts import heuristic_classification
from shared.llm.base import LLMResponse


# ==================== Test Data ====================


def create_mock_classification_response() -> dict:
    """Create a mock LLM classification response."""
    return {
        "intent_type": "evaluation",
        "funnel_stage": "consideration",
        "buying_signal": 0.65,
        "trust_need": 0.70,
        "query_intent": "Commercial",
        "reasoning": "User is comparing options to make an informed decision.",
    }


def create_mock_llm_response(content: dict) -> LLMResponse:
    """Create a mock LLM response."""
    return LLMResponse(
        text=json.dumps(content),
        model="gpt-4o",
        provider="openai",
        tokens_used=200,
        latency_ms=500,
        raw_response={},
    )


# ==================== Schema Tests ====================


class TestIntentType:
    """Tests for IntentType enum."""

    def test_intent_type_values(self):
        """Test IntentType enum values."""
        assert IntentType.INFORMATIONAL.value == "informational"
        assert IntentType.EVALUATION.value == "evaluation"
        assert IntentType.DECISION.value == "decision"


class TestFunnelStage:
    """Tests for FunnelStage enum."""

    def test_funnel_stage_values(self):
        """Test FunnelStage enum values."""
        assert FunnelStage.AWARENESS.value == "awareness"
        assert FunnelStage.CONSIDERATION.value == "consideration"
        assert FunnelStage.PURCHASE.value == "purchase"


class TestQueryIntent:
    """Tests for QueryIntent enum."""

    def test_query_intent_values(self):
        """Test QueryIntent enum values."""
        assert QueryIntent.COMMERCIAL.value == "Commercial"
        assert QueryIntent.INFORMATIONAL.value == "Informational"
        assert QueryIntent.NAVIGATIONAL.value == "Navigational"
        assert QueryIntent.TRANSACTIONAL.value == "Transactional"


class TestClassificationResult:
    """Tests for ClassificationResult schema."""

    def test_valid_classification(self):
        """Test creating a valid classification result."""
        result = ClassificationResult(
            intent_type=IntentType.EVALUATION,
            funnel_stage=FunnelStage.CONSIDERATION,
            buying_signal=0.65,
            trust_need=0.70,
            query_intent=QueryIntent.COMMERCIAL,
            confidence_score=0.85,
            reasoning="User is comparing options.",
        )
        assert result.intent_type == IntentType.EVALUATION
        assert result.buying_signal == 0.65
        assert result.trust_need == 0.70

    def test_buying_signal_bounds(self):
        """Test buying signal must be between 0 and 1."""
        with pytest.raises(ValueError):
            ClassificationResult(
                intent_type=IntentType.INFORMATIONAL,
                funnel_stage=FunnelStage.AWARENESS,
                buying_signal=1.5,  # Invalid
                trust_need=0.5,
            )

        with pytest.raises(ValueError):
            ClassificationResult(
                intent_type=IntentType.INFORMATIONAL,
                funnel_stage=FunnelStage.AWARENESS,
                buying_signal=-0.1,  # Invalid
                trust_need=0.5,
            )

    def test_trust_need_bounds(self):
        """Test trust need must be between 0 and 1."""
        with pytest.raises(ValueError):
            ClassificationResult(
                intent_type=IntentType.INFORMATIONAL,
                funnel_stage=FunnelStage.AWARENESS,
                buying_signal=0.5,
                trust_need=1.1,  # Invalid
            )


class TestLLMClassificationResponse:
    """Tests for LLMClassificationResponse schema."""

    def test_valid_response_parsing(self):
        """Test parsing a valid LLM response."""
        data = create_mock_classification_response()
        parsed = LLMClassificationResponse.model_validate(data)

        assert parsed.intent_type == "evaluation"
        assert parsed.funnel_stage == "consideration"
        assert parsed.buying_signal == 0.65

    def test_intent_type_normalization(self):
        """Test intent type is normalized to lowercase."""
        data = {
            "intent_type": "EVALUATION",
            "funnel_stage": "consideration",
            "buying_signal": 0.5,
            "trust_need": 0.5,
        }
        parsed = LLMClassificationResponse.model_validate(data)
        assert parsed.intent_type == "evaluation"

    def test_funnel_stage_normalization(self):
        """Test funnel stage is normalized to lowercase."""
        data = {
            "intent_type": "evaluation",
            "funnel_stage": "CONSIDERATION",
            "buying_signal": 0.5,
            "trust_need": 0.5,
        }
        parsed = LLMClassificationResponse.model_validate(data)
        assert parsed.funnel_stage == "consideration"

    def test_invalid_intent_type_raises(self):
        """Test invalid intent type raises validation error."""
        data = {
            "intent_type": "invalid_intent",
            "funnel_stage": "consideration",
            "buying_signal": 0.5,
            "trust_need": 0.5,
        }
        with pytest.raises(ValueError, match="Invalid intent_type"):
            LLMClassificationResponse.model_validate(data)

    def test_invalid_funnel_stage_raises(self):
        """Test invalid funnel stage raises validation error."""
        data = {
            "intent_type": "evaluation",
            "funnel_stage": "invalid_stage",
            "buying_signal": 0.5,
            "trust_need": 0.5,
        }
        with pytest.raises(ValueError, match="Invalid funnel_stage"):
            LLMClassificationResponse.model_validate(data)

    def test_to_classification_result(self):
        """Test converting to ClassificationResult."""
        data = create_mock_classification_response()
        parsed = LLMClassificationResponse.model_validate(data)
        result = parsed.to_classification_result()

        assert isinstance(result, ClassificationResult)
        assert result.intent_type == IntentType.EVALUATION
        assert result.funnel_stage == FunnelStage.CONSIDERATION
        assert result.query_intent == QueryIntent.COMMERCIAL


# ==================== Heuristic Classification Tests ====================


class TestHeuristicClassification:
    """Tests for heuristic-based classification."""

    def test_informational_keywords(self):
        """Test informational intent detection."""
        prompts = [
            "What is machine learning?",
            "How does cloud computing work?",
            "Explain the difference between SQL and NoSQL",
        ]
        for prompt in prompts:
            result = heuristic_classification(prompt)
            assert result["intent_type"] == "informational", f"Failed for: {prompt}"

    def test_evaluation_keywords(self):
        """Test evaluation intent detection."""
        prompts = [
            "Compare AWS vs Azure for enterprise workloads",
            "Which is better, React or Vue?",
            "Pros and cons of microservices architecture",
        ]
        for prompt in prompts:
            result = heuristic_classification(prompt)
            assert result["intent_type"] == "evaluation", f"Failed for: {prompt}"

    def test_decision_keywords(self):
        """Test decision intent detection."""
        prompts = [
            "How to buy enterprise licenses?",
            "What's the pricing for the pro plan?",
            "How do I get started with your platform?",
        ]
        for prompt in prompts:
            result = heuristic_classification(prompt)
            assert result["intent_type"] == "decision", f"Failed for: {prompt}"

    def test_awareness_funnel_stage(self):
        """Test awareness funnel stage detection."""
        prompts = [
            "What is project management software?",
            "Introduction to CRM systems",
            "Basics of cloud storage",
        ]
        for prompt in prompts:
            result = heuristic_classification(prompt)
            assert result["funnel_stage"] == "awareness", f"Failed for: {prompt}"

    def test_consideration_funnel_stage(self):
        """Test consideration funnel stage detection."""
        prompts = [
            "Compare Asana vs Monday.com features",
            "Review of Salesforce vs HubSpot",
            "What are the best alternatives to Dropbox?",
        ]
        for prompt in prompts:
            result = heuristic_classification(prompt)
            assert result["funnel_stage"] == "consideration", f"Failed for: {prompt}"

    def test_purchase_funnel_stage(self):
        """Test purchase funnel stage detection."""
        prompts = [
            "What's the pricing for enterprise plan?",
            "How to purchase annual subscription?",
            "Can I get a trial before buying?",
        ]
        for prompt in prompts:
            result = heuristic_classification(prompt)
            assert result["funnel_stage"] == "purchase", f"Failed for: {prompt}"

    def test_buying_signal_ranges(self):
        """Test buying signal is calculated correctly."""
        # Low buying signal
        low_signal = heuristic_classification("What is machine learning?")
        assert low_signal["buying_signal"] < 0.4

        # Medium buying signal
        medium_signal = heuristic_classification("Compare AWS vs Azure for my company")
        assert 0.3 < medium_signal["buying_signal"] < 0.8

        # High buying signal
        high_signal = heuristic_classification("What's the pricing for the enterprise plan?")
        assert high_signal["buying_signal"] > 0.7

    def test_trust_need_adjustment(self):
        """Test trust need is adjusted based on complexity."""
        # Simple prompt
        simple = heuristic_classification("What is CRM?")

        # Complex prompt with enterprise context
        complex_prompt = heuristic_classification(
            "What security certifications does your enterprise solution have for our company's compliance requirements?"
        )

        assert complex_prompt["trust_need"] > simple["trust_need"]


# ==================== Classifier Tests ====================


class TestPromptClassifier:
    """Tests for PromptClassifier class."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = MagicMock()
        client.complete_json = AsyncMock()
        return client

    @pytest.fixture
    def classifier(self, mock_llm_client):
        """Create a PromptClassifier with mocked LLM client."""
        return PromptClassifier(llm_client=mock_llm_client)

    @pytest.mark.asyncio
    async def test_classify_with_llm_success(self, classifier, mock_llm_client):
        """Test successful LLM classification."""
        mock_response = create_mock_llm_response(create_mock_classification_response())
        mock_llm_client.complete_json.return_value = mock_response

        input_data = PromptClassificationInput(
            prompt_id=uuid.uuid4(),
            prompt_text="Compare AWS vs Azure for enterprise deployment",
            conversation_topic="Cloud platform evaluation",
            icp_name="IT Director",
        )

        result = await classifier._classify_with_llm(input_data)

        assert isinstance(result, ClassificationResult)
        assert result.intent_type == IntentType.EVALUATION
        assert result.funnel_stage == FunnelStage.CONSIDERATION
        mock_llm_client.complete_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_classify_with_llm_retry_on_validation_error(
        self, classifier, mock_llm_client
    ):
        """Test retry on validation error."""
        # First response is invalid, second is valid
        invalid_response = create_mock_llm_response({"invalid": "data"})
        valid_response = create_mock_llm_response(create_mock_classification_response())

        mock_llm_client.complete_json.side_effect = [invalid_response, valid_response]

        input_data = PromptClassificationInput(
            prompt_id=uuid.uuid4(),
            prompt_text="Compare options",
        )

        result = await classifier._classify_with_llm(input_data)

        assert result.intent_type == IntentType.EVALUATION
        assert mock_llm_client.complete_json.call_count == 2

    @pytest.mark.asyncio
    async def test_classify_with_llm_fallback_to_heuristics(
        self, classifier, mock_llm_client
    ):
        """Test fallback to heuristics when LLM fails."""
        # All LLM calls fail
        mock_llm_client.complete_json.side_effect = Exception("LLM error")

        input_data = PromptClassificationInput(
            prompt_id=uuid.uuid4(),
            prompt_text="What is machine learning?",
        )

        result = await classifier._classify_with_llm(input_data)

        # Should get heuristic result
        assert result.confidence_score == 0.5  # Heuristic confidence
        assert result.intent_type == IntentType.INFORMATIONAL

    @pytest.mark.asyncio
    async def test_classify_with_llm_no_fallback_raises(self, mock_llm_client):
        """Test error raised when fallback disabled and LLM fails."""
        classifier = PromptClassifier(
            llm_client=mock_llm_client,
            use_heuristics_fallback=False,
        )
        mock_llm_client.complete_json.side_effect = Exception("LLM error")

        input_data = PromptClassificationInput(
            prompt_id=uuid.uuid4(),
            prompt_text="Test prompt text for classification",
        )

        with pytest.raises(ClassificationError):
            await classifier._classify_with_llm(input_data)

    def test_classify_batch_with_heuristics(self, classifier):
        """Test batch classification with heuristics."""
        batch_inputs = [
            {"prompt_text": "What is cloud computing?"},
            {"prompt_text": "Compare AWS vs Azure"},
            {"prompt_text": "How much does it cost?"},
        ]

        results = classifier._classify_batch_with_heuristics(batch_inputs)

        assert len(results) == 3
        assert all(isinstance(r, ClassificationResult) for r in results)
        assert results[0].intent_type == IntentType.INFORMATIONAL
        assert results[1].intent_type == IntentType.EVALUATION
        assert results[2].intent_type == IntentType.DECISION


# ==================== Summary Tests ====================


class TestClassificationSummary:
    """Tests for classification summary building."""

    def test_build_summary_empty(self):
        """Test summary with empty classifications."""
        summary = _build_classification_summary([])

        assert summary.total == 0
        assert summary.avg_buying_signal == 0.0
        assert summary.avg_trust_need == 0.0

    def test_build_summary_with_data(self):
        """Test summary with classification data."""
        classifications = [
            ClassifiedPromptResponse(
                prompt_id=uuid.uuid4(),
                prompt_text="Test 1",
                conversation_id=uuid.uuid4(),
                icp_id=uuid.uuid4(),
                classification=ClassificationResult(
                    intent_type=IntentType.INFORMATIONAL,
                    funnel_stage=FunnelStage.AWARENESS,
                    buying_signal=0.2,
                    trust_need=0.3,
                ),
            ),
            ClassifiedPromptResponse(
                prompt_id=uuid.uuid4(),
                prompt_text="Test 2",
                conversation_id=uuid.uuid4(),
                icp_id=uuid.uuid4(),
                classification=ClassificationResult(
                    intent_type=IntentType.EVALUATION,
                    funnel_stage=FunnelStage.CONSIDERATION,
                    buying_signal=0.6,
                    trust_need=0.7,
                ),
            ),
            ClassifiedPromptResponse(
                prompt_id=uuid.uuid4(),
                prompt_text="Test 3",
                conversation_id=uuid.uuid4(),
                icp_id=uuid.uuid4(),
                classification=ClassificationResult(
                    intent_type=IntentType.EVALUATION,
                    funnel_stage=FunnelStage.CONSIDERATION,
                    buying_signal=0.7,
                    trust_need=0.8,
                ),
            ),
        ]

        summary = _build_classification_summary(classifications)

        assert summary.total == 3
        assert summary.by_intent_type[IntentType.INFORMATIONAL] == 1
        assert summary.by_intent_type[IntentType.EVALUATION] == 2
        assert summary.by_funnel_stage[FunnelStage.AWARENESS] == 1
        assert summary.by_funnel_stage[FunnelStage.CONSIDERATION] == 2
        assert summary.avg_buying_signal == pytest.approx(0.5, rel=0.01)
        assert summary.avg_trust_need == pytest.approx(0.6, rel=0.01)
