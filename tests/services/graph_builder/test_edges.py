"""
Tests for EdgeManager component.

Tests edge/relationship creation, retrieval, and batch operations.
"""

import pytest

from services.graph_builder.components.edges import EdgeManager
from services.graph_builder.schemas import (
    CoMentionedEdge,
    CompetesWithEdge,
    HasConcernEdge,
    InitiatesEdge,
    TriggersEdge,
    ContainsEdge,
    RanksForEdge,
    InstallsBeliefEdge,
    RecommendsEdge,
    IgnoresEdge,
    BeliefTypeEnum,
    PresenceStateEnum,
    RelationshipTypeEnum,
)


class TestEdgeManagerCoMentions:
    """Tests for CO_MENTIONED edge operations."""

    @pytest.mark.asyncio
    async def test_create_co_mention(self, mock_neo4j_client):
        """Test creating a CO_MENTIONED edge."""
        manager = EdgeManager(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [{"r": {"count": 1}, "source": "Brand1", "target": "Brand2"}]
        ])

        edge = CoMentionedEdge(
            source_brand_id="brand-1",
            target_brand_id="brand-2",
            count=1,
            avg_position_delta=0.5,
            llm_provider="openai",
        )
        result = await manager.create_co_mention(edge)

        assert result is not None
        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_get_co_mentions(self, mock_neo4j_client):
        """Test retrieving co-mentions for a brand."""
        manager = EdgeManager(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [
                {"brand_name": "Brand2", "brand_id": "b2", "count": 5, "avg_position_delta": 0.3},
                {"brand_name": "Brand3", "brand_id": "b3", "count": 3, "avg_position_delta": -0.2},
            ]
        ])

        results = await manager.get_co_mentions("brand-1", limit=10)

        assert len(results) == 2
        assert results[0]["brand_name"] == "Brand2"
        assert results[0]["count"] == 5

    @pytest.mark.asyncio
    async def test_create_co_mentions_batch(self, mock_neo4j_client):
        """Test batch CO_MENTIONED edge creation."""
        manager = EdgeManager(mock_neo4j_client)

        edges = [
            CoMentionedEdge(source_brand_id="1", target_brand_id="2", count=1),
            CoMentionedEdge(source_brand_id="1", target_brand_id="3", count=2),
            CoMentionedEdge(source_brand_id="2", target_brand_id="3", count=1),
        ]

        mock_neo4j_client.set_query_results([
            [{"count": 3}]
        ])

        count = await manager.create_co_mentions_batch(edges)

        assert count == 3


class TestEdgeManagerCompetition:
    """Tests for COMPETES_WITH edge operations."""

    @pytest.mark.asyncio
    async def test_create_competes_with(self, mock_neo4j_client):
        """Test creating a COMPETES_WITH edge."""
        manager = EdgeManager(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [{"r": {"relationship_type": "direct"}, "source": "Brand1", "target": "Brand2"}]
        ])

        edge = CompetesWithEdge(
            source_brand_id="brand-1",
            target_brand_id="brand-2",
            relationship_type=RelationshipTypeEnum.DIRECT,
        )
        result = await manager.create_competes_with(edge)

        assert result is not None

    @pytest.mark.asyncio
    async def test_get_competitors(self, mock_neo4j_client):
        """Test retrieving competitors for a brand."""
        manager = EdgeManager(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [
                {"brand_name": "Competitor1", "brand_id": "c1", "relationship_type": "direct"},
                {"brand_name": "Competitor2", "brand_id": "c2", "relationship_type": "indirect"},
            ]
        ])

        results = await manager.get_competitors("brand-1")

        assert len(results) == 2
        assert results[0]["relationship_type"] == "direct"


class TestEdgeManagerICPRelations:
    """Tests for ICP relationship edges."""

    @pytest.mark.asyncio
    async def test_create_has_concern(self, mock_neo4j_client):
        """Test creating a HAS_CONCERN edge."""
        manager = EdgeManager(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [{"r": {"priority": 1}}]
        ])

        edge = HasConcernEdge(
            icp_id="icp-1",
            concern_id="concern-1",
            priority=1,
        )
        result = await manager.create_has_concern(edge)

        assert result is not None

    @pytest.mark.asyncio
    async def test_get_icp_concerns(self, mock_neo4j_client):
        """Test retrieving concerns for an ICP."""
        manager = EdgeManager(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [
                {"concern_id": "c1", "description": "Concern 1", "category": "pain", "priority": 1},
                {"concern_id": "c2", "description": "Concern 2", "category": "pain", "priority": 2},
            ]
        ])

        results = await manager.get_icp_concerns("icp-1")

        assert len(results) == 2
        assert results[0]["priority"] == 1

    @pytest.mark.asyncio
    async def test_create_initiates(self, mock_neo4j_client):
        """Test creating an INITIATES edge."""
        manager = EdgeManager(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [{"r": {}}]
        ])

        edge = InitiatesEdge(
            icp_id="icp-1",
            conversation_id="conv-1",
        )
        result = await manager.create_initiates(edge)

        assert result is not None

    @pytest.mark.asyncio
    async def test_create_has_concerns_batch(self, mock_neo4j_client):
        """Test batch HAS_CONCERN edge creation."""
        manager = EdgeManager(mock_neo4j_client)

        edges = [
            HasConcernEdge(icp_id="icp-1", concern_id="c1", priority=1),
            HasConcernEdge(icp_id="icp-1", concern_id="c2", priority=2),
        ]

        mock_neo4j_client.set_query_results([
            [{"count": 2}]
        ])

        count = await manager.create_has_concerns_batch(edges)

        assert count == 2


class TestEdgeManagerIntentRelations:
    """Tests for Intent relationship edges."""

    @pytest.mark.asyncio
    async def test_create_triggers(self, mock_neo4j_client):
        """Test creating a TRIGGERS edge."""
        manager = EdgeManager(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [{"r": {}}]
        ])

        edge = TriggersEdge(
            concern_id="concern-1",
            intent_id="intent-1",
        )
        result = await manager.create_triggers(edge)

        assert result is not None

    @pytest.mark.asyncio
    async def test_create_contains(self, mock_neo4j_client):
        """Test creating a CONTAINS edge."""
        manager = EdgeManager(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [{"r": {}}]
        ])

        edge = ContainsEdge(
            conversation_id="conv-1",
            intent_id="intent-1",
        )
        result = await manager.create_contains(edge)

        assert result is not None


class TestEdgeManagerRanksFor:
    """Tests for RANKS_FOR edge operations."""

    @pytest.mark.asyncio
    async def test_create_ranks_for(self, mock_neo4j_client):
        """Test creating a RANKS_FOR edge."""
        manager = EdgeManager(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [{"r": {"position": 1, "count": 1}}]
        ])

        edge = RanksForEdge(
            brand_id="brand-1",
            intent_id="intent-1",
            position=1,
            presence=PresenceStateEnum.RECOMMENDED,
            llm_provider="openai",
            count=1,
        )
        result = await manager.create_ranks_for(edge)

        assert result is not None

    @pytest.mark.asyncio
    async def test_get_brand_rankings(self, mock_neo4j_client):
        """Test retrieving brand rankings for an intent."""
        manager = EdgeManager(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [
                {"brand_name": "Brand1", "brand_id": "b1", "position": 1, "presence": "recommended", "count": 5, "llm_provider": "openai"},
                {"brand_name": "Brand2", "brand_id": "b2", "position": 2, "presence": "mentioned", "count": 3, "llm_provider": "openai"},
            ]
        ])

        results = await manager.get_brand_rankings("intent-1")

        assert len(results) == 2
        assert results[0]["position"] == 1
        assert results[0]["presence"] == "recommended"

    @pytest.mark.asyncio
    async def test_create_ranks_for_batch(self, mock_neo4j_client):
        """Test batch RANKS_FOR edge creation."""
        manager = EdgeManager(mock_neo4j_client)

        edges = [
            RanksForEdge(brand_id="b1", intent_id="i1", position=1, presence=PresenceStateEnum.RECOMMENDED, llm_provider="openai"),
            RanksForEdge(brand_id="b2", intent_id="i1", position=2, presence=PresenceStateEnum.MENTIONED, llm_provider="openai"),
        ]

        mock_neo4j_client.set_query_results([
            [{"count": 2}]
        ])

        count = await manager.create_ranks_for_batch(edges)

        assert count == 2


class TestEdgeManagerBeliefs:
    """Tests for INSTALLS_BELIEF edge operations."""

    @pytest.mark.asyncio
    async def test_create_installs_belief(self, mock_neo4j_client):
        """Test creating an INSTALLS_BELIEF edge."""
        manager = EdgeManager(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [{"r": {"count": 1, "confidence": 0.85}}]
        ])

        edge = InstallsBeliefEdge(
            brand_id="brand-1",
            belief_type=BeliefTypeEnum.OUTCOME,
            intent_id="intent-1",
            llm_provider="openai",
            count=1,
            confidence=0.85,
        )
        result = await manager.create_installs_belief(edge)

        assert result is not None

    @pytest.mark.asyncio
    async def test_get_belief_map(self, mock_neo4j_client):
        """Test retrieving belief map for a brand."""
        manager = EdgeManager(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [
                {"belief_type": "outcome", "total_count": 10, "avg_confidence": 0.85},
                {"belief_type": "truth", "total_count": 5, "avg_confidence": 0.7},
            ]
        ])

        results = await manager.get_belief_map("brand-1")

        assert len(results) == 2
        assert results[0]["belief_type"] == "outcome"
        assert results[0]["total_count"] == 10

    @pytest.mark.asyncio
    async def test_create_installs_beliefs_batch(self, mock_neo4j_client):
        """Test batch INSTALLS_BELIEF edge creation."""
        manager = EdgeManager(mock_neo4j_client)

        edges = [
            InstallsBeliefEdge(brand_id="b1", belief_type=BeliefTypeEnum.OUTCOME, confidence=0.8),
            InstallsBeliefEdge(brand_id="b1", belief_type=BeliefTypeEnum.TRUTH, confidence=0.7),
        ]

        mock_neo4j_client.set_query_results([
            [{"count": 2}]
        ])

        count = await manager.create_installs_beliefs_batch(edges)

        assert count == 2


class TestEdgeManagerLLMRelations:
    """Tests for LLM Provider relationship edges."""

    @pytest.mark.asyncio
    async def test_create_recommends(self, mock_neo4j_client):
        """Test creating a RECOMMENDS edge."""
        manager = EdgeManager(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [{"r": {"position": 1}}]
        ])

        edge = RecommendsEdge(
            llm_provider="openai",
            llm_model="gpt-4",
            brand_id="brand-1",
            intent_id="intent-1",
            position=1,
            belief_type=BeliefTypeEnum.OUTCOME,
        )
        result = await manager.create_recommends(edge)

        assert result is not None

    @pytest.mark.asyncio
    async def test_get_llm_recommendations(self, mock_neo4j_client):
        """Test retrieving LLM recommendations."""
        manager = EdgeManager(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [
                {"brand_name": "Brand1", "brand_id": "b1", "position": 1, "belief_type": "outcome"},
                {"brand_name": "Brand2", "brand_id": "b2", "position": 2, "belief_type": "truth"},
            ]
        ])

        results = await manager.get_llm_recommendations("openai", "gpt-4")

        assert len(results) == 2
        assert results[0]["position"] == 1

    @pytest.mark.asyncio
    async def test_create_ignores(self, mock_neo4j_client):
        """Test creating an IGNORES edge."""
        manager = EdgeManager(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [{"r": {"competitor_mentioned": "brand-2"}}]
        ])

        edge = IgnoresEdge(
            llm_provider="openai",
            llm_model="gpt-4",
            brand_id="brand-1",
            intent_id="intent-1",
            competitor_mentioned="brand-2",
        )
        result = await manager.create_ignores(edge)

        assert result is not None

    @pytest.mark.asyncio
    async def test_get_ignored_by(self, mock_neo4j_client):
        """Test retrieving LLMs that ignore a brand."""
        manager = EdgeManager(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [
                {"llm_provider": "openai", "llm_model": "gpt-4", "intent_id": "i1", "competitor_mentioned": "brand-2"},
            ]
        ])

        results = await manager.get_ignored_by("brand-1")

        assert len(results) == 1
        assert results[0]["competitor_mentioned"] == "brand-2"


class TestEdgeManagerUtilities:
    """Tests for EdgeManager utility methods."""

    @pytest.mark.asyncio
    async def test_delete_edge(self, mock_neo4j_client):
        """Test deleting an edge."""
        manager = EdgeManager(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [{"count": 1}]
        ])

        deleted = await manager.delete_edge(
            "CO_MENTIONED", "brand-1", "brand-2", "Brand", "Brand"
        )

        assert deleted is True

    @pytest.mark.asyncio
    async def test_count_edges(self, mock_neo4j_client):
        """Test counting edges by type."""
        manager = EdgeManager(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [{"count": 50}]
        ])

        count = await manager.count_edges("CO_MENTIONED")

        assert count == 50
