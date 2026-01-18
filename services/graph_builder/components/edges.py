"""
Edge Manager for Knowledge Graph Builder.

Handles creation, update, and retrieval of all relationship types in Neo4j.
"""

from typing import Any

from shared.utils.logging import get_logger
from shared.db.neo4j_client import Neo4jClient

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
)

logger = get_logger(__name__)


class EdgeManager:
    """
    Manages edge/relationship operations in the Neo4j knowledge graph.

    Handles creation, update, and retrieval of:
    - CO_MENTIONED (Brand -> Brand)
    - COMPETES_WITH (Brand -> Brand)
    - HAS_CONCERN (ICP -> Concern)
    - INITIATES (ICP -> Conversation)
    - TRIGGERS (Concern -> Intent)
    - CONTAINS (Conversation -> Intent)
    - RANKS_FOR (Brand -> Intent)
    - INSTALLS_BELIEF (Brand -> BeliefType)
    - RECOMMENDS (LLMProvider -> Brand)
    - IGNORES (LLMProvider -> Brand)
    """

    def __init__(self, neo4j_client: Neo4jClient):
        """
        Initialize EdgeManager.

        Args:
            neo4j_client: Neo4j client instance.
        """
        self.client = neo4j_client

    # =========================================================================
    # CO_MENTIONED EDGES (Brand -> Brand)
    # =========================================================================

    async def create_co_mention(self, edge: CoMentionedEdge) -> dict[str, Any] | None:
        """
        Create or update a CO_MENTIONED relationship between brands.

        If the relationship exists, increments count and updates avg_position_delta.
        """
        query = """
        MATCH (b1:Brand {id: $source_brand_id})
        MATCH (b2:Brand {id: $target_brand_id})
        MERGE (b1)-[r:CO_MENTIONED {llm_provider: $llm_provider}]->(b2)
        ON CREATE SET
            r.count = $count,
            r.avg_position_delta = $avg_position_delta,
            r.created_at = datetime()
        ON MATCH SET
            r.count = r.count + $count,
            r.avg_position_delta = CASE
                WHEN $avg_position_delta IS NOT NULL
                THEN (r.avg_position_delta * (r.count - $count) + $avg_position_delta * $count) / r.count
                ELSE r.avg_position_delta
            END,
            r.updated_at = datetime()
        RETURN r, b1.name as source, b2.name as target
        """
        params = edge.model_dump()
        params["llm_provider"] = params.get("llm_provider") or "all"
        result = await self.client.execute_query(query, params)
        if result and len(result) > 0:
            logger.debug(f"Created/updated CO_MENTIONED: {result[0]['source']} -> {result[0]['target']}")
            return dict(result[0]["r"])
        return None

    async def get_co_mentions(
        self,
        brand_id: str,
        llm_provider: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get brands co-mentioned with the given brand."""
        query = """
        MATCH (b1:Brand {id: $brand_id})-[r:CO_MENTIONED]-(b2:Brand)
        WHERE $llm_provider IS NULL OR r.llm_provider = $llm_provider
        RETURN b2.name as brand_name, b2.id as brand_id,
               r.count as count, r.avg_position_delta as avg_position_delta
        ORDER BY r.count DESC
        LIMIT $limit
        """
        result = await self.client.execute_query(
            query,
            {"brand_id": brand_id, "llm_provider": llm_provider, "limit": limit}
        )
        return [dict(r) for r in result] if result else []

    async def create_co_mentions_batch(self, edges: list[CoMentionedEdge]) -> int:
        """Create multiple CO_MENTIONED relationships in batch."""
        query = """
        UNWIND $edges AS edge
        MATCH (b1:Brand {id: edge.source_brand_id})
        MATCH (b2:Brand {id: edge.target_brand_id})
        MERGE (b1)-[r:CO_MENTIONED {llm_provider: coalesce(edge.llm_provider, 'all')}]->(b2)
        ON CREATE SET
            r.count = edge.count,
            r.avg_position_delta = edge.avg_position_delta,
            r.created_at = datetime()
        ON MATCH SET
            r.count = r.count + edge.count,
            r.updated_at = datetime()
        RETURN count(r) as count
        """
        edges_data = [e.model_dump() for e in edges]
        result = await self.client.execute_query(query, {"edges": edges_data})
        count = result[0]["count"] if result else 0
        logger.info(f"Batch created/updated {count} CO_MENTIONED edges")
        return count

    # =========================================================================
    # COMPETES_WITH EDGES (Brand -> Brand)
    # =========================================================================

    async def create_competes_with(self, edge: CompetesWithEdge) -> dict[str, Any] | None:
        """Create or update a COMPETES_WITH relationship between brands."""
        query = """
        MATCH (b1:Brand {id: $source_brand_id})
        MATCH (b2:Brand {id: $target_brand_id})
        MERGE (b1)-[r:COMPETES_WITH]->(b2)
        SET r.relationship_type = $relationship_type,
            r.updated_at = datetime()
        RETURN r, b1.name as source, b2.name as target
        """
        params = edge.model_dump()
        params["relationship_type"] = edge.relationship_type.value
        result = await self.client.execute_query(query, params)
        if result and len(result) > 0:
            logger.debug(f"Created/updated COMPETES_WITH: {result[0]['source']} -> {result[0]['target']}")
            return dict(result[0]["r"])
        return None

    async def get_competitors(self, brand_id: str) -> list[dict[str, Any]]:
        """Get competitors of a brand."""
        query = """
        MATCH (b1:Brand {id: $brand_id})-[r:COMPETES_WITH]->(b2:Brand)
        RETURN b2.name as brand_name, b2.id as brand_id,
               r.relationship_type as relationship_type
        """
        result = await self.client.execute_query(query, {"brand_id": brand_id})
        return [dict(r) for r in result] if result else []

    # =========================================================================
    # HAS_CONCERN EDGES (ICP -> Concern)
    # =========================================================================

    async def create_has_concern(self, edge: HasConcernEdge) -> dict[str, Any] | None:
        """Create or update a HAS_CONCERN relationship."""
        query = """
        MATCH (i:ICP {id: $icp_id})
        MATCH (c:Concern {id: $concern_id})
        MERGE (i)-[r:HAS_CONCERN]->(c)
        SET r.priority = $priority,
            r.updated_at = datetime()
        RETURN r
        """
        params = edge.model_dump()
        result = await self.client.execute_query(query, params)
        if result and len(result) > 0:
            logger.debug(f"Created/updated HAS_CONCERN: ICP {edge.icp_id} -> Concern {edge.concern_id}")
            return dict(result[0]["r"])
        return None

    async def get_icp_concerns(self, icp_id: str) -> list[dict[str, Any]]:
        """Get concerns for an ICP."""
        query = """
        MATCH (i:ICP {id: $icp_id})-[r:HAS_CONCERN]->(c:Concern)
        RETURN c.id as concern_id, c.description as description,
               c.category as category, r.priority as priority
        ORDER BY r.priority
        """
        result = await self.client.execute_query(query, {"icp_id": icp_id})
        return [dict(r) for r in result] if result else []

    async def create_has_concerns_batch(self, edges: list[HasConcernEdge]) -> int:
        """Create multiple HAS_CONCERN relationships in batch."""
        query = """
        UNWIND $edges AS edge
        MATCH (i:ICP {id: edge.icp_id})
        MATCH (c:Concern {id: edge.concern_id})
        MERGE (i)-[r:HAS_CONCERN]->(c)
        SET r.priority = edge.priority,
            r.updated_at = datetime()
        RETURN count(r) as count
        """
        edges_data = [e.model_dump() for e in edges]
        result = await self.client.execute_query(query, {"edges": edges_data})
        count = result[0]["count"] if result else 0
        logger.info(f"Batch created/updated {count} HAS_CONCERN edges")
        return count

    # =========================================================================
    # INITIATES EDGES (ICP -> Conversation)
    # =========================================================================

    async def create_initiates(self, edge: InitiatesEdge) -> dict[str, Any] | None:
        """Create an INITIATES relationship."""
        query = """
        MATCH (i:ICP {id: $icp_id})
        MATCH (c:Conversation {id: $conversation_id})
        MERGE (i)-[r:INITIATES]->(c)
        SET r.updated_at = datetime()
        RETURN r
        """
        params = edge.model_dump()
        result = await self.client.execute_query(query, params)
        if result and len(result) > 0:
            logger.debug(f"Created INITIATES: ICP {edge.icp_id} -> Conversation {edge.conversation_id}")
            return dict(result[0]["r"])
        return None

    async def create_initiates_batch(self, edges: list[InitiatesEdge]) -> int:
        """Create multiple INITIATES relationships in batch."""
        query = """
        UNWIND $edges AS edge
        MATCH (i:ICP {id: edge.icp_id})
        MATCH (c:Conversation {id: edge.conversation_id})
        MERGE (i)-[r:INITIATES]->(c)
        SET r.updated_at = datetime()
        RETURN count(r) as count
        """
        edges_data = [e.model_dump() for e in edges]
        result = await self.client.execute_query(query, {"edges": edges_data})
        count = result[0]["count"] if result else 0
        logger.info(f"Batch created {count} INITIATES edges")
        return count

    # =========================================================================
    # TRIGGERS EDGES (Concern -> Intent)
    # =========================================================================

    async def create_triggers(self, edge: TriggersEdge) -> dict[str, Any] | None:
        """Create a TRIGGERS relationship."""
        query = """
        MATCH (c:Concern {id: $concern_id})
        MATCH (i:Intent {id: $intent_id})
        MERGE (c)-[r:TRIGGERS]->(i)
        SET r.updated_at = datetime()
        RETURN r
        """
        params = edge.model_dump()
        result = await self.client.execute_query(query, params)
        if result and len(result) > 0:
            logger.debug(f"Created TRIGGERS: Concern {edge.concern_id} -> Intent {edge.intent_id}")
            return dict(result[0]["r"])
        return None

    async def create_triggers_batch(self, edges: list[TriggersEdge]) -> int:
        """Create multiple TRIGGERS relationships in batch."""
        query = """
        UNWIND $edges AS edge
        MATCH (c:Concern {id: edge.concern_id})
        MATCH (i:Intent {id: edge.intent_id})
        MERGE (c)-[r:TRIGGERS]->(i)
        SET r.updated_at = datetime()
        RETURN count(r) as count
        """
        edges_data = [e.model_dump() for e in edges]
        result = await self.client.execute_query(query, {"edges": edges_data})
        count = result[0]["count"] if result else 0
        logger.info(f"Batch created {count} TRIGGERS edges")
        return count

    # =========================================================================
    # CONTAINS EDGES (Conversation -> Intent)
    # =========================================================================

    async def create_contains(self, edge: ContainsEdge) -> dict[str, Any] | None:
        """Create a CONTAINS relationship."""
        query = """
        MATCH (c:Conversation {id: $conversation_id})
        MATCH (i:Intent {id: $intent_id})
        MERGE (c)-[r:CONTAINS]->(i)
        SET r.updated_at = datetime()
        RETURN r
        """
        params = edge.model_dump()
        result = await self.client.execute_query(query, params)
        if result and len(result) > 0:
            logger.debug(f"Created CONTAINS: Conversation {edge.conversation_id} -> Intent {edge.intent_id}")
            return dict(result[0]["r"])
        return None

    async def create_contains_batch(self, edges: list[ContainsEdge]) -> int:
        """Create multiple CONTAINS relationships in batch."""
        query = """
        UNWIND $edges AS edge
        MATCH (c:Conversation {id: edge.conversation_id})
        MATCH (i:Intent {id: edge.intent_id})
        MERGE (c)-[r:CONTAINS]->(i)
        SET r.updated_at = datetime()
        RETURN count(r) as count
        """
        edges_data = [e.model_dump() for e in edges]
        result = await self.client.execute_query(query, {"edges": edges_data})
        count = result[0]["count"] if result else 0
        logger.info(f"Batch created {count} CONTAINS edges")
        return count

    # =========================================================================
    # RANKS_FOR EDGES (Brand -> Intent)
    # =========================================================================

    async def create_ranks_for(self, edge: RanksForEdge) -> dict[str, Any] | None:
        """
        Create or update a RANKS_FOR relationship.

        If the relationship exists, increments count and updates position average.
        """
        query = """
        MATCH (b:Brand {id: $brand_id})
        MATCH (i:Intent {id: $intent_id})
        MERGE (b)-[r:RANKS_FOR {llm_provider: $llm_provider}]->(i)
        ON CREATE SET
            r.position = $position,
            r.presence = $presence,
            r.count = $count,
            r.created_at = datetime()
        ON MATCH SET
            r.position = ($position * $count + r.position * r.count) / (r.count + $count),
            r.count = r.count + $count,
            r.updated_at = datetime()
        RETURN r
        """
        params = edge.model_dump()
        params["presence"] = edge.presence.value
        result = await self.client.execute_query(query, params)
        if result and len(result) > 0:
            logger.debug(f"Created/updated RANKS_FOR: Brand {edge.brand_id} -> Intent {edge.intent_id}")
            return dict(result[0]["r"])
        return None

    async def get_brand_rankings(
        self,
        intent_id: str,
        llm_provider: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get brand rankings for an intent."""
        query = """
        MATCH (b:Brand)-[r:RANKS_FOR]->(i:Intent {id: $intent_id})
        WHERE $llm_provider IS NULL OR r.llm_provider = $llm_provider
        RETURN b.name as brand_name, b.id as brand_id,
               r.position as position, r.presence as presence,
               r.count as count, r.llm_provider as llm_provider
        ORDER BY r.position
        """
        result = await self.client.execute_query(
            query,
            {"intent_id": intent_id, "llm_provider": llm_provider}
        )
        return [dict(r) for r in result] if result else []

    async def create_ranks_for_batch(self, edges: list[RanksForEdge]) -> int:
        """Create multiple RANKS_FOR relationships in batch."""
        query = """
        UNWIND $edges AS edge
        MATCH (b:Brand {id: edge.brand_id})
        MATCH (i:Intent {id: edge.intent_id})
        MERGE (b)-[r:RANKS_FOR {llm_provider: edge.llm_provider}]->(i)
        ON CREATE SET
            r.position = edge.position,
            r.presence = edge.presence,
            r.count = edge.count,
            r.created_at = datetime()
        ON MATCH SET
            r.count = r.count + edge.count,
            r.updated_at = datetime()
        RETURN count(r) as count
        """
        edges_data = []
        for e in edges:
            data = e.model_dump()
            data["presence"] = e.presence.value
            edges_data.append(data)
        result = await self.client.execute_query(query, {"edges": edges_data})
        count = result[0]["count"] if result else 0
        logger.info(f"Batch created/updated {count} RANKS_FOR edges")
        return count

    # =========================================================================
    # INSTALLS_BELIEF EDGES (Brand -> BeliefType)
    # =========================================================================

    async def create_installs_belief(self, edge: InstallsBeliefEdge) -> dict[str, Any] | None:
        """
        Create or update an INSTALLS_BELIEF relationship.

        Tracks which beliefs a brand installs through LLM responses.
        """
        query = """
        MATCH (b:Brand {id: $brand_id})
        MATCH (bt:BeliefType {type: $belief_type})
        MERGE (b)-[r:INSTALLS_BELIEF {
            llm_provider: coalesce($llm_provider, 'all'),
            intent_id: coalesce($intent_id, 'all')
        }]->(bt)
        ON CREATE SET
            r.count = $count,
            r.confidence = $confidence,
            r.created_at = datetime()
        ON MATCH SET
            r.count = r.count + $count,
            r.confidence = (r.confidence * (r.count - $count) + $confidence * $count) / r.count,
            r.updated_at = datetime()
        RETURN r
        """
        params = edge.model_dump()
        params["belief_type"] = edge.belief_type.value
        result = await self.client.execute_query(query, params)
        if result and len(result) > 0:
            logger.debug(f"Created/updated INSTALLS_BELIEF: Brand {edge.brand_id} -> {edge.belief_type.value}")
            return dict(result[0]["r"])
        return None

    async def get_belief_map(
        self,
        brand_id: str,
        llm_provider: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get belief map for a brand."""
        query = """
        MATCH (b:Brand {id: $brand_id})-[r:INSTALLS_BELIEF]->(bt:BeliefType)
        WHERE $llm_provider IS NULL OR r.llm_provider = $llm_provider
        RETURN bt.type as belief_type,
               sum(r.count) as total_count,
               avg(r.confidence) as avg_confidence
        ORDER BY total_count DESC
        """
        result = await self.client.execute_query(
            query,
            {"brand_id": brand_id, "llm_provider": llm_provider}
        )
        return [dict(r) for r in result] if result else []

    async def create_installs_beliefs_batch(self, edges: list[InstallsBeliefEdge]) -> int:
        """Create multiple INSTALLS_BELIEF relationships in batch."""
        query = """
        UNWIND $edges AS edge
        MATCH (b:Brand {id: edge.brand_id})
        MATCH (bt:BeliefType {type: edge.belief_type})
        MERGE (b)-[r:INSTALLS_BELIEF {
            llm_provider: coalesce(edge.llm_provider, 'all'),
            intent_id: coalesce(edge.intent_id, 'all')
        }]->(bt)
        ON CREATE SET
            r.count = edge.count,
            r.confidence = edge.confidence,
            r.created_at = datetime()
        ON MATCH SET
            r.count = r.count + edge.count,
            r.updated_at = datetime()
        RETURN count(r) as count
        """
        edges_data = []
        for e in edges:
            data = e.model_dump()
            data["belief_type"] = e.belief_type.value
            edges_data.append(data)
        result = await self.client.execute_query(query, {"edges": edges_data})
        count = result[0]["count"] if result else 0
        logger.info(f"Batch created/updated {count} INSTALLS_BELIEF edges")
        return count

    # =========================================================================
    # RECOMMENDS EDGES (LLMProvider -> Brand)
    # =========================================================================

    async def create_recommends(self, edge: RecommendsEdge) -> dict[str, Any] | None:
        """Create a RECOMMENDS relationship."""
        query = """
        MATCH (l:LLMProvider {name: $llm_provider, model: $llm_model})
        MATCH (b:Brand {id: $brand_id})
        MERGE (l)-[r:RECOMMENDS {intent_id: coalesce($intent_id, 'all')}]->(b)
        SET r.position = $position,
            r.belief_type = $belief_type,
            r.updated_at = datetime()
        RETURN r
        """
        params = edge.model_dump()
        params["belief_type"] = edge.belief_type.value if edge.belief_type else None
        result = await self.client.execute_query(query, params)
        if result and len(result) > 0:
            logger.debug(f"Created RECOMMENDS: {edge.llm_provider}/{edge.llm_model} -> Brand {edge.brand_id}")
            return dict(result[0]["r"])
        return None

    async def get_llm_recommendations(
        self,
        llm_provider: str,
        llm_model: str,
        intent_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get brands recommended by an LLM."""
        query = """
        MATCH (l:LLMProvider {name: $llm_provider, model: $llm_model})-[r:RECOMMENDS]->(b:Brand)
        WHERE $intent_id IS NULL OR r.intent_id = $intent_id
        RETURN b.name as brand_name, b.id as brand_id,
               r.position as position, r.belief_type as belief_type
        ORDER BY r.position
        """
        result = await self.client.execute_query(
            query,
            {"llm_provider": llm_provider, "llm_model": llm_model, "intent_id": intent_id}
        )
        return [dict(r) for r in result] if result else []

    async def create_recommends_batch(self, edges: list[RecommendsEdge]) -> int:
        """Create multiple RECOMMENDS relationships in batch."""
        query = """
        UNWIND $edges AS edge
        MATCH (l:LLMProvider {name: edge.llm_provider, model: edge.llm_model})
        MATCH (b:Brand {id: edge.brand_id})
        MERGE (l)-[r:RECOMMENDS {intent_id: coalesce(edge.intent_id, 'all')}]->(b)
        SET r.position = edge.position,
            r.belief_type = edge.belief_type,
            r.updated_at = datetime()
        RETURN count(r) as count
        """
        edges_data = []
        for e in edges:
            data = e.model_dump()
            data["belief_type"] = e.belief_type.value if e.belief_type else None
            edges_data.append(data)
        result = await self.client.execute_query(query, {"edges": edges_data})
        count = result[0]["count"] if result else 0
        logger.info(f"Batch created {count} RECOMMENDS edges")
        return count

    # =========================================================================
    # IGNORES EDGES (LLMProvider -> Brand)
    # =========================================================================

    async def create_ignores(self, edge: IgnoresEdge) -> dict[str, Any] | None:
        """Create an IGNORES relationship."""
        query = """
        MATCH (l:LLMProvider {name: $llm_provider, model: $llm_model})
        MATCH (b:Brand {id: $brand_id})
        MERGE (l)-[r:IGNORES {intent_id: coalesce($intent_id, 'all')}]->(b)
        SET r.competitor_mentioned = $competitor_mentioned,
            r.updated_at = datetime()
        RETURN r
        """
        params = edge.model_dump()
        result = await self.client.execute_query(query, params)
        if result and len(result) > 0:
            logger.debug(f"Created IGNORES: {edge.llm_provider}/{edge.llm_model} -> Brand {edge.brand_id}")
            return dict(result[0]["r"])
        return None

    async def get_ignored_by(
        self,
        brand_id: str,
        llm_provider: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get LLMs that ignore a brand."""
        query = """
        MATCH (l:LLMProvider)-[r:IGNORES]->(b:Brand {id: $brand_id})
        WHERE $llm_provider IS NULL OR l.name = $llm_provider
        RETURN l.name as llm_provider, l.model as llm_model,
               r.intent_id as intent_id, r.competitor_mentioned as competitor_mentioned
        """
        result = await self.client.execute_query(
            query,
            {"brand_id": brand_id, "llm_provider": llm_provider}
        )
        return [dict(r) for r in result] if result else []

    async def create_ignores_batch(self, edges: list[IgnoresEdge]) -> int:
        """Create multiple IGNORES relationships in batch."""
        query = """
        UNWIND $edges AS edge
        MATCH (l:LLMProvider {name: edge.llm_provider, model: edge.llm_model})
        MATCH (b:Brand {id: edge.brand_id})
        MERGE (l)-[r:IGNORES {intent_id: coalesce(edge.intent_id, 'all')}]->(b)
        SET r.competitor_mentioned = edge.competitor_mentioned,
            r.updated_at = datetime()
        RETURN count(r) as count
        """
        edges_data = [e.model_dump() for e in edges]
        result = await self.client.execute_query(query, {"edges": edges_data})
        count = result[0]["count"] if result else 0
        logger.info(f"Batch created {count} IGNORES edges")
        return count

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    async def delete_edge(
        self,
        edge_type: str,
        source_id: str,
        target_id: str,
        source_label: str,
        target_label: str,
    ) -> bool:
        """
        Delete an edge by type and endpoints.

        Args:
            edge_type: Relationship type (CO_MENTIONED, RANKS_FOR, etc.)
            source_id: Source node ID.
            target_id: Target node ID.
            source_label: Source node label.
            target_label: Target node label.

        Returns:
            True if deleted, False otherwise.
        """
        query = f"""
        MATCH (s:{source_label} {{id: $source_id}})-[r:{edge_type}]->(t:{target_label} {{id: $target_id}})
        DELETE r
        RETURN count(r) as count
        """
        result = await self.client.execute_query(
            query,
            {"source_id": source_id, "target_id": target_id}
        )
        deleted = result[0]["count"] > 0 if result else False
        if deleted:
            logger.debug(f"Deleted {edge_type} edge: {source_id} -> {target_id}")
        return deleted

    async def count_edges(self, edge_type: str) -> int:
        """Count edges by type."""
        query = f"""
        MATCH ()-[r:{edge_type}]->()
        RETURN count(r) as count
        """
        result = await self.client.execute_query(query, {})
        return result[0]["count"] if result else 0
