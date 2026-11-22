"""API configuration settings.

Settings are resolved from environment variables prefixed with
``OPENSCIENCE_API_`` (for example ``OPENSCIENCE_API_SECRET_KEY``).
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class APISettings(BaseSettings):
    """Runtime configuration for the openScience REST API."""

    model_config = SettingsConfigDict(
        env_prefix="OPENSCIENCE_API_",
        env_file=".env",
        extra="ignore",
    )

    # Application
    title: str = "openScience API"
    description: str = "REST API for the openScience AI workbench."
    version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    debug: bool = False

    # Security
    secret_key: str = Field(
        default="openscience-dev-secret-key-change-in-production",
        description="Secret key used to sign JWT tokens.",
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # CORS
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = Field(default_factory=lambda: ["*"])
    cors_allow_headers: list[str] = Field(default_factory=lambda: ["*"])

    # Database
    database_url: str = Field(default_factory=lambda: f"sqlite:///{Path.cwd() / 'openscience.db'}")

    # Rate limiting (requests per minute per client IP)
    rate_limit: str = "60/minute"
    rate_limit_enabled: bool = True

    # Core framework
    sandbox_enabled: bool = False
    compute_backend: str = "local"


@lru_cache
def get_settings() -> APISettings:
    """Return cached API settings."""
    return APISettings()


def reset_settings_cache() -> None:
    """Clear the cached settings (useful for tests)."""
    get_settings.cache_clear()
