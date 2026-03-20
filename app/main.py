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


@app.on_event("startup")
async def startup():
    logger.info(
        f"🦞 OpenClaw Service v{settings.SERVICE_VERSION} started "
        f"(enabled={settings.ENABLED}, domain={settings.PLATFORM_DOMAIN})"
    )


@app.on_event("shutdown")
async def shutdown():
    logger.info("🦞 OpenClaw Service shutting down")
