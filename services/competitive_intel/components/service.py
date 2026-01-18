"""
Competitive Intelligence Service Layer.

Orchestrates analysis engine, graph queries, and persistence
to provide complete competitive analysis capabilities.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from shared.utils.logging import get_logger
from shared.db.neo4j_client import Neo4jClient

from services.competitive_intel.schemas import (
    ShareOfVoiceResponse,
    SubstitutionAnalysisResponse,
    SubstitutionPatternResponse,
    BrandMetrics,
    ProviderMetrics,
    SubstituteInfo,
    ShareOfVoiceCreate,
    SubstitutionPatternCreate,
)
from services.competitive_intel.components.analysis_engine import (
    AnalysisEngine,
    BrandPresenceData,
)
from services.competitive_intel.components.graph_queries import GraphQueryBuilder
from services.competitive_intel.components.repository import CompetitiveIntelRepository

logger = get_logger(__name__)


class CompetitiveIntelService:
    """
    Competitive Intelligence Service.

    Orchestrates:
    - Analysis engine execution
    - Graph query integration
    - PostgreSQL persistence
    - Response normalization across LLM providers
    """

    def __init__(
        self,
        db_session: AsyncSession,
        neo4j_client: Neo4jClient,
    ):
        """
        Initialize service with dependencies.

        Args:
            db_session: SQLAlchemy async session.
            neo4j_client: Neo4j client instance.
        """
        self.db = db_session
        self.repository = CompetitiveIntelRepository(db_session)
        self.graph_builder = GraphQueryBuilder(neo4j_client)
        self.engine = AnalysisEngine()

    async def analyze_website_substitution(
        self,
        website_id: uuid.UUID,
        tracked_brand_name: str | None = None,
        llm_provider: str | None = None,
        period_start: date | None = None,
        period_end: date | None = None,
    ) -> SubstitutionAnalysisResponse:
        """
        Perform full substitution analysis for a website.

        Args:
            website_id: Website UUID.
            tracked_brand_name: Primary brand to track.
            llm_provider: Optional provider filter.
            period_start: Analysis period start.
            period_end: Analysis period end.

        Returns:
            Complete SubstitutionAnalysisResponse.
        """
        logger.info(f"Running substitution analysis for website {website_id}")

        # Get tracked brand from DB if not provided
        if not tracked_brand_name:
            tracked_brand = await self.repository.get_tracked_brand(website_id)
            tracked_brand_name = tracked_brand.name if tracked_brand else "Unknown"

        # Get brand rankings from graph
        rankings = await self.graph_builder.get_brand_rankings(
            website_id=str(website_id),
            llm_provider=llm_provider,
            limit=500,
        )

        if not rankings:
            return self._empty_analysis_response(website_id, tracked_brand_name)

        # Convert to analysis format
        brand_data, response_brands, total_by_provider = self._convert_rankings(rankings)

        # Run analysis
        result = self.engine.run_full_analysis(
            website_id=website_id,
            tracked_brand=tracked_brand_name,
            tracked_brand_id=None,
            brand_data=brand_data,
            total_responses_by_provider=total_by_provider,
            response_brands=response_brands,
            period_start=period_start,
            period_end=period_end,
        )

        # Persist results
        await self._persist_analysis_results(
            website_id=website_id,
            result=result,
            period_start=period_start or date.today(),
            period_end=period_end or date.today(),
        )

        await self.db.commit()

        logger.info(f"Substitution analysis complete for website {website_id}")
        return result

    async def get_brand_share_of_voice(
        self,
        brand_name: str,
        llm_provider: str | None = None,
        include_competitors: bool = True,
        top_n: int = 10,
    ) -> ShareOfVoiceResponse:
        """
        Get share of voice for a specific brand.

        Args:
            brand_name: Brand name to analyze.
            llm_provider: Optional provider filter.
            include_competitors: Include competitor data.
            top_n: Number of competitors to include.

        Returns:
            ShareOfVoiceResponse with metrics.
        """
        # Get SOV from graph
        sov_data = await self.graph_builder.get_share_of_voice_metrics(
            brand_name=brand_name,
            llm_provider=llm_provider,
        )

        # Get provider breakdown
        provider_rankings = await self.graph_builder.get_provider_brand_rankings(brand_name)

        by_provider = self._build_provider_metrics(provider_rankings)

        overall = self._build_brand_metrics(brand_name, sov_data)

        competitors = []
        if include_competitors:
            competitors = await self._get_competitor_metrics(
                brand_name=brand_name,
                llm_provider=llm_provider,
                limit=top_n,
            )

        return ShareOfVoiceResponse(
            brand_name=brand_name,
            overall_metrics=overall,
            by_provider=by_provider,
            competitors=competitors,
        )

    async def get_substitution_patterns(
        self,
        brand_name: str | None = None,
        llm_provider: str | None = None,
        min_count: int = 1,
        limit: int = 20,
    ) -> list[SubstitutionPatternResponse]:
        """
        Get substitution patterns from graph.

        Args:
            brand_name: Optional missing brand filter.
            llm_provider: Optional provider filter.
            min_count: Minimum occurrence count.
            limit: Maximum results.

        Returns:
            List of SubstitutionPatternResponse.
        """
        patterns = await self.graph_builder.get_substitution_patterns(
            missing_brand=brand_name,
            llm_provider=llm_provider,
            limit=limit * 2,
        )

        # Group and filter
        grouped: dict[str, list] = {}
        for p in patterns:
            if p.occurrence_count >= min_count:
                if p.missing_brand not in grouped:
                    grouped[p.missing_brand] = []
                grouped[p.missing_brand].append(p)

        # Build responses
        results = []
        for missing, subs in list(grouped.items())[:limit]:
            substitutes = [
                SubstituteInfo(
                    brand_name=s.substitute_brand,
                    normalized_name=s.substitute_brand.lower().strip(),
                    occurrence_count=s.occurrence_count,
                    avg_position=s.avg_position,
                    providers=s.providers,
                )
                for s in subs
            ]

            total = sum(s.occurrence_count for s in substitutes)
            for sub in substitutes:
                sub.substitution_rate = round(sub.occurrence_count / total * 100, 2) if total > 0 else 0.0

            results.append(SubstitutionPatternResponse(
                missing_brand_name=missing,
                total_absence_count=total,
                substitutes=substitutes,
                top_substitute=substitutes[0] if substitutes else None,
            ))

        return results

    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================

    def _convert_rankings(
        self,
        rankings: list[dict],
    ) -> tuple[list[BrandPresenceData], dict[str, list[str]], dict[str, int]]:
        """Convert graph rankings to analysis format."""
        brand_data = []
        response_brands: dict[str, list[str]] = {}
        total_by_provider: dict[str, int] = {}

        for r in rankings:
            brand_data.append(BrandPresenceData(
                brand_id=uuid.UUID(r["brand_id"]) if r.get("brand_id") else None,
                brand_name=r["brand_name"],
                normalized_name=r["normalized_name"],
                llm_provider=r["provider"],
                presence=r["presence"],
                position_rank=r.get("position"),
                response_id=r.get("intent_id"),
            ))

            intent_id = r.get("intent_id", "")
            if intent_id not in response_brands:
                response_brands[intent_id] = []
            response_brands[intent_id].append(r["brand_name"])

            provider = r["provider"]
            total_by_provider[provider] = total_by_provider.get(provider, 0) + 1

        return brand_data, response_brands, total_by_provider

    def _empty_analysis_response(
        self,
        website_id: uuid.UUID,
        tracked_brand: str,
    ) -> SubstitutionAnalysisResponse:
        """Create empty analysis response."""
        return SubstitutionAnalysisResponse(
            website_id=website_id,
            tracked_brand=tracked_brand,
            share_of_voice=ShareOfVoiceResponse(
                brand_name=tracked_brand,
                overall_metrics=BrandMetrics(
                    brand_name=tracked_brand,
                    normalized_name=tracked_brand.lower().strip(),
                ),
            ),
            summary={"message": "No data available"},
        )

    def _build_provider_metrics(
        self,
        provider_rankings: dict[str, dict],
    ) -> list[ProviderMetrics]:
        """Build provider metrics list."""
        result = []
        for prov, metrics in provider_rankings.items():
            total = metrics.get("total_mentions", 0)
            mentions = metrics.get("total_mentions", 0)
            recs = metrics.get("recommendations", 0)

            result.append(ProviderMetrics(
                provider=prov,
                mention_count=mentions,
                recommendation_count=recs,
                first_position_count=metrics.get("first_positions", 0),
                total_responses=total,
                avg_position=metrics.get("avg_position"),
                visibility_score=round(mentions / total * 100, 2) if total > 0 else 0.0,
                recommendation_rate=round(recs / mentions * 100, 2) if mentions > 0 else 0.0,
            ))

        return result

    def _build_brand_metrics(
        self,
        brand_name: str,
        sov_data: dict,
    ) -> BrandMetrics:
        """Build brand metrics from SOV data."""
        mentions = sov_data.get("total_mentions", 0)
        recs = sov_data.get("recommendations", 0)

        return BrandMetrics(
            brand_name=brand_name,
            normalized_name=brand_name.lower().strip(),
            mention_count=mentions,
            recommendation_count=recs,
            first_position_count=sov_data.get("first_positions", 0),
            total_responses=mentions,
            avg_position=sov_data.get("avg_position"),
            visibility_score=round(mentions / mentions * 100, 2) if mentions > 0 else 0.0,
            recommendation_rate=round(recs / mentions * 100, 2) if mentions > 0 else 0.0,
        )

    async def _get_competitor_metrics(
        self,
        brand_name: str,
        llm_provider: str | None,
        limit: int,
    ) -> list[BrandMetrics]:
        """Get competitor metrics."""
        co_mentions = await self.graph_builder.get_co_mentions(
            brand_name=brand_name,
            llm_provider=llm_provider,
            limit=limit,
        )

        competitors = []
        for cm in co_mentions:
            sov = await self.graph_builder.get_share_of_voice_metrics(
                brand_name=cm.brand_name,
                llm_provider=llm_provider,
            )
            competitors.append(self._build_brand_metrics(cm.brand_name, sov))

        return competitors

    async def _persist_analysis_results(
        self,
        website_id: uuid.UUID,
        result: SubstitutionAnalysisResponse,
        period_start: date,
        period_end: date,
    ) -> None:
        """Persist analysis results to PostgreSQL."""
        # Get or create tracked brand
        tracked_brand = await self.repository.get_or_create_brand(result.tracked_brand)

        # Persist share of voice
        for pm in result.share_of_voice.by_provider:
            await self.repository.upsert_share_of_voice(ShareOfVoiceCreate(
                website_id=website_id,
                brand_id=tracked_brand.id,
                llm_provider=pm.provider,
                mention_count=pm.mention_count,
                recommendation_count=pm.recommendation_count,
                first_position_count=pm.first_position_count,
                total_responses=pm.total_responses,
                visibility_score=Decimal(str(pm.visibility_score)),
                recommendation_rate=Decimal(str(pm.recommendation_rate)),
                period_start=period_start,
                period_end=period_end,
            ))

        # Persist substitution patterns
        for sub in result.brands_substituting_tracked[:20]:
            substitute_brand = await self.repository.get_or_create_brand(sub.brand_name)
            await self.repository.upsert_substitution_pattern(SubstitutionPatternCreate(
                website_id=website_id,
                missing_brand_id=tracked_brand.id,
                substitute_brand_id=substitute_brand.id,
                occurrence_count=sub.occurrence_count,
                avg_position=Decimal(str(sub.avg_position)) if sub.avg_position else None,
                period_start=period_start,
                period_end=period_end,
            ))
