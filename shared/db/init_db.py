"""
Database initialization script.

This module provides utilities for initializing all database connections:
- PostgreSQL (via Alembic migrations)
- Redis (connection verification)
- Neo4j (schema setup)

Usage:
    # Initialize all databases
    python -m shared.db.init_db

    # Run specific commands
    python -m shared.db.init_db --postgres-only
    python -m shared.db.init_db --redis-only
    python -m shared.db.init_db --neo4j-only
    python -m shared.db.init_db --health-check
"""

import argparse
import asyncio
import logging
import subprocess
import sys
from pathlib import Path
from typing import Any

from shared.config import settings
from shared.db.postgres_client import PostgresClient, get_postgres_client
from shared.db.redis_client import RedisClient, get_redis_client
from shared.db.neo4j_client import Neo4jClient, get_neo4j_client
from shared.db.neo4j_schema import setup_schema as setup_neo4j_schema

logger = logging.getLogger(__name__)


async def init_postgres(run_migrations: bool = True) -> dict[str, Any]:
    """
    Initialize PostgreSQL database.

    Args:
        run_migrations: Whether to run Alembic migrations.

    Returns:
        Initialization result.
    """
    logger.info("Initializing PostgreSQL...")
    result = {"status": "pending", "migrations": None, "health": None}

    client = get_postgres_client()

    try:
        # Connect to verify database is accessible
        await client.connect()
        result["health"] = await client.health_check()

        if run_migrations:
            # Run Alembic migrations
            logger.info("Running Alembic migrations...")
            project_root = Path(__file__).parent.parent.parent
            migration_result = subprocess.run(
                ["alembic", "upgrade", "head"],
                cwd=project_root,
                capture_output=True,
                text=True,
            )

            if migration_result.returncode == 0:
                result["migrations"] = {
                    "status": "success",
                    "output": migration_result.stdout,
                }
                logger.info("Migrations completed successfully")
            else:
                result["migrations"] = {
                    "status": "failed",
                    "error": migration_result.stderr,
                }
                logger.error("Migration failed: %s", migration_result.stderr)

        result["status"] = "healthy" if result["health"]["status"] == "healthy" else "unhealthy"
        logger.info("PostgreSQL initialization complete")

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        logger.error("PostgreSQL initialization failed: %s", e)

    finally:
        await client.disconnect()

    return result


async def init_redis(flush: bool = False) -> dict[str, Any]:
    """
    Initialize Redis connection.

    Args:
        flush: Whether to flush the Redis database.

    Returns:
        Initialization result.
    """
    logger.info("Initializing Redis...")
    result = {"status": "pending", "health": None}

    client = get_redis_client()

    try:
        await client.connect()
        result["health"] = await client.health_check()

        if flush:
            logger.warning("Flushing Redis database...")
            await client.client.flushdb()
            result["flushed"] = True
            logger.info("Redis database flushed")

        result["status"] = "healthy" if result["health"]["status"] == "healthy" else "unhealthy"
        logger.info("Redis initialization complete")

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        logger.error("Redis initialization failed: %s", e)

    finally:
        await client.disconnect()

    return result


async def init_neo4j(setup_schema: bool = True) -> dict[str, Any]:
    """
    Initialize Neo4j connection and schema.

    Args:
        setup_schema: Whether to run schema setup.

    Returns:
        Initialization result.
    """
    logger.info("Initializing Neo4j...")
    result = {"status": "pending", "health": None, "schema": None}

    client = get_neo4j_client()

    try:
        await client.connect()
        result["health"] = await client.health_check()

        if setup_schema:
            logger.info("Setting up Neo4j schema...")
            result["schema"] = await setup_neo4j_schema(client)
            logger.info("Neo4j schema setup complete")

        result["status"] = "healthy" if result["health"]["status"] == "healthy" else "unhealthy"
        logger.info("Neo4j initialization complete")

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        logger.error("Neo4j initialization failed: %s", e)

    finally:
        await client.disconnect()

    return result


async def init_all(
    run_migrations: bool = True,
    setup_neo4j: bool = True,
    flush_redis: bool = False,
) -> dict[str, Any]:
    """
    Initialize all databases.

    Args:
        run_migrations: Whether to run PostgreSQL migrations.
        setup_neo4j: Whether to setup Neo4j schema.
        flush_redis: Whether to flush Redis.

    Returns:
        Initialization results for all databases.
    """
    logger.info("Initializing all databases...")

    results = {
        "postgres": await init_postgres(run_migrations=run_migrations),
        "redis": await init_redis(flush=flush_redis),
        "neo4j": await init_neo4j(setup_schema=setup_neo4j),
    }

    # Determine overall status
    all_healthy = all(
        r["status"] == "healthy" for r in results.values()
    )
    results["overall_status"] = "healthy" if all_healthy else "unhealthy"

    logger.info("Database initialization complete. Overall status: %s", results["overall_status"])
    return results


async def health_check_all() -> dict[str, Any]:
    """
    Perform health check on all databases.

    Returns:
        Health check results for all databases.
    """
    logger.info("Performing health check on all databases...")

    results = {}

    # PostgreSQL health check
    pg_client = get_postgres_client()
    try:
        await pg_client.connect()
        results["postgres"] = await pg_client.health_check()
    except Exception as e:
        results["postgres"] = {"status": "unhealthy", "error": str(e)}
    finally:
        await pg_client.disconnect()

    # Redis health check
    redis_client = get_redis_client()
    try:
        await redis_client.connect()
        results["redis"] = await redis_client.health_check()
    except Exception as e:
        results["redis"] = {"status": "unhealthy", "error": str(e)}
    finally:
        await redis_client.disconnect()

    # Neo4j health check
    neo4j_client = get_neo4j_client()
    try:
        await neo4j_client.connect()
        results["neo4j"] = await neo4j_client.health_check()
    except Exception as e:
        results["neo4j"] = {"status": "unhealthy", "error": str(e)}
    finally:
        await neo4j_client.disconnect()

    # Overall status
    all_healthy = all(
        r.get("status") == "healthy" for r in results.values()
    )
    results["overall_status"] = "healthy" if all_healthy else "unhealthy"

    return results


async def create_default_organization() -> dict[str, Any]:
    """
    Create the default organization for development.

    Returns:
        Created organization data.
    """
    import uuid
    from sqlalchemy import text

    logger.info("Creating default organization...")

    client = get_postgres_client()
    result = {"status": "pending"}

    try:
        await client.connect()

        default_org_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

        async with client.session() as session:
            # Check if default org exists
            check_query = text("SELECT id FROM organizations WHERE id = :id")
            existing = await session.execute(check_query, {"id": default_org_id})

            if existing.scalar():
                result["status"] = "exists"
                result["organization_id"] = str(default_org_id)
                logger.info("Default organization already exists")
            else:
                # Create default organization
                insert_query = text("""
                    INSERT INTO organizations (id, name, slug, plan_type, created_at, updated_at)
                    VALUES (:id, :name, :slug, :plan_type, NOW(), NOW())
                    RETURNING id
                """)
                await session.execute(insert_query, {
                    "id": default_org_id,
                    "name": "Default Organization",
                    "slug": "default",
                    "plan_type": "free",
                })
                await session.commit()

                result["status"] = "created"
                result["organization_id"] = str(default_org_id)
                logger.info("Default organization created: %s", default_org_id)

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        logger.error("Failed to create default organization: %s", e)

    finally:
        await client.disconnect()

    return result


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Initialize databases for LLM Brand Monitor"
    )
    parser.add_argument(
        "--postgres-only",
        action="store_true",
        help="Initialize only PostgreSQL",
    )
    parser.add_argument(
        "--redis-only",
        action="store_true",
        help="Initialize only Redis",
    )
    parser.add_argument(
        "--neo4j-only",
        action="store_true",
        help="Initialize only Neo4j",
    )
    parser.add_argument(
        "--health-check",
        action="store_true",
        help="Perform health check only",
    )
    parser.add_argument(
        "--skip-migrations",
        action="store_true",
        help="Skip Alembic migrations",
    )
    parser.add_argument(
        "--skip-neo4j-schema",
        action="store_true",
        help="Skip Neo4j schema setup",
    )
    parser.add_argument(
        "--flush-redis",
        action="store_true",
        help="Flush Redis database",
    )
    parser.add_argument(
        "--create-default-org",
        action="store_true",
        help="Create default organization",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    async def run():
        import json

        if args.health_check:
            results = await health_check_all()
        elif args.postgres_only:
            results = await init_postgres(run_migrations=not args.skip_migrations)
        elif args.redis_only:
            results = await init_redis(flush=args.flush_redis)
        elif args.neo4j_only:
            results = await init_neo4j(setup_schema=not args.skip_neo4j_schema)
        elif args.create_default_org:
            results = await create_default_organization()
        else:
            results = await init_all(
                run_migrations=not args.skip_migrations,
                setup_neo4j=not args.skip_neo4j_schema,
                flush_redis=args.flush_redis,
            )

        print(json.dumps(results, indent=2, default=str))

        # Exit with error code if unhealthy
        if isinstance(results, dict):
            status = results.get("overall_status") or results.get("status")
            if status not in ("healthy", "success", "created", "exists"):
                sys.exit(1)

    asyncio.run(run())


if __name__ == "__main__":
    main()
