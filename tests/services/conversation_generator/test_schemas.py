"""
Tests for Conversation Generator schemas.

Tests Pydantic models and validation logic.
"""

import uuid
import pytest

from services.conversation_generator.schemas import (
    PromptType,
    GeneratedPrompt,
    GeneratedConversation,
    ConversationGenerationResponse,
    BatchConversationResponse,
    ConversationGenerationRequest,
    ConversationSummary,
)


class TestPromptType:
    """Tests for PromptType enum."""

    def test_prompt_type_values(self):
        """Test PromptType enum values."""
        assert PromptType.PRIMARY.value == "primary"
        assert PromptType.FOLLOW_UP.value == "follow_up"
        assert PromptType.CLARIFICATION.value == "clarification"


class TestGeneratedPrompt:
    """Tests for GeneratedPrompt schema."""

    def test_valid_prompt(self):
        """Test creating a valid prompt."""
        prompt = GeneratedPrompt(
            prompt_text="What are the main features of your product?",
            prompt_type=PromptType.PRIMARY,
            sequence_order=0,
            expected_response_type="informational",
        )
        assert prompt.prompt_text == "What are the main features of your product?"
        assert prompt.prompt_type == PromptType.PRIMARY

    def test_prompt_type_string_coercion(self):
        """Test that string values are coerced to enum."""
        prompt = GeneratedPrompt(
            prompt_text="This is a follow-up question about your services",
            prompt_type="follow_up",
            sequence_order=1,
        )
        assert prompt.prompt_type == "follow_up"

    def test_prompt_text_too_short(self):
        """Test validation fails for too short prompt text."""
        with pytest.raises(ValueError):
            GeneratedPrompt(
                prompt_text="Short",
                prompt_type=PromptType.PRIMARY,
                sequence_order=0,
            )

    def test_negative_sequence_order(self):
        """Test validation fails for negative sequence order."""
        with pytest.raises(ValueError):
            GeneratedPrompt(
                prompt_text="What services do you offer?",
                prompt_type=PromptType.PRIMARY,
                sequence_order=-1,
            )


class TestGeneratedConversation:
    """Tests for GeneratedConversation schema."""

    @pytest.fixture
    def valid_prompts(self):
        """Create a list of valid prompts."""
        return [
            GeneratedPrompt(
                prompt_text="What services do you offer for enterprise customers?",
                prompt_type=PromptType.PRIMARY,
                sequence_order=0,
            ),
            GeneratedPrompt(
                prompt_text="How does the pricing structure work?",
                prompt_type=PromptType.FOLLOW_UP,
                sequence_order=1,
            ),
            GeneratedPrompt(
                prompt_text="What integrations are available?",
                prompt_type=PromptType.FOLLOW_UP,
                sequence_order=2,
            ),
            GeneratedPrompt(
                prompt_text="Can we schedule a demo call?",
                prompt_type=PromptType.FOLLOW_UP,
                sequence_order=3,
            ),
        ]

    def test_valid_conversation(self, valid_prompts):
        """Test creating a valid conversation."""
        conversation = GeneratedConversation(
            topic="Enterprise service inquiry and evaluation",
            context="A Fortune 500 company is evaluating solutions for their global team.",
            expected_outcome="Complete understanding of enterprise features",
            is_core_conversation=True,
            sequence_number=1,
            prompts=valid_prompts,
        )
        assert len(conversation.prompts) == 4

    def test_topic_too_short(self, valid_prompts):
        """Test validation fails for too short topic."""
        with pytest.raises(ValueError):
            GeneratedConversation(
                topic="Hi",
                context="A company is looking for solutions to their problems.",
                expected_outcome="Understanding features",
                sequence_number=1,
                prompts=valid_prompts,
            )

    def test_context_too_short(self, valid_prompts):
        """Test validation fails for too short context."""
        with pytest.raises(ValueError):
            GeneratedConversation(
                topic="Enterprise inquiry topic",
                context="Short context",
                expected_outcome="Understanding features",
                sequence_number=1,
                prompts=valid_prompts,
            )

    def test_sequence_number_bounds(self, valid_prompts):
        """Test sequence number must be between 1 and 10."""
        with pytest.raises(ValueError):
            GeneratedConversation(
                topic="Valid topic here",
                context="Valid context that is long enough to pass validation",
                expected_outcome="Valid outcome",
                sequence_number=0,  # Invalid
                prompts=valid_prompts,
            )

        with pytest.raises(ValueError):
            GeneratedConversation(
                topic="Valid topic here",
                context="Valid context that is long enough to pass validation",
                expected_outcome="Valid outcome",
                sequence_number=11,  # Invalid
                prompts=valid_prompts,
            )

    def test_too_few_prompts(self):
        """Test validation fails for too few prompts."""
        prompts = [
            GeneratedPrompt(
                prompt_text="What services do you offer?",
                prompt_type=PromptType.PRIMARY,
                sequence_order=0,
            ),
        ]
        with pytest.raises(ValueError):
            GeneratedConversation(
                topic="Valid topic here",
                context="Valid context that is long enough to pass validation",
                expected_outcome="Valid outcome",
                sequence_number=1,
                prompts=prompts,
            )

    def test_no_primary_prompt(self):
        """Test validation fails when no primary prompt."""
        prompts = [
            GeneratedPrompt(
                prompt_text="Follow up question one about services",
                prompt_type=PromptType.FOLLOW_UP,
                sequence_order=0,
            ),
            GeneratedPrompt(
                prompt_text="Follow up question two about pricing",
                prompt_type=PromptType.FOLLOW_UP,
                sequence_order=1,
            ),
            GeneratedPrompt(
                prompt_text="Follow up question three about features",
                prompt_type=PromptType.FOLLOW_UP,
                sequence_order=2,
            ),
            GeneratedPrompt(
                prompt_text="Follow up question four about support",
                prompt_type=PromptType.FOLLOW_UP,
                sequence_order=3,
            ),
        ]
        with pytest.raises(ValueError, match="primary"):
            GeneratedConversation(
                topic="Valid topic here",
                context="Valid context that is long enough to pass validation",
                expected_outcome="Valid outcome",
                sequence_number=1,
                prompts=prompts,
            )

    def test_multiple_primary_prompts(self):
        """Test validation fails for multiple primary prompts."""
        prompts = [
            GeneratedPrompt(
                prompt_text="First primary question about services",
                prompt_type=PromptType.PRIMARY,
                sequence_order=0,
            ),
            GeneratedPrompt(
                prompt_text="Second primary question about features",
                prompt_type=PromptType.PRIMARY,
                sequence_order=1,
            ),
            GeneratedPrompt(
                prompt_text="Follow up question about pricing",
                prompt_type=PromptType.FOLLOW_UP,
                sequence_order=2,
            ),
            GeneratedPrompt(
                prompt_text="Another follow up about support",
                prompt_type=PromptType.FOLLOW_UP,
                sequence_order=3,
            ),
        ]
        with pytest.raises(ValueError, match="Exactly one primary"):
            GeneratedConversation(
                topic="Valid topic here",
                context="Valid context that is long enough to pass validation",
                expected_outcome="Valid outcome",
                sequence_number=1,
                prompts=prompts,
            )


class TestConversationGenerationRequest:
    """Tests for ConversationGenerationRequest schema."""

    def test_default_values(self):
        """Test default values are set correctly."""
        request = ConversationGenerationRequest()
        assert request.force_regenerate is False
        assert request.llm_provider is None

    def test_custom_values(self):
        """Test custom values are accepted."""
        request = ConversationGenerationRequest(
            force_regenerate=True,
            llm_provider="anthropic",
        )
        assert request.force_regenerate is True
        assert request.llm_provider == "anthropic"


class TestConversationSummary:
    """Tests for ConversationSummary schema."""

    def test_valid_summary(self):
        """Test creating a valid summary."""
        summary = ConversationSummary(
            id=uuid.uuid4(),
            topic="Product inquiry topic",
            context="Customer looking for solutions",
            expected_outcome="Understanding of product features",
            is_core_conversation=True,
            sequence_number=1,
            prompt_count=4,
            created_at="2024-01-01T00:00:00Z",
        )
        assert summary.prompt_count == 4
        assert summary.is_core_conversation is True


class TestBatchConversationResponse:
    """Tests for BatchConversationResponse schema."""

    def test_validates_totals(self):
        """Test that totals are validated correctly."""
        icp_id = uuid.uuid4()

        # Create valid conversations
        def create_valid_prompts():
            return [
                GeneratedPrompt(
                    prompt_text="What services do you offer for enterprise?",
                    prompt_type=PromptType.PRIMARY,
                    sequence_order=0,
                ),
                GeneratedPrompt(
                    prompt_text="How does pricing work?",
                    prompt_type=PromptType.FOLLOW_UP,
                    sequence_order=1,
                ),
                GeneratedPrompt(
                    prompt_text="What about integrations?",
                    prompt_type=PromptType.FOLLOW_UP,
                    sequence_order=2,
                ),
                GeneratedPrompt(
                    prompt_text="Can we get a demo?",
                    prompt_type=PromptType.FOLLOW_UP,
                    sequence_order=3,
                ),
            ]

        conversations = []
        for i in range(10):
            conversations.append(
                GeneratedConversation(
                    topic=f"Topic {i + 1} about different feature",
                    context="Valid context that is long enough for validation",
                    expected_outcome="Valid expected outcome",
                    is_core_conversation=i < 5,
                    sequence_number=i + 1,
                    prompts=create_valid_prompts(),
                )
            )

        icp_result = ConversationGenerationResponse(
            icp_id=icp_id,
            icp_name="Test ICP",
            conversations=conversations,
        )

        # Valid batch response
        batch = BatchConversationResponse(
            website_id=uuid.uuid4(),
            total_icps=1,
            total_conversations=10,
            icp_results=[icp_result],
        )
        assert batch.total_conversations == 10

        # Invalid batch response (wrong total)
        with pytest.raises(ValueError, match="Expected 20 conversations"):
            BatchConversationResponse(
                website_id=uuid.uuid4(),
                total_icps=2,
                total_conversations=10,  # Should be 20
                icp_results=[icp_result],
            )
