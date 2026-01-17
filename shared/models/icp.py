"""
Ideal Customer Profile (ICP) model.
"""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db.postgres import Base
from shared.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from shared.models.website import Website
    from shared.models.conversation import ConversationSequence


class ICP(Base, UUIDMixin, TimestampMixin):
    """Ideal Customer Profile model."""

    __tablename__ = "icps"

    website_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("websites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Demographics
    demographics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    # Professional Profile
    professional_profile: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    # Psychographics
    pain_points: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    goals: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    motivations: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    objections: Mapped[list[str] | None] = mapped_column(JSONB)

    # Behavior
    decision_factors: Mapped[list[str] | None] = mapped_column(JSONB)
    information_sources: Mapped[list[str] | None] = mapped_column(JSONB)
    buying_journey_stage: Mapped[str | None] = mapped_column(String(50))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    website: Mapped["Website"] = relationship(
        "Website",
        back_populates="icps",
    )
    conversations: Mapped[list["ConversationSequence"]] = relationship(
        "ConversationSequence",
        back_populates="icp",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        # Unique constraint: one sequence number per website
        {"sqlite_autoincrement": True},
    )
