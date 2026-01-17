"""
Competitive analysis models.

Includes:
- CompetitorRelationship: Tracks relationships between brands
- ShareOfVoice: Aggregated visibility metrics per brand/provider
- SubstitutionPattern: Tracks which brands appear when others are absent
"""

import uuid
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db.postgres import Base
from shared.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from shared.models.website import Website
    from shared.models.brand import Brand


class CompetitorRelationship(Base, UUIDMixin, TimestampMixin):
    """
    Competitor relationship between brands.

    Tracks the competitive relationships identified for a website's brand
    against other brands found in the market.

    Attributes:
        website_id: The website context for this relationship
        primary_brand_id: The tracked/primary brand
        competitor_brand_id: The competitor brand
        relationship_type: direct, indirect, or substitute
    """

    __tablename__ = "competitor_relationships"

    website_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("websites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    primary_brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brands.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    competitor_brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brands.id", ondelete="CASCADE"),
        nullable=False,
    )
    relationship_type: Mapped[str | None] = mapped_column(String(50))

    # Relationships
    website: Mapped["Website"] = relationship("Website")
    primary_brand: Mapped["Brand"] = relationship(
        "Brand",
        foreign_keys=[primary_brand_id],
    )
    competitor_brand: Mapped["Brand"] = relationship(
        "Brand",
        foreign_keys=[competitor_brand_id],
    )

    __table_args__ = (
        UniqueConstraint(
            "website_id", "primary_brand_id", "competitor_brand_id",
            name="uq_competitor_relationships_brands",
        ),
    )


class ShareOfVoice(Base, UUIDMixin, TimestampMixin):
    """
    Share of Voice metrics per brand and provider.

    Aggregated metrics tracking brand visibility, recommendations,
    and positioning across LLM providers for a given time period.

    Attributes:
        website_id: The website context
        brand_id: The brand being measured
        llm_provider: The LLM provider (openai, google, anthropic, perplexity)
        mention_count: Total times brand was mentioned
        recommendation_count: Times brand was recommended
        first_position_count: Times brand appeared in first position
        total_responses: Total responses analyzed
        visibility_score: Calculated visibility (0-100)
        trust_score: Calculated trust score (0-100)
        recommendation_rate: Percentage of recommendations (0-100)
        period_start: Start of measurement period
        period_end: End of measurement period
    """

    __tablename__ = "share_of_voice"

    website_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("websites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brands.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    llm_provider: Mapped[str] = mapped_column(String(50), nullable=False)

    # Raw metrics
    mention_count: Mapped[int] = mapped_column(Integer, default=0)
    recommendation_count: Mapped[int] = mapped_column(Integer, default=0)
    first_position_count: Mapped[int] = mapped_column(Integer, default=0)
    total_responses: Mapped[int] = mapped_column(Integer, default=0)

    # Calculated scores (0-100 scale)
    visibility_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    trust_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    recommendation_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))

    # Time period
    period_start: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    # Relationships
    website: Mapped["Website"] = relationship("Website")
    brand: Mapped["Brand"] = relationship("Brand")

    __table_args__ = (
        UniqueConstraint(
            "website_id", "brand_id", "llm_provider", "period_start", "period_end",
            name="uq_share_of_voice_period",
        ),
    )


class SubstitutionPattern(Base, UUIDMixin, TimestampMixin):
    """
    Substitution pattern tracking.

    Tracks which brands appear as substitutes when a specific brand
    is missing from LLM responses. Used to identify competitive threats.

    Attributes:
        website_id: The website context
        missing_brand_id: The brand that was absent
        substitute_brand_id: The brand that appeared instead
        occurrence_count: Number of times this substitution occurred
        avg_position: Average position of the substitute
        llm_provider: The LLM provider where pattern was observed
        period_start: Start of observation period
        period_end: End of observation period
    """

    __tablename__ = "substitution_patterns"

    website_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("websites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    missing_brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brands.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    substitute_brand_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brands.id", ondelete="CASCADE"),
        nullable=False,
    )

    occurrence_count: Mapped[int] = mapped_column(Integer, default=1)
    avg_position: Mapped[Decimal | None] = mapped_column(Numeric(3, 1))

    llm_provider: Mapped[str | None] = mapped_column(String(50))

    period_start: Mapped[date | None] = mapped_column(Date)
    period_end: Mapped[date | None] = mapped_column(Date)

    # Relationships
    website: Mapped["Website"] = relationship("Website")
    missing_brand: Mapped["Brand"] = relationship(
        "Brand",
        foreign_keys=[missing_brand_id],
    )
    substitute_brand: Mapped["Brand"] = relationship(
        "Brand",
        foreign_keys=[substitute_brand_id],
    )
