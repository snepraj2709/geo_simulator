"""
Neo4j client for knowledge graph operations.

This module provides a robust Neo4j client with:
- Async driver with connection pooling
- Health check capabilities
- Query execution utilities
- Transaction support
- Graceful shutdown handling
"""

import logging
from typing import Any

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession
from neo4j.exceptions import Neo4jError

from shared.config import settings

logger = logging.getLogger(__name__)


class Neo4jClient:
    """
    Neo4j client for knowledge graph operations.

    Provides async Neo4j access with connection pooling,
    health checks, and query utilities.

    Usage:
        client = Neo4jClient()
        await client.connect()

        async with client.session() as session:
            result = await session.run("MATCH (n) RETURN n LIMIT 10")
            records = await result.data()

        await client.disconnect()
    """

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
        max_connection_pool_size: int = 50,
        connection_acquisition_timeout: float = 60.0,
    ):
        """
        Initialize Neo4j client.

        Args:
            uri: Neo4j connection URI. Defaults to settings.
            user: Neo4j username. Defaults to settings.
            password: Neo4j password. Defaults to settings.
            max_connection_pool_size: Maximum connections in pool.
            connection_acquisition_timeout: Timeout for acquiring connections.
        """
        self._uri = uri or settings.neo4j_uri
        self._user = user or settings.neo4j_user
        self._password = password or settings.neo4j_password
        self._max_connection_pool_size = max_connection_pool_size
        self._connection_acquisition_timeout = connection_acquisition_timeout

        self._driver: AsyncDriver | None = None
        self._is_connected = False

    @property
    def driver(self) -> AsyncDriver:
        """Get the Neo4j driver."""
        if self._driver is None:
            raise RuntimeError("Neo4j not connected. Call connect() first.")
        return self._driver

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._is_connected

    async def connect(self) -> None:
        """
        Establish Neo4j connection.

        Raises:
            Neo4jError: If connection fails.
        """
        if self._is_connected:
            logger.warning("Neo4j client already connected")
            return

        logger.info("Connecting to Neo4j at %s", self._uri)

        try:
            self._driver = AsyncGraphDatabase.driver(
                self._uri,
                auth=(self._user, self._password),
                max_connection_pool_size=self._max_connection_pool_size,
                connection_acquisition_timeout=self._connection_acquisition_timeout,
            )

            # Verify connection
            await self._driver.verify_connectivity()

            self._is_connected = True
            logger.info("Neo4j connection established successfully")

        except Neo4jError as e:
            logger.error("Failed to connect to Neo4j: %s", e)
            raise

    async def disconnect(self) -> None:
        """
        Close Neo4j connection.
        """
        if not self._is_connected:
            return

        logger.info("Disconnecting from Neo4j")

        if self._driver:
            await self._driver.close()
            self._driver = None

        self._is_connected = False
        logger.info("Neo4j connection closed")

    def session(self, database: str | None = None) -> AsyncSession:
        """
        Get a Neo4j session.

        Args:
            database: Database name. None uses default.

        Returns:
            AsyncSession: Neo4j session.
        """
        return self.driver.session(database=database)

    async def health_check(self) -> dict[str, Any]:
        """
        Perform Neo4j health check.

        Returns:
            dict: Health status including server info.
        """
        try:
            await self.driver.verify_connectivity()
            server_info = await self.driver.get_server_info()
            return {
                "status": "healthy",
                "server_address": str(server_info.address),
                "protocol_version": str(server_info.protocol_version),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }

    # ==================== Query Utilities ====================

    async def run_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Run a Cypher query and return results.

        Args:
            query: Cypher query string.
            parameters: Query parameters.
            database: Database name.

        Returns:
            List of result records as dictionaries.
        """
        async with self.session(database=database) as session:
            result = await session.run(query, parameters or {})
            return await result.data()

    async def run_query_single(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Run a Cypher query and return single result.

        Args:
            query: Cypher query string.
            parameters: Query parameters.
            database: Database name.

        Returns:
            Single result record or None.
        """
        results = await self.run_query(query, parameters, database)
        return results[0] if results else None

    async def execute_write(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str | None = None,
    ) -> dict[str, Any]:
        """
        Execute a write query and return summary.

        Args:
            query: Cypher query string.
            parameters: Query parameters.
            database: Database name.

        Returns:
            Query summary with counters.
        """
        async with self.session(database=database) as session:
            result = await session.run(query, parameters or {})
            summary = await result.consume()
            return {
                "nodes_created": summary.counters.nodes_created,
                "nodes_deleted": summary.counters.nodes_deleted,
                "relationships_created": summary.counters.relationships_created,
                "relationships_deleted": summary.counters.relationships_deleted,
                "properties_set": summary.counters.properties_set,
                "labels_added": summary.counters.labels_added,
                "labels_removed": summary.counters.labels_removed,
                "indexes_added": summary.counters.indexes_added,
                "indexes_removed": summary.counters.indexes_removed,
                "constraints_added": summary.counters.constraints_added,
                "constraints_removed": summary.counters.constraints_removed,
            }

    # ==================== Node Operations ====================

    async def create_node(
        self,
        labels: list[str],
        properties: dict[str, Any],
        database: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Create a node with labels and properties.

        Args:
            labels: Node labels.
            properties: Node properties.
            database: Database name.

        Returns:
            Created node properties with element_id.
        """
        labels_str = ":".join(labels)
        query = f"""
        CREATE (n:{labels_str} $props)
        RETURN n, elementId(n) as element_id
        """
        result = await self.run_query_single(query, {"props": properties}, database)
        if result:
            node_data = dict(result["n"])
            node_data["element_id"] = result["element_id"]
            return node_data
        return None

    async def find_node(
        self,
        label: str,
        properties: dict[str, Any],
        database: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Find a node by label and properties.

        Args:
            label: Node label.
            properties: Properties to match.
            database: Database name.

        Returns:
            Node properties or None.
        """
        where_clauses = " AND ".join([f"n.{k} = ${k}" for k in properties.keys()])
        query = f"""
        MATCH (n:{label})
        WHERE {where_clauses}
        RETURN n, elementId(n) as element_id
        LIMIT 1
        """
        result = await self.run_query_single(query, properties, database)
        if result:
            node_data = dict(result["n"])
            node_data["element_id"] = result["element_id"]
            return node_data
        return None

    async def find_nodes(
        self,
        label: str,
        properties: dict[str, Any] | None = None,
        limit: int = 100,
        database: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Find nodes by label and optional properties.

        Args:
            label: Node label.
            properties: Properties to match.
            limit: Maximum number of results.
            database: Database name.

        Returns:
            List of matching nodes.
        """
        if properties:
            where_clauses = " AND ".join([f"n.{k} = ${k}" for k in properties.keys()])
            query = f"""
            MATCH (n:{label})
            WHERE {where_clauses}
            RETURN n, elementId(n) as element_id
            LIMIT $limit
            """
            params = {**properties, "limit": limit}
        else:
            query = f"""
            MATCH (n:{label})
            RETURN n, elementId(n) as element_id
            LIMIT $limit
            """
            params = {"limit": limit}

        results = await self.run_query(query, params, database)
        nodes = []
        for result in results:
            node_data = dict(result["n"])
            node_data["element_id"] = result["element_id"]
            nodes.append(node_data)
        return nodes

    async def update_node(
        self,
        label: str,
        match_properties: dict[str, Any],
        set_properties: dict[str, Any],
        database: str | None = None,
    ) -> dict[str, Any] | None:
        """
        Update a node's properties.

        Args:
            label: Node label.
            match_properties: Properties to identify the node.
            set_properties: Properties to set.
            database: Database name.

        Returns:
            Updated node properties or None.
        """
        where_clauses = " AND ".join([f"n.{k} = $match_{k}" for k in match_properties.keys()])
        set_clauses = ", ".join([f"n.{k} = $set_{k}" for k in set_properties.keys()])

        query = f"""
        MATCH (n:{label})
        WHERE {where_clauses}
        SET {set_clauses}
        RETURN n, elementId(n) as element_id
        """

        params = {f"match_{k}": v for k, v in match_properties.items()}
        params.update({f"set_{k}": v for k, v in set_properties.items()})

        result = await self.run_query_single(query, params, database)
        if result:
            node_data = dict(result["n"])
            node_data["element_id"] = result["element_id"]
            return node_data
        return None

    async def delete_node(
        self,
        label: str,
        properties: dict[str, Any],
        detach: bool = True,
        database: str | None = None,
    ) -> int:
        """
        Delete a node.

        Args:
            label: Node label.
            properties: Properties to identify the node.
            detach: Whether to delete relationships too.
            database: Database name.

        Returns:
            Number of nodes deleted.
        """
        where_clauses = " AND ".join([f"n.{k} = ${k}" for k in properties.keys()])
        delete_cmd = "DETACH DELETE" if detach else "DELETE"

        query = f"""
        MATCH (n:{label})
        WHERE {where_clauses}
        {delete_cmd} n
        """

        summary = await self.execute_write(query, properties, database)
        return summary["nodes_deleted"]

    # ==================== Relationship Operations ====================

    async def create_relationship(
        self,
        from_label: str,
        from_properties: dict[str, Any],
        to_label: str,
        to_properties: dict[str, Any],
        rel_type: str,
        rel_properties: dict[str, Any] | None = None,
        database: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a relationship between two nodes.

        Args:
            from_label: Source node label.
            from_properties: Source node properties.
            to_label: Target node label.
            to_properties: Target node properties.
            rel_type: Relationship type.
            rel_properties: Relationship properties.
            database: Database name.

        Returns:
            Summary of created relationship.
        """
        from_where = " AND ".join([f"a.{k} = $from_{k}" for k in from_properties.keys()])
        to_where = " AND ".join([f"b.{k} = $to_{k}" for k in to_properties.keys()])

        if rel_properties:
            query = f"""
            MATCH (a:{from_label}), (b:{to_label})
            WHERE {from_where} AND {to_where}
            CREATE (a)-[r:{rel_type} $rel_props]->(b)
            RETURN type(r) as type
            """
        else:
            query = f"""
            MATCH (a:{from_label}), (b:{to_label})
            WHERE {from_where} AND {to_where}
            CREATE (a)-[r:{rel_type}]->(b)
            RETURN type(r) as type
            """

        params = {f"from_{k}": v for k, v in from_properties.items()}
        params.update({f"to_{k}": v for k, v in to_properties.items()})
        if rel_properties:
            params["rel_props"] = rel_properties

        return await self.execute_write(query, params, database)

    async def find_relationships(
        self,
        from_label: str | None = None,
        to_label: str | None = None,
        rel_type: str | None = None,
        limit: int = 100,
        database: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Find relationships matching criteria.

        Args:
            from_label: Source node label filter.
            to_label: Target node label filter.
            rel_type: Relationship type filter.
            limit: Maximum results.
            database: Database name.

        Returns:
            List of relationships with source and target nodes.
        """
        from_part = f"(a:{from_label})" if from_label else "(a)"
        to_part = f"(b:{to_label})" if to_label else "(b)"
        rel_part = f"[r:{rel_type}]" if rel_type else "[r]"

        query = f"""
        MATCH {from_part}-{rel_part}->{to_part}
        RETURN a, r, b, type(r) as rel_type
        LIMIT $limit
        """

        results = await self.run_query(query, {"limit": limit}, database)
        return [
            {
                "from": dict(r["a"]),
                "to": dict(r["b"]),
                "relationship": dict(r["r"]) if r["r"] else {},
                "rel_type": r["rel_type"],
            }
            for r in results
        ]


# Global client instance
_client: Neo4jClient | None = None


def get_neo4j_client() -> Neo4jClient:
    """
    Get the global Neo4j client instance.

    Returns:
        Neo4jClient: The global client instance.
    """
    global _client
    if _client is None:
        _client = Neo4jClient()
    return _client


async def get_graph() -> Neo4jClient:
    """
    FastAPI dependency for getting the Neo4j client.

    Returns:
        Neo4jClient: Neo4j client instance.
    """
    client = get_neo4j_client()
    if not client.is_connected:
        await client.connect()
    return client
