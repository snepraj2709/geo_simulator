"""
Tests for FastAPI endpoints.
"""

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from services.scraper.main import app
from services.scraper.schemas import ScrapeType, JobStatus


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health check returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "service": "scraper"}


class TestScrapeEndpoint:
    """Tests for POST /scrape endpoint."""

    @patch("services.scraper.main.get_db")
    @patch("services.scraper.main.celery_app")
    def test_submit_scrape_success(self, mock_celery, mock_db, client, sample_website):
        """Test successful scrape submission."""
        # Mock database
        mock_session = AsyncMock()
        mock_db.return_value = mock_session

        # Mock website query
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_website
        mock_session.execute.return_value = mock_result

        # Submit scrape
        website_id = str(sample_website.id)
        response = client.post(
            f"/scrape?website_id={website_id}",
            json={"type": "incremental"},
        )

        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "queued"
        assert data["type"] == "incremental"
        assert "job_id" in data

    @patch("services.scraper.main.get_db")
    def test_submit_scrape_website_not_found(self, mock_db, client):
        """Test scrape submission with non-existent website."""
        # Mock database
        mock_session = AsyncMock()
        mock_db.return_value = mock_session

        # Mock website not found
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        website_id = str(uuid.uuid4())
        response = client.post(
            f"/scrape?website_id={website_id}",
            json={"type": "incremental"},
        )

        assert response.status_code == 404

    @patch("services.scraper.main.get_db")
    @patch("services.scraper.main.rate_limiter")
    def test_submit_hard_scrape_limit_exceeded(
        self, mock_limiter, mock_db, client, sample_website
    ):
        """Test hard scrape limit exceeded."""
        # Mock database
        mock_session = AsyncMock()
        mock_db.return_value = mock_session

        mock_result = AsyncMock()
        mock_result.scalar_one_or_none.return_value = sample_website
        mock_session.execute.return_value = mock_result

        # Mock rate limiter
        mock_limiter.can_hard_scrape.return_value = False
        mock_limiter.next_hard_scrape_available.return_value = datetime.now(
            timezone.utc
        )

        website_id = str(sample_website.id)
        response = client.post(
            f"/scrape?website_id={website_id}",
            json={"type": "hard"},
        )

        assert response.status_code == 429


class TestJobStatusEndpoint:
    """Tests for GET /scrape/{job_id}/status endpoint."""

    @patch("services.scraper.main.get_job")
    def test_get_job_status_success(self, mock_get_job, client):
        """Test successful job status retrieval."""
        from services.scraper.schemas import ScrapeJobData

        job_id = uuid.uuid4()
        mock_job = ScrapeJobData(
            job_id=job_id,
            website_id=uuid.uuid4(),
            type=ScrapeType.INCREMENTAL,
            status=JobStatus.RUNNING,
            total_pages=10,
            completed_pages=5,
        )
        mock_get_job.return_value = mock_job

        response = client.get(f"/scrape/{job_id}/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["completed_pages"] == 5

    @patch("services.scraper.main.get_job")
    def test_get_job_status_not_found(self, mock_get_job, client):
        """Test job status for non-existent job."""
        mock_get_job.return_value = None

        job_id = uuid.uuid4()
        response = client.get(f"/scrape/{job_id}/status")

        assert response.status_code == 404


class TestScrapedContentEndpoint:
    """Tests for GET /scrape/{website_id}/content endpoint."""

    @patch("services.scraper.main.get_db")
    def test_get_scraped_content_success(
        self, mock_db, client, sample_website, sample_scraped_page
    ):
        """Test successful scraped content retrieval."""
        # Mock database
        mock_session = AsyncMock()
        mock_db.return_value = mock_session

        # Mock queries
        mock_website_result = AsyncMock()
        mock_website_result.scalar_one_or_none.return_value = sample_website

        mock_count_result = AsyncMock()
        mock_count_result.scalar.return_value = 1

        mock_pages_result = AsyncMock()
        mock_pages_result.scalars.return_value.all.return_value = [sample_scraped_page]

        mock_analysis_result = AsyncMock()
        mock_analysis_result.scalar_one_or_none.return_value = None

        mock_session.execute.side_effect = [
            mock_website_result,
            mock_count_result,
            mock_pages_result,
            mock_analysis_result,
        ]

        website_id = str(sample_website.id)
        response = client.get(f"/scrape/{website_id}/content")

        assert response.status_code == 200
        data = response.json()
        assert data["total_pages"] == 1
        assert len(data["pages"]) == 1

    @patch("services.scraper.main.get_db")
    def test_get_scraped_content_with_pagination(self, mock_db, client, sample_website):
        """Test scraped content with pagination."""
        # Mock database
        mock_session = AsyncMock()
        mock_db.return_value = mock_session

        mock_website_result = AsyncMock()
        mock_website_result.scalar_one_or_none.return_value = sample_website

        mock_count_result = AsyncMock()
        mock_count_result.scalar.return_value = 100

        mock_pages_result = AsyncMock()
        mock_pages_result.scalars.return_value.all.return_value = []

        mock_analysis_result = AsyncMock()
        mock_analysis_result.scalar_one_or_none.return_value = None

        mock_session.execute.side_effect = [
            mock_website_result,
            mock_count_result,
            mock_pages_result,
            mock_analysis_result,
        ]

        website_id = str(sample_website.id)
        response = client.get(f"/scrape/{website_id}/content?page=2&limit=20")

        assert response.status_code == 200
        data = response.json()
        assert data["total_pages"] == 100
