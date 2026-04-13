"""
OpenClaw Integration Service
==============================

Standalone microservice for managing OpenClaw ↔ ResonantGenesis connections.

Architecture:
- Fully isolated — no shared DB, no shared imports from other services
- Communicates with platform via HTTP (agent_engine_service, auth_service)
- Can be enabled/disabled via OPENCLAW_SERVICE_ENABLED env var
- Can be removed from docker-compose without affecting any other service

Endpoints mounted at /openclaw/* via gateway proxy.
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="OpenClaw Integration Service",
    description="Manages OpenClaw ↔ ResonantGenesis agent connections via webhooks",
    version=settings.SERVICE_VERSION,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routes under root — gateway will prefix with /openclaw
app.include_router(router)


@app.get("/")
async def root():
    """Root endpoint — shows connector status and available endpoints."""
    from . import platform_auth
    tokens = platform_auth._token_cache or platform_auth._load_tokens()
    import time
    expires_at = tokens.get("expires_at", 0)
    authenticated = bool(tokens.get("access_token")) and time.time() < expires_at
    return {
        "service": "RG_OpenClaw Connector",
        "version": settings.SERVICE_VERSION,
        "status": "running",
        "authenticated": authenticated,
        "user": tokens.get("email", "") if authenticated else None,
        "platform": settings.PLATFORM_DOMAIN,
        "endpoints": {
            "health": "GET /health",
            "auth_login": "POST /auth/login",
            "auth_status": "GET /auth/status",
            "skills_available": "GET /skills/available",
            "skills_execute": "POST /skills/execute",
            "agents_register": "POST /agents/register",
            "agents_heartbeat": "POST /agents/heartbeat",
            "memory_ingest": "POST /memory/ingest",
            "memory_query": "POST /memory/query",
            "manifest": "GET /manifest",
            "task_execute": "POST /task/execute",
            "setup_guide": "GET /setup-guide",
            "polling": "Active — checks platform every 5s for tasks",
        },
        "docs": "http://localhost:8000/docs",
    }


@app.on_event("startup")
async def startup():
    logger.info(
        f"🦞 OpenClaw Service v{settings.SERVICE_VERSION} started "
        f"(enabled={settings.ENABLED}, domain={settings.PLATFORM_DOMAIN})"
    )
    # Start background polling for federated tasks
    from .routers import start_polling
    start_polling()
    logger.info("🦞 Federated task polling active — polling platform every 5s")


@app.on_event("shutdown")
async def shutdown():
    from .routers import stop_polling
    stop_polling()
    logger.info("🦞 OpenClaw Service shutting down")
