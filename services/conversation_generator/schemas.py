"""
Pydantic schemas for Conversation Generator Service.

Defines request/response models for conversation generation.
"""

from enum import Enum
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class PromptType(str, Enum):
    """Type of prompt in a conversation."""
    PRIMARY = "primary"
    FOLLOW_UP = "follow_up"
    CLARIFICATION = "clarification"


class GeneratedPrompt(BaseModel):
    """A single prompt within a conversation."""
    prompt_text: str = Field(..., min_length=10, max_length=2000)
    prompt_type: PromptType
    sequence_order: int = Field(..., ge=0)
    expected_response_type: str | None = Field(
        default=None,
        description="Type of response expected (e.g., informational, comparison, recommendation)",
    )

    model_config = {"use_enum_values": True}


class GeneratedConversation(BaseModel):
    """A generated conversation topic with prompts."""
    topic: str = Field(..., min_length=5, max_length=500)
    context: str = Field(
        ...,
        min_length=20,
        max_length=2000,
        description="Situational context for this conversation",
    )
    expected_outcome: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="What the user hopes to achieve",
    )
    is_core_conversation: bool = Field(
        default=False,
        description="Whether this is one of the 5 core conversation threads",
    )
    sequence_number: int = Field(
        ...,
        ge=1,
        le=10,
        description="Order within the ICP (1-10)",
    )
    prompts: list[GeneratedPrompt] = Field(
        ...,
        min_length=4,
        max_length=6,
        description="Primary prompt + 3-5 follow-up sub-prompts",
    )

    @field_validator("prompts")
    @classmethod
    def validate_prompts(cls, v: list[GeneratedPrompt]) -> list[GeneratedPrompt]:
        """Ensure prompts have correct structure."""
        if not v:
            raise ValueError("At least 4 prompts required (1 primary + 3 follow-ups)")

        # Check for exactly one primary prompt
        primary_count = sum(1 for p in v if p.prompt_type == PromptType.PRIMARY)
        if primary_count != 1:
            raise ValueError("Exactly one primary prompt required")

        # Check sequence order starts at 0
        if v[0].sequence_order != 0:
            raise ValueError("First prompt must have sequence_order 0")

        return v


class ConversationGenerationResponse(BaseModel):
    """Response containing all generated conversations for an ICP."""
    icp_id: UUID
    icp_name: str
    conversations: list[GeneratedConversation] = Field(
        ...,
        min_length=10,
        max_length=10,
        description="Exactly 10 conversations per ICP",
    )

    @model_validator(mode="after")
    def validate_conversations(self) -> "ConversationGenerationResponse":
        """Validate conversation structure and uniqueness."""
        if len(self.conversations) != 10:
            raise ValueError("Exactly 10 conversations required per ICP")

        # Check core conversations (first 5)
        core_count = sum(1 for c in self.conversations if c.is_core_conversation)
        if core_count != 5:
            raise ValueError("Exactly 5 core conversations required")

        # Validate sequence numbers are unique and 1-10
        sequence_numbers = [c.sequence_number for c in self.conversations]
        if sorted(sequence_numbers) != list(range(1, 11)):
            raise ValueError("Sequence numbers must be 1-10 with no duplicates")

        # Check topic uniqueness
        topics = [c.topic.lower().strip() for c in self.conversations]
        if len(set(topics)) != len(topics):
            raise ValueError("All conversation topics must be unique")

        return self


class BatchConversationResponse(BaseModel):
    """Response for batch conversation generation across all ICPs."""
    website_id: UUID
    total_icps: int
    total_conversations: int
    icp_results: list[ConversationGenerationResponse]

    @model_validator(mode="after")
    def validate_totals(self) -> "BatchConversationResponse":
        """Validate batch totals."""
        expected_conversations = self.total_icps * 10
        if self.total_conversations != expected_conversations:
            raise ValueError(
                f"Expected {expected_conversations} conversations for {self.total_icps} ICPs"
            )
        return self


# ==================== API Request/Response Schemas ====================


class ConversationGenerationRequest(BaseModel):
    """Request to generate conversations for an ICP."""
    force_regenerate: bool = Field(
        default=False,
        description="Whether to regenerate existing conversations",
    )
    llm_provider: str | None = Field(
        default=None,
        description="LLM provider to use (openai, anthropic)",
    )


class BatchConversationRequest(BaseModel):
    """Request to generate conversations for all ICPs of a website."""
    website_id: UUID
    force_regenerate: bool = False
    llm_provider: str | None = None


class ConversationJobResponse(BaseModel):
    """Response when a conversation generation job is queued."""
    job_id: UUID
    icp_id: UUID
    status: str = "queued"
    message: str = "Conversation generation job queued"


class BatchJobResponse(BaseModel):
    """Response when batch conversation generation is queued."""
    job_id: UUID
    website_id: UUID
    icp_count: int
    status: str = "queued"
    message: str = "Batch conversation generation job queued"


class ConversationSummary(BaseModel):
    """Summary of a stored conversation."""
    id: UUID
    topic: str
    context: str
    expected_outcome: str | None
    is_core_conversation: bool
    sequence_number: int
    prompt_count: int
    created_at: str


class ICPConversationsResponse(BaseModel):
    """Response containing all conversations for an ICP."""
    icp_id: UUID
    icp_name: str
    conversation_count: int
    conversations: list[ConversationSummary]


class ConversationDetailResponse(BaseModel):
    """Detailed response for a single conversation with all prompts."""
    id: UUID
    topic: str
    context: str
    expected_outcome: str | None
    is_core_conversation: bool
    sequence_number: int
    icp_id: UUID
    icp_name: str
    prompts: list[GeneratedPrompt]
    created_at: str
    updated_at: str
