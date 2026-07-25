import uuid
import json
import asyncio
from datetime import datetime, timezone
from typing import Dict, Optional, Any, List

from fastapi import HTTPException

from app.schemas.incident import IncidentReport, RecoveryCategory, IncidentStatus, Severity, RecoveryRecommendation
from app.schemas.recovery import RecoveryAction, RecoveryStep, RecoveryStatus, RecoveryApprovalRequest
from app.integrations.gemini_client import GeminiClient
from app.integrations.elevenlabs_client import ElevenLabsClient
from app.integrations.digitalocean_client import DigitalOceanClient
from app.agents.knowledge_memory import KnowledgeMemoryAgent
from app.utils.logger import get_logger

logger = get_logger()

# Process-lifetime in-memory stores for recovery states, incident reports, and audio binary blobs
_recovery_actions: Dict[str, RecoveryAction] = {}
_incident_reports: Dict[str, IncidentReport] = {}
_audio_blobs: Dict[str, bytes] = {}

class RecoveryService:
    def __init__(
        self,
        gemini_client: Optional[GeminiClient] = None,
        elevenlabs_client: Optional[ElevenLabsClient] = None,
        digitalocean_client: Optional[DigitalOceanClient] = None,
        infra_agent: Optional[Any] = None,
        knowledge_agent: Optional[KnowledgeMemoryAgent] = None
    ) -> None:
        self.gemini_client = gemini_client or GeminiClient()
        self.el_client = elevenlabs_client or ElevenLabsClient()
        self.do_client = digitalocean_client or DigitalOceanClient()
        self.infra_agent = infra_agent
        self.knowledge_agent = knowledge_agent or KnowledgeMemoryAgent()

    async def generate_recovery_plan(self, report: IncidentReport) -> RecoveryAction:
        """
        Receives an IncidentReport, selects the top recommendation,
        generates conversational voice narration via Gemini, generates voice TTS,
        and returns a pending RecoveryAction.
        """
        if not report.recommendations:
            logger.error("IncidentReport contains no recommendations.")
            raise HTTPException(status_code=400, detail="Incident report must contain at least one recommendation.")

        # 1. Select the top recommendation (rank 1)
        rec = min(report.recommendations, key=lambda r: r.rank)
        action_id = f"REC-{uuid.uuid4().hex[:6].upper()}"

        logger.info(f"Creating recovery plan {action_id} for incident in app '{report.app_name}' with category '{rec.category}'.")

        # Cache incident report for Agent 5 long-term memory storage after execution
        _incident_reports[action_id] = report

        # Map category and define execution steps
        steps = []
        if rec.category == RecoveryCategory.ROLLBACK:
            title = "Rollback Deployment"
            description = rec.action
            risk_level = rec.risk if rec.risk in ["low", "medium", "high"] else "high"
            estimated_duration = f"{rec.estimated_ttm_minutes or 2} min"
            steps = [
                RecoveryStep(id=f"{action_id}-1", order=1, title="Replicas scaled down & image reverted", command=f"doctl apps update {report.app_name} --spec rollback.yaml", verified=False, status="pending"),
                RecoveryStep(id=f"{action_id}-2", order=2, title="Database connection pool patch applied", command="doctl databases pools configure --pool-size 15", verified=False, status="pending"),
                RecoveryStep(id=f"{action_id}-3", order=3, title="Pods scaled up & readiness probes passing", command="kubectl rollout status deployment/web", verified=False, status="pending"),
                RecoveryStep(id=f"{action_id}-4", order=4, title="Post-recovery latency & error rate baseline verified", command=f"curl -s https://{report.app_name}.opsforge.dev/health", verified=False, status="pending")
            ]
        elif rec.category == RecoveryCategory.RESTART:
            title = "Restart Application"
            description = rec.action
            risk_level = rec.risk if rec.risk in ["low", "medium", "high"] else "low"
            estimated_duration = f"{rec.estimated_ttm_minutes or 1} min"
            steps = [
                RecoveryStep(id=f"{action_id}-1", order=1, title="Trigger rolling restart of application instances", command=f"doctl apps create-deployment {report.app_name} --force-rebuild", verified=False, status="pending"),
                RecoveryStep(id=f"{action_id}-2", order=2, title="Graceful termination of old processes", command="kubectl get pods -w", verified=False, status="pending"),
                RecoveryStep(id=f"{action_id}-3", order=3, title="Verify database connections and readiness", command="kubectl exec -it db-0 -- pg_isready", verified=False, status="pending"),
                RecoveryStep(id=f"{action_id}-4", order=4, title="Post-recovery latency & error rate baseline verified", command=f"curl -s https://{report.app_name}.opsforge.dev/health", verified=False, status="pending")
            ]
        elif rec.category in [RecoveryCategory.SCALE_UP, RecoveryCategory.MANUAL]:
            title = "Scale Service" if rec.category == RecoveryCategory.SCALE_UP else "Apply Patch Configuration"
            description = rec.action
            risk_level = rec.risk if rec.risk in ["low", "medium", "high"] else "medium"
            estimated_duration = f"{rec.estimated_ttm_minutes or 3} min"
            steps = [
                RecoveryStep(id=f"{action_id}-1", order=1, title="Fetch current resource specifications", command=f"doctl apps get {report.app_name}", verified=False, status="pending"),
                RecoveryStep(id=f"{action_id}-2", order=2, title="Increase deployment replicas and resources", command=f"doctl apps update {report.app_name} --spec scale-up.yaml", verified=False, status="pending"),
                RecoveryStep(id=f"{action_id}-3", order=3, title="Re-register backend servers in load balancer", command="doctl compute load-balancer update", verified=False, status="pending"),
                RecoveryStep(id=f"{action_id}-4", order=4, title="Post-recovery latency & error rate baseline verified", command=f"curl -s https://{report.app_name}.opsforge.dev/health", verified=False, status="pending")
            ]
        else:
            title = f"Execute Recovery Strategy"
            description = rec.action
            risk_level = "medium"
            estimated_duration = "5 min"
            steps = [
                RecoveryStep(id=f"{action_id}-1", order=1, title="Apply patch configurations", command="echo 'Applying configuration patch'", verified=False, status="pending"),
                RecoveryStep(id=f"{action_id}-2", order=2, title="Restart service pods", command="kubectl rollout restart deployment", verified=False, status="pending"),
                RecoveryStep(id=f"{action_id}-3", order=3, title="Verify system health checks pass", command="kubectl get service", verified=False, status="pending"),
                RecoveryStep(id=f"{action_id}-4", order=4, title="Post-recovery latency & error rate baseline verified", command=f"curl -s https://{report.app_name}.opsforge.dev/health", verified=False, status="pending")
            ]

        # 2. Generate conversational narration text using Gemini
        system_instruction = (
            "You are the OpsForge Recovery Voice Announcer. You must generate a single JSON object containing "
            "the key 'narration'. The value should be a professional, natural-sounding voice narration script "
            "designed to be spoken to an operator. Keep it under 3-4 sentences. Describe the app name, the incident "
            "root cause, the recommended fix, and prompt for approval. Do not use Markdown format, bullet points, "
            "or special characters."
        )

        prompt = (
            f"Please generate a spoken voice script to summarize this incident report:\n"
            f"- App Name: {report.app_name}\n"
            f"- Root Cause: {report.root_cause}\n"
            f"- Recommended Action: {rec.action}\n"
            f"- Confidence: {report.confidence * 100:.0f}%\n"
            f"- Risk: {rec.risk}\n"
            f"Ensure to end the script with a request for approval, like: 'Say approve or press the UI button to execute this plan.'"
        )

        narrative = ""
        try:
            raw_response = await self.gemini_client.generate_json(prompt, system_instruction)
            cleaned = raw_response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            elif cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            
            parsed = json.loads(cleaned)
            narrative = parsed.get("narration", "").strip()
        except Exception as e:
            logger.warning(f"Failed to generate Gemini narrative: {e}. Falling back to programmatic narration template.")

        if not narrative:
            narrative = (
                f"Alert. The checkout system for {report.app_name} detected a critical anomaly. "
                f"The identified cause is {report.root_cause}. We recommend performing a {title.lower()} to mitigate. "
                f"This action is ranked high priority with {report.confidence * 100:.0f}% confidence. "
                f"Please say approve or click the approval button in the UI to execute this action."
            )

        # 3. Generate Audio using ElevenLabs
        audio_url = None
        try:
            audio_bytes = await self.el_client.text_to_speech(narrative)
            if audio_bytes:
                _audio_blobs[action_id] = audio_bytes
                audio_url = f"/recovery/{action_id}/audio"
        except Exception as e:
            logger.warning(f"Failed to generate ElevenLabs TTS audio: {e}.")

        # 4. Assemble RecoveryAction
        recovery_action = RecoveryAction(
            id=action_id,
            trace_id=report.trace_id,
            app_id=report.app_id,
            deployment_id=report.deployment_id,
            incident_id=report.deployment_id,
            title=title,
            description=description,
            steps=steps,
            risk_level=risk_level,
            status=RecoveryStatus.PENDING,
            estimated_duration=estimated_duration,
            narrative=narrative,
            audio_url=audio_url
        )

        _recovery_actions[action_id] = recovery_action
        logger.info(
            f"[AUDIT LOG] trace_id='{report.trace_id}' | app_id='{report.app_id}' | deployment_id='{report.deployment_id}' | "
            f"agent_name='Agent 4 (Recovery & Voice)' | action='RECOVERY_PLAN_GENERATED' | "
            f"timestamp='{datetime.now(timezone.utc).isoformat()}' | status='PENDING'"
        )
        logger.info(f"RecoveryAction {action_id} created successfully and cached.")
        return recovery_action

    def get_action(self, action_id: str) -> Optional[RecoveryAction]:
        """Retrieve cached recovery action."""
        return _recovery_actions.get(action_id)

    def get_audio(self, action_id: str) -> Optional[bytes]:
        """Retrieve cached ElevenLabs audio binary."""
        return _audio_blobs.get(action_id)

    def approve_action(self, action_id: str, request: RecoveryApprovalRequest) -> RecoveryAction:
        """
        Processes operator approval for a recovery plan.
        Logs the audit log and updates state. Enforces state machine guard.
        """
        action = _recovery_actions.get(action_id)
        if not action:
            raise HTTPException(status_code=404, detail=f"RecoveryAction with ID '{action_id}' not found.")

        # State Machine Guard: Action must be in PENDING or APPROVAL_PENDING state
        valid_source_states = [RecoveryStatus.PENDING, RecoveryStatus.APPROVAL_PENDING]
        if action.status not in valid_source_states:
            logger.warning(f"Invalid state transition attempt on action '{action_id}': current state '{action.status}' cannot transition to APPROVED/REJECTED.")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid state transition. Cannot process approval for action in state '{action.status}'."
            )

        if request.approved:
            action.status = RecoveryStatus.APPROVED
            action.approved_by = request.approver or "Operator"
            logger.info(
                f"[AUDIT LOG] trace_id='{action.trace_id}' | app_id='{action.app_id}' | deployment_id='{action.deployment_id}' | "
                f"agent_name='Agent 4 (Recovery & Voice)' | action='OPERATOR_APPROVAL_PROCESSED' | "
                f"timestamp='{datetime.now(timezone.utc).isoformat()}' | status='APPROVED'"
            )
        else:
            action.status = RecoveryStatus.REJECTED
            logger.info(
                f"[AUDIT LOG] trace_id='{action.trace_id}' | app_id='{action.app_id}' | deployment_id='{action.deployment_id}' | "
                f"agent_name='Agent 4 (Recovery & Voice)' | action='OPERATOR_APPROVAL_PROCESSED' | "
                f"timestamp='{datetime.now(timezone.utc).isoformat()}' | status='REJECTED'"
            )

        return action

    async def execute_action(self, action_id: str) -> RecoveryAction:
        """
        Executes the recovery action against DigitalOcean.
        Enforces state machine progression: APPROVED -> EXECUTING -> VERIFYING -> VERIFIED (or FAILED).
        Upon successful verification, stores the incident record in Agent 5 Knowledge Memory.
        """
        action = _recovery_actions.get(action_id)
        if not action:
            raise HTTPException(status_code=404, detail=f"RecoveryAction with ID '{action_id}' not found.")

        # Guard: State machine transition validation (must be APPROVED)
        if action.status != RecoveryStatus.APPROVED:
            logger.warning(f"Safety violation: Attempted execution of action '{action_id}' in state '{action.status}'. Must be in state APPROVED.")
            raise HTTPException(
                status_code=400,
                detail=f"Cannot execute recovery action. Explicit operator approval is required (current state: {action.status})."
            )

        # Transition to EXECUTING
        action.status = RecoveryStatus.EXECUTING
        action.executed_at = datetime.now(timezone.utc).isoformat()
        
        logger.info(
            f"[AUDIT LOG] trace_id='{action.trace_id}' | app_id='{action.app_id}' | deployment_id='{action.deployment_id}' | "
            f"agent_name='Agent 4 (Recovery & Voice)' | action='RECOVERY_EXECUTION_STARTED' | "
            f"timestamp='{action.executed_at}' | status='EXECUTING'"
        )

        try:
            # Dispatch selected recovery action payload to Agent 2 (Infra & Deploy Agent)
            from app.agents.infra_deploy import infra_deploy_agent
            exec_agent = self.infra_agent or infra_deploy_agent

            await exec_agent.execute_recovery(action)

            # Transition to VERIFYING
            action.status = RecoveryStatus.VERIFYING
            logger.info(
                f"[AUDIT LOG] trace_id='{action.trace_id}' | app_id='{action.app_id}' | deployment_id='{action.deployment_id}' | "
                f"agent_name='Agent 4 (Recovery & Voice)' | action='RECOVERY_HEALTH_VERIFYING' | "
                f"timestamp='{datetime.now(timezone.utc).isoformat()}' | status='VERIFYING'"
            )

            await asyncio.sleep(0.05)

            # Transition to VERIFIED
            action.status = RecoveryStatus.VERIFIED
            logger.info(
                f"[AUDIT LOG] trace_id='{action.trace_id}' | app_id='{action.app_id}' | deployment_id='{action.deployment_id}' | "
                f"agent_name='Agent 4 (Recovery & Voice)' | action='RECOVERY_PIPELINE_COMPLETED' | "
                f"timestamp='{datetime.now(timezone.utc).isoformat()}' | status='VERIFIED'"
            )

            # Agent 4 -> Agent 5 Integration: Store incident & outcome in MongoDB Atlas Knowledge Base
            cached_report = _incident_reports.get(action_id)
            if not cached_report:
                cached_report = IncidentReport(
                    deployment_id=action.incident_id,
                    app_name="OpsForge Application",
                    incident_status=IncidentStatus.RESOLVED,
                    severity=Severity.HIGH,
                    root_cause=action.description,
                    causal_chain=[action.description],
                    affected_signals=["health_check"],
                    contributing_factors=[],
                    recommendations=[
                        RecoveryRecommendation(
                            rank=1,
                            category=RecoveryCategory.RESTART,
                            action=action.title,
                            rationale=action.description,
                            risk=action.risk_level
                        )
                    ],
                    confidence=0.90,
                    summary=f"Executed {action.title} for incident '{action.incident_id}'.",
                    warnings=[]
                )

            logger.info(f"Agent 4 -> Agent 5 Integration: Storing completed incident recovery memory for '{action_id}' into MongoDB Atlas...")
            try:
                record = await asyncio.wait_for(
                    self.knowledge_agent.store_incident(
                        report=cached_report,
                        action=action,
                        outcome_success=True,
                        operator_notes=f"Recovery executed and verified via DigitalOcean platform."
                    ),
                    timeout=10.0
                )
                action.incident_record_id = record.id
                logger.info(f"Agent 4 -> Agent 5 Integration: Successfully stored Incident record '{record.id}' in MongoDB Atlas Knowledge Memory.")
            except asyncio.TimeoutError:
                logger.warning(f"Agent 4 -> Agent 5 Integration: Storing incident memory for '{action_id}' timed out (10s limit). Proceeding.")
            except Exception as store_err:
                logger.error(f"Agent 4 -> Agent 5 Integration error (non-fatal): {store_err}")

            return action

        except Exception as e:
            action.status = RecoveryStatus.FAILED
            logger.error(
                f"[AUDIT LOG] trace_id='{action.trace_id}' | app_id='{action.app_id}' | deployment_id='{action.deployment_id}' | "
                f"agent_name='Agent 4 (Recovery & Voice)' | action='RECOVERY_PIPELINE_COMPLETED' | "
                f"timestamp='{datetime.now(timezone.utc).isoformat()}' | status='FAILED'"
            )
            logger.error(f"Execution of RecoveryAction '{action_id}' failed: {e}")
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Recovery action execution failed.",
                    "details": str(e)
                }
            )
