"""
Pytest fixtures for Knowledge Graph Builder tests.

Provides mock Neo4j client and test data fixtures.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Any


class MockNeo4jClient:
    """Mock Neo4j client for testing without a real database."""

    def __init__(self):
        self._data = {
            "nodes": {},  # label -> {id -> node_data}
            "edges": [],  # list of edge data
        }
        self._query_results = []

    async def execute_query(self, query: str, params: dict[str, Any]) -> list[dict]:
        """
        Mock query execution.

        Returns pre-configured results or simulates based on query patterns.
        """
        # If we have pre-configured results, use them
        if self._query_results:
            return self._query_results.pop(0)

        # Simulate based on query patterns
        query_lower = query.lower()

        # Count queries
        if "count(" in query_lower and "return count" in query_lower:
            return [{"count": len(self._data.get("nodes", {}).get("Brand", {}))}]

        # MERGE/CREATE queries - return mock node/edge
        if "merge" in query_lower or "create" in query_lower:
            # Extract label from query
            for label in ["Brand", "ICP", "Intent", "Concern", "BeliefType", "LLMProvider", "Conversation"]:
                if label.lower() in query_lower:
                    return [{label[0].lower(): {"id": params.get("id", "test-id"), **params}}]
            # For edges, return the relationship
            return [{"r": params, "count": 1}]

        # MATCH queries - return empty by default unless configured
        if "match" in query_lower:
            return []

        return []

    def set_query_results(self, results: list[list[dict]]) -> None:
        """Set pre-configured query results."""
        self._query_results = results

    async def health_check(self) -> bool:
        """Mock health check."""
        return True

    async def close(self) -> None:
        """Mock close."""
        pass


@pytest.fixture
def mock_neo4j_client():
    """Create a mock Neo4j client."""
    return MockNeo4jClient()


@pytest.fixture
def sample_brand_data():
    """Sample brand data for testing."""
    return {
        "id": "brand-123",
        "name": "TestBrand",
        "normalized_name": "testbrand",
        "domain": "testbrand.com",
        "industry": "Technology",
        "is_tracked": True,
    }


@pytest.fixture
def sample_icp_data():
    """Sample ICP data for testing."""
    return {
        "id": "icp-123",
        "name": "Tech Product Manager",
        "website_id": "website-123",
        "demographics": {
            "age_range": "25-45",
            "location": "US",
        },
        "pain_points": [
            "Difficulty prioritizing features",
            "Lack of team alignment",
        ],
        "goals": [
            "Improve product velocity",
            "Better stakeholder communication",
        ],
    }


@pytest.fixture
def sample_intent_data():
    """Sample intent data for testing."""
    return {
        "id": "intent-123",
        "prompt_id": "prompt-123",
        "intent_type": "evaluation",
        "funnel_stage": "consideration",
        "buying_signal": 0.7,
        "trust_need": 0.8,
        "query_text": "Best tools for feature prioritization",
    }


@pytest.fixture
def sample_concern_data():
    """Sample concern data for testing."""
    return {
        "id": "concern-123",
        "description": "Difficulty prioritizing features",
        "category": "pain_point",
    }


@pytest.fixture
def sample_conversation_data():
    """Sample conversation data for testing."""
    return {
        "id": "conv-123",
        "topic": "Feature prioritization tools",
        "context": "Product manager looking for tools",
    }


@pytest.fixture
def sample_llm_provider_data():
    """Sample LLM provider data for testing."""
    return {
        "name": "openai",
        "model": "gpt-4",
    }


@pytest.fixture
def sample_simulation_data():
    """Sample simulation data for graph building."""
    return {
        "icps": [
            {
                "id": "icp-1",
                "name": "Tech PM",
                "website_id": "website-1",
                "demographics": {"age_range": "25-45"},
                "pain_points": ["Feature prioritization"],
                "goals": ["Improve velocity"],
            }
        ],
        "conversations": [
            {
                "id": "conv-1",
                "topic": "Product management tools",
                "context": "Evaluating options",
                "icp_id": "icp-1",
            }
        ],
        "prompts": [
            {
                "id": "prompt-1",
                "conversation_id": "conv-1",
                "prompt_text": "Best product management tools?",
                "classification": {
                    "intent_type": "evaluation",
                    "funnel_stage": "consideration",
                    "buying_signal": 0.6,
                    "trust_need": 0.7,
                },
            }
        ],
        "responses": [
            {
                "prompt_id": "prompt-1",
                "llm_provider": "openai",
                "llm_model": "gpt-4",
                "brand_states": [
                    {
                        "brand_name": "ProductBoard",
                        "normalized_name": "productboard",
                        "presence": "recommended",
                        "position_rank": 1,
                        "belief_sold": "outcome",
                        "confidence": 0.9,
                    },
                    {
                        "brand_name": "Aha",
                        "normalized_name": "aha",
                        "presence": "mentioned",
                        "position_rank": 2,
                        "belief_sold": "truth",
                        "confidence": 0.7,
                    },
                ],
            }
        ],
    }


@pytest.fixture
def sample_brand_state():
    """Sample brand state from LLM response."""
    return {
        "brand_name": "TestBrand",
        "normalized_name": "testbrand",
        "presence": "recommended",
        "position_rank": 1,
        "belief_sold": "outcome",
        "confidence": 0.85,
    }
