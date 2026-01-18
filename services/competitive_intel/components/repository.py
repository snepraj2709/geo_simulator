"""
PostgreSQL Repository for Competitive Analysis.

Handles persistence of:
- Share of Voice metrics
- Substitution patterns
- Competitor relationships
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from shared.utils.logging import get_logger
from shared.models import (
    ShareOfVoice,
    SubstitutionPattern,
    CompetitorRelationship,
    Brand,
)

from services.competitive_intel.schemas import (
    ShareOfVoiceCreate,
    SubstitutionPatternCreate,
    CompetitorRelationshipCreate,
)

logger = get_logger(__name__)


class CompetitiveIntelRepository:
    """
    Repository for competitive intelligence data persistence.

    Provides CRUD operations for share of voice, substitution patterns,
    and competitor relationships.
    """

    def __init__(self, session: AsyncSession):
        """Initialize with database session."""
        self.session = session

    # =========================================================================
    # SHARE OF VOICE
    # =========================================================================

    async def upsert_share_of_voice(
        self,
        data: ShareOfVoiceCreate,
    ) -> ShareOfVoice:
        """
        Insert or update share of voice record.

        Args:
            data: Share of voice data.

        Returns:
            ShareOfVoice model instance.
        """
        # Check for existing record
        result = await self.session.execute(
            select(ShareOfVoice).where(
                and_(
                    ShareOfVoice.website_id == data.website_id,
                    ShareOfVoice.brand_id == data.brand_id,
                    ShareOfVoice.llm_provider == data.llm_provider,
                    ShareOfVoice.period_start == data.period_start,
                    ShareOfVoice.period_end == data.period_end,
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing
            existing.mention_count = data.mention_count
            existing.recommendation_count = data.recommendation_count
            existing.first_position_count = data.first_position_count
            existing.total_responses = data.total_responses
            existing.visibility_score = data.visibility_score
            existing.trust_score = data.trust_score
            existing.recommendation_rate = data.recommendation_rate
            return existing
        else:
            # Create new
            sov = ShareOfVoice(
                website_id=data.website_id,
                brand_id=data.brand_id,
                llm_provider=data.llm_provider,
                mention_count=data.mention_count,
                recommendation_count=data.recommendation_count,
                first_position_count=data.first_position_count,
                total_responses=data.total_responses,
                visibility_score=data.visibility_score,
                trust_score=data.trust_score,
                recommendation_rate=data.recommendation_rate,
                period_start=data.period_start,
                period_end=data.period_end,
            )
            self.session.add(sov)
            return sov

    async def get_share_of_voice(
        self,
        website_id: uuid.UUID,
        brand_id: uuid.UUID | None = None,
        llm_provider: str | None = None,
        period_start: date | None = None,
        period_end: date | None = None,
    ) -> list[ShareOfVoice]:
        """
        Get share of voice records with filtering.

        Args:
            website_id: Website UUID.
            brand_id: Optional brand filter.
            llm_provider: Optional provider filter.
            period_start: Optional period start filter.
            period_end: Optional period end filter.

        Returns:
            List of ShareOfVoice records.
        """
        query = select(ShareOfVoice).where(ShareOfVoice.website_id == website_id)

        if brand_id:
            query = query.where(ShareOfVoice.brand_id == brand_id)
        if llm_provider:
            query = query.where(ShareOfVoice.llm_provider == llm_provider)
        if period_start:
            query = query.where(ShareOfVoice.period_start >= period_start)
        if period_end:
            query = query.where(ShareOfVoice.period_end <= period_end)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_brand_sov_by_provider(
        self,
        website_id: uuid.UUID,
        brand_id: uuid.UUID,
    ) -> dict[str, dict[str, Any]]:
        """Get share of voice for a brand grouped by provider."""
        records = await self.get_share_of_voice(
            website_id=website_id,
            brand_id=brand_id,
        )

        result = {}
        for r in records:
            result[r.llm_provider] = {
                "mention_count": r.mention_count,
                "recommendation_count": r.recommendation_count,
                "first_position_count": r.first_position_count,
                "visibility_score": float(r.visibility_score) if r.visibility_score else 0.0,
                "trust_score": float(r.trust_score) if r.trust_score else 0.0,
                "recommendation_rate": float(r.recommendation_rate) if r.recommendation_rate else 0.0,
            }

        return result

    # =========================================================================
    # SUBSTITUTION PATTERNS
    # =========================================================================

    async def upsert_substitution_pattern(
        self,
        data: SubstitutionPatternCreate,
    ) -> SubstitutionPattern:
        """
        Insert or update substitution pattern.

        Args:
            data: Substitution pattern data.

        Returns:
            SubstitutionPattern model instance.
        """
        # Check for existing
        query = select(SubstitutionPattern).where(
            and_(
                SubstitutionPattern.website_id == data.website_id,
                SubstitutionPattern.missing_brand_id == data.missing_brand_id,
                SubstitutionPattern.substitute_brand_id == data.substitute_brand_id,
            )
        )
        if data.llm_provider:
            query = query.where(SubstitutionPattern.llm_provider == data.llm_provider)

        result = await self.session.execute(query)
        existing = result.scalar_one_or_none()

        if existing:
            existing.occurrence_count = data.occurrence_count
            existing.avg_position = data.avg_position
            existing.updated_at = datetime.utcnow()
            return existing
        else:
            pattern = SubstitutionPattern(
                website_id=data.website_id,
                missing_brand_id=data.missing_brand_id,
                substitute_brand_id=data.substitute_brand_id,
                occurrence_count=data.occurrence_count,
                avg_position=data.avg_position,
                llm_provider=data.llm_provider,
                period_start=data.period_start,
                period_end=data.period_end,
            )
            self.session.add(pattern)
            return pattern

    async def get_substitution_patterns(
        self,
        website_id: uuid.UUID,
        missing_brand_id: uuid.UUID | None = None,
        llm_provider: str | None = None,
        min_count: int = 1,
        limit: int = 50,
    ) -> list[SubstitutionPattern]:
        """
        Get substitution patterns with filtering.

        Args:
            website_id: Website UUID.
            missing_brand_id: Optional missing brand filter.
            llm_provider: Optional provider filter.
            min_count: Minimum occurrence count.
            limit: Maximum results.

        Returns:
            List of SubstitutionPattern records.
        """
        query = select(SubstitutionPattern).where(
            and_(
                SubstitutionPattern.website_id == website_id,
                SubstitutionPattern.occurrence_count >= min_count,
            )
        )

        if missing_brand_id:
            query = query.where(SubstitutionPattern.missing_brand_id == missing_brand_id)
        if llm_provider:
            query = query.where(SubstitutionPattern.llm_provider == llm_provider)

        query = query.order_by(SubstitutionPattern.occurrence_count.desc()).limit(limit)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    # =========================================================================
    # COMPETITOR RELATIONSHIPS
    # =========================================================================

    async def create_competitor_relationship(
        self,
        data: CompetitorRelationshipCreate,
    ) -> CompetitorRelationship:
        """Create a competitor relationship."""
        rel = CompetitorRelationship(
            website_id=data.website_id,
            primary_brand_id=data.primary_brand_id,
            competitor_brand_id=data.competitor_brand_id,
            relationship_type=data.relationship_type.value if data.relationship_type else None,
        )
        self.session.add(rel)
        return rel

    async def get_competitors(
        self,
        website_id: uuid.UUID,
        brand_id: uuid.UUID,
    ) -> list[CompetitorRelationship]:
        """Get competitors for a brand."""
        result = await self.session.execute(
            select(CompetitorRelationship).where(
                and_(
                    CompetitorRelationship.website_id == website_id,
                    CompetitorRelationship.primary_brand_id == brand_id,
                )
            )
        )
        return list(result.scalars().all())

    # =========================================================================
    # BRAND LOOKUPS
    # =========================================================================

    async def get_or_create_brand(
        self,
        name: str,
        domain: str | None = None,
    ) -> Brand:
        """Get or create a brand by name."""
        normalized = name.lower().strip()

        result = await self.session.execute(
            select(Brand).where(Brand.normalized_name == normalized)
        )
        brand = result.scalar_one_or_none()

        if brand:
            return brand

        brand = Brand(
            name=name,
            normalized_name=normalized,
            domain=domain,
        )
        self.session.add(brand)
        return brand

    async def get_tracked_brand(
        self,
        website_id: uuid.UUID,
    ) -> Brand | None:
        """Get the tracked brand for a website."""
        result = await self.session.execute(
            select(Brand).where(Brand.is_tracked == True).limit(1)
        )
        return result.scalar_one_or_none()
