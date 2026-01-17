"""
Ideal Customer Profile (ICP) model.

ICPs represent distinct customer segments for a website. Each website
has up to 5 ICPs that define different personas who might be interested
in the website's offerings.
"""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db.postgres import Base
from shared.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from shared.models.website import Website
    from shared.models.conversation import ConversationSequence


class ICP(Base, UUIDMixin, TimestampMixin):
    """
    Ideal Customer Profile model.

    Represents a distinct customer persona for a website. Each website can have
    up to 5 ICPs, each with a unique sequence number (1-5).

    Attributes:
        website_id: Reference to the parent website
        name: Human-readable name for the ICP (e.g., "Enterprise Decision Maker")
        description: Detailed description of this persona
        sequence_number: Order within the website (1-5)
        demographics: Age, location, income, education info
        professional_profile: Job titles, company size, industry
        pain_points: List of challenges this persona faces
        goals: List of objectives this persona wants to achieve
        motivations: Primary and secondary motivators
        objections: Common buying objections
        decision_factors: What influences purchase decisions
        information_sources: Where they research solutions
        buying_journey_stage: Typical entry point in the funnel
        is_active: Whether this ICP is active for simulations
    """

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

    # Demographics - structured as JSONB for flexibility
    # Expected: {"age_range": "25-45", "gender": "any", "location": "US/EU", "income_level": "middle-upper"}
    demographics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    # Professional Profile
    # Expected: {"job_titles": ["PM", "Lead"], "company_size": "50-500", "industry": "Tech", "seniority": "mid-senior"}
    professional_profile: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    # Psychographics
    pain_points: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    goals: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    motivations: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    objections: Mapped[list[str] | None] = mapped_column(JSONB)

    # Behavioral attributes
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
        # Each website can only have one ICP per sequence number
        UniqueConstraint("website_id", "sequence_number", name="uq_icps_website_sequence"),
        # Partial index for active ICPs
        Index("idx_icps_active", "is_active", postgresql_where=(is_active == True)),
    )
