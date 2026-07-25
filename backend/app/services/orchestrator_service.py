"""
OrchestratorService — OpsForge End-to-End Pipeline Engine.

Composes Agents 1–5 in the canonical execution order without modifying
any agent internals. Manages trace propagation, per-stage timing, and
structured error handling.

Pipeline sequence:
  PipelineRequest
  → Stage PLAN    : Agent 1 (DeploymentPlannerAgent.create_plan)
  → Stage DEPLOY  : Agent 2 (InfraDeployAgent.deploy)          [includes A2→A3 bridge]
  → Stage RCA     : Agent 3 (RootCauseAgent.run)               [includes A3→A5 vector search]
  → Stage RECOVERY_PLAN : Agent 3 (hand_off_to_recovery)       [Agent 4 creates RecoveryAction]
  → WorkflowResult (status=AWAITING_APPROVAL, recovery_action_id=...)

Subsequent approval and execution are human-triggered via existing
REST endpoints:
  POST /recovery/{id}/approve   → operator decision
  POST /recovery/{id}/execute   → Agent 4 → Agent 2 → Agent 5
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.agents.deployment_planner import DeploymentPlannerAgent
from app.agents.infra_deploy import InfraDeployAgent
from app.agents.root_cause import RootCauseAgent
from app.schemas.deployment import PlannerRequest, DeploymentPlan, DeploymentResult
from app.schemas.incident import IncidentAnalysisRequest, IncidentReport
from app.schemas.recovery import RecoveryAction
from app.schemas.orchestration import (
    PipelineRequest,
    StageResult,
    StageStatus,
    WorkflowResult,
    WorkflowStatus,
)
from app.services.pipeline_bridge_service import PipelineBridgeService
from app.utils.logger import get_logger

logger = get_logger()

# ---------------------------------------------------------------------------
# In-process cache for completed WorkflowResults (trace_id → WorkflowResult)
# ---------------------------------------------------------------------------
_workflow_cache: Dict[str, WorkflowResult] = {}


def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _ms_since(start_iso: str) -> int:
    """Compute elapsed milliseconds since a UTC ISO-8601 timestamp."""
    start = datetime.fromisoformat(start_iso)
    delta = datetime.now(timezone.utc) - start
    return int(delta.total_seconds() * 1000)


def _stage_ok(name: str, started_at: str, data: Dict[str, Any]) -> StageResult:
    finished = _now_iso()
    return StageResult(
        stage=name,
        status=StageStatus.COMPLETED,
        started_at=started_at,
        finished_at=finished,
        duration_ms=_ms_since(started_at),
        data=data,
    )


def _stage_fail(name: str, started_at: str, error: str) -> StageResult:
    finished = _now_iso()
    return StageResult(
        stage=name,
        status=StageStatus.FAILED,
        started_at=started_at,
        finished_at=finished,
        duration_ms=_ms_since(started_at),
        error=error,
    )


class OrchestratorService:
    """
    Composes Agents 1–5 into a single end-to-end deployment and
    incident response pipeline.

    The orchestrator is intentionally thin — it delegates all business
    logic to the individual agents and their pairwise integrations.
    """

    def __init__(
        self,
        planner_agent: Optional[DeploymentPlannerAgent] = None,
        infra_agent: Optional[InfraDeployAgent] = None,
        rca_agent: Optional[RootCauseAgent] = None,
    ) -> None:
        self.planner_agent = planner_agent or DeploymentPlannerAgent()
        self.infra_agent = infra_agent or InfraDeployAgent()
        self.rca_agent = rca_agent or RootCauseAgent()

    # ------------------------------------------------------------------
    # Main pipeline entry point
    # ------------------------------------------------------------------

    async def run(self, request: PipelineRequest) -> WorkflowResult:
        """
        Execute the full pre-approval pipeline:
          PLAN → DEPLOY → RCA → RECOVERY_PLAN

        Returns a WorkflowResult in AWAITING_APPROVAL state containing
        the recovery_action_id for the operator approval flow.
        """
        trace_id = str(uuid.uuid4())
        pipeline_started_at = _now_iso()
        stages: List[StageResult] = []

        logger.info(
            f"[ORCHESTRATOR] Pipeline started | trace_id='{trace_id}' | "
            f"simulate_failure={request.simulate_failure}"
        )

        # Shared state populated across stages
        plan: Optional[DeploymentPlan] = None
        result: Optional[DeploymentResult] = None
        report: Optional[IncidentReport] = None
        recovery_action: Optional[RecoveryAction] = None

        # ----------------------------------------------------------------
        # Stage 1: PLAN — Agent 1 generates DeploymentPlan
        # ----------------------------------------------------------------
        stage_name = "PLAN"
        stage_start = _now_iso()
        logger.info(f"[ORCHESTRATOR] Stage '{stage_name}' starting | trace_id='{trace_id}'")
        try:
            planner_request = PlannerRequest(
                description=request.description,
                dockerfile=request.dockerfile,
                repository=request.repository,
                branch=request.branch,
            )
            plan = await self.planner_agent.create_plan(planner_request)
            stages.append(
                _stage_ok(stage_name, stage_start, {
                    "app_name":     plan.application.name,
                    "runtime":      plan.application.runtime,
                    "platform":     plan.deployment.platform,
                    "region":       plan.deployment.region,
                    "strategy":     plan.deployment.strategy,
                    "replicas":     plan.deployment.replicas,
                    "warnings":     plan.warnings,
                    "assumptions":  plan.assumptions,
                })
            )
            logger.info(
                f"[ORCHESTRATOR] Stage '{stage_name}' completed | app='{plan.application.name}' | "
                f"trace_id='{trace_id}'"
            )
        except Exception as exc:
            stages.append(_stage_fail(stage_name, stage_start, str(exc)))
            return self._abort(trace_id, pipeline_started_at, stages, str(exc))

        # ----------------------------------------------------------------
        # Stage 2: DEPLOY — Agent 2 executes DeploymentPlan
        # Note: Agent 2 internally calls Agent 3 via PipelineBridgeService,
        #       but we invoke Agent 2 directly here (not via Agent 1's
        #       create_and_deploy) so we can inject the trace_id and
        #       retain the result for the orchestration stages below.
        # ----------------------------------------------------------------
        stage_name = "DEPLOY"
        stage_start = _now_iso()
        logger.info(f"[ORCHESTRATOR] Stage '{stage_name}' starting | trace_id='{trace_id}'")
        try:
            result = await self.infra_agent.deployment_service.execute_deployment(
                plan=plan,
                repository=request.repository,
                branch=request.branch
            )
            # Inject the shared trace_id so all downstream stages can correlate
            result.trace_id = trace_id
            stages.append(
                _stage_ok(stage_name, stage_start, {
                    "status":        result.status,
                    "app_id":        result.app_id,
                    "deployment_id": result.deployment_id,
                    "app_name":      result.app_name,
                    "live_url":      result.live_url,
                    "message":       result.message,
                    "created_at":    result.created_at,
                })
            )
            logger.info(
                f"[ORCHESTRATOR] Stage '{stage_name}' completed | "
                f"deployment_id='{result.deployment_id}' | status='{result.status}' | "
                f"trace_id='{trace_id}'"
            )
        except Exception as exc:
            stages.append(_stage_fail(stage_name, stage_start, str(exc)))
            return self._abort(trace_id, pipeline_started_at, stages, str(exc))

        # ----------------------------------------------------------------
        # Stage 3: RCA — Agent 3 runs full root cause analysis
        #   Internally: Agent 3 queries Agent 5 for vector similarity search
        # ----------------------------------------------------------------
        stage_name = "RCA"
        stage_start = _now_iso()
        logger.info(f"[ORCHESTRATOR] Stage '{stage_name}' starting | trace_id='{trace_id}'")
        try:
            # Transform the deployment result into an incident analysis request.
            # If simulate_failure is True, generate a realistic failure telemetry payload
            # to trigger the incident detection and RCA pipeline.
            incident_request = PipelineBridgeService.transform_deployment_to_incident_request(result)

            if request.simulate_failure:
                incident_request = _inject_failure_telemetry(incident_request)
                logger.info(
                    f"[ORCHESTRATOR] Injected controlled failure telemetry into RCA request | "
                    f"trace_id='{trace_id}'"
                )

            report = await self.rca_agent.run(incident_request)
            stages.append(
                _stage_ok(stage_name, stage_start, {
                    "incident_status":      report.incident_status,
                    "severity":             report.severity,
                    "root_cause":           report.root_cause,
                    "causal_chain":         report.causal_chain,
                    "affected_signals":     report.affected_signals,
                    "contributing_factors": report.contributing_factors,
                    "confidence":           report.confidence,
                    "recommendations_count": len(report.recommendations),
                    "similar_incidents_found": len(report.similar_incidents),
                    "summary":              report.summary,
                    "warnings":             report.warnings,
                })
            )
            logger.info(
                f"[ORCHESTRATOR] Stage '{stage_name}' completed | "
                f"severity='{report.severity}' | confidence={report.confidence:.2f} | "
                f"similar_incidents={len(report.similar_incidents)} | trace_id='{trace_id}'"
            )
        except Exception as exc:
            stages.append(_stage_fail(stage_name, stage_start, str(exc)))
            return self._abort(trace_id, pipeline_started_at, stages, str(exc))

        # ----------------------------------------------------------------
        # Stage 4: RECOVERY_PLAN — Agent 4 (via Agent 3 handoff) creates
        #          a pending RecoveryAction with voice narration
        #
        # In development mode (SKIP_AGENT4=true), the pipeline stops here
        # and returns the Agent 3 RCA result directly without invoking
        # Agent 4. This allows verifying Agent 3 independently.
        # ----------------------------------------------------------------
        from app.utils.config import settings as _cfg

        if _cfg.SKIP_AGENT4:
            logger.info(
                f"[ORCHESTRATOR] SKIP_AGENT4=true — skipping RECOVERY_PLAN stage | "
                f"trace_id='{trace_id}'"
            )
            stages.append(StageResult(
                stage="RECOVERY_PLAN",
                status=StageStatus.SKIPPED,
                started_at=_now_iso(),
                finished_at=_now_iso(),
                duration_ms=0,
                data={"reason": "SKIP_AGENT4=true (development mode)"},
            ))

            finished_at = _now_iso()
            workflow = WorkflowResult(
                trace_id=trace_id,
                workflow_status=WorkflowStatus.COMPLETED,
                stages=stages,
                # Cross-stage summary
                app_name=result.app_name or plan.application.name,
                deployment_id=result.deployment_id,
                app_id=result.app_id,
                live_url=result.live_url,
                incident_detected=(report.incident_status.value != "resolved"),
                severity=str(report.severity.value) if hasattr(report.severity, "value") else str(report.severity),
                root_cause=report.root_cause,
                confidence=report.confidence,
                similar_incidents_found=len(report.similar_incidents),
                # Timing
                started_at=pipeline_started_at,
                finished_at=finished_at,
                total_duration_ms=_ms_since(pipeline_started_at),
            )

            _workflow_cache[trace_id] = workflow
            logger.info(
                f"[ORCHESTRATOR] Pipeline completed (dev mode, Agent 4 skipped) | "
                f"trace_id='{trace_id}' | duration_ms={workflow.total_duration_ms}"
            )
            return workflow

        # --- Production path: invoke Agent 4 ---
        stage_name = "RECOVERY_PLAN"
        stage_start = _now_iso()
        logger.info(f"[ORCHESTRATOR] Stage '{stage_name}' starting | trace_id='{trace_id}'")
        try:
            recovery_action = await self.rca_agent.hand_off_to_recovery(report)
            stages.append(
                _stage_ok(stage_name, stage_start, {
                    "recovery_action_id": recovery_action.id,
                    "title":              recovery_action.title,
                    "description":        recovery_action.description,
                    "risk_level":         recovery_action.risk_level,
                    "status":             recovery_action.status,
                    "estimated_duration": recovery_action.estimated_duration,
                    "steps_count":        len(recovery_action.steps),
                    "has_audio":          recovery_action.audio_url is not None,
                    "audio_url":          recovery_action.audio_url,
                    "approval_endpoint":  f"/recovery/{recovery_action.id}/approve",
                    "execute_endpoint":   f"/recovery/{recovery_action.id}/execute",
                })
            )
            logger.info(
                f"[ORCHESTRATOR] Stage '{stage_name}' completed | "
                f"recovery_action_id='{recovery_action.id}' | risk='{recovery_action.risk_level}' | "
                f"trace_id='{trace_id}'"
            )
        except Exception as exc:
            stages.append(_stage_fail(stage_name, stage_start, str(exc)))
            return self._abort(trace_id, pipeline_started_at, stages, str(exc))

        # ----------------------------------------------------------------
        # Build and cache the final WorkflowResult
        # ----------------------------------------------------------------
        finished_at = _now_iso()
        workflow = WorkflowResult(
            trace_id=trace_id,
            workflow_status=WorkflowStatus.AWAITING_APPROVAL,
            stages=stages,
            # Cross-stage summary
            app_name=result.app_name or plan.application.name,
            deployment_id=result.deployment_id,
            app_id=result.app_id,
            live_url=result.live_url,
            incident_detected=(report.incident_status.value != "resolved"),
            severity=str(report.severity.value) if hasattr(report.severity, "value") else str(report.severity),
            root_cause=report.root_cause,
            confidence=report.confidence,
            recovery_action_id=recovery_action.id,
            similar_incidents_found=len(report.similar_incidents),
            # Timing
            started_at=pipeline_started_at,
            finished_at=finished_at,
            total_duration_ms=_ms_since(pipeline_started_at),
        )

        _workflow_cache[trace_id] = workflow

        logger.info(
            f"[ORCHESTRATOR] Pipeline completed | trace_id='{trace_id}' | "
            f"status='{workflow.workflow_status}' | "
            f"recovery_action_id='{recovery_action.id}' | "
            f"duration_ms={workflow.total_duration_ms}"
        )

        return workflow

    # ------------------------------------------------------------------
    # Cache lookup
    # ------------------------------------------------------------------

    def get_workflow(self, trace_id: str) -> Optional[WorkflowResult]:
        """Retrieve a previously cached WorkflowResult by trace_id."""
        return _workflow_cache.get(trace_id)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _abort(
        self,
        trace_id: str,
        started_at: str,
        stages: List[StageResult],
        error: str,
    ) -> WorkflowResult:
        """Build a FAILED WorkflowResult and cache it."""
        finished_at = _now_iso()
        workflow = WorkflowResult(
            trace_id=trace_id,
            workflow_status=WorkflowStatus.FAILED,
            stages=stages,
            started_at=started_at,
            finished_at=finished_at,
            total_duration_ms=_ms_since(started_at),
            error=error,
        )
        _workflow_cache[trace_id] = workflow
        logger.error(
            f"[ORCHESTRATOR] Pipeline FAILED | trace_id='{trace_id}' | error='{error}'"
        )
        return workflow


# ---------------------------------------------------------------------------
# Failure Telemetry Injection
# ---------------------------------------------------------------------------

def _inject_failure_telemetry(
    request: IncidentAnalysisRequest,
) -> IncidentAnalysisRequest:
    """
    Enrich a post-deployment IncidentAnalysisRequest with a realistic
    controlled-failure telemetry payload so that Agent 3's rule-based
    incident detector fires and generates a meaningful RCA + Recovery plan.

    Only called when PipelineRequest.simulate_failure=True.
    This preserves all existing request fields (trace_id, app_id, etc.)
    and appends synthetic logs, metrics, and events.
    """
    from datetime import timedelta
    from app.schemas.incident import LogEntry, MetricPoint, DeploymentEvent

    now = datetime.now(timezone.utc)

    failure_logs = [
        LogEntry(
            timestamp=now - timedelta(seconds=90),
            level="ERROR",
            message="FATAL: Database connection pool exhausted — max_connections=100 reached",
            source="app",
        ),
        LogEntry(
            timestamp=now - timedelta(seconds=75),
            level="ERROR",
            message="ConnectionPoolTimeoutError: Could not acquire connection within 30s",
            source="app",
        ),
        LogEntry(
            timestamp=now - timedelta(seconds=60),
            level="ERROR",
            message="HTTP 503 Service Unavailable — upstream connection failure",
            source="platform",
        ),
        LogEntry(
            timestamp=now - timedelta(seconds=45),
            level="WARN",
            message="Health check probe failed — /healthz returned status 503",
            source="infra",
        ),
        LogEntry(
            timestamp=now - timedelta(seconds=30),
            level="ERROR",
            message="Container restart triggered by Railway health checker (restart_count=3)",
            source="infra",
        ),
    ]

    failure_metrics = [
        MetricPoint(timestamp=now - timedelta(seconds=120), name="cpu_percent",    value=18.2,  unit="%"),
        MetricPoint(timestamp=now - timedelta(seconds=90),  name="cpu_percent",    value=22.4,  unit="%"),
        MetricPoint(timestamp=now - timedelta(seconds=90),  name="error_rate",     value=0.0,   unit="%"),
        MetricPoint(timestamp=now - timedelta(seconds=75),  name="error_rate",     value=48.7,  unit="%"),
        MetricPoint(timestamp=now - timedelta(seconds=60),  name="error_rate",     value=91.3,  unit="%"),
        MetricPoint(timestamp=now - timedelta(seconds=60),  name="p99_latency_ms", value=4820.0, unit="ms"),
        MetricPoint(timestamp=now - timedelta(seconds=45),  name="p99_latency_ms", value=8900.0, unit="ms"),
        MetricPoint(timestamp=now - timedelta(seconds=45),  name="ram_percent",    value=87.6,  unit="%"),
        MetricPoint(timestamp=now - timedelta(seconds=30),  name="ram_percent",    value=96.1,  unit="%"),
        MetricPoint(timestamp=now - timedelta(seconds=15),  name="restart_count",  value=3.0,   unit="count"),
    ]

    failure_events = list(request.events) + [
        DeploymentEvent(
            timestamp=now - timedelta(seconds=80),
            event_type="HEALTH_CHECK_FAILED",
            description="Railway health check probe returned HTTP 503 — container marked unhealthy",
            metadata={"probe_path": "/healthz", "http_status": 503, "consecutive_failures": 3},
        ),
        DeploymentEvent(
            timestamp=now - timedelta(seconds=35),
            event_type="CONTAINER_RESTART",
            description="Application container automatically restarted due to consecutive health check failures",
            metadata={"restart_count": 3, "exit_code": 137, "reason": "OOMKilled"},
        ),
    ]

    return IncidentAnalysisRequest(
        trace_id=request.trace_id,
        app_id=request.app_id,
        deployment_id=request.deployment_id,
        app_name=request.app_name,
        deployment_status=request.deployment_status,
        infrastructure_metadata=request.infrastructure_metadata,
        logs=failure_logs,
        metrics=failure_metrics,
        events=failure_events,
    )


# ---------------------------------------------------------------------------
# Singleton instance
# ---------------------------------------------------------------------------
orchestrator_service = OrchestratorService()
