"""
Tests for QueryBuilder component.

Tests high-level graph queries for belief maps, co-mentions, ICP journeys, etc.
"""

import pytest

from services.graph_builder.components.queries import QueryBuilder
from services.graph_builder.schemas import (
    BeliefMapResponse,
    CoMentionResponse,
    ICPJourneyResponse,
    SubstitutionPatternResponse,
    IntentTypeEnum,
)


class TestQueryBuilderBeliefMaps:
    """Tests for belief map queries."""

    @pytest.mark.asyncio
    async def test_get_belief_map(self, mock_neo4j_client):
        """Test getting belief map for a brand."""
        query = QueryBuilder(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [
                {"belief_type": "outcome", "total_count": 10, "avg_confidence": 0.85},
                {"belief_type": "truth", "total_count": 5, "avg_confidence": 0.7},
                {"belief_type": "superiority", "total_count": 3, "avg_confidence": 0.6},
            ]
        ])

        result = await query.get_belief_map("TestBrand")

        assert isinstance(result, BeliefMapResponse)
        assert result.brand_name == "TestBrand"
        assert len(result.beliefs) == 3
        assert result.total_occurrences == 18
        assert result.beliefs[0]["belief_type"] == "outcome"
        assert result.beliefs[0]["count"] == 10

    @pytest.mark.asyncio
    async def test_get_belief_map_with_provider_filter(self, mock_neo4j_client):
        """Test getting belief map filtered by LLM provider."""
        query = QueryBuilder(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [
                {"belief_type": "outcome", "total_count": 5, "avg_confidence": 0.9},
            ]
        ])

        result = await query.get_belief_map("TestBrand", llm_provider="openai")

        assert len(result.beliefs) == 1
        assert result.total_occurrences == 5

    @pytest.mark.asyncio
    async def test_get_belief_map_empty(self, mock_neo4j_client):
        """Test getting belief map for brand with no data."""
        query = QueryBuilder(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            []
        ])

        result = await query.get_belief_map("NonexistentBrand")

        assert result.brand_name == "NonexistentBrand"
        assert len(result.beliefs) == 0
        assert result.total_occurrences == 0

    @pytest.mark.asyncio
    async def test_get_belief_comparison(self, mock_neo4j_client):
        """Test comparing beliefs across brands."""
        query = QueryBuilder(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [
                {"brand_name": "Brand1", "belief_type": "outcome", "count": 10, "confidence": 0.8},
                {"brand_name": "Brand1", "belief_type": "truth", "count": 5, "confidence": 0.7},
                {"brand_name": "Brand2", "belief_type": "outcome", "count": 8, "confidence": 0.75},
            ]
        ])

        result = await query.get_belief_comparison(["Brand1", "Brand2"])

        assert "Brand1" in result
        assert "Brand2" in result
        assert len(result["Brand1"]) == 2
        assert len(result["Brand2"]) == 1


class TestQueryBuilderCoMentions:
    """Tests for co-mention queries."""

    @pytest.mark.asyncio
    async def test_get_co_mentions(self, mock_neo4j_client):
        """Test getting co-mentions for a brand."""
        query = QueryBuilder(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [
                {"brand_name": "Competitor1", "normalized_name": "competitor1", "co_mention_count": 15, "avg_position_delta": 0.5, "llm_provider": "openai"},
                {"brand_name": "Competitor2", "normalized_name": "competitor2", "co_mention_count": 10, "avg_position_delta": -0.3, "llm_provider": "openai"},
            ]
        ])

        result = await query.get_co_mentions("TestBrand", limit=10)

        assert isinstance(result, CoMentionResponse)
        assert result.brand_name == "TestBrand"
        assert len(result.co_mentions) == 2
        assert result.co_mentions[0]["count"] == 15
        assert result.co_mentions[0]["avg_position_delta"] == 0.5

    @pytest.mark.asyncio
    async def test_get_co_mentions_empty(self, mock_neo4j_client):
        """Test getting co-mentions for brand with no co-mentions."""
        query = QueryBuilder(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            []
        ])

        result = await query.get_co_mentions("LonelyBrand")

        assert len(result.co_mentions) == 0

    @pytest.mark.asyncio
    async def test_get_co_mention_network(self, mock_neo4j_client):
        """Test getting co-mention network."""
        query = QueryBuilder(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [{
                "nodes": [
                    {"id": "1", "name": "Brand1", "normalized_name": "brand1"},
                    {"id": "2", "name": "Brand2", "normalized_name": "brand2"},
                ],
                "edges": [
                    {"source": "brand1", "target": "brand2", "count": 5},
                ]
            }]
        ])

        result = await query.get_co_mention_network("brand1", depth=2)

        assert "nodes" in result
        assert "edges" in result


class TestQueryBuilderICPJourneys:
    """Tests for ICP journey queries."""

    @pytest.mark.asyncio
    async def test_get_icp_journey(self, mock_neo4j_client):
        """Test getting ICP journey data."""
        query = QueryBuilder(mock_neo4j_client)

        # Mock ICP query
        mock_neo4j_client.set_query_results([
            # ICP info
            [{"name": "Tech PM", "pain_points": ["Priority issues"], "goals": ["Improve velocity"]}],
            # Concerns and intents
            [
                {
                    "concern_id": "c1",
                    "description": "Difficulty prioritizing",
                    "category": "pain_point",
                    "priority": 1,
                    "intents": [
                        {"id": "i1", "intent_type": "evaluation", "funnel_stage": "consideration", "buying_signal": 0.7}
                    ]
                }
            ],
            # Brand recommendations
            [
                {"brand_name": "Tool1", "brand_id": "b1", "intent_id": "i1", "intent_type": "evaluation", "position": 1, "presence": "recommended", "llm_provider": "openai"},
                {"brand_name": "Tool2", "brand_id": "b2", "intent_id": "i1", "intent_type": "evaluation", "position": 2, "presence": "mentioned", "llm_provider": "openai"},
            ]
        ])

        result = await query.get_icp_journey("icp-123", include_brands=True)

        assert isinstance(result, ICPJourneyResponse)
        assert result.icp_id == "icp-123"
        assert result.icp_name == "Tech PM"
        assert len(result.concerns) == 1
        assert len(result.brand_recommendations) == 2

    @pytest.mark.asyncio
    async def test_get_icp_journey_not_found(self, mock_neo4j_client):
        """Test getting journey for non-existent ICP."""
        query = QueryBuilder(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            []  # No ICP found
        ])

        result = await query.get_icp_journey("nonexistent")

        assert result.icp_id == "nonexistent"
        assert result.icp_name == "Unknown"
        assert len(result.concerns) == 0


class TestQueryBuilderSubstitutions:
    """Tests for substitution pattern queries."""

    @pytest.mark.asyncio
    async def test_get_substitution_patterns(self, mock_neo4j_client):
        """Test getting substitution patterns."""
        query = QueryBuilder(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [
                {"brand_name": "Substitute1", "brand_id": "s1", "substitution_count": 8, "avg_position": 1.5, "llm_providers": ["openai", "anthropic"]},
                {"brand_name": "Substitute2", "brand_id": "s2", "substitution_count": 5, "avg_position": 2.0, "llm_providers": ["openai"]},
            ]
        ])

        result = await query.get_substitution_patterns("IgnoredBrand")

        assert isinstance(result, SubstitutionPatternResponse)
        assert result.missing_brand == "IgnoredBrand"
        assert len(result.substitutes) == 2
        assert result.substitutes[0]["substitution_count"] == 8

    @pytest.mark.asyncio
    async def test_get_substitution_patterns_empty(self, mock_neo4j_client):
        """Test getting substitution patterns when none exist."""
        query = QueryBuilder(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            []
        ])

        result = await query.get_substitution_patterns("BrandNeverIgnored")

        assert len(result.substitutes) == 0


class TestQueryBuilderCompetitive:
    """Tests for competitive analysis queries."""

    @pytest.mark.asyncio
    async def test_get_share_of_voice(self, mock_neo4j_client):
        """Test getting share of voice metrics."""
        query = QueryBuilder(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [
                {"brand_name": "Brand1", "total_mentions": 50, "first_positions": 20, "recommendations": 30, "avg_position": 1.5, "first_position_rate": 40, "recommendation_rate": 60},
                {"brand_name": "Brand2", "total_mentions": 30, "first_positions": 10, "recommendations": 15, "avg_position": 2.0, "first_position_rate": 33, "recommendation_rate": 50},
            ]
        ])

        result = await query.get_share_of_voice(["Brand1", "Brand2"])

        assert "Brand1" in result
        assert "Brand2" in result
        assert result["Brand1"]["total_mentions"] == 50
        assert "share_of_voice" in result["Brand1"]

    @pytest.mark.asyncio
    async def test_get_competitive_landscape(self, mock_neo4j_client):
        """Test getting competitive landscape."""
        query = QueryBuilder(mock_neo4j_client)

        # Mock competitor query, then SOV query, then co-mentions
        mock_neo4j_client.set_query_results([
            # Competitors
            [
                {"competitor_name": "Competitor1", "competitor_id": "c1", "relationship_type": "direct"},
            ],
            # Share of voice
            [
                {"brand_name": "TestBrand", "total_mentions": 40, "first_positions": 15, "recommendations": 25, "avg_position": 1.8, "first_position_rate": 38, "recommendation_rate": 63},
                {"brand_name": "Competitor1", "total_mentions": 35, "first_positions": 12, "recommendations": 20, "avg_position": 2.0, "first_position_rate": 34, "recommendation_rate": 57},
            ],
            # Co-mentions
            [
                {"brand_name": "Competitor1", "normalized_name": "competitor1", "co_mention_count": 20, "avg_position_delta": 0.2, "llm_provider": "all"},
            ]
        ])

        result = await query.get_competitive_landscape("TestBrand")

        assert result["brand_name"] == "TestBrand"
        assert "competitors" in result
        assert "share_of_voice" in result
        assert "co_mentions" in result


class TestQueryBuilderIntents:
    """Tests for intent analysis queries."""

    @pytest.mark.asyncio
    async def test_get_intent_brand_coverage(self, mock_neo4j_client):
        """Test getting intent brand coverage."""
        query = QueryBuilder(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [
                {
                    "intent_id": "i1",
                    "intent_type": "evaluation",
                    "funnel_stage": "consideration",
                    "buying_signal": 0.7,
                    "brand_count": 5,
                    "top_brands": [
                        {"name": "Brand1", "position": 1, "presence": "recommended"},
                        {"name": "Brand2", "position": 2, "presence": "mentioned"},
                    ]
                }
            ]
        ])

        result = await query.get_intent_brand_coverage(intent_type=IntentTypeEnum.EVALUATION)

        assert len(result) == 1
        assert result[0]["brand_count"] == 5


class TestQueryBuilderBeliefAggregation:
    """Tests for enhanced belief aggregation queries."""

    @pytest.mark.asyncio
    async def test_get_belief_by_funnel_stage(self, mock_neo4j_client):
        """Test getting belief distribution by funnel stage."""
        query = QueryBuilder(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [
                {
                    "funnel_stage": "awareness",
                    "beliefs": [
                        {"belief_type": "truth", "count": 10, "confidence": 0.7, "brand_count": 5},
                        {"belief_type": "social_proof", "count": 8, "confidence": 0.8, "brand_count": 4},
                    ]
                },
                {
                    "funnel_stage": "consideration",
                    "beliefs": [
                        {"belief_type": "outcome", "count": 15, "confidence": 0.85, "brand_count": 6},
                        {"belief_type": "superiority", "count": 12, "confidence": 0.75, "brand_count": 5},
                    ]
                },
            ]
        ])

        result = await query.get_belief_by_funnel_stage()

        assert "awareness" in result
        assert "consideration" in result
        assert len(result["awareness"]["beliefs"]) == 2
        assert result["awareness"]["total_count"] == 18

    @pytest.mark.asyncio
    async def test_get_belief_by_funnel_stage_with_brand_filter(self, mock_neo4j_client):
        """Test getting belief by funnel stage filtered by brand."""
        query = QueryBuilder(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [
                {
                    "funnel_stage": "decision",
                    "beliefs": [
                        {"belief_type": "transaction", "count": 5, "confidence": 0.9, "brand_count": 1},
                    ]
                }
            ]
        ])

        result = await query.get_belief_by_funnel_stage(brand_name="TestBrand")

        assert "decision" in result
        assert len(result["decision"]["beliefs"]) == 1

    @pytest.mark.asyncio
    async def test_get_brand_belief_profile(self, mock_neo4j_client):
        """Test getting comprehensive belief profile for a brand."""
        query = QueryBuilder(mock_neo4j_client)

        # Mock all the queries used by get_brand_belief_profile
        mock_neo4j_client.set_query_results([
            # get_belief_map
            [
                {"belief_type": "outcome", "total_count": 10, "avg_confidence": 0.85},
                {"belief_type": "superiority", "total_count": 5, "avg_confidence": 0.7},
            ],
            # get_belief_by_funnel_stage
            [
                {
                    "funnel_stage": "consideration",
                    "beliefs": [
                        {"belief_type": "outcome", "count": 10, "confidence": 0.85, "brand_count": 1},
                    ]
                }
            ],
            # effectiveness query
            [
                {"belief_type": "outcome", "recommendation_with_belief": 8, "avg_confidence": 0.9},
            ],
            # consistency query
            [
                {
                    "belief_type": "outcome",
                    "provider_count": 2,
                    "by_provider": [
                        {"provider": "openai", "count": 6, "confidence": 0.85},
                        {"provider": "anthropic", "count": 4, "confidence": 0.9},
                    ]
                }
            ],
        ])

        result = await query.get_brand_belief_profile("TestBrand")

        assert result["brand_name"] == "TestBrand"
        assert "overall_beliefs" in result
        assert "by_funnel_stage" in result
        assert "effectiveness" in result
        assert "consistency_across_providers" in result

    @pytest.mark.asyncio
    async def test_get_belief_trends(self, mock_neo4j_client):
        """Test getting belief trends across brands."""
        query = QueryBuilder(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [
                {
                    "belief_type": "outcome",
                    "total_installations": 100,
                    "avg_confidence": 0.8,
                    "brand_count": 20,
                    "provider_count": 3,
                    "sample_brands": ["Brand1", "Brand2", "Brand3"],
                },
                {
                    "belief_type": "superiority",
                    "total_installations": 50,
                    "avg_confidence": 0.75,
                    "brand_count": 15,
                    "provider_count": 3,
                    "sample_brands": ["Brand1", "Brand4"],
                },
            ]
        ])

        result = await query.get_belief_trends()

        assert "trends" in result
        assert len(result["trends"]) == 2
        assert result["total_installations"] == 150
        # Check percentage calculation
        assert result["trends"][0]["percentage"] == 66.7  # 100/150 * 100

    @pytest.mark.asyncio
    async def test_get_belief_trends_with_filters(self, mock_neo4j_client):
        """Test getting belief trends with brand and provider filters."""
        query = QueryBuilder(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [
                {
                    "belief_type": "outcome",
                    "total_installations": 25,
                    "avg_confidence": 0.85,
                    "brand_count": 2,
                    "provider_count": 1,
                    "sample_brands": ["Brand1", "Brand2"],
                },
            ]
        ])

        result = await query.get_belief_trends(
            brand_names=["Brand1", "Brand2"],
            llm_providers=["openai"]
        )

        assert result["filters"]["brand_names"] == ["Brand1", "Brand2"]
        assert result["filters"]["llm_providers"] == ["openai"]

    @pytest.mark.asyncio
    async def test_get_belief_effectiveness_analysis(self, mock_neo4j_client):
        """Test getting belief effectiveness analysis."""
        query = QueryBuilder(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [
                {
                    "belief_type": "outcome",
                    "brand_count": 10,
                    "total_installations": 50,
                    "avg_belief_confidence": 0.85,
                    "avg_position": 1.5,
                    "recommendations": 40,
                    "first_positions": 20,
                    "recommendation_rate": 80.0,
                    "first_position_rate": 40.0,
                },
                {
                    "belief_type": "superiority",
                    "brand_count": 8,
                    "total_installations": 30,
                    "avg_belief_confidence": 0.7,
                    "avg_position": 2.0,
                    "recommendations": 20,
                    "first_positions": 10,
                    "recommendation_rate": 66.7,
                    "first_position_rate": 33.3,
                },
            ]
        ])

        result = await query.get_belief_effectiveness_analysis()

        assert "effectiveness" in result
        assert len(result["effectiveness"]) == 2
        assert result["effectiveness"][0]["belief_type"] == "outcome"
        assert result["effectiveness"][0]["recommendation_rate"] == 80.0

    @pytest.mark.asyncio
    async def test_get_belief_effectiveness_with_filters(self, mock_neo4j_client):
        """Test belief effectiveness with type and provider filters."""
        query = QueryBuilder(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [
                {
                    "belief_type": "outcome",
                    "brand_count": 5,
                    "total_installations": 20,
                    "avg_belief_confidence": 0.9,
                    "avg_position": 1.2,
                    "recommendations": 18,
                    "first_positions": 15,
                    "recommendation_rate": 90.0,
                    "first_position_rate": 75.0,
                },
            ]
        ])

        result = await query.get_belief_effectiveness_analysis(
            belief_type="outcome",
            llm_provider="openai"
        )

        assert result["filters"]["belief_type"] == "outcome"
        assert result["filters"]["llm_provider"] == "openai"
        assert len(result["effectiveness"]) == 1


class TestQueryBuilderStats:
    """Tests for graph statistics queries."""

    @pytest.mark.asyncio
    async def test_get_graph_stats(self, mock_neo4j_client):
        """Test getting overall graph statistics."""
        query = QueryBuilder(mock_neo4j_client)

        # Mock node counts
        mock_neo4j_client.set_query_results([
            # Node counts
            [
                {"label": "Brand", "count": 100},
                {"label": "ICP", "count": 25},
                {"label": "Intent", "count": 500},
                {"label": "Concern", "count": 75},
                {"label": "BeliefType", "count": 6},
                {"label": "LLMProvider", "count": 4},
                {"label": "Conversation", "count": 125},
            ],
            # Edge counts
            [
                {"type": "CO_MENTIONED", "count": 500},
                {"type": "COMPETES_WITH", "count": 50},
                {"type": "HAS_CONCERN", "count": 75},
                {"type": "TRIGGERS", "count": 200},
                {"type": "RANKS_FOR", "count": 1000},
                {"type": "INSTALLS_BELIEF", "count": 800},
                {"type": "RECOMMENDS", "count": 600},
                {"type": "IGNORES", "count": 150},
            ]
        ])

        result = await query.get_graph_stats()

        assert "nodes" in result
        assert "edges" in result
        assert "total_nodes" in result
        assert "total_edges" in result
        assert result["nodes"]["Brand"] == 100
        assert result["edges"]["CO_MENTIONED"] == 500
