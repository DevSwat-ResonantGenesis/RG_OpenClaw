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

    # Platform URLs (internal Docker network)
    AGENT_ENGINE_URL: str = os.getenv(
        "AGENT_ENGINE_URL", "http://agent_engine_service:8000"
    )
    AUTH_SERVICE_URL: str = os.getenv(
        "AUTH_SERVICE_URL", "http://auth_service:8000"
    )
    MEMORY_SERVICE_URL: str = os.getenv(
        "MEMORY_SERVICE_URL", "http://memory_service:8000"
    )
    RARA_SERVICE_URL: str = os.getenv(
        "RARA_SERVICE_URL", "http://rg_internal_invarients_sim:8093"
    )
    BLOCKCHAIN_SERVICE_URL: str = os.getenv(
        "BLOCKCHAIN_SERVICE_URL", "http://blockchain_service:8000"
    )
    MARKETPLACE_SERVICE_URL: str = os.getenv(
        "MARKETPLACE_SERVICE_URL", "http://marketplace_service:8000"
    )

    # Public platform domain (used to build webhook URLs)
    PLATFORM_DOMAIN: str = os.getenv("PLATFORM_DOMAIN", "resonantgenesis.xyz")

    # Internal service key for service-to-service auth
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
        env_prefix = "OPENCLAW_"
        case_sensitive = False


settings = Settings()
