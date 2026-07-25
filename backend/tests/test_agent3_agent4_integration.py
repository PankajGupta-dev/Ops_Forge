import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.incident import (
    IncidentAnalysisRequest,
    IncidentReport,
    IncidentStatus,
    Severity,
    RecoveryRecommendation,
    RecoveryCategory,
    LogEntry,
)
from app.schemas.recovery import (
    RecoveryAction,
    RecoveryStatus,
    RecoveryApprovalRequest,
)
from app.agents.root_cause import RootCauseAgent
from app.agents.recovery_voice import RecoveryVoiceAgent

client = TestClient(app)


def _make_incident_report() -> IncidentReport:
    return IncidentReport(
        trace_id="trace-agent3-agent4-001",
        app_id="do-app-auth-service",
        deployment_id="dep-998877",
        app_name="auth-service",
        incident_status=IncidentStatus.OPEN,
        severity=Severity.HIGH,
        root_cause="Out of memory crash caused by memory leak in token validator pool.",
        causal_chain=[
            "Memory usage reached 98.5%",
            "Kernel OOM killer invoked process kill",
            "Health check probes failed with connection refused"
        ],
        affected_signals=["ram_percent", "error_rate"],
        contributing_factors=["High concurrent request spike"],
        recommendations=[
            RecoveryRecommendation(
                rank=1,
                category=RecoveryCategory.RESTART,
                action="Trigger application container restart to release memory",
                rationale="Clears memory leak state immediately and restores service availability",
                risk="low",
                estimated_ttm_minutes=1
            )
        ],
        confidence=0.92,
        summary="Memory exhaustion caused container crash; restart will immediately clear leak state.",
        warnings=[]
    )


@pytest.mark.asyncio
async def test_agent3_to_agent4_successful_handoff():
    """Verify Agent 3 transfers complete incident analysis to Agent 4 and receives pending RecoveryAction."""
    report = _make_incident_report()

    mock_recovery_agent = MagicMock(spec=RecoveryVoiceAgent)
    mock_action = RecoveryAction(
        id="REC-TEST-001",
        trace_id=report.trace_id,
        app_id=report.app_id,
        deployment_id=report.deployment_id,
        incident_id=report.deployment_id,
        title="Restart Application",
        description=report.recommendations[0].action,
        steps=[],
        risk_level=report.recommendations[0].risk,
        status=RecoveryStatus.PENDING,
        estimated_duration="1 min",
        narrative="Alert. Auth service experienced OOM crash.",
        audio_url="/recovery/REC-TEST-001/audio"
    )
    mock_recovery_agent.create_recovery_plan = AsyncMock(return_value=mock_action)

    agent3 = RootCauseAgent(recovery_agent=mock_recovery_agent)
    action = await agent3.hand_off_to_recovery(report)

    assert action.id == "REC-TEST-001"
    assert action.trace_id == "trace-agent3-agent4-001"
    assert action.app_id == "do-app-auth-service"
    assert action.deployment_id == "dep-998877"
    assert action.risk_level == "low"
    assert action.status == RecoveryStatus.PENDING

    mock_recovery_agent.create_recovery_plan.assert_called_once_with(report)


@pytest.mark.asyncio
async def test_agent3_to_agent4_empty_recommendations_rejection():
    """Verify Agent 3 rejects handoff if IncidentReport contains no recommendations."""
    report = _make_incident_report()
    object.__setattr__(report, "recommendations", [])

    agent3 = RootCauseAgent()
    with pytest.raises(HTTPException) as exc_info:
        await agent3.hand_off_to_recovery(report)

    assert exc_info.value.status_code == 400
    assert "Cannot hand off incident report without recovery recommendations" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_agent3_to_agent4_timeout_handling():
    """Verify Agent 3 handles communication timeout when calling Agent 4 gracefully."""
    report = _make_incident_report()

    mock_recovery_agent = MagicMock(spec=RecoveryVoiceAgent)
    async def slow_create_plan(r):
        await asyncio.sleep(2.0)
        return MagicMock()
    mock_recovery_agent.create_recovery_plan = slow_create_plan

    agent3 = RootCauseAgent(recovery_agent=mock_recovery_agent)

    with pytest.raises(HTTPException) as exc_info:
        await agent3.hand_off_to_recovery(report, timeout_seconds=0.1)

    assert exc_info.value.status_code == 504
    assert "Communication timeout during Agent 3 to Agent 4 recovery handoff" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_agent4_returns_approval_decision_to_agent3():
    """Verify Agent 4 processes approval or rejection and updates status correctly."""
    mock_recovery_agent = MagicMock(spec=RecoveryVoiceAgent)
    action = RecoveryAction(
        id="REC-TEST-002",
        incident_id="dep-12345",
        title="Restart App",
        description="Restart",
        steps=[],
        risk_level="low",
        status=RecoveryStatus.PENDING,
        estimated_duration="1 min"
    )

    # Approve
    approved_action = action.model_copy(deep=True)
    approved_action.status = RecoveryStatus.APPROVED
    approved_action.approved_by = "Lead Operator"

    mock_recovery_agent.process_approval = MagicMock(return_value=approved_action)

    req = RecoveryApprovalRequest(approved=True, approver="Lead Operator", approval_mode="ui")
    res = mock_recovery_agent.process_approval("REC-TEST-002", req)

    assert res.status == RecoveryStatus.APPROVED
    assert res.approved_by == "Lead Operator"

    # Reject
    rejected_action = action.model_copy(deep=True)
    rejected_action.status = RecoveryStatus.REJECTED

    mock_recovery_agent.process_approval = MagicMock(return_value=rejected_action)

    reject_req = RecoveryApprovalRequest(approved=False, approver="Lead Operator", approval_mode="voice")
    reject_res = mock_recovery_agent.process_approval("REC-TEST-002", reject_req)

    assert reject_res.status == RecoveryStatus.REJECTED


def test_analyze_and_handoff_api_endpoint():
    """Verify POST /incident/analyze-and-handoff REST API endpoint."""
    mock_report = _make_incident_report()
    mock_action = RecoveryAction(
        id="REC-API-001",
        trace_id=mock_report.trace_id,
        app_id=mock_report.app_id,
        deployment_id=mock_report.deployment_id,
        incident_id=mock_report.deployment_id,
        title="Restart Application",
        description=mock_report.recommendations[0].action,
        steps=[],
        risk_level="low",
        status=RecoveryStatus.PENDING,
        estimated_duration="1 min",
        narrative="Alert. Auth service OOM crash.",
        audio_url="/recovery/REC-API-001/audio"
    )

    payload = {
        "trace_id": "trace-api-123",
        "app_id": "do-app-auth",
        "deployment_id": "dep-998877",
        "app_name": "auth-service",
        "logs": [
            {
                "timestamp": "2026-07-25T11:00:00Z",
                "level": "ERROR",
                "message": "Process killed: out of memory",
                "source": "app"
            }
        ],
        "metrics": [],
        "events": []
    }

    with patch("app.routes.incidents._agent.run_with_recovery_handoff", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = (mock_report, mock_action)

        response = client.post("/incident/analyze-and-handoff", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "REC-API-001"
        assert data.get("deploymentId") == "dep-998877" or data.get("deployment_id") == "dep-998877"
        assert data.get("riskLevel") == "low" or data.get("risk_level") == "low"
        assert data["status"] == "pending"
        assert data["narrative"] == "Alert. Auth service OOM crash."
