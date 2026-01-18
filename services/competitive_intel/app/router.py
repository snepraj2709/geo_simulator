"""
FastAPI router for Competitive Substitution Engine.

Endpoints:
- POST /analyze-substitution/{website_id}
- GET /share-of-voice/{brand_name}
- GET /substitution-patterns
"""

import uuid
from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from shared.db.neo4j_client import get_graph, Neo4jClient
from shared.utils.logging import get_logger

from services.competitive_intel.schemas import (
    LLMProviderEnum,
    ShareOfVoiceRequest,
    ShareOfVoiceResponse,
    SubstitutionAnalysisRequest,
    SubstitutionAnalysisResponse,
    SubstitutionPatternResponse,
    SubstitutionPatternsRequest,
    AnalysisJobResponse,
    BrandMetrics,
    ProviderMetrics,
    SubstituteInfo,
)
from services.competitive_intel.components.graph_queries import GraphQueryBuilder
from services.competitive_intel.components.analysis_engine import (
    AnalysisEngine,
    BrandPresenceData,
    AggregatedMetrics,
)

logger = get_logger(__name__)

router = APIRouter()


async def get_graph_query_builder(
    neo4j: Annotated[Neo4jClient, Depends(get_graph)],
) -> GraphQueryBuilder:
    """Dependency for getting graph query builder."""
    return GraphQueryBuilder(neo4j)


GraphQueryDep = Annotated[GraphQueryBuilder, Depends(get_graph_query_builder)]


@router.post(
    "/analyze-substitution/{website_id}",
    response_model=SubstitutionAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze substitution patterns",
    description="Perform full competitive substitution analysis for a website.",
)
async def analyze_substitution(
    website_id: uuid.UUID,
    request: SubstitutionAnalysisRequest,
    graph_builder: GraphQueryDep,
) -> SubstitutionAnalysisResponse:
    """
    Analyze substitution patterns for a website.

    Performs:
    - Share of voice calculation by LLM provider
    - Substitution pattern detection
    - Competitive gap identification
    - Opportunity scoring
    """
    logger.info(f"Starting substitution analysis for website {website_id}")

    try:
        engine = AnalysisEngine()

        # Determine tracked brand
        tracked_brand = request.tracked_brand_name or "Unknown Brand"

        # Get brand rankings from graph
        llm_provider = None
        if request.llm_providers and LLMProviderEnum.ALL not in request.llm_providers:
            llm_provider = request.llm_providers[0].value

        rankings = await graph_builder.get_brand_rankings(
            website_id=str(website_id),
            llm_provider=llm_provider,
            limit=500,
        )

        if not rankings:
            # Return empty analysis if no data
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
                summary={
                    "total_brands_analyzed": 0,
                    "total_responses_analyzed": 0,
                    "message": "No data available for analysis",
                },
            )

        # Convert to BrandPresenceData
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

            # Track response -> brands mapping
            intent_id = r.get("intent_id", "")
            if intent_id not in response_brands:
                response_brands[intent_id] = []
            response_brands[intent_id].append(r["brand_name"])

            # Track totals by provider
            provider = r["provider"]
            total_by_provider[provider] = total_by_provider.get(provider, 0) + 1

        # Run full analysis
        result = engine.run_full_analysis(
            website_id=website_id,
            tracked_brand=tracked_brand,
            tracked_brand_id=None,
            brand_data=brand_data,
            total_responses_by_provider=total_by_provider,
            response_brands=response_brands,
            period_start=request.period_start,
            period_end=request.period_end,
        )

        logger.info(f"Substitution analysis complete for website {website_id}")
        return result

    except Exception as e:
        logger.error(f"Error in substitution analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}",
        )


@router.get(
    "/share-of-voice/{brand_name}",
    response_model=ShareOfVoiceResponse,
    summary="Get share of voice",
    description="Get share of voice metrics for a specific brand.",
)
async def get_share_of_voice(
    brand_name: str,
    graph_builder: GraphQueryDep,
    llm_provider: LLMProviderEnum | None = Query(default=None),
    include_competitors: bool = Query(default=True),
    top_n_competitors: int = Query(default=10, ge=1, le=50),
) -> ShareOfVoiceResponse:
    """
    Get share of voice metrics for a brand.

    Returns visibility, recommendation rate, and positioning data.
    """
    logger.info(f"Getting share of voice for brand: {brand_name}")

    try:
        provider = llm_provider.value if llm_provider and llm_provider != LLMProviderEnum.ALL else None

        # Get SOV metrics from graph
        sov_data = await graph_builder.get_share_of_voice_metrics(
            brand_name=brand_name,
            llm_provider=provider,
        )

        # Get provider breakdown
        provider_rankings = await graph_builder.get_provider_brand_rankings(brand_name)

        by_provider = [
            ProviderMetrics(
                provider=prov,
                mention_count=metrics.get("total_mentions", 0),
                recommendation_count=metrics.get("recommendations", 0),
                first_position_count=metrics.get("first_positions", 0),
                total_responses=metrics.get("total_mentions", 0),
                avg_position=metrics.get("avg_position"),
                visibility_score=0.0,  # Calculated below
                recommendation_rate=0.0,
            )
            for prov, metrics in provider_rankings.items()
        ]

        # Calculate visibility scores
        for pm in by_provider:
            if pm.total_responses > 0:
                pm.visibility_score = round(pm.mention_count / pm.total_responses * 100, 2)
                if pm.mention_count > 0:
                    pm.recommendation_rate = round(pm.recommendation_count / pm.mention_count * 100, 2)

        # Build overall metrics
        total_mentions = sov_data.get("total_mentions", 0)
        total_responses = total_mentions  # Approximation
        recommendations = sov_data.get("recommendations", 0)
        first_positions = sov_data.get("first_positions", 0)
        avg_position = sov_data.get("avg_position")

        visibility_score = (total_mentions / total_responses * 100) if total_responses > 0 else 0.0
        recommendation_rate = (recommendations / total_mentions * 100) if total_mentions > 0 else 0.0

        overall = BrandMetrics(
            brand_name=brand_name,
            normalized_name=brand_name.lower().strip(),
            mention_count=total_mentions,
            recommendation_count=recommendations,
            first_position_count=first_positions,
            total_responses=total_responses,
            avg_position=avg_position,
            visibility_score=round(visibility_score, 2),
            trust_score=0.0,  # Would need additional data
            recommendation_rate=round(recommendation_rate, 2),
            share_of_voice=0.0,  # Requires competitive context
        )

        # Get competitors if requested
        competitors = []
        if include_competitors:
            co_mentions = await graph_builder.get_co_mentions(
                brand_name=brand_name,
                llm_provider=provider,
                limit=top_n_competitors,
            )

            for cm in co_mentions:
                comp_sov = await graph_builder.get_share_of_voice_metrics(
                    brand_name=cm.brand_name,
                    llm_provider=provider,
                )
                comp_mentions = comp_sov.get("total_mentions", 0)
                comp_recs = comp_sov.get("recommendations", 0)

                competitors.append(BrandMetrics(
                    brand_name=cm.brand_name,
                    normalized_name=cm.normalized_name,
                    mention_count=comp_mentions,
                    recommendation_count=comp_recs,
                    first_position_count=comp_sov.get("first_positions", 0),
                    total_responses=comp_mentions,
                    avg_position=comp_sov.get("avg_position"),
                    visibility_score=round(comp_mentions / total_responses * 100, 2) if total_responses > 0 else 0.0,
                    recommendation_rate=round(comp_recs / comp_mentions * 100, 2) if comp_mentions > 0 else 0.0,
                ))

        return ShareOfVoiceResponse(
            brand_name=brand_name,
            overall_metrics=overall,
            by_provider=by_provider,
            competitors=competitors[:top_n_competitors],
        )

    except Exception as e:
        logger.error(f"Error getting share of voice: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get share of voice: {str(e)}",
        )


@router.get(
    "/substitution-patterns",
    response_model=list[SubstitutionPatternResponse],
    summary="Get substitution patterns",
    description="Get substitution patterns showing which brands appear when others are absent.",
)
async def get_substitution_patterns(
    graph_builder: GraphQueryDep,
    brand_name: str | None = Query(default=None, description="Filter by missing brand"),
    llm_provider: LLMProviderEnum | None = Query(default=None),
    min_count: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[SubstitutionPatternResponse]:
    """
    Get substitution patterns from the knowledge graph.

    Returns patterns showing which brands appear when the target brand is ignored.
    """
    logger.info(f"Getting substitution patterns, brand={brand_name}")

    try:
        provider = llm_provider.value if llm_provider and llm_provider != LLMProviderEnum.ALL else None

        patterns = await graph_builder.get_substitution_patterns(
            missing_brand=brand_name,
            llm_provider=provider,
            limit=limit * 2,  # Get more to filter
        )

        # Group by missing brand
        grouped: dict[str, list] = {}
        for p in patterns:
            if p.occurrence_count >= min_count:
                if p.missing_brand not in grouped:
                    grouped[p.missing_brand] = []
                grouped[p.missing_brand].append(p)

        # Build responses
        results = []
        for missing_brand, subs in list(grouped.items())[:limit]:
            substitutes = [
                SubstituteInfo(
                    brand_name=s.substitute_brand,
                    normalized_name=s.substitute_brand.lower().strip(),
                    occurrence_count=s.occurrence_count,
                    avg_position=s.avg_position,
                    providers=s.providers,
                    substitution_rate=0.0,  # Would need total to calculate
                )
                for s in subs
            ]

            # Calculate substitution rates
            total = sum(s.occurrence_count for s in substitutes)
            for sub in substitutes:
                sub.substitution_rate = round(sub.occurrence_count / total * 100, 2) if total > 0 else 0.0

            results.append(SubstitutionPatternResponse(
                missing_brand_name=missing_brand,
                total_absence_count=total,
                substitutes=substitutes,
                top_substitute=substitutes[0] if substitutes else None,
            ))

        return results

    except Exception as e:
        logger.error(f"Error getting substitution patterns: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get substitution patterns: {str(e)}",
        )
