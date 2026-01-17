"""
Main FastAPI application entry point.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.config import settings
from shared.db.postgres import close_db, init_db
from shared.db.redis import close_redis
from shared.graph import close_graph
from shared.utils.logging import setup_logging

from services.api.app.routers import (
    auth,
    brands,
    conversations,
    health,
    icps,
    simulations,
    websites,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    setup_logging()

    if settings.is_development:
        await init_db()

    yield

    # Shutdown
    await close_db()
    await close_redis()
    await close_graph()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="LLM Brand Influence Monitor",
        description="AI Visibility & Trust Platform - Simulate and audit LLM answers",
        version="0.1.0",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.is_development else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
    app.include_router(websites.router, prefix="/websites", tags=["Websites"])
    app.include_router(icps.router, prefix="/websites/{website_id}/icps", tags=["ICPs"])
    app.include_router(
        conversations.router,
        prefix="/websites/{website_id}/conversations",
        tags=["Conversations"],
    )
    app.include_router(
        simulations.router,
        prefix="/websites/{website_id}/simulations",
        tags=["Simulations"],
    )
    app.include_router(brands.router, prefix="/websites/{website_id}/brands", tags=["Brands"])

    return app


app = create_app()


def run():
    """Run the application with uvicorn."""
    import uvicorn

    uvicorn.run(
        "services.api.app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_reload,
        workers=settings.api_workers if not settings.api_reload else 1,
    )


if __name__ == "__main__":
    run()
