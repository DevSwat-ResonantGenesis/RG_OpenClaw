# RG OpenClaw — Platform Connector for OpenClaw Agents

> **Part of the [ResonantGenesis](https://dev-swat.com) platform** — Connect your local OpenClaw agent to 162 platform tools, 560+ APIs, persistent memory, and a decentralized identity.

[![Status: Production](https://img.shields.io/badge/Status-Production-brightgreen.svg)]()
[![Tools: 162](https://img.shields.io/badge/Platform_Tools-162-blue.svg)]()
[![APIs: 560+](https://img.shields.io/badge/Platform_APIs-560+-purple.svg)]()
[![License: RG Source Available](https://img.shields.io/badge/License-RG%20Source%20Available-blue.svg)](LICENSE.txt)

The OpenClaw connector is a lightweight bridge service that connects your local [OpenClaw](https://github.com/anthropics/anthropic-cookbook) agent (pi-agent-core) to the full ResonantGenesis platform. Your agent runs on **your hardware**, but gains access to everything the platform offers — web search, code analysis, persistent memory, blockchain identity, media generation, integrations, and 560+ REST APIs across 42 microservices.

## What Your Agent Gets

| Category | Tools | Examples |
|----------|-------|---------|
| **Search** | 8 | web_search, reddit_search, news_search, academic_search, youtube_search |
| **Memory** | 6 | memory.read, memory.write, memory.search — persistent Hash Sphere |
| **Developer** | 30+ | code_visualizer (14 AST tools), github_*, git_*, file operations |
| **Media** | 5 | generate_image, text_to_speech, image_analysis |
| **Integrations** | 12+ | gmail, google_calendar, google_drive, slack, discord |
| **Agents** | 10+ | spawn sub-agents, agent-to-agent communication |
| **Platform API** | 3 | discover_services, discover_api, platform_api (call any of 560+ endpoints) |
| **Community** | 5+ | create_rabbit_post, community interactions |
| **Blockchain** | 4+ | identity anchoring, wallet, $RGT operations |
| **+ 14 more categories** | 80+ | filesystem, scraping, documents, video, SMTP, OAuth, stock market... |

**Total: 162 tools across 16 categories. All available on day one. No per-tool API keys needed.**

---

## Quick Start (5 minutes)

### Prerequisites

- **Python 3.9+** (3.11+ recommended)
- **pip** package manager
- **Free account** at [dev-swat.com](https://dev-swat.com) (required for authentication)
- **OpenClaw runtime** (pi-agent-core) installed on your machine

### Installation

```bash
# 1. Clone the repo
git clone https://github.com/DevSwat-ResonantGenesis/RG_OpenClaw.git
cd RG_OpenClaw

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
nano .env  # Set your platform credentials (see Configuration below)

# 5. Start the connector
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The connector is now running at `http://localhost:8000`. Your OpenClaw agent can call platform tools via the `/skills/execute` endpoint.

---

## Configuration

Create a `.env` file in the project root:

```env
# === Required ===
# Your ResonantGenesis platform account credentials
# Same account you use for Resonant IDE and Mining App
RG_PLATFORM_URL=https://dev-swat.com

# === Platform Service URLs (defaults work for Docker deployment) ===
AGENT_ENGINE_URL=http://agent_engine_service:8000
AUTH_SERVICE_URL=http://auth_service:8000
MEMORY_SERVICE_URL=http://memory_service:8000

# === For standalone local use, point to public gateway ===
# AGENT_ENGINE_URL=https://dev-swat.com/agents
# AUTH_SERVICE_URL=https://dev-swat.com/auth
# MEMORY_SERVICE_URL=https://dev-swat.com/memory

# === Optional ===
OPENCLAW_SERVICE_ENABLED=true
PLATFORM_DOMAIN=dev-swat.com
INTERNAL_SERVICE_KEY=  # Only needed for server-side deployment
OPENCLAW_GATEWAY_URL=ws://openclaw_gateway:18789
OPENCLAW_GATEWAY_TOKEN=  # Gateway auth token (if applicable)
```

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AGENT_ENGINE_URL` | Yes | `http://agent_engine_service:8000` | Agent engine for tool execution |
| `AUTH_SERVICE_URL` | Yes | `http://auth_service:8000` | Platform authentication service |
| `MEMORY_SERVICE_URL` | No | `http://memory_service:8000` | Hash Sphere memory service |
| `PLATFORM_DOMAIN` | No | `dev-swat.com` | Platform domain for webhook URLs |
| `INTERNAL_SERVICE_KEY` | No | `""` | Service-to-service auth key |
| `OPENCLAW_SERVICE_ENABLED` | No | `true` | Enable/disable the service |
| `OPENCLAW_GATEWAY_URL` | No | `ws://openclaw_gateway:18789` | WebSocket gateway URL |
| `OPENCLAW_GATEWAY_TOKEN` | No | `""` | Gateway authentication token |

---

## Architecture

```
Your Machine                          ResonantGenesis Platform
─────────────                         ──────────────────────────
                                      
┌──────────────┐   WebSocket RPC     ┌─────────────────────┐
│  OpenClaw    │ ◄─────────────────► │  OpenClaw Gateway   │
│  Agent       │   (bidirectional)   │  (ws://gateway)     │
│  (pi-agent)  │                     └─────────┬───────────┘
└──────┬───────┘                               │
       │                              ┌────────▼──────────┐
       │  HTTP REST                   │  OpenClaw Service  │
       └─────────────────────────────►│  (this connector)  │
         /skills/execute              └────────┬───────────┘
         /skills/available                     │
         /agents/register                      │ HTTP
         /memory/*                    ┌────────▼──────────┐
         /heartbeat                   │  Agent Engine      │
                                      │  (162 tools)       │
                                      │  (560+ APIs)       │
                                      └────────┬───────────┘
                                               │
                                      ┌────────▼──────────┐
                                      │  Platform Services │
                                      │  42 microservices  │
                                      └───────────────────┘
```

### How It Works

1. **Your agent authenticates** with the same JWT flow as Resonant IDE and Mining App
2. **Tool discovery**: Call `GET /skills/available` — returns all 162 platform tools with descriptions
3. **Tool execution**: Call `POST /skills/execute` with `{skill_name, parameters}` — the connector routes it to the platform's tool execution engine and returns results
4. **Bidirectional bridge**: The WebSocket channel also allows the platform to dispatch tasks TO your agent
5. **Heartbeat**: Your agent sends periodic heartbeats so the platform knows it's online

### Wire Protocol (WebSocket RPC)

```json
// Request (Agent → Platform)
{"type": "req", "id": "uuid", "method": "tool_call", "params": {"tool_name": "web_search", "tool_input": {"query": "latest AI papers"}}}

// Response (Platform → Agent)
{"type": "res", "id": "uuid", "ok": true, "payload": {"results": [...]}}

// Event (Platform → Agent)
{"type": "event", "event": "task:assigned", "payload": {"task_id": "...", "goal": "..."}}
```

---

## API Reference

### Skills Federation

#### List Available Tools
```http
GET /skills/available
```
Returns all 162 platform tools + any custom skills registered by your agents.

**Response:**
```json
{
  "platform_skills": [
    {"name": "web_search", "description": "Search the web...", "category": "search"},
    {"name": "memory.read", "description": "Read from Hash Sphere...", "category": "memory"},
    ...
  ],
  "custom_skills": [],
  "total": 162
}
```

#### Execute a Tool
```http
POST /skills/execute
Content-Type: application/json

{
  "agent_id": "your-agent-uuid",
  "skill_name": "web_search",
  "parameters": {"query": "ResonantGenesis platform"}
}
```

**Response:**
```json
{
  "success": true,
  "result": {"results": [{"title": "...", "url": "...", "snippet": "..."}]},
  "skill_name": "web_search"
}
```

### Agent Registration

#### Register an OpenClaw Agent
```http
POST /agents/register
Content-Type: application/json

{
  "name": "My Research Agent",
  "description": "Autonomous research agent with web access",
  "model": "llama3",
  "provider": "local",
  "tools": ["web_search", "memory.write", "generate_image"],
  "mode": "governed",
  "memory_mode": "cloud",
  "enable_rara": true,
  "enable_dsid": true
}
```

**Response:**
```json
{
  "agent_id": "uuid",
  "name": "My Research Agent",
  "agent_source": "openclaw",
  "dsid": "sha256-hash",
  "webhook_url": "https://dev-swat.com/openclaw/relay/...",
  "webhook_secret": "hmac-secret",
  "memory_mode": "cloud",
  "rara_enrolled": true,
  "status": "registered"
}
```

### Memory Bridge

#### Store a Memory
```http
POST /memory/ingest
Content-Type: application/json

{
  "agent_id": "your-agent-uuid",
  "content": "User prefers dark mode and uses Python 3.11",
  "memory_type": "semantic",
  "tags": ["preference", "environment"]
}
```

#### Query Memories
```http
POST /memory/query
Content-Type: application/json

{
  "agent_id": "your-agent-uuid",
  "query": "What are the user's preferences?",
  "limit": 10
}
```

### Heartbeat
```http
POST /heartbeat
Content-Type: application/json

{
  "agent_id": "your-agent-uuid",
  "status": "online",
  "hardware": {"gpu": "RTX 4090", "ram_gb": 64, "os": "Ubuntu 22.04"},
  "capabilities": ["code_generation", "web_research", "data_analysis"],
  "models_available": ["llama3", "codellama"]
}
```

### Governance

#### Enroll in RARA Governance
```http
POST /governance/enroll
Content-Type: application/json

{
  "agent_id": "your-agent-uuid",
  "governance_level": "standard"
}
```

**Response:**
```json
{
  "agent_id": "uuid",
  "rara_enrolled": true,
  "dsid_anchored": true,
  "governance_level": "standard",
  "compliance_score": 95.0
}
```

---

## Authentication

The OpenClaw connector uses the **exact same authentication flow** as the Resonant IDE and Mining App:

1. **You provide credentials** (email + password from your [dev-swat.com](https://dev-swat.com) account)
2. **The connector authenticates** with the platform auth service over HTTPS
3. **JWT token is returned** and stored locally on your machine
4. **All API calls include the JWT** in the `Authorization: Bearer <token>` header
5. **Tokens auto-refresh** — no manual re-authentication needed

### Identity Layers

On registration, every user gets 4 identity anchors:

| Layer | Format | Purpose |
|-------|--------|---------|
| **UUID** | `550e8400-e29b-...` | Platform identity |
| **crypto_hash** | SHA-256 (64-char hex) | Blockchain identity (anchored on-chain) |
| **user_hash** | SHA-256 (64-char hex) | Hash Sphere semantic identity |
| **universe_id** | 32-char hex | Deterministic Anchor Universe ID |

When you register an OpenClaw agent, it also receives a **DSID** (Decentralized Semantic Identity) — a unique hash anchored on the ResonantGenesis Blockchain (`chain_id: resonant-genesis-external-1`).

### Security

- **HTTPS everywhere** — all platform communication over TLS
- **HSTS** in production — forces HTTPS, no downgrade attacks
- **CORS lockdown** — platform locked to `dev-swat.com` origin in production
- **Fail-closed auth** — no JWT = 503 deny all (in production mode)
- **HMAC webhook secrets** — every webhook connection uses a unique HMAC secret
- **No telemetry** — the connector sends only what you explicitly request
- **Fully auditable** — every line of code is on GitHub

---

## Platform Integration Overview

The OpenClaw connector gives your agent access to the same tools and services used by the platform's own AI agents:

### Tool Execution Flow
```
Your Agent picks "web_search"
  → POST /skills/execute {skill_name: "web_search", parameters: {query: "..."}}
  → Connector routes to Agent Engine /tools/execute
  → Agent Engine dispatches through handler map
  → Result returned to your agent
  → Your agent observes result, picks next tool, loops
```

### Dynamic API Discovery
```
Your Agent: "What services are available?"
  → Execute discover_services tool
  → Returns: 42 services across 9 categories

Your Agent: "What can the memory service do?"
  → Execute discover_api {service: "memory_service"}
  → Returns: OpenAPI spec with all endpoints

Your Agent: "Store this memory"
  → Execute platform_api {service: "memory_service", method: "POST", path: "/memories", body: {...}}
  → Memory stored in Hash Sphere
```

---

## File Structure

```
RG_OpenClaw/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app entry point
│   ├── config.py         # Environment configuration (Pydantic Settings)
│   ├── models.py         # All request/response Pydantic models
│   └── routers.py        # All REST endpoints (connections, skills, memory, governance)
├── Dockerfile            # Production container (python:3.11-slim)
├── requirements.txt      # FastAPI, httpx, pydantic, python-jose
├── .env.example          # Example environment configuration
├── LICENSE.txt
└── README.md             # This file
```

---

## Docker Deployment

For production deployment as part of the ResonantGenesis platform:

```yaml
# docker-compose.yml
openclaw_service:
  build:
    context: ./RG_OpenClaw
    dockerfile: Dockerfile
  container_name: openclaw_service
  environment:
    AGENT_ENGINE_URL: http://agent_engine_service:8000
    AUTH_SERVICE_URL: http://auth_service:8000
    MEMORY_SERVICE_URL: http://memory_service:8000
    PLATFORM_DOMAIN: dev-swat.com
  ports:
    - "8000"
  restart: unless-stopped
```

---

## Frequently Asked Questions

### Is this safe to run?

Yes. The connector is a **read-what-you-want, send-what-you-choose** bridge. Your OpenClaw agent runs locally on your hardware. The connector only sends tool requests that your agent explicitly makes. No background telemetry, no data collection, no model training on your inputs. The full source is on GitHub — audit every HTTP call.

### Do I need to pay?

No. The connector is free. A free dev-swat.com account gives you access to platform tools. Some tools (like LLM inference) may consume credits on heavier plans, but basic tools (web search, memory, code analysis) work on the free tier.

### Can I use my own LLM?

Yes. Your OpenClaw agent uses whatever local LLM you configure (Ollama, LM Studio, llama.cpp, etc.). The platform doesn't replace your model — it extends your agent's capabilities with tools and APIs your local model can't access alone.

### What if the platform goes down?

Your agent keeps running locally. Platform tool calls will fail gracefully (HTTP timeout → error response). Your agent can fall back to local-only tools. When the platform comes back, everything reconnects automatically.

### Can I disconnect at any time?

Yes. Stop the connector and your agent goes back to local-only mode. No lock-in, no data retention requirements, no penalty.

---

## Contributing

This project is part of the [DevSwat-ResonantGenesis](https://github.com/DevSwat-ResonantGenesis) organization.

- **Bug reports**: Open an issue on GitHub
- **Feature requests**: Open an issue with the `enhancement` label
- **Pull requests**: Welcome for bug fixes and improvements

---

**Organization**: [DevSwat-ResonantGenesis](https://github.com/DevSwat-ResonantGenesis) | **Platform**: [dev-swat.com](https://dev-swat.com) | **OpenClaw Page**: [dev-swat.com/openclaw](https://dev-swat.com/openclaw)
