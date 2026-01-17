"""
Conversation and Prompt models.
"""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
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
    """Conversation sequence model."""

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
    is_core_conversation: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
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


class Prompt(Base, UUIDMixin, TimestampMixin):
    """Individual prompt within a conversation."""

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
    """Prompt classification metadata."""

    __tablename__ = "prompt_classifications"

    prompt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
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
    classifier_version: Mapped[str | None] = mapped_column(String(50))

    # Relationships
    prompt: Mapped["Prompt"] = relationship(
        "Prompt",
        back_populates="classification",
    )
