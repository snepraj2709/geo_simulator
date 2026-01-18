"""
Tests for GraphBuilder component.

Tests the main graph building orchestration engine.
"""

import pytest

from services.graph_builder.components.builder import GraphBuilder, BuildStats
from services.graph_builder.schemas import (
    GraphBuildRequest,
    GraphBuildResponse,
    BatchNodeCreate,
    BatchEdgeCreate,
    BrandNode,
    ICPNode,
    IntentNode,
    CoMentionedEdge,
    RanksForEdge,
    BeliefTypeEnum,
    PresenceStateEnum,
    IntentTypeEnum,
    FunnelStageEnum,
)


class TestBuildStats:
    """Tests for BuildStats dataclass."""

    def test_build_stats_defaults(self):
        """Test BuildStats default values."""
        stats = BuildStats()

        assert stats.nodes_created == 0
        assert stats.nodes_updated == 0
        assert stats.edges_created == 0
        assert stats.edges_updated == 0
        assert stats.errors == []

    def test_build_stats_duration(self):
        """Test BuildStats duration calculation."""
        import time

        stats = BuildStats()
        time.sleep(0.01)  # Small delay

        assert stats.duration_ms > 0


class TestGraphBuilderInitialization:
    """Tests for GraphBuilder initialization."""

    @pytest.mark.asyncio
    async def test_initialize_graph(self, mock_neo4j_client):
        """Test graph initialization creates constraints and indexes."""
        builder = GraphBuilder(mock_neo4j_client)

        # Mock all constraint/index creation to succeed
        mock_neo4j_client.set_query_results([
            [],  # Constraint 1
            [],  # Constraint 2
            [],  # Constraint 3
            [],  # Constraint 4
            [],  # Constraint 5
            [],  # Constraint 6
            [],  # Index 1
            [],  # Index 2
            [],  # Index 3
            [],  # Index 4
            [],  # Index 5
            [{"count": 6}],  # BeliefType nodes
        ])

        success = await builder.initialize_graph()

        assert success is True


class TestGraphBuilderBatchNodeCreation:
    """Tests for batch node creation."""

    @pytest.mark.asyncio
    async def test_create_nodes_batch(self, mock_neo4j_client):
        """Test batch node creation."""
        builder = GraphBuilder(mock_neo4j_client)

        nodes = BatchNodeCreate(
            brands=[
                BrandNode(id="1", name="Brand1", normalized_name="brand1"),
                BrandNode(id="2", name="Brand2", normalized_name="brand2"),
            ],
            icps=[
                ICPNode(id="1", name="ICP1", website_id="w1"),
            ],
        )

        # Mock batch creation results
        mock_neo4j_client.set_query_results([
            [{"count": 2}],  # Brands
            [{"count": 1}],  # ICPs
        ])

        result = await builder.create_nodes_batch(nodes)

        assert result.success is True
        assert result.created == 3


class TestGraphBuilderBatchEdgeCreation:
    """Tests for batch edge creation."""

    @pytest.mark.asyncio
    async def test_create_edges_batch(self, mock_neo4j_client):
        """Test batch edge creation."""
        builder = GraphBuilder(mock_neo4j_client)

        edges = BatchEdgeCreate(
            co_mentions=[
                CoMentionedEdge(source_brand_id="1", target_brand_id="2"),
            ],
            ranks_for=[
                RanksForEdge(brand_id="1", intent_id="i1", position=1, presence=PresenceStateEnum.RECOMMENDED, llm_provider="openai"),
            ],
        )

        mock_neo4j_client.set_query_results([
            [{"count": 1}],  # Co-mentions
            [{"count": 1}],  # Ranks for
        ])

        result = await builder.create_edges_batch(edges)

        assert result.success is True
        assert result.created == 2


class TestGraphBuilderSimulation:
    """Tests for building graph from simulation data."""

    @pytest.mark.asyncio
    async def test_build_from_simulation(self, mock_neo4j_client, sample_simulation_data):
        """Test building graph from simulation data."""
        builder = GraphBuilder(mock_neo4j_client)

        request = GraphBuildRequest(
            website_id="website-1",
            incremental=True,
        )

        # Mock all the initialization and batch creation calls
        mock_neo4j_client.set_query_results([
            # Initialize graph
            [],  # Constraints
            [],
            [],
            [],
            [],
            [],
            [],  # Indexes
            [],
            [],
            [],
            [],
            [{"count": 6}],  # BeliefType nodes

            # Build ICPs
            [{"count": 1}],  # ICP nodes
            [{"count": 1}],  # Concern nodes
            [{"count": 1}],  # HAS_CONCERN edges

            # Build Conversations
            [{"count": 1}],  # Conversation nodes
            [{"count": 1}],  # INITIATES edges

            # Build Intents
            [{"count": 1}],  # Intent nodes
            [{"count": 1}],  # CONTAINS edges

            # Build from responses
            [{"count": 2}],  # Brand nodes
            [{"count": 1}],  # LLM Provider nodes
            [{"count": 2}],  # RANKS_FOR edges
            [{"count": 2}],  # INSTALLS_BELIEF edges
            [{"count": 1}],  # RECOMMENDS edges
            [{"count": 0}],  # IGNORES edges
            [{"count": 1}],  # CO_MENTIONED edges
        ])

        result = await builder.build_from_simulation(request, sample_simulation_data)

        assert isinstance(result, GraphBuildResponse)
        assert result.success is True
        assert result.build_duration_ms is not None

    @pytest.mark.asyncio
    async def test_build_from_simulation_empty_data(self, mock_neo4j_client):
        """Test building graph with empty simulation data."""
        builder = GraphBuilder(mock_neo4j_client)

        request = GraphBuildRequest(
            website_id="website-1",
        )

        # Mock just the initialization
        mock_neo4j_client.set_query_results([
            # Initialize graph
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [{"count": 6}],
        ])

        result = await builder.build_from_simulation(request, {})

        assert result.success is True
        assert result.nodes_created == 0


class TestGraphBuilderIncrementalUpdates:
    """Tests for incremental graph updates."""

    @pytest.mark.asyncio
    async def test_update_brand_rankings(self, mock_neo4j_client):
        """Test updating brand rankings."""
        builder = GraphBuilder(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [{"r": {"position": 1, "count": 1}}]
        ])

        success = await builder.update_brand_rankings(
            brand_id="brand-1",
            intent_id="intent-1",
            llm_provider="openai",
            position=1,
            presence=PresenceStateEnum.RECOMMENDED,
        )

        assert success is True

    @pytest.mark.asyncio
    async def test_add_belief_installation(self, mock_neo4j_client):
        """Test adding belief installation."""
        builder = GraphBuilder(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [{"r": {"count": 1, "confidence": 0.8}}]
        ])

        success = await builder.add_belief_installation(
            brand_id="brand-1",
            belief_type=BeliefTypeEnum.OUTCOME,
            intent_id="intent-1",
            llm_provider="openai",
            confidence=0.8,
        )

        assert success is True


class TestGraphBuilderCleanup:
    """Tests for graph cleanup operations."""

    @pytest.mark.asyncio
    async def test_clear_website_data(self, mock_neo4j_client):
        """Test clearing website data."""
        builder = GraphBuilder(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [{"deleted": 50}]
        ])

        deleted = await builder.clear_website_data("website-123")

        assert deleted == 50

    @pytest.mark.asyncio
    async def test_clear_all(self, mock_neo4j_client):
        """Test clearing all graph data."""
        builder = GraphBuilder(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [{"deleted": 1000}]
        ])

        deleted = await builder.clear_all()

        assert deleted == 1000


class TestGraphBuilderICPProcessing:
    """Tests for ICP-specific processing."""

    @pytest.mark.asyncio
    async def test_build_icps_creates_concerns(self, mock_neo4j_client):
        """Test that building ICPs also creates concerns and relationships."""
        builder = GraphBuilder(mock_neo4j_client)

        icps_data = [
            {
                "id": "icp-1",
                "name": "Test ICP",
                "website_id": "w1",
                "demographics": {},
                "pain_points": ["Pain 1", "Pain 2", "Pain 3"],
                "goals": ["Goal 1"],
            }
        ]

        mock_neo4j_client.set_query_results([
            [{"count": 1}],  # ICP nodes
            [{"count": 3}],  # Concern nodes (one per pain point)
            [{"count": 3}],  # HAS_CONCERN edges
        ])

        stats = BuildStats()
        await builder._build_icps(icps_data, stats)

        # Should have created ICP, concerns, and edges
        assert stats.nodes_created >= 1
        assert stats.edges_created >= 1


class TestGraphBuilderResponseProcessing:
    """Tests for LLM response processing."""

    @pytest.mark.asyncio
    async def test_build_from_responses_creates_co_mentions(self, mock_neo4j_client):
        """Test that processing responses creates co-mention edges."""
        builder = GraphBuilder(mock_neo4j_client)

        responses_data = [
            {
                "prompt_id": "p1",
                "llm_provider": "openai",
                "llm_model": "gpt-4",
                "brand_states": [
                    {"brand_name": "Brand1", "normalized_name": "brand1", "presence": "recommended", "position_rank": 1},
                    {"brand_name": "Brand2", "normalized_name": "brand2", "presence": "mentioned", "position_rank": 2},
                    {"brand_name": "Brand3", "normalized_name": "brand3", "presence": "mentioned", "position_rank": 3},
                ],
            }
        ]

        mock_neo4j_client.set_query_results([
            [{"count": 3}],  # Brand nodes
            [{"count": 1}],  # LLM Provider nodes
            [{"count": 3}],  # RANKS_FOR edges
            [{"count": 0}],  # INSTALLS_BELIEF edges (no beliefs in test data)
            [{"count": 1}],  # RECOMMENDS edges
            [{"count": 0}],  # IGNORES edges
            [{"count": 3}],  # CO_MENTIONED edges (3 pairs from 3 brands)
        ])

        stats = BuildStats()
        await builder._build_from_responses(responses_data, stats)

        # Should have created brands, provider, and various edges
        assert stats.nodes_created > 0
        assert stats.edges_created > 0

    @pytest.mark.asyncio
    async def test_build_from_responses_handles_beliefs(self, mock_neo4j_client):
        """Test that processing responses creates belief installation edges."""
        builder = GraphBuilder(mock_neo4j_client)

        responses_data = [
            {
                "prompt_id": "p1",
                "llm_provider": "openai",
                "llm_model": "gpt-4",
                "brand_states": [
                    {
                        "brand_name": "Brand1",
                        "normalized_name": "brand1",
                        "presence": "recommended",
                        "position_rank": 1,
                        "belief_sold": "outcome",
                        "confidence": 0.9,
                    },
                ],
            }
        ]

        mock_neo4j_client.set_query_results([
            [{"count": 1}],  # Brand nodes
            [{"count": 1}],  # LLM Provider nodes
            [{"count": 1}],  # RANKS_FOR edges
            [{"count": 1}],  # INSTALLS_BELIEF edges
            [{"count": 1}],  # RECOMMENDS edges
            [{"count": 0}],  # IGNORES edges
            [{"count": 0}],  # CO_MENTIONED edges (only one brand)
        ])

        stats = BuildStats()
        await builder._build_from_responses(responses_data, stats)

        assert stats.edges_created >= 1  # At least the belief edge


class TestGraphBuilderErrorHandling:
    """Tests for error handling in graph building."""

    @pytest.mark.asyncio
    async def test_build_with_error_records_in_stats(self, mock_neo4j_client):
        """Test that errors during build are recorded in stats."""
        builder = GraphBuilder(mock_neo4j_client)

        request = GraphBuildRequest(website_id="w1")

        # Make initialization fail
        mock_neo4j_client.set_query_results([])

        # Patch to raise an exception
        async def raise_error(*args, **kwargs):
            raise Exception("Test error")

        original_init = builder.initialize_graph
        builder.initialize_graph = raise_error

        result = await builder.build_from_simulation(request, {})

        assert result.success is False
        assert len(result.errors) > 0
        assert "Test error" in result.errors[0]

        # Restore
        builder.initialize_graph = original_init
