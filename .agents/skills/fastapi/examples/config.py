"""
Example: Configuration & Settings
===================================
Reference implementation of Pydantic BaseSettings with environment validation,
secrets management, and environment-specific configuration.

Location: app/core/config.py
"""

from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings — loaded from environment variables and .env file.

    Rules:
    1. ALL configuration goes through this class — no scattered os.getenv().
    2. Secrets use SecretStr to prevent accidental logging.
    3. Validators run at startup — app fails fast on invalid config.
    4. Defaults are for development; production values come from environment.

    Usage:
        from app.core.config import settings
        print(settings.APP_NAME)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # Ignore unrecognized env vars
    )

    # ═══════════════════════════════════════════════════════════════════════
    # APPLICATION
    # ═══════════════════════════════════════════════════════════════════════

    APP_NAME: str = "Backend Clima"
    APP_VERSION: str = "0.1.0"
    APP_DESCRIPTION: str = "Backend Clima API"
    ENVIRONMENT: str = Field(
        default="development",
        description="Runtime environment: development | staging | production",
    )
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # ═══════════════════════════════════════════════════════════════════════
    # DATABASE
    # ═══════════════════════════════════════════════════════════════════════

    DATABASE_URL: str = Field(
        ...,
        description="Async database connection URL (e.g., postgresql+asyncpg://user:pass@host/db)",
    )
    DATABASE_POOL_SIZE: int = Field(default=5, ge=1, le=50)
    DATABASE_MAX_OVERFLOW: int = Field(default=10, ge=0, le=100)
    DATABASE_POOL_TIMEOUT: int = Field(default=30, ge=5, le=120)
    DATABASE_ECHO: bool = False  # Set True to log SQL queries (dev only)

    # ═══════════════════════════════════════════════════════════════════════
    # SECURITY
    # ═══════════════════════════════════════════════════════════════════════

    SECRET_KEY: SecretStr = Field(
        ...,
        description="JWT signing key — generate with: openssl rand -hex 32",
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=5, le=1440)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, ge=1, le=90)

    # ═══════════════════════════════════════════════════════════════════════
    # CORS
    # ═══════════════════════════════════════════════════════════════════════

    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = ["*"]

    # ═══════════════════════════════════════════════════════════════════════
    # REDIS (optional)
    # ═══════════════════════════════════════════════════════════════════════

    REDIS_URL: str | None = Field(
        default=None,
        description="Redis URL for caching/task queue (e.g., redis://localhost:6379/0)",
    )

    # ═══════════════════════════════════════════════════════════════════════
    # LOGGING
    # ═══════════════════════════════════════════════════════════════════════

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = Field(
        default="json",
        description="Log format: json (structured) | text (human-readable)",
    )

    # ═══════════════════════════════════════════════════════════════════════
    # PRODUCTION SETTINGS
    # ═══════════════════════════════════════════════════════════════════════

    ALLOWED_HOSTS: list[str] = ["*"]  # Restrict in production!
    WORKERS: int = Field(default=4, ge=1, le=32)

    # ═══════════════════════════════════════════════════════════════════════
    # VALIDATORS
    # ═══════════════════════════════════════════════════════════════════════

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Ensure ENVIRONMENT is one of the allowed values."""
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            msg = f"ENVIRONMENT must be one of {allowed}, got '{v}'"
            raise ValueError(msg)
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Ensure LOG_LEVEL is a valid Python logging level."""
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed:
            msg = f"LOG_LEVEL must be one of {allowed}, got '{v}'"
            raise ValueError(msg)
        return v.upper()

    @field_validator("LOG_FORMAT")
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        """Ensure LOG_FORMAT is either 'json' or 'text'."""
        if v not in {"json", "text"}:
            msg = f"LOG_FORMAT must be 'json' or 'text', got '{v}'"
            raise ValueError(msg)
        return v

    # ═══════════════════════════════════════════════════════════════════════
    # COMPUTED PROPERTIES
    # ═══════════════════════════════════════════════════════════════════════

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == "development"

    @property
    def show_docs(self) -> bool:
        """Whether to expose /docs and /redoc (disabled in production)."""
        return not self.is_production


# ─── Cached Settings Instance ────────────────────────────────────────────────


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Using lru_cache ensures the .env file is read only once.
    To reload settings (e.g., in tests), clear the cache:
        get_settings.cache_clear()
    """
    return Settings()


# Module-level convenience access
settings = get_settings()
