"""
Conversation and Prompt models.

Conversations represent simulated user journeys through LLM interactions.
Each conversation belongs to an ICP and contains multiple prompts.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db.postgres import Base
from shared.models.base import TimestampMixin, UUIDMixin
from shared.models.enums import FunnelStage, IntentType, PromptType, QueryIntent

if TYPE_CHECKING:
    from shared.models.website import Website
    from shared.models.icp import ICP
    from shared.models.simulation import LLMResponse


class ConversationSequence(Base, UUIDMixin, TimestampMixin):
    """
    Conversation sequence model.

    Represents a multi-turn conversation flow for a specific ICP.
    Each website has 50 conversations (10 topics x 5 ICPs).

    Attributes:
        website_id: Parent website reference
        icp_id: The ICP this conversation represents
        topic: The conversation topic/theme
        context: Situational context for the conversation
        expected_outcome: What the user hopes to achieve
        is_core_conversation: True for the 5 constant conversations per ICP
        sequence_number: Order within the ICP (1-10)
    """

    __tablename__ = "conversation_sequences"

    website_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("websites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    icp_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("icps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    topic: Mapped[str] = mapped_column(String(255), nullable=False)
    context: Mapped[str | None] = mapped_column(Text)
    expected_outcome: Mapped[str | None] = mapped_column(Text)
    is_core_conversation: Mapped[bool] = mapped_column(Boolean, default=False)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    website: Mapped["Website"] = relationship(
        "Website",
        back_populates="conversations",
    )
    icp: Mapped["ICP"] = relationship(
        "ICP",
        back_populates="conversations",
    )
    prompts: Mapped[list["Prompt"]] = relationship(
        "Prompt",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Prompt.sequence_order",
    )

    __table_args__ = (
        # Each ICP can only have one conversation per sequence number
        UniqueConstraint("icp_id", "sequence_number", name="uq_conversations_icp_sequence"),
        # Index for core conversations lookup
        Index(
            "idx_conversations_core",
            "is_core_conversation",
            postgresql_where=(is_core_conversation == True),
        ),
    )


class Prompt(Base, UUIDMixin, TimestampMixin):
    """
    Individual prompt within a conversation.

    Represents a single user query in a multi-turn conversation.
    Each prompt can be classified and will generate multiple LLM responses.

    Attributes:
        conversation_id: Parent conversation reference
        prompt_text: The actual prompt/question text
        prompt_type: primary, follow_up, or clarification
        sequence_order: Order within the conversation
    """

    __tablename__ = "prompts"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversation_sequences.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=PromptType.PRIMARY.value,
        index=True,
    )
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    conversation: Mapped["ConversationSequence"] = relationship(
        "ConversationSequence",
        back_populates="prompts",
    )
    classification: Mapped["PromptClassification | None"] = relationship(
        "PromptClassification",
        back_populates="prompt",
        uselist=False,
        cascade="all, delete-orphan",
    )
    llm_responses: Mapped[list["LLMResponse"]] = relationship(
        "LLMResponse",
        back_populates="prompt",
        cascade="all, delete-orphan",
    )


class PromptClassification(Base, UUIDMixin):
    """
    Prompt classification metadata.

    Stores the classified intent, funnel stage, and other attributes
    for a prompt. Used to analyze how different prompts perform.

    Attributes:
        prompt_id: Reference to the classified prompt
        intent_type: informational, evaluation, or decision
        funnel_stage: awareness, consideration, or purchase
        buying_signal: 0.0-1.0 score indicating purchase intent
        trust_need: 0.0-1.0 score indicating need for trust-building
        query_intent: Commercial, Informational, Navigational, Transactional
        confidence_score: Classifier confidence (0.0-1.0)
        classifier_version: Version of the classifier used
        classified_at: When classification was performed
    """

    __tablename__ = "prompt_classifications"

    prompt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # UserIntent fields
    intent_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    funnel_stage: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    buying_signal: Mapped[Decimal] = mapped_column(
        Numeric(3, 2),
        nullable=False,
    )
    trust_need: Mapped[Decimal] = mapped_column(
        Numeric(3, 2),
        nullable=False,
    )

    # Additional classification
    query_intent: Mapped[str | None] = mapped_column(String(50))

    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    classified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    classifier_version: Mapped[str | None] = mapped_column(String(50))

    # Relationships
    prompt: Mapped["Prompt"] = relationship(
        "Prompt",
        back_populates="classification",
    )
