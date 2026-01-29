"""Application configuration with Pydantic Settings."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_env_file() -> str:
    """Find .env file in current or parent directory."""
    # Check current directory first (backend/.env)
    if Path(".env").exists():
        return ".env"
    # Then check parent directory (project root .env)
    if Path("../.env").exists():
        return "../.env"
    # Default to current directory
    return ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=_find_env_file(),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Epiphan Sales Agent"
    environment: str = "development"
    debug: bool = False
    version: str = "0.1.0"
    api_host: str = "0.0.0.0"
    api_port: int = 8001

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"]
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            import json

            return json.loads(v)
        return v

    # Database
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5433/epiphan_sales_agent"
    )
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_recycle: int = 3600

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Security
    jwt_secret_key: str = Field(default="change-me-in-production")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    crm_encryption_key: str = Field(default="")

    # AI Providers
    anthropic_api_key: str = Field(default="")
    cerebras_api_key: str = Field(default="")
    cerebras_api_base: str = "https://api.cerebras.ai/v1"
    deepseek_api_key: str = Field(default="")
    openrouter_api_key: str = Field(default="")

    # HubSpot
    hubspot_access_token: str = Field(default="")
    hubspot_client_id: str = Field(default="")
    hubspot_client_secret: str = Field(default="")
    hubspot_portal_id: str = Field(default="")

    # Clari Copilot
    clari_api_key: str = Field(default="")
    clari_api_base: str = "https://api.clari.com/v1"
    clari_workspace_id: str = Field(default="")

    # Supabase
    supabase_url: str = Field(default="")
    supabase_anon_key: str = Field(default="")
    supabase_service_key: str = Field(default="")
    supabase_jwt_secret: str = Field(default="")

    # Enrichment APIs
    apollo_api_key: str = Field(default="")
    hunter_api_key: str = Field(default="")
    clearbit_api_key: str = Field(default="")

    # Apollo Webhooks (PHONES ARE GOLD!)
    # See docs/reference/APOLLO_ENRICHMENT.md for details
    apollo_webhook_secret: str = Field(
        default="",
        description="Secret for validating Apollo webhook signatures (HMAC-SHA256)"
    )
    apollo_webhook_url: str = Field(
        default="",
        description="Public URL for Apollo phone callbacks. REQUIRED for mobile/direct phones. "
        "Example: https://api.yourdomain.com/api/webhooks/apollo/phone-reveal"
    )

    # Monitoring
    langchain_tracing_v2: bool = False
    langchain_api_key: str = Field(default="")
    langsmith_project: str = "epiphan-sales-agent"
    sentry_dsn: str = Field(default="")

    # Budget & Rate Limits
    daily_budget_usd: float = 50.0
    monthly_budget_usd: float = 1000.0
    cost_warning_threshold: float = 0.80
    cost_downgrade_threshold: float = 0.90
    cost_block_threshold: float = 1.00
    rate_limit_enabled: bool = True
    rate_limit_default: str = "100/minute"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
