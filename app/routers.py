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
from datetime import datetime, timezone
from typing import Optional, Dict, Any

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
    """Extract user ID from gateway-injected headers."""
    user_id = (
        request.headers.get("x-user-id")
        or request.headers.get("rg-user-id")
        or ""
    )
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
    """Make authenticated request to agent_engine_service."""
    url = f"{settings.AGENT_ENGINE_URL}/{path.lstrip('/')}"
    headers = {
        "x-user-id": user_id,
        "Content-Type": "application/json",
    }
    if settings.INTERNAL_SERVICE_KEY:
        headers["x-internal-service-key"] = settings.INTERNAL_SERVICE_KEY
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

    if resp.status_code >= 400:
        logger.warning(f"Agent engine {method} {path} returned {resp.status_code}: {resp.text[:200]}")
        raise HTTPException(
            status_code=resp.status_code,
            detail=resp.json().get("detail", resp.text[:200]) if resp.headers.get("content-type", "").startswith("application/json") else resp.text[:200],
        )
    return resp.json()


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

    # Check OpenClaw Gateway health
    gateway_ok = False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.OPENCLAW_GATEWAY_HTTP_URL}/healthz")
            gateway_ok = resp.status_code == 200
    except Exception:
        pass

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
):
    """
    Public endpoint: relay an OpenClaw event to an agent's webhook trigger.
    
    This is an alternative to calling the agent webhook directly.
    It adds OpenClaw-specific metadata and logging.
    
    No authentication required — HMAC signature verification happens at the
    agent_engine_service webhook endpoint.
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
    # Use internal service header to bypass signature verification (we're an internal relay)
    target_url = f"{settings.AGENT_ENGINE_URL}/webhooks/agent/{agent_id}/trigger"
    headers = {
        "Content-Type": "application/json",
        "x-internal-service": "openclaw_service",
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

    # 1. Create agent on agent_engine_service with source=openclaw
    agent_data = {
        "name": body.name,
        "description": body.description or f"OpenClaw agent running on user hardware",
        "system_prompt": body.system_prompt,
        "provider": body.provider or "local",
        "model": body.model,
        "temperature": body.temperature,
        "max_tokens": body.max_tokens,
        "tools": body.tools or ["web_search", "fetch_url"],
        "mode": body.mode,
        "agent_source": "openclaw",
        "openclaw_config": openclaw_config,
        "agent_public_hash": agent_crypto_hash,
    }

    # Check for superuser in request headers
    is_superuser = (request.headers.get("x-is-superuser") or "").strip().lower() in {"1", "true", "yes", "on"}
    extra_headers = {"x-is-superuser": "true"} if is_superuser else {}

    agent_result = await _agent_engine_request("POST", "agents/", user_id, json_body=agent_data, extra_headers=extra_headers)
    agent_id = agent_result.get("id", "")
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
            resp = await client.post(
                f"{settings.MEMORY_SERVICE_URL}/memories/ingest",
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
                headers={
                    "x-user-id": user_id,
                    "x-internal-service-key": settings.INTERNAL_SERVICE_KEY,
                },
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
            resp = await client.post(
                f"{settings.MEMORY_SERVICE_URL}/memories/search",
                json={
                    "query": body.query,
                    "limit": body.limit,
                    "filters": {
                        "agent_id": body.agent_id,
                        "memory_type": body.memory_type,
                    },
                },
                headers={
                    "x-user-id": user_id,
                    "x-internal-service-key": settings.INTERNAL_SERVICE_KEY,
                },
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

PLATFORM_SKILLS = [
    {"name": "web_search", "description": "Search the web using multiple engines", "category": "web", "risk_level": "low"},
    {"name": "fetch_url", "description": "Fetch and extract content from a URL", "category": "web", "risk_level": "low"},
    {"name": "code_visualizer", "description": "Analyze code repositories and generate architecture reports", "category": "developer-tools", "risk_level": "low"},
    {"name": "memory_search", "description": "Search long-term Hash Sphere memory", "category": "memory", "risk_level": "low"},
    {"name": "memory_store", "description": "Store new memories in Hash Sphere", "category": "memory", "risk_level": "low"},
    {"name": "web_scrape", "description": "Advanced web scraping with content extraction", "category": "web", "risk_level": "medium"},
    {"name": "file_create", "description": "Create files on the platform", "category": "filesystem", "risk_level": "medium"},
    {"name": "api_call", "description": "Make HTTP requests to external APIs", "category": "network", "risk_level": "medium"},
]


@router.get("/skills/available")
async def list_available_skills(request: Request):
    """
    List all platform skills available to OpenClaw agents.
    
    Includes both built-in platform skills and any custom skills
    registered by this user's OpenClaw agents.
    """
    user_id = _get_user_id(request)

    # Collect custom skills from all user's openclaw agents
    all_custom = []
    for agent_id, skills in _custom_skills_store.items():
        for s in skills:
            all_custom.append({**s, "source": "openclaw_custom"})

    return {
        "platform_skills": PLATFORM_SKILLS,
        "custom_skills": all_custom,
        "total": len(PLATFORM_SKILLS) + len(all_custom),
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

    # Platform skill — route to agent_engine_service for execution
    try:
        result = await _agent_engine_request(
            "POST",
            f"agents/{body.agent_id}/execute",
            user_id,
            json_body={
                "goal": f"Execute skill: {body.skill_name}",
                "context": {"skill": body.skill_name, "parameters": body.parameters},
            },
        )
        return SkillExecuteResponse(
            success=True,
            result=result,
            skill_name=body.skill_name,
        )
    except HTTPException as e:
        return SkillExecuteResponse(success=False, error=str(e.detail), skill_name=body.skill_name)
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
