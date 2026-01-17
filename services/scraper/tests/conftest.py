"""
Pytest configuration and fixtures for scraper service tests.
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from shared.models.website import Website, ScrapedPage, WebsiteAnalysis
from shared.models.enums import WebsiteStatus


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session():
    """Create a test database session."""
    # Use in-memory SQLite for tests
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with engine.begin() as conn:
        # Create tables
        from shared.db.postgres import Base
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def sample_website():
    """Create a sample website for testing."""
    return Website(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        domain="example.com",
        url="https://example.com",
        name="Example Company",
        description="Test website",
        status=WebsiteStatus.PENDING.value,
        scrape_depth=3,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def sample_scraped_page():
    """Create a sample scraped page for testing."""
    return ScrapedPage(
        id=uuid.uuid4(),
        website_id=uuid.uuid4(),
        url="https://example.com/page",
        url_hash="abc123",
        title="Test Page",
        meta_description="Test description",
        content_text="Test content",
        word_count=100,
        page_type="homepage",
        http_status=200,
        scraped_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_playwright_browser():
    """Create a mock Playwright browser."""
    browser = AsyncMock()
    context = AsyncMock()
    page = AsyncMock()

    # Setup mock chain
    browser.new_context = AsyncMock(return_value=context)
    context.new_page = AsyncMock(return_value=page)
    context.close = AsyncMock()

    # Setup page mocks
    page.goto = AsyncMock()
    page.content = AsyncMock(return_value="<html><body>Test</body></html>")

    return browser


@pytest.fixture
def mock_celery_app():
    """Create a mock Celery app."""
    app = MagicMock()
    app.send_task = MagicMock()
    return app


@pytest.fixture
def sample_html():
    """Sample HTML for testing."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
        <meta name="description" content="Test description">
    </head>
    <body>
        <h1>Welcome</h1>
        <p>This is a test page.</p>
        <a href="/about">About</a>
        <a href="/contact">Contact</a>
        <a href="https://external.com">External</a>
    </body>
    </html>
    """
