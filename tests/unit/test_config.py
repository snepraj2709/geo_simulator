"""Tests for configuration module."""

import pytest

from shared.config import Settings, get_settings


class TestSettings:
    """Test settings configuration."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = Settings()
        assert settings.app_env == "development"
        assert settings.api_port == 8000
        assert settings.database_pool_size == 20

    def test_is_development(self):
        """Test is_development property."""
        settings = Settings(app_env="development")
        assert settings.is_development is True
        assert settings.is_production is False

    def test_is_production(self):
        """Test is_production property."""
        settings = Settings(app_env="production")
        assert settings.is_development is False
        assert settings.is_production is True

    def test_get_settings_cached(self):
        """Test that get_settings returns cached instance."""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2
