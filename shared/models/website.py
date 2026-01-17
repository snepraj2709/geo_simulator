"""
Website and scraping models.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.db.postgres import Base
from shared.models.base import TimestampMixin, UUIDMixin
from shared.models.enums import WebsiteStatus

if TYPE_CHECKING:
    from shared.models.user import Organization
    from shared.models.icp import ICP
    from shared.models.conversation import ConversationSequence
    from shared.models.simulation import SimulationRun


class Website(Base, UUIDMixin, TimestampMixin):
    """Tracked website model."""

    __tablename__ = "websites"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(50),
        default=WebsiteStatus.PENDING.value,
        index=True,
    )
    last_scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_hard_scrape_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scrape_depth: Mapped[int] = mapped_column(Integer, default=3)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="websites",
    )
    pages: Mapped[list["ScrapedPage"]] = relationship(
        "ScrapedPage",
        back_populates="website",
        cascade="all, delete-orphan",
    )
    analysis: Mapped["WebsiteAnalysis | None"] = relationship(
        "WebsiteAnalysis",
        back_populates="website",
        uselist=False,
        cascade="all, delete-orphan",
    )
    icps: Mapped[list["ICP"]] = relationship(
        "ICP",
        back_populates="website",
        cascade="all, delete-orphan",
    )
    conversations: Mapped[list["ConversationSequence"]] = relationship(
        "ConversationSequence",
        back_populates="website",
        cascade="all, delete-orphan",
    )
    simulation_runs: Mapped[list["SimulationRun"]] = relationship(
        "SimulationRun",
        back_populates="website",
        cascade="all, delete-orphan",
    )


class ScrapedPage(Base, UUIDMixin):
    """Scraped page content model."""

    __tablename__ = "scraped_pages"

    website_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("websites.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    url_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(512))
    meta_description: Mapped[str | None] = mapped_column(Text)
    content_text: Mapped[str | None] = mapped_column(Text)
    content_html_path: Mapped[str | None] = mapped_column(String(512))
    word_count: Mapped[int | None] = mapped_column(Integer)
    page_type: Mapped[str | None] = mapped_column(String(50), index=True)
    http_status: Mapped[int | None] = mapped_column(Integer)
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Relationships
    website: Mapped["Website"] = relationship(
        "Website",
        back_populates="pages",
    )


class WebsiteAnalysis(Base, UUIDMixin):
    """Website analysis results model."""

    __tablename__ = "website_analysis"

    website_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("websites.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    industry: Mapped[str | None] = mapped_column(String(255))
    business_model: Mapped[str | None] = mapped_column(String(100))
    primary_offerings: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    value_propositions: Mapped[list[str] | None] = mapped_column(JSONB)
    target_markets: Mapped[list[str] | None] = mapped_column(JSONB)
    competitors_mentioned: Mapped[list[str] | None] = mapped_column(JSONB)
    analyzed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Relationships
    website: Mapped["Website"] = relationship(
        "Website",
        back_populates="analysis",
    )
