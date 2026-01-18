"""
Query Builder for Knowledge Graph Builder.

Provides high-level graph query utilities for:
- Belief maps
- Co-mention analysis
- ICP journey mapping
- Substitution patterns
- Competitive analysis
"""

from typing import Any

from shared.utils.logging import get_logger
from shared.db.neo4j_client import Neo4jClient

from services.graph_builder.schemas import (
    BeliefMapResponse,
    CoMentionResponse,
    ICPJourneyResponse,
    SubstitutionPatternResponse,
    IntentTypeEnum,
)

logger = get_logger(__name__)


class QueryBuilder:
    """
    Builds and executes complex graph queries.

    Provides high-level query methods for:
    - Belief maps: How brands install beliefs across intents
    - Co-mentions: Brand co-occurrence patterns
    - ICP journeys: Concern -> Intent -> Brand recommendation paths
    - Substitution patterns: Who replaces whom when ignored
    """

    def __init__(self, neo4j_client: Neo4jClient):
        """
        Initialize QueryBuilder.

        Args:
            neo4j_client: Neo4j client instance.
        """
        self.client = neo4j_client

    # =========================================================================
    # BELIEF MAP QUERIES
    # =========================================================================

    async def get_belief_map(
        self,
        brand_name: str,
        llm_provider: str | None = None,
        intent_type: IntentTypeEnum | None = None,
    ) -> BeliefMapResponse:
        """
        Get belief map for a brand.

        Shows distribution of belief types installed by the brand across LLM responses.

        Args:
            brand_name: Brand name to query.
            llm_provider: Optional LLM provider filter.
            intent_type: Optional intent type filter.

        Returns:
            BeliefMapResponse with belief distribution.
        """
        query = """
        MATCH (b:Brand {normalized_name: $normalized_name})-[r:INSTALLS_BELIEF]->(bt:BeliefType)
        WHERE ($llm_provider IS NULL OR r.llm_provider = $llm_provider)
        """

        # Add intent type filter if specified
        if intent_type:
            query += """
            AND EXISTS {
                MATCH (i:Intent {intent_type: $intent_type})
                WHERE r.intent_id = i.id
            }
            """

        query += """
        RETURN bt.type as belief_type,
               sum(r.count) as total_count,
               avg(r.confidence) as avg_confidence
        ORDER BY total_count DESC
        """

        params = {
            "normalized_name": brand_name.lower().strip(),
            "llm_provider": llm_provider,
            "intent_type": intent_type.value if intent_type else None,
        }

        result = await self.client.execute_query(query, params)

        beliefs = []
        total = 0
        if result:
            for row in result:
                belief_data = {
                    "belief_type": row["belief_type"],
                    "count": row["total_count"],
                    "confidence": round(row["avg_confidence"], 3) if row["avg_confidence"] else 0,
                }
                beliefs.append(belief_data)
                total += row["total_count"]

        return BeliefMapResponse(
            brand_name=brand_name,
            beliefs=beliefs,
            total_occurrences=total,
        )

    async def get_belief_comparison(
        self,
        brand_names: list[str],
        llm_provider: str | None = None,
    ) -> dict[str, Any]:
        """
        Compare belief maps across multiple brands.

        Args:
            brand_names: List of brand names to compare.
            llm_provider: Optional LLM provider filter.

        Returns:
            Comparison data with belief distributions per brand.
        """
        query = """
        MATCH (b:Brand)-[r:INSTALLS_BELIEF]->(bt:BeliefType)
        WHERE b.normalized_name IN $normalized_names
        AND ($llm_provider IS NULL OR r.llm_provider = $llm_provider)
        RETURN b.name as brand_name,
               bt.type as belief_type,
               sum(r.count) as count,
               avg(r.confidence) as confidence
        ORDER BY b.name, count DESC
        """

        normalized_names = [name.lower().strip() for name in brand_names]
        result = await self.client.execute_query(
            query,
            {"normalized_names": normalized_names, "llm_provider": llm_provider}
        )

        comparison = {}
        if result:
            for row in result:
                brand = row["brand_name"]
                if brand not in comparison:
                    comparison[brand] = []
                comparison[brand].append({
                    "belief_type": row["belief_type"],
                    "count": row["count"],
                    "confidence": round(row["confidence"], 3) if row["confidence"] else 0,
                })

        return comparison

    async def get_belief_by_funnel_stage(
        self,
        brand_name: str | None = None,
        llm_provider: str | None = None,
    ) -> dict[str, Any]:
        """
        Get belief distribution segmented by funnel stage.

        Shows which belief types are most effective at each stage of the buyer journey.

        Args:
            brand_name: Optional brand name filter.
            llm_provider: Optional LLM provider filter.

        Returns:
            Belief distribution per funnel stage.
        """
        query = """
        MATCH (b:Brand)-[r:INSTALLS_BELIEF]->(bt:BeliefType)
        MATCH (i:Intent {id: r.intent_id})
        WHERE ($normalized_name IS NULL OR b.normalized_name = $normalized_name)
        AND ($llm_provider IS NULL OR r.llm_provider = $llm_provider)
        WITH i.funnel_stage as funnel_stage,
             bt.type as belief_type,
             sum(r.count) as total_count,
             avg(r.confidence) as avg_confidence,
             count(DISTINCT b) as brand_count
        RETURN funnel_stage,
               collect({
                   belief_type: belief_type,
                   count: total_count,
                   confidence: avg_confidence,
                   brand_count: brand_count
               }) as beliefs
        ORDER BY CASE funnel_stage
            WHEN 'awareness' THEN 1
            WHEN 'consideration' THEN 2
            WHEN 'decision' THEN 3
            WHEN 'retention' THEN 4
            ELSE 5
        END
        """

        result = await self.client.execute_query(
            query,
            {
                "normalized_name": brand_name.lower().strip() if brand_name else None,
                "llm_provider": llm_provider,
            }
        )

        funnel_data = {}
        if result:
            for row in result:
                stage = row["funnel_stage"] or "unknown"
                funnel_data[stage] = {
                    "beliefs": [
                        {
                            "belief_type": b["belief_type"],
                            "count": b["count"],
                            "confidence": round(b["confidence"], 3) if b["confidence"] else 0,
                            "brand_count": b["brand_count"],
                        }
                        for b in row["beliefs"]
                    ],
                    "total_count": sum(b["count"] for b in row["beliefs"]),
                }

        return funnel_data

    async def get_brand_belief_profile(
        self,
        brand_name: str,
        llm_provider: str | None = None,
    ) -> dict[str, Any]:
        """
        Get comprehensive belief profile for a brand.

        Combines belief map with funnel stage breakdown and effectiveness metrics.

        Args:
            brand_name: Brand name to analyze.
            llm_provider: Optional LLM provider filter.

        Returns:
            Complete belief profile with multiple dimensions.
        """
        normalized = brand_name.lower().strip()

        # Get overall belief distribution
        belief_map = await self.get_belief_map(brand_name, llm_provider)

        # Get belief by funnel stage
        funnel_beliefs = await self.get_belief_by_funnel_stage(brand_name, llm_provider)

        # Get belief effectiveness (correlation with recommendations)
        effectiveness_query = """
        MATCH (b:Brand {normalized_name: $normalized_name})-[r:INSTALLS_BELIEF]->(bt:BeliefType)
        MATCH (llm:LLMProvider)-[rec:RECOMMENDS]->(b)
        WHERE r.intent_id = rec.intent_id
        AND ($llm_provider IS NULL OR r.llm_provider = $llm_provider)
        WITH bt.type as belief_type,
             count(*) as recommendation_with_belief,
             avg(r.confidence) as avg_confidence
        RETURN belief_type,
               recommendation_with_belief,
               avg_confidence
        ORDER BY recommendation_with_belief DESC
        """

        effectiveness_result = await self.client.execute_query(
            effectiveness_query,
            {"normalized_name": normalized, "llm_provider": llm_provider}
        )

        effectiveness = []
        if effectiveness_result:
            for row in effectiveness_result:
                effectiveness.append({
                    "belief_type": row["belief_type"],
                    "recommendations_with_belief": row["recommendation_with_belief"],
                    "avg_confidence": round(row["avg_confidence"], 3) if row["avg_confidence"] else 0,
                })

        # Get belief consistency across providers
        consistency_query = """
        MATCH (b:Brand {normalized_name: $normalized_name})-[r:INSTALLS_BELIEF]->(bt:BeliefType)
        WITH bt.type as belief_type,
             r.llm_provider as provider,
             sum(r.count) as count,
             avg(r.confidence) as confidence
        RETURN belief_type,
               collect({provider: provider, count: count, confidence: confidence}) as by_provider,
               count(DISTINCT provider) as provider_count
        ORDER BY provider_count DESC
        """

        consistency_result = await self.client.execute_query(
            consistency_query,
            {"normalized_name": normalized}
        )

        consistency = []
        if consistency_result:
            for row in consistency_result:
                consistency.append({
                    "belief_type": row["belief_type"],
                    "provider_count": row["provider_count"],
                    "by_provider": [
                        {
                            "provider": p["provider"],
                            "count": p["count"],
                            "confidence": round(p["confidence"], 3) if p["confidence"] else 0,
                        }
                        for p in row["by_provider"]
                    ],
                })

        return {
            "brand_name": brand_name,
            "overall_beliefs": belief_map.beliefs,
            "total_occurrences": belief_map.total_occurrences,
            "by_funnel_stage": funnel_beliefs,
            "effectiveness": effectiveness,
            "consistency_across_providers": consistency,
        }

    async def get_belief_trends(
        self,
        brand_names: list[str] | None = None,
        llm_providers: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Get belief trends across brands and LLM providers.

        Identifies which beliefs are most commonly installed overall.

        Args:
            brand_names: Optional list of brands to analyze.
            llm_providers: Optional list of providers to include.

        Returns:
            Trend data showing belief patterns.
        """
        query = """
        MATCH (b:Brand)-[r:INSTALLS_BELIEF]->(bt:BeliefType)
        WHERE ($brand_names IS NULL OR b.normalized_name IN $brand_names)
        AND ($llm_providers IS NULL OR r.llm_provider IN $llm_providers)
        WITH bt.type as belief_type,
             sum(r.count) as total_installations,
             avg(r.confidence) as avg_confidence,
             count(DISTINCT b) as brand_count,
             count(DISTINCT r.llm_provider) as provider_count,
             collect(DISTINCT b.name)[0..5] as sample_brands
        RETURN belief_type,
               total_installations,
               avg_confidence,
               brand_count,
               provider_count,
               sample_brands
        ORDER BY total_installations DESC
        """

        normalized_names = [n.lower().strip() for n in brand_names] if brand_names else None

        result = await self.client.execute_query(
            query,
            {
                "brand_names": normalized_names,
                "llm_providers": llm_providers,
            }
        )

        trends = []
        total = 0
        if result:
            for row in result:
                trends.append({
                    "belief_type": row["belief_type"],
                    "total_installations": row["total_installations"],
                    "avg_confidence": round(row["avg_confidence"], 3) if row["avg_confidence"] else 0,
                    "brand_count": row["brand_count"],
                    "provider_count": row["provider_count"],
                    "sample_brands": row["sample_brands"],
                })
                total += row["total_installations"]

        # Calculate percentages
        for trend in trends:
            trend["percentage"] = round(trend["total_installations"] / total * 100, 1) if total > 0 else 0

        return {
            "trends": trends,
            "total_installations": total,
            "filters": {
                "brand_names": brand_names,
                "llm_providers": llm_providers,
            },
        }

    async def get_belief_effectiveness_analysis(
        self,
        belief_type: str | None = None,
        llm_provider: str | None = None,
    ) -> dict[str, Any]:
        """
        Analyze which beliefs correlate with better brand positioning.

        Compares belief installations with recommendation rates and positions.

        Args:
            belief_type: Optional specific belief type to analyze.
            llm_provider: Optional LLM provider filter.

        Returns:
            Effectiveness metrics for each belief type.
        """
        query = """
        MATCH (b:Brand)-[belief:INSTALLS_BELIEF]->(bt:BeliefType)
        WHERE ($belief_type IS NULL OR bt.type = $belief_type)
        AND ($llm_provider IS NULL OR belief.llm_provider = $llm_provider)

        // Get ranking info for same brand/intent
        OPTIONAL MATCH (b)-[rank:RANKS_FOR]->(i:Intent {id: belief.intent_id})
        WHERE rank.llm_provider = belief.llm_provider

        WITH bt.type as belief_type,
             b.name as brand_name,
             belief.confidence as belief_confidence,
             rank.position as position,
             rank.presence as presence,
             belief.count as belief_count

        WITH belief_type,
             count(DISTINCT brand_name) as brand_count,
             sum(belief_count) as total_installations,
             avg(belief_confidence) as avg_belief_confidence,
             avg(CASE WHEN position IS NOT NULL THEN position END) as avg_position,
             sum(CASE WHEN presence = 'recommended' THEN 1 ELSE 0 END) as recommendations,
             sum(CASE WHEN position = 1 THEN 1 ELSE 0 END) as first_positions

        RETURN belief_type,
               brand_count,
               total_installations,
               avg_belief_confidence,
               avg_position,
               recommendations,
               first_positions,
               CASE WHEN total_installations > 0
                    THEN toFloat(recommendations) / total_installations * 100
                    ELSE 0 END as recommendation_rate,
               CASE WHEN total_installations > 0
                    THEN toFloat(first_positions) / total_installations * 100
                    ELSE 0 END as first_position_rate
        ORDER BY recommendation_rate DESC
        """

        result = await self.client.execute_query(
            query,
            {
                "belief_type": belief_type,
                "llm_provider": llm_provider,
            }
        )

        effectiveness = []
        if result:
            for row in result:
                effectiveness.append({
                    "belief_type": row["belief_type"],
                    "brand_count": row["brand_count"],
                    "total_installations": row["total_installations"],
                    "avg_confidence": round(row["avg_belief_confidence"], 3) if row["avg_belief_confidence"] else 0,
                    "avg_position": round(row["avg_position"], 2) if row["avg_position"] else None,
                    "recommendations": row["recommendations"],
                    "first_positions": row["first_positions"],
                    "recommendation_rate": round(row["recommendation_rate"], 1) if row["recommendation_rate"] else 0,
                    "first_position_rate": round(row["first_position_rate"], 1) if row["first_position_rate"] else 0,
                })

        return {
            "effectiveness": effectiveness,
            "filters": {
                "belief_type": belief_type,
                "llm_provider": llm_provider,
            },
        }

    # =========================================================================
    # CO-MENTION QUERIES
    # =========================================================================

    async def get_co_mentions(
        self,
        brand_name: str,
        limit: int = 10,
        llm_provider: str | None = None,
    ) -> CoMentionResponse:
        """
        Get brands co-mentioned with the target brand.

        Args:
            brand_name: Brand name to query.
            limit: Maximum results to return.
            llm_provider: Optional LLM provider filter.

        Returns:
            CoMentionResponse with co-mentioned brands.
        """
        query = """
        MATCH (target:Brand {normalized_name: $normalized_name})-[r:CO_MENTIONED]-(other:Brand)
        WHERE $llm_provider IS NULL OR r.llm_provider = $llm_provider
        RETURN other.name as brand_name,
               other.normalized_name as normalized_name,
               r.count as co_mention_count,
               r.avg_position_delta as avg_position_delta,
               r.llm_provider as llm_provider
        ORDER BY r.count DESC
        LIMIT $limit
        """

        result = await self.client.execute_query(
            query,
            {
                "normalized_name": brand_name.lower().strip(),
                "llm_provider": llm_provider,
                "limit": limit,
            }
        )

        co_mentions = []
        if result:
            for row in result:
                co_mentions.append({
                    "brand_name": row["brand_name"],
                    "normalized_name": row["normalized_name"],
                    "count": row["co_mention_count"],
                    "avg_position_delta": round(row["avg_position_delta"], 2) if row["avg_position_delta"] else None,
                    "llm_provider": row["llm_provider"],
                })

        return CoMentionResponse(
            brand_name=brand_name,
            co_mentions=co_mentions,
        )

    async def get_co_mention_network(
        self,
        brand_name: str,
        depth: int = 2,
        min_count: int = 1,
    ) -> dict[str, Any]:
        """
        Get co-mention network centered on a brand.

        Args:
            brand_name: Central brand name.
            depth: Relationship depth to traverse.
            min_count: Minimum co-mention count to include.

        Returns:
            Network data with nodes and edges.
        """
        query = """
        MATCH path = (center:Brand {normalized_name: $normalized_name})-[:CO_MENTIONED*1..$depth]-(other:Brand)
        WHERE ALL(r IN relationships(path) WHERE r.count >= $min_count)
        WITH nodes(path) as nodes, relationships(path) as rels
        UNWIND nodes as n
        WITH DISTINCT n, rels
        UNWIND rels as r
        WITH DISTINCT n, r
        RETURN collect(DISTINCT {
            id: n.id,
            name: n.name,
            normalized_name: n.normalized_name
        }) as nodes,
        collect(DISTINCT {
            source: startNode(r).normalized_name,
            target: endNode(r).normalized_name,
            count: r.count
        }) as edges
        """

        result = await self.client.execute_query(
            query,
            {
                "normalized_name": brand_name.lower().strip(),
                "depth": depth,
                "min_count": min_count,
            }
        )

        if result and len(result) > 0:
            return {
                "nodes": result[0]["nodes"],
                "edges": result[0]["edges"],
            }
        return {"nodes": [], "edges": []}

    # =========================================================================
    # ICP JOURNEY QUERIES
    # =========================================================================

    async def get_icp_journey(
        self,
        icp_id: str,
        include_brands: bool = True,
    ) -> ICPJourneyResponse:
        """
        Get the journey path for an ICP.

        Maps: ICP -> Concerns -> Intents -> Brand Recommendations

        Args:
            icp_id: ICP UUID.
            include_brands: Whether to include brand recommendations.

        Returns:
            ICPJourneyResponse with journey data.
        """
        # Get ICP info
        icp_query = """
        MATCH (i:ICP {id: $icp_id})
        RETURN i.name as name, i.pain_points as pain_points, i.goals as goals
        """
        icp_result = await self.client.execute_query(icp_query, {"icp_id": icp_id})

        if not icp_result:
            return ICPJourneyResponse(
                icp_id=icp_id,
                icp_name="Unknown",
                concerns=[],
                intents=[],
                brand_recommendations=[],
            )

        icp_name = icp_result[0]["name"]

        # Get concerns and triggered intents
        concerns_query = """
        MATCH (i:ICP {id: $icp_id})-[hc:HAS_CONCERN]->(c:Concern)
        OPTIONAL MATCH (c)-[:TRIGGERS]->(intent:Intent)
        RETURN c.id as concern_id,
               c.description as description,
               c.category as category,
               hc.priority as priority,
               collect(DISTINCT {
                   id: intent.id,
                   intent_type: intent.intent_type,
                   funnel_stage: intent.funnel_stage,
                   buying_signal: intent.buying_signal
               }) as intents
        ORDER BY hc.priority
        """
        concerns_result = await self.client.execute_query(concerns_query, {"icp_id": icp_id})

        concerns = []
        all_intents = []
        intent_ids = set()

        if concerns_result:
            for row in concerns_result:
                concerns.append({
                    "concern_id": row["concern_id"],
                    "description": row["description"],
                    "category": row["category"],
                    "priority": row["priority"],
                })
                for intent in row["intents"]:
                    if intent["id"] and intent["id"] not in intent_ids:
                        intent_ids.add(intent["id"])
                        all_intents.append(intent)

        # Get brand recommendations if requested
        brand_recommendations = []
        if include_brands and intent_ids:
            brands_query = """
            MATCH (b:Brand)-[r:RANKS_FOR]->(i:Intent)
            WHERE i.id IN $intent_ids
            RETURN b.name as brand_name,
                   b.id as brand_id,
                   i.id as intent_id,
                   i.intent_type as intent_type,
                   r.position as position,
                   r.presence as presence,
                   r.llm_provider as llm_provider
            ORDER BY r.position
            """
            brands_result = await self.client.execute_query(
                brands_query,
                {"intent_ids": list(intent_ids)}
            )

            if brands_result:
                for row in brands_result:
                    brand_recommendations.append({
                        "brand_name": row["brand_name"],
                        "brand_id": row["brand_id"],
                        "intent_id": row["intent_id"],
                        "intent_type": row["intent_type"],
                        "position": row["position"],
                        "presence": row["presence"],
                        "llm_provider": row["llm_provider"],
                    })

        return ICPJourneyResponse(
            icp_id=icp_id,
            icp_name=icp_name,
            concerns=concerns,
            intents=all_intents,
            brand_recommendations=brand_recommendations,
        )

    # =========================================================================
    # SUBSTITUTION PATTERN QUERIES
    # =========================================================================

    async def get_substitution_patterns(
        self,
        brand_name: str,
        llm_provider: str | None = None,
        limit: int = 10,
    ) -> SubstitutionPatternResponse:
        """
        Find brands that substitute for a brand when it's ignored.

        Args:
            brand_name: Brand that was ignored.
            llm_provider: Optional LLM provider filter.
            limit: Maximum results.

        Returns:
            SubstitutionPatternResponse with substitute brands.
        """
        query = """
        // Find intents where the brand was ignored
        MATCH (llm:LLMProvider)-[ignore:IGNORES]->(missing:Brand {normalized_name: $normalized_name})
        WHERE $llm_provider IS NULL OR llm.name = $llm_provider

        // Find brands recommended for those same intents
        MATCH (llm)-[rec:RECOMMENDS]->(substitute:Brand)
        WHERE rec.intent_id = ignore.intent_id
        AND substitute.normalized_name <> $normalized_name

        RETURN substitute.name as brand_name,
               substitute.id as brand_id,
               count(*) as substitution_count,
               avg(rec.position) as avg_position,
               collect(DISTINCT llm.name) as llm_providers
        ORDER BY substitution_count DESC
        LIMIT $limit
        """

        result = await self.client.execute_query(
            query,
            {
                "normalized_name": brand_name.lower().strip(),
                "llm_provider": llm_provider,
                "limit": limit,
            }
        )

        substitutes = []
        if result:
            for row in result:
                substitutes.append({
                    "brand_name": row["brand_name"],
                    "brand_id": row["brand_id"],
                    "substitution_count": row["substitution_count"],
                    "avg_position": round(row["avg_position"], 1) if row["avg_position"] else None,
                    "llm_providers": row["llm_providers"],
                })

        return SubstitutionPatternResponse(
            missing_brand=brand_name,
            substitutes=substitutes,
        )

    # =========================================================================
    # COMPETITIVE ANALYSIS QUERIES
    # =========================================================================

    async def get_share_of_voice(
        self,
        brand_names: list[str],
        llm_provider: str | None = None,
    ) -> dict[str, Any]:
        """
        Calculate share of voice for brands.

        Args:
            brand_names: List of brand names to analyze.
            llm_provider: Optional LLM provider filter.

        Returns:
            Share of voice metrics per brand.
        """
        query = """
        MATCH (b:Brand)-[r:RANKS_FOR]->(i:Intent)
        WHERE b.normalized_name IN $normalized_names
        AND ($llm_provider IS NULL OR r.llm_provider = $llm_provider)
        WITH b.name as brand_name,
             count(r) as total_mentions,
             sum(CASE WHEN r.position = 1 THEN 1 ELSE 0 END) as first_positions,
             sum(CASE WHEN r.presence = 'recommended' THEN 1 ELSE 0 END) as recommendations,
             avg(r.position) as avg_position
        RETURN brand_name,
               total_mentions,
               first_positions,
               recommendations,
               round(avg_position * 10) / 10 as avg_position,
               round(toFloat(first_positions) / total_mentions * 100) as first_position_rate,
               round(toFloat(recommendations) / total_mentions * 100) as recommendation_rate
        ORDER BY total_mentions DESC
        """

        normalized_names = [name.lower().strip() for name in brand_names]
        result = await self.client.execute_query(
            query,
            {"normalized_names": normalized_names, "llm_provider": llm_provider}
        )

        metrics = {}
        total_mentions = 0

        if result:
            for row in result:
                metrics[row["brand_name"]] = {
                    "total_mentions": row["total_mentions"],
                    "first_positions": row["first_positions"],
                    "recommendations": row["recommendations"],
                    "avg_position": row["avg_position"],
                    "first_position_rate": row["first_position_rate"],
                    "recommendation_rate": row["recommendation_rate"],
                }
                total_mentions += row["total_mentions"]

            # Calculate share of voice percentages
            for brand in metrics:
                metrics[brand]["share_of_voice"] = round(
                    metrics[brand]["total_mentions"] / total_mentions * 100, 1
                ) if total_mentions > 0 else 0

        return metrics

    async def get_competitive_landscape(
        self,
        brand_name: str,
        llm_provider: str | None = None,
    ) -> dict[str, Any]:
        """
        Get competitive landscape for a brand.

        Args:
            brand_name: Target brand name.
            llm_provider: Optional LLM provider filter.

        Returns:
            Competitive landscape data.
        """
        # Get direct competitors
        competitors_query = """
        MATCH (b:Brand {normalized_name: $normalized_name})-[r:COMPETES_WITH]->(c:Brand)
        RETURN c.name as competitor_name,
               c.id as competitor_id,
               r.relationship_type as relationship_type
        """

        competitors_result = await self.client.execute_query(
            competitors_query,
            {"normalized_name": brand_name.lower().strip()}
        )

        competitors = []
        competitor_names = [brand_name]

        if competitors_result:
            for row in competitors_result:
                competitors.append({
                    "name": row["competitor_name"],
                    "id": row["competitor_id"],
                    "relationship_type": row["relationship_type"],
                })
                competitor_names.append(row["competitor_name"])

        # Get share of voice for brand and competitors
        sov = await self.get_share_of_voice(competitor_names, llm_provider)

        # Get co-mentions with competitors
        co_mentions = await self.get_co_mentions(brand_name, limit=20, llm_provider=llm_provider)

        return {
            "brand_name": brand_name,
            "competitors": competitors,
            "share_of_voice": sov,
            "co_mentions": co_mentions.co_mentions,
        }

    # =========================================================================
    # INTENT ANALYSIS QUERIES
    # =========================================================================

    async def get_intent_brand_coverage(
        self,
        intent_type: IntentTypeEnum | None = None,
        funnel_stage: str | None = None,
        llm_provider: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get brand coverage across intents.

        Args:
            intent_type: Optional intent type filter.
            funnel_stage: Optional funnel stage filter.
            llm_provider: Optional LLM provider filter.

        Returns:
            List of intents with brand coverage data.
        """
        query = """
        MATCH (i:Intent)<-[r:RANKS_FOR]-(b:Brand)
        WHERE ($intent_type IS NULL OR i.intent_type = $intent_type)
        AND ($funnel_stage IS NULL OR i.funnel_stage = $funnel_stage)
        AND ($llm_provider IS NULL OR r.llm_provider = $llm_provider)
        WITH i, count(DISTINCT b) as brand_count,
             collect(DISTINCT {name: b.name, position: r.position, presence: r.presence}) as brands
        RETURN i.id as intent_id,
               i.intent_type as intent_type,
               i.funnel_stage as funnel_stage,
               i.buying_signal as buying_signal,
               brand_count,
               brands[0..5] as top_brands
        ORDER BY brand_count DESC
        """

        result = await self.client.execute_query(
            query,
            {
                "intent_type": intent_type.value if intent_type else None,
                "funnel_stage": funnel_stage,
                "llm_provider": llm_provider,
            }
        )

        return [dict(row) for row in result] if result else []

    # =========================================================================
    # UTILITY QUERIES
    # =========================================================================

    async def get_graph_stats(self) -> dict[str, Any]:
        """Get overall graph statistics."""
        query = """
        CALL {
            MATCH (n:Brand) RETURN 'Brand' as label, count(n) as count
            UNION ALL
            MATCH (n:ICP) RETURN 'ICP' as label, count(n) as count
            UNION ALL
            MATCH (n:Intent) RETURN 'Intent' as label, count(n) as count
            UNION ALL
            MATCH (n:Concern) RETURN 'Concern' as label, count(n) as count
            UNION ALL
            MATCH (n:BeliefType) RETURN 'BeliefType' as label, count(n) as count
            UNION ALL
            MATCH (n:LLMProvider) RETURN 'LLMProvider' as label, count(n) as count
            UNION ALL
            MATCH (n:Conversation) RETURN 'Conversation' as label, count(n) as count
        }
        RETURN label, count
        """

        node_counts = {}
        result = await self.client.execute_query(query, {})
        if result:
            for row in result:
                node_counts[row["label"]] = row["count"]

        # Get edge counts
        edge_query = """
        CALL {
            MATCH ()-[r:CO_MENTIONED]->() RETURN 'CO_MENTIONED' as type, count(r) as count
            UNION ALL
            MATCH ()-[r:COMPETES_WITH]->() RETURN 'COMPETES_WITH' as type, count(r) as count
            UNION ALL
            MATCH ()-[r:HAS_CONCERN]->() RETURN 'HAS_CONCERN' as type, count(r) as count
            UNION ALL
            MATCH ()-[r:TRIGGERS]->() RETURN 'TRIGGERS' as type, count(r) as count
            UNION ALL
            MATCH ()-[r:RANKS_FOR]->() RETURN 'RANKS_FOR' as type, count(r) as count
            UNION ALL
            MATCH ()-[r:INSTALLS_BELIEF]->() RETURN 'INSTALLS_BELIEF' as type, count(r) as count
            UNION ALL
            MATCH ()-[r:RECOMMENDS]->() RETURN 'RECOMMENDS' as type, count(r) as count
            UNION ALL
            MATCH ()-[r:IGNORES]->() RETURN 'IGNORES' as type, count(r) as count
        }
        RETURN type, count
        """

        edge_counts = {}
        edge_result = await self.client.execute_query(edge_query, {})
        if edge_result:
            for row in edge_result:
                edge_counts[row["type"]] = row["count"]

        return {
            "nodes": node_counts,
            "edges": edge_counts,
            "total_nodes": sum(node_counts.values()),
            "total_edges": sum(edge_counts.values()),
        }
