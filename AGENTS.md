# ClimaSync.AI — AI Agents: Change Log & Complete Run Guide

> **Scope:** This document covers the AI agent pipeline added to `Backend_ClimaSync.AI` and provides a step-by-step guide to run the entire ClimaSync.AI platform — Data Collection Service, Backend API, AI Agents, and Frontend.

---

## Table of Contents

1. [What Changed](#1-what-changed)
2. [Agent Architecture Overview](#2-agent-architecture-overview)
3. [New Files Created](#3-new-files-created)
4. [Modified Files](#4-modified-files)
5. [Complete Run Guide](#5-complete-run-guide)
   - [Prerequisites](#prerequisites)
   - [Service 1 — Data Collection (Port 8000)](#service-1--data-collection-port-8000)
   - [Service 2 — Backend API + Agents (Port 8001)](#service-2--backend-api--agents-port-8001)
   - [Service 3 — Frontend (Port 3000)](#service-3--frontend-port-3000)
6. [Using the Agent Endpoints](#6-using-the-agent-endpoints)
7. [Environment Variables Reference](#7-environment-variables-reference)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. What Changed

### Summary

A **4-agent AI pipeline** was added to the backend (`Backend_ClimaSync.AI`) using the **OpenAI SDK** (`gpt-4o-mini`). The pipeline is triggered via a single HTTP call and automates the full disaster response workflow:

| Step | Agent | LLM? | What it does |
|------|-------|------|-------------|
| 1 | Data Extraction Agent | ❌ No | Fetches disaster event from DB, live weather from Open-Meteo, seismic/flood sensor data, and nearby verified NGOs |
| 2 | Risk Analysis Agent | ✅ Yes | Classifies risk level (`low/medium/high/critical`), scores severity, estimates affected population; writes back to DB |
| 3 | Task Definer Agent | ✅ Yes | Generates 3–8 actionable tasks (`ambulance`, `boat`, `medical`, `food`, `evacuation`, `shelter`); inserts into `tasks` table as `pending_approval` |
| 4 | Task Allocator Agent | ✅ Yes | Matches tasks to NGOs by resource capability and proximity; updates tasks to `pending_acceptance`; creates notifications for each NGO |

**Total LLM calls per pipeline run: 3** (Agents 2, 3, and 4 each make one call).

---

## 2. Agent Architecture Overview

```
POST /api/v1/agents/analyze/{event_id}
        │
        ▼
┌─────────────────────────┐
│  Agent 1                │  Pure DB + HTTP data fetch
│  DataExtractionAgent    │  • DisasterEvent row (Supabase)
│                         │  • Live weather (Open-Meteo API)
│                         │  • Sensor data (Data Collection svc)
│                         │  • Verified NGOs + their resources
└──────────┬──────────────┘
           │ DisasterContext
           ▼
┌─────────────────────────┐
│  Agent 2                │  1 LLM call → JSON mode
│  RiskAnalysisAgent      │  • Classifies risk_level
│                         │  • Sets severity_score
│                         │  • Writes back to disaster_events
└──────────┬──────────────┘
           │ RiskReport
           ▼
┌─────────────────────────┐
│  Agent 3                │  1 LLM call → JSON mode
│  TaskDefinerAgent       │  • Generates task list (3–8 tasks)
│                         │  • Inserts into tasks table
│                         │    status = 'pending_approval'
│                         │    created_by_type = 'ai'
└──────────┬──────────────┘
           │ List[PersistedTask]
           ▼
┌─────────────────────────┐
│  Agent 4                │  1 LLM call → JSON mode
│  TaskAllocatorAgent     │  • Matches tasks → NGOs by resources
│                         │  • Updates tasks: assigned_ngo_id
│                         │    status = 'pending_acceptance'
│                         │  • Creates notifications for NGOs
└─────────────────────────┘
           │ AllocationMap
           ▼
    AgentPipelineResult (returned to caller)
```

---

## 3. New Files Created

All new files live in `Backend_ClimaSync.AI/app/modules/agents/`:

| File | Purpose |
|------|---------|
| `__init__.py` | Package marker |
| `schemas.py` | All Pydantic I/O types: `DisasterContext`, `RiskReport`, `TaskDefinition`, `AllocationMap`, `AgentPipelineResult` |
| `base_agent.py` | Shared `AsyncOpenAI` client (singleton), JSON-mode LLM caller with exponential-backoff retries (3 attempts), prompt serialiser |
| `data_extraction_agent.py` | Agent 1 — DB queries (PostGIS coords, NGO resources), Open-Meteo weather, sensor data from Data Collection svc |
| `risk_analysis_agent.py` | Agent 2 — Pakistan-context risk analyst prompt, parses `RiskReport`, updates `disaster_events` row |
| `task_definer_agent.py` | Agent 3 — Emergency coordinator prompt, generates task list, raw SQL INSERT into `tasks` table |
| `task_allocator_agent.py` | Agent 4 — Logistics coordinator prompt, NGO resource matching, updates tasks + inserts `notifications` |
| `orchestrator.py` | Chains all 4 agents in sequence, returns `AgentPipelineResult` |
| `router.py` | FastAPI router with 4 endpoints (full pipeline + 3 debug endpoints) |

---

## 4. Modified Files

### `Backend_ClimaSync.AI/app/core/config.py`

Added four new settings:

```python
# --- AI Agents ---
OPENAI_API_KEY: str = ""
OPENAI_MODEL: str = "gpt-4o-mini"
OPENAI_TIMEOUT_SECONDS: int = 60
DATA_COLLECTION_BASE_URL: str = "http://localhost:8000"

# Kill switch
MODULE_AGENTS_ENABLED: bool = True
```

### `Backend_ClimaSync.AI/app/main.py`

Registered the agents router:

```python
from app.modules.agents.router import router as agents_router
# ...
app.include_router(agents_router, prefix=prefix, dependencies=[Depends(require_module_active("agents"))])
```

### `Backend_ClimaSync.AI/.env`

Added agent environment variables (you must fill in `OPENAI_API_KEY`):

```env
# --- AI Agents ---
OPENAI_API_KEY=         ← fill this in
OPENAI_MODEL=gpt-4o-mini
OPENAI_TIMEOUT_SECONDS=60
DATA_COLLECTION_BASE_URL=http://localhost:8000
MODULE_AGENTS_ENABLED=true
```

### `Backend_ClimaSync.AI/pyproject.toml`

`httpx` was promoted from dev-only to a main dependency (needed by Agent 1 for HTTP calls to Open-Meteo and the Data Collection service).

---

## 5. Complete Run Guide

### Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Python | ≥ 3.12 | `python --version` |
| `uv` (Python package manager) | latest | `uv --version` |
| Node.js | ≥ 18 | `node --version` |
| npm | ≥ 9 | `npm --version` |
| OpenAI API key | — | From [platform.openai.com](https://platform.openai.com) |

> **Ports used:**
> - `8000` — Data Collection Service
> - `8001` — Backend API (includes Agents)
> - `3000` — Frontend (Next.js)

---

### Service 1 — Data Collection (Port 8000)

The Data Collection service monitors Pakistan for seismic, flood, and weather events and dispatches alerts to the backend.

**Step 1 — Install dependencies**
```powershell
cd d:\fyp\Data_collection
uv sync
```

**Step 2 — Verify `.env`**

The `.env` file at `d:\fyp\.env` (root) or `d:\fyp\Data_collection\.env` should have:
```env
APP_PORT=8000
DATABASE_URL=<your-supabase-connection-string>
GOOGLE_FLOOD_HUB_API_KEY=<your-key>
MAIN_SYSTEM_BASE_URL=http://localhost:8001
```

**Step 3 — Start the service**
```powershell
cd d:\fyp\Data_collection
uv run python main.py
```

Or with uvicorn directly:
```powershell
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Verify:** Open `http://localhost:8000/docs` — Swagger UI should load.

---

### Service 2 — Backend API + Agents (Port 8001)

This is the main FastAPI backend. It includes all business logic, authentication, task management, NGO management, and the new AI agent pipeline.

**Step 1 — Install dependencies**
```powershell
cd d:\fyp\Backend_ClimaSync.AI
uv sync
```

**Step 2 — Add your OpenAI API key to `.env`**

Open `d:\fyp\Backend_ClimaSync.AI\.env` and set:
```env
OPENAI_API_KEY=sk-proj-...your-key-here...
```

> Get a key from: https://platform.openai.com/api-keys
> The pipeline uses `gpt-4o-mini` by default (very cost-efficient — ~3 calls per disaster event analysis).

**Step 3 — Start the backend**
```powershell
cd d:\fyp\Backend_ClimaSync.AI
uv run uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8001 --reload
```

**Verify:**
- `http://localhost:8001/health` → `{"status": "healthy", "version": "0.1.0"}`
- `http://localhost:8001/docs` → Swagger UI with all routes including `/api/v1/agents/*`

---

### Service 3 — Frontend (Port 3000)

The Next.js frontend (React 19 + Mapbox GL + Framer Motion).

**Step 1 — Install dependencies**
```powershell
cd d:\fyp\front-end-ClimasyncAI
npm install
```

**Step 2 — Verify `.env.local`**

Check `d:\fyp\front-end-ClimasyncAI\.env.local`:
```env
NEXT_PUBLIC_MAPBOX_TOKEN="pk.eyJ1..."
NEXT_PUBLIC_API_BASE_URL="http://localhost:8001/api/v1"
```

> ⚠️ The frontend should point to the **backend** (port 8001), not the data collection service.
> If it currently shows `8000`, update it to `8001`.

**Step 3 — Start the frontend**
```powershell
cd d:\fyp\front-end-ClimasyncAI
npm run dev
```

**Verify:** Open `http://localhost:3000` — the ClimaSync.AI dashboard should load.

---

### Running All 3 Services Together

Open **3 separate PowerShell terminals** and run one command in each:

```powershell
# Terminal 1 — Data Collection
cd d:\fyp\Data_collection
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 — Backend + Agents
cd d:\fyp\Backend_ClimaSync.AI
uv run uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8001 --reload

# Terminal 3 — Frontend
cd d:\fyp\front-end-ClimasyncAI
npm run dev
```

---

## 6. Using the Agent Endpoints

All agent endpoints are available in the Swagger UI at `http://localhost:8001/docs` under the **AI Agents** section.

### Full Pipeline (recommended)

```http
POST http://localhost:8001/api/v1/agents/analyze/{event_id}
```

Replace `{event_id}` with a valid UUID from the `disaster_events` table.

**Example response:**
```json
{
  "event_id": "3f7c8b12-...",
  "risk_report": {
    "risk_level": "high",
    "severity_score": 7.5,
    "affected_population_estimate": 45000,
    "estimated_damage_pkr": 50000000,
    "key_risk_factors": ["high rainfall", "dense population", "flash flood risk"],
    "recommended_response_window_hours": 12,
    "confidence": 0.87,
    "reasoning": "The Swat Valley event..."
  },
  "tasks_created": 5,
  "tasks_allocated": 4,
  "unallocated_task_ids": ["a1b2c3..."],
  "allocation_summary": "4 of 5 tasks assigned to 3 NGOs..."
}
```

### Debug Endpoints

| Endpoint | What it runs | Useful for |
|----------|-------------|-----------|
| `POST /api/v1/agents/extract/{event_id}` | Agent 1 only | Testing DB connectivity + weather fetch |
| `POST /api/v1/agents/risk/{event_id}` | Agents 1 + 2 | Checking risk classification without writing tasks |
| `POST /api/v1/agents/tasks/{event_id}` | Agents 1 + 2 + 3 | Creating tasks without allocation |

### Getting a valid `event_id`

Query the database or use the existing disasters API:
```http
GET http://localhost:8001/api/v1/disasters
Authorization: Bearer <your-jwt-token>
```

---

## 7. Environment Variables Reference

### Backend (`Backend_ClimaSync.AI/.env`)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | ✅ | — | PostgreSQL connection string (Supabase) |
| `SECRET_KEY` | ✅ | — | JWT signing secret |
| `OPENAI_API_KEY` | ✅ | `""` | OpenAI API key for agent LLM calls |
| `OPENAI_MODEL` | ❌ | `gpt-4o-mini` | OpenAI model to use |
| `OPENAI_TIMEOUT_SECONDS` | ❌ | `60` | Timeout per LLM call |
| `DATA_COLLECTION_BASE_URL` | ❌ | `http://localhost:8000` | Data Collection service URL |
| `MODULE_AGENTS_ENABLED` | ❌ | `true` | Kill switch for agent endpoints |

### Data Collection (`Data_collection/.env` or root `.env`)

| Variable | Required | Description |
|----------|----------|-------------|
| `APP_PORT` | ❌ | Port to run on (default `8000`) |
| `GOOGLE_FLOOD_HUB_API_KEY` | ✅ | Google Flood Hub API key |
| `MAIN_SYSTEM_BASE_URL` | ✅ | URL of the Backend API (e.g. `http://localhost:8001`) |

### Frontend (`front-end-ClimasyncAI/.env.local`)

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_BASE_URL` | ✅ | Backend API base URL (should be `http://localhost:8001/api/v1`) |
| `NEXT_PUBLIC_MAPBOX_TOKEN` | ✅ | Mapbox GL public token for map rendering |

---

## 8. Troubleshooting

### `OPENAI_API_KEY` not set
```
openai.AuthenticationError: No API key provided
```
**Fix:** Add `OPENAI_API_KEY=sk-...` to `Backend_ClimaSync.AI/.env`.

---

### `DisasterEvent {id} not found`
```json
{"detail": "DisasterEvent <uuid> not found"}
```
**Fix:** Make sure the event_id exists in the `disaster_events` table. Use `GET /api/v1/disasters` to find valid IDs.

---

### No NGOs found / all tasks unallocated
The allocator requires NGOs with `verification_status = 'verified'` in `ngo_profiles`. If the DB has no verified NGOs, Agent 4 will return all tasks in `unallocated_task_ids`.

**Fix:** Seed some NGO data or verify existing NGOs via the Admin panel.

---

### Weather fetch fails (Agent 1)
If Open-Meteo is unreachable, Agent 1 returns `{"error": "...", "source": "open-meteo"}` in `weather_summary` — the pipeline continues without weather context. This is a soft failure.

---

### Sensor data fetch fails (Agent 1)
If the Data Collection service is not running, the `sensor_readings` field will contain `{"error": "...", "event_type": "..."}` — again a soft failure. The remaining agents still run.

---

### `MODULE_AGENTS_ENABLED=false` returns 503
If you deliberately disabled the agents module, set `MODULE_AGENTS_ENABLED=true` in `.env` and restart the backend.

---

### Port conflicts
| Symptom | Fix |
|---------|-----|
| Port 8000 in use | Stop the existing process or change `APP_PORT` in Data Collection `.env` |
| Port 8001 in use | Change the `--port` flag in the uvicorn command |
| Port 3000 in use | Next.js will auto-select 3001 — update `NEXT_PUBLIC_API_BASE_URL` if needed |

---

*Last updated: 2026-05-07 | Author: AI-assisted via Antigravity*
