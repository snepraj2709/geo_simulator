"""
Brand and belief map models.
"""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db.postgres import Base
from shared.models.base import TimestampMixin, UUIDMixin
from shared.models.enums import BeliefType, BrandPresence

if TYPE_CHECKING:
    from shared.models.simulation import LLMResponse
    from shared.models.conversation import PromptClassification


class Brand(Base, UUIDMixin, TimestampMixin):
    """Brand entity model."""

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
    is_tracked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

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


class LLMBrandState(Base, UUIDMixin, TimestampMixin):
    """Brand state per LLM response."""

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

    # LLMBrandState
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


class LLMAnswerBeliefMap(Base, UUIDMixin, TimestampMixin):
    """Aggregated belief map for analytics."""

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
