# Base image for all services
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VERSION=1.7.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="$POETRY_HOME/bin:$PATH"

# Set work directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Install dependencies
RUN poetry install --no-root --no-dev

# Copy application code
COPY shared/ ./shared/
COPY services/ ./services/

# Install the application
RUN poetry install --no-dev

# -------------------------------------------
# API Service
# -------------------------------------------
FROM base as api

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the API service
CMD ["uvicorn", "services.api.app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# -------------------------------------------
# Celery Worker
# -------------------------------------------
FROM base as worker

# Install Playwright for scraping (optional, can be moved to scraper-specific image)
RUN playwright install chromium && playwright install-deps chromium

# Run Celery worker
CMD ["celery", "-A", "shared.queue.celery_app", "worker", "-l", "info", "-Q", "default,scraping,simulation,classification,analysis,graph"]

# -------------------------------------------
# Celery Beat (Scheduler)
# -------------------------------------------
FROM base as beat

# Run Celery beat
CMD ["celery", "-A", "shared.queue.celery_app", "beat", "-l", "info"]

# -------------------------------------------
# Flower (Celery Monitor)
# -------------------------------------------
FROM base as flower

EXPOSE 5555

# Run Flower
CMD ["celery", "-A", "shared.queue.celery_app", "flower", "--port=5555"]
