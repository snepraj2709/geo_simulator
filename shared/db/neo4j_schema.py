"""
Neo4j schema setup script.

This module defines and creates the Neo4j schema including:
- Node constraints (uniqueness)
- Indexes for query optimization
- Node label definitions

Based on ARCHITECTURE.md Knowledge Graph Builder specification.
"""

import logging
from typing import Any

from shared.db.neo4j_client import Neo4jClient, get_neo4j_client

logger = logging.getLogger(__name__)


# ==================== Node Labels ====================
# These are the primary node types in the knowledge graph

NODE_LABELS = {
    "Brand": "Represents a brand/company entity that can be mentioned in LLM responses",
    "ICP": "Ideal Customer Profile representing a customer persona",
    "Intent": "User intent classification (informational, evaluation, decision)",
    "Concern": "Pain point or concern that an ICP might have",
    "Conversation": "A conversation sequence representing a user journey",
    "BeliefType": "Type of belief installed by LLM responses (truth, superiority, outcome, etc.)",
    "LLMResponse": "An LLM response to a prompt",
    "Prompt": "A user prompt/question",
}

# ==================== Relationship Types ====================
# These are the edge types connecting nodes

RELATIONSHIP_TYPES = {
    "MENTIONS": "Brand → Brand co-occurrence in responses",
    "HAS_CONCERN": "ICP → Concern mapping",
    "TRIGGERS_INTENT": "Concern → Intent causation",
    "RANKS_FOR": "Brand → Intent ranking relationship",
    "INSTALLS_BELIEF": "LLMResponse → BeliefType belief installation",
    "HAS_PROMPT": "Conversation → Prompt containment",
    "GENERATES": "Prompt → LLMResponse generation",
    "BELONGS_TO": "Various → parent containment",
    "RECOMMENDS": "LLMResponse → Brand recommendation",
    "COMPARES": "LLMResponse → Brand comparison",
}


# ==================== Schema Definitions ====================

CONSTRAINTS = [
    # Brand constraints
    {
        "name": "brand_normalized_name_unique",
        "query": """
        CREATE CONSTRAINT brand_normalized_name_unique IF NOT EXISTS
        FOR (b:Brand) REQUIRE b.normalized_name IS UNIQUE
        """,
    },
    {
        "name": "brand_id_unique",
        "query": """
        CREATE CONSTRAINT brand_id_unique IF NOT EXISTS
        FOR (b:Brand) REQUIRE b.id IS UNIQUE
        """,
    },
    # ICP constraints
    {
        "name": "icp_id_unique",
        "query": """
        CREATE CONSTRAINT icp_id_unique IF NOT EXISTS
        FOR (i:ICP) REQUIRE i.id IS UNIQUE
        """,
    },
    # Intent constraints
    {
        "name": "intent_name_unique",
        "query": """
        CREATE CONSTRAINT intent_name_unique IF NOT EXISTS
        FOR (i:Intent) REQUIRE i.name IS UNIQUE
        """,
    },
    # Concern constraints
    {
        "name": "concern_id_unique",
        "query": """
        CREATE CONSTRAINT concern_id_unique IF NOT EXISTS
        FOR (c:Concern) REQUIRE c.id IS UNIQUE
        """,
    },
    # Conversation constraints
    {
        "name": "conversation_id_unique",
        "query": """
        CREATE CONSTRAINT conversation_id_unique IF NOT EXISTS
        FOR (c:Conversation) REQUIRE c.id IS UNIQUE
        """,
    },
    # BeliefType constraints
    {
        "name": "belieftype_name_unique",
        "query": """
        CREATE CONSTRAINT belieftype_name_unique IF NOT EXISTS
        FOR (b:BeliefType) REQUIRE b.name IS UNIQUE
        """,
    },
    # LLMResponse constraints
    {
        "name": "llmresponse_id_unique",
        "query": """
        CREATE CONSTRAINT llmresponse_id_unique IF NOT EXISTS
        FOR (r:LLMResponse) REQUIRE r.id IS UNIQUE
        """,
    },
    # Prompt constraints
    {
        "name": "prompt_id_unique",
        "query": """
        CREATE CONSTRAINT prompt_id_unique IF NOT EXISTS
        FOR (p:Prompt) REQUIRE p.id IS UNIQUE
        """,
    },
]


INDEXES = [
    # Brand indexes
    {
        "name": "brand_name_index",
        "query": """
        CREATE INDEX brand_name_index IF NOT EXISTS
        FOR (b:Brand) ON (b.name)
        """,
    },
    {
        "name": "brand_industry_index",
        "query": """
        CREATE INDEX brand_industry_index IF NOT EXISTS
        FOR (b:Brand) ON (b.industry)
        """,
    },
    {
        "name": "brand_is_tracked_index",
        "query": """
        CREATE INDEX brand_is_tracked_index IF NOT EXISTS
        FOR (b:Brand) ON (b.is_tracked)
        """,
    },
    # ICP indexes
    {
        "name": "icp_website_id_index",
        "query": """
        CREATE INDEX icp_website_id_index IF NOT EXISTS
        FOR (i:ICP) ON (i.website_id)
        """,
    },
    {
        "name": "icp_name_index",
        "query": """
        CREATE INDEX icp_name_index IF NOT EXISTS
        FOR (i:ICP) ON (i.name)
        """,
    },
    # Intent indexes
    {
        "name": "intent_type_index",
        "query": """
        CREATE INDEX intent_type_index IF NOT EXISTS
        FOR (i:Intent) ON (i.type)
        """,
    },
    {
        "name": "intent_funnel_stage_index",
        "query": """
        CREATE INDEX intent_funnel_stage_index IF NOT EXISTS
        FOR (i:Intent) ON (i.funnel_stage)
        """,
    },
    # Concern indexes
    {
        "name": "concern_category_index",
        "query": """
        CREATE INDEX concern_category_index IF NOT EXISTS
        FOR (c:Concern) ON (c.category)
        """,
    },
    # Conversation indexes
    {
        "name": "conversation_website_id_index",
        "query": """
        CREATE INDEX conversation_website_id_index IF NOT EXISTS
        FOR (c:Conversation) ON (c.website_id)
        """,
    },
    {
        "name": "conversation_icp_id_index",
        "query": """
        CREATE INDEX conversation_icp_id_index IF NOT EXISTS
        FOR (c:Conversation) ON (c.icp_id)
        """,
    },
    # LLMResponse indexes
    {
        "name": "llmresponse_provider_index",
        "query": """
        CREATE INDEX llmresponse_provider_index IF NOT EXISTS
        FOR (r:LLMResponse) ON (r.provider)
        """,
    },
    {
        "name": "llmresponse_simulation_run_id_index",
        "query": """
        CREATE INDEX llmresponse_simulation_run_id_index IF NOT EXISTS
        FOR (r:LLMResponse) ON (r.simulation_run_id)
        """,
    },
    # Prompt indexes
    {
        "name": "prompt_conversation_id_index",
        "query": """
        CREATE INDEX prompt_conversation_id_index IF NOT EXISTS
        FOR (p:Prompt) ON (p.conversation_id)
        """,
    },
    {
        "name": "prompt_type_index",
        "query": """
        CREATE INDEX prompt_type_index IF NOT EXISTS
        FOR (p:Prompt) ON (p.type)
        """,
    },
    # Full-text search indexes
    {
        "name": "brand_fulltext_index",
        "query": """
        CREATE FULLTEXT INDEX brand_fulltext_index IF NOT EXISTS
        FOR (b:Brand) ON EACH [b.name, b.normalized_name]
        """,
    },
    {
        "name": "concern_fulltext_index",
        "query": """
        CREATE FULLTEXT INDEX concern_fulltext_index IF NOT EXISTS
        FOR (c:Concern) ON EACH [c.description]
        """,
    },
]


# ==================== Seed Data ====================
# Pre-populate BeliefType and Intent nodes

BELIEF_TYPES = [
    {"name": "truth", "description": "Epistemic clarity, neutrality - establishes facts"},
    {"name": "superiority", "description": "Better than alternatives - positions brand above competitors"},
    {"name": "outcome", "description": "ROI, performance, results - focuses on tangible benefits"},
    {"name": "transaction", "description": "Buy now, act - drives immediate action"},
    {"name": "identity", "description": "People like you use this - appeals to self-image"},
    {"name": "social_proof", "description": "Others chose this - leverages social validation"},
]

INTENT_TYPES = [
    {"name": "informational", "type": "informational", "funnel_stage": "awareness", "description": "User seeking information/education"},
    {"name": "evaluation", "type": "evaluation", "funnel_stage": "consideration", "description": "User comparing options"},
    {"name": "decision", "type": "decision", "funnel_stage": "purchase", "description": "User ready to make a decision"},
]


async def create_constraints(client: Neo4jClient) -> dict[str, Any]:
    """
    Create all uniqueness constraints.

    Args:
        client: Neo4j client instance.

    Returns:
        Summary of created constraints.
    """
    results = {"created": 0, "failed": 0, "errors": []}

    for constraint in CONSTRAINTS:
        try:
            await client.execute_write(constraint["query"])
            results["created"] += 1
            logger.info("Created constraint: %s", constraint["name"])
        except Exception as e:
            # Constraint might already exist
            if "already exists" in str(e).lower():
                logger.debug("Constraint already exists: %s", constraint["name"])
            else:
                results["failed"] += 1
                results["errors"].append({"name": constraint["name"], "error": str(e)})
                logger.error("Failed to create constraint %s: %s", constraint["name"], e)

    return results


async def create_indexes(client: Neo4jClient) -> dict[str, Any]:
    """
    Create all indexes for query optimization.

    Args:
        client: Neo4j client instance.

    Returns:
        Summary of created indexes.
    """
    results = {"created": 0, "failed": 0, "errors": []}

    for index in INDEXES:
        try:
            await client.execute_write(index["query"])
            results["created"] += 1
            logger.info("Created index: %s", index["name"])
        except Exception as e:
            # Index might already exist
            if "already exists" in str(e).lower():
                logger.debug("Index already exists: %s", index["name"])
            else:
                results["failed"] += 1
                results["errors"].append({"name": index["name"], "error": str(e)})
                logger.error("Failed to create index %s: %s", index["name"], e)

    return results


async def seed_belief_types(client: Neo4jClient) -> int:
    """
    Seed the BeliefType nodes.

    Args:
        client: Neo4j client instance.

    Returns:
        Number of belief types created.
    """
    created = 0
    for belief in BELIEF_TYPES:
        query = """
        MERGE (b:BeliefType {name: $name})
        ON CREATE SET b.description = $description
        RETURN b
        """
        result = await client.run_query_single(query, belief)
        if result:
            created += 1
            logger.debug("Seeded BeliefType: %s", belief["name"])

    logger.info("Seeded %d BeliefType nodes", created)
    return created


async def seed_intent_types(client: Neo4jClient) -> int:
    """
    Seed the Intent nodes.

    Args:
        client: Neo4j client instance.

    Returns:
        Number of intent types created.
    """
    created = 0
    for intent in INTENT_TYPES:
        query = """
        MERGE (i:Intent {name: $name})
        ON CREATE SET i.type = $type, i.funnel_stage = $funnel_stage, i.description = $description
        RETURN i
        """
        result = await client.run_query_single(query, intent)
        if result:
            created += 1
            logger.debug("Seeded Intent: %s", intent["name"])

    logger.info("Seeded %d Intent nodes", created)
    return created


async def setup_schema(client: Neo4jClient | None = None) -> dict[str, Any]:
    """
    Set up the complete Neo4j schema.

    Creates all constraints, indexes, and seed data.

    Args:
        client: Optional Neo4j client. If not provided, uses global client.

    Returns:
        Summary of setup operations.
    """
    if client is None:
        client = get_neo4j_client()
        if not client.is_connected:
            await client.connect()

    logger.info("Starting Neo4j schema setup")

    results = {
        "constraints": await create_constraints(client),
        "indexes": await create_indexes(client),
        "seed_data": {
            "belief_types": await seed_belief_types(client),
            "intent_types": await seed_intent_types(client),
        },
    }

    logger.info("Neo4j schema setup complete")
    return results


async def drop_all_constraints(client: Neo4jClient) -> int:
    """
    Drop all constraints (for testing/reset purposes).

    Args:
        client: Neo4j client instance.

    Returns:
        Number of constraints dropped.
    """
    query = "SHOW CONSTRAINTS"
    constraints = await client.run_query(query)

    dropped = 0
    for constraint in constraints:
        name = constraint.get("name")
        if name:
            try:
                await client.execute_write(f"DROP CONSTRAINT {name} IF EXISTS")
                dropped += 1
                logger.info("Dropped constraint: %s", name)
            except Exception as e:
                logger.error("Failed to drop constraint %s: %s", name, e)

    return dropped


async def drop_all_indexes(client: Neo4jClient) -> int:
    """
    Drop all indexes (for testing/reset purposes).

    Args:
        client: Neo4j client instance.

    Returns:
        Number of indexes dropped.
    """
    query = "SHOW INDEXES"
    indexes = await client.run_query(query)

    dropped = 0
    for index in indexes:
        name = index.get("name")
        # Skip internal indexes
        if name and not name.startswith("__"):
            try:
                await client.execute_write(f"DROP INDEX {name} IF EXISTS")
                dropped += 1
                logger.info("Dropped index: %s", name)
            except Exception as e:
                logger.error("Failed to drop index %s: %s", name, e)

    return dropped


async def reset_schema(client: Neo4jClient | None = None) -> dict[str, Any]:
    """
    Reset the Neo4j schema by dropping and recreating everything.

    WARNING: This will delete all data!

    Args:
        client: Optional Neo4j client.

    Returns:
        Summary of reset operations.
    """
    if client is None:
        client = get_neo4j_client()
        if not client.is_connected:
            await client.connect()

    logger.warning("Resetting Neo4j schema - all data will be deleted!")

    # Delete all nodes and relationships
    await client.execute_write("MATCH (n) DETACH DELETE n")
    logger.info("Deleted all nodes and relationships")

    # Drop constraints and indexes
    dropped_constraints = await drop_all_constraints(client)
    dropped_indexes = await drop_all_indexes(client)

    # Recreate schema
    setup_results = await setup_schema(client)

    return {
        "dropped": {
            "constraints": dropped_constraints,
            "indexes": dropped_indexes,
        },
        "created": setup_results,
    }


# CLI entry point
if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)

    async def main():
        client = get_neo4j_client()
        await client.connect()
        try:
            results = await setup_schema(client)
            print("Schema setup results:", results)
        finally:
            await client.disconnect()

    asyncio.run(main())
