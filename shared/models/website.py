"""
Website and scraping models.

Websites are the primary entities that users track. Each website
can have scraped pages, analysis results, ICPs, and simulation runs.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
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
    """
    Tracked website model.

    Represents a website being monitored for brand presence in LLM responses.
    Each organization can track multiple websites, but each domain is unique
    within an organization.

    Attributes:
        organization_id: Owner organization
        domain: Website domain (e.g., example.com)
        url: Full URL of the website
        name: Display name for the website
        description: Optional description
        status: pending, scraping, completed, failed
        last_scraped_at: Last time content was scraped
        last_hard_scrape_at: Last full re-scrape (rate limited)
        scrape_depth: How deep to crawl (default 3)
    """

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

    __table_args__ = (
        # Each organization can only have one website per domain
        UniqueConstraint("organization_id", "domain", name="uq_websites_org_domain"),
    )


class ScrapedPage(Base, UUIDMixin):
    """
    Scraped page content model.

    Stores content scraped from website pages. Each page is identified
    by its URL hash to ensure uniqueness within a website.

    Attributes:
        website_id: Parent website reference
        url: Full URL of the page
        url_hash: SHA-256 hash of URL for quick lookup
        title: Page title from <title> tag
        meta_description: Meta description content
        content_text: Extracted text content
        content_html_path: S3 path to full HTML
        word_count: Number of words in content
        page_type: homepage, product, service, blog, about, contact, etc.
        http_status: HTTP status code from scraping
        scraped_at: When the page was scraped
    """

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

    __table_args__ = (
        # Each website can only have one page per URL hash
        UniqueConstraint("website_id", "url_hash", name="uq_scraped_pages_website_url"),
    )


class WebsiteAnalysis(Base, UUIDMixin):
    """
    Website analysis results model.

    Stores the results of AI analysis of website content, including
    industry classification, business model, and competitive landscape.

    Attributes:
        website_id: Parent website (one analysis per website)
        industry: Detected industry (e.g., "SaaS", "E-commerce")
        business_model: b2b, b2c, b2b2c, marketplace
        primary_offerings: List of products/services offered
        value_propositions: Key value propositions identified
        target_markets: Target market segments
        competitors_mentioned: Competitor brands found on the site
        analyzed_at: When analysis was performed
    """

    __tablename__ = "website_analysis"

    website_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("websites.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
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

    # Extended business intelligence fields (JSONB for flexibility)
    company_profile: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    products_detailed: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    services_detailed: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    target_audience: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    technologies_used: Mapped[list[str] | None] = mapped_column(JSONB)
    certifications: Mapped[list[str] | None] = mapped_column(JSONB)
    partnerships: Mapped[list[str] | None] = mapped_column(JSONB)
    named_entities: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Relationships
    website: Mapped["Website"] = relationship(
        "Website",
        back_populates="analysis",
    )
