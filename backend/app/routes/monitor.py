"""
Monitor Routes — OpsForge AI Incident Commander API.

POST /monitor/start
    Accepts MonitorStartRequest (service_name + base_url).
    Collects real HTTP telemetry from base_url (/health, response latency, logs, events),
    runs Agent 3 incident detection & Gemini RCA, queries Agent 5 Knowledge Search,
    and returns a complete MonitoringStatusResponse.
"""

from fastapi import APIRouter, HTTPException, status
from app.services.monitoring_service import monitoring_service, MonitorStartRequest, MonitoringStatusResponse
from app.utils.logger import get_logger

logger = get_logger()

router = APIRouter(prefix="/monitor", tags=["AI Incident Commander Monitoring"])


@router.post(
    "/start",
    response_model=MonitoringStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Start monitoring any pre-deployed application URL",
    description=(
        "Collects real HTTP telemetry from the provided base_url, runs Agent 3 "
        "anomaly detection and Gemini Root Cause Analysis (RCA), and queries Agent 5 "
        "Knowledge Memory for similar historical incidents."
    ),
)
async def start_monitoring(request: MonitorStartRequest) -> MonitoringStatusResponse:
    """
    POST /monitor/start

    Body: MonitorStartRequest (service_name, base_url)
    Returns: MonitoringStatusResponse
    """
    if not request.service_name or not request.service_name.strip():
        raise HTTPException(status_code=400, detail="service_name cannot be empty.")
    if not request.base_url or not request.base_url.strip():
        raise HTTPException(status_code=400, detail="base_url cannot be empty.")

    logger.info(f"POST /monitor/start | service_name='{request.service_name}' | base_url='{request.base_url}'")
    return await monitoring_service.monitor_url(request)
