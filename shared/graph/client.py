"""
Neo4j graph database client for knowledge graph operations.
"""

from contextlib import asynccontextmanager
from typing import Any

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession

from shared.config import settings

_driver: AsyncDriver | None = None


async def get_driver() -> AsyncDriver:
    """Get or create Neo4j driver."""
    global _driver
    if _driver is None:
        _driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return _driver


async def close_graph() -> None:
    """Close Neo4j driver."""
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None


@asynccontextmanager
async def get_graph_session():
    """Get Neo4j session context manager."""
    driver = await get_driver()
    async with driver.session() as session:
        yield session


async def get_graph_client() -> "GraphClient":
    """Get graph client instance."""
    return GraphClient()


class GraphClient:
    """High-level Neo4j graph client for brand influence operations."""

    async def create_brand(
        self,
        brand_id: str,
        name: str,
        normalized_name: str,
        domain: str | None = None,
        industry: str | None = None,
        is_tracked: bool = False,
    ) -> dict[str, Any]:
        """Create a brand node."""
        query = """
        MERGE (b:Brand {id: $id})
        SET b.name = $name,
            b.normalized_name = $normalized_name,
            b.domain = $domain,
            b.industry = $industry,
            b.is_tracked = $is_tracked
        RETURN b
        """
        async with get_graph_session() as session:
            result = await session.run(
                query,
                id=brand_id,
                name=name,
                normalized_name=normalized_name,
                domain=domain,
                industry=industry,
                is_tracked=is_tracked,
            )
            record = await result.single()
            return dict(record["b"]) if record else {}

    async def create_icp(
        self,
        icp_id: str,
        name: str,
        website_id: str,
        pain_points: list[str],
        goals: list[str],
    ) -> dict[str, Any]:
        """Create an ICP node."""
        query = """
        MERGE (i:ICP {id: $id})
        SET i.name = $name,
            i.website_id = $website_id,
            i.pain_points = $pain_points,
            i.goals = $goals
        RETURN i
        """
        async with get_graph_session() as session:
            result = await session.run(
                query,
                id=icp_id,
                name=name,
                website_id=website_id,
                pain_points=pain_points,
                goals=goals,
            )
            record = await result.single()
            return dict(record["i"]) if record else {}

    async def create_co_mention(
        self,
        brand1_id: str,
        brand2_id: str,
        llm_provider: str,
        position_delta: float = 0.0,
    ) -> None:
        """Create or update co-mention relationship between brands."""
        query = """
        MATCH (b1:Brand {id: $brand1_id})
        MATCH (b2:Brand {id: $brand2_id})
        MERGE (b1)-[r:CO_MENTIONED {llm_provider: $llm_provider}]->(b2)
        ON CREATE SET r.count = 1, r.avg_position_delta = $position_delta
        ON MATCH SET r.count = r.count + 1,
                     r.avg_position_delta = (r.avg_position_delta * (r.count - 1) + $position_delta) / r.count
        """
        async with get_graph_session() as session:
            await session.run(
                query,
                brand1_id=brand1_id,
                brand2_id=brand2_id,
                llm_provider=llm_provider,
                position_delta=position_delta,
            )

    async def create_belief_installation(
        self,
        brand_id: str,
        belief_type: str,
        intent_id: str,
        llm_provider: str,
        confidence: float = 1.0,
    ) -> None:
        """Record belief installation from LLM response."""
        query = """
        MATCH (b:Brand {id: $brand_id})
        MERGE (bt:BeliefType {type: $belief_type})
        MERGE (b)-[r:INSTALLS_BELIEF {intent_id: $intent_id, llm_provider: $llm_provider}]->(bt)
        ON CREATE SET r.count = 1, r.confidence = $confidence
        ON MATCH SET r.count = r.count + 1,
                     r.confidence = (r.confidence * (r.count - 1) + $confidence) / r.count
        """
        async with get_graph_session() as session:
            await session.run(
                query,
                brand_id=brand_id,
                belief_type=belief_type,
                intent_id=intent_id,
                llm_provider=llm_provider,
                confidence=confidence,
            )

    async def get_brand_co_mentions(
        self,
        brand_name: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get brands co-mentioned with target brand."""
        query = """
        MATCH (target:Brand {name: $brand_name})-[r:CO_MENTIONED]-(other:Brand)
        RETURN other.name as brand_name,
               other.id as brand_id,
               sum(r.count) as total_count,
               avg(r.avg_position_delta) as avg_position_delta
        ORDER BY total_count DESC
        LIMIT $limit
        """
        async with get_graph_session() as session:
            result = await session.run(query, brand_name=brand_name, limit=limit)
            records = await result.data()
            return records

    async def get_brand_beliefs(
        self,
        brand_name: str,
    ) -> list[dict[str, Any]]:
        """Get belief distribution for a brand."""
        query = """
        MATCH (b:Brand {name: $brand_name})-[r:INSTALLS_BELIEF]->(bt:BeliefType)
        RETURN bt.type as belief_type,
               sum(r.count) as total_count,
               avg(r.confidence) as avg_confidence
        ORDER BY total_count DESC
        """
        async with get_graph_session() as session:
            result = await session.run(query, brand_name=brand_name)
            records = await result.data()
            return records

    async def get_icp_journey_paths(
        self,
        icp_id: str,
    ) -> list[dict[str, Any]]:
        """Get ICP concern to brand recommendation paths."""
        query = """
        MATCH path = (icp:ICP {id: $icp_id})-[:HAS_CONCERN]->(c:Concern)-[:TRIGGERS]->(i:Intent)<-[:RANKS_FOR]-(b:Brand)
        RETURN c.description as concern,
               i.intent_type as intent_type,
               i.query_text as query,
               collect({
                   brand: b.name,
                   position: [(b)-[r:RANKS_FOR]->(i) | r.position][0],
                   presence: [(b)-[r:RANKS_FOR]->(i) | r.presence][0]
               }) as brands
        """
        async with get_graph_session() as session:
            result = await session.run(query, icp_id=icp_id)
            records = await result.data()
            return records
