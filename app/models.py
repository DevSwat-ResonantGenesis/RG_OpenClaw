"""
OpenClaw Service Models
========================

Pydantic models for request/response validation.
Fully self-contained — no imports from other platform services.
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


# ============================================
# Connection Models
# ============================================

class OpenClawConnectionCreate(BaseModel):
    """Create a new OpenClaw ↔ ResonantGenesis connection."""
    agent_id: str = Field(..., description="ResonantGenesis agent UUID to connect")
    connection_name: Optional[str] = Field(None, description="Friendly name for this connection")
    openclaw_config: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional OpenClaw-side config (automation name, trigger type, etc.)"
    )


class OpenClawConnection(BaseModel):
    """A live OpenClaw ↔ Agent connection."""
    id: str
    user_id: str
    agent_id: str
    agent_name: Optional[str] = None
    connection_name: str
    webhook_url: str
    webhook_path: str
    webhook_secret: str
    status: str = "active"  # active | paused | error
    trigger_count: int = 0
    last_triggered_at: Optional[str] = None
    created_at: Optional[str] = None
    openclaw_config: Dict[str, Any] = {}


class OpenClawConnectionList(BaseModel):
    """List of connections for a user."""
    connections: List[OpenClawConnection]
    count: int
    platform_domain: str


class OpenClawConnectionStatus(BaseModel):
    """Quick status check for the integration card."""
    connected: bool
    connection_count: int = 0
    connections: List[Dict[str, Any]] = []
    webhook_base_url: str = ""


# ============================================
# Webhook Models
# ============================================

class WebhookRelayPayload(BaseModel):
    """Payload from OpenClaw to relay to an agent."""
    event: str = "incoming"
    data: Dict[str, Any] = {}
    source: str = "openclaw"
    timestamp: Optional[str] = None


class WebhookRelayResponse(BaseModel):
    """Response after relaying a webhook."""
    status: str  # triggered | received | error | debounced
    session_id: Optional[str] = None
    message: Optional[str] = None


# ============================================
# Health / Info Models
# ============================================

class ServiceHealth(BaseModel):
    """Service health response."""
    service: str = "openclaw_service"
    version: str = "1.0.0"
    status: str = "healthy"
    enabled: bool = True
    platform_domain: str = ""
    agent_engine_reachable: bool = False
    timestamp: str = ""


class ClawHubManifest(BaseModel):
    """ClawHub skill package manifest."""
    name: str = "resonantgenesis"
    display_name: str = "ResonantGenesis (Cloud)"
    description: str = "Cloud-based AI agent platform. Triggers agents via webhooks."
    privacy_level: str = "cloud"
    requires_internet: bool = True
    version: str = "1.0.0"
    config_schema: Dict[str, Any] = {}


# ============================================
# Heartbeat / Reverse Connection Models
# ============================================

class AgentHeartbeat(BaseModel):
    """Heartbeat sent by an OpenClaw agent running on user hardware."""
    agent_id: str
    status: str = "online"  # online | busy | degraded | shutting_down
    hardware: Optional[Dict[str, Any]] = None  # cpu, gpu, ram, os info
    capabilities: Optional[List[str]] = None  # what this agent can do
    models_available: Optional[List[str]] = None  # local LLM models loaded
    uptime_seconds: Optional[int] = None
    current_load: Optional[float] = None  # 0.0-1.0
    version: Optional[str] = None  # openclaw agent version


class AgentHeartbeatResponse(BaseModel):
    """Response to heartbeat — can include pending tasks or config updates."""
    acknowledged: bool = True
    pending_tasks: List[Dict[str, Any]] = []
    config_update: Optional[Dict[str, Any]] = None


# ============================================
# OpenClaw Agent Registration Models
# ============================================

class OpenClawAgentRegister(BaseModel):
    """Register an OpenClaw agent that runs on user hardware."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    system_prompt: Optional[str] = None
    provider: Optional[str] = "local"  # local, ollama, etc
    model: str = "llama3"  # local model name
    temperature: float = 0.7
    max_tokens: int = 4096
    tools: Optional[List[str]] = None
    mode: str = "governed"  # governed | unbounded
    # Hardware info
    endpoint_url: Optional[str] = None  # URL where the agent is reachable
    hardware: Optional[Dict[str, Any]] = None  # cpu, gpu, ram
    # Memory config
    memory_mode: str = "cloud"  # cloud (use our Hash Sphere) | local | hybrid
    local_memory_endpoint: Optional[str] = None  # if memory_mode is local/hybrid
    # Custom skills
    custom_skills: Optional[List[Dict[str, Any]]] = None  # skills the agent brings
    # Governance
    enable_rara: bool = True  # opt-in to RARA governance
    enable_dsid: bool = True  # opt-in to DSID identity anchoring


class OpenClawAgentResponse(BaseModel):
    """Response after registering an OpenClaw agent."""
    agent_id: str
    name: str
    agent_source: str = "openclaw"
    dsid: Optional[str] = None
    agent_public_hash: Optional[str] = None
    agent_crypto_hash: Optional[str] = None
    agent_semantic_hash: Optional[str] = None
    agent_universe_id: Optional[str] = None
    webhook_url: str = ""
    webhook_secret: str = ""
    memory_mode: str = "cloud"
    rara_enrolled: bool = False
    skills_registered: int = 0
    status: str = "registered"


# ============================================
# Memory Bridge Models
# ============================================

class MemoryBridgeIngest(BaseModel):
    """Ingest a memory from an OpenClaw agent into Hash Sphere."""
    agent_id: str
    content: str
    memory_type: str = "episodic"  # episodic | semantic | procedural
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None


class MemoryBridgeQuery(BaseModel):
    """Query memories from Hash Sphere for an OpenClaw agent."""
    agent_id: str
    query: str
    limit: int = 10
    memory_type: Optional[str] = None


class MemoryBridgeResponse(BaseModel):
    """Memory query response."""
    memories: List[Dict[str, Any]] = []
    count: int = 0
    source: str = "hash_sphere"  # hash_sphere | local | hybrid


# ============================================
# Skills Federation Models
# ============================================

class SkillImport(BaseModel):
    """Import a custom skill from an OpenClaw agent."""
    name: str = Field(..., min_length=1, max_length=128)
    description: str
    agent_id: str  # the openclaw agent that provides this skill
    parameters_schema: Optional[Dict[str, Any]] = None
    endpoint_url: Optional[str] = None  # where to call this skill on user hardware
    category: str = "custom"
    risk_level: str = "medium"


class SkillExecuteRequest(BaseModel):
    """Execute a platform skill on behalf of an OpenClaw agent."""
    agent_id: str
    skill_name: str
    parameters: Dict[str, Any] = {}


class SkillExecuteResponse(BaseModel):
    """Result of skill execution."""
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    skill_name: str = ""


# ============================================
# Governance Bridge Models
# ============================================

class GovernanceEnroll(BaseModel):
    """Enroll an OpenClaw agent in RARA governance."""
    agent_id: str
    governance_level: str = "standard"  # standard | strict | minimal


class GovernanceStatus(BaseModel):
    """Governance status for an OpenClaw agent."""
    agent_id: str
    rara_enrolled: bool = False
    dsid_anchored: bool = False
    governance_level: str = "standard"
    compliance_score: Optional[float] = None
    violations: int = 0
    last_audit: Optional[str] = None


# ============================================
# Marketplace Models
# ============================================

class MarketplaceListRequest(BaseModel):
    """List an OpenClaw agent on the marketplace."""
    agent_id: str
    name: str
    description: str
    category: str = "utility"
    tags: List[str] = []
    price_per_execution: float = 0.0
    runs_on: str = "user_hardware"  # user_hardware | cloud | hybrid
