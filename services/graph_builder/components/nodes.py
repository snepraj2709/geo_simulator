"""
Node Manager for Knowledge Graph Builder.

Handles creation, update, and retrieval of all node types in Neo4j.
"""

from typing import Any

from shared.utils.logging import get_logger
from shared.db.neo4j_client import Neo4jClient

from services.graph_builder.schemas import (
    BrandNode,
    ICPNode,
    IntentNode,
    ConcernNode,
    BeliefTypeNode,
    LLMProviderNode,
    ConversationNode,
    BeliefTypeEnum,
)

logger = get_logger(__name__)


class NodeManager:
    """
    Manages node operations in the Neo4j knowledge graph.

    Handles creation, update, and retrieval of:
    - Brand nodes
    - ICP nodes
    - Intent nodes
    - Concern nodes
    - BeliefType nodes
    - LLMProvider nodes
    - Conversation nodes
    """

    def __init__(self, neo4j_client: Neo4jClient):
        """
        Initialize NodeManager.

        Args:
            neo4j_client: Neo4j client instance.
        """
        self.client = neo4j_client

    # =========================================================================
    # BRAND NODES
    # =========================================================================

    async def create_brand(self, brand: BrandNode) -> dict[str, Any] | None:
        """
        Create or update a Brand node.

        Args:
            brand: Brand node data.

        Returns:
            Created/updated node data or None on failure.
        """
        query = """
        MERGE (b:Brand {normalized_name: $normalized_name})
        SET b.id = $id,
            b.name = $name,
            b.domain = $domain,
            b.industry = $industry,
            b.is_tracked = $is_tracked,
            b.updated_at = datetime()
        RETURN b
        """
        params = brand.model_dump()
        result = await self.client.execute_query(query, params)
        if result and len(result) > 0:
            logger.debug(f"Created/updated Brand node: {brand.name}")
            return dict(result[0]["b"])
        return None

    async def get_brand(self, normalized_name: str) -> dict[str, Any] | None:
        """Get a Brand node by normalized name."""
        query = """
        MATCH (b:Brand {normalized_name: $normalized_name})
        RETURN b
        """
        result = await self.client.execute_query(query, {"normalized_name": normalized_name})
        if result and len(result) > 0:
            return dict(result[0]["b"])
        return None

    async def get_brand_by_id(self, brand_id: str) -> dict[str, Any] | None:
        """Get a Brand node by ID."""
        query = """
        MATCH (b:Brand {id: $id})
        RETURN b
        """
        result = await self.client.execute_query(query, {"id": brand_id})
        if result and len(result) > 0:
            return dict(result[0]["b"])
        return None

    async def create_brands_batch(self, brands: list[BrandNode]) -> int:
        """
        Create multiple Brand nodes in batch.

        Args:
            brands: List of brand nodes.

        Returns:
            Number of nodes created/updated.
        """
        query = """
        UNWIND $brands AS brand
        MERGE (b:Brand {normalized_name: brand.normalized_name})
        SET b.id = brand.id,
            b.name = brand.name,
            b.domain = brand.domain,
            b.industry = brand.industry,
            b.is_tracked = brand.is_tracked,
            b.updated_at = datetime()
        RETURN count(b) as count
        """
        brands_data = [b.model_dump() for b in brands]
        result = await self.client.execute_query(query, {"brands": brands_data})
        count = result[0]["count"] if result else 0
        logger.info(f"Batch created/updated {count} Brand nodes")
        return count

    # =========================================================================
    # ICP NODES
    # =========================================================================

    async def create_icp(self, icp: ICPNode) -> dict[str, Any] | None:
        """Create or update an ICP node."""
        query = """
        MERGE (i:ICP {id: $id})
        SET i.name = $name,
            i.website_id = $website_id,
            i.demographics = $demographics,
            i.pain_points = $pain_points,
            i.goals = $goals,
            i.updated_at = datetime()
        RETURN i
        """
        params = icp.model_dump()
        result = await self.client.execute_query(query, params)
        if result and len(result) > 0:
            logger.debug(f"Created/updated ICP node: {icp.name}")
            return dict(result[0]["i"])
        return None

    async def get_icp(self, icp_id: str) -> dict[str, Any] | None:
        """Get an ICP node by ID."""
        query = """
        MATCH (i:ICP {id: $id})
        RETURN i
        """
        result = await self.client.execute_query(query, {"id": icp_id})
        if result and len(result) > 0:
            return dict(result[0]["i"])
        return None

    async def get_icps_by_website(self, website_id: str) -> list[dict[str, Any]]:
        """Get all ICP nodes for a website."""
        query = """
        MATCH (i:ICP {website_id: $website_id})
        RETURN i
        ORDER BY i.name
        """
        result = await self.client.execute_query(query, {"website_id": website_id})
        return [dict(r["i"]) for r in result] if result else []

    async def create_icps_batch(self, icps: list[ICPNode]) -> int:
        """Create multiple ICP nodes in batch."""
        query = """
        UNWIND $icps AS icp
        MERGE (i:ICP {id: icp.id})
        SET i.name = icp.name,
            i.website_id = icp.website_id,
            i.demographics = icp.demographics,
            i.pain_points = icp.pain_points,
            i.goals = icp.goals,
            i.updated_at = datetime()
        RETURN count(i) as count
        """
        icps_data = [i.model_dump() for i in icps]
        result = await self.client.execute_query(query, {"icps": icps_data})
        count = result[0]["count"] if result else 0
        logger.info(f"Batch created/updated {count} ICP nodes")
        return count

    # =========================================================================
    # INTENT NODES
    # =========================================================================

    async def create_intent(self, intent: IntentNode) -> dict[str, Any] | None:
        """Create or update an Intent node."""
        query = """
        MERGE (i:Intent {id: $id})
        SET i.prompt_id = $prompt_id,
            i.intent_type = $intent_type,
            i.funnel_stage = $funnel_stage,
            i.buying_signal = $buying_signal,
            i.trust_need = $trust_need,
            i.query_text = $query_text,
            i.updated_at = datetime()
        RETURN i
        """
        params = intent.model_dump()
        params["intent_type"] = intent.intent_type.value
        params["funnel_stage"] = intent.funnel_stage.value
        result = await self.client.execute_query(query, params)
        if result and len(result) > 0:
            logger.debug(f"Created/updated Intent node: {intent.id}")
            return dict(result[0]["i"])
        return None

    async def get_intent(self, intent_id: str) -> dict[str, Any] | None:
        """Get an Intent node by ID."""
        query = """
        MATCH (i:Intent {id: $id})
        RETURN i
        """
        result = await self.client.execute_query(query, {"id": intent_id})
        if result and len(result) > 0:
            return dict(result[0]["i"])
        return None

    async def create_intents_batch(self, intents: list[IntentNode]) -> int:
        """Create multiple Intent nodes in batch."""
        query = """
        UNWIND $intents AS intent
        MERGE (i:Intent {id: intent.id})
        SET i.prompt_id = intent.prompt_id,
            i.intent_type = intent.intent_type,
            i.funnel_stage = intent.funnel_stage,
            i.buying_signal = intent.buying_signal,
            i.trust_need = intent.trust_need,
            i.query_text = intent.query_text,
            i.updated_at = datetime()
        RETURN count(i) as count
        """
        intents_data = []
        for intent in intents:
            data = intent.model_dump()
            data["intent_type"] = intent.intent_type.value
            data["funnel_stage"] = intent.funnel_stage.value
            intents_data.append(data)
        result = await self.client.execute_query(query, {"intents": intents_data})
        count = result[0]["count"] if result else 0
        logger.info(f"Batch created/updated {count} Intent nodes")
        return count

    # =========================================================================
    # CONCERN NODES
    # =========================================================================

    async def create_concern(self, concern: ConcernNode) -> dict[str, Any] | None:
        """Create or update a Concern node."""
        query = """
        MERGE (c:Concern {id: $id})
        SET c.description = $description,
            c.category = $category,
            c.updated_at = datetime()
        RETURN c
        """
        params = concern.model_dump()
        result = await self.client.execute_query(query, params)
        if result and len(result) > 0:
            logger.debug(f"Created/updated Concern node: {concern.id}")
            return dict(result[0]["c"])
        return None

    async def get_concern(self, concern_id: str) -> dict[str, Any] | None:
        """Get a Concern node by ID."""
        query = """
        MATCH (c:Concern {id: $id})
        RETURN c
        """
        result = await self.client.execute_query(query, {"id": concern_id})
        if result and len(result) > 0:
            return dict(result[0]["c"])
        return None

    async def create_concerns_batch(self, concerns: list[ConcernNode]) -> int:
        """Create multiple Concern nodes in batch."""
        query = """
        UNWIND $concerns AS concern
        MERGE (c:Concern {id: concern.id})
        SET c.description = concern.description,
            c.category = concern.category,
            c.updated_at = datetime()
        RETURN count(c) as count
        """
        concerns_data = [c.model_dump() for c in concerns]
        result = await self.client.execute_query(query, {"concerns": concerns_data})
        count = result[0]["count"] if result else 0
        logger.info(f"Batch created/updated {count} Concern nodes")
        return count

    # =========================================================================
    # BELIEF TYPE NODES
    # =========================================================================

    async def ensure_belief_types(self) -> int:
        """
        Ensure all BeliefType nodes exist in the graph.

        Creates the 6 standard belief type nodes if they don't exist.

        Returns:
            Number of nodes created.
        """
        query = """
        UNWIND $types AS type
        MERGE (bt:BeliefType {type: type})
        RETURN count(bt) as count
        """
        belief_types = [bt.value for bt in BeliefTypeEnum]
        result = await self.client.execute_query(query, {"types": belief_types})
        count = result[0]["count"] if result else 0
        logger.info(f"Ensured {count} BeliefType nodes exist")
        return count

    async def get_belief_type(self, belief_type: BeliefTypeEnum) -> dict[str, Any] | None:
        """Get a BeliefType node."""
        query = """
        MATCH (bt:BeliefType {type: $type})
        RETURN bt
        """
        result = await self.client.execute_query(query, {"type": belief_type.value})
        if result and len(result) > 0:
            return dict(result[0]["bt"])
        return None

    # =========================================================================
    # LLM PROVIDER NODES
    # =========================================================================

    async def create_llm_provider(self, provider: LLMProviderNode) -> dict[str, Any] | None:
        """Create or update an LLM Provider node."""
        query = """
        MERGE (l:LLMProvider {name: $name, model: $model})
        SET l.updated_at = datetime()
        RETURN l
        """
        params = provider.model_dump()
        result = await self.client.execute_query(query, params)
        if result and len(result) > 0:
            logger.debug(f"Created/updated LLMProvider node: {provider.name}/{provider.model}")
            return dict(result[0]["l"])
        return None

    async def get_llm_provider(self, name: str, model: str) -> dict[str, Any] | None:
        """Get an LLM Provider node."""
        query = """
        MATCH (l:LLMProvider {name: $name, model: $model})
        RETURN l
        """
        result = await self.client.execute_query(query, {"name": name, "model": model})
        if result and len(result) > 0:
            return dict(result[0]["l"])
        return None

    async def create_llm_providers_batch(self, providers: list[LLMProviderNode]) -> int:
        """Create multiple LLM Provider nodes in batch."""
        query = """
        UNWIND $providers AS provider
        MERGE (l:LLMProvider {name: provider.name, model: provider.model})
        SET l.updated_at = datetime()
        RETURN count(l) as count
        """
        providers_data = [p.model_dump() for p in providers]
        result = await self.client.execute_query(query, {"providers": providers_data})
        count = result[0]["count"] if result else 0
        logger.info(f"Batch created/updated {count} LLMProvider nodes")
        return count

    # =========================================================================
    # CONVERSATION NODES
    # =========================================================================

    async def create_conversation(self, conversation: ConversationNode) -> dict[str, Any] | None:
        """Create or update a Conversation node."""
        query = """
        MERGE (c:Conversation {id: $id})
        SET c.topic = $topic,
            c.context = $context,
            c.updated_at = datetime()
        RETURN c
        """
        params = conversation.model_dump()
        result = await self.client.execute_query(query, params)
        if result and len(result) > 0:
            logger.debug(f"Created/updated Conversation node: {conversation.topic}")
            return dict(result[0]["c"])
        return None

    async def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        """Get a Conversation node by ID."""
        query = """
        MATCH (c:Conversation {id: $id})
        RETURN c
        """
        result = await self.client.execute_query(query, {"id": conversation_id})
        if result and len(result) > 0:
            return dict(result[0]["c"])
        return None

    async def create_conversations_batch(self, conversations: list[ConversationNode]) -> int:
        """Create multiple Conversation nodes in batch."""
        query = """
        UNWIND $conversations AS conv
        MERGE (c:Conversation {id: conv.id})
        SET c.topic = conv.topic,
            c.context = conv.context,
            c.updated_at = datetime()
        RETURN count(c) as count
        """
        conversations_data = [c.model_dump() for c in conversations]
        result = await self.client.execute_query(query, {"conversations": conversations_data})
        count = result[0]["count"] if result else 0
        logger.info(f"Batch created/updated {count} Conversation nodes")
        return count

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    async def delete_node(self, label: str, node_id: str) -> bool:
        """
        Delete a node by label and ID.

        Args:
            label: Node label (Brand, ICP, etc.)
            node_id: Node ID.

        Returns:
            True if deleted, False otherwise.
        """
        query = f"""
        MATCH (n:{label} {{id: $id}})
        DETACH DELETE n
        RETURN count(n) as count
        """
        result = await self.client.execute_query(query, {"id": node_id})
        deleted = result[0]["count"] > 0 if result else False
        if deleted:
            logger.debug(f"Deleted {label} node: {node_id}")
        return deleted

    async def count_nodes(self, label: str) -> int:
        """Count nodes by label."""
        query = f"""
        MATCH (n:{label})
        RETURN count(n) as count
        """
        result = await self.client.execute_query(query, {})
        return result[0]["count"] if result else 0
