"""Property-based tests for configuration validation.

**Feature: high-frequency-transaction-system, Property 4: Configuration Validation**
**Validates: Requirements 3.1, 3.2**
"""

import os
from typing import Any

import pytest
from hypothesis import given, settings, strategies as st
from pydantic import ValidationError

from app.core.config import Settings


# Required database parameters that must be present
REQUIRED_DB_PARAMS = ["POSTGRES_HOST", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"]

# All parameters needed for a valid configuration
ALL_REQUIRED_PARAMS = REQUIRED_DB_PARAMS + ["SECRET_KEY"]


def make_valid_env() -> dict[str, str]:
    """Create a complete valid environment configuration."""
    return {
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_USER": "testuser",
        "POSTGRES_PASSWORD": "testpass",
        "POSTGRES_DB": "testdb",
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "SECRET_KEY": "test-secret-key",
        "DEBUG": "false",
    }


@settings(max_examples=100)
@given(missing_param=st.sampled_from(ALL_REQUIRED_PARAMS))
def test_missing_required_param_raises_validation_error(missing_param: str) -> None:
    """
    **Feature: high-frequency-transaction-system, Property 4: Configuration Validation**
    
    *For any* set of environment variables missing a required database parameter
    (POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB) or SECRET_KEY,
    loading the Settings SHALL raise a ValidationError.
    
    **Validates: Requirements 3.1, 3.2**
    """
    # Create valid env and remove one required param
    env = make_valid_env()
    del env[missing_param]
    
    # Clear any existing env vars that might interfere
    original_env = {}
    for key in make_valid_env().keys():
        if key in os.environ:
            original_env[key] = os.environ.pop(key)
    
    try:
        # Set our test environment
        for key, value in env.items():
            os.environ[key] = value
        
        # Attempting to load settings should raise ValidationError
        # Use _env_file=None to prevent loading from .env file during test
        with pytest.raises(ValidationError):
            Settings(_env_file=None)
    finally:
        # Restore original environment
        for key in env.keys():
            if key in os.environ:
                del os.environ[key]
        for key, value in original_env.items():
            os.environ[key] = value


# Strategy for valid environment variable values (no null characters, non-empty after strip)
env_value_strategy = st.text(
    alphabet=st.characters(blacklist_characters="\x00"),
    min_size=1,
    max_size=50,
).filter(lambda x: x.strip())


@settings(max_examples=100)
@given(
    host=env_value_strategy,
    user=env_value_strategy,
    password=env_value_strategy,
    db=env_value_strategy,
    secret=env_value_strategy,
)
def test_valid_config_loads_successfully(
    host: str, user: str, password: str, db: str, secret: str
) -> None:
    """
    **Feature: high-frequency-transaction-system, Property 4: Configuration Validation**
    
    *For any* complete set of valid environment variables, loading the Settings
    SHALL succeed and provide typed access to all configuration values.
    
    **Validates: Requirements 3.1, 3.3**
    """
    env = {
        "POSTGRES_HOST": host,
        "POSTGRES_PORT": "5432",
        "POSTGRES_USER": user,
        "POSTGRES_PASSWORD": password,
        "POSTGRES_DB": db,
        "SECRET_KEY": secret,
    }
    
    # Clear any existing env vars
    original_env = {}
    for key in make_valid_env().keys():
        if key in os.environ:
            original_env[key] = os.environ.pop(key)
    
    try:
        for key, value in env.items():
            os.environ[key] = value
        
        # Use _env_file=None to prevent loading from .env file during test
        settings = Settings(_env_file=None)
        
        # Verify typed access to all values
        assert settings.POSTGRES_HOST == host
        assert settings.POSTGRES_USER == user
        assert settings.POSTGRES_PASSWORD == password
        assert settings.POSTGRES_DB == db
        assert settings.SECRET_KEY == secret
        assert isinstance(settings.POSTGRES_PORT, int)
        assert settings.POSTGRES_PORT == 5432
        
        # Verify database_url property constructs correctly
        expected_url = f"postgresql+asyncpg://{user}:{password}@{host}:5432/{db}"
        assert settings.database_url == expected_url
    finally:
        for key in env.keys():
            if key in os.environ:
                del os.environ[key]
        for key, value in original_env.items():
            os.environ[key] = value
