"""
Tests for NodeManager component.

Tests node creation, retrieval, and batch operations.
"""

import pytest
from unittest.mock import AsyncMock, patch

from services.graph_builder.components.nodes import NodeManager
from services.graph_builder.schemas import (
    BrandNode,
    ICPNode,
    IntentNode,
    ConcernNode,
    ConversationNode,
    LLMProviderNode,
    BeliefTypeEnum,
    IntentTypeEnum,
    FunnelStageEnum,
)


class TestNodeManagerBrands:
    """Tests for Brand node operations."""

    @pytest.mark.asyncio
    async def test_create_brand(self, mock_neo4j_client, sample_brand_data):
        """Test creating a brand node."""
        manager = NodeManager(mock_neo4j_client)

        # Configure mock to return the created brand
        mock_neo4j_client.set_query_results([
            [{"b": sample_brand_data}]
        ])

        brand = BrandNode(**sample_brand_data)
        result = await manager.create_brand(brand)

        assert result is not None
        assert result["name"] == "TestBrand"
        assert result["normalized_name"] == "testbrand"

    @pytest.mark.asyncio
    async def test_get_brand(self, mock_neo4j_client, sample_brand_data):
        """Test retrieving a brand node."""
        manager = NodeManager(mock_neo4j_client)

        # Configure mock to return the brand
        mock_neo4j_client.set_query_results([
            [{"b": sample_brand_data}]
        ])

        result = await manager.get_brand("testbrand")

        assert result is not None
        assert result["name"] == "TestBrand"

    @pytest.mark.asyncio
    async def test_get_brand_not_found(self, mock_neo4j_client):
        """Test retrieving a non-existent brand."""
        manager = NodeManager(mock_neo4j_client)

        # Configure mock to return empty result
        mock_neo4j_client.set_query_results([[]])

        result = await manager.get_brand("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_create_brands_batch(self, mock_neo4j_client):
        """Test batch brand creation."""
        manager = NodeManager(mock_neo4j_client)

        brands = [
            BrandNode(id="1", name="Brand1", normalized_name="brand1"),
            BrandNode(id="2", name="Brand2", normalized_name="brand2"),
            BrandNode(id="3", name="Brand3", normalized_name="brand3"),
        ]

        # Configure mock to return count
        mock_neo4j_client.set_query_results([
            [{"count": 3}]
        ])

        count = await manager.create_brands_batch(brands)

        assert count == 3


class TestNodeManagerICPs:
    """Tests for ICP node operations."""

    @pytest.mark.asyncio
    async def test_create_icp(self, mock_neo4j_client, sample_icp_data):
        """Test creating an ICP node."""
        manager = NodeManager(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [{"i": sample_icp_data}]
        ])

        icp = ICPNode(**sample_icp_data)
        result = await manager.create_icp(icp)

        assert result is not None
        assert result["name"] == "Tech Product Manager"

    @pytest.mark.asyncio
    async def test_get_icps_by_website(self, mock_neo4j_client, sample_icp_data):
        """Test retrieving ICPs for a website."""
        manager = NodeManager(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [{"i": sample_icp_data}]
        ])

        results = await manager.get_icps_by_website("website-123")

        assert len(results) == 1
        assert results[0]["name"] == "Tech Product Manager"

    @pytest.mark.asyncio
    async def test_create_icps_batch(self, mock_neo4j_client):
        """Test batch ICP creation."""
        manager = NodeManager(mock_neo4j_client)

        icps = [
            ICPNode(id="1", name="ICP1", website_id="w1"),
            ICPNode(id="2", name="ICP2", website_id="w1"),
        ]

        mock_neo4j_client.set_query_results([
            [{"count": 2}]
        ])

        count = await manager.create_icps_batch(icps)

        assert count == 2


class TestNodeManagerIntents:
    """Tests for Intent node operations."""

    @pytest.mark.asyncio
    async def test_create_intent(self, mock_neo4j_client, sample_intent_data):
        """Test creating an Intent node."""
        manager = NodeManager(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [{"i": sample_intent_data}]
        ])

        intent = IntentNode(
            id=sample_intent_data["id"],
            prompt_id=sample_intent_data["prompt_id"],
            intent_type=IntentTypeEnum.EVALUATION,
            funnel_stage=FunnelStageEnum.CONSIDERATION,
            buying_signal=sample_intent_data["buying_signal"],
            trust_need=sample_intent_data["trust_need"],
            query_text=sample_intent_data["query_text"],
        )
        result = await manager.create_intent(intent)

        assert result is not None

    @pytest.mark.asyncio
    async def test_create_intents_batch(self, mock_neo4j_client):
        """Test batch Intent creation."""
        manager = NodeManager(mock_neo4j_client)

        intents = [
            IntentNode(
                id="1",
                prompt_id="p1",
                intent_type=IntentTypeEnum.INFORMATIONAL,
                funnel_stage=FunnelStageEnum.AWARENESS,
                buying_signal=0.3,
                trust_need=0.5,
            ),
            IntentNode(
                id="2",
                prompt_id="p2",
                intent_type=IntentTypeEnum.DECISION,
                funnel_stage=FunnelStageEnum.PURCHASE,
                buying_signal=0.9,
                trust_need=0.8,
            ),
        ]

        mock_neo4j_client.set_query_results([
            [{"count": 2}]
        ])

        count = await manager.create_intents_batch(intents)

        assert count == 2


class TestNodeManagerConcerns:
    """Tests for Concern node operations."""

    @pytest.mark.asyncio
    async def test_create_concern(self, mock_neo4j_client, sample_concern_data):
        """Test creating a Concern node."""
        manager = NodeManager(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [{"c": sample_concern_data}]
        ])

        concern = ConcernNode(**sample_concern_data)
        result = await manager.create_concern(concern)

        assert result is not None
        assert result["description"] == "Difficulty prioritizing features"

    @pytest.mark.asyncio
    async def test_create_concerns_batch(self, mock_neo4j_client):
        """Test batch Concern creation."""
        manager = NodeManager(mock_neo4j_client)

        concerns = [
            ConcernNode(id="1", description="Concern 1"),
            ConcernNode(id="2", description="Concern 2"),
        ]

        mock_neo4j_client.set_query_results([
            [{"count": 2}]
        ])

        count = await manager.create_concerns_batch(concerns)

        assert count == 2


class TestNodeManagerBeliefTypes:
    """Tests for BeliefType node operations."""

    @pytest.mark.asyncio
    async def test_ensure_belief_types(self, mock_neo4j_client):
        """Test ensuring all belief type nodes exist."""
        manager = NodeManager(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [{"count": 6}]  # 6 belief types
        ])

        count = await manager.ensure_belief_types()

        assert count == 6

    @pytest.mark.asyncio
    async def test_get_belief_type(self, mock_neo4j_client):
        """Test retrieving a belief type node."""
        manager = NodeManager(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [{"bt": {"type": "outcome"}}]
        ])

        result = await manager.get_belief_type(BeliefTypeEnum.OUTCOME)

        assert result is not None
        assert result["type"] == "outcome"


class TestNodeManagerLLMProviders:
    """Tests for LLMProvider node operations."""

    @pytest.mark.asyncio
    async def test_create_llm_provider(self, mock_neo4j_client, sample_llm_provider_data):
        """Test creating an LLM Provider node."""
        manager = NodeManager(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [{"l": sample_llm_provider_data}]
        ])

        provider = LLMProviderNode(**sample_llm_provider_data)
        result = await manager.create_llm_provider(provider)

        assert result is not None
        assert result["name"] == "openai"
        assert result["model"] == "gpt-4"

    @pytest.mark.asyncio
    async def test_create_llm_providers_batch(self, mock_neo4j_client):
        """Test batch LLM Provider creation."""
        manager = NodeManager(mock_neo4j_client)

        providers = [
            LLMProviderNode(name="openai", model="gpt-4"),
            LLMProviderNode(name="anthropic", model="claude-3"),
            LLMProviderNode(name="google", model="gemini-pro"),
        ]

        mock_neo4j_client.set_query_results([
            [{"count": 3}]
        ])

        count = await manager.create_llm_providers_batch(providers)

        assert count == 3


class TestNodeManagerConversations:
    """Tests for Conversation node operations."""

    @pytest.mark.asyncio
    async def test_create_conversation(self, mock_neo4j_client, sample_conversation_data):
        """Test creating a Conversation node."""
        manager = NodeManager(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [{"c": sample_conversation_data}]
        ])

        conversation = ConversationNode(**sample_conversation_data)
        result = await manager.create_conversation(conversation)

        assert result is not None
        assert result["topic"] == "Feature prioritization tools"

    @pytest.mark.asyncio
    async def test_create_conversations_batch(self, mock_neo4j_client):
        """Test batch Conversation creation."""
        manager = NodeManager(mock_neo4j_client)

        conversations = [
            ConversationNode(id="1", topic="Topic 1"),
            ConversationNode(id="2", topic="Topic 2"),
        ]

        mock_neo4j_client.set_query_results([
            [{"count": 2}]
        ])

        count = await manager.create_conversations_batch(conversations)

        assert count == 2


class TestNodeManagerUtilities:
    """Tests for NodeManager utility methods."""

    @pytest.mark.asyncio
    async def test_delete_node(self, mock_neo4j_client):
        """Test deleting a node."""
        manager = NodeManager(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [{"count": 1}]
        ])

        deleted = await manager.delete_node("Brand", "brand-123")

        assert deleted is True

    @pytest.mark.asyncio
    async def test_delete_node_not_found(self, mock_neo4j_client):
        """Test deleting a non-existent node."""
        manager = NodeManager(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [{"count": 0}]
        ])

        deleted = await manager.delete_node("Brand", "nonexistent")

        assert deleted is False

    @pytest.mark.asyncio
    async def test_count_nodes(self, mock_neo4j_client):
        """Test counting nodes by label."""
        manager = NodeManager(mock_neo4j_client)

        mock_neo4j_client.set_query_results([
            [{"count": 25}]
        ])

        count = await manager.count_nodes("Brand")

        assert count == 25
