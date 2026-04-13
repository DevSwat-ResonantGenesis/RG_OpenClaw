# RG OpenClaw — Federated Agent Connector

> **Part of the [ResonantGenesis](https://dev-swat.com) platform** — Run agents on YOUR hardware. Access 162 platform tools, 560+ APIs, persistent memory, blockchain identity, and execute tasks from the platform UI.

[![Status: Production](https://img.shields.io/badge/Status-Production-brightgreen.svg)]()
[![Tools: 162](https://img.shields.io/badge/Platform_Tools-162-blue.svg)]()
[![APIs: 560+](https://img.shields.io/badge/Platform_APIs-560+-purple.svg)]()
[![License: RG Source Available](https://img.shields.io/badge/License-RG%20Source%20Available-blue.svg)](LICENSE.txt)

The OpenClaw connector is a **federated agent bridge** that connects your local OpenClaw agent to the ResonantGenesis platform. Your agent runs on **your hardware** with your LLM, but gains full access to platform tools — web search, code analysis, persistent memory, blockchain identity, media generation, and 560+ REST APIs across 42 microservices.

**Federated means**: Your agent is registered on the platform with `agent_source='federated'`. You can run it from the platform's Agents page (dev-swat.com/agents), and the platform dispatches tasks to your local machine. Your compute, your data, your control.

## Full Tool Catalog

**137 tools across 15 categories — all available to your agent on day one. No per-tool API keys needed.**

### Search & Web (11 tools)
| Tool | Description |
|------|-------------|
| `web_search` | Search the web for current information, news, articles, documentation |
| `fetch_url` | Fetch and read content from any URL |
| `read_webpage` | Read a webpage and extract clean structured content |
| `read_many_pages` | Read multiple web pages in parallel (max 5) |
| `reddit_search` | Search Reddit for discussions and recommendations |
| `image_search` | Search for images on the web |
| `news_search` | Search latest news articles |
| `places_search` | Search for businesses on Google Maps |
| `youtube_search` | Search YouTube for videos |
| `deep_research` | Deep multi-source research via Perplexity AI |
| `wikipedia` | Search and read Wikipedia articles |

### Memory & Hash Sphere (9 tools)
| Tool | Description |
|------|-------------|
| `memory_read` | Search user's long-term memory |
| `memory_write` | Save information to long-term memory |
| `memory_search` | Deep keyword + semantic search through memories |
| `memory_stats` | Get memory usage stats |
| `hash_sphere_search` | Search Hash Sphere anchors (blockchain-verified memories) |
| `hash_sphere_anchor` | Create a new blockchain-verified memory point |
| `hash_sphere_list_anchors` | List all user's Hash Sphere anchors |
| `hash_sphere_hash` | Generate a Hash Sphere hash for content |
| `hash_sphere_resonance` | Check resonance between two content pieces |

### Code Visualizer / SAST (8 tools)
| Tool | Description |
|------|-------------|
| `code_visualizer_scan` | AST-scan project: functions, classes, endpoints, imports, pipelines, dead code |
| `code_visualizer_functions` | List all functions and API endpoints |
| `code_visualizer_trace` | Trace dependency flow from any node |
| `code_visualizer_governance` | Architecture governance: reachability, drift, health score (0-100) |
| `code_visualizer_graph` | Get full dependency graph |
| `code_visualizer_pipeline` | Get auto-detected pipeline flow |
| `code_visualizer_filter` | Filter graph by file path, node type, or keyword |
| `code_visualizer_by_type` | Get all nodes of a type (function, class, endpoint, service, etc.) |

### Agents OS (24 tools)
| Tool | Description |
|------|-------------|
| `agents_list` | List user's AI agents |
| `agents_create` | Create a new AI agent |
| `agents_start` | Start/run an agent |
| `agents_stop` | Stop a running agent |
| `agents_status` | Get agent config and status |
| `agents_delete` | Delete an agent |
| `agents_update` | Update agent config — name, goal, model, tools, etc. |
| `agents_sessions` | List sessions/runs for an agent |
| `agents_session_steps` | Get execution steps for a session |
| `agents_session_trace` | Full execution trace — steps, waterfall, cost, safety flags |
| `agents_metrics` | Get agent run metrics (sessions, tokens, success rate) |
| `agents_session_cancel` | Cancel a running session |
| `workspace_snapshot` | Full overview of workspace |
| `run_agent` | Directly run an agent with a goal |
| `schedule_agent` | Set recurring schedule for an agent |
| `present_options` | Present interactive options to the user |
| `architect_plan` | Analyze a request and produce a JSON blueprint for production-ready agents |
| `architect_create_agent` | Create a fully-configured agent from a blueprint |
| `architect_assign_goal` | Assign a goal to an agent |
| `architect_create_schedule` | Create a recurring schedule — cron or interval |
| `architect_create_webhook` | Create a webhook trigger for an agent |
| `architect_set_autonomy` | Set autonomy mode (governed, supervised, unbounded) |
| `architect_list_available_tools` | List all tools available to assign to agents |
| `architect_list_providers` | List available LLM providers and models |

### Media Generation (3 tools)
| Tool | Description |
|------|-------------|
| `generate_image` | Generate an AI image from text (DALL-E) |
| `generate_audio` | Generate speech from text (TTS) |
| `generate_music` | Generate music from text description |

### Integrations (9 tools)
| Tool | Description |
|------|-------------|
| `gmail_send` | Send email via Gmail |
| `gmail_read` | Read recent Gmail inbox |
| `slack_send` | Send Slack message |
| `slack_read` | Read Slack channel messages |
| `google_calendar` | Google Calendar: list/create events, check availability |
| `google_drive` | Google Drive: list/search/read/create files |
| `figma` | Figma: list projects, get file, inspect components |
| `sigma` | Sigma Computing dashboards and analytics |
| `send_email` | Send email via SendGrid with HTML support |

### GitHub (9 tools)
| Tool | Description |
|------|-------------|
| `github_create_repo` | Create GitHub repository |
| `github_list_repos` | List GitHub repositories |
| `github_list_files` | List files in a GitHub repo |
| `github_download_file` | Download file from GitHub repo |
| `github_upload_file` | Upload file to GitHub repo |
| `github_pull_request` | Create or list pull requests |
| `github_issue` | Create or list issues |
| `github_commit` | Get commits in a repository |
| `github_comment` | Comment on a GitHub issue or PR |

### Git Operations (5 tools)
| Tool | Description |
|------|-------------|
| `git_clone` | Clone a Git repository |
| `git_branch` | Create, list, or switch Git branches |
| `git_merge` | Merge a branch into current branch |
| `git_push` | Push commits to remote |
| `git_pull` | Pull changes from remote |

### State Physics Engine (21 tools)
| Tool | Description |
|------|-------------|
| `sp_state` | Get full State Physics universe — nodes, edges, metrics, invariants |
| `sp_reset` | Reset State Physics universe to initial state |
| `sp_nodes` | List all nodes in Hash Sphere universe |
| `sp_metrics` | Get universe metrics — node count, edge count, entropy |
| `sp_identity` | Create identity node in Hash Sphere universe |
| `sp_simulate` | Run N physics simulation steps |
| `sp_galaxy` | Create galaxy-scale simulation |
| `sp_demo` | Seed universe with demo data |
| `sp_asymmetry` | Get asymmetry score — trust variance and Gini |
| `sp_physics_config` | Update physics engine parameters |
| `sp_entropy_config` | Update entropy engine parameters |
| `sp_entropy_toggle` | Enable or disable entropy injection |
| `sp_entropy_perturbation` | Inject perturbation event |
| `sp_agent_spawn` | Spawn autonomous agent in universe |
| `sp_agent_step` | Step the active agent once |
| `sp_agent_kill` | Kill the active agent |
| `sp_agents_spawn` | Spawn multiple agents |
| `sp_agents_kill_all` | Kill all autonomous agents |
| `sp_experiment` | Setup named experiment — zero_agent, stress_test, long_run |
| `sp_memory_cost` | Set memory cost multiplier |
| `sp_metrics_record` | Record metrics snapshot to history |

### Community / Rabbit (12 tools)
| Tool | Description |
|------|-------------|
| `create_rabbit_post` | Create post in Rabbit community |
| `list_rabbit_communities` | List all Rabbit communities |
| `list_rabbit_posts` | List Rabbit posts |
| `rabbit_vote` | Vote on Rabbit post/comment |
| `create_rabbit_community` | Create a new Rabbit community |
| `get_rabbit_community` | Get a Rabbit community by slug |
| `search_rabbit_posts` | Search Rabbit posts by keyword |
| `get_rabbit_post` | Get a specific Rabbit post by ID |
| `delete_rabbit_post` | Delete a Rabbit post (owner only) |
| `create_rabbit_comment` | Comment on a Rabbit post |
| `list_rabbit_comments` | List comments on a Rabbit post |
| `delete_rabbit_comment` | Delete a Rabbit comment (owner only) |

### Developer (4 tools)
| Tool | Description |
|------|-------------|
| `execute_code` | Run code in Docker sandbox (Python, JavaScript, Bash) |
| `http_request` | HTTP request to internal platform APIs |
| `external_http_request` | HTTP request to any external URL |
| `dev_tool` | Bridge to ED service for file ops, git, docker, testing |

### Utilities (6 tools)
| Tool | Description |
|------|-------------|
| `weather` | Get current weather and 3-day forecast |
| `stock_crypto` | Get real-time stock or crypto prices |
| `generate_chart` | Generate chart image from data (bar, line, pie, radar, scatter) |
| `visualize` | Generate SVG diagram inline |
| `get_current_time` | Get current date, time, timezone |
| `get_system_info` | Get platform system info |

### Platform API (2 tools)
| Tool | Description |
|------|-------------|
| `platform_api_search` | Search ~383 platform API endpoints |
| `platform_api_call` | Call any authenticated platform API endpoint |

### Filesystem (10 tools)
| Tool | Description |
|------|-------------|
| `file_read` | Read file with offset/limit |
| `file_write` | Create or overwrite file |
| `file_edit` | Replace exact unique string in file |
| `multi_edit` | Atomic batch edits on one file |
| `file_list` | List directory contents |
| `file_delete` | Delete file or directory |
| `grep_search` | Search text pattern in files via ripgrep |
| `find_by_name` | Find files by name glob |
| `run_command` | Run shell command |
| `command_status` | Check background command status |

### Tool Management & Self-Creation (6 tools)
| Tool | Description |
|------|-------------|
| `create_tool` | Create custom HTTP tool stored in DB. Set `is_shared=true` to make it platform-wide |
| `list_tools` | List user's custom tools + all shared platform tools |
| `delete_tool` | Delete a custom tool |
| `update_tool` | Update an existing custom tool |
| `auto_build_tool` | **LLM designs, validates (AST safety scan), and registers a new tool at runtime.** Describe what the tool should do and it will be auto-created |
| `check_tool_exists` | Check if a capability exists as a tool. If not found, suggests using `auto_build_tool` |

---

## Self-Creating Tools — Agents Build What They Need

One of the most powerful capabilities of the platform is that **agents can create their own tools at runtime**. If an agent needs a capability that doesn't exist, it can design, validate, and register a new tool — and that tool immediately becomes available to the entire platform.

### How It Works

```
Agent needs a tool that doesn't exist
       │
       ▼
┌──────────────────────────────────────┐
│  1. check_tool_exists               │  ← Search 137+ built-in + all custom tools
│     "I need to track package prices" │
└──────────────┬───────────────────────┘
               │ Not found → suggests auto_build_tool
               ▼
┌──────────────────────────────────────┐
│  2. auto_build_tool                  │  ← LLM designs the tool spec
│     capability: "Track package       │
│     shipping prices from carriers"   │
│                                      │
│     → LLM generates: tool_name,     │
│       description, endpoint_url,     │
│       http_method, parameters,       │
│       request_body, category         │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  3. AST Safety Scan                  │  ← Validates no forbidden URLs,
│     No localhost, no metadata,       │     no SSRF patterns, valid schema
│     no file://, valid JSON           │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│  4. Registered in DB                 │  ← Stored in agentic_custom_tools
│     is_shared=true → platform-wide   │     category auto-assigned
│     Immediately available to ALL     │     Cache invalidated for all users
│     agents across the platform       │
└──────────────────────────────────────┘
```

### Key Features

- **LLM-Designed**: Agent describes what it needs in natural language → LLM generates the full tool spec
- **Safety-Scanned**: Every auto-built tool goes through AST safety validation (no SSRF, no internal endpoints)
- **Platform-Wide**: Set `is_shared=true` (default) and the tool is available to ALL users and agents
- **DB-Persisted**: Tools survive restarts, stored in PostgreSQL `agentic_custom_tools` table
- **Category Auto-Assignment**: Tools are categorized automatically (or use a custom category)
- **Immediate Availability**: No restart needed — tool is usable in the same conversation

### Example: Agent Creates a Tool

```json
// Agent calls auto_build_tool
{
  "capability": "Get real-time cryptocurrency fear and greed index",
  "category": "market_data",
  "is_shared": true
}

// LLM designs and registers:
{
  "tool_name": "crypto_fear_greed_index",
  "description": "Get the current cryptocurrency Fear & Greed Index",
  "endpoint_url": "https://api.alternative.me/fng/?limit=1",
  "http_method": "GET",
  "parameters": {"limit": "number of data points"},
  "category": "market_data",
  "is_shared": true
}

// Tool is now available platform-wide. Any agent can call:
// POST /skills/execute {"skill_name": "crypto_fear_greed_index", "parameters": {"limit": "1"}}
```

---

## Quick Start (5 minutes)

### Prerequisites

- **Python 3.9+** (3.11+ recommended)
- **pip** package manager
- **Free account** at [dev-swat.com](https://dev-swat.com) (required for authentication)

### Installation

```bash
# 1. Clone and set up
git clone https://github.com/DevSwat-ResonantGenesis/RG_OpenClaw.git
cd RG_OpenClaw
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Config (defaults work out of the box — no editing needed)
cp .env.example .env

# 3. Start the connector
uvicorn app.main:app --port 8000 --reload
```

Open http://localhost:8000 in your browser — you should see the connector status page.

### Full Tested A-to-Z Flow

Every command below has been tested end-to-end against the production platform (dev-swat.com) on April 13, 2026.

```bash
# ── Step 1: Check connector is running ────────────────────────────
curl http://localhost:8000/
# → {"service": "RG_OpenClaw Connector", "status": "running", "authenticated": false, ...}

# ── Step 2: Authenticate with your dev-swat.com account ──────────
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "your-password"}'
# → {"success": true, "user_id": "d85c1fd7-...", "email": "you@example.com", "expires_in": 86400}

# ── Step 3: Verify authentication ────────────────────────────────
curl http://localhost:8000/auth/status
# → {"authenticated": true, "token_expired": false, "token_ttl_seconds": 86185, "email": "you@example.com"}

# ── Step 4: Discover platform tools ──────────────────────────────
curl http://localhost:8000/skills/available | python3 -m json.tool
# → {"platform_skills": [...162 tools...], "total": 162}

# ── Step 5: Register a federated agent ───────────────────────────
# This creates your agent on the platform with agent_source='federated'
# and stores your hardware info, tools, and connection URL.
curl -X POST http://localhost:8000/agents/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-openclaw-agent",
    "description": "Federated agent on my local machine",
    "tools": ["web_search", "memory_read", "memory_write", "fetch_url", "deep_research"],
    "hardware": {"os": "macOS", "arch": "arm64"}
  }'
# → {"agent_id": "4c4466c7-...", "name": "my-openclaw-agent", "agent_source": "openclaw", "status": "registered"}

# ── Step 6: Execute a platform tool ──────────────────────────────
curl -X POST http://localhost:8000/skills/execute \
  -H "Content-Type: application/json" \
  -d '{"skill_name": "web_search", "parameters": {"query": "latest AI agent frameworks 2026"}}'
# → {"success": true, "result": {"results": [{"title": "Top 7 AI Agent Frameworks...", "url": "..."}]}}

# ── Step 7: Send heartbeat ───────────────────────────────────────
curl -X POST http://localhost:8000/agents/heartbeat \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "YOUR_AGENT_ID", "status": "online"}'
# → {"acknowledged": true, "pending_tasks": []}

# ── Step 8: Write memory to Hash Sphere ──────────────────────────
curl -X POST http://localhost:8000/memory/ingest \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "YOUR_AGENT_ID", "content": "First memory from my OpenClaw agent"}'
# → {"success": true, "data": {"id": "ee8f1d6d-...", "hash": "242c26...", "resonance_score": 1.69}}

# ── Step 9: Query memories ───────────────────────────────────────
curl -X POST http://localhost:8000/memory/query \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "YOUR_AGENT_ID", "query": "openclaw agent", "limit": 5}'
# → {"results": [{"content": "First memory from my OpenClaw agent", ...}]}

# ── Step 10: Run agent from platform UI ──────────────────────────
# Go to https://dev-swat.com/agents → find your agent → click Run
# The platform dispatches the task to your local connector.
# Your connector uses web_search, memory_read, memory_write to complete it.
# Results appear in the platform's session viewer with tools_used and duration.
```

### What happens when you Run from the platform

```
Platform UI (dev-swat.com/agents)
  → User clicks "Run" on federated agent
  → Agent Engine checks agent_source == 'federated'
  → Agent Engine POSTs task to your connector at localhost:8000/task/execute
  → Your connector executes using web_search, memory_read, memory_write
  → Results returned to Agent Engine → displayed in platform UI
  → Session shows: status=completed, tools_used, duration_ms
```

JWT is stored at `~/.openclaw/tokens.json` (chmod 600). Tokens auto-refresh — no manual re-authentication.

---

## Configuration

Create a `.env` file in the project root:

```env
# === Platform Domain ===
PLATFORM_DOMAIN=dev-swat.com

# === Platform Service URLs (standalone — through gateway HTTPS) ===
AUTH_SERVICE_URL=https://dev-swat.com/auth
AGENT_ENGINE_URL=https://dev-swat.com/api/v1/agents
MEMORY_SERVICE_URL=https://dev-swat.com/api/v1/memory
BLOCKCHAIN_SERVICE_URL=https://dev-swat.com/blockchain
LLM_SERVICE_URL=https://dev-swat.com/api/v1/llm
RARA_SERVICE_URL=https://dev-swat.com/api/v1/rara

# === Service Toggle ===
OPENCLAW_SERVICE_ENABLED=true
```

> **Note**: Defaults are standalone-first — all traffic routes through the platform's existing HTTPS gateway. No ports are exposed publicly. For Docker deployment, see the Docker section below.

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PLATFORM_DOMAIN` | No | `dev-swat.com` | Platform domain for webhook URLs |
| `AUTH_SERVICE_URL` | Yes | `https://dev-swat.com/auth` | Platform auth (through gateway) |
| `AGENT_ENGINE_URL` | Yes | `https://dev-swat.com/api/v1/agents` | Agent engine for tool execution |
| `MEMORY_SERVICE_URL` | No | `https://dev-swat.com/api/v1/memory` | Hash Sphere memory service |
| `BLOCKCHAIN_SERVICE_URL` | No | `https://dev-swat.com/blockchain` | Blockchain identity anchoring |
| `LLM_SERVICE_URL` | No | `https://dev-swat.com/api/v1/llm` | Unified LLM service |
| `RARA_SERVICE_URL` | No | `https://dev-swat.com/api/v1/rara` | RARA governance service |
| `INTERNAL_SERVICE_KEY` | No | `""` | Service-to-service auth (Docker only) |
| `OPENCLAW_SERVICE_ENABLED` | No | `true` | Enable/disable the service |

---

## Architecture

```
Your Machine (localhost:8000)          ResonantGenesis Platform (HTTPS)
────────────────────────────           ──────────────────────────────────

┌─────────────────────────┐           ┌──────────────────────┐
│  OpenClaw Connector     │  ──────►  │  HTTPS Gateway       │ ← TLS termination
│  (this repo)            │  HTTPS    │  (dev-swat.com:443)  │   JWT validation
│                         │  JWT auth │                      │   Rate limiting
│  /auth/login            │  ◄──────  │  Dispatches tasks    │
│  /auth/status           │  task     │  to your connector   │
│  /skills/available      │  dispatch │  when you click Run  │
│  /skills/execute        │           └──────────┬───────────┘
│  /agents/register       │                      │
│  /agents/heartbeat      │           ┌──────────▼───────────┐
│  /memory/ingest         │           │  Agent Engine         │
│  /memory/query          │           │  162 tools, 560+ APIs │
│  /task/execute ◄────────│───────────│  Federated dispatch   │
│                         │           └──────────┬───────────┘
└─────────────────────────┘                      │
                                      ┌──────────▼───────────┐
Your LLM (Ollama, Groq, etc.)        │  42 Microservices     │
Your hardware, your data              │  Memory, Blockchain,  │
                                      │  Storage, LLM, etc.   │
                                      └──────────────────────┘
```

### Two-Way Traffic

- **Outbound (You → Platform)**: Your connector calls platform tools via HTTPS. `POST /skills/execute` → gateway → agent engine → tool result → back to you.
- **Inbound (Platform → You)**: When you click "Run" on your federated agent at dev-swat.com/agents, the platform sends the task to `localhost:8000/task/execute`. Your connector runs it locally using platform tools and returns results.

> **Security**: All outbound traffic is JWT-authenticated HTTPS. Inbound task dispatch only works when your connector is running locally — the platform can't reach you unless you're online.

### How It Works

1. **Start connector**: `uvicorn app.main:app --port 8000 --reload` — connector runs locally
2. **Authenticate**: `POST /auth/login` with your dev-swat.com credentials — JWT stored at `~/.openclaw/tokens.json`
3. **Register agent**: `POST /agents/register` — creates a federated agent on the platform with `agent_source='federated'`, your tools, hardware info, and connection URL
4. **Discover tools**: `GET /skills/available` — returns all 162 platform tools
5. **Execute tools**: `POST /skills/execute` with `{skill_name, parameters}` — routed through the gateway
6. **Run from platform**: Click "Run" on your agent at dev-swat.com/agents — platform dispatches task to your connector, which executes using web_search + memory
7. **Heartbeat**: Periodic `POST /agents/heartbeat` keeps your agent status "online" on the platform
8. **Memory**: `POST /memory/ingest` and `POST /memory/query` — persistent Hash Sphere memory across sessions
9. **Token auto-refresh**: JWT tokens refresh automatically — no manual re-authentication needed

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

#### Register a Federated Agent
```http
POST /agents/register
Content-Type: application/json

{
  "name": "my-research-agent",
  "description": "Federated agent with web search and memory",
  "tools": ["web_search", "memory_read", "memory_write", "fetch_url", "deep_research"],
  "hardware": {"os": "macOS", "arch": "arm64"}
}
```

**Response:**
```json
{
  "agent_id": "4c4466c7-429c-4068-9208-87c1d08f2d0f",
  "name": "my-research-agent",
  "agent_source": "openclaw",
  "agent_public_hash": "9a8b0628018a0e76...",
  "agent_crypto_hash": "9a8b0628018a0e76...",
  "status": "registered"
}
```

**What this does on the platform:**
- Creates agent with `agent_source='federated'` (visible on Agents page)
- Stores `openclaw_config` with your `connection_url`, `hardware_info`, `capabilities`
- Assigns platform tools to the agent
- Anchors agent identity on the blockchain (DSID)
- Agent appears at dev-swat.com/agents with a "Federated" badge

### Task Execution (Platform → Local)

When you click "Run" on a federated agent in the platform UI, the Agent Engine dispatches the task to your local connector:

#### Execute a Task Locally
```http
POST /task/execute
Content-Type: application/json

{
  "task": "Search for upcoming AI events in San Francisco this week",
  "agent_id": "4c4466c7-...",
  "available_tools": ["web_search", "memory_read", "memory_write"],
  "context": {"user_id": "d85c1fd7-..."}
}
```

**Response:**
```json
{
  "success": true,
  "task_id": "4c4466c7-...",
  "output": "**Search Results:**\n- [AI Summit SF 2026](https://...)...\n\n**Relevant Memories:**\n- ...",
  "tools_used": ["web_search", "memory_read", "memory_write"],
  "duration_ms": 6491
}
```

The connector automatically:
1. Searches the web if the task mentions search-related keywords
2. Reads relevant memories from Hash Sphere
3. Stores the task result as a new memory
4. Returns structured output with tools_used and timing

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
│   ├── main.py            # FastAPI app + root status page + startup/shutdown
│   ├── config.py           # Environment config (Pydantic Settings, all service URLs)
│   ├── models.py           # Request/response Pydantic models (agent register, heartbeat, memory, etc.)
│   ├── platform_auth.py    # JWT auth — login, token storage at ~/.openclaw/tokens.json, auto-refresh
│   └── routers.py          # All endpoints: auth, skills, agents, memory, governance, task/execute
├── Dockerfile             # Production container (python:3.11-slim)
├── requirements.txt       # FastAPI, httpx, pydantic, python-jose, cryptography
├── .env.example           # Example config (defaults work out of the box)
├── LICENSE.txt
└── README.md              # This file
```

### Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Connector status dashboard |
| `GET` | `/health` | Health check |
| `POST` | `/auth/login` | Authenticate with dev-swat.com credentials |
| `GET` | `/auth/status` | Check auth status (no network call) |
| `GET` | `/skills/available` | List all 162 platform tools |
| `POST` | `/skills/execute` | Execute a platform tool by name |
| `POST` | `/agents/register` | Register a federated agent on the platform |
| `POST` | `/agents/heartbeat` | Send agent heartbeat (keeps status "online") |
| `POST` | `/memory/ingest` | Store memory in Hash Sphere |
| `POST` | `/memory/query` | Query memories from Hash Sphere |
| `POST` | `/task/execute` | Receive and execute platform-dispatched tasks |
| `GET` | `/manifest` | Agent manifest for marketplace |
| `GET` | `/setup-guide` | Setup instructions |

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
    BLOCKCHAIN_SERVICE_URL: http://blockchain_service:8000
    LLM_SERVICE_URL: http://llm_service:8000
    PLATFORM_DOMAIN: dev-swat.com
    INTERNAL_SERVICE_KEY: ${INTERNAL_SERVICE_KEY}
  # No ports exposed — internal network only. Gateway proxies all traffic.
  networks:
    - app-network
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
