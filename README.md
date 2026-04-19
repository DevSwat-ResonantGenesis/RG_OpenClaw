# RG OpenClaw — Federated Agent Connector

> **Part of the [DevSwat](https://dev-swat.com) platform** — Run agents on YOUR hardware. YOUR data stays on YOUR machine.

[![Status: Production](https://img.shields.io/badge/Status-Production-brightgreen.svg)]()
[![Local Tools: 8](https://img.shields.io/badge/Local_Tools-8-orange.svg)]()
[![Platform Tools: 162](https://img.shields.io/badge/Platform_Tools-162-blue.svg)]()
[![License: RG Source Available](https://img.shields.io/badge/License-RG%20Source%20Available-blue.svg)](LICENSE.txt)

The OpenClaw connector is a **local-first federated agent** that runs on your machine. Tools execute **locally** — web search, page fetching, code execution, and memory all happen on YOUR hardware. Only the final answer is sent to the platform. Memory is stored in a **local SQLite database** on your machine, never uploaded to the server.

**Local-First means**: When your agent calls `web_search`, it searches DuckDuckGo directly from your machine. When it calls `memory_write`, it saves to `~/.openclaw/data/memory.db` on your disk. When it calls `fetch_url`, your machine fetches the page. The platform server only receives step notifications (tool name + timing) and the final answer text. **Your data never leaves your machine.**

For cloud-only tools (Google Calendar, Slack, image generation) that require OAuth or GPU, the connector falls back to the platform server automatically.

## Full Tool Catalog

**137 tools across 15 categories — all available to your agent on day one. No per-tool API keys needed.**

### Search & Web (11 tools)
| Tool | Runs Where | Description |
|------|-----------|-------------|
| `web_search` | **🟢 LOCAL** | Search the web via DuckDuckGo — runs on YOUR machine, no API key |
| `fetch_url` | **🟢 LOCAL** | Fetch and read content from any URL — YOUR machine fetches it directly |
| `read_webpage` | **🟢 LOCAL** | Read a webpage and extract clean text (BeautifulSoup) |
| `read_many_pages` | Platform | Read multiple web pages in parallel (max 5) |
| `reddit_search` | Platform | Search Reddit for discussions and recommendations |
| `image_search` | Platform | Search for images on the web |
| `news_search` | Platform | Search latest news articles |
| `places_search` | Platform | Search for businesses on Google Maps |
| `youtube_search` | Platform | Search YouTube for videos |
| `deep_research` | **🟢 LOCAL** | Deep multi-source research — search + fetch combo on YOUR machine |
| `wikipedia` | Platform | Search and read Wikipedia articles |

### Memory — LOCAL on Your Machine (9 tools)
| Tool | Runs Where | Description |
|------|-----------|-------------|
| `memory_read` | **🟢 LOCAL** | Search your local memory (SQLite FTS5 full-text search) |
| `memory_write` | **🟢 LOCAL** | Save information to local memory (`~/.openclaw/data/memory.db`) |
| `memory_search` | **🟢 LOCAL** | Deep keyword search through local memories |
| `memory_stats` | Platform | Get memory usage stats |
| `hash_sphere_search` | Platform | Search Hash Sphere anchors (blockchain-verified memories) |
| `hash_sphere_anchor` | Platform | Create a new blockchain-verified memory point |
| `hash_sphere_list_anchors` | Platform | List all user's Hash Sphere anchors |
| `hash_sphere_hash` | Platform | Generate a Hash Sphere hash for content |
| `hash_sphere_resonance` | Platform | Check resonance between two content pieces |

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
| Tool | Runs Where | Description |
|------|-----------|-------------|
| `execute_code` | **🟢 LOCAL** | Run Python code on YOUR machine (subprocess, 30s timeout) |
| `http_request` | Platform | HTTP request to internal platform APIs |
| `external_http_request` | Platform | HTTP request to any external URL |
| `dev_tool` | Platform | Bridge to ED service for file ops, git, docker, testing |

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

# ── Step 8: Run agent from platform UI ───────────────────────────
# Go to https://dev-swat.com/agents → find your agent → click Run
# The platform dispatches the task to your local connector.
# Your connector executes tools LOCALLY on your machine:
#   web_search → DuckDuckGo (your machine)
#   memory_read/write → local SQLite (~/.openclaw/data/memory.db)
#   fetch_url → your machine fetches the page directly
# Only the final answer is sent back to the platform.
```

### What happens when you Run from the platform

```
Platform UI (dev-swat.com/agents)
  → User clicks "Run" on federated agent
  → Agent Engine queues task (status: pending)
  → Your local connector polls GET /federation/tasks/poll every 5 seconds
  → Connector picks up the task (status → dispatched)
  → LLM decides which tools to call (via platform LLM service)
  → Tools execute LOCALLY on your machine:
      web_search   → DuckDuckGo (no API key, runs locally)
      fetch_url    → httpx + BeautifulSoup (runs locally)
      memory_write → SQLite at ~/.openclaw/data/memory.db
      memory_read  → SQLite FTS5 full-text search
      execute_code → Python subprocess (30s timeout)
  → Step reports sent to platform (tool name + timing only, NO data)
  → Final answer submitted via POST /federation/tasks/{id}/result
  → Platform UI shows: status=completed, tools_used, duration_ms
  → Your memory stays on YOUR machine. Server only has the final answer.
```

**Security**: ALL traffic is outbound HTTPS from your machine. The platform never connects to you — your connector pulls tasks. Works behind any firewall, NAT, or VPN.

### Two ways to create a federated agent

**Option A: From the platform UI (easiest)**
1. Go to dev-swat.com/agents → click **+ Create**
2. Fill in name/description → click **Next**
3. On the Type step, click **⚡ Federated (Local)**
4. Pick provider/model/tools → **Create**
5. Agent appears on your Agents page with `agent_source='federated'`

**Option B: From the local connector (CLI)**
```bash
curl -X POST http://localhost:8000/agents/register \
  -H "Content-Type: application/json" \
  -d '{"name": "my-agent", "tools": ["web_search", "memory_read", "memory_write"]}'
```

### Mode toggle (governed / unbounded)

Federated agents default to **unbounded** (no approval gates, 200 max steps, 500K max tokens). You can toggle anytime:

```bash
# Switch to governed (25 steps max, approval gates)
curl -X PATCH https://dev-swat.com/api/v1/agents/AGENT_ID/mode \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{"mode": "governed"}'

# Switch back to unbounded
curl -X PATCH https://dev-swat.com/api/v1/agents/AGENT_ID/mode \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{"mode": "unbounded"}'
```

| | Governed | Unbounded |
|---|---|---|
| Safety gate | Every step checked | No checks |
| Max steps | 25 | 200 |
| Max tokens | 50,000 | 500,000 |
| Rate limit | 30/min | 120/min |
| Best for | Shared agents, production | Your own agents, local dev |

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

## Architecture — Local-First

```
Your Machine (localhost:8000)                    DevSwat Platform (HTTPS)
──────────────────────────────────               ──────────────────────────────────

┌────────────────────────────────┐               ┌──────────────────────┐
│  OpenClaw Connector (this repo)│               │  HTTPS Gateway       │
│                                │               │  (dev-swat.com:443)  │
│  LOCAL EXECUTION:              │               └──────────┬───────────┘
│  ┌───────────────────────┐     │                          │
│  │ web_search (DuckDuckGo)│    │               ┌──────────▼───────────┐
│  │ fetch_url (httpx+BS4) │     │               │  Agent Engine         │
│  │ deep_research (local) │     │  LLM call     │                      │
│  │ memory_write (SQLite) │     │──────────────►│  LLM Service          │
│  │ memory_read  (SQLite) │     │◄──────────────│  (Groq/OpenAI/etc)    │
│  │ execute_code (subproc)│     │               │                      │
│  └───────────────────────┘     │  step report  │  Receives:           │
│                                │──────────────►│  - Tool name + timing │
│  CLOUD FALLBACK ONLY:          │               │  - Final answer only  │
│  google_calendar ─────────────►│  result       │  - "ran_locally: true"│
│  gmail_send ──────────────────►│──────────────►│                      │
│  image_generation ────────────►│               │  Does NOT receive:    │
│  slack_send ──────────────────►│               │  - Memory content     │
│                                │               │  - Search results     │
│  LOCAL STORAGE:                │               │  - Fetched pages      │
│  ~/.openclaw/data/memory.db    │               │  - Code output        │
│  (SQLite + FTS5 full-text)     │               └──────────────────────┘
└────────────────────────────────┘
```

### What runs WHERE

| Category | Tool | Runs On | Data Stored |
|----------|------|---------|-------------|
| 🟢 Search | `web_search` | **Your machine** | Your machine only |
| 🟢 Fetch | `fetch_url`, `read_webpage` | **Your machine** | Your machine only |
| 🟢 Research | `deep_research` | **Your machine** | Your machine only |
| 🟢 Memory | `memory_write`, `memory_read` | **Your machine** | `~/.openclaw/data/memory.db` |
| 🟢 Code | `execute_code` | **Your machine** | Your machine only |
| 🔵 Google | `google_calendar`, `gmail_send` | Platform server | Server (needs OAuth) |
| 🔵 Media | `generate_image`, `generate_audio` | Platform server | Server (needs GPU) |
| 🔵 Slack | `slack_send`, `slack_read` | Platform server | Server (needs OAuth) |
| 🔵 LLM | Chat completions | Platform server | Not stored |

### Outbound-Only Traffic

**ALL traffic is outbound from your machine. The platform NEVER connects to you.**

- **LLM calls (You → Platform)**: `POST /llm/chat/completions` → LLM service → response
- **Task polling (You → Platform)**: Every 5s, `GET /federation/tasks/poll` → returns pending task or null
- **Step reports (You → Platform)**: `POST /federation/tasks/{id}/step` → tool name + timing only
- **Result submission (You → Platform)**: `POST /federation/tasks/{id}/result` → final answer text only

> **Privacy**: Memory content, search results, fetched pages, and code output **never leave your machine**. The platform only knows which tools were called and the final answer.

> **Security**: Zero inbound connections. Works behind any firewall, NAT, VPN. JWT-authenticated HTTPS only. No tunnels needed. No ports exposed.

### How It Works

1. **Start connector**: `uvicorn app.main:app --port 8000 --reload` — starts connector + background polling
2. **Authenticate**: `POST /auth/login` with your dev-swat.com credentials — JWT stored at `~/.openclaw/tokens.json`
3. **Create agent**: Either from platform UI (+ Create → ⚡ Federated) or locally (`POST /agents/register`)
4. **Polling starts**: Connector polls `GET /federation/tasks/poll` every 5 seconds automatically
5. **Run from platform**: Click "Run" on your agent at dev-swat.com/agents → task queued → connector picks it up
6. **Local execution**: Tools run on YOUR machine (web_search → DuckDuckGo, memory → local SQLite)
7. **Live streaming**: Each tool call reports step metadata to platform UI (tool name + timing, no data)
8. **Result submitted**: `POST /federation/tasks/{id}/result` → only final answer sent to platform
9. **Memory persists locally**: All memories stay in `~/.openclaw/data/memory.db` on your disk
10. **Token auto-refresh**: JWT tokens refresh automatically — no manual re-authentication needed

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

### Memory — Local SQLite (Privacy-First)

All agent memory is stored **locally on your machine** in a SQLite database with FTS5 full-text search.

```
Location: ~/.openclaw/data/memory.db
Engine:   SQLite + FTS5 full-text search
Privacy:  Memory content NEVER sent to server
Persists: Across sessions, restarts, and updates
```

During agent execution, `memory_write` and `memory_read` are handled entirely locally:
- **Write**: Content + tags + metadata → SQLite + FTS5 index
- **Read**: FTS5 full-text search with relevance ranking
- **Step report to server**: Only says `"[memory_write — stored locally on user machine]"`

#### Legacy Cloud Memory Bridge (Optional)

If you need to sync specific memories to the platform's Hash Sphere (blockchain-verified):

```http
POST /memory/ingest
Content-Type: application/json

{
  "agent_id": "your-agent-uuid",
  "content": "Content to store on platform",
  "memory_type": "semantic",
  "tags": ["preference"]
}
```

> **Note**: This is opt-in. By default, all agent memory stays local.

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

## Local-First Execution Model

OpenClaw uses a **local-first** architecture. Most tools run directly on your machine. Only cloud-only tools (requiring OAuth credentials or GPU) fall back to the platform server.

### Tool Execution Flow
```
LLM decides to call "web_search"
  → OpenClaw checks: is this a local tool? YES
  → Executes DuckDuckGo search on YOUR machine
  → Result stays on your machine
  → Step report to server: {tool_name: "web_search", ran_locally: true}
  → LLM sees result, picks next tool

LLM decides to call "gmail_send"
  → OpenClaw checks: is this a local tool? NO (needs OAuth)
  → Falls back to platform server: POST /tools/execute
  → Server executes via Google API
  → Result returned to your agent
```

### Privacy Guarantees

| Data Type | Stored Where | Sent to Server? |
|-----------|-------------|----------------|
| Memory content | `~/.openclaw/data/memory.db` | ❌ Never |
| Search results | In-memory only (during task) | ❌ Never |
| Fetched page content | In-memory only | ❌ Never |
| Code execution output | In-memory only | ❌ Never |
| Tool name + timing | — | ✅ Step reports |
| Final answer text | — | ✅ Result submission |

---

## File Structure

```
RG_OpenClaw/
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI app + root status page + startup/shutdown
│   ├── config.py           # Environment config (LOCAL_DATA_DIR, service URLs)
│   ├── models.py           # Request/response Pydantic models
│   ├── platform_auth.py    # JWT auth — login, token storage at ~/.openclaw/tokens.json
│   ├── local_tools.py      # ⚡ LOCAL tool implementations (web_search, fetch_url, memory, code exec)
│   └── routers.py          # All endpoints + ReAct agent loop with local-first execution
├── Dockerfile             # Production container (python:3.11-slim)
├── requirements.txt       # FastAPI, httpx, pydantic, duckduckgo-search, beautifulsoup4, aiosqlite
├── .env.example           # Example config (defaults work out of the box)
├── LICENSE.txt
└── README.md              # This file

Local data (created automatically):
~/.openclaw/
├── data/
│   └── memory.db          # SQLite + FTS5 — all agent memories stored locally
└── tokens.json            # JWT auth tokens (chmod 600)
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
| `POST` | `/memory/ingest` | (Legacy) Store memory in platform Hash Sphere |
| `POST` | `/memory/query` | (Legacy) Query platform Hash Sphere |
| `POST` | `/task/execute` | Receive and execute platform-dispatched tasks |
| `GET` | `/manifest` | Agent manifest for marketplace |

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

Yes. Tools execute **locally on your machine**. Memory is stored in **local SQLite** on your disk. The platform server only receives the tool name + timing for live UI updates, and the final answer text. No memory content, no search results, no fetched pages are sent to the server. Full source on GitHub — audit every HTTP call.

### Where is my data stored?

**On your machine.** Memory goes to `~/.openclaw/data/memory.db` (SQLite). Search results, fetched pages, and code output stay in RAM during the task and are never persisted on the server. Only the final answer text is sent to the platform for display in the UI.

### Do I need to pay?

No. The connector is free. A free dev-swat.com account gives you LLM access (Groq). Local tools (web search, memory, code exec, fetch URL) cost nothing — they run on your machine. Cloud-only tools (Google integrations, image generation) may consume platform credits.

### Can I use my own LLM?

Currently, LLM calls go through the platform's LLM service (Groq, OpenAI, etc.). Local LLM support (Ollama, LM Studio) is planned for a future release.

### What if the platform goes down?

Local tools (web_search, fetch_url, memory, code exec) will still work since they run on your machine. Only LLM calls and cloud-only tools will fail gracefully. When the platform comes back, everything reconnects automatically.

### Can I disconnect at any time?

Yes. Stop the connector and your agent goes back to local-only mode. Your memory persists in `~/.openclaw/data/memory.db` — nothing is lost. No lock-in, no data retention requirements.

---

## Contributing

This project is part of the [DevSwat-ResonantGenesis](https://github.com/DevSwat-ResonantGenesis) organization.

- **Bug reports**: Open an issue on GitHub
- **Feature requests**: Open an issue with the `enhancement` label
- **Pull requests**: Welcome for bug fixes and improvements

---

**Organization**: [DevSwat-ResonantGenesis](https://github.com/DevSwat-ResonantGenesis) | **Platform**: [dev-swat.com](https://dev-swat.com) | **OpenClaw Page**: [dev-swat.com/openclaw](https://dev-swat.com/openclaw)
