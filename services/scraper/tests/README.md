# Website Scraper Service - Testing Guide

## Prerequisites

Install test dependencies:

```bash
pip install pytest pytest-asyncio pytest-cov aiosqlite
```

If pip fails, try:
```bash
python -m pip install pytest pytest-asyncio pytest-cov aiosqlite
```

## Running Tests

### All Tests
```bash
pytest tests/ -v
```

### With Coverage
```bash
pytest tests/ --cov=services.scraper --cov-report=html
```

### Specific Test Files
```bash
# Component tests
pytest tests/test_components.py -v

# API tests
pytest tests/test_api.py -v
```

### Individual Test Classes
```bash
pytest tests/test_components.py::TestURLQueueManager -v
pytest tests/test_components.py::TestCircuitBreaker -v
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py           # Pytest fixtures
├── test_components.py    # Component unit tests
└── test_api.py          # API endpoint tests
```

## Fixtures Available

- `db_session` - In-memory SQLite database
- `sample_website` - Test website data
- `sample_scraped_page` - Test page data
- `mock_playwright_browser` - Mock Playwright browser
- `mock_celery_app` - Mock Celery app
- `sample_html` - Sample HTML for parsing

## Test Coverage

### Components
- ✅ URLQueueManager - Depth limiting, deduplication
- ✅ ContentParser - HTML parsing, link extraction
- ✅ RateLimiter - Rate limiting, hard scrape cooldown
- ✅ ErrorHandler - Error categorization, retry logic
- ✅ CircuitBreaker - Failure detection, auto-recovery

### API Endpoints
- ✅ POST /scrape - Scrape submission
- ✅ GET /scrape/{job_id}/status - Job status
- ✅ GET /scrape/{website_id}/content - Scraped content

## Troubleshooting

### pytest not found
Make sure pytest is installed in your Python environment:
```bash
python -m pytest --version
```

### Import errors
Make sure you're in the project root or have PYTHONPATH set:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/../.."  # Unix
$env:PYTHONPATH="$env:PYTHONPATH;$(pwd)\..\..\"  # Windows PowerShell
```

### Database errors
Tests use in-memory SQLite. If you see database errors, ensure aiosqlite is installed:
```bash
pip install aiosqlite
```

## Manual Testing

If automated tests fail, you can manually test the scraper:

```python
import asyncio
from services.scraper.scraper import WebsiteScraper

async def test_scrape():
    async with WebsiteScraper(max_depth=2, max_pages=10) as scraper:
        results, entities = await scraper.scrape_website("https://example.com")
        print(f"Scraped {len(results)} pages")
        for result in results:
            print(f"  {result.url}: {'✓' if result.success else '✗'}")

asyncio.run(test_scrape())
```

## CI/CD Integration

For CI/CD pipelines:

```yaml
# .github/workflows/test.yml
- name: Install dependencies
  run: pip install -r requirements-test.txt

- name: Run tests
  run: pytest tests/ --cov=services.scraper --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
```
