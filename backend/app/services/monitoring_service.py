"""
Monitoring Service — OpsForge AI Incident Commander.

Responsibility:
  Accepts a pre-deployed application URL (base_url), collects real HTTP telemetry
  (health status, response times, logs, events), runs Agent 3 rule-based incident detection,
  and if an anomaly/unhealthy state is detected, runs Gemini RCA & Agent 5 Knowledge Memory vector search.

Decoupled from Agent 1 (Planner), Agent 2 (Deployer), and Agent 4 (Recovery Voice).
"""

import uuid
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

from app.schemas.incident import IncidentAnalysisRequest, IncidentReport, LogEntry, MetricPoint, DeploymentEvent
from app.services.telemetry_service import collect_real_telemetry
from app.agents.root_cause import RootCauseAgent
from app.agents.knowledge_memory import KnowledgeMemoryAgent
from app.utils.logger import get_logger

logger = get_logger()


class MonitorStartRequest(BaseModel):
    """Request payload for POST /monitor/start"""
    service_name: str = Field(..., description="Name of pre-deployed service to monitor")
    base_url:     str = Field(..., description="Public base URL of application (e.g. https://app.up.railway.app)")


class MonitoringStatusResponse(BaseModel):
    """Response payload for monitoring service analysis"""
    service_name:      str
    base_url:          str
    health_status:      str = Field(..., description="healthy | unhealthy | degraded")
    incident_detected: bool
    detection_reasons: List[str] = Field(default_factory=list)
    logs:              List[LogEntry] = Field(default_factory=list)
    metrics:           List[MetricPoint] = Field(default_factory=list)
    events:            List[DeploymentEvent] = Field(default_factory=list)
    rca_report:        Optional[IncidentReport] = None


class MonitoringService:
    def __init__(self, rca_agent: Optional[RootCauseAgent] = None, knowledge_agent: Optional[KnowledgeMemoryAgent] = None):
        self.rca_agent = rca_agent or RootCauseAgent()
        self.knowledge_agent = knowledge_agent or KnowledgeMemoryAgent()

    async def monitor_url(self, request: MonitorStartRequest) -> MonitoringStatusResponse:
        """
        Collect real telemetry from base_url, run incident detection, and if unhealthy,
        execute Agent 3 RCA + Agent 5 Knowledge Search.
        """
        service_name = request.service_name.strip()
        base_url = request.base_url.strip()
        deployment_id = f"dep-{uuid.uuid4().hex[:8]}"

        logger.info(f"[MONITOR] Probing service '{service_name}' at URL '{base_url}'...")

        # 1. Collect real HTTP telemetry
        logs, metrics, events, health_status = await collect_real_telemetry(base_url)

        # 2. Build analysis request
        analysis_req = IncidentAnalysisRequest(
            trace_id=str(uuid.uuid4()),
            app_id=service_name.lower().replace(" ", "-"),
            deployment_id=deployment_id,
            app_name=service_name,
            deployment_status=health_status,
            infrastructure_metadata={"base_url": base_url, "health_status": health_status},
            logs=logs,
            metrics=metrics,
            events=events,
        )

        # 3. Always run Agent 3 RCA (which internally handles detection & Agent 5 vector search)
        report: Optional[IncidentReport] = None
        try:
            report = await self.rca_agent.run(analysis_req)
        except Exception as exc:
            logger.error(f"[MONITOR] Agent 3 RCA execution error: {exc}")

        detection_reasons = []
        incident_detected = False
        if report:
            incident_detected = (report.incident_status.value != "resolved") if hasattr(report.incident_status, "value") else (str(report.incident_status) != "resolved")
            detection_reasons = report.affected_signals or [report.root_cause]

        return MonitoringStatusResponse(
            service_name=service_name,
            base_url=base_url,
            health_status=health_status,
            incident_detected=incident_detected,
            detection_reasons=detection_reasons,
            logs=logs,
            metrics=metrics,
            events=events,
            rca_report=report,
        )


monitoring_service = MonitoringService()
