# LLM Brand Influence Monitor

An AI Visibility & Trust Platform that simulates and audits LLM answers to measure brand presence, competitive positioning, and belief formation across major language models.

## Overview

Unlike traditional SEO tools that score pages, this platform **simulates how LLMs perceive and recommend brands** by:

- Modeling question clusters from Ideal Customer Profiles (ICPs)
- Mapping entity dominance across multiple LLM providers
- Analyzing LLM answer construction patterns
- Building knowledge graphs of brand relationships

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Core Services                            │
├─────────────────────────────────────────────────────────────────┤
│  Website Scraper → ICP Generator → Conversation Generator       │
│         ↓               ↓                   ↓                   │
│  Prompt Classifier → LLM Simulation → Brand Presence Detector   │
│         ↓               ↓                   ↓                   │
│  Knowledge Graph Builder → Competitive Substitution Engine      │
└─────────────────────────────────────────────────────────────────┘
```

## Tech Stack

- **Backend**: Python 3.11, FastAPI
- **Task Queue**: Celery + Redis
- **Databases**: PostgreSQL, Neo4j, Elasticsearch
- **LLM Providers**: OpenAI, Anthropic, Google, Perplexity
- **Infrastructure**: Docker, Kubernetes

## Prerequisites

- Python 3.11+
- Poetry 1.7+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+
- Neo4j 5+

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/geo_simulator.git
cd geo_simulator
```

### 2. Set Up Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API keys and configuration
# At minimum, set your LLM API keys:
# - OPENAI_API_KEY
# - ANTHROPIC_API_KEY
# - GOOGLE_API_KEY (optional)
# - PERPLEXITY_API_KEY (optional)
```

### 3. Start with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Check service health
docker-compose ps
```

### 4. Or Run Locally with Poetry

```bash
# Install dependencies
poetry install

# Run database migrations
poetry run alembic upgrade head

# Start the API server
poetry run uvicorn services.api.app.main:app --reload

# In another terminal, start Celery worker
poetry run celery -A shared.queue.celery_app worker -l info

# In another terminal, start Celery beat (scheduler)
poetry run celery -A shared.queue.celery_app beat -l info
```

### 5. Access the Services

- **API Documentation**: http://localhost:8000/docs
- **API Health Check**: http://localhost:8000/health
- **Flower (Task Monitor)**: http://localhost:5555
- **Neo4j Browser**: http://localhost:7474
- **MinIO Console**: http://localhost:9001

## Project Structure

```
llm-brand-monitor/
├── docs/                      # Documentation
│   ├── ARCHITECTURE.md        # System architecture
│   ├── DATA_MODEL.md          # Database schemas
│   ├── API_SPEC.md            # API documentation
│   └── DEPLOYMENT.md          # Deployment guide
├── services/                  # Microservices
│   ├── api/                   # REST API service
│   │   └── app/
│   │       ├── main.py        # FastAPI application
│   │       ├── routers/       # API endpoints
│   │       ├── schemas/       # Pydantic models
│   │       └── dependencies.py
│   ├── scraper/               # Website scraping
│   ├── simulator/             # LLM simulation
│   ├── classifier/            # Prompt classification
│   ├── analyzer/              # Brand analysis
│   └── graph_builder/         # Knowledge graph
├── shared/                    # Shared libraries
│   ├── config.py              # Configuration
│   ├── db/                    # Database clients
│   │   ├── postgres.py
│   │   └── redis.py
│   ├── graph/                 # Neo4j client
│   ├── llm/                   # LLM clients
│   │   ├── openai_client.py
│   │   ├── anthropic_client.py
│   │   └── google_client.py
│   ├── models/                # SQLAlchemy models
│   ├── queue/                 # Celery configuration
│   └── utils/                 # Utilities
├── tests/                     # Test suites
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── scripts/                   # Utility scripts
├── docker-compose.yml         # Development setup
├── docker-compose.prod.yml    # Production overrides
├── Dockerfile                 # Multi-stage build
├── pyproject.toml             # Poetry configuration
└── .env.example               # Environment template
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_ENV` | Environment (development/staging/production) | `development` |
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `REDIS_URL` | Redis connection string | Required |
| `NEO4J_URI` | Neo4j connection URI | Required |
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `ANTHROPIC_API_KEY` | Anthropic API key | Optional |
| `GOOGLE_API_KEY` | Google AI API key | Optional |
| `PERPLEXITY_API_KEY` | Perplexity API key | Optional |

See `.env.example` for all available options.

## API Usage

### Authentication

```bash
# Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123", "name": "John", "organization_name": "Acme"}'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'
```

### Submit a Website

```bash
curl -X POST http://localhost:8000/websites \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "name": "Example Company"}'
```

### Run a Simulation

```bash
curl -X POST http://localhost:8000/websites/<website_id>/simulations \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"llm_providers": ["openai", "anthropic", "google"]}'
```

## Development

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=shared --cov=services

# Run specific test file
poetry run pytest tests/unit/test_llm_client.py
```

### Code Quality

```bash
# Format code
poetry run black .

# Lint code
poetry run ruff check .

# Type checking
poetry run mypy .
```

### Database Migrations

```bash
# Create a new migration
poetry run alembic revision --autogenerate -m "Description"

# Apply migrations
poetry run alembic upgrade head

# Rollback one migration
poetry run alembic downgrade -1
```

## Deployment

### Docker

```bash
# Build images
docker-compose build

# Production deployment
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Kubernetes

See `docs/DEPLOYMENT.md` for Kubernetes deployment instructions including:
- Helm charts
- Resource limits
- Horizontal Pod Autoscaling
- Ingress configuration

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [Data Model](docs/DATA_MODEL.md)
- [API Specification](docs/API_SPEC.md)
- [Deployment Guide](docs/DEPLOYMENT.md)

## Key Concepts

### Brand Presence States

```
ignored → mentioned → trusted → recommended → compared
```

- **ignored**: Brand not mentioned at all
- **mentioned**: Brand name appears without context
- **trusted**: Brand cited as authority without sales push
- **recommended**: Brand with clear call-to-action
- **compared**: Brand in neutral evaluation context

### Belief Types

```
truth | superiority | outcome | transaction | identity | social_proof
```

Each LLM response installs one primary belief type per brand mentioned.

### User Intent Classification

```json
{
  "intent_type": "informational | evaluation | decision",
  "funnel_stage": "awareness | consideration | purchase",
  "buying_signal": 0.0 - 1.0,
  "trust_need": 0.0 - 1.0
}
```

## License

MIT License - see LICENSE file for details.

## Support

- Issues: [GitHub Issues](https://github.com/your-org/llm-brand-monitor/issues)
- Documentation: [docs/](docs/)
