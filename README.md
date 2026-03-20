# RG OpenClaw

> **Part of the [ResonantGenesis](https://dev-swat.com) platform** — OpenClaw ↔ ResonantGenesis agent integration service.

[![Status: Production](https://img.shields.io/badge/Status-Production-brightgreen.svg)]()
[![Port: 8000](https://img.shields.io/badge/Port-8000-orange.svg)]()
[![License: RG Source Available](https://img.shields.io/badge/License-RG%20Source%20Available-blue.svg)](LICENSE.txt)

Standalone microservice for managing OpenClaw ↔ ResonantGenesis connections via webhooks. Fully isolated — no shared DB, no shared imports. Can be enabled/disabled via `OPENCLAW_SERVICE_ENABLED` env var without affecting any other service.

## Architecture

```
Gateway → /openclaw/* → openclaw_service:8000
                            ├── Webhook management
                            ├── Agent connection routing
                            └── HTTP calls to agent_engine_service, auth_service
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `AGENT_ENGINE_URL` | Internal URL for agent engine |
| `AUTH_SERVICE_URL` | Internal URL for auth service |
| `PLATFORM_DOMAIN` | Platform domain (default: resonantgenesis.xyz) |
| `INTERNAL_SERVICE_KEY` | Internal service authentication key |
| `OPENCLAW_SERVICE_ENABLED` | Enable/disable service (default: true) |

## Quick Start

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Deployment Status

- **Extracted from**: `genesis2026_production_backend/openclaw_service/`
- **Server path**: `/home/deploy/RG_OpenClaw`
- **Docker service**: `openclaw_service`

---
**Organization**: [DevSwat-ResonantGenesis](https://github.com/DevSwat-ResonantGenesis) | **Platform**: [dev-swat.com](https://dev-swat.com)
