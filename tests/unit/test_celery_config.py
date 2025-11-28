"""Unit tests for Celery configuration.

Tests Celery instance initialization, configuration loading from environment
variables, broker URL and backend URL construction, and serialization settings.

**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6**
"""

import os
from typing import Generator

import pytest


@pytest.fixture
def clean_env() -> Generator[None, None, None]:
    """Fixture to clean environment variables before and after tests."""
    original_env = dict(os.environ)
    yield
    os.environ.clear()
    os.environ.update(original_env)


def make_valid_env() -> dict[str, str]:
    """Create a complete valid environment configuration."""
    return {
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_USER": "testuser",
        "POSTGRES_PASSWORD": "testpass",
        "POSTGRES_DB": "testdb",
        "REDIS_HOST": "redis-test",
        "REDIS_PORT": "6380",
        "SECRET_KEY": "test-secret-key",
        "DEBUG": "false",
    }


class TestCeleryInstanceInitialization:
    """Tests for Celery instance initialization (Requirement 1.1)."""

    def test_celery_app_has_unique_application_name(self) -> None:
        """Test that Celery instance is created with unique application name.
        
        **Validates: Requirement 1.1**
        """
        from app.core.celery_app import celery_app
        
        assert celery_app.main == "hfts_worker", (
            f"Expected Celery app name 'hfts_worker', got '{celery_app.main}'"
        )

    def test_celery_app_is_celery_instance(self) -> None:
        """Test that celery_app is a proper Celery instance.
        
        **Validates: Requirement 1.1**
        """
        from celery import Celery
        from app.core.celery_app import celery_app
        
        assert isinstance(celery_app, Celery), (
            f"Expected Celery instance, got {type(celery_app)}"
        )


class TestCeleryConfigurationLoading:
    """Tests for configuration loading from environment (Requirements 1.2, 1.3)."""

    def test_celery_broker_url_uses_redis_settings(self, clean_env: None) -> None:
        """Test that broker URL is constructed from Redis settings.
        
        **Validates: Requirement 1.2**
        """
        from app.core.config import Settings
        
        env = make_valid_env()
        for key, value in env.items():
            os.environ[key] = value
        
        settings = Settings(_env_file=None)
        
        expected_url = f"redis://{env['REDIS_HOST']}:{env['REDIS_PORT']}/0"
        assert settings.celery_broker_url == expected_url

    def test_celery_result_backend_uses_redis_settings(self, clean_env: None) -> None:
        """Test that result backend URL is constructed from Redis settings.
        
        **Validates: Requirement 1.3**
        """
        from app.core.config import Settings
        
        env = make_valid_env()
        for key, value in env.items():
            os.environ[key] = value
        
        settings = Settings(_env_file=None)
        
        expected_url = f"redis://{env['REDIS_HOST']}:{env['REDIS_PORT']}/0"
        assert settings.celery_result_backend == expected_url

    def test_celery_uses_default_redis_when_not_specified(self, clean_env: None) -> None:
        """Test that default Redis settings are used when not specified.
        
        **Validates: Requirements 1.2, 1.3**
        """
        from app.core.config import Settings
        
        # Set only required env vars (no REDIS_HOST/PORT)
        env = {
            "POSTGRES_HOST": "localhost",
            "POSTGRES_PORT": "5432",
            "POSTGRES_USER": "testuser",
            "POSTGRES_PASSWORD": "testpass",
            "POSTGRES_DB": "testdb",
            "SECRET_KEY": "test-secret-key",
        }
        for key, value in env.items():
            os.environ[key] = value
        
        settings = Settings(_env_file=None)
        
        # Default Redis is localhost:6379
        expected_url = "redis://localhost:6379/0"
        assert settings.celery_broker_url == expected_url
        assert settings.celery_result_backend == expected_url


class TestCelerySerializationSettings:
    """Tests for serialization settings (Requirements 1.4, 1.5, 1.6)."""

    def test_task_serializer_is_json(self) -> None:
        """Test that task serialization format is JSON.
        
        **Validates: Requirement 1.4**
        """
        from app.core.celery_app import celery_app
        
        assert celery_app.conf.task_serializer == "json", (
            f"Expected task_serializer 'json', got '{celery_app.conf.task_serializer}'"
        )

    def test_result_serializer_is_json(self) -> None:
        """Test that result serialization format is JSON.
        
        **Validates: Requirement 1.5**
        """
        from app.core.celery_app import celery_app
        
        assert celery_app.conf.result_serializer == "json", (
            f"Expected result_serializer 'json', got '{celery_app.conf.result_serializer}'"
        )

    def test_accept_content_includes_json(self) -> None:
        """Test that accept_content includes JSON.
        
        **Validates: Requirement 1.6**
        """
        from app.core.celery_app import celery_app
        
        assert "json" in celery_app.conf.accept_content, (
            f"Expected 'json' in accept_content, got {celery_app.conf.accept_content}"
        )


class TestCeleryAdditionalSettings:
    """Tests for additional Celery configuration settings."""

    def test_timezone_is_utc(self) -> None:
        """Test that timezone is set to UTC."""
        from app.core.celery_app import celery_app
        
        assert celery_app.conf.timezone == "UTC"

    def test_enable_utc_is_true(self) -> None:
        """Test that enable_utc is True."""
        from app.core.celery_app import celery_app
        
        assert celery_app.conf.enable_utc is True

    def test_task_track_started_is_enabled(self) -> None:
        """Test that task tracking is enabled."""
        from app.core.celery_app import celery_app
        
        assert celery_app.conf.task_track_started is True

    def test_task_time_limit_is_set(self) -> None:
        """Test that task time limit is configured."""
        from app.core.celery_app import celery_app
        
        assert celery_app.conf.task_time_limit == 300  # 5 minutes

    def test_result_expires_is_set(self) -> None:
        """Test that result expiration is configured."""
        from app.core.celery_app import celery_app
        
        assert celery_app.conf.result_expires == 3600  # 1 hour
