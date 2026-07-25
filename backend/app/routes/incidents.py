"""
Incident Routes — Agent 3 (Telemetry & Root Cause Agent)

POST /incident/analyze
  Accept raw telemetry → run Agent 3 pipeline → return IncidentReport JSON.
"""

from fastapi import APIRouter, HTTPException

from app.schemas.incident import IncidentAnalysisRequest, IncidentReport
from app.agents.root_cause import RootCauseAgent
from app.utils.logger import get_logger

logger = get_logger()

router = APIRouter(prefix="/incident", tags=["Agent 3 — Root Cause Analysis"])

# One instance per process (GeminiClient is stateless, safe to reuse).
_agent = RootCauseAgent()


@router.post(
    "/analyze",
    response_model=IncidentReport,
    summary="Trigger root cause analysis for a deployment",
    description=(
        "Accepts deployment telemetry (logs, metrics, events), runs rule-based "
        "incident detection and correlation, then queries Gemini to produce a "
        "ranked IncidentReport with recovery recommendations."
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
        f"POST /incident/analyze received — deployment_id='{request.deployment_id}'"
    )

    return await _agent.run(request)
