"""
Database clients and utilities.

This package provides database clients for:
- PostgreSQL (primary data storage)
- Redis (caching and message broker)
- Neo4j (knowledge graph)
"""

# PostgreSQL base
from shared.db.postgres import (
    AsyncSessionLocal,
    Base,
    engine,
    get_db,
    init_db,
)

# PostgreSQL client with connection pooling
from shared.db.postgres_client import (
    PostgresClient,
    get_postgres_client,
    get_session,
)

# Redis client for caching
from shared.db.redis_client import (
    RedisClient,
    get_redis_client,
    get_cache,
)

# Neo4j client for knowledge graph
from shared.db.neo4j_client import (
    Neo4jClient,
    get_neo4j_client,
    get_graph,
)

# Neo4j schema setup
from shared.db.neo4j_schema import (
    setup_schema as setup_neo4j_schema,
    reset_schema as reset_neo4j_schema,
)

# Database initialization
from shared.db.init_db import (
    init_all,
    init_postgres,
    init_redis,
    init_neo4j,
    health_check_all,
    create_default_organization,
)

__all__ = [
    # PostgreSQL base
    "engine",
    "AsyncSessionLocal",
    "Base",
    "get_db",
    "init_db",
    # PostgreSQL client
    "PostgresClient",
    "get_postgres_client",
    "get_session",
    # Redis client
    "RedisClient",
    "get_redis_client",
    "get_cache",
    # Neo4j client
    "Neo4jClient",
    "get_neo4j_client",
    "get_graph",
    # Neo4j schema
    "setup_neo4j_schema",
    "reset_neo4j_schema",
    # Initialization
    "init_all",
    "init_postgres",
    "init_redis",
    "init_neo4j",
    "health_check_all",
    "create_default_organization",
]
