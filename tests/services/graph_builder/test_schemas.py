"""
Tests for Knowledge Graph Builder schemas.

Tests Pydantic model validation for all node and edge types.
"""

import pytest
from pydantic import ValidationError

from services.graph_builder.schemas import (
    # Enums
    BeliefTypeEnum,
    PresenceStateEnum,
    IntentTypeEnum,
    FunnelStageEnum,
    RelationshipTypeEnum,
    # Node schemas
    BrandNode,
    ICPNode,
    IntentNode,
    ConcernNode,
    BeliefTypeNode,
    LLMProviderNode,
    ConversationNode,
    # Edge schemas
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
    # Request/Response schemas
    GraphBuildRequest,
    GraphBuildResponse,
    BeliefMapRequest,
    BeliefMapResponse,
    CoMentionRequest,
    CoMentionResponse,
    ICPJourneyRequest,
    ICPJourneyResponse,
    BatchNodeCreate,
    BatchEdgeCreate,
    BatchOperationResult,
)


class TestEnums:
    """Tests for enum types."""

    def test_belief_type_enum_values(self):
        """Test all BeliefTypeEnum values."""
        assert BeliefTypeEnum.TRUTH.value == "truth"
        assert BeliefTypeEnum.SUPERIORITY.value == "superiority"
        assert BeliefTypeEnum.OUTCOME.value == "outcome"
        assert BeliefTypeEnum.TRANSACTION.value == "transaction"
        assert BeliefTypeEnum.IDENTITY.value == "identity"
        assert BeliefTypeEnum.SOCIAL_PROOF.value == "social_proof"

    def test_presence_state_enum_values(self):
        """Test all PresenceStateEnum values."""
        assert PresenceStateEnum.IGNORED.value == "ignored"
        assert PresenceStateEnum.MENTIONED.value == "mentioned"
        assert PresenceStateEnum.TRUSTED.value == "trusted"
        assert PresenceStateEnum.RECOMMENDED.value == "recommended"
        assert PresenceStateEnum.COMPARED.value == "compared"

    def test_intent_type_enum_values(self):
        """Test all IntentTypeEnum values."""
        assert IntentTypeEnum.INFORMATIONAL.value == "informational"
        assert IntentTypeEnum.EVALUATION.value == "evaluation"
        assert IntentTypeEnum.DECISION.value == "decision"

    def test_funnel_stage_enum_values(self):
        """Test all FunnelStageEnum values."""
        assert FunnelStageEnum.AWARENESS.value == "awareness"
        assert FunnelStageEnum.CONSIDERATION.value == "consideration"
        assert FunnelStageEnum.PURCHASE.value == "purchase"


class TestBrandNode:
    """Tests for BrandNode schema."""

    def test_valid_brand_node(self, sample_brand_data):
        """Test valid BrandNode creation."""
        brand = BrandNode(**sample_brand_data)
        assert brand.id == "brand-123"
        assert brand.name == "TestBrand"
        assert brand.normalized_name == "testbrand"
        assert brand.domain == "testbrand.com"
        assert brand.industry == "Technology"
        assert brand.is_tracked is True

    def test_brand_node_minimal(self):
        """Test BrandNode with minimal fields."""
        brand = BrandNode(
            id="123",
            name="Test",
            normalized_name="test",
        )
        assert brand.domain is None
        assert brand.industry is None
        assert brand.is_tracked is False

    def test_brand_node_missing_required(self):
        """Test BrandNode fails without required fields."""
        with pytest.raises(ValidationError):
            BrandNode(id="123", name="Test")  # missing normalized_name


class TestICPNode:
    """Tests for ICPNode schema."""

    def test_valid_icp_node(self, sample_icp_data):
        """Test valid ICPNode creation."""
        icp = ICPNode(**sample_icp_data)
        assert icp.id == "icp-123"
        assert icp.name == "Tech Product Manager"
        assert icp.website_id == "website-123"
        assert len(icp.pain_points) == 2
        assert len(icp.goals) == 2

    def test_icp_node_minimal(self):
        """Test ICPNode with minimal fields."""
        icp = ICPNode(
            id="123",
            name="Test ICP",
            website_id="website-1",
        )
        assert icp.demographics == {}
        assert icp.pain_points == []
        assert icp.goals == []


class TestIntentNode:
    """Tests for IntentNode schema."""

    def test_valid_intent_node(self, sample_intent_data):
        """Test valid IntentNode creation."""
        intent = IntentNode(**sample_intent_data)
        assert intent.id == "intent-123"
        assert intent.intent_type == IntentTypeEnum.EVALUATION
        assert intent.funnel_stage == FunnelStageEnum.CONSIDERATION
        assert intent.buying_signal == 0.7
        assert intent.trust_need == 0.8

    def test_intent_node_signal_bounds(self):
        """Test buying_signal and trust_need bounds."""
        # Valid at boundaries
        intent = IntentNode(
            id="1",
            prompt_id="p1",
            intent_type=IntentTypeEnum.INFORMATIONAL,
            funnel_stage=FunnelStageEnum.AWARENESS,
            buying_signal=0.0,
            trust_need=1.0,
        )
        assert intent.buying_signal == 0.0
        assert intent.trust_need == 1.0

    def test_intent_node_invalid_signal(self):
        """Test IntentNode rejects invalid signal values."""
        with pytest.raises(ValidationError):
            IntentNode(
                id="1",
                prompt_id="p1",
                intent_type=IntentTypeEnum.INFORMATIONAL,
                funnel_stage=FunnelStageEnum.AWARENESS,
                buying_signal=1.5,  # Invalid: > 1.0
                trust_need=0.5,
            )


class TestConcernNode:
    """Tests for ConcernNode schema."""

    def test_valid_concern_node(self, sample_concern_data):
        """Test valid ConcernNode creation."""
        concern = ConcernNode(**sample_concern_data)
        assert concern.id == "concern-123"
        assert concern.description == "Difficulty prioritizing features"
        assert concern.category == "pain_point"

    def test_concern_node_optional_category(self):
        """Test ConcernNode without category."""
        concern = ConcernNode(
            id="123",
            description="Test concern",
        )
        assert concern.category is None


class TestEdgeSchemas:
    """Tests for edge/relationship schemas."""

    def test_co_mentioned_edge(self):
        """Test CoMentionedEdge creation."""
        edge = CoMentionedEdge(
            source_brand_id="brand-1",
            target_brand_id="brand-2",
            count=5,
            avg_position_delta=0.5,
            llm_provider="openai",
        )
        assert edge.count == 5
        assert edge.avg_position_delta == 0.5

    def test_competes_with_edge(self):
        """Test CompetesWithEdge creation."""
        edge = CompetesWithEdge(
            source_brand_id="brand-1",
            target_brand_id="brand-2",
            relationship_type=RelationshipTypeEnum.DIRECT,
        )
        assert edge.relationship_type == RelationshipTypeEnum.DIRECT

    def test_has_concern_edge(self):
        """Test HasConcernEdge creation."""
        edge = HasConcernEdge(
            icp_id="icp-1",
            concern_id="concern-1",
            priority=1,
        )
        assert edge.priority == 1

    def test_has_concern_edge_priority_bounds(self):
        """Test HasConcernEdge priority must be >= 1."""
        with pytest.raises(ValidationError):
            HasConcernEdge(
                icp_id="icp-1",
                concern_id="concern-1",
                priority=0,  # Invalid: < 1
            )

    def test_ranks_for_edge(self):
        """Test RanksForEdge creation."""
        edge = RanksForEdge(
            brand_id="brand-1",
            intent_id="intent-1",
            position=1,
            presence=PresenceStateEnum.RECOMMENDED,
            llm_provider="openai",
            count=1,
        )
        assert edge.position == 1
        assert edge.presence == PresenceStateEnum.RECOMMENDED

    def test_installs_belief_edge(self):
        """Test InstallsBeliefEdge creation."""
        edge = InstallsBeliefEdge(
            brand_id="brand-1",
            belief_type=BeliefTypeEnum.OUTCOME,
            intent_id="intent-1",
            llm_provider="openai",
            count=3,
            confidence=0.85,
        )
        assert edge.belief_type == BeliefTypeEnum.OUTCOME
        assert edge.confidence == 0.85

    def test_recommends_edge(self):
        """Test RecommendsEdge creation."""
        edge = RecommendsEdge(
            llm_provider="openai",
            llm_model="gpt-4",
            brand_id="brand-1",
            position=1,
        )
        assert edge.llm_provider == "openai"
        assert edge.position == 1

    def test_ignores_edge(self):
        """Test IgnoresEdge creation."""
        edge = IgnoresEdge(
            llm_provider="openai",
            llm_model="gpt-4",
            brand_id="brand-1",
            competitor_mentioned="brand-2",
        )
        assert edge.competitor_mentioned == "brand-2"


class TestRequestResponseSchemas:
    """Tests for API request/response schemas."""

    def test_graph_build_request(self):
        """Test GraphBuildRequest creation."""
        request = GraphBuildRequest(
            website_id="website-123",
            simulation_run_id="sim-123",
            incremental=True,
        )
        assert request.website_id == "website-123"
        assert request.incremental is True

    def test_graph_build_response(self):
        """Test GraphBuildResponse creation."""
        response = GraphBuildResponse(
            success=True,
            nodes_created=10,
            edges_created=25,
            nodes_updated=5,
            edges_updated=3,
            build_duration_ms=150,
        )
        assert response.success is True
        assert response.nodes_created == 10
        assert response.edges_created == 25

    def test_belief_map_response(self):
        """Test BeliefMapResponse creation."""
        response = BeliefMapResponse(
            brand_name="TestBrand",
            beliefs=[
                {"belief_type": "outcome", "count": 10, "confidence": 0.8},
                {"belief_type": "truth", "count": 5, "confidence": 0.7},
            ],
            total_occurrences=15,
        )
        assert response.brand_name == "TestBrand"
        assert len(response.beliefs) == 2
        assert response.total_occurrences == 15

    def test_co_mention_response(self):
        """Test CoMentionResponse creation."""
        response = CoMentionResponse(
            brand_name="TestBrand",
            co_mentions=[
                {"brand_name": "Other", "count": 5},
            ],
        )
        assert len(response.co_mentions) == 1


class TestBatchSchemas:
    """Tests for batch operation schemas."""

    def test_batch_node_create(self):
        """Test BatchNodeCreate creation."""
        batch = BatchNodeCreate(
            brands=[
                BrandNode(id="1", name="Brand1", normalized_name="brand1"),
                BrandNode(id="2", name="Brand2", normalized_name="brand2"),
            ],
            icps=[
                ICPNode(id="1", name="ICP1", website_id="w1"),
            ],
        )
        assert len(batch.brands) == 2
        assert len(batch.icps) == 1
        assert len(batch.intents) == 0

    def test_batch_edge_create(self):
        """Test BatchEdgeCreate creation."""
        batch = BatchEdgeCreate(
            co_mentions=[
                CoMentionedEdge(source_brand_id="1", target_brand_id="2"),
            ],
            ranks_for=[
                RanksForEdge(
                    brand_id="1",
                    intent_id="i1",
                    position=1,
                    presence=PresenceStateEnum.RECOMMENDED,
                    llm_provider="openai",
                ),
            ],
        )
        assert len(batch.co_mentions) == 1
        assert len(batch.ranks_for) == 1

    def test_batch_operation_result(self):
        """Test BatchOperationResult creation."""
        result = BatchOperationResult(
            success=True,
            created=10,
            updated=5,
            failed=1,
            errors=["Failed to create node X"],
        )
        assert result.success is True
        assert result.created == 10
        assert len(result.errors) == 1
