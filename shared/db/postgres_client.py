"""
PostgreSQL client with connection pooling and health checks.

This module provides a robust PostgreSQL client with:
- Async connection pooling via SQLAlchemy
- Health check capabilities
- Connection statistics
- Graceful shutdown handling
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from sqlalchemy import event, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import AsyncAdaptedQueuePool

from shared.config import settings

logger = logging.getLogger(__name__)


class PostgresClient:
    """
    PostgreSQL database client with connection pooling.

    Provides async database access with connection pooling,
    health checks, and connection statistics.

    Usage:
        client = PostgresClient()
        await client.connect()

        async with client.session() as session:
            result = await session.execute(text("SELECT 1"))

        await client.disconnect()
    """

    def __init__(
        self,
        database_url: str | None = None,
        pool_size: int | None = None,
        max_overflow: int | None = None,
        pool_timeout: int = 30,
        pool_recycle: int = 1800,
        echo: bool | None = None,
    ):
        """
        Initialize PostgreSQL client.

        Args:
            database_url: PostgreSQL connection URL. Defaults to settings.
            pool_size: Number of connections to keep in pool. Defaults to settings.
            max_overflow: Max additional connections beyond pool_size. Defaults to settings.
            pool_timeout: Seconds to wait for connection from pool.
            pool_recycle: Seconds before recycling a connection.
            echo: Whether to log SQL statements. Defaults to settings.
        """
        self._database_url = database_url or str(settings.database_url)
        self._pool_size = pool_size or settings.database_pool_size
        self._max_overflow = max_overflow or settings.database_max_overflow
        self._pool_timeout = pool_timeout
        self._pool_recycle = pool_recycle
        self._echo = echo if echo is not None else settings.database_echo

        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None
        self._is_connected = False

    @property
    def engine(self) -> AsyncEngine:
        """Get the SQLAlchemy engine."""
        if self._engine is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._engine

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._is_connected

    async def connect(self) -> None:
        """
        Establish database connection and create connection pool.

        Raises:
            SQLAlchemyError: If connection fails.
        """
        if self._is_connected:
            logger.warning("PostgreSQL client already connected")
            return

        logger.info(
            "Connecting to PostgreSQL with pool_size=%d, max_overflow=%d",
            self._pool_size,
            self._max_overflow,
        )

        try:
            self._engine = create_async_engine(
                self._database_url,
                poolclass=AsyncAdaptedQueuePool,
                pool_size=self._pool_size,
                max_overflow=self._max_overflow,
                pool_timeout=self._pool_timeout,
                pool_recycle=self._pool_recycle,
                pool_pre_ping=True,  # Enable connection health checks
                echo=self._echo,
                future=True,
            )

            # Set up event listeners for connection pool monitoring
            event.listen(self._engine.sync_engine, "checkout", self._on_checkout)
            event.listen(self._engine.sync_engine, "checkin", self._on_checkin)

            self._session_factory = async_sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )

            # Verify connection
            async with self._engine.connect() as conn:
                await conn.execute(text("SELECT 1"))

            self._is_connected = True
            logger.info("PostgreSQL connection established successfully")

        except SQLAlchemyError as e:
            logger.error("Failed to connect to PostgreSQL: %s", e)
            raise

    async def disconnect(self) -> None:
        """
        Close database connections and dispose of the connection pool.
        """
        if not self._is_connected:
            return

        logger.info("Disconnecting from PostgreSQL")

        if self._engine:
            await self._engine.dispose()
            self._engine = None

        self._session_factory = None
        self._is_connected = False
        logger.info("PostgreSQL connection closed")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session from the pool.

        Yields:
            AsyncSession: Database session.

        Raises:
            RuntimeError: If not connected.
            SQLAlchemyError: If session operations fail.
        """
        if not self._session_factory:
            raise RuntimeError("Database not connected. Call connect() first.")

        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except SQLAlchemyError:
            await session.rollback()
            raise
        finally:
            await session.close()

    @asynccontextmanager
    async def connection(self) -> AsyncGenerator[AsyncConnection, None]:
        """
        Get a raw database connection from the pool.

        Yields:
            AsyncConnection: Database connection.
        """
        async with self.engine.connect() as conn:
            yield conn

    async def health_check(self) -> dict[str, Any]:
        """
        Perform database health check.

        Returns:
            dict: Health status including connection info.
        """
        try:
            async with self.engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                _ = result.scalar()

            pool = self.engine.pool
            return {
                "status": "healthy",
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalid": pool.invalidatedcount() if hasattr(pool, "invalidatedcount") else 0,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }

    async def get_pool_stats(self) -> dict[str, int]:
        """
        Get connection pool statistics.

        Returns:
            dict: Pool statistics.
        """
        if not self._engine:
            return {}

        pool = self._engine.pool
        return {
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
        }

    def _on_checkout(self, dbapi_conn: Any, connection_record: Any, connection_proxy: Any) -> None:
        """Event handler for connection checkout from pool."""
        logger.debug("Connection checked out from pool")

    def _on_checkin(self, dbapi_conn: Any, connection_record: Any) -> None:
        """Event handler for connection checkin to pool."""
        logger.debug("Connection returned to pool")


# Global client instance
_client: PostgresClient | None = None


def get_postgres_client() -> PostgresClient:
    """
    Get the global PostgreSQL client instance.

    Returns:
        PostgresClient: The global client instance.
    """
    global _client
    if _client is None:
        _client = PostgresClient()
    return _client


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for getting a database session.

    Yields:
        AsyncSession: Database session.
    """
    client = get_postgres_client()
    async with client.session() as session:
        yield session
