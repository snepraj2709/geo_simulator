"""
Centralized configuration management for all services.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = False
    app_secret_key: str = Field(default="change-me-in-production")
    app_name: str = "LLM Brand Monitor"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_workers: int = 4
    api_reload: bool = False

    # Database (PostgreSQL)
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/llm_brand_monitor"
    )
    database_pool_size: int = 20
    database_max_overflow: int = 10
    database_echo: bool = False

    # Redis
    redis_url: RedisDsn = Field(default="redis://localhost:6379/0")
    redis_pool_size: int = 10

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    # Elasticsearch/OpenSearch
    elasticsearch_url: str = "http://localhost:9200"
    elasticsearch_user: str = "admin"
    elasticsearch_password: str = "admin"

    # S3/MinIO
    s3_bucket: str = "llm-brand-monitor"
    s3_region: str = "us-east-1"
    s3_endpoint_url: str | None = None  # For MinIO local development
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None

    # LLM API Keys
    openai_api_key: str | None = None
    google_api_key: str | None = None
    anthropic_api_key: str | None = None
    perplexity_api_key: str | None = None

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # JWT
    jwt_secret_key: str = Field(default="jwt-secret-change-me")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7

    # Rate Limiting
    rate_limit_auth: int = 10  # per minute
    rate_limit_read: int = 100  # per minute
    rate_limit_write: int = 30  # per minute
    rate_limit_simulation: int = 5  # per hour
    hard_scrape_cooldown_days: int = 7

    # Feature Flags
    feature_perplexity_enabled: bool = True
    feature_new_classifier: bool = False

    # Monitoring
    sentry_dsn: str | None = None
    log_level: str = "INFO"
    log_format: Literal["json", "console"] = "console"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
