"""Property-based tests for Celery configuration from environment.

**Feature: async-task-processing, Property 1: Celery Configuration from Environment**
**Validates: Requirements 1.2, 1.3, 7.3, 7.4**
"""

import os
from typing import Generator

import pytest
from hypothesis import given, settings, strategies as st

from app.core.config import Settings


# Strategy for valid hostnames (alphanumeric with hyphens and dots)
hostname_strategy = st.from_regex(
    r"[a-zA-Z][a-zA-Z0-9\-\.]{0,49}",
    fullmatch=True
).filter(lambda x: len(x) > 0 and not x.endswith("-") and not x.endswith("."))

# Strategy for valid port numbers (1-65535)
port_strategy = st.integers(min_value=1, max_value=65535)


def make_base_env() -> dict[str, str]:
    """Create a base valid environment configuration without Redis settings."""
    return {
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_USER": "testuser",
        "POSTGRES_PASSWORD": "testpass",
        "POSTGRES_DB": "testdb",
        "SECRET_KEY": "test-secret-key",
        "DEBUG": "false",
    }


@pytest.fixture
def clean_env() -> Generator[None, None, None]:
    """Fixture to clean environment variables before and after tests."""
    # Store original environment
    original_env = dict(os.environ)
    
    # Clear relevant env vars
    env_keys_to_clear = [
        "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_USER", "POSTGRES_PASSWORD",
        "POSTGRES_DB", "REDIS_HOST", "REDIS_PORT", "SECRET_KEY", "DEBUG",
        "CELERY_BROKER_URL", "CELERY_RESULT_BACKEND"
    ]
    for key in env_keys_to_clear:
        os.environ.pop(key, None)
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@settings(max_examples=100)
@given(
    redis_host=hostname_strategy,
    redis_port=port_strategy,
)
def test_celery_broker_url_constructed_from_redis_settings(
    redis_host: str,
    redis_port: int,
) -> None:
    """
    **Feature: async-task-processing, Property 1: Celery Configuration from Environment**
    
    *For any* valid Redis host and port combination in environment variables,
    the Settings SHALL construct the celery_broker_url property using those values.
    
    **Validates: Requirements 1.2, 7.3**
    """
    # Store original environment
    original_env = dict(os.environ)
    
    try:
        # Clear relevant env vars
        env_keys_to_clear = [
            "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_USER", "POSTGRES_PASSWORD",
            "POSTGRES_DB", "REDIS_HOST", "REDIS_PORT", "SECRET_KEY", "DEBUG",
            "CELERY_BROKER_URL", "CELERY_RESULT_BACKEND"
        ]
        for key in env_keys_to_clear:
            os.environ.pop(key, None)
        
        # Set up environment with Redis settings
        env = make_base_env()
        env["REDIS_HOST"] = redis_host
        env["REDIS_PORT"] = str(redis_port)
        
        for key, value in env.items():
            os.environ[key] = value
        
        # Load settings (use _env_file=None to prevent loading from .env file)
        settings_instance = Settings(_env_file=None)
        
        # Verify broker URL is constructed from Redis settings
        expected_broker_url = f"redis://{redis_host}:{redis_port}/0"
        assert settings_instance.celery_broker_url == expected_broker_url, (
            f"Expected broker URL '{expected_broker_url}', "
            f"got '{settings_instance.celery_broker_url}'"
        )
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


@settings(max_examples=100)
@given(
    redis_host=hostname_strategy,
    redis_port=port_strategy,
)
def test_celery_result_backend_constructed_from_redis_settings(
    redis_host: str,
    redis_port: int,
) -> None:
    """
    **Feature: async-task-processing, Property 1: Celery Configuration from Environment**
    
    *For any* valid Redis host and port combination in environment variables,
    the Settings SHALL construct the celery_result_backend property using those values.
    
    **Validates: Requirements 1.3, 7.4**
    """
    # Store original environment
    original_env = dict(os.environ)
    
    try:
        # Clear relevant env vars
        env_keys_to_clear = [
            "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_USER", "POSTGRES_PASSWORD",
            "POSTGRES_DB", "REDIS_HOST", "REDIS_PORT", "SECRET_KEY", "DEBUG",
            "CELERY_BROKER_URL", "CELERY_RESULT_BACKEND"
        ]
        for key in env_keys_to_clear:
            os.environ.pop(key, None)
        
        # Set up environment with Redis settings
        env = make_base_env()
        env["REDIS_HOST"] = redis_host
        env["REDIS_PORT"] = str(redis_port)
        
        for key, value in env.items():
            os.environ[key] = value
        
        # Load settings (use _env_file=None to prevent loading from .env file)
        settings_instance = Settings(_env_file=None)
        
        # Verify result backend URL is constructed from Redis settings
        expected_backend_url = f"redis://{redis_host}:{redis_port}/0"
        assert settings_instance.celery_result_backend == expected_backend_url, (
            f"Expected result backend URL '{expected_backend_url}', "
            f"got '{settings_instance.celery_result_backend}'"
        )
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


@settings(max_examples=100)
@given(
    redis_host=hostname_strategy,
    redis_port=port_strategy,
)
def test_celery_broker_and_backend_urls_match(
    redis_host: str,
    redis_port: int,
) -> None:
    """
    **Feature: async-task-processing, Property 1: Celery Configuration from Environment**
    
    *For any* valid Redis host and port combination, the celery_broker_url and
    celery_result_backend properties SHALL produce identical URLs (both use same Redis).
    
    **Validates: Requirements 1.2, 1.3, 7.3, 7.4**
    """
    # Store original environment
    original_env = dict(os.environ)
    
    try:
        # Clear relevant env vars
        env_keys_to_clear = [
            "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_USER", "POSTGRES_PASSWORD",
            "POSTGRES_DB", "REDIS_HOST", "REDIS_PORT", "SECRET_KEY", "DEBUG",
            "CELERY_BROKER_URL", "CELERY_RESULT_BACKEND"
        ]
        for key in env_keys_to_clear:
            os.environ.pop(key, None)
        
        # Set up environment with Redis settings
        env = make_base_env()
        env["REDIS_HOST"] = redis_host
        env["REDIS_PORT"] = str(redis_port)
        
        for key, value in env.items():
            os.environ[key] = value
        
        # Load settings
        settings_instance = Settings(_env_file=None)
        
        # Both URLs should be identical (same Redis instance for broker and backend)
        assert settings_instance.celery_broker_url == settings_instance.celery_result_backend, (
            f"Broker URL '{settings_instance.celery_broker_url}' should match "
            f"backend URL '{settings_instance.celery_result_backend}'"
        )
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)
