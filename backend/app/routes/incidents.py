"""
Incident Routes — Agent 3 (Telemetry & Root Cause Agent)

POST /incident/analyze
  Accept raw telemetry → run Agent 3 pipeline → return IncidentReport JSON.

POST /incident/analyze-and-handoff
  Accept raw telemetry → run Agent 3 pipeline → automatically hand off to Agent 4 (Recovery & Voice) → return RecoveryAction JSON.
"""

from fastapi import APIRouter, HTTPException, status
from app.schemas.incident import IncidentAnalysisRequest, IncidentReport
from app.schemas.recovery import RecoveryAction
from app.agents.root_cause import RootCauseAgent
from app.utils.logger import get_logger

logger = get_logger()

router = APIRouter(prefix="/incident", tags=["Agent 3 — Root Cause Analysis"])

# Single process-wide instance
_agent = RootCauseAgent()


@router.post(
    "/analyze",
    response_model=IncidentReport,
    status_code=status.HTTP_200_OK,
    summary="Trigger root cause analysis for a deployment",
    description=(
        "Accepts deployment telemetry (logs, metrics, events), runs rule-based "
        "incident detection and correlation, queries Agent 5 Knowledge Memory, and "
        "uses Gemini to produce a ranked IncidentReport with recovery recommendations."
    ),
)
async def analyze_incident(request: IncidentAnalysisRequest) -> IncidentReport:
    """
    POST /incident/analyze

    Body: IncidentAnalysisRequest
    Returns: IncidentReport
    """
    if not request.deployment_id or not request.deployment_id.strip():
        raise HTTPException(status_code=400, detail="deployment_id cannot be empty.")
    if not request.app_name or not request.app_name.strip():
        raise HTTPException(status_code=400, detail="app_name cannot be empty.")

    if not request.logs and not request.metrics and not request.events:
        raise HTTPException(
            status_code=400,
            detail="At least one of: logs, metrics, or events must be provided.",
        )

    logger.info(
        f"POST /incident/analyze received — deployment_id='{request.deployment_id}', app='{request.app_name}'"
    )

    return await _agent.run(request)


@router.post(
    "/analyze-and-handoff",
    response_model=RecoveryAction,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger root cause analysis and automatically hand off to Agent 4 Recovery",
    description=(
        "Accepts raw deployment telemetry, executes Agent 3 Root Cause Analysis, "
        "and automatically hands off the analysis payload to Agent 4 (Recovery & Voice Approval), "
        "returning a generated pending RecoveryAction with voice narration script and audio endpoint."
    ),
)
async def analyze_and_handoff(request: IncidentAnalysisRequest) -> RecoveryAction:
    """
    POST /incident/analyze-and-handoff

    Body: IncidentAnalysisRequest
    Returns: RecoveryAction
    """
    if not request.deployment_id or not request.deployment_id.strip():
        raise HTTPException(status_code=400, detail="deployment_id cannot be empty.")
    if not request.app_name or not request.app_name.strip():
        raise HTTPException(status_code=400, detail="app_name cannot be empty.")

    if not request.logs and not request.metrics and not request.events:
        raise HTTPException(
            status_code=400,
            detail="At least one of: logs, metrics, or events must be provided.",
        )

    logger.info(
        f"POST /incident/analyze-and-handoff received — deployment_id='{request.deployment_id}', app='{request.app_name}'"
    )

    _, action = await _agent.run_with_recovery_handoff(request)
    return action
