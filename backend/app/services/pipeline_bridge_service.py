from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from app.schemas.deployment import DeploymentResult
from app.schemas.incident import (
    IncidentAnalysisRequest,
    LogEntry,
    MetricPoint,
    DeploymentEvent
)
from app.utils.logger import get_logger

logger = get_logger()

class PipelineBridgeService:
    """
    Service responsible ONLY for data transformation between Agent 2 (Infra & Deploy)
    and Agent 3 (Telemetry & Root Cause).
    
    Strictly preserves:
      - trace_id
      - app_id
      - deployment_id
      - app_name
      - deployment_status
      - created_at / timestamp
      - infrastructure_metadata
      
    Does NOT collect telemetry. Telemetry collection is isolated to TelemetryService.
    """

    @staticmethod
    def transform_deployment_to_incident_request(
        deployment_result: DeploymentResult,
        logs: Optional[List[LogEntry]] = None,
        metrics: Optional[List[MetricPoint]] = None,
        events: Optional[List[DeploymentEvent]] = None
    ) -> IncidentAnalysisRequest:
        """
        Transforms a DeploymentResult into a structured IncidentAnalysisRequest.
        """
        trace_id = deployment_result.trace_id
        app_id = deployment_result.app_id
        deployment_id = deployment_result.deployment_id or "unknown-deployment"
        app_name = deployment_result.app_name or (
            deployment_result.details.get("app_name") if deployment_result.details else "opsforge-app"
        ) or "opsforge-app"
        status = deployment_result.status
        metadata = dict(deployment_result.details or {})
        if deployment_result.live_url:
            metadata["live_url"] = deployment_result.live_url
        if deployment_result.created_at:
            metadata["created_at"] = deployment_result.created_at

        logger.info(
            f"[AUDIT LOG] [PipelineBridgeService] Transforming DeploymentResult -> IncidentAnalysisRequest | "
            f"trace_id='{trace_id}', app_id='{app_id}', deployment_id='{deployment_id}', app_name='{app_name}', status='{status}'"
        )

        event_list: List[DeploymentEvent] = list(events or [])

        # If deployment status is failed, ensure a DeploymentEvent is recorded
        if status.lower() in ("failed", "error"):
            deploy_failed_event = DeploymentEvent(
                timestamp=datetime.now(timezone.utc),
                event_type="DEPLOY_FAILED",
                description=deployment_result.message or "Infrastructure deployment failed",
                metadata=metadata
            )
            event_list.append(deploy_failed_event)
        elif not event_list:
            deploy_event = DeploymentEvent(
                timestamp=datetime.now(timezone.utc),
                event_type="DEPLOY_COMPLETED",
                description=deployment_result.message or "Infrastructure deployment completed",
                metadata=metadata
            )
            event_list.append(deploy_event)

        log_list: List[LogEntry] = list(logs or [])
        raw_logs = metadata.get("raw_logs", [])
        if not log_list and raw_logs:
            for item in raw_logs:
                msg = item.get("message", "")
                sev = item.get("severity", "ERROR").upper()
                if msg:
                    log_list.append(LogEntry(
                        timestamp=datetime.now(timezone.utc),
                        level=sev if sev in ("INFO", "WARN", "ERROR", "FATAL", "CRITICAL") else "ERROR",
                        message=msg,
                        source="railway_deploy"
                    ))

        request = IncidentAnalysisRequest(
            trace_id=trace_id,
            app_id=app_id,
            deployment_id=deployment_id,
            app_name=app_name,
            deployment_status=status,
            infrastructure_metadata=metadata,
            logs=log_list,
            metrics=metrics or [],
            events=event_list
        )

        logger.info(
            f"[AUDIT LOG] trace_id='{trace_id}' | app_id='{app_id}' | deployment_id='{deployment_id}' | "
            f"agent_name='PipelineBridgeService' | action='DATA_TRANSFORMATION_COMPLETED' | "
            f"timestamp='{datetime.now(timezone.utc).isoformat()}' | status='SUCCESS'"
        )

        return request
