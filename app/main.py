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
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

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


# Dashboard HTML path
_DASHBOARD_HTML = Path(__file__).parent / "static" / "dashboard.html"


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint — serves the OpenClaw dashboard UI."""
    if _DASHBOARD_HTML.exists():
        return HTMLResponse(_DASHBOARD_HTML.read_text())
    return HTMLResponse("<h1>OpenClaw Connector</h1><p>Dashboard file not found. Check app/static/dashboard.html</p>")


@app.get("/api/status")
async def api_status():
    """Programmatic status endpoint (JSON)."""
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
        "docs": "http://localhost:8000/docs",
    }


@app.get("/dashboard/data")
async def dashboard_data():
    """Live dashboard data for the UI."""
    from .routers import _polling_active, _poll_stats, _task_log
    from . import platform_auth
    import time as _time

    tokens = platform_auth._token_cache or platform_auth._load_tokens()
    expires_at = tokens.get("expires_at", 0)
    authenticated = bool(tokens.get("access_token")) and _time.time() < expires_at
    user_id = tokens.get("user_id", "")

    # Fetch agents from platform if authenticated
    agents = []
    if authenticated and user_id:
        try:
            from .routers import _agent_engine_request
            data = await _agent_engine_request("GET", "agents/", user_id)
            raw = data if isinstance(data, list) else data.get("agents", [])
            for a in raw:
                if a.get("agent_source") == "federated":
                    agents.append({
                        "name": a.get("name", "Unknown"),
                        "mode": a.get("mode", "governed"),
                        "tools_count": len(a.get("tools", [])),
                        "status": "active" if a.get("is_active") else "inactive",
                        "id": a.get("id", ""),
                    })
        except Exception:
            pass

    return {
        "polling_active": _polling_active,
        "poll_count": _poll_stats.get("count", 0),
        "tasks_picked": _poll_stats.get("tasks_picked", 0),
        "last_poll": _poll_stats.get("last_poll", None),
        "agents": agents,
        "tasks": list(_task_log),
        "recent_activity": list(_poll_stats.get("activity", [])),
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
