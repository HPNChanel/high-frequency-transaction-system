"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.
    
    All required database parameters must be provided via environment
    variables or a .env file. Missing required parameters will raise
    a ValidationError at application startup.
    """
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Ignore extra environment variables
    )
    
    # Database - Required
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    
    # Redis - Optional with defaults
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    
    # Application
    SECRET_KEY: str
    DEBUG: bool = False
    
    @property
    def database_url(self) -> str:
        """Construct async PostgreSQL database URL with asyncpg driver."""
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


# Singleton settings instance - lazily loaded
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the application settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
