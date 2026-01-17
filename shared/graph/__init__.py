"""
Neo4j graph database client.
"""

from shared.graph.client import (
    GraphClient,
    close_graph,
    get_graph_client,
)

__all__ = [
    "GraphClient",
    "get_graph_client",
    "close_graph",
]
