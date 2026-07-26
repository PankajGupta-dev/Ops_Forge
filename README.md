# OpsForge 🚀

**OpsForge** is an autonomous AI platform engineer — a multi-agent system that takes a deployment description and Dockerfile, and runs the complete lifecycle end-to-end: from deployment planning and infrastructure provisioning, through root cause analysis and voice-narrated recovery, to searchable knowledge memory.

> Built with FastAPI · React · Gemini · Railway · GHCR · MongoDB Atlas · ElevenLabs

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Agent Pipeline](#agent-pipeline)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Frontend Pages](#frontend-pages)
- [Running Tests](#running-tests)

---

## Overview

OpsForge replaces the traditional on-call engineer loop with five specialised AI agents that collaborate through a single orchestrated pipeline:

```
User Request
  → Agent 1: Parse & plan the deployment
  → Agent 2: Clone repo · Build image · Push to GHCR · Deploy to Railway
  → Agent 3: Collect telemetry · Run root cause analysis · Query knowledge base
  → Agent 4: Generate ranked recovery plan · Narrate via voice (ElevenLabs)
  → Agent 5: Store incident + resolution in MongoDB vector memory
```

The operator receives a recovery plan for approval. Once approved, Agent 4 triggers Agent 2 to execute the infrastructure fix, and Agent 5 persists the resolved incident for future similarity search.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                     OpsForge Frontend                   │
│          React + Vite + TypeScript (port 3000)          │
└─────────────────────┬───────────────────────────────────┘
                      │ REST / JSON
┌─────────────────────▼───────────────────────────────────┐
│                   OpsForge Backend                      │
│              FastAPI v3.0.0  (port 8000)                │
│                                                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ Agent 1  │ │ Agent 2  │ │ Agent 3  │ │ Agent 4  │  │
│  │ Planner  │→│  Infra   │→│   RCA    │→│ Recovery │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│                                   │             │       │
│                            ┌──────▼──────┐      │       │
│                            │  Agent 5    │      │       │
│                            │  Knowledge  │      │       │
│                            │  Memory     │      │       │
│                            └─────────────┘      │       │
└─────────────────────────────────────────────────┼───────┘
                                                  │
          ┌───────────────┬──────────────┬─────────┘
          ▼               ▼              ▼
     Railway API     GHCR / Docker   MongoDB Atlas
     (deployment)    (image registry) (vector memory)
          │               │
     ElevenLabs       Gemini API
     (voice TTS)      (LLM reasoning)
```

---

## Agent Pipeline

### Agent 1 — Deployment Planner
Parses the user's description and Dockerfile to generate a structured `DeploymentPlan` (application name, runtime, platform, region, strategy, replicas, database config, network ports).

### Agent 2 — Infra & Deploy
Executes the full container deployment pipeline:
1. `git clone` the target repository and checkout the specified branch
2. Validate or write the Dockerfile
3. `docker build` the image locally, tagged with a unique `trace_id`
4. Authenticate to **GitHub Container Registry (GHCR)** and `docker push`
5. Update the existing **Railway** service with the new image
6. Poll Railway until the deployment reaches a terminal state
7. Retrieve the real public deployment URL

### Agent 3 — Root Cause Analysis
After deployment, collects telemetry (logs, metrics, events), calls **Gemini** with a structured prompt to produce a ranked causal chain, severity score, confidence level, and recommendations. Queries Agent 5 for historically similar incidents.

### Agent 4 — Recovery & Voice
Receives the RCA report, generates a step-by-step recovery action plan ranked by risk level, and narrates it using **ElevenLabs TTS**. Waits for operator approval before executing.

### Agent 5 — Knowledge Memory
Persists every resolved incident as a vector document in **MongoDB Atlas**. Exposes a similarity search API used by Agent 3 to surface historical precedents.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, TypeScript |
| Backend | FastAPI, Python 3.12, Uvicorn |
| AI / LLM | Google Gemini API (`gemini-2.5-flash`) |
| Container Registry | GitHub Container Registry (GHCR) |
| Deployment Platform | Railway |
| Voice Synthesis | ElevenLabs |
| Database / Memory | MongoDB Atlas |
| Auth | GitHub OAuth 2.0 + JWT |

---

## Project Structure

```
Ops_Forge/
├── backend/
│   ├── app/
│   │   ├── agents/              # The 5 AI agents
│   │   │   ├── deployment_planner.py   # Agent 1
│   │   │   ├── infra_deploy.py         # Agent 2
│   │   │   ├── root_cause.py           # Agent 3
│   │   │   ├── recovery_voice.py       # Agent 4
│   │   │   └── knowledge_memory.py     # Agent 5
│   │   ├── integrations/        # External service clients
│   │   │   ├── gemini_client.py
│   │   │   ├── railway_client.py
│   │   │   ├── elevenlabs_client.py
│   │   │   └── mongodb_client.py
│   │   ├── routes/              # FastAPI routers
│   │   │   ├── pipeline.py      # POST /pipeline/run (E2E)
│   │   │   ├── deploy.py        # Agent 1 & 2 endpoints
│   │   │   ├── incidents.py     # Agent 3 endpoints
│   │   │   ├── recovery.py      # Agent 4 endpoints
│   │   │   ├── memory.py        # Agent 5 endpoints
│   │   │   └── auth.py          # GitHub OAuth
│   │   ├── services/            # Business logic
│   │   │   ├── orchestrator_service.py   # E2E pipeline engine
│   │   │   ├── deployment_service.py     # Agent 2 core logic
│   │   │   ├── pipeline_bridge_service.py
│   │   │   └── recovery_service.py
│   │   ├── schemas/             # Pydantic models
│   │   └── utils/               # Config, logger
│   └── tests/                   # Pytest integration tests
├── frontend/
│   └── src/
│       ├── pages/               # React pages
│       │   ├── Dashboard.tsx
│       │   ├── DeploymentPlanner.tsx
│       │   ├── DeploymentDetail.tsx
│       │   ├── RootCauseAnalysis.tsx
│       │   ├── RecoveryApproval.tsx
│       │   ├── RecoveryVerification.tsx
│       │   ├── IncidentFeed.tsx
│       │   ├── KnowledgeBase.tsx
│       │   └── PostmortemReport.tsx
│       ├── services/            # API service layer
│       └── components/          # Shared UI components
├── demo-app/                    # Sample deployable app
├── infra/                       # Infrastructure config
├── docs/                        # Architecture notes
├── scripts/                     # Dev helper scripts
├── docker-compose.yml
└── .env                         # Environment variables (see below)
```

---

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- Docker (for local image builds)
- Git

### 1. Clone the repository

```bash
git clone https://github.com/PankajGupta-dev/Ops_Forge.git
cd Ops_Forge
```

### 2. Configure environment variables

Copy `.env` and fill in your credentials (see [Environment Variables](#environment-variables)):

```bash
# Edit .env at the project root
```

### 3. Start the backend

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Backend will be available at `http://localhost:8000`  
Interactive API docs at `http://localhost:8000/docs`

### 4. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend will be available at `http://localhost:3000`

---

## Environment Variables

All variables go in the `.env` file at the project root.

```env
# GitHub OAuth
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITHUB_CALLBACK_URL=http://localhost:8000/auth/github/callback
FRONTEND_URL=http://localhost:3000
JWT_SECRET=
JWT_ALGORITHM=HS256

# Gemini (Google AI Studio — key must start with AIza...)
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-2.5-flash-preview-05-20

# MongoDB Atlas
MONGODB_ATLAS_URI=mongodb+srv://...

# ElevenLabs
ELEVENLABS_API_KEY=
ELEVENLABS_VOICE_ID=

# Railway (existing service — Agent 2 never creates new services)
RAILWAY_API_TOKEN=
RAILWAY_PROJECT_ID=
RAILWAY_SERVICE_ID=

# GitHub Container Registry (Agent 2 image push)
GHCR_USERNAME=
GHCR_TOKEN=

# Development flags
SKIP_AGENT4=false          # Set to true to skip Agent 4 in the pipeline

# Frontend
VITE_API_BASE_URL=http://localhost:8000
PORT=3000
```

> **Note:** The Gemini API key must start with `AIza`. Keys starting with `AQ.` are OAuth session tokens and will not work.

---

## API Reference

The full interactive API docs are at `http://localhost:8000/docs` when the backend is running.

### Key Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Backend health check, all agent statuses |
| `POST` | `/pipeline/run` | **Run the full E2E pipeline** (Agents 1–5) |
| `GET` | `/pipeline/status/{trace_id}` | Get pipeline result by trace ID |
| `POST` | `/deploy/plan` | Agent 1 — generate deployment plan |
| `POST` | `/deploy/execute` | Agent 2 — execute a deployment plan |
| `POST` | `/incidents/analyze` | Agent 3 — run root cause analysis |
| `GET` | `/recovery/{id}` | Agent 4 — get recovery action |
| `POST` | `/recovery/{id}/approve` | Agent 4 — operator approval |
| `POST` | `/recovery/{id}/execute` | Agent 4 → Agent 2 — execute recovery |
| `POST` | `/memory/store` | Agent 5 — store resolved incident |
| `POST` | `/memory/search` | Agent 5 — similarity search |
| `GET` | `/auth/github` | GitHub OAuth login |

### E2E Pipeline Request

```json
POST /pipeline/run
{
  "description": "Deploy a Node.js API with MongoDB",
  "dockerfile": "FROM node:18\nEXPOSE 8080\nCMD [\"node\", \"server.js\"]",
  "repository": "PankajGupta-dev/my-app",
  "branch": "main",
  "simulate_failure": false
}
```

### E2E Pipeline Response

```json
{
  "trace_id": "abc-123",
  "workflow_status": "awaiting_approval",
  "app_name": "my-app",
  "live_url": "https://my-app.up.railway.app",
  "severity": "high",
  "root_cause": "...",
  "confidence": 0.92,
  "recovery_action_id": "ra-xyz",
  "stages": [
    { "stage": "PLAN",          "status": "completed", "duration_ms": 1200 },
    { "stage": "DEPLOY",        "status": "completed", "duration_ms": 45000 },
    { "stage": "RCA",           "status": "completed", "duration_ms": 3100 },
    { "stage": "RECOVERY_PLAN", "status": "completed", "duration_ms": 2800 }
  ]
}
```

---

## Frontend Pages

| Page | Route | Description |
|---|---|---|
| Landing | `/` | Product overview and login |
| Dashboard | `/dashboard` | Live deployment health overview |
| Deployment Planner | `/deployments` | Trigger the full AI pipeline |
| Deployment Detail | `/deployments/:traceId` | Per-pipeline stage visualisation |
| Root Cause Analysis | `/rca/:traceId` | AI-generated causal chain and signals |
| Recovery Approval | `/recovery/:id` | Operator approval interface |
| Recovery Verification | `/recovery/:id/verify` | Post-recovery verification |
| Incident Feed | `/incidents` | Live incident stream |
| Knowledge Base | `/knowledge` | Historical incident search |
| Postmortem Report | `/postmortem/:id` | Auto-generated postmortem |

---

## Running Tests

```bash
cd backend
pytest tests/ -v
```

### Test suites

| File | Coverage |
|---|---|
| `test_agent1_agent2_integration.py` | Agent 1 → Agent 2 handoff |
| `test_agent2_simplified_deployment.py` | Full Agent 2 deployment pipeline |
| `test_agent2_agent3_integration.py` | Agent 2 → Agent 3 bridge |
| `test_agent2_agent4_integration.py` | Agent 4 → Agent 2 recovery execution |

All 14 tests pass in ~56 seconds.

---

## License

MIT
