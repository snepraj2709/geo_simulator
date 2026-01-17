"""
Brand and belief map models.

Brands are entities mentioned in LLM responses. The system tracks
their presence, position, and the beliefs they install.
"""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, Numeric, String, Boolean, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db.postgres import Base
from shared.models.base import TimestampMixin, UUIDMixin
from shared.models.enums import BeliefType, BrandPresence

if TYPE_CHECKING:
    from shared.models.simulation import LLMResponse
    from shared.models.conversation import PromptClassification


class Brand(Base, UUIDMixin, TimestampMixin):
    """
    Brand entity model.

    Represents a brand/company that can be mentioned in LLM responses.
    Brands are normalized by name to prevent duplicates.

    Attributes:
        name: Display name of the brand
        normalized_name: Lowercase, trimmed name for matching
        domain: Website domain if known
        industry: Industry classification
        is_tracked: True if this is a user's own brand
    """

    __tablename__ = "brands"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    domain: Mapped[str | None] = mapped_column(String(255))
    industry: Mapped[str | None] = mapped_column(String(255))
    is_tracked: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    brand_states: Mapped[list["LLMBrandState"]] = relationship(
        "LLMBrandState",
        back_populates="brand",
        cascade="all, delete-orphan",
    )
    belief_maps: Mapped[list["LLMAnswerBeliefMap"]] = relationship(
        "LLMAnswerBeliefMap",
        back_populates="brand",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        # Index for finding tracked brands quickly
        Index("idx_brands_tracked", "is_tracked", postgresql_where=(is_tracked == True)),
    )


class LLMBrandState(Base, UUIDMixin, TimestampMixin):
    """
    Brand state per LLM response.

    Tracks how a specific brand appeared in a specific LLM response,
    including its presence type, position, and the belief it installs.

    Attributes:
        llm_response_id: The response containing this brand
        brand_id: The brand that was mentioned
        presence: ignored, mentioned, trusted, recommended, compared
        position_rank: Position in response (1 = first mentioned)
        belief_sold: truth, superiority, outcome, transaction, identity, social_proof
    """

    __tablename__ = "llm_brand_states"

    llm_response_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("llm_responses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brands.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Brand presence state
    presence: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    position_rank: Mapped[int | None] = mapped_column(Integer)

    # BeliefType sold
    belief_sold: Mapped[str | None] = mapped_column(String(50), index=True)

    # Relationships
    llm_response: Mapped["LLMResponse"] = relationship(
        "LLMResponse",
        back_populates="brand_states",
    )
    brand: Mapped["Brand"] = relationship(
        "Brand",
        back_populates="brand_states",
    )

    __table_args__ = (
        # Each response can only have one state per brand
        UniqueConstraint("llm_response_id", "brand_id", name="uq_llm_brand_states_response_brand"),
    )


class LLMAnswerBeliefMap(Base, UUIDMixin, TimestampMixin):
    """
    Aggregated belief map for analytics.

    Denormalized view combining LLM response, prompt classification, and brand
    state data for efficient querying in analytics dashboards.

    Attributes:
        llm_response_id: Source response
        prompt_classification_id: Classification of the prompt (optional)
        brand_id: The brand being tracked
        intent_type: Denormalized from classification
        funnel_stage: Denormalized from classification
        buying_signal: Denormalized from classification
        trust_need: Denormalized from classification
        presence: Denormalized from brand state
        position_rank: Denormalized from brand state
        belief_sold: Denormalized from brand state
        llm_provider: Denormalized from response
    """

    __tablename__ = "llm_answer_belief_maps"

    llm_response_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("llm_responses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prompt_classification_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("prompt_classifications.id", ondelete="SET NULL"),
    )
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brands.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Denormalized fields for query performance
    intent_type: Mapped[str | None] = mapped_column(String(50), index=True)
    funnel_stage: Mapped[str | None] = mapped_column(String(50))
    buying_signal: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))
    trust_need: Mapped[Decimal | None] = mapped_column(Numeric(3, 2))

    presence: Mapped[str | None] = mapped_column(String(50))
    position_rank: Mapped[int | None] = mapped_column(Integer)
    belief_sold: Mapped[str | None] = mapped_column(String(50))

    llm_provider: Mapped[str | None] = mapped_column(String(50), index=True)

    # Relationships
    brand: Mapped["Brand"] = relationship(
        "Brand",
        back_populates="belief_maps",
    )
