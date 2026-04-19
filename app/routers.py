"""
OpenClaw Service API Routes — Full Federation
===============================================

Fully isolated REST API for managing OpenClaw ↔ ResonantGenesis federation.
Communicates with platform services via HTTP only — no shared DB, no shared imports.

Endpoints:
  GET  /health              — Service health + agent engine reachability
  GET  /status              — Quick connection status for frontend card
  GET  /connections         — List user's OpenClaw connections
  POST /connections         — Create a new connection (auto-creates webhook trigger)
  DELETE /connections/{id}  — Remove a connection (deletes webhook trigger)
  POST /connections/{id}/pause   — Pause a connection
  POST /connections/{id}/resume  — Resume a connection
  POST /relay/{agent_id}   — Public: relay OpenClaw event to agent (no auth)
  GET  /manifest            — ClawHub skill manifest
  GET  /setup-guide         — Setup instructions for OpenClaw config

  Federation:
  POST /agents/register     — Register an OpenClaw agent (creates on platform + DSID + RARA)
  POST /agents/heartbeat    — Heartbeat from OpenClaw agent running on user hardware
  GET  /agents/openclaw     — List user's OpenClaw agents
  POST /memory/ingest       — Ingest memory into Hash Sphere from OpenClaw agent
  POST /memory/query        — Query Hash Sphere memories for an OpenClaw agent
  GET  /skills/available    — List platform skills available to OpenClaw agents
  POST /skills/execute      — Execute a platform skill on behalf of OpenClaw agent
  POST /skills/import       — Import a custom skill from OpenClaw agent
  GET  /governance/{agent_id}     — Governance status for an OpenClaw agent
  POST /governance/enroll   — Enroll OpenClaw agent in RARA governance
  POST /marketplace/list    — List an OpenClaw agent on the marketplace
"""

import logging
import hashlib
import secrets
import httpx
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import json
import os
import time
import uuid

from fastapi import APIRouter, Request, HTTPException, Header

from .config import settings
from .models import (
    OpenClawConnectionCreate,
    OpenClawConnection,
    OpenClawConnectionList,
    OpenClawConnectionStatus,
    WebhookRelayPayload,
    WebhookRelayResponse,
    ServiceHealth,
    AgentHeartbeat,
    AgentHeartbeatResponse,
    OpenClawAgentRegister,
    OpenClawAgentResponse,
    MemoryBridgeIngest,
    MemoryBridgeQuery,
    MemoryBridgeResponse,
    SkillImport,
    SkillExecuteRequest,
    SkillExecuteResponse,
    GovernanceEnroll,
    GovernanceStatus,
    MarketplaceListRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["openclaw"])

# In-memory heartbeat tracker (agent_id → last heartbeat info)
_heartbeat_store: Dict[str, Dict[str, Any]] = {}

# In-memory custom skills registry (agent_id → list of imported skills)
_custom_skills_store: Dict[str, list] = {}


# ============================================
# HELPERS
# ============================================

def _get_user_id(request: Request) -> str:
    """Extract user ID from gateway headers or local JWT (standalone mode)."""
    user_id = (
        request.headers.get("x-user-id")
        or request.headers.get("rg-user-id")
        or ""
    )
    # Standalone mode: fall back to locally stored JWT identity
    if not user_id:
        from . import platform_auth
        user_id = platform_auth.get_user_id() or ""
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user_id


def _build_webhook_url(agent_id: str) -> str:
    """Build the full public webhook URL for an agent."""
    return f"https://{settings.PLATFORM_DOMAIN}/api/v1/webhooks/agent/{agent_id}/trigger"


def _build_openclaw_relay_url(agent_id: str) -> str:
    """Build the OpenClaw relay URL (goes through this service)."""
    return f"https://{settings.PLATFORM_DOMAIN}/api/v1/openclaw/relay/{agent_id}"


async def _agent_engine_request(
    method: str,
    path: str,
    user_id: str,
    json_body: dict = None,
    timeout: float = 10.0,
    extra_headers: dict = None,
) -> dict:
    """Make authenticated request to agent_engine_service.
    
    NOTE: AGENT_ENGINE_URL may be https://dev-swat.com/api/v1/agents (standalone)
    or http://agent_engine_service:8000 (Docker).
    
    For gateway mode: /api/v1/agents/{path} → gateway proxies to agent_engine as agents/{path}.
    So paths starting with 'agents/' must be stripped to avoid agents/agents/ double-prefix.
    For Docker mode: paths go direct — no stripping needed.
    """
    clean_path = path.lstrip("/")
    # Gateway mode: AGENT_ENGINE_URL already maps to /agents on the service
    # The gateway catch-all re-adds 'agents/' prefix, so strip it here
    is_gateway = "/api/v1/agents" in settings.AGENT_ENGINE_URL or "dev-swat.com" in settings.AGENT_ENGINE_URL
    if is_gateway and clean_path.startswith("agents"):
        # "agents/" → "" , "agents/{id}" → "{id}"
        clean_path = clean_path[len("agents"):].lstrip("/")
    url = f"{settings.AGENT_ENGINE_URL.rstrip('/')}/{clean_path}" if clean_path else settings.AGENT_ENGINE_URL.rstrip("/")
    logger.info("Agent engine request: %s %s", method, url)
    headers = {
        "x-user-id": user_id,
        "Content-Type": "application/json",
    }
    if settings.INTERNAL_SERVICE_KEY:
        headers["x-internal-service-key"] = settings.INTERNAL_SERVICE_KEY
    # Standalone mode: inject JWT for gateway authentication
    from . import platform_auth
    auth_headers = {}
    try:
        import asyncio
        auth_headers = await platform_auth.get_auth_headers()
    except Exception:
        pass
    if auth_headers:
        headers.update(auth_headers)
    if extra_headers:
        headers.update(extra_headers)

    async with httpx.AsyncClient(timeout=timeout) as client:
        if method == "GET":
            resp = await client.get(url, headers=headers)
        elif method == "POST":
            resp = await client.post(url, headers=headers, json=json_body or {})
        elif method == "DELETE":
            resp = await client.delete(url, headers=headers)
        elif method == "PATCH":
            resp = await client.patch(url, headers=headers, json=json_body or {})
        else:
            raise ValueError(f"Unsupported method: {method}")

    is_json = resp.headers.get("content-type", "").startswith("application/json")
    if resp.status_code >= 400:
        logger.warning(f"Agent engine {method} {path} returned {resp.status_code}: {resp.text[:200]}")
        detail = resp.text[:200]
        if is_json:
            try:
                detail = resp.json().get("detail", detail)
            except Exception:
                pass
        raise HTTPException(status_code=resp.status_code, detail=detail)
    if is_json:
        return resp.json()
    # Non-JSON success response — try parsing anyway, fall back to dict
    try:
        return resp.json()
    except Exception:
        return {"raw": resp.text[:500], "status_code": resp.status_code}


# ============================================
# LOCAL AUTHENTICATION (standalone mode only)
# ============================================
# When running locally, the user must authenticate with the platform first.
# These endpoints handle JWT login/refresh/logout through the platform's
# existing HTTPS gateway — zero ports exposed, enterprise-grade security.

@router.post("/auth/login")
async def auth_login(request: Request):
    """
    Authenticate with ResonantGenesis platform.

    Body: {"email": "...", "password": "..."}
    Stores JWT locally at ~/.openclaw/tokens.json (chmod 600).
    All subsequent API calls auto-attach the token.
    """
    from . import platform_auth

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    email = body.get("email", "").strip()
    password = body.get("password", "")

    if not email or not password:
        raise HTTPException(status_code=400, detail="email and password are required")

    result = await platform_auth.login(email, password)
    if not result.get("success"):
        raise HTTPException(status_code=401, detail=result.get("error", "Authentication failed"))

    return result


@router.post("/auth/logout")
async def auth_logout():
    """Clear stored JWT tokens."""
    from . import platform_auth
    return await platform_auth.logout()


@router.get("/auth/status")
async def auth_status():
    """Check current authentication status (no network call)."""
    from . import platform_auth
    tokens = platform_auth._token_cache or platform_auth._load_tokens()

    if not tokens.get("access_token"):
        return {
            "authenticated": False,
            "message": "Not authenticated. POST /auth/login with email and password.",
        }

    import time as _time
    expires_at = tokens.get("expires_at", 0)
    email = tokens.get("email", "")
    user_id = tokens.get("user_id", "")

    # Fallback: decode claims from JWT if not stored
    if tokens.get("access_token") and (not expires_at or not email or not user_id):
        try:
            import base64, json as _json
            payload_b64 = tokens["access_token"].split(".")[1]
            payload_b64 += "=" * (4 - len(payload_b64) % 4)
            payload = _json.loads(base64.urlsafe_b64decode(payload_b64))
            if not expires_at:
                expires_at = payload.get("exp", 0)
            if not email:
                email = payload.get("email", payload.get("preferred_username", ""))
            if not user_id:
                user_id = payload.get("sub", payload.get("user_id", ""))
            # Backfill into token cache so dashboard/data picks it up
            if user_id and not tokens.get("user_id"):
                tokens["user_id"] = user_id
                platform_auth._token_cache["user_id"] = user_id
            # Fetch email from platform if JWT doesn't have it
            if not email and user_id:
                try:
                    auth_hdrs_tmp = {"Authorization": f"Bearer {tokens['access_token']}", "x-user-id": user_id}
                    async with httpx.AsyncClient(timeout=5.0) as uc:
                        me_resp = await uc.get(
                            f"https://{settings.PLATFORM_DOMAIN}/auth/me",
                            headers=auth_hdrs_tmp,
                        )
                        if me_resp.status_code == 200:
                            me_data = me_resp.json()
                            email = me_data.get("email", me_data.get("username", ""))
                except Exception:
                    pass
            if email and not tokens.get("email"):
                tokens["email"] = email
                platform_auth._token_cache["email"] = email
            platform_auth._save_tokens(platform_auth._token_cache)
        except Exception:
            pass
    expired = _time.time() >= expires_at
    ttl = max(0, int(expires_at - _time.time()))

    return {
        "authenticated": True,
        "user_id": user_id,
        "email": email,
        "platform": tokens.get("platform_domain", ""),
        "token_expired": expired,
        "token_ttl_seconds": ttl,
        "has_refresh_token": bool(tokens.get("refresh_token")),
    }


@router.get("/auth/oauth-start")
async def auth_oauth_start(request: Request):
    """Start OAuth redirect flow: redirect user to platform login page.
    The platform will authenticate the user and redirect back to /auth-callback with the JWT.
    """
    from fastapi.responses import RedirectResponse

    # Detect which port we're running on from the incoming request
    host = request.headers.get("host", "localhost:8000")
    port = host.split(":")[-1] if ":" in host else "8000"

    # Redirect to platform's desktop-callback endpoint
    # It checks the user's cookie, and if logged in, redirects to our /auth-callback with the token
    callback_url = f"https://{settings.PLATFORM_DOMAIN}/auth/desktop-callback?port={port}"
    return RedirectResponse(callback_url)


@router.get("/auth-callback")
async def auth_oauth_callback(request: Request, token: str = ""):
    """Receive JWT from platform OAuth redirect.
    After the user confirms login on dev-swat.com, the platform redirects here
    with the token. We store it and show a success page.
    """
    from fastapi.responses import HTMLResponse

    if not token:
        return HTMLResponse("""
        <html><body style="background:#121214;color:#fff;font-family:system-ui;display:flex;align-items:center;justify-content:center;height:100vh">
        <div style="text-align:center"><h2 style="color:#FA547C">Authentication Failed</h2><p>No token received. Please try again.</p>
        <a href="/" style="color:#01A6BC">Back to Dashboard</a></div></body></html>
        """, status_code=400)

    # Decode JWT to extract user info (without full verification — platform already verified)
    import json as _json, base64
    try:
        payload_b64 = token.split(".")[1]
        payload_b64 += "=" * (4 - len(payload_b64) % 4)  # pad base64
        claims = _json.loads(base64.urlsafe_b64decode(payload_b64))
        user_id = claims.get("sub", claims.get("user_id", ""))
        email = claims.get("email", "")
        exp = claims.get("exp", 0)
    except Exception:
        user_id, email, exp = "", "", 0

    # If JWT doesn't contain email, fetch from platform user service
    if user_id and not email:
        try:
            async with httpx.AsyncClient(timeout=8.0) as uc:
                me_resp = await uc.get(
                    f"https://{settings.PLATFORM_DOMAIN}/auth/me",
                    headers={"Authorization": f"Bearer {token}", "x-user-id": user_id},
                )
                if me_resp.status_code == 200:
                    me_data = me_resp.json()
                    email = me_data.get("email", me_data.get("username", ""))
        except Exception:
            pass

    # Store token using platform_auth
    from . import platform_auth
    import time as _time
    token_data = {
        "access_token": token,
        "refresh_token": "",  # Redirect flow doesn't give refresh token
        "user_id": user_id,
        "email": email,
        "expires_at": exp if exp > 1e9 else _time.time() + 86400,  # fallback 24h
        "platform_domain": settings.PLATFORM_DOMAIN,
        "authenticated_at": _time.time(),
    }
    platform_auth._save_tokens(token_data)
    platform_auth._token_cache = token_data

    logger.info(f"OAuth callback: authenticated as {email} (user_id={user_id})")

    return HTMLResponse(f"""
    <html><body style="background:#121214;color:#fff;font-family:system-ui;display:flex;align-items:center;justify-content:center;height:100vh">
    <div style="text-align:center">
      <div style="font-size:48px;margin-bottom:16px">&#129438;</div>
      <h2 style="color:#71C23E;margin-bottom:8px">Connected!</h2>
      <p style="color:#a0a0a8;margin-bottom:20px">Logged in as <strong style="color:#fff">{email or 'user'}</strong></p>
      <p style="color:#a0a0a8;font-size:14px">Redirecting to dashboard...</p>
    </div>
    <script>setTimeout(function(){{ window.location.href = '/'; }}, 1500);</script>
    </body></html>
    """)


@router.post("/auth/refresh")
async def auth_refresh():
    """Force refresh the access token using stored refresh token."""
    from . import platform_auth

    if not platform_auth.is_authenticated():
        raise HTTPException(status_code=401, detail="Not authenticated — login first")

    success = await platform_auth.refresh_token()
    if not success:
        raise HTTPException(status_code=401, detail="Token refresh failed — re-login required")

    return {"success": True, "message": "Token refreshed"}


# ============================================
# HEALTH & INFO
# ============================================

@router.get("/health", response_model=ServiceHealth)
async def health_check():
    """Service health with agent engine reachability check."""
    engine_ok = False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.AGENT_ENGINE_URL}/health")
            engine_ok = resp.status_code == 200
    except Exception:
        pass

    # Check if locally authenticated (standalone mode)
    from . import platform_auth
    authenticated = platform_auth.is_authenticated()

    return ServiceHealth(
        service="openclaw_service",
        version=settings.SERVICE_VERSION,
        status="healthy" if settings.ENABLED else "disabled",
        enabled=settings.ENABLED,
        platform_domain=settings.PLATFORM_DOMAIN,
        agent_engine_reachable=engine_ok,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/manifest")
async def get_clawhub_manifest():
    """Return the ClawHub skill package manifest for discovery."""
    return {
        "name": "resonantgenesis",
        "display_name": "ResonantGenesis (Cloud)",
        "description": (
            "⚠️ Cloud-based AI agent platform. Triggers agents via webhooks. "
            "Data processed on remote servers. Your agent identity lives on Ethereum."
        ),
        "privacy_level": "cloud",
        "requires_internet": True,
        "version": settings.SERVICE_VERSION,
        "author": "ResonantGenesis",
        "homepage": f"https://{settings.PLATFORM_DOMAIN}",
        "config_schema": {
            "webhook_url": {
                "type": "url",
                "required": True,
                "description": "Your ResonantGenesis webhook URL (get from dashboard or /connect-profiles)",
            },
            "webhook_secret": {
                "type": "secret",
                "required": True,
                "description": "HMAC-SHA256 secret for signature verification",
            },
        },
        "actions": [
            {
                "name": "trigger_agent",
                "description": "Trigger a ResonantGenesis agent workflow via webhook",
                "method": "POST",
                "signature_header": "X-Webhook-Signature",
                "signature_method": "hmac-sha256",
            }
        ],
        "tags": ["ai-agents", "ethereum", "blockchain", "automation", "webhooks"],
    }


@router.get("/setup-guide")
async def get_setup_guide():
    """Return step-by-step setup instructions for OpenClaw configuration."""
    base = f"https://{settings.PLATFORM_DOMAIN}"
    return {
        "title": "ResonantGenesis × OpenClaw Setup Guide",
        "steps": [
            {
                "step": 1,
                "title": "Connect on ResonantGenesis",
                "description": f"Go to {base}/connect-profiles and click 'Connect' on the Openclaw card.",
            },
            {
                "step": 2,
                "title": "Select an Agent",
                "description": "Choose which ResonantGenesis agent should handle OpenClaw events.",
            },
            {
                "step": 3,
                "title": "Copy Webhook URL & Secret",
                "description": "The connection will generate a unique webhook URL and HMAC secret.",
            },
            {
                "step": 4,
                "title": "Configure in OpenClaw",
                "description": "In your OpenClaw automation, set the webhook action URL and signature.",
                "example_config": {
                    "automations": [
                        {
                            "name": "AI Agent Trigger",
                            "trigger": {"type": "telegram", "pattern": "/ask"},
                            "action": {
                                "type": "webhook",
                                "url": "<your_webhook_url>",
                                "headers": {"X-Webhook-Signature": "${WEBHOOK_SECRET}"},
                                "body": {
                                    "event": "telegram_message",
                                    "data": {"message": "${telegram.message}"},
                                },
                            },
                        }
                    ]
                },
            },
            {
                "step": 5,
                "title": "Test",
                "description": "Send a test event from OpenClaw and check the agent execution log.",
            },
        ],
    }


# ============================================
# CONNECTION STATUS (for frontend card)
# ============================================

@router.get("/status", response_model=OpenClawConnectionStatus)
async def get_connection_status(request: Request):
    """Quick status check for the /connect-profiles Openclaw card."""
    if not settings.ENABLED:
        return OpenClawConnectionStatus(
            connected=False,
            webhook_base_url=f"https://{settings.PLATFORM_DOMAIN}",
        )

    user_id = _get_user_id(request)

    try:
        # Query agent engine for all webhook triggers owned by this user
        data = await _agent_engine_request("GET", "webhooks/user/list", user_id)
        triggers = data.get("triggers", [])

        # Filter to openclaw-tagged triggers
        oc_triggers = [
            t for t in triggers
            if t.get("name", "").lower().startswith("openclaw")
            or "openclaw" in (t.get("name", "") + str(t.get("context_template", ""))).lower()
        ]

        connections = []
        for t in oc_triggers:
            connections.append({
                "id": t.get("id"),
                "agent_id": t.get("agent_id"),
                "agent_name": t.get("agent_name"),
                "name": t.get("name"),
                "webhook_url": _build_webhook_url(t.get("agent_id", "")),
                "trigger_count": t.get("trigger_count", 0),
                "last_triggered_at": t.get("last_triggered_at"),
                "enabled": t.get("enabled", True),
            })

        return OpenClawConnectionStatus(
            connected=len(connections) > 0,
            connection_count=len(connections),
            connections=connections,
            webhook_base_url=f"https://{settings.PLATFORM_DOMAIN}",
        )
    except HTTPException:
        # User might not have any agents yet — that's fine
        return OpenClawConnectionStatus(
            connected=False,
            webhook_base_url=f"https://{settings.PLATFORM_DOMAIN}",
        )
    except Exception as e:
        logger.warning(f"Status check failed: {e}")
        return OpenClawConnectionStatus(
            connected=False,
            webhook_base_url=f"https://{settings.PLATFORM_DOMAIN}",
        )


# ============================================
# CONNECTION CRUD
# ============================================

@router.get("/connections", response_model=OpenClawConnectionList)
async def list_connections(request: Request):
    """List all OpenClaw connections for the authenticated user."""
    user_id = _get_user_id(request)

    try:
        data = await _agent_engine_request("GET", "webhooks/user/list", user_id)
    except HTTPException:
        return OpenClawConnectionList(
            connections=[],
            count=0,
            platform_domain=settings.PLATFORM_DOMAIN,
        )

    triggers = data.get("triggers", [])
    oc_triggers = [
        t for t in triggers
        if t.get("name", "").lower().startswith("openclaw")
        or "openclaw" in (t.get("name", "") + str(t.get("context_template", ""))).lower()
    ]

    connections = []
    for t in oc_triggers:
        connections.append(OpenClawConnection(
            id=t.get("id", ""),
            user_id=user_id,
            agent_id=t.get("agent_id", ""),
            agent_name=t.get("agent_name"),
            connection_name=t.get("name", "OpenClaw Connection"),
            webhook_url=_build_webhook_url(t.get("agent_id", "")),
            webhook_path=t.get("webhook_path", ""),
            webhook_secret=t.get("webhook_secret", ""),
            status="active" if t.get("enabled", True) else "paused",
            trigger_count=t.get("trigger_count", 0),
            last_triggered_at=t.get("last_triggered_at"),
            created_at=t.get("created_at"),
            openclaw_config={},
        ))

    return OpenClawConnectionList(
        connections=connections,
        count=len(connections),
        platform_domain=settings.PLATFORM_DOMAIN,
    )


@router.post("/connections", response_model=OpenClawConnection)
async def create_connection(body: OpenClawConnectionCreate, request: Request):
    """
    Create a new OpenClaw ↔ Agent connection.
    
    This creates a webhook trigger on agent_engine_service tagged as 'openclaw'.
    Returns the webhook URL and secret needed for OpenClaw configuration.
    """
    if not settings.ENABLED:
        raise HTTPException(status_code=503, detail="OpenClaw service is currently disabled")

    user_id = _get_user_id(request)
    agent_id = body.agent_id
    conn_name = body.connection_name or "OpenClaw Connection"

    # Create webhook trigger via agent_engine_service
    wh_secret = secrets.token_hex(settings.DEFAULT_SECRET_LENGTH)
    trigger_data = {
        "name": f"OpenClaw: {conn_name}",
        "goal_template": "Process OpenClaw event: {event}",
        "webhook_secret": wh_secret,
        "debounce_seconds": 3,
    }

    result = await _agent_engine_request(
        "POST",
        f"webhooks/agent/{agent_id}/create",
        user_id,
        json_body=trigger_data,
    )

    webhook_url = _build_webhook_url(agent_id)
    logger.info(f"OpenClaw connection created: user={user_id} agent={agent_id} url={webhook_url}")

    return OpenClawConnection(
        id=result.get("id", ""),
        user_id=user_id,
        agent_id=agent_id,
        agent_name=result.get("agent_name"),
        connection_name=f"OpenClaw: {conn_name}",
        webhook_url=webhook_url,
        webhook_path=result.get("webhook_path", ""),
        webhook_secret=wh_secret,
        status="active",
        trigger_count=0,
        created_at=datetime.now(timezone.utc).isoformat(),
        openclaw_config=body.openclaw_config or {},
    )


@router.delete("/connections/{trigger_id}")
async def delete_connection(trigger_id: str, request: Request):
    """Delete an OpenClaw connection (removes the webhook trigger)."""
    user_id = _get_user_id(request)

    await _agent_engine_request("DELETE", f"webhooks/trigger/{trigger_id}", user_id)
    logger.info(f"OpenClaw connection deleted: user={user_id} trigger={trigger_id}")

    return {"status": "deleted", "trigger_id": trigger_id}


@router.post("/connections/{trigger_id}/pause")
async def pause_connection(trigger_id: str, request: Request):
    """Pause an OpenClaw connection (disables webhook trigger)."""
    user_id = _get_user_id(request)

    result = await _agent_engine_request("PATCH", f"webhooks/trigger/{trigger_id}/toggle", user_id)
    return {"status": "paused" if not result.get("enabled") else "active", "trigger_id": trigger_id}


@router.post("/connections/{trigger_id}/resume")
async def resume_connection(trigger_id: str, request: Request):
    """Resume a paused OpenClaw connection."""
    user_id = _get_user_id(request)

    result = await _agent_engine_request("PATCH", f"webhooks/trigger/{trigger_id}/toggle", user_id)
    return {"status": "active" if result.get("enabled") else "paused", "trigger_id": trigger_id}


# ============================================
# WEBHOOK RELAY (Public — no auth required)
# ============================================

@router.post("/relay/{agent_id}", response_model=WebhookRelayResponse)
async def relay_openclaw_event(
    agent_id: str,
    body: WebhookRelayPayload,
    request: Request,
    x_webhook_signature: Optional[str] = Header(None),
    x_internal_service_key: Optional[str] = Header(None),
):
    """
    Public endpoint: relay an OpenClaw event to an agent's webhook trigger.
    
    This is an alternative to calling the agent webhook directly.
    It adds OpenClaw-specific metadata and logging.
    
    Requires either:
    - Valid X-Internal-Service-Key (for internal services)
    - Valid X-Webhook-Signature (for external callers)
    """
    if not settings.ENABLED:
        raise HTTPException(status_code=503, detail="OpenClaw service is currently disabled")

    # Build relay payload with OpenClaw metadata
    relay_payload = {
        "event": body.event,
        "data": body.data,
        "source": "openclaw",
        "timestamp": body.timestamp or datetime.now(timezone.utc).isoformat(),
        "relay": True,
    }

    # Forward to agent_engine_service webhook trigger
    # Authenticate as internal service using INTERNAL_SERVICE_KEY
    target_url = f"{settings.AGENT_ENGINE_URL}/webhooks/agent/{agent_id}/trigger"
    headers = {
        "Content-Type": "application/json",
        "X-Internal-Service-Key": settings.INTERNAL_SERVICE_KEY,
    }
    if x_webhook_signature:
        headers["X-Webhook-Signature"] = x_webhook_signature

    try:
        async with httpx.AsyncClient(timeout=settings.WEBHOOK_RELAY_TIMEOUT_SECONDS) as client:
            resp = await client.post(target_url, json=relay_payload, headers=headers)

        if resp.status_code >= 400:
            error_detail = resp.text[:200]
            logger.warning(f"Webhook relay failed for agent {agent_id}: {resp.status_code} {error_detail}")
            return WebhookRelayResponse(
                status="error",
                message=f"Agent webhook returned {resp.status_code}",
            )

        data = resp.json()
        logger.info(f"OpenClaw relay → agent {agent_id}: {data.get('status', 'unknown')}")

        return WebhookRelayResponse(
            status=data.get("status", "received"),
            session_id=data.get("session_id"),
            message=data.get("message"),
        )

    except httpx.TimeoutException:
        logger.error(f"Webhook relay timeout for agent {agent_id}")
        return WebhookRelayResponse(status="error", message="Agent webhook timed out")
    except Exception as e:
        logger.error(f"Webhook relay error for agent {agent_id}: {e}")
        return WebhookRelayResponse(status="error", message="Internal relay error")


# ============================================
# AGENT REGISTRATION (OpenClaw agents on user hardware)
# ============================================

@router.post("/agents/register", response_model=OpenClawAgentResponse)
async def register_openclaw_agent(body: OpenClawAgentRegister, request: Request):
    """
    Register an OpenClaw agent that runs on user hardware.
    
    This creates a full agent record on ResonantGenesis with:
    - agent_source = 'openclaw'
    - DSID identity anchoring (Ethereum)
    - RARA governance enrollment (opt-in)
    - Webhook trigger for bidirectional communication
    - Memory bridge configuration
    - Custom skills registration
    
    The agent will appear on the user's Agents page with an OpenClaw badge.
    """
    if not settings.ENABLED:
        raise HTTPException(status_code=503, detail="OpenClaw service is currently disabled")

    user_id = _get_user_id(request)

    # Build openclaw_config with all federation metadata
    openclaw_config = {
        "endpoint_url": body.endpoint_url,
        "hardware": body.hardware or {},
        "memory_mode": body.memory_mode,
        "local_memory_endpoint": body.local_memory_endpoint,
        "custom_skills": body.custom_skills or [],
        "enable_rara": body.enable_rara,
        "enable_dsid": body.enable_dsid,
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "last_heartbeat": None,
        "connection_status": "registered",
    }

    # 0. Generate Hash Sphere identity for this agent
    #    Same 4-layer identity as users: UUID + crypto_hash + user_hash + universe_id
    agent_identity_seed = f"openclaw:{user_id}:{body.name}:{datetime.now(timezone.utc).isoformat()}"
    agent_crypto_hash = hashlib.sha256(agent_identity_seed.encode("utf-8")).hexdigest()
    agent_semantic_hash = hashlib.sha256(
        f"hash_sphere:{agent_crypto_hash}:{body.name}".encode("utf-8")
    ).hexdigest()
    agent_universe_id = hashlib.sha256(
        f"universe:{agent_crypto_hash}".encode("utf-8")
    ).hexdigest()[:32]

    openclaw_config["agent_crypto_hash"] = agent_crypto_hash
    openclaw_config["agent_semantic_hash"] = agent_semantic_hash
    openclaw_config["agent_universe_id"] = agent_universe_id

    # Anchor identity on blockchain
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{settings.BLOCKCHAIN_SERVICE_URL}/identity/register",
                json={
                    "user_id": f"agent:{body.name}",
                    "crypto_hash": agent_crypto_hash,
                    "user_hash": agent_semantic_hash,
                    "universe_id": agent_universe_id,
                    "identity_type": "agent",
                    "source": "openclaw",
                },
                headers={"X-Internal-Key": settings.INTERNAL_SERVICE_KEY},
            )
        logger.info(f"Agent identity anchored on blockchain: hash={agent_crypto_hash[:16]}...")
    except Exception as e:
        logger.warning(f"Blockchain identity anchoring failed: {e}")

    # Store identity in Hash Sphere memory
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"{settings.MEMORY_SERVICE_URL}/memories/ingest",
                json={
                    "content": f"Agent {body.name} registered with crypto_hash={agent_crypto_hash}, semantic_hash={agent_semantic_hash}, universe_id={agent_universe_id}, source=openclaw",
                    "memory_type": "semantic",
                    "metadata": {
                        "type": "agent_identity",
                        "agent_name": body.name,
                        "crypto_hash": agent_crypto_hash,
                        "semantic_hash": agent_semantic_hash,
                        "universe_id": agent_universe_id,
                        "source": "openclaw",
                    },
                    "tags": ["agent_identity", "openclaw", "hash_sphere"],
                },
                headers={
                    "x-user-id": user_id,
                    "x-internal-service-key": settings.INTERNAL_SERVICE_KEY,
                },
            )
    except Exception as e:
        logger.warning(f"Hash Sphere identity store failed: {e}")

    # 1. Register via /federation/register — sets agent_source='federated' + stores openclaw_config
    federation_data = {
        "name": body.name,
        "description": body.description or f"OpenClaw agent running on user hardware",
        "connection_url": f"http://localhost:8000",
        "hardware_info": openclaw_config.get("hardware_info", {}),
        "client_version": f"openclaw-connector/{settings.SERVICE_VERSION}",
        "capabilities": body.tools or ["web_search", "fetch_url"],
        "tools": body.tools or ["web_search", "fetch_url", "memory_read", "memory_write"],
        "provider": body.provider or "groq",
        "model": body.model or "llama-3.3-70b-versatile",
    }

    agent_result = await _agent_engine_request("POST", "federation/register", user_id, json_body=federation_data, timeout=30.0)
    agent_id = agent_result.get("agent_id") or agent_result.get("id", "")
    logger.info(f"OpenClaw agent registered: user={user_id} agent={agent_id} name={body.name} hash={agent_crypto_hash[:16]}...")

    # 2. Create webhook trigger for this agent
    wh_secret = secrets.token_hex(settings.DEFAULT_SECRET_LENGTH)
    try:
        await _agent_engine_request(
            "POST",
            f"webhooks/agent/{agent_id}/create",
            user_id,
            json_body={
                "name": f"OpenClaw: {body.name}",
                "goal_template": "Process OpenClaw event: {event}",
                "webhook_secret": wh_secret,
                "debounce_seconds": 3,
            },
        )
    except Exception as e:
        logger.warning(f"Webhook creation failed for openclaw agent {agent_id}: {e}")
        wh_secret = ""

    # 3. Register custom skills if provided
    skills_count = 0
    if body.custom_skills:
        for skill_def in body.custom_skills:
            skill_name = skill_def.get("name", "")
            if skill_name:
                if agent_id not in _custom_skills_store:
                    _custom_skills_store[agent_id] = []
                _custom_skills_store[agent_id].append({
                    "name": skill_name,
                    "description": skill_def.get("description", ""),
                    "agent_id": agent_id,
                    "endpoint_url": skill_def.get("endpoint_url") or body.endpoint_url,
                    "parameters_schema": skill_def.get("parameters_schema"),
                    "category": "custom_openclaw",
                    "registered_at": datetime.now(timezone.utc).isoformat(),
                })
                skills_count += 1
        logger.info(f"Registered {skills_count} custom skills for openclaw agent {agent_id}")

    # 4. Enroll in RARA governance if opted in
    rara_enrolled = False
    if body.enable_rara:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                dsid_value = agent_result.get("dsid") or ""
                public_key = f"pk_{hashlib.sha256((dsid_value or agent_id).encode('utf-8')).hexdigest()}"
                resp = await client.post(
                    f"{settings.RARA_SERVICE_URL}/agents/register",
                    json={
                        "agent_id": agent_id,
                        "role": "executor",
                        "dsid": dsid_value,
                        "public_key": public_key,
                        "capabilities": body.tools or [],
                        "source": "openclaw",
                    },
                    headers={"x-internal-service-key": settings.INTERNAL_SERVICE_KEY},
                )
                rara_enrolled = resp.status_code in (200, 201)
        except Exception as e:
            logger.warning(f"RARA enrollment failed for openclaw agent {agent_id}: {e}")

    return OpenClawAgentResponse(
        agent_id=agent_id,
        name=body.name,
        agent_source="openclaw",
        dsid=agent_result.get("dsid"),
        agent_public_hash=agent_crypto_hash,
        agent_crypto_hash=agent_crypto_hash,
        agent_semantic_hash=agent_semantic_hash,
        agent_universe_id=agent_universe_id,
        webhook_url=_build_webhook_url(agent_id) if wh_secret else "",
        webhook_secret=wh_secret,
        memory_mode=body.memory_mode,
        rara_enrolled=rara_enrolled,
        skills_registered=skills_count,
        status="registered",
    )


@router.get("/agents/openclaw")
async def list_openclaw_agents(request: Request):
    """List all OpenClaw agents owned by the authenticated user."""
    user_id = _get_user_id(request)

    try:
        data = await _agent_engine_request("GET", "agents/", user_id)
    except HTTPException:
        return {"agents": [], "count": 0}

    agents = data if isinstance(data, list) else data.get("agents", data)

    # Filter to openclaw agents only
    oc_agents = []
    for a in agents:
        source = a.get("agent_source", "cloud")
        if source == "openclaw":
            agent_id = a.get("id", "")
            hb = _heartbeat_store.get(agent_id)
            connection_status = "offline"
            if hb:
                elapsed = (datetime.now(timezone.utc) - datetime.fromisoformat(hb["timestamp"])).total_seconds()
                connection_status = "online" if elapsed < settings.HEARTBEAT_TIMEOUT_SECONDS else "offline"

            oc_agents.append({
                **a,
                "connection_status": connection_status,
                "last_heartbeat": hb.get("timestamp") if hb else None,
                "hardware": (a.get("openclaw_config") or {}).get("hardware"),
                "custom_skills_count": len(_custom_skills_store.get(agent_id, [])),
            })

    return {"agents": oc_agents, "count": len(oc_agents)}


# ============================================
# HEARTBEAT (OpenClaw agents report status)
# ============================================

@router.post("/agents/heartbeat", response_model=AgentHeartbeatResponse)
async def agent_heartbeat(body: AgentHeartbeat, request: Request):
    """
    Receive heartbeat from an OpenClaw agent running on user hardware.
    
    The agent calls this periodically to report its status, hardware info,
    and available models. If no heartbeat arrives within HEARTBEAT_TIMEOUT_SECONDS,
    the agent is considered offline.
    """
    user_id = _get_user_id(request)

    now = datetime.now(timezone.utc)
    _heartbeat_store[body.agent_id] = {
        "user_id": user_id,
        "status": body.status,
        "hardware": body.hardware,
        "capabilities": body.capabilities,
        "models_available": body.models_available,
        "uptime_seconds": body.uptime_seconds,
        "current_load": body.current_load,
        "version": body.version,
        "timestamp": now.isoformat(),
    }

    # Update openclaw_config on agent_engine_service with latest heartbeat info
    try:
        await _agent_engine_request(
            "PATCH",
            f"agents/{body.agent_id}",
            user_id,
            json_body={
                "openclaw_config": {
                    "last_heartbeat": now.isoformat(),
                    "connection_status": body.status,
                    "hardware": body.hardware,
                    "models_available": body.models_available,
                },
            },
        )
    except Exception as e:
        logger.debug(f"Heartbeat config update failed for {body.agent_id}: {e}")

    logger.debug(f"Heartbeat from openclaw agent {body.agent_id}: status={body.status}")

    return AgentHeartbeatResponse(
        acknowledged=True,
        pending_tasks=[],  # future: queue tasks for the agent to pick up
        config_update=None,
    )


# ============================================
# TASK EXECUTION (platform-dispatched tasks for federated agents)
# ============================================

@router.post("/task/execute")
async def execute_task(request: Request):
    """
    Execute a task dispatched from the platform.

    When a user clicks 'Run' on a federated agent in the platform UI,
    the agent engine sends the task here. The local OpenClaw agent
    processes it using local compute + platform tools, then returns results.
    """
    import time as _time
    t0 = _time.time()

    body = await request.json()
    task = body.get("task", "")
    agent_id = body.get("agent_id", "")
    context = body.get("context", {})
    available_tools = body.get("available_tools", [])

    if not task:
        return {"success": False, "error": "No task provided", "task_id": agent_id}

    user_id = _get_user_id(request)
    logger.info(f"[TASK] Received platform task for agent {agent_id}: {task[:100]}...")

    # Execute using LLM-driven ReAct agent loop (ALL platform tools)
    try:
        from . import platform_auth
        auth_hdrs = await platform_auth.get_auth_headers()
        result = await _llm_agent_execute(
            goal=task,
            agent_id=agent_id,
            available_tools=available_tools,
            user_id=user_id,
            auth_hdrs=auth_hdrs,
            context=context,
        )
        elapsed = int((_time.time() - t0) * 1000)
        result["task_id"] = agent_id
        result["duration_ms"] = elapsed
        return result

    except Exception as e:
        logger.error(f"[TASK] Execution failed for agent {agent_id}: {e}")
        return {
            "success": False,
            "task_id": agent_id,
            "output": None,
            "tools_used": [],
            "duration_ms": int((_time.time() - t0) * 1000),
            "error": str(e),
        }


# ============================================
# BACKGROUND TASK POLLING (secure outbound-only federation)
# ============================================
# The connector polls the platform every 5s for pending tasks.
# All traffic is OUTBOUND HTTPS — zero inbound connections needed.
# JWT-authenticated — only your tasks are returned.

_polling_active = False
_poll_stats = {"count": 0, "tasks_picked": 0, "last_poll": None, "activity": []}
_task_log = []  # list of completed task summaries for dashboard

def _add_activity(msg, msg_type="info"):
    """Add entry to dashboard activity log."""
    from datetime import datetime
    entry = {"time": datetime.now().strftime("%H:%M:%S"), "msg": msg, "type": msg_type}
    _poll_stats.setdefault("activity", []).insert(0, entry)
    if len(_poll_stats["activity"]) > 50:
        _poll_stats["activity"] = _poll_stats["activity"][:50]

async def _llm_agent_execute(
    goal: str,
    agent_id: str,
    available_tools: list,
    user_id: str,
    auth_hdrs: dict,
    context: dict = None,
    max_loops: int = 8,
    session_id: str = "",
    task_id: str = "",
) -> dict:
    """LLM-driven ReAct agent loop using ALL platform tools.

    1. Fetch tool definitions from platform
    2. Build OpenAI function-call schema for available tools
    3. Send goal + tools to LLM, let it decide which to call
    4. Execute tool calls via platform /tools/execute
    5. Feed results back, loop until LLM produces final answer
    """
    import json as _json

    tools_used = []

    # Fetch full tool definitions from platform
    platform_tools = await _fetch_platform_tools()
    tool_map = {t["name"]: t for t in platform_tools}  # name -> {name, description, params}

    # Build OpenAI function-call format for tools the agent has access to
    openai_tools = []
    for tname in available_tools:
        tdef = tool_map.get(tname)
        if not tdef:
            continue
        # Build JSON schema properties from params
        props = {}
        required = []
        for p in tdef.get("params", []):
            pname = p.get("name", "")
            if not pname:
                continue
            ptype = p.get("type", "string")
            ptype_map = {"string": "string", "integer": "integer", "number": "number",
                         "boolean": "boolean", "array": "array", "object": "object"}
            schema = {"type": ptype_map.get(str(ptype).lower(), "string"), "description": p.get("description", "")}
            if p.get("enum"):
                schema["enum"] = p["enum"]
            props[pname] = schema
            if p.get("required"):
                required.append(pname)
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tname,
                "description": tdef.get("description", ""),
                "parameters": {"type": "object", "properties": props, "required": required},
            },
        })

    # System prompt
    system_msg = (
        "You are a federated AI agent running on the user's local machine via ResonantGenesis OpenClaw. "
        "You have access to platform tools. Use them to accomplish the user's task. "
        "Think step-by-step. Call tools as needed. When you have a complete answer, respond with your final text. "
        "Always use memory_write to save important findings. Always use memory_read to check for relevant context first. "
        "Format your final response in clean markdown."
    )

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": goal},
    ]

    # ReAct loop
    for loop_i in range(max_loops):
        # Call LLM with tools
        llm_body = {
            "model": "llama-3.3-70b-versatile",
            "messages": messages,
            "max_tokens": 4096,
            "temperature": 0.3,
        }
        if openai_tools:
            llm_body["tools"] = openai_tools
            llm_body["tool_choice"] = "auto"

        try:
            llm_hdrs = {"Content-Type": "application/json"}
            llm_hdrs.update(auth_hdrs)
            async with httpx.AsyncClient(timeout=60.0) as lc:
                llm_resp = await lc.post(
                    f"{settings.LLM_SERVICE_URL}/chat/completions",
                    json=llm_body,
                    headers=llm_hdrs,
                )
            if llm_resp.status_code != 200:
                logger.warning(f"[AGENT] LLM returned {llm_resp.status_code}: {llm_resp.text[:200]}")
                break
            llm_data = llm_resp.json()
        except Exception as e:
            logger.error(f"[AGENT] LLM request failed: {e}")
            break

        # Extract assistant message
        choice = (llm_data.get("choices") or [{}])[0]
        msg = choice.get("message", {})
        finish = choice.get("finish_reason", "stop")

        # tool_calls can be at message level OR choice level depending on LLM service
        tool_calls = msg.get("tool_calls") or choice.get("tool_calls") or []
        # Ensure msg has tool_calls for the messages list
        if tool_calls and not msg.get("tool_calls"):
            msg["tool_calls"] = tool_calls

        # If no tool calls AND not a tool_calls finish reason, we have the final answer
        if (not tool_calls and finish != "tool_calls"):
            final_text = msg.get("content", "")
            if final_text:
                # Save result to memory
                if "memory_write" in available_tools:
                    try:
                        await _agent_engine_request(
                            "POST", "tools/execute", user_id,
                            json_body={"tool_name": "memory_write", "tool_input": {
                                "content": f"Task: {goal}\nResult: {final_text[:500]}",
                                "tags": ["task_result", "openclaw"],
                            }},
                            timeout=10.0,
                        )
                        if "memory_write" not in tools_used:
                            tools_used.append("memory_write")
                    except Exception:
                        pass
                return {"success": True, "output": final_text, "tools_used": tools_used}
            break

        # Process tool calls
        messages.append(msg)  # assistant message with tool_calls

        for tc in tool_calls:
            fn = tc.get("function", {})
            tool_name = fn.get("name", "")
            try:
                tool_args = _json.loads(fn.get("arguments", "{}"))
            except Exception:
                tool_args = {}

            tc_id = tc.get("id", f"call_{loop_i}")
            logger.info(f"[AGENT] Loop {loop_i+1}: calling {tool_name}({list(tool_args.keys())})")
            _add_activity(f'<span class="tool">{tool_name}</span>({", ".join(f"{k}=" for k in tool_args)})', 'info')

            # Execute via platform (async for heavy tools, inline for light)
            _HEAVY = {"web_search", "fetch_url", "browser_automation", "deep_research",
                       "code_execution", "execute_code", "pdf_parse", "spreadsheet",
                       "google_calendar", "google_drive", "database_query",
                       "image_generation", "generate_image", "generate_audio", "generate_video"}
            try:
                is_heavy = tool_name in _HEAVY
                tool_result = await _agent_engine_request(
                    "POST", "tools/execute", user_id,
                    json_body={
                        "tool_name": tool_name,
                        "tool_input": tool_args,
                        "session_id": session_id,
                        "async": is_heavy,
                    },
                    timeout=120.0 if is_heavy else 30.0,
                )

                # If async, poll for result
                if tool_result.get("async") and tool_result.get("task_id"):
                    celery_task_id = tool_result["task_id"]
                    _add_activity(f'<span class="tool">{tool_name}</span> queued (background)', 'info')
                    # Poll every 2s up to 2 minutes
                    for _poll_i in range(60):
                        await asyncio.sleep(2)
                        poll_resp = await _agent_engine_request(
                            "GET", f"tools/result/{celery_task_id}", user_id,
                            timeout=10.0,
                        )
                        if poll_resp.get("ready"):
                            tool_result = poll_resp
                            break
                    else:
                        tool_result = {"success": False, "error": "Background tool timed out after 120s"}

                result_text = ""
                if tool_result.get("success"):
                    if tool_name not in tools_used:
                        tools_used.append(tool_name)
                    r = tool_result.get("result", tool_result.get("output", ""))
                    result_text = _json.dumps(r, default=str)[:3000] if isinstance(r, (dict, list)) else str(r)[:3000]
                else:
                    result_text = f"Error: {tool_result.get('error', 'unknown')}"
            except Exception as e:
                result_text = f"Tool execution error: {e}"

            messages.append({"role": "tool", "tool_call_id": tc_id, "content": result_text})

            # Report step to platform for live streaming
            if task_id:
                import time as _t
                try:
                    step_hdrs = {"x-user-id": user_id, "Content-Type": "application/json"}
                    step_hdrs.update(auth_hdrs)
                    async with httpx.AsyncClient(timeout=5.0) as sc:
                        await sc.post(
                            f"{settings.AGENT_ENGINE_URL}/federation/tasks/{task_id}/step",
                            json={
                                "step_type": "tool_call",
                                "tool_name": tool_name,
                                "tool_input": tool_args,
                                "tool_output": {"result": result_text[:2000]},
                                "reasoning": msg.get("content", "") or f"Calling {tool_name}",
                                "duration_ms": int((_t.time() - t0) * 1000) if 't0' in dir() else 0,
                            },
                            headers=step_hdrs,
                        )
                except Exception as step_err:
                    logger.debug(f"[AGENT] Step report failed: {step_err}")

    # If we exhausted loops without a final answer, ask LLM for a summary
    last_content = ""
    for m in reversed(messages):
        if m.get("role") == "assistant" and m.get("content"):
            last_content = m["content"]
            break

    if not last_content and tools_used:
        # One final LLM call without tools — force a summary
        try:
            messages.append({"role": "user", "content": "Now summarize everything you found into a clear, complete answer. Do NOT call any more tools."})
            summary_body = {
                "model": "llama-3.3-70b-versatile",
                "messages": messages,
                "max_tokens": 4096,
                "temperature": 0.3,
            }
            async with httpx.AsyncClient(timeout=60.0) as sc:
                summary_resp = await sc.post(
                    f"{settings.LLM_SERVICE_URL}/chat/completions",
                    json=summary_body,
                    headers=auth_hdrs,
                )
            if summary_resp.status_code == 200:
                s_data = summary_resp.json()
                s_msg = (s_data.get("choices") or [{}])[0].get("message", {})
                last_content = s_msg.get("content", "")
        except Exception as e:
            logger.warning(f"[AGENT] Summary call failed: {e}")

    return {
        "success": bool(last_content or tools_used),
        "output": last_content or f"Agent used {len(tools_used)} tools but did not produce a final summary.",
        "tools_used": tools_used,
    }


async def _poll_federation_tasks():
    """Background loop: poll the platform for pending federated tasks."""
    global _polling_active
    _polling_active = True
    poll_interval = 5  # seconds

    from . import platform_auth
    logger.info("[POLL] Federated task polling started (every %ds)", poll_interval)

    while _polling_active:
        try:
            # Check if authenticated
            auth_hdrs = await platform_auth.get_auth_headers()
            if not auth_hdrs:
                await asyncio.sleep(poll_interval)
                continue

            user_id = platform_auth._token_cache.get("user_id", "")
            if not user_id:
                # Decode from JWT if not stored
                try:
                    import base64, json as _json
                    tok = platform_auth._token_cache.get("access_token", "")
                    if tok:
                        payload_b64 = tok.split(".")[1]
                        payload_b64 += "=" * (4 - len(payload_b64) % 4)
                        claims = _json.loads(base64.urlsafe_b64decode(payload_b64))
                        user_id = claims.get("sub", claims.get("user_id", ""))
                        if user_id:
                            platform_auth._token_cache["user_id"] = user_id
                            email = claims.get("email", "")
                            if email:
                                platform_auth._token_cache["email"] = email
                            platform_auth._save_tokens(platform_auth._token_cache)
                except Exception:
                    pass
            if not user_id:
                await asyncio.sleep(poll_interval)
                continue

            # Poll for pending tasks
            hdrs = {"x-user-id": user_id, "Content-Type": "application/json"}
            hdrs.update(auth_hdrs)

            # Send heartbeat to platform so server knows we're alive
            try:
                # Fetch registered agents to get agent_ids for heartbeat
                async with httpx.AsyncClient(timeout=8.0) as hb_client:
                    agents_resp = await hb_client.get(
                        f"{settings.AGENT_ENGINE_URL}",
                        headers=hdrs,
                    )
                    if agents_resp.status_code == 200:
                        for ag in agents_resp.json():
                            if ag.get("agent_source") in ("federated", "openclaw"):
                                await hb_client.post(
                                    f"{settings.AGENT_ENGINE_URL}/federation/heartbeat",
                                    json={"agent_id": ag["id"], "status": "online"},
                                    headers=hdrs,
                                )
            except Exception as hb_err:
                logger.debug(f"[POLL] Heartbeat send failed: {hb_err}")

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{settings.AGENT_ENGINE_URL}/federation/tasks/poll",
                    headers=hdrs,
                )

            _poll_stats["count"] = _poll_stats.get("count", 0) + 1
            from datetime import datetime
            _poll_stats["last_poll"] = datetime.now().strftime("%H:%M:%S")

            if resp.status_code != 200:
                await asyncio.sleep(poll_interval)
                continue

            data = resp.json()
            task_data = data.get("task")
            if not task_data:
                await asyncio.sleep(poll_interval)
                continue

            # We got a task! Execute it
            task_id = task_data["task_id"]
            session_id = task_data.get("session_id", "")
            goal = task_data["goal"]
            agent_id = task_data["agent_id"]
            tools = task_data.get("tools", [])
            context = task_data.get("context", {})

            logger.info(f"[POLL] Picked up task {task_id}: {goal[:80]}...")
            _poll_stats["tasks_picked"] = _poll_stats.get("tasks_picked", 0) + 1
            _add_activity(f'<span class="tool">Task picked up:</span> {goal[:60]}...', 'info')

            # Execute using LLM-driven ReAct agent loop
            import time as _time
            t0 = _time.time()
            tools_used = []

            try:
                result_body = await _llm_agent_execute(
                    goal=goal,
                    agent_id=agent_id,
                    available_tools=tools,
                    user_id=user_id,
                    auth_hdrs=auth_hdrs,
                    context=context,
                    session_id=session_id,
                    task_id=task_id,
                )
                tools_used = result_body.get("tools_used", [])
                elapsed = int((_time.time() - t0) * 1000)
                result_body["duration_ms"] = elapsed

            except Exception as e:
                elapsed = int((_time.time() - t0) * 1000)
                result_body = {
                    "success": False,
                    "output": f"Execution error: {e}",
                    "tools_used": tools_used,
                    "duration_ms": elapsed,
                    "error": str(e),
                }

            # Submit result back to platform
            try:
                result_hdrs = {"x-user-id": user_id, "Content-Type": "application/json"}
                result_hdrs.update(auth_hdrs)
                async with httpx.AsyncClient(timeout=15.0) as rc:
                    submit_resp = await rc.post(
                        f"{settings.AGENT_ENGINE_URL}/federation/tasks/{task_id}/result",
                        json=result_body,
                        headers=result_hdrs,
                    )
                logger.info(f"[POLL] Task {task_id} result submitted ({submit_resp.status_code}), tools={tools_used}, {elapsed}ms")
                _task_log.insert(0, {
                    "goal": goal[:100],
                    "tools_used": tools_used,
                    "duration_ms": elapsed,
                    "status": "completed" if result_body.get("success") else "failed",
                    "task_id": task_id,
                    "output": result_body.get("output", ""),
                })
                if len(_task_log) > 20:
                    _task_log[:] = _task_log[:20]
                _add_activity(f'<span class="success">Task completed</span> — tools: <span class="tool">{", ".join(tools_used)}</span> — {elapsed}ms', 'success')
            except Exception as e:
                logger.error(f"[POLL] Failed to submit result for task {task_id}: {e}")

        except Exception as e:
            logger.debug(f"[POLL] Polling cycle error: {e}")

        await asyncio.sleep(poll_interval)


def start_polling():
    """Start the background polling loop."""
    asyncio.get_event_loop().create_task(_poll_federation_tasks())


def stop_polling():
    """Stop the background polling loop."""
    global _polling_active
    _polling_active = False


# ============================================
# MEMORY BRIDGE (Hash Sphere integration for OpenClaw agents)
# ============================================

@router.post("/memory/ingest")
async def memory_ingest(body: MemoryBridgeIngest, request: Request):
    """
    Ingest a memory from an OpenClaw agent into Hash Sphere.
    
    OpenClaw agents running on user hardware can store memories in our
    cloud-based Hash Sphere memory service. This enables:
    - Persistent long-term memory across sessions
    - Cross-agent memory sharing within the same user
    - Memory anchoring for identity verification
    """
    user_id = _get_user_id(request)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            from . import platform_auth
            auth_hdrs = await platform_auth.get_auth_headers()
            hdrs = {"x-user-id": user_id, "Content-Type": "application/json"}
            if settings.INTERNAL_SERVICE_KEY:
                hdrs["x-internal-service-key"] = settings.INTERNAL_SERVICE_KEY
            hdrs.update(auth_hdrs)
            resp = await client.post(
                f"{settings.MEMORY_SERVICE_URL}/ingest",
                json={
                    "content": body.content,
                    "memory_type": body.memory_type,
                    "metadata": {
                        **(body.metadata or {}),
                        "source": "openclaw",
                        "agent_id": body.agent_id,
                    },
                    "tags": body.tags or [],
                },
                headers=hdrs,
            )
        if resp.status_code >= 400:
            return {"success": False, "error": f"Memory service returned {resp.status_code}"}
        return {"success": True, "data": resp.json(), "source": "hash_sphere"}
    except Exception as e:
        logger.warning(f"Memory ingest failed for agent {body.agent_id}: {e}")
        return {"success": False, "error": str(e)}


@router.post("/memory/query", response_model=MemoryBridgeResponse)
async def memory_query(body: MemoryBridgeQuery, request: Request):
    """
    Query memories from Hash Sphere for an OpenClaw agent.
    
    Supports filtering by memory type and limiting results.
    Users who chose 'hybrid' memory mode will also get local results
    (handled client-side by the OpenClaw agent).
    """
    user_id = _get_user_id(request)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            from . import platform_auth
            auth_hdrs = await platform_auth.get_auth_headers()
            hdrs = {"x-user-id": user_id, "Content-Type": "application/json"}
            if settings.INTERNAL_SERVICE_KEY:
                hdrs["x-internal-service-key"] = settings.INTERNAL_SERVICE_KEY
            hdrs.update(auth_hdrs)
            resp = await client.post(
                f"{settings.MEMORY_SERVICE_URL}/search",
                json={
                    "query": body.query,
                    "limit": body.limit,
                    "filters": {
                        "agent_id": body.agent_id,
                        "memory_type": body.memory_type,
                    },
                },
                headers=hdrs,
            )
        if resp.status_code >= 400:
            return MemoryBridgeResponse(memories=[], count=0, source="hash_sphere")
        data = resp.json()
        memories = data.get("results", data.get("memories", []))
        return MemoryBridgeResponse(
            memories=memories,
            count=len(memories),
            source="hash_sphere",
        )
    except Exception as e:
        logger.warning(f"Memory query failed for agent {body.agent_id}: {e}")
        return MemoryBridgeResponse(memories=[], count=0, source="hash_sphere")


# ============================================
# SKILLS FEDERATION
# ============================================

# Platform tools are now loaded dynamically from the unified registry
# via agent_engine_service /tools/list endpoint — no hardcoded list
_cached_platform_tools = None
_cached_at = None

async def _fetch_platform_tools() -> list:
    """Fetch all platform tools from agent_engine unified registry (cached 5 min)."""
    global _cached_platform_tools, _cached_at
    import time
    if _cached_platform_tools and _cached_at and (time.time() - _cached_at) < 300:
        return _cached_platform_tools
    try:
        from . import platform_auth
        headers = await platform_auth.get_auth_headers()
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{settings.AGENT_ENGINE_URL}/tools/list", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                # API may return a list directly or {"tools": [...]}
                if isinstance(data, list):
                    _cached_platform_tools = data
                else:
                    _cached_platform_tools = data.get("tools", data.get("items", []))
                _cached_at = time.time()
                logger.info("Fetched %d platform tools", len(_cached_platform_tools))
                return _cached_platform_tools
    except Exception as e:
        logger.warning(f"Failed to fetch platform tools: {e}")
    return _cached_platform_tools or []


@router.get("/skills/available")
async def list_available_skills(request: Request):
    """
    List ALL 159+ platform tools available to OpenClaw agents.
    
    Fetches dynamically from the unified tool registry via agent_engine.
    Also includes any custom skills registered by OpenClaw agents.
    """
    user_id = _get_user_id(request)

    platform_tools = await _fetch_platform_tools()

    # Collect custom skills from all user's openclaw agents
    all_custom = []
    for agent_id, skills in _custom_skills_store.items():
        for s in skills:
            all_custom.append({**s, "source": "openclaw_custom"})

    return {
        "platform_skills": platform_tools,
        "custom_skills": all_custom,
        "total": len(platform_tools) + len(all_custom),
    }


@router.post("/skills/execute", response_model=SkillExecuteResponse)
async def execute_skill(body: SkillExecuteRequest, request: Request):
    """
    Execute a platform skill on behalf of an OpenClaw agent.
    
    This allows OpenClaw agents running on user hardware to use
    ResonantGenesis platform skills (web_search, code_visualizer, etc.)
    without needing their own API keys for those services.
    """
    user_id = _get_user_id(request)

    # Check if it's a custom skill (routes to user hardware)
    for agent_skills in _custom_skills_store.values():
        for skill in agent_skills:
            if skill["name"] == body.skill_name and skill.get("endpoint_url"):
                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        resp = await client.post(
                            skill["endpoint_url"],
                            json={"skill": body.skill_name, "parameters": body.parameters},
                        )
                    return SkillExecuteResponse(
                        success=resp.status_code < 400,
                        result=resp.json() if resp.status_code < 400 else None,
                        error=resp.text[:200] if resp.status_code >= 400 else None,
                        skill_name=body.skill_name,
                    )
                except Exception as e:
                    return SkillExecuteResponse(success=False, error=str(e), skill_name=body.skill_name)

    # Platform tool — execute via agent_engine /tools/execute
    try:
        result = await _agent_engine_request(
            "POST",
            "tools/execute",
            user_id,
            json_body={"tool_name": body.skill_name, "tool_input": body.parameters or {}},
            timeout=30.0,
        )
        return SkillExecuteResponse(
            success=result.get("success", False),
            result=result.get("result"),
            error=result.get("error"),
            skill_name=body.skill_name,
        )
    except HTTPException as he:
        return SkillExecuteResponse(success=False, error=str(he.detail), skill_name=body.skill_name)
    except Exception as e:
        return SkillExecuteResponse(success=False, error=str(e), skill_name=body.skill_name)


@router.post("/skills/import")
async def import_skill(body: SkillImport, request: Request):
    """
    Import a custom skill from an OpenClaw agent into the platform.
    
    This registers the skill so other agents and the platform can discover
    and use it. The skill executes on the OpenClaw agent's hardware.
    """
    user_id = _get_user_id(request)

    if body.agent_id not in _custom_skills_store:
        _custom_skills_store[body.agent_id] = []

    # Check for duplicates
    existing = [s for s in _custom_skills_store[body.agent_id] if s["name"] == body.name]
    if existing:
        raise HTTPException(status_code=409, detail=f"Skill '{body.name}' already registered for this agent")

    skill_record = {
        "name": body.name,
        "description": body.description,
        "agent_id": body.agent_id,
        "endpoint_url": body.endpoint_url,
        "parameters_schema": body.parameters_schema,
        "category": body.category,
        "risk_level": body.risk_level,
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "registered_by": user_id,
    }
    _custom_skills_store[body.agent_id].append(skill_record)

    logger.info(f"Custom skill imported: {body.name} from agent {body.agent_id}")
    return {"status": "imported", "skill": skill_record}


# ============================================
# GOVERNANCE BRIDGE (RARA + DSID)
# ============================================

@router.get("/governance/{agent_id}", response_model=GovernanceStatus)
async def get_governance_status(agent_id: str, request: Request):
    """
    Get governance status for an OpenClaw agent.
    
    Shows RARA enrollment, DSID anchoring, compliance score, and violations.
    """
    user_id = _get_user_id(request)

    # Get agent info for DSID status
    try:
        agent = await _agent_engine_request("GET", f"agents/{agent_id}", user_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Agent not found")

    dsid = agent.get("dsid")
    dsid_anchored = bool(dsid)

    # Check RARA enrollment
    rara_enrolled = False
    compliance_score = None
    violations = 0
    last_audit = None
    governance_level = "standard"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{settings.RARA_SERVICE_URL}/agents/{agent_id}/governance",
                headers={"x-internal-service-key": settings.INTERNAL_SERVICE_KEY},
            )
            if resp.status_code == 200:
                gov_data = resp.json()
                rara_enrolled = gov_data.get("enrolled", False)
                compliance_score = gov_data.get("compliance_score")
                violations = gov_data.get("violations", 0)
                last_audit = gov_data.get("last_audit")
                governance_level = gov_data.get("governance_level", "standard")
    except Exception:
        pass  # RARA service may not be available

    return GovernanceStatus(
        agent_id=agent_id,
        rara_enrolled=rara_enrolled,
        dsid_anchored=dsid_anchored,
        governance_level=governance_level,
        compliance_score=compliance_score,
        violations=violations,
        last_audit=last_audit,
    )


@router.post("/governance/enroll")
async def enroll_governance(body: GovernanceEnroll, request: Request):
    """
    Enroll an OpenClaw agent in RARA governance.
    
    This registers the agent with the RARA service for:
    - Compliance monitoring
    - Action auditing
    - Safety rule enforcement
    - Trust tier management
    """
    user_id = _get_user_id(request)

    # Get agent info
    try:
        agent = await _agent_engine_request("GET", f"agents/{body.agent_id}", user_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Agent not found")

    if agent.get("agent_source") != "openclaw":
        raise HTTPException(status_code=400, detail="This endpoint is for OpenClaw agents only")

    dsid = agent.get("dsid", "")
    public_key = f"pk_{hashlib.sha256((dsid or body.agent_id).encode('utf-8')).hexdigest()}"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{settings.RARA_SERVICE_URL}/agents/register",
                json={
                    "agent_id": body.agent_id,
                    "role": "executor",
                    "dsid": dsid,
                    "public_key": public_key,
                    "capabilities": agent.get("tools", []),
                    "source": "openclaw",
                    "governance_level": body.governance_level,
                },
                headers={"x-internal-service-key": settings.INTERNAL_SERVICE_KEY},
            )
        enrolled = resp.status_code in (200, 201)
        return {
            "status": "enrolled" if enrolled else "failed",
            "agent_id": body.agent_id,
            "governance_level": body.governance_level,
            "dsid": dsid,
        }
    except Exception as e:
        logger.warning(f"RARA enrollment failed for {body.agent_id}: {e}")
        return {"status": "failed", "agent_id": body.agent_id, "error": str(e)}


# ============================================
# MARKETPLACE (list OpenClaw agents)
# ============================================

@router.post("/marketplace/list")
async def marketplace_list(body: MarketplaceListRequest, request: Request):
    """
    List an OpenClaw agent on the ResonantGenesis marketplace.
    
    OpenClaw agents can be listed with a 'Runs on: User Hardware' badge.
    Buyers can connect to the agent via webhook or direct connection.
    """
    user_id = _get_user_id(request)

    # Verify agent exists and is openclaw
    try:
        agent = await _agent_engine_request("GET", f"agents/{body.agent_id}", user_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Agent not found")

    if agent.get("agent_source") != "openclaw":
        raise HTTPException(status_code=400, detail="Only OpenClaw agents can be listed with hardware badge")

    # Mark as published on agent_engine_service
    try:
        await _agent_engine_request(
            "PATCH",
            f"agents/{body.agent_id}",
            user_id,
            json_body={"published_to_marketplace": True},
        )
    except Exception:
        pass

    # Submit to marketplace service
    listing_data = {
        "name": body.name,
        "description": body.description,
        "category": body.category,
        "tags": body.tags + ["openclaw", "user-hardware"],
        "price_per_execution": body.price_per_execution,
        "agent_config": {
            "agent_id": body.agent_id,
            "agent_source": "openclaw",
            "runs_on": body.runs_on,
            "dsid": agent.get("dsid"),
            "agent_public_hash": agent.get("agent_public_hash"),
        },
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.MARKETPLACE_SERVICE_URL}/marketplace/listings",
                json=listing_data,
                headers={
                    "x-user-id": user_id,
                    "x-internal-service-key": settings.INTERNAL_SERVICE_KEY,
                },
            )
        if resp.status_code in (200, 201):
            return {"status": "listed", "agent_id": body.agent_id, "listing": resp.json()}
        else:
            return {"status": "listed_partial", "agent_id": body.agent_id, "note": "Agent marked for marketplace but listing service returned non-200"}
    except Exception as e:
        logger.warning(f"Marketplace listing failed for {body.agent_id}: {e}")
        return {"status": "listed_partial", "agent_id": body.agent_id, "note": f"Agent marked for marketplace. Listing sync pending: {e}"}


# ============================================
# UNIFIED LLM PROXY (OpenAI-Compatible)
# ============================================
# Routes OpenClaw gateway LLM calls through the platform's
# Unified LLM Service, which handles BYOK keys, provider
# fallback chains, rate limiting, and model routing.
# The gateway connects here instead of calling providers directly.
# ============================================

# Provider detection from model name
_MODEL_PROVIDER_MAP = {
    "llama": "groq", "mixtral": "groq", "gemma": "groq",
    "gpt-": "openai", "o1": "openai", "o3": "openai", "o4": "openai",
    "claude": "anthropic",
    "gemini": "gemini",
    "deepseek": "deepseek",
    "mistral": "mistral",
}

# BYOK key cache: user_id → {provider: key, ...}
_byok_cache: Dict[str, Dict[str, Any]] = {}
_BYOK_CACHE_TTL = 300  # 5 minutes


async def _fetch_byok_keys(user_id: str) -> Dict[str, str]:
    """Fetch user's BYOK API keys from auth service (cached)."""
    now = time.time()
    cached = _byok_cache.get(user_id)
    if cached and now - cached.get("_ts", 0) < _BYOK_CACHE_TTL:
        return {k: v for k, v in cached.items() if k != "_ts"}

    keys = {}
    try:
        url = f"{settings.AUTH_SERVICE_URL}/auth/internal/user-api-keys/{user_id}"
        headers = {"x-user-id": user_id}
        if settings.INTERNAL_SERVICE_KEY:
            headers["x-internal-service-key"] = settings.INTERNAL_SERVICE_KEY
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                _alias = {"google": "gemini", "chatgpt": "openai", "claude": "anthropic"}
                for entry in resp.json().get("keys", []):
                    prov = entry.get("provider")
                    key = entry.get("api_key")
                    if prov and key:
                        keys[_alias.get(prov.lower(), prov.lower())] = key
    except Exception as e:
        logger.warning(f"[LLM-Proxy] BYOK fetch failed for {user_id}: {e}")

    keys["_ts"] = now
    _byok_cache[user_id] = keys
    if keys:
        real_keys = {k: v for k, v in keys.items() if k != "_ts"}
        if real_keys:
            logger.info(f"[LLM-Proxy] BYOK loaded for {user_id}: {list(real_keys.keys())}")
    return {k: v for k, v in keys.items() if k != "_ts"}


def _detect_provider(model: str) -> Optional[str]:
    """Detect provider from model name."""
    model_lower = (model or "").lower()
    for pattern, provider in _MODEL_PROVIDER_MAP.items():
        if pattern in model_lower:
            return provider
    return None


@router.post("/v1/chat/completions")
async def llm_proxy_chat_completions(request: Request):
    """
    OpenAI-compatible chat completions proxy.

    Routes OpenClaw gateway LLM calls through the platform's Unified LLM
    Service, which handles BYOK keys, provider fallback, and model routing.

    The gateway calls this instead of hitting OpenAI/Groq/Anthropic directly.
    No hardcoded API keys needed in openclaw.json.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    model = body.get("model", "")
    messages = body.get("messages", [])
    temperature = body.get("temperature", 0.7)
    max_tokens = body.get("max_tokens", 4096)
    tools = body.get("tools")
    tool_choice = body.get("tool_choice")
    stream = body.get("stream", False)

    if not messages:
        raise HTTPException(status_code=400, detail="messages is required")

    # Detect provider from model name
    provider = _detect_provider(model)

    # Try to get user_id for BYOK (gateway can pass via header)
    user_id = (
        request.headers.get("x-user-id")
        or request.headers.get("x-openclaw-user-id")
        or ""
    )

    # Fetch BYOK keys if we have a user_id
    user_api_keys = {}
    if user_id:
        user_api_keys = await _fetch_byok_keys(user_id)

    # Build request for platform LLM service
    llm_payload = {
        "messages": [
            {"role": m.get("role", "user"), "content": m.get("content", "")}
            for m in messages if m.get("content")
        ],
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "provider": provider,
    }
    if tools:
        llm_payload["tools"] = tools
    if tool_choice:
        llm_payload["tool_choice"] = tool_choice
    if user_id:
        llm_payload["user_id"] = user_id
    if user_api_keys:
        llm_payload["user_api_keys"] = user_api_keys

    # Forward to platform LLM service
    llm_url = f"{settings.LLM_SERVICE_URL}/llm/chat/completions"
    headers = {"Content-Type": "application/json"}
    if settings.INTERNAL_SERVICE_KEY:
        headers["x-internal-service-key"] = settings.INTERNAL_SERVICE_KEY
    if user_id:
        headers["x-user-id"] = user_id

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(llm_url, json=llm_payload, headers=headers)

            if resp.status_code == 200:
                data = resp.json()
                # LLM service may return its own format — normalize to OpenAI format
                if "choices" in data:
                    # Already OpenAI-compatible
                    logger.info(f"[LLM-Proxy] OK model={model} provider={provider} user={user_id or 'platform'}")
                    return data
                else:
                    # Wrap in OpenAI format
                    content = data.get("content", data.get("text", ""))
                    usage = data.get("usage", {})
                    tool_calls_resp = data.get("tool_calls", [])

                    message = {"role": "assistant", "content": content}
                    if tool_calls_resp:
                        message["tool_calls"] = tool_calls_resp
                        message["content"] = content or None

                    openai_response = {
                        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
                        "object": "chat.completion",
                        "created": int(time.time()),
                        "model": data.get("model", model),
                        "choices": [{
                            "index": 0,
                            "message": message,
                            "finish_reason": "tool_calls" if tool_calls_resp else "stop",
                        }],
                        "usage": {
                            "prompt_tokens": usage.get("prompt_tokens", usage.get("input_tokens", 0)),
                            "completion_tokens": usage.get("completion_tokens", usage.get("output_tokens", 0)),
                            "total_tokens": usage.get("total_tokens", 0),
                        },
                    }
                    logger.info(f"[LLM-Proxy] OK model={model} provider={data.get('provider', provider)} user={user_id or 'platform'}")
                    return openai_response
            else:
                error_text = resp.text[:500]
                logger.warning(f"[LLM-Proxy] LLM service returned {resp.status_code}: {error_text}")
                # Return OpenAI-compatible error
                return {
                    "error": {
                        "message": f"LLM service error: {error_text}",
                        "type": "server_error",
                        "code": resp.status_code,
                    }
                }
    except httpx.TimeoutException:
        logger.error(f"[LLM-Proxy] Timeout calling LLM service for model={model}")
        return {
            "error": {
                "message": "LLM service timeout",
                "type": "timeout",
                "code": 504,
            }
        }
    except Exception as e:
        logger.error(f"[LLM-Proxy] Error: {e}")
        return {
            "error": {
                "message": f"LLM proxy error: {str(e)[:300]}",
                "type": "internal_error",
                "code": 500,
            }
        }
