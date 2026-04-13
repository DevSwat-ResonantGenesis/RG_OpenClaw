"""
OpenClaw Service Configuration
===============================

All settings loaded from environment variables.
Service is fully isolated — communicates with platform only via HTTP.
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Service identity
    SERVICE_NAME: str = "openclaw_service"
    SERVICE_VERSION: str = "1.0.0"

    # Platform URLs — defaults are standalone (through gateway HTTPS).
    # Docker-internal URLs are set via environment variables in docker-compose.
    AGENT_ENGINE_URL: str = os.getenv(
        "AGENT_ENGINE_URL", "https://dev-swat.com/api/v1/agents"
    )
    AUTH_SERVICE_URL: str = os.getenv(
        "AUTH_SERVICE_URL", "https://dev-swat.com/auth"
    )
    MEMORY_SERVICE_URL: str = os.getenv(
        "MEMORY_SERVICE_URL", "https://dev-swat.com/api/v1/memory"
    )
    RARA_SERVICE_URL: str = os.getenv(
        "RARA_SERVICE_URL", "https://dev-swat.com/api/v1/rara"
    )
    BLOCKCHAIN_SERVICE_URL: str = os.getenv(
        "BLOCKCHAIN_SERVICE_URL", "https://dev-swat.com/blockchain"
    )
    MARKETPLACE_SERVICE_URL: str = os.getenv(
        "MARKETPLACE_SERVICE_URL", "https://dev-swat.com/api/v1/marketplace"
    )
    LLM_SERVICE_URL: str = os.getenv(
        "LLM_SERVICE_URL", "https://dev-swat.com/api/v1/llm"
    )

    # Public platform domain (used to build webhook URLs)
    PLATFORM_DOMAIN: str = os.getenv("PLATFORM_DOMAIN", "dev-swat.com")

    # Internal service key for service-to-service auth (Docker only)
    INTERNAL_SERVICE_KEY: str = os.getenv("INTERNAL_SERVICE_KEY", "")

    # OpenClaw service toggle — can disable without removing from compose
    ENABLED: bool = os.getenv("OPENCLAW_SERVICE_ENABLED", "true").lower() == "true"

    # HMAC default secret length (bytes) for auto-generated webhook secrets
    DEFAULT_SECRET_LENGTH: int = 32

    # Rate limiting
    MAX_CONNECTIONS_PER_USER: int = 10
    WEBHOOK_RELAY_TIMEOUT_SECONDS: float = 30.0

    # Heartbeat
    HEARTBEAT_TIMEOUT_SECONDS: int = 120  # Agent offline if no heartbeat in 2 min

    class Config:
        case_sensitive = False


settings = Settings()
