"""
Neo4j Graph Queries for Competitive Analysis.

Provides graph query utilities for:
- Co-mention analysis
- Substitution pattern detection
- Competitive relationship queries
- Share of voice from graph data
"""

from typing import Any
import uuid

from shared.utils.logging import get_logger
from shared.db.neo4j_client import Neo4jClient

from services.competitive_intel.schemas import (
    GraphCoMention,
    GraphSubstitution,
)

logger = get_logger(__name__)


class GraphQueryBuilder:
    """
    Builds and executes Neo4j queries for competitive analysis.

    Leverages the knowledge graph for:
    - Brand co-occurrence patterns
    - Substitution detection via IGNORES relationships
    - Competitive landscape mapping
    """

    def __init__(self, neo4j_client: Neo4jClient):
        """
        Initialize GraphQueryBuilder.

        Args:
            neo4j_client: Neo4j client instance.
        """
        self.client = neo4j_client

    # =========================================================================
    # SHARE OF VOICE QUERIES
    # =========================================================================

    async def get_brand_rankings(
        self,
        website_id: str | None = None,
        llm_provider: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get brand rankings from the graph.

        Args:
            website_id: Optional website filter.
            llm_provider: Optional provider filter.
            limit: Maximum results.

        Returns:
            List of brand ranking data.
        """
        query = """
        MATCH (b:Brand)-[r:RANKS_FOR]->(i:Intent)
        WHERE ($llm_provider IS NULL OR r.llm_provider = $llm_provider)
        WITH b.name as brand_name,
             b.normalized_name as normalized_name,
             b.id as brand_id,
             r.llm_provider as provider,
             r.presence as presence,
             r.position as position,
             i.id as intent_id
        RETURN brand_name, normalized_name, brand_id, provider, presence, position, intent_id
        LIMIT $limit
        """

        result = await self.client.run_query(
            query,
            {"llm_provider": llm_provider, "limit": limit}
        )

        return result

    async def get_share_of_voice_metrics(
        self,
        brand_name: str,
        llm_provider: str | None = None,
    ) -> dict[str, Any]:
        """
        Get share of voice metrics for a brand from the graph.

        Args:
            brand_name: Brand name to analyze.
            llm_provider: Optional provider filter.

        Returns:
            SOV metrics dictionary.
        """
        query = """
        MATCH (b:Brand {normalized_name: $normalized_name})-[r:RANKS_FOR]->(i:Intent)
        WHERE ($llm_provider IS NULL OR r.llm_provider = $llm_provider)
        WITH b,
             count(r) as total_mentions,
             sum(CASE WHEN r.position = 1 THEN 1 ELSE 0 END) as first_positions,
             sum(CASE WHEN r.presence = 'recommended' THEN 1 ELSE 0 END) as recommendations,
             avg(r.position) as avg_position,
             collect(DISTINCT r.llm_provider) as providers
        RETURN b.name as brand_name,
               b.id as brand_id,
               total_mentions,
               first_positions,
               recommendations,
               avg_position,
               providers
        """

        result = await self.client.run_query_single(
            query,
            {
                "normalized_name": brand_name.lower().strip(),
                "llm_provider": llm_provider,
            }
        )

        if not result:
            return {
                "brand_name": brand_name,
                "total_mentions": 0,
                "first_positions": 0,
                "recommendations": 0,
                "avg_position": None,
                "providers": [],
            }

        return result

    async def get_competitive_sov(
        self,
        brand_names: list[str],
        llm_provider: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get comparative share of voice for multiple brands.

        Args:
            brand_names: List of brand names to compare.
            llm_provider: Optional provider filter.

        Returns:
            List of SOV data for each brand.
        """
        query = """
        MATCH (b:Brand)-[r:RANKS_FOR]->(i:Intent)
        WHERE b.normalized_name IN $normalized_names
        AND ($llm_provider IS NULL OR r.llm_provider = $llm_provider)
        WITH b.name as brand_name,
             b.normalized_name as normalized_name,
             count(r) as total_mentions,
             sum(CASE WHEN r.position = 1 THEN 1 ELSE 0 END) as first_positions,
             sum(CASE WHEN r.presence = 'recommended' THEN 1 ELSE 0 END) as recommendations,
             avg(r.position) as avg_position
        RETURN brand_name, normalized_name, total_mentions, first_positions, recommendations, avg_position
        ORDER BY total_mentions DESC
        """

        normalized_names = [n.lower().strip() for n in brand_names]

        return await self.client.run_query(
            query,
            {"normalized_names": normalized_names, "llm_provider": llm_provider}
        )

    # =========================================================================
    # CO-MENTION QUERIES
    # =========================================================================

    async def get_co_mentions(
        self,
        brand_name: str,
        llm_provider: str | None = None,
        limit: int = 20,
    ) -> list[GraphCoMention]:
        """
        Get brands co-mentioned with target brand.

        Args:
            brand_name: Target brand name.
            llm_provider: Optional provider filter.
            limit: Maximum results.

        Returns:
            List of co-mentioned brands.
        """
        query = """
        MATCH (target:Brand {normalized_name: $normalized_name})-[r:CO_MENTIONED]-(other:Brand)
        WHERE $llm_provider IS NULL OR r.llm_provider = $llm_provider
        WITH other.name as brand_name,
             other.normalized_name as normalized_name,
             sum(r.count) as co_mention_count,
             avg(r.avg_position_delta) as avg_position_delta,
             collect(DISTINCT r.llm_provider) as providers
        RETURN brand_name, normalized_name, co_mention_count, avg_position_delta, providers
        ORDER BY co_mention_count DESC
        LIMIT $limit
        """

        result = await self.client.run_query(
            query,
            {
                "normalized_name": brand_name.lower().strip(),
                "llm_provider": llm_provider,
                "limit": limit,
            }
        )

        return [
            GraphCoMention(
                brand_name=r["brand_name"],
                normalized_name=r["normalized_name"],
                co_mention_count=r["co_mention_count"],
                avg_position_delta=r["avg_position_delta"],
                providers=r["providers"] or [],
            )
            for r in result
        ]

    async def get_co_mention_pairs(
        self,
        llm_provider: str | None = None,
        min_count: int = 2,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get all significant co-mention pairs.

        Args:
            llm_provider: Optional provider filter.
            min_count: Minimum co-mention count.
            limit: Maximum results.

        Returns:
            List of co-mention pairs with counts.
        """
        query = """
        MATCH (a:Brand)-[r:CO_MENTIONED]->(b:Brand)
        WHERE r.count >= $min_count
        AND ($llm_provider IS NULL OR r.llm_provider = $llm_provider)
        RETURN a.name as brand_a,
               a.normalized_name as norm_a,
               b.name as brand_b,
               b.normalized_name as norm_b,
               r.count as count,
               r.avg_position_delta as position_delta,
               r.llm_provider as provider
        ORDER BY r.count DESC
        LIMIT $limit
        """

        return await self.client.run_query(
            query,
            {
                "llm_provider": llm_provider,
                "min_count": min_count,
                "limit": limit,
            }
        )

    # =========================================================================
    # SUBSTITUTION QUERIES
    # =========================================================================

    async def get_substitution_patterns(
        self,
        missing_brand: str | None = None,
        llm_provider: str | None = None,
        limit: int = 50,
    ) -> list[GraphSubstitution]:
        """
        Get substitution patterns from graph.

        Finds brands that appear when another brand is ignored.

        Args:
            missing_brand: Optional specific brand to analyze.
            llm_provider: Optional provider filter.
            limit: Maximum results.

        Returns:
            List of substitution patterns.
        """
        query = """
        // Find intents where a brand was ignored
        MATCH (llm:LLMProvider)-[ignore:IGNORES]->(missing:Brand)
        WHERE ($missing_brand IS NULL OR missing.normalized_name = $missing_brand)
        AND ($llm_provider IS NULL OR llm.name = $llm_provider)

        // Find brands recommended for the same intent
        MATCH (llm)-[rec:RECOMMENDS]->(substitute:Brand)
        WHERE rec.intent_id = ignore.intent_id
        AND substitute.normalized_name <> missing.normalized_name

        WITH missing.name as missing_brand,
             substitute.name as substitute_brand,
             count(*) as occurrence_count,
             avg(rec.position) as avg_position,
             collect(DISTINCT llm.name) as providers

        RETURN missing_brand, substitute_brand, occurrence_count, avg_position, providers
        ORDER BY occurrence_count DESC
        LIMIT $limit
        """

        result = await self.client.run_query(
            query,
            {
                "missing_brand": missing_brand.lower().strip() if missing_brand else None,
                "llm_provider": llm_provider,
                "limit": limit,
            }
        )

        return [
            GraphSubstitution(
                missing_brand=r["missing_brand"],
                substitute_brand=r["substitute_brand"],
                occurrence_count=r["occurrence_count"],
                avg_position=r["avg_position"],
                providers=r["providers"] or [],
            )
            for r in result
        ]

    async def get_brands_replacing(
        self,
        brand_name: str,
        llm_provider: str | None = None,
        limit: int = 20,
    ) -> list[GraphSubstitution]:
        """
        Get brands that replace the target brand when it's ignored.

        Args:
            brand_name: The brand being replaced.
            llm_provider: Optional provider filter.
            limit: Maximum results.

        Returns:
            List of substitute brands.
        """
        return await self.get_substitution_patterns(
            missing_brand=brand_name,
            llm_provider=llm_provider,
            limit=limit,
        )

    async def get_brands_replaced_by(
        self,
        brand_name: str,
        llm_provider: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Get brands that the target brand replaces.

        Args:
            brand_name: The substitute brand.
            llm_provider: Optional provider filter.
            limit: Maximum results.

        Returns:
            List of brands being replaced.
        """
        query = """
        // Find intents where brands were ignored
        MATCH (llm:LLMProvider)-[ignore:IGNORES]->(missing:Brand)
        WHERE ($llm_provider IS NULL OR llm.name = $llm_provider)

        // Find where target brand was recommended instead
        MATCH (llm)-[rec:RECOMMENDS]->(sub:Brand {normalized_name: $substitute_brand})
        WHERE rec.intent_id = ignore.intent_id

        WITH missing.name as replaced_brand,
             missing.normalized_name as normalized_name,
             count(*) as replacement_count,
             avg(rec.position) as avg_position,
             collect(DISTINCT llm.name) as providers

        RETURN replaced_brand, normalized_name, replacement_count, avg_position, providers
        ORDER BY replacement_count DESC
        LIMIT $limit
        """

        return await self.client.run_query(
            query,
            {
                "substitute_brand": brand_name.lower().strip(),
                "llm_provider": llm_provider,
                "limit": limit,
            }
        )

    # =========================================================================
    # COMPETITIVE RELATIONSHIP QUERIES
    # =========================================================================

    async def get_competitors(
        self,
        brand_name: str,
        include_indirect: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Get competitors for a brand from graph.

        Args:
            brand_name: Target brand name.
            include_indirect: Include indirect competitors.

        Returns:
            List of competitor data.
        """
        query = """
        MATCH (b:Brand {normalized_name: $normalized_name})-[r:COMPETES_WITH]->(c:Brand)
        WHERE $include_indirect OR r.relationship_type = 'direct'
        RETURN c.name as competitor_name,
               c.normalized_name as normalized_name,
               c.id as competitor_id,
               r.relationship_type as relationship_type
        """

        return await self.client.run_query(
            query,
            {
                "normalized_name": brand_name.lower().strip(),
                "include_indirect": include_indirect,
            }
        )

    async def get_competitive_landscape(
        self,
        brand_name: str,
        llm_provider: str | None = None,
    ) -> dict[str, Any]:
        """
        Get full competitive landscape for a brand.

        Args:
            brand_name: Target brand.
            llm_provider: Optional provider filter.

        Returns:
            Competitive landscape data.
        """
        # Get SOV
        sov = await self.get_share_of_voice_metrics(brand_name, llm_provider)

        # Get competitors
        competitors = await self.get_competitors(brand_name)

        # Get SOV for competitors
        competitor_names = [c["competitor_name"] for c in competitors]
        competitor_sov = []
        if competitor_names:
            competitor_sov = await self.get_competitive_sov(competitor_names, llm_provider)

        # Get co-mentions
        co_mentions = await self.get_co_mentions(brand_name, llm_provider, limit=10)

        # Get substitution patterns
        substitutes = await self.get_brands_replacing(brand_name, llm_provider, limit=10)

        return {
            "brand_name": brand_name,
            "share_of_voice": sov,
            "competitors": competitors,
            "competitor_sov": competitor_sov,
            "co_mentions": [cm.model_dump() for cm in co_mentions],
            "substitutes": [s.model_dump() for s in substitutes],
        }

    # =========================================================================
    # INTENT-BASED QUERIES
    # =========================================================================

    async def get_brand_intent_coverage(
        self,
        brand_name: str,
        llm_provider: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get intent coverage for a brand.

        Args:
            brand_name: Target brand.
            llm_provider: Optional provider filter.

        Returns:
            List of intents with brand's coverage.
        """
        query = """
        MATCH (b:Brand {normalized_name: $normalized_name})-[r:RANKS_FOR]->(i:Intent)
        WHERE ($llm_provider IS NULL OR r.llm_provider = $llm_provider)
        RETURN i.id as intent_id,
               i.intent_type as intent_type,
               i.funnel_stage as funnel_stage,
               i.buying_signal as buying_signal,
               r.position as position,
               r.presence as presence,
               r.llm_provider as provider
        ORDER BY r.position
        """

        return await self.client.run_query(
            query,
            {
                "normalized_name": brand_name.lower().strip(),
                "llm_provider": llm_provider,
            }
        )

    async def get_intent_brand_distribution(
        self,
        intent_id: str,
        llm_provider: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get brand distribution for a specific intent.

        Args:
            intent_id: Intent UUID.
            llm_provider: Optional provider filter.

        Returns:
            List of brands and their rankings for the intent.
        """
        query = """
        MATCH (b:Brand)-[r:RANKS_FOR]->(i:Intent {id: $intent_id})
        WHERE ($llm_provider IS NULL OR r.llm_provider = $llm_provider)
        RETURN b.name as brand_name,
               b.normalized_name as normalized_name,
               r.position as position,
               r.presence as presence,
               r.llm_provider as provider
        ORDER BY r.position
        """

        return await self.client.run_query(
            query,
            {"intent_id": intent_id, "llm_provider": llm_provider}
        )

    # =========================================================================
    # PROVIDER COMPARISON QUERIES
    # =========================================================================

    async def get_provider_brand_rankings(
        self,
        brand_name: str,
    ) -> dict[str, dict[str, Any]]:
        """
        Get brand rankings across all providers.

        Args:
            brand_name: Target brand.

        Returns:
            Dict mapping provider to ranking metrics.
        """
        query = """
        MATCH (b:Brand {normalized_name: $normalized_name})-[r:RANKS_FOR]->(i:Intent)
        WITH r.llm_provider as provider,
             count(r) as total_mentions,
             sum(CASE WHEN r.position = 1 THEN 1 ELSE 0 END) as first_positions,
             sum(CASE WHEN r.presence = 'recommended' THEN 1 ELSE 0 END) as recommendations,
             avg(r.position) as avg_position
        RETURN provider, total_mentions, first_positions, recommendations, avg_position
        ORDER BY total_mentions DESC
        """

        result = await self.client.run_query(
            query,
            {"normalized_name": brand_name.lower().strip()}
        )

        return {
            r["provider"]: {
                "total_mentions": r["total_mentions"],
                "first_positions": r["first_positions"],
                "recommendations": r["recommendations"],
                "avg_position": r["avg_position"],
            }
            for r in result
        }

    async def get_provider_comparison(
        self,
        brand_names: list[str],
    ) -> dict[str, dict[str, dict[str, Any]]]:
        """
        Compare brand rankings across providers.

        Args:
            brand_names: List of brands to compare.

        Returns:
            Nested dict: brand -> provider -> metrics.
        """
        query = """
        MATCH (b:Brand)-[r:RANKS_FOR]->(i:Intent)
        WHERE b.normalized_name IN $normalized_names
        WITH b.name as brand_name,
             r.llm_provider as provider,
             count(r) as total_mentions,
             sum(CASE WHEN r.position = 1 THEN 1 ELSE 0 END) as first_positions,
             sum(CASE WHEN r.presence = 'recommended' THEN 1 ELSE 0 END) as recommendations,
             avg(r.position) as avg_position
        RETURN brand_name, provider, total_mentions, first_positions, recommendations, avg_position
        ORDER BY brand_name, total_mentions DESC
        """

        normalized_names = [n.lower().strip() for n in brand_names]
        result = await self.client.run_query(
            query,
            {"normalized_names": normalized_names}
        )

        comparison: dict[str, dict[str, dict[str, Any]]] = {}
        for r in result:
            brand = r["brand_name"]
            provider = r["provider"]

            if brand not in comparison:
                comparison[brand] = {}

            comparison[brand][provider] = {
                "total_mentions": r["total_mentions"],
                "first_positions": r["first_positions"],
                "recommendations": r["recommendations"],
                "avg_position": r["avg_position"],
            }

        return comparison
