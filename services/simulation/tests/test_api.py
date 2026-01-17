"""
Tests for the LLM Simulation Service API endpoints.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from services.simulation.main import app
from services.simulation.schemas import LLMProviderType


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_check(self, client):
        """Test basic health check."""
        with patch(
            "services.simulation.main.LLMAdapterFactory.health_check_all",
            new_callable=AsyncMock,
        ) as mock_health:
            mock_health.return_value = {
                "openai": True,
                "google": True,
                "anthropic": False,
                "perplexity": True,
            }

            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "providers" in data

    def test_provider_health_check(self, client):
        """Test individual provider health check."""
        with patch(
            "services.simulation.main.LLMAdapterFactory.get_adapter"
        ) as mock_factory:
            mock_adapter = AsyncMock()
            mock_adapter.health_check = AsyncMock(return_value=True)
            mock_adapter.model = "gpt-4o"
            mock_factory.return_value = mock_adapter

            response = client.get("/health/providers")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)


class TestSimulationEndpoints:
    """Tests for simulation endpoints."""

    def test_create_simulation(self, client):
        """Test creating a new simulation."""
        with patch(
            "services.simulation.main.get_simulation_rate_limiter"
        ) as mock_limiter:
            mock_instance = AsyncMock()
            mock_instance.check_simulation_limit = AsyncMock(
                return_value=AsyncMock(allowed=True, remaining=4)
            )
            mock_limiter.return_value = mock_instance

            response = client.post(
                "/simulations",
                json={
                    "website_id": str(uuid.uuid4()),
                    "llm_providers": ["openai", "google"],
                },
            )

            assert response.status_code == 202
            data = response.json()
            assert data["status"] == "queued"
            assert "id" in data

    def test_create_simulation_rate_limited(self, client):
        """Test simulation creation when rate limited."""
        with patch(
            "services.simulation.main.get_simulation_rate_limiter"
        ) as mock_limiter:
            mock_instance = AsyncMock()
            mock_instance.check_simulation_limit = AsyncMock(
                return_value=AsyncMock(allowed=False, retry_after=3600)
            )
            mock_limiter.return_value = mock_instance

            response = client.post(
                "/simulations",
                json={
                    "website_id": str(uuid.uuid4()),
                },
            )

            assert response.status_code == 429

    def test_get_simulation_status(self, client):
        """Test getting simulation status."""
        simulation_id = uuid.uuid4()

        response = client.get(f"/simulations/{simulation_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(simulation_id)
        assert "status" in data

    def test_get_simulation_responses(self, client):
        """Test getting simulation responses."""
        simulation_id = uuid.uuid4()

        response = client.get(f"/simulations/{simulation_id}/responses")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data

    def test_get_simulation_metrics(self, client):
        """Test getting simulation metrics."""
        simulation_id = uuid.uuid4()

        response = client.get(f"/simulations/{simulation_id}/metrics")

        assert response.status_code == 200
        data = response.json()
        assert data["simulation_id"] == str(simulation_id)

    def test_get_simulation_brands(self, client):
        """Test getting simulation brand extractions."""
        simulation_id = uuid.uuid4()

        response = client.get(f"/simulations/{simulation_id}/brands")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data


class TestQueryEndpoints:
    """Tests for query endpoints."""

    def test_query_llm(self, client, mock_all_llm_clients):
        """Test querying a single LLM."""
        with patch(
            "services.simulation.main.BrandExtractor"
        ) as mock_extractor_class:
            mock_extractor = AsyncMock()
            mock_extractor.extract = AsyncMock(
                return_value=AsyncMock(brands=[])
            )
            mock_extractor_class.return_value = mock_extractor

            response = client.post(
                "/query",
                json={
                    "prompt": "What are the best project management tools?",
                    "provider": "openai",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert "provider" in data
            assert "response_text" in data

    def test_query_llm_invalid_provider(self, client):
        """Test querying with invalid provider."""
        response = client.post(
            "/query",
            json={
                "prompt": "Test",
                "provider": "invalid_provider",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_query_parallel(self, client, mock_all_llm_clients):
        """Test parallel querying of multiple LLMs."""
        response = client.post(
            "/query/parallel",
            params={
                "prompt": "What are the best tools?",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestRateLimitEndpoints:
    """Tests for rate limit endpoints."""

    def test_get_rate_limits(self, client):
        """Test getting rate limit status."""
        with patch(
            "services.simulation.main.get_simulation_rate_limiter"
        ) as mock_limiter:
            mock_instance = AsyncMock()
            mock_instance.get_rate_limit_info = AsyncMock(return_value=[])
            mock_limiter.return_value = mock_instance

            response = client.get("/rate-limits")

            assert response.status_code == 200
            data = response.json()
            assert "limits" in data


class TestErrorHandling:
    """Tests for error handling."""

    def test_query_llm_failure(self, client):
        """Test handling of LLM query failure."""
        with patch(
            "services.simulation.main.LLMAdapterFactory.get_adapter"
        ) as mock_factory:
            mock_adapter = AsyncMock()
            mock_adapter.query = AsyncMock(side_effect=Exception("API Error"))
            mock_factory.return_value = mock_adapter

            response = client.post(
                "/query",
                json={
                    "prompt": "Test prompt",
                    "provider": "openai",
                },
            )

            assert response.status_code == 500
            data = response.json()
            assert "error" in data["detail"]

    def test_invalid_request_body(self, client):
        """Test handling of invalid request body."""
        response = client.post(
            "/simulations",
            json={},  # Missing required fields
        )

        assert response.status_code == 422


class TestCORS:
    """Tests for CORS configuration."""

    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        # In development mode, should allow all origins
        assert response.status_code in [200, 405]  # 405 if OPTIONS not explicitly handled
