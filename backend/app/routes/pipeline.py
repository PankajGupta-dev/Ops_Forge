"""
Pipeline Routes — OpsForge End-to-End Orchestration API.

POST /pipeline/run
    Accepts a PipelineRequest (description + Dockerfile + simulate_failure flag).
    Executes the full pre-approval pipeline:
      Agent 1 → Agent 2 → Agent 3 (+ Agent 5) → Agent 4 (plan only)
    Returns a WorkflowResult in AWAITING_APPROVAL state.

    The response includes a recovery_action_id. Use the existing recovery
    endpoints to drive operator approval and infrastructure execution:
      POST /recovery/{recovery_action_id}/approve
      POST /recovery/{recovery_action_id}/execute

GET /pipeline/status/{trace_id}
    Retrieve a previously-executed WorkflowResult from the in-process cache.
"""

from fastapi import APIRouter, HTTPException, status

from app.schemas.orchestration import PipelineRequest, WorkflowResult
from app.services.orchestrator_service import orchestrator_service
from app.utils.logger import get_logger

logger = get_logger()

router = APIRouter(
    prefix="/pipeline",
    tags=["E2E Orchestration Pipeline (Agents 1–5)"],
)


@router.post(
    "/run",
    response_model=WorkflowResult,
    status_code=status.HTTP_200_OK,
    summary="Execute the full OpsForge deployment and incident response pipeline",
    description=(
        "Runs the complete end-to-end pipeline in a single call:\n\n"
        "1. **PLAN** — Agent 1 parses the Dockerfile and generates a DeploymentPlan\n"
        "2. **DEPLOY** — Agent 2 provisions infrastructure and deploys the application\n"
        "3. **RCA** — Agent 3 collects telemetry, runs root cause analysis, and queries "
        "Agent 5 Knowledge Memory for similar historical incidents\n"
        "4. **RECOVERY_PLAN** — Agent 3 hands off to Agent 4, which generates a ranked "
        "recovery plan with voice narration\n\n"
        "Returns a `WorkflowResult` in `awaiting_approval` state. The `recovery_action_id` "
        "field identifies the pending RecoveryAction. Submit operator approval via "
        "`POST /recovery/{recovery_action_id}/approve`, then execute via "
        "`POST /recovery/{recovery_action_id}/execute`."
    ),
)
async def run_pipeline(request: PipelineRequest) -> WorkflowResult:
    """
    POST /pipeline/run

    Body: PipelineRequest
    Returns: WorkflowResult
    """
    if not request.description or not request.description.strip():
        raise HTTPException(status_code=400, detail="description cannot be empty.")
    if not request.dockerfile or not request.dockerfile.strip():
        raise HTTPException(status_code=400, detail="dockerfile cannot be empty.")

    logger.info(
        f"POST /pipeline/run | simulate_failure={request.simulate_failure} | "
        f"description='{request.description[:60]}...'"
    )

    return await orchestrator_service.run(request)


@router.get(
    "/status/{trace_id}",
    response_model=WorkflowResult,
    status_code=status.HTTP_200_OK,
    summary="Retrieve the status and result of a pipeline run by trace ID",
    description=(
        "Looks up a previously-executed pipeline run using its globally unique trace ID. "
        "Returns the full WorkflowResult including per-stage timing, outputs, and the "
        "current recovery_action status."
    ),
)
async def get_pipeline_status(trace_id: str) -> WorkflowResult:
    """
    GET /pipeline/status/{trace_id}

    Returns cached WorkflowResult if found.
    """
    workflow = orchestrator_service.get_workflow(trace_id)
    if not workflow:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No pipeline run found for trace_id='{trace_id}'. "
                "Pipeline results are stored in-process and will not survive server restarts."
            ),
        )
    logger.info(f"GET /pipeline/status/{trace_id} | status='{workflow.workflow_status}'")
    return workflow
