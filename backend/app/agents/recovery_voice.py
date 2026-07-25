from typing import Optional
from app.schemas.incident import IncidentReport
from app.schemas.recovery import RecoveryAction, RecoveryApprovalRequest
from app.services.recovery_service import RecoveryService
from app.agents.knowledge_memory import KnowledgeMemoryAgent
from app.integrations.gemini_client import GeminiClient
from app.integrations.elevenlabs_client import ElevenLabsClient
from app.integrations.railway_client import RailwayClient
from app.utils.logger import get_logger

logger = get_logger()

class RecoveryVoiceAgent:
    """
    Agent 4: Recovery & Voice Approval Agent.
    
    Coordinates:
      1. Parsing IncidentReports and selecting the top recovery plan.
      2. Generating a voice script and synthesis with ElevenLabs.
      3. Processing UI / voice operator approvals.
      4. Safe infrastructure action execution via Railway.
      5. Post-recovery incident memory storage in Agent 5 Knowledge Memory.
    """
    def __init__(
        self,
        gemini_client: Optional[GeminiClient] = None,
        elevenlabs_client: Optional[ElevenLabsClient] = None,
        railway_client: Optional[RailwayClient] = None,
        infra_agent: Optional[object] = None,
        knowledge_agent: Optional[KnowledgeMemoryAgent] = None
    ) -> None:
        self.recovery_service = RecoveryService(
            gemini_client=gemini_client,
            elevenlabs_client=elevenlabs_client,
            railway_client=railway_client,
            infra_agent=infra_agent,
            knowledge_agent=knowledge_agent
        )


    async def create_recovery_plan(self, report: IncidentReport) -> RecoveryAction:
        """
        Generates the detailed recovery steps and TTS audio.
        """
        logger.info(f"Agent 4 invoked: generating plan for deployment '{report.deployment_id}' ({report.app_name}).")
        return await self.recovery_service.generate_recovery_plan(report)

    def process_approval(self, action_id: str, request: RecoveryApprovalRequest) -> RecoveryAction:
        """
        Approves or rejects a cached recovery action.
        """
        logger.info(f"Agent 4: Processing approval status change for '{action_id}' (approved: {request.approved}).")
        return self.recovery_service.approve_action(action_id, request)

    async def execute_recovery(self, action_id: str) -> RecoveryAction:
        """
        Triggers step execution and automated verification.
        """
        logger.info(f"Agent 4: Executing recovery action pipeline for '{action_id}'.")
        return await self.recovery_service.execute_action(action_id)
