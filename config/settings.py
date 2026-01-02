"""
GroupPulse Application Settings

Uses Pydantic Settings for environment variable validation and type safety.
All settings are loaded from environment variables or .env file.
"""

from typing import Optional
from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # =============================================================================
    # Application
    # =============================================================================
    APP_NAME: str = Field(default="GroupPulse", description="Application name")
    APP_VERSION: str = Field(default="1.0.0", description="Application version")
    ENVIRONMENT: str = Field(
        default="production",
        pattern="^(development|staging|production)$",
        description="Application environment"
    )
    DEBUG: bool = Field(default=False, description="Debug mode")
    LOG_LEVEL: str = Field(
        default="INFO",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
        description="Logging level"
    )

    # =============================================================================
    # Database (PostgreSQL or SQLite)
    # =============================================================================
    DATABASE_URL: str = Field(
        description="Database connection URL (PostgreSQL or SQLite)"
    )
    DB_POOL_SIZE: int = Field(default=10, ge=1, le=100, description="Connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=20, ge=0, le=100, description="Max overflow connections")
    DB_POOL_TIMEOUT: int = Field(default=30, ge=1, description="Pool timeout in seconds")
    DB_ECHO: bool = Field(default=False, description="Echo SQL queries (debugging)")

    # =============================================================================
    # Redis (Optional)
    # =============================================================================
    REDIS_URL: Optional[str] = Field(
        default=None,
        description="Redis connection URL (optional, for caching)"
    )
    REDIS_MAX_CONNECTIONS: int = Field(default=50, ge=1, le=200, description="Max Redis connections")

    # =============================================================================
    # Telegram Bot
    # =============================================================================
    BOT_TOKEN: str = Field(description="Telegram bot token from @BotFather")
    BOT_WEBHOOK_URL: Optional[str] = Field(default=None, description="Webhook URL (optional)")
    BOT_WEBHOOK_SECRET: Optional[str] = Field(default=None, description="Webhook secret (optional)")

    @field_validator("BOT_TOKEN")
    @classmethod
    def validate_bot_token(cls, v: str) -> str:
        """Validate bot token format."""
        if not v or ":" not in v:
            raise ValueError("BOT_TOKEN must be in format: 123456:ABC-DEF...")
        return v

    # =============================================================================
    # Telegram API Credentials (for all user accounts)
    # =============================================================================
    API_ID: int = Field(description="Telegram API ID from my.telegram.org")
    API_HASH: str = Field(description="Telegram API Hash from my.telegram.org")

    @field_validator("API_HASH")
    @classmethod
    def validate_api_hash(cls, v: str) -> str:
        """Validate API hash format."""
        if not v or len(v) != 32:
            raise ValueError("API_HASH must be 32 characters long")
        return v

    # =============================================================================
    # Security & Encryption
    # =============================================================================
    JWT_SECRET: str = Field(default="change-me-in-production", description="JWT secret key")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    JWT_EXPIRATION_HOURS: int = Field(default=24, ge=1, description="JWT expiration in hours")

    # =============================================================================
    # Rate Limiting
    # =============================================================================
    GLOBAL_RATE_LIMIT: int = Field(
        default=100,
        ge=1,
        description="Global system rate limit (messages/second)"
    )
    ACCOUNT_RATE_LIMIT: int = Field(
        default=20,
        ge=1,
        le=30,
        description="Per-account rate limit (messages/second)"
    )
    DESTINATION_RATE_LIMIT: int = Field(
        default=5,
        ge=1,
        description="Per-destination rate limit (messages/second)"
    )

    # =============================================================================
    # Performance
    # =============================================================================
    MAX_WORKERS: int = Field(default=10, ge=1, le=100, description="Max userbot workers")
    MAX_CONCURRENT_FORWARDS: int = Field(default=100, ge=1, description="Max concurrent forwards")
    MESSAGE_BATCH_SIZE: int = Field(default=50, ge=1, description="Batch size for DB operations")

    # =============================================================================
    # Data Retention
    # =============================================================================
    MESSAGE_LOG_RETENTION_DAYS: int = Field(
        default=30,
        ge=1,
        description="Message log retention in days"
    )
    METRICS_RETENTION_DAYS: int = Field(
        default=7,
        ge=1,
        description="Metrics retention in days"
    )

    # =============================================================================
    # Monitoring (Optional)
    # =============================================================================
    SENTRY_DSN: Optional[str] = Field(default=None, description="Sentry DSN for error tracking")
    PROMETHEUS_PORT: int = Field(default=8001, ge=1024, le=65535, description="Prometheus port")

    # =============================================================================
    # Computed Properties
    # =============================================================================
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.ENVIRONMENT == "production"

    def __repr__(self) -> str:
        """String representation (hide sensitive data)."""
        return f"<Settings environment={self.ENVIRONMENT} app={self.APP_NAME}>"


# Global settings instance (singleton)
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get application settings (singleton pattern).

    Returns:
        Settings: Application settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# Convenient alias
settings = get_settings()
