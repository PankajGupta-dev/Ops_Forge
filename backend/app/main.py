from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.deploy import router as deploy_router
from app.routes.incidents import router as incidents_router
from app.routes.recovery import router as recovery_router
from app.routes.memory import router as memory_router
from app.routes.pipeline import router as pipeline_router
from app.routes.auth import router as auth_router
from app.routes.monitor import router as monitor_router

app = FastAPI(
    title="OpsForge Backend API",
    description=(
        "OpsForge Autonomous AI Platform Engineer — "
        "Agent 1 (Deployment Planner) | Agent 2 (Infra & Deploy) | "
        "Agent 3 (Root Cause Analysis) | Agent 4 (Recovery & Voice) | "
        "Agent 5 (Knowledge Memory) | E2E Orchestration Pipeline | GitHub OAuth"
    ),
    version="3.0.0",
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth routes
app.include_router(auth_router)

# Agent routes
app.include_router(deploy_router)
app.include_router(incidents_router)
app.include_router(recovery_router)
app.include_router(memory_router)
app.include_router(monitor_router)

# E2E Orchestration Pipeline
app.include_router(pipeline_router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status":  "healthy",
        "service": "OpsForge Backend",
        "version": "3.0.0",
        "agents": {
            "agent_1": "active",
            "agent_2": "active",
            "agent_3": "active",
            "agent_4": "active",
            "agent_5": "active",
        },
        "auth": "active",
        "pipeline": "active",
    }

# Single-Link SPA Static File Handler (for Render / Docker single-port hosting)
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if not os.path.exists(static_dir):
    static_dir = os.path.join(os.getcwd(), "static")

if os.path.exists(static_dir):
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        file_path = os.path.join(static_dir, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)

