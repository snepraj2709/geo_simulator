"""
Graph Builder for Knowledge Graph Builder Service.

Main orchestration engine for building the Neo4j knowledge graph
from simulation data. Includes belief type classification as defined
in ARCHITECTURE.md.
"""

import time
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from shared.utils.logging import get_logger
from shared.db.neo4j_client import Neo4jClient

from services.graph_builder.components.nodes import NodeManager
from services.graph_builder.components.edges import EdgeManager
from services.graph_builder.components.belief_classifier import (
    BeliefClassifier,
    BeliefClassification,
    BeliefAnalysis,
)
from services.graph_builder.schemas import (
    BrandNode,
    ICPNode,
    IntentNode,
    ConcernNode,
    ConversationNode,
    LLMProviderNode,
    CoMentionedEdge,
    HasConcernEdge,
    InitiatesEdge,
    TriggersEdge,
    ContainsEdge,
    RanksForEdge,
    InstallsBeliefEdge,
    RecommendsEdge,
    IgnoresEdge,
    GraphBuildRequest,
    GraphBuildResponse,
    BatchNodeCreate,
    BatchEdgeCreate,
    BatchOperationResult,
    BeliefTypeEnum,
    PresenceStateEnum,
    IntentTypeEnum,
    FunnelStageEnum,
)

logger = get_logger(__name__)


@dataclass
class BuildStats:
    """Statistics from a graph build operation."""

    nodes_created: int = 0
    nodes_updated: int = 0
    edges_created: int = 0
    edges_updated: int = 0
    errors: list[str] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)

    @property
    def duration_ms(self) -> int:
        """Get build duration in milliseconds."""
        return int((time.time() - self.start_time) * 1000)


class GraphBuilder:
    """
    Main graph building orchestration engine.

    Coordinates NodeManager and EdgeManager to build the knowledge graph
    from simulation data including:
    - Brands and their relationships
    - ICPs and their concerns
    - Intents and brand rankings
    - Belief installations
    - LLM provider recommendations
    """

    def __init__(self, neo4j_client: Neo4jClient, enable_belief_classification: bool = True):
        """
        Initialize GraphBuilder.

        Args:
            neo4j_client: Neo4j client instance.
            enable_belief_classification: Whether to classify beliefs from response text.
        """
        self.client = neo4j_client
        self.node_manager = NodeManager(neo4j_client)
        self.edge_manager = EdgeManager(neo4j_client)
        self.belief_classifier = BeliefClassifier() if enable_belief_classification else None
        self._enable_belief_classification = enable_belief_classification

    async def initialize_graph(self) -> bool:
        """
        Initialize the graph with required constraints and base nodes.

        Creates:
        - Index constraints for node types
        - BeliefType nodes

        Returns:
            True if initialization succeeded.
        """
        try:
            # Create constraints
            constraints = [
                "CREATE CONSTRAINT brand_normalized_name IF NOT EXISTS FOR (b:Brand) REQUIRE b.normalized_name IS UNIQUE",
                "CREATE CONSTRAINT icp_id IF NOT EXISTS FOR (i:ICP) REQUIRE i.id IS UNIQUE",
                "CREATE CONSTRAINT intent_id IF NOT EXISTS FOR (i:Intent) REQUIRE i.id IS UNIQUE",
                "CREATE CONSTRAINT concern_id IF NOT EXISTS FOR (c:Concern) REQUIRE c.id IS UNIQUE",
                "CREATE CONSTRAINT belief_type IF NOT EXISTS FOR (bt:BeliefType) REQUIRE bt.type IS UNIQUE",
                "CREATE CONSTRAINT conversation_id IF NOT EXISTS FOR (c:Conversation) REQUIRE c.id IS UNIQUE",
            ]

            for constraint in constraints:
                try:
                    await self.client.execute_query(constraint, {})
                except Exception as e:
                    # Constraint might already exist
                    logger.debug(f"Constraint creation note: {e}")

            # Create indexes for better query performance
            indexes = [
                "CREATE INDEX brand_id IF NOT EXISTS FOR (b:Brand) ON (b.id)",
                "CREATE INDEX brand_name IF NOT EXISTS FOR (b:Brand) ON (b.name)",
                "CREATE INDEX icp_website IF NOT EXISTS FOR (i:ICP) ON (i.website_id)",
                "CREATE INDEX intent_type IF NOT EXISTS FOR (i:Intent) ON (i.intent_type)",
                "CREATE INDEX intent_funnel IF NOT EXISTS FOR (i:Intent) ON (i.funnel_stage)",
            ]

            for index in indexes:
                try:
                    await self.client.execute_query(index, {})
                except Exception as e:
                    logger.debug(f"Index creation note: {e}")

            # Ensure BeliefType nodes exist
            await self.node_manager.ensure_belief_types()

            logger.info("Graph initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Graph initialization failed: {e}")
            return False

    # =========================================================================
    # BATCH NODE CREATION
    # =========================================================================

    async def create_nodes_batch(self, nodes: BatchNodeCreate) -> BatchOperationResult:
        """
        Create multiple nodes in batch.

        Args:
            nodes: BatchNodeCreate with nodes to create.

        Returns:
            BatchOperationResult with counts.
        """
        total_created = 0
        errors = []

        try:
            if nodes.brands:
                count = await self.node_manager.create_brands_batch(nodes.brands)
                total_created += count

            if nodes.icps:
                count = await self.node_manager.create_icps_batch(nodes.icps)
                total_created += count

            if nodes.intents:
                count = await self.node_manager.create_intents_batch(nodes.intents)
                total_created += count

            if nodes.concerns:
                count = await self.node_manager.create_concerns_batch(nodes.concerns)
                total_created += count

            if nodes.conversations:
                count = await self.node_manager.create_conversations_batch(nodes.conversations)
                total_created += count

        except Exception as e:
            errors.append(str(e))
            logger.error(f"Batch node creation error: {e}")

        return BatchOperationResult(
            success=len(errors) == 0,
            created=total_created,
            errors=errors,
        )

    # =========================================================================
    # BATCH EDGE CREATION
    # =========================================================================

    async def create_edges_batch(self, edges: BatchEdgeCreate) -> BatchOperationResult:
        """
        Create multiple edges in batch.

        Args:
            edges: BatchEdgeCreate with edges to create.

        Returns:
            BatchOperationResult with counts.
        """
        total_created = 0
        errors = []

        try:
            if edges.co_mentions:
                count = await self.edge_manager.create_co_mentions_batch(edges.co_mentions)
                total_created += count

            if edges.has_concerns:
                count = await self.edge_manager.create_has_concerns_batch(edges.has_concerns)
                total_created += count

            if edges.initiates:
                count = await self.edge_manager.create_initiates_batch(edges.initiates)
                total_created += count

            if edges.triggers:
                count = await self.edge_manager.create_triggers_batch(edges.triggers)
                total_created += count

            if edges.contains:
                count = await self.edge_manager.create_contains_batch(edges.contains)
                total_created += count

            if edges.ranks_for:
                count = await self.edge_manager.create_ranks_for_batch(edges.ranks_for)
                total_created += count

            if edges.installs_beliefs:
                count = await self.edge_manager.create_installs_beliefs_batch(edges.installs_beliefs)
                total_created += count

            if edges.recommends:
                count = await self.edge_manager.create_recommends_batch(edges.recommends)
                total_created += count

            if edges.ignores:
                count = await self.edge_manager.create_ignores_batch(edges.ignores)
                total_created += count

        except Exception as e:
            errors.append(str(e))
            logger.error(f"Batch edge creation error: {e}")

        return BatchOperationResult(
            success=len(errors) == 0,
            created=total_created,
            errors=errors,
        )

    # =========================================================================
    # GRAPH BUILDING FROM SIMULATION DATA
    # =========================================================================

    async def build_from_simulation(
        self,
        request: GraphBuildRequest,
        simulation_data: dict[str, Any],
    ) -> GraphBuildResponse:
        """
        Build graph from simulation run data.

        Args:
            request: Build request parameters.
            simulation_data: Data from simulation run containing:
                - icps: List of ICP data
                - conversations: List of conversation data
                - prompts: List of prompt/intent data
                - responses: List of LLM response data with brand states

        Returns:
            GraphBuildResponse with build results.
        """
        stats = BuildStats()

        try:
            # Initialize graph if needed
            await self.initialize_graph()

            # Step 1: Create ICP nodes
            if "icps" in simulation_data:
                await self._build_icps(simulation_data["icps"], stats)

            # Step 2: Create Conversation nodes
            if "conversations" in simulation_data:
                await self._build_conversations(simulation_data["conversations"], stats)

            # Step 3: Create Intent nodes from prompts
            if "prompts" in simulation_data:
                await self._build_intents(simulation_data["prompts"], stats)

            # Step 4: Process LLM responses to build brands and relationships
            if "responses" in simulation_data:
                await self._build_from_responses(simulation_data["responses"], stats)

            logger.info(
                f"Graph build complete: {stats.nodes_created} nodes, "
                f"{stats.edges_created} edges in {stats.duration_ms}ms"
            )

            return GraphBuildResponse(
                success=len(stats.errors) == 0,
                nodes_created=stats.nodes_created,
                edges_created=stats.edges_created,
                nodes_updated=stats.nodes_updated,
                edges_updated=stats.edges_updated,
                errors=stats.errors,
                build_duration_ms=stats.duration_ms,
            )

        except Exception as e:
            logger.error(f"Graph build failed: {e}")
            stats.errors.append(str(e))
            return GraphBuildResponse(
                success=False,
                errors=stats.errors,
                build_duration_ms=stats.duration_ms,
            )

    async def _build_icps(self, icps_data: list[dict], stats: BuildStats) -> None:
        """Build ICP nodes and their concerns."""
        icp_nodes = []
        concern_nodes = []
        has_concern_edges = []

        for icp_data in icps_data:
            # Create ICP node
            icp_node = ICPNode(
                id=str(icp_data["id"]),
                name=icp_data["name"],
                website_id=str(icp_data["website_id"]),
                demographics=icp_data.get("demographics", {}),
                pain_points=icp_data.get("pain_points", []),
                goals=icp_data.get("goals", []),
            )
            icp_nodes.append(icp_node)

            # Create Concern nodes from pain points
            for i, pain_point in enumerate(icp_data.get("pain_points", [])):
                concern_id = f"{icp_data['id']}_concern_{i}"
                concern_node = ConcernNode(
                    id=concern_id,
                    description=pain_point,
                    category="pain_point",
                )
                concern_nodes.append(concern_node)

                has_concern_edges.append(HasConcernEdge(
                    icp_id=str(icp_data["id"]),
                    concern_id=concern_id,
                    priority=i + 1,
                ))

        # Batch create
        if icp_nodes:
            count = await self.node_manager.create_icps_batch(icp_nodes)
            stats.nodes_created += count

        if concern_nodes:
            count = await self.node_manager.create_concerns_batch(concern_nodes)
            stats.nodes_created += count

        if has_concern_edges:
            count = await self.edge_manager.create_has_concerns_batch(has_concern_edges)
            stats.edges_created += count

    async def _build_conversations(self, conversations_data: list[dict], stats: BuildStats) -> None:
        """Build Conversation nodes and ICP relationships."""
        conv_nodes = []
        initiates_edges = []

        for conv_data in conversations_data:
            conv_node = ConversationNode(
                id=str(conv_data["id"]),
                topic=conv_data["topic"],
                context=conv_data.get("context"),
            )
            conv_nodes.append(conv_node)

            if "icp_id" in conv_data:
                initiates_edges.append(InitiatesEdge(
                    icp_id=str(conv_data["icp_id"]),
                    conversation_id=str(conv_data["id"]),
                ))

        if conv_nodes:
            count = await self.node_manager.create_conversations_batch(conv_nodes)
            stats.nodes_created += count

        if initiates_edges:
            count = await self.edge_manager.create_initiates_batch(initiates_edges)
            stats.edges_created += count

    async def _build_intents(self, prompts_data: list[dict], stats: BuildStats) -> None:
        """Build Intent nodes from prompt classifications."""
        intent_nodes = []
        contains_edges = []
        triggers_edges = []

        for prompt_data in prompts_data:
            classification = prompt_data.get("classification", {})
            if not classification:
                continue

            intent_node = IntentNode(
                id=str(prompt_data["id"]),
                prompt_id=str(prompt_data["id"]),
                intent_type=IntentTypeEnum(classification.get("intent_type", "informational")),
                funnel_stage=FunnelStageEnum(classification.get("funnel_stage", "awareness")),
                buying_signal=classification.get("buying_signal", 0.0),
                trust_need=classification.get("trust_need", 0.0),
                query_text=prompt_data.get("prompt_text"),
            )
            intent_nodes.append(intent_node)

            # Link to conversation if available
            if "conversation_id" in prompt_data:
                contains_edges.append(ContainsEdge(
                    conversation_id=str(prompt_data["conversation_id"]),
                    intent_id=str(prompt_data["id"]),
                ))

        if intent_nodes:
            count = await self.node_manager.create_intents_batch(intent_nodes)
            stats.nodes_created += count

        if contains_edges:
            count = await self.edge_manager.create_contains_batch(contains_edges)
            stats.edges_created += count

    async def _build_from_responses(self, responses_data: list[dict], stats: BuildStats) -> None:
        """
        Build brand nodes and relationships from LLM responses.

        Implements belief type classification as defined in ARCHITECTURE.md:
        - If belief_sold is provided in brand_state, uses that directly
        - Otherwise, uses BeliefClassifier to classify from response text
        - Creates INSTALLS_BELIEF relationships per ARCHITECTURE.md diagram
        """
        brand_nodes = {}  # normalized_name -> BrandNode
        llm_providers = {}  # (name, model) -> LLMProviderNode

        ranks_for_edges = []
        installs_belief_edges = []
        recommends_edges = []
        ignores_edges = []
        co_mention_pairs = {}  # (brand1, brand2, provider) -> count

        for response_data in responses_data:
            provider_name = response_data.get("llm_provider", "unknown")
            model_name = response_data.get("llm_model", "unknown")
            prompt_id = str(response_data.get("prompt_id", ""))
            response_text = response_data.get("response_text", "")

            # Get intent type for context-aware belief classification
            intent_type = None
            classification = response_data.get("classification", {})
            if classification:
                intent_type_str = classification.get("intent_type")
                if intent_type_str:
                    try:
                        intent_type = IntentTypeEnum(intent_type_str)
                    except ValueError:
                        pass

            # Track LLM provider
            provider_key = (provider_name, model_name)
            if provider_key not in llm_providers:
                llm_providers[provider_key] = LLMProviderNode(
                    name=provider_name,
                    model=model_name,
                )

            # Process brand states
            brand_states = response_data.get("brand_states", [])
            response_brands = []

            for brand_state in brand_states:
                brand_name = brand_state.get("brand_name", "")
                normalized = brand_state.get("normalized_name", brand_name.lower().strip())

                # Create/update brand node
                if normalized and normalized not in brand_nodes:
                    brand_nodes[normalized] = BrandNode(
                        id=brand_state.get("brand_id", normalized),
                        name=brand_name,
                        normalized_name=normalized,
                        is_tracked=brand_state.get("is_tracked", False),
                    )

                response_brands.append(normalized)

                presence = brand_state.get("presence", "mentioned")
                position = brand_state.get("position_rank")
                belief = brand_state.get("belief_sold")
                confidence = brand_state.get("confidence", 0.8)

                # Classify belief if not provided and classifier is enabled
                if not belief and self._enable_belief_classification and self.belief_classifier and response_text:
                    belief_classification = self._classify_belief_for_brand(
                        response_text=response_text,
                        brand_name=brand_name,
                        presence_state=PresenceStateEnum(presence) if presence else None,
                        intent_type=intent_type,
                    )
                    if belief_classification:
                        belief = belief_classification.belief_type.value
                        confidence = belief_classification.confidence

                # Create RANKS_FOR edge
                if prompt_id and position:
                    ranks_for_edges.append(RanksForEdge(
                        brand_id=normalized,
                        intent_id=prompt_id,
                        position=position,
                        presence=PresenceStateEnum(presence),
                        llm_provider=provider_name,
                        count=1,
                    ))

                # Create INSTALLS_BELIEF edge (per ARCHITECTURE.md)
                if belief:
                    installs_belief_edges.append(InstallsBeliefEdge(
                        brand_id=normalized,
                        belief_type=BeliefTypeEnum(belief),
                        intent_id=prompt_id,
                        llm_provider=provider_name,
                        count=1,
                        confidence=confidence,
                    ))

                # Create RECOMMENDS or IGNORES edge
                if presence == "recommended":
                    recommends_edges.append(RecommendsEdge(
                        llm_provider=provider_name,
                        llm_model=model_name,
                        brand_id=normalized,
                        intent_id=prompt_id,
                        position=position or 1,
                        belief_type=BeliefTypeEnum(belief) if belief else None,
                    ))
                elif presence == "ignored":
                    # Find what was recommended instead
                    competitor = None
                    for other in brand_states:
                        if other.get("presence") == "recommended":
                            competitor = other.get("normalized_name")
                            break
                    ignores_edges.append(IgnoresEdge(
                        llm_provider=provider_name,
                        llm_model=model_name,
                        brand_id=normalized,
                        intent_id=prompt_id,
                        competitor_mentioned=competitor,
                    ))

            # Track co-mentions
            for i, brand1 in enumerate(response_brands):
                for brand2 in response_brands[i + 1:]:
                    key = (min(brand1, brand2), max(brand1, brand2), provider_name)
                    co_mention_pairs[key] = co_mention_pairs.get(key, 0) + 1

        # Batch create all nodes
        if brand_nodes:
            brand_list = list(brand_nodes.values())
            count = await self.node_manager.create_brands_batch(brand_list)
            stats.nodes_created += count

        if llm_providers:
            provider_list = list(llm_providers.values())
            count = await self.node_manager.create_llm_providers_batch(provider_list)
            stats.nodes_created += count

        # Batch create edges
        if ranks_for_edges:
            count = await self.edge_manager.create_ranks_for_batch(ranks_for_edges)
            stats.edges_created += count

        if installs_belief_edges:
            count = await self.edge_manager.create_installs_beliefs_batch(installs_belief_edges)
            stats.edges_created += count

        if recommends_edges:
            count = await self.edge_manager.create_recommends_batch(recommends_edges)
            stats.edges_created += count

        if ignores_edges:
            count = await self.edge_manager.create_ignores_batch(ignores_edges)
            stats.edges_created += count

        # Create co-mention edges
        if co_mention_pairs:
            co_mention_edges = []
            for (brand1, brand2, provider), count in co_mention_pairs.items():
                co_mention_edges.append(CoMentionedEdge(
                    source_brand_id=brand1,
                    target_brand_id=brand2,
                    count=count,
                    llm_provider=provider,
                ))
            edge_count = await self.edge_manager.create_co_mentions_batch(co_mention_edges)
            stats.edges_created += edge_count

    # =========================================================================
    # INCREMENTAL UPDATES
    # =========================================================================

    async def update_brand_rankings(
        self,
        brand_id: str,
        intent_id: str,
        llm_provider: str,
        position: int,
        presence: PresenceStateEnum,
    ) -> bool:
        """
        Update brand rankings for a single response.

        Args:
            brand_id: Brand ID.
            intent_id: Intent ID.
            llm_provider: LLM provider name.
            position: Position rank.
            presence: Presence state.

        Returns:
            True if update succeeded.
        """
        edge = RanksForEdge(
            brand_id=brand_id,
            intent_id=intent_id,
            position=position,
            presence=presence,
            llm_provider=llm_provider,
            count=1,
        )
        result = await self.edge_manager.create_ranks_for(edge)
        return result is not None

    async def add_belief_installation(
        self,
        brand_id: str,
        belief_type: BeliefTypeEnum,
        intent_id: str | None = None,
        llm_provider: str | None = None,
        confidence: float = 0.8,
    ) -> bool:
        """
        Add a belief installation record.

        Args:
            brand_id: Brand ID.
            belief_type: Type of belief installed.
            intent_id: Optional intent ID.
            llm_provider: Optional LLM provider.
            confidence: Confidence score.

        Returns:
            True if creation succeeded.
        """
        edge = InstallsBeliefEdge(
            brand_id=brand_id,
            belief_type=belief_type,
            intent_id=intent_id,
            llm_provider=llm_provider,
            count=1,
            confidence=confidence,
        )
        result = await self.edge_manager.create_installs_belief(edge)
        return result is not None

    # =========================================================================
    # BELIEF CLASSIFICATION METHODS
    # =========================================================================

    def _classify_belief_for_brand(
        self,
        response_text: str,
        brand_name: str,
        presence_state: PresenceStateEnum | None = None,
        intent_type: IntentTypeEnum | None = None,
    ) -> BeliefClassification | None:
        """
        Classify belief type for a brand from response text.

        Uses context-aware classification considering:
        - Text context around brand mention
        - Presence state (recommended, trusted, etc.)
        - Intent type (informational, evaluation, decision)

        Args:
            response_text: Full LLM response text.
            brand_name: Brand name to analyze.
            presence_state: Brand's presence state for context.
            intent_type: Query intent type for context.

        Returns:
            BeliefClassification or None if no belief detected.
        """
        if not self.belief_classifier:
            return None

        return self.belief_classifier.classify_belief(
            context=response_text,
            brand_name=brand_name,
            presence_state=presence_state,
            intent_type=intent_type,
        )

    def classify_beliefs_from_text(
        self,
        text: str,
        brand_name: str | None = None,
        presence_state: PresenceStateEnum | None = None,
        intent_type: IntentTypeEnum | None = None,
    ) -> list[BeliefClassification]:
        """
        Classify all belief types from text.

        Public method for standalone belief classification.

        Args:
            text: Text to analyze.
            brand_name: Optional brand name for context extraction.
            presence_state: Optional presence state for score adjustment.
            intent_type: Optional intent type for score adjustment.

        Returns:
            List of BeliefClassification sorted by confidence.
        """
        if not self.belief_classifier:
            return []

        return self.belief_classifier.classify_all_beliefs(
            context=text,
            presence_state=presence_state,
            intent_type=intent_type,
        )

    def analyze_brand_beliefs(
        self,
        response_text: str,
        brand_name: str,
        presence_state: PresenceStateEnum | None = None,
        intent_type: IntentTypeEnum | None = None,
    ) -> BeliefAnalysis:
        """
        Perform full belief analysis for a brand.

        Analyzes what beliefs the LLM response installs about a brand,
        implementing the belief type classification from ARCHITECTURE.md.

        Args:
            response_text: Full LLM response text.
            brand_name: Brand name to analyze.
            presence_state: Brand's presence state.
            intent_type: Query intent type.

        Returns:
            BeliefAnalysis with primary and all detected beliefs.
        """
        if not self.belief_classifier:
            return BeliefAnalysis(
                brand_name=brand_name,
                primary_belief=None,
                presence_state=presence_state,
                intent_type=intent_type,
            )

        return self.belief_classifier.analyze_brand_beliefs(
            response_text=response_text,
            brand_name=brand_name,
            presence_state=presence_state,
            intent_type=intent_type,
        )

    async def classify_and_store_beliefs(
        self,
        response_text: str,
        brand_name: str,
        intent_id: str | None = None,
        llm_provider: str | None = None,
        presence_state: PresenceStateEnum | None = None,
        intent_type: IntentTypeEnum | None = None,
    ) -> list[InstallsBeliefEdge]:
        """
        Classify beliefs from text and create INSTALLS_BELIEF edges.

        Convenience method that combines classification and storage.

        Args:
            response_text: LLM response text to analyze.
            brand_name: Brand being analyzed.
            intent_id: Optional intent ID.
            llm_provider: Optional LLM provider.
            presence_state: Optional presence state.
            intent_type: Optional intent type.

        Returns:
            List of InstallsBeliefEdge created.
        """
        beliefs = self.classify_beliefs_from_text(
            text=response_text,
            brand_name=brand_name,
            presence_state=presence_state,
            intent_type=intent_type,
        )

        edges = []
        normalized_name = brand_name.lower().strip()

        for belief_classification in beliefs:
            if belief_classification.confidence >= 0.3:  # Threshold for storage
                edge = InstallsBeliefEdge(
                    brand_id=normalized_name,
                    belief_type=belief_classification.belief_type,
                    intent_id=intent_id,
                    llm_provider=llm_provider,
                    count=1,
                    confidence=belief_classification.confidence,
                )
                edges.append(edge)

                # Store in graph
                await self.edge_manager.create_installs_belief(edge)

        return edges

    # =========================================================================
    # CLEANUP METHODS
    # =========================================================================

    async def clear_website_data(self, website_id: str) -> int:
        """
        Clear all graph data for a website.

        Args:
            website_id: Website ID to clear.

        Returns:
            Number of nodes deleted.
        """
        query = """
        MATCH (i:ICP {website_id: $website_id})
        OPTIONAL MATCH (i)-[:HAS_CONCERN]->(c:Concern)
        OPTIONAL MATCH (i)-[:INITIATES]->(conv:Conversation)
        OPTIONAL MATCH (conv)-[:CONTAINS]->(intent:Intent)
        DETACH DELETE i, c, conv, intent
        RETURN count(*) as deleted
        """
        result = await self.client.execute_query(query, {"website_id": website_id})
        deleted = result[0]["deleted"] if result else 0
        logger.info(f"Cleared {deleted} nodes for website {website_id}")
        return deleted

    async def clear_all(self) -> int:
        """
        Clear all graph data. Use with caution!

        Returns:
            Number of nodes deleted.
        """
        query = """
        MATCH (n)
        DETACH DELETE n
        RETURN count(n) as deleted
        """
        result = await self.client.execute_query(query, {})
        deleted = result[0]["deleted"] if result else 0
        logger.warning(f"Cleared all {deleted} nodes from graph")
        return deleted
