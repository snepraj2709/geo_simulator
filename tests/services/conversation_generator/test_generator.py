"""
Tests for Conversation Generator.

Tests the conversation generation logic with mocked LLM responses.
"""

import json
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from services.conversation_generator.generator import (
    ConversationGenerator,
    ConversationGenerationError,
)
from services.conversation_generator.schemas import (
    GeneratedConversation,
    GeneratedPrompt,
    ConversationGenerationResponse,
    PromptType,
)
from shared.llm.base import LLMResponse


# ==================== Test Data ====================


def create_mock_conversation_response() -> dict:
    """Create a mock LLM response with valid conversations."""
    conversations = []
    for i in range(10):
        prompts = [
            {
                "prompt_text": f"What are your pricing options for enterprise customers?",
                "prompt_type": "primary",
                "sequence_order": 0,
                "expected_response_type": "informational",
            },
            {
                "prompt_text": "Do you offer volume discounts?",
                "prompt_type": "follow_up",
                "sequence_order": 1,
                "expected_response_type": "informational",
            },
            {
                "prompt_text": "What's included in the enterprise plan?",
                "prompt_type": "follow_up",
                "sequence_order": 2,
                "expected_response_type": "comparison",
            },
            {
                "prompt_text": "Can we get a custom quote?",
                "prompt_type": "follow_up",
                "sequence_order": 3,
                "expected_response_type": "action",
            },
        ]

        conversations.append({
            "topic": f"Topic {i + 1}: {'Core' if i < 5 else 'Variable'} conversation about feature {i + 1}",
            "context": f"A {['small', 'medium', 'large'][i % 3]} company is looking for solutions to improve their {'workflow' if i % 2 == 0 else 'productivity'}. They have been researching options for several weeks.",
            "expected_outcome": f"Understanding of pricing and features for scenario {i + 1}",
            "is_core_conversation": i < 5,
            "sequence_number": i + 1,
            "prompts": prompts,
        })

    return {"conversations": conversations}


def create_mock_llm_response(content: dict) -> LLMResponse:
    """Create a mock LLM response."""
    return LLMResponse(
        text=json.dumps(content),
        model="gpt-4o",
        provider="openai",
        tokens_used=5000,
        latency_ms=2000,
        raw_response={},
    )


# ==================== Schema Tests ====================


class TestGeneratedPrompt:
    """Tests for GeneratedPrompt schema."""

    def test_valid_primary_prompt(self):
        """Test valid primary prompt."""
        prompt = GeneratedPrompt(
            prompt_text="What services do you offer?",
            prompt_type=PromptType.PRIMARY,
            sequence_order=0,
            expected_response_type="informational",
        )
        assert prompt.prompt_type == PromptType.PRIMARY
        assert prompt.sequence_order == 0

    def test_valid_follow_up_prompt(self):
        """Test valid follow-up prompt."""
        prompt = GeneratedPrompt(
            prompt_text="Can you tell me more about pricing?",
            prompt_type=PromptType.FOLLOW_UP,
            sequence_order=1,
            expected_response_type="informational",
        )
        assert prompt.prompt_type == PromptType.FOLLOW_UP

    def test_prompt_text_min_length(self):
        """Test prompt text minimum length validation."""
        with pytest.raises(ValueError):
            GeneratedPrompt(
                prompt_text="Short",  # Too short
                prompt_type=PromptType.PRIMARY,
                sequence_order=0,
            )


class TestGeneratedConversation:
    """Tests for GeneratedConversation schema."""

    def test_valid_conversation(self):
        """Test valid conversation with prompts."""
        prompts = [
            GeneratedPrompt(
                prompt_text="What services do you offer for enterprise customers?",
                prompt_type=PromptType.PRIMARY,
                sequence_order=0,
            ),
            GeneratedPrompt(
                prompt_text="How does pricing work for large teams?",
                prompt_type=PromptType.FOLLOW_UP,
                sequence_order=1,
            ),
            GeneratedPrompt(
                prompt_text="What integrations are available?",
                prompt_type=PromptType.FOLLOW_UP,
                sequence_order=2,
            ),
            GeneratedPrompt(
                prompt_text="Can we schedule a demo?",
                prompt_type=PromptType.FOLLOW_UP,
                sequence_order=3,
            ),
        ]

        conversation = GeneratedConversation(
            topic="Enterprise service inquiry",
            context="A large enterprise is evaluating solutions for their team of 500+ employees.",
            expected_outcome="Understanding of enterprise features and scheduling a demo",
            is_core_conversation=True,
            sequence_number=1,
            prompts=prompts,
        )

        assert conversation.topic == "Enterprise service inquiry"
        assert len(conversation.prompts) == 4

    def test_requires_primary_prompt(self):
        """Test that exactly one primary prompt is required."""
        prompts = [
            GeneratedPrompt(
                prompt_text="First follow-up question about something",
                prompt_type=PromptType.FOLLOW_UP,
                sequence_order=0,
            ),
            GeneratedPrompt(
                prompt_text="Second follow-up question here",
                prompt_type=PromptType.FOLLOW_UP,
                sequence_order=1,
            ),
            GeneratedPrompt(
                prompt_text="Third follow-up question for testing",
                prompt_type=PromptType.FOLLOW_UP,
                sequence_order=2,
            ),
            GeneratedPrompt(
                prompt_text="Fourth follow-up question needed",
                prompt_type=PromptType.FOLLOW_UP,
                sequence_order=3,
            ),
        ]

        with pytest.raises(ValueError, match="primary prompt"):
            GeneratedConversation(
                topic="Test topic for conversation",
                context="Test context with sufficient length to pass validation",
                expected_outcome="Test outcome for validation",
                sequence_number=1,
                prompts=prompts,
            )

    def test_requires_minimum_prompts(self):
        """Test that minimum prompts are required."""
        prompts = [
            GeneratedPrompt(
                prompt_text="What services do you offer for businesses?",
                prompt_type=PromptType.PRIMARY,
                sequence_order=0,
            ),
            GeneratedPrompt(
                prompt_text="How much does it cost?",
                prompt_type=PromptType.FOLLOW_UP,
                sequence_order=1,
            ),
        ]

        with pytest.raises(ValueError):
            GeneratedConversation(
                topic="Test topic for testing",
                context="Test context that is long enough to pass validation",
                expected_outcome="Test expected outcome",
                sequence_number=1,
                prompts=prompts,
            )


class TestConversationGenerationResponse:
    """Tests for ConversationGenerationResponse schema."""

    def test_requires_10_conversations(self):
        """Test that exactly 10 conversations are required."""
        with pytest.raises(ValueError):
            ConversationGenerationResponse(
                icp_id=uuid.uuid4(),
                icp_name="Test ICP",
                conversations=[],  # Empty list
            )

    def test_requires_5_core_conversations(self):
        """Test that exactly 5 core conversations are required."""
        data = create_mock_conversation_response()
        # Make all conversations non-core
        for conv in data["conversations"]:
            conv["is_core_conversation"] = False

        conversations = [
            GeneratedConversation.model_validate(c) for c in data["conversations"]
        ]

        with pytest.raises(ValueError, match="5 core conversations"):
            ConversationGenerationResponse(
                icp_id=uuid.uuid4(),
                icp_name="Test ICP",
                conversations=conversations,
            )

    def test_requires_unique_sequence_numbers(self):
        """Test that sequence numbers must be unique."""
        data = create_mock_conversation_response()
        # Set duplicate sequence numbers
        data["conversations"][0]["sequence_number"] = 1
        data["conversations"][1]["sequence_number"] = 1

        conversations = [
            GeneratedConversation.model_validate(c) for c in data["conversations"]
        ]

        with pytest.raises(ValueError, match="no duplicates"):
            ConversationGenerationResponse(
                icp_id=uuid.uuid4(),
                icp_name="Test ICP",
                conversations=conversations,
            )

    def test_requires_unique_topics(self):
        """Test that topics must be unique."""
        data = create_mock_conversation_response()
        # Set duplicate topics
        data["conversations"][0]["topic"] = "Same topic"
        data["conversations"][1]["topic"] = "Same topic"

        conversations = [
            GeneratedConversation.model_validate(c) for c in data["conversations"]
        ]

        with pytest.raises(ValueError, match="unique"):
            ConversationGenerationResponse(
                icp_id=uuid.uuid4(),
                icp_name="Test ICP",
                conversations=conversations,
            )


# ==================== Generator Tests ====================


class TestConversationGenerator:
    """Tests for ConversationGenerator class."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = MagicMock()
        client.complete_json = AsyncMock()
        return client

    @pytest.fixture
    def generator(self, mock_llm_client):
        """Create a ConversationGenerator with mocked LLM client."""
        return ConversationGenerator(llm_client=mock_llm_client)

    @pytest.mark.asyncio
    async def test_generate_with_retries_success(self, generator, mock_llm_client):
        """Test successful generation on first attempt."""
        mock_response = create_mock_llm_response(create_mock_conversation_response())
        mock_llm_client.complete_json.return_value = mock_response

        website_context = {
            "company_name": "Test Company",
            "industry": "Technology",
            "products": ["Product A", "Product B"],
            "services": ["Service A"],
            "value_propositions": ["Fast", "Reliable"],
        }

        icp_data = {
            "name": "Enterprise Buyer",
            "job_role": "IT Manager",
            "industry": "Technology",
            "company_size": "Large",
            "demographics": {"age_range": "35-50"},
            "pain_points": ["Integration complexity"],
            "goals": ["Improve efficiency"],
            "decision_factors": ["Price", "Support"],
            "communication_style": "Professional",
            "behavior_patterns": {
                "research_behavior": "Online research",
                "preferred_channels": ["Email"],
            },
        }

        conversations = await generator._generate_with_retries(
            website_context=website_context,
            icp_data=icp_data,
        )

        assert len(conversations) == 10
        assert all(isinstance(c, GeneratedConversation) for c in conversations)
        mock_llm_client.complete_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_with_retries_retry_on_validation_error(
        self, generator, mock_llm_client
    ):
        """Test retry on validation error."""
        # First response is invalid, second is valid
        invalid_response = create_mock_llm_response({"conversations": []})
        valid_response = create_mock_llm_response(create_mock_conversation_response())

        mock_llm_client.complete_json.side_effect = [invalid_response, valid_response]

        website_context = {
            "company_name": "Test Company",
            "industry": "Technology",
            "products": [],
            "services": [],
            "value_propositions": [],
        }

        icp_data = {
            "name": "Test Buyer",
            "job_role": "Manager",
            "industry": "Tech",
            "company_size": "Medium",
            "demographics": {},
            "pain_points": [],
            "goals": [],
            "decision_factors": [],
            "communication_style": "Professional",
            "behavior_patterns": {},
        }

        conversations = await generator._generate_with_retries(
            website_context=website_context,
            icp_data=icp_data,
        )

        assert len(conversations) == 10
        assert mock_llm_client.complete_json.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_with_retries_max_retries_exceeded(
        self, generator, mock_llm_client
    ):
        """Test that ConversationGenerationError is raised after max retries."""
        invalid_response = create_mock_llm_response({"conversations": []})
        mock_llm_client.complete_json.return_value = invalid_response

        website_context = {
            "company_name": "Test Company",
            "industry": "Technology",
            "products": [],
            "services": [],
            "value_propositions": [],
        }

        icp_data = {
            "name": "Test Buyer",
            "job_role": "Manager",
            "industry": "Tech",
            "company_size": "Medium",
            "demographics": {},
            "pain_points": [],
            "goals": [],
            "decision_factors": [],
            "communication_style": "Professional",
            "behavior_patterns": {},
        }

        with pytest.raises(ConversationGenerationError):
            await generator._generate_with_retries(
                website_context=website_context,
                icp_data=icp_data,
            )

        assert mock_llm_client.complete_json.call_count == generator.MAX_RETRIES

    def test_validate_quality_valid(self, generator):
        """Test quality validation passes for valid conversations."""
        data = create_mock_conversation_response()
        conversations = [
            GeneratedConversation.model_validate(c) for c in data["conversations"]
        ]

        # Should not raise
        generator._validate_quality(conversations)

    def test_validate_quality_wrong_count(self, generator):
        """Test quality validation fails for wrong conversation count."""
        data = create_mock_conversation_response()
        conversations = [
            GeneratedConversation.model_validate(c) for c in data["conversations"][:5]
        ]

        with pytest.raises(ValueError, match="Expected 10"):
            generator._validate_quality(conversations)

    def test_validate_quality_duplicate_topics(self, generator):
        """Test quality validation fails for duplicate topics."""
        data = create_mock_conversation_response()
        data["conversations"][0]["topic"] = data["conversations"][1]["topic"]

        conversations = [
            GeneratedConversation.model_validate(c) for c in data["conversations"]
        ]

        with pytest.raises(ValueError, match="unique"):
            generator._validate_quality(conversations)

    def test_build_icp_data(self, generator):
        """Test building ICP data dictionary."""
        mock_icp = MagicMock()
        mock_icp.name = "Enterprise Buyer"
        mock_icp.description = "A typical enterprise buyer"
        mock_icp.professional_profile = {
            "job_role": "IT Director",
            "industry": "Technology",
            "company_size": "Enterprise",
            "communication_style": "Formal",
            "research_behavior": "Thorough",
        }
        mock_icp.demographics = {"age_range": "40-55"}
        mock_icp.pain_points = ["Complexity", "Cost"]
        mock_icp.goals = ["Efficiency", "ROI"]
        mock_icp.decision_factors = ["Support", "Features"]
        mock_icp.information_sources = ["Industry reports", "Peer reviews"]

        result = generator._build_icp_data(mock_icp)

        assert result["name"] == "Enterprise Buyer"
        assert result["job_role"] == "IT Director"
        assert "Complexity" in result["pain_points"]
        assert result["communication_style"] == "Formal"
