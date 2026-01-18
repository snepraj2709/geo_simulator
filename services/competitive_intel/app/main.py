"""
Competitive Substitution Engine - FastAPI Application.

Provides competitive analysis capabilities:
- Share of voice analysis
- Substitution pattern detection
- Competitive gap identification
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from shared.config import settings
from shared.db.neo4j_client import get_neo4j_client
from shared.utils.logging import setup_logging, get_logger

from services.competitive_intel.app.router import router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    setup_logging()
    logger.info("Starting Competitive Substitution Engine")

    # Connect to Neo4j
    neo4j_client = get_neo4j_client()
    try:
        await neo4j_client.connect()
        logger.info("Neo4j connection established")
    except Exception as e:
        logger.warning(f"Neo4j connection failed: {e}")

    yield

    # Shutdown
    logger.info("Shutting down Competitive Substitution Engine")
    await neo4j_client.disconnect()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Competitive Substitution Engine",
        description="Analyze brand substitution patterns across LLM providers",
        version="1.0.0",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    # Register router
    app.include_router(
        router,
        prefix="/competitive",
        tags=["Competitive Analysis"],
    )

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": "competitive-substitution-engine"}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "services.competitive_intel.app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
    )
