from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.deploy import router as deploy_router
from app.routes.incidents import router as incidents_router
from app.routes.recovery import router as recovery_router
from app.routes.memory import router as memory_router
from app.routes.pipeline import router as pipeline_router

app = FastAPI(
    title="OpsForge Backend API",
    description=(
        "OpsForge Autonomous AI Platform Engineer — "
        "Agent 1 (Deployment Planner) | Agent 2 (Infra & Deploy) | "
        "Agent 3 (Root Cause Analysis) | Agent 4 (Recovery & Voice) | "
        "Agent 5 (Knowledge Memory) | E2E Orchestration Pipeline"
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

# Agent routes
app.include_router(deploy_router)
app.include_router(incidents_router)
app.include_router(recovery_router)
app.include_router(memory_router)

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
        "pipeline": "active",
    }
