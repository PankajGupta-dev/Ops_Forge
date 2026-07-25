from fastapi import APIRouter, HTTPException, Response, status
from app.schemas.incident import IncidentReport
from app.schemas.recovery import RecoveryAction, RecoveryApprovalRequest
from app.agents.recovery_voice import RecoveryVoiceAgent
from app.utils.logger import get_logger

logger = get_logger()

router = APIRouter(prefix="/recovery", tags=["Agent 4 — Recovery & Voice Approval"])

# Instantiate the recovery agent
_agent = RecoveryVoiceAgent()

@router.post(
    "/plan",
    response_model=RecoveryAction,
    status_code=status.HTTP_201_CREATED,
    summary="Generate recovery action plan and narration",
    description="Consumes an IncidentReport, creates a recommended RecoveryAction with steps, and starts voice synthesis."
)
async def create_plan(report: IncidentReport) -> RecoveryAction:
    if not report.deployment_id or not report.deployment_id.strip():
        raise HTTPException(status_code=400, detail="deployment_id is required.")
    
    logger.info(f"POST /recovery/plan received for deployment {report.deployment_id}")
    return await _agent.create_recovery_plan(report)

@router.get(
    "/{action_id}",
    response_model=RecoveryAction,
    summary="Get status of a recovery action",
    description="Retrieves the current execution status and details of a recovery action by ID."
)
async def get_action(action_id: str) -> RecoveryAction:
    action = _agent.recovery_service.get_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail=f"RecoveryAction with ID '{action_id}' not found.")
    return action

@router.post(
    "/{action_id}/approve",
    response_model=RecoveryAction,
    summary="Submit operator approval",
    description="Submits the operator decision to approve or reject a pending recovery strategy."
)
async def approve_action(action_id: str, request: RecoveryApprovalRequest) -> RecoveryAction:
    logger.info(f"POST /recovery/{action_id}/approve received. Decision approved={request.approved}")
    return _agent.process_approval(action_id, request)

@router.post(
    "/{action_id}/execute",
    response_model=RecoveryAction,
    summary="Execute approved recovery action",
    description="Triggers deployment/restart/scale steps against Railway if the action was approved."
)
async def execute_action(action_id: str) -> RecoveryAction:
    logger.info(f"POST /recovery/{action_id}/execute received.")
    return await _agent.execute_recovery(action_id)

@router.get(
    "/{action_id}/audio",
    summary="Retrieve generated narration audio file",
    description="Streams the generated ElevenLabs TTS audio MP3 for the voice approval agent."
)
async def get_audio(action_id: str):
    audio_bytes = _agent.recovery_service.get_audio(action_id)
    if not audio_bytes:
        raise HTTPException(
            status_code=404, 
            detail=f"Audio narration for RecoveryAction '{action_id}' not found or synthesis failed."
        )
    return Response(content=audio_bytes, media_type="audio/mpeg")
