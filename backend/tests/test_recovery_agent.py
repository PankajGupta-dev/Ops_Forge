import json
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.incident import IncidentReport, RecoveryRecommendation, RecoveryCategory, Severity, IncidentStatus
from app.schemas.recovery import RecoveryAction, RecoveryStatus, RecoveryApprovalRequest
from app.agents.recovery_voice import RecoveryVoiceAgent

client = TestClient(app)

# ---------------------------------------------------------------------------
# Mocks & Helpers
# ---------------------------------------------------------------------------

def _make_report() -> IncidentReport:
    rec = RecoveryRecommendation(
        rank=1,
        category=RecoveryCategory.ROLLBACK,
        action="Revert to last stable deployment and scale up",
        rationale="Root cause is database OOM. Reverting image clears pool limit.",
        risk="low",
        estimated_ttm_minutes=2
    )
    return IncidentReport(
        deployment_id="dep-12345",
        app_name="checkout-service",
        incident_status=IncidentStatus.OPEN,
        severity=Severity.CRITICAL,
        root_cause="Database connections exhausted",
        causal_chain=["DB pool limit reached", "Checkout API OOM"],
        affected_signals=["p99_latency_ms"],
        contributing_factors=["increased checkout traffic"],
        recommendations=[rec],
        confidence=0.92,
        summary="Checkout API is down due to DB exhaustion.",
        warnings=[]
    )

# ---------------------------------------------------------------------------
# Service & Agent Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_recovery_plan_generation_success():
    report = _make_report()
    
    mock_gemini = MagicMock()
    mock_gemini.generate_json = AsyncMock(return_value=json.dumps({"narration": "Checkout API is offline. Reverting deployment."}))
    
    mock_el = MagicMock()
    mock_el.text_to_speech = AsyncMock(return_value=b"DUMMY_MP3_DATA")
    
    agent = RecoveryVoiceAgent(gemini_client=mock_gemini, elevenlabs_client=mock_el)
    
    action = await agent.create_recovery_plan(report)
    
    assert isinstance(action, RecoveryAction)
    assert action.status == RecoveryStatus.APPROVAL_PENDING
    assert action.incident_id == "dep-12345"
    assert action.risk_level == "low"
    assert action.estimated_duration == "2 min"
    assert len(action.steps) == 4
    assert action.narrative == "Checkout API is offline. Reverting deployment."
    assert action.audio_url == f"/recovery/{action.id}/audio"

@pytest.mark.asyncio
async def test_recovery_plan_generation_gemini_fallback():
    report = _make_report()
    
    # Gemini throws error, testing robust fallback
    mock_gemini = MagicMock()
    mock_gemini.generate_json = AsyncMock(side_effect=Exception("API limit exceeded"))
    
    mock_el = MagicMock()
    mock_el.text_to_speech = AsyncMock(return_value=b"DUMMY_MP3_DATA")
    
    agent = RecoveryVoiceAgent(gemini_client=mock_gemini, elevenlabs_client=mock_el)
    action = await agent.create_recovery_plan(report)
    
    assert isinstance(action, RecoveryAction)
    assert "Database connections exhausted" in action.narrative
    assert action.status == RecoveryStatus.APPROVAL_PENDING

def test_recovery_approval_state_transitions():
    report = _make_report()
    agent = RecoveryVoiceAgent()
    
    # Pre-populate action 1 for approve
    action_id_1 = "REC-TEST1"
    action1 = RecoveryAction(
        id=action_id_1,
        incident_id=report.deployment_id,
        title="Test Rollback",
        description="description",
        steps=[],
        risk_level="low",
        status=RecoveryStatus.APPROVAL_PENDING,
        estimated_duration="2 min"
    )
    # Pre-populate action 2 for reject
    action_id_2 = "REC-TEST2"
    action2 = RecoveryAction(
        id=action_id_2,
        incident_id=report.deployment_id,
        title="Test Rollback",
        description="description",
        steps=[],
        risk_level="low",
        status=RecoveryStatus.APPROVAL_PENDING,
        estimated_duration="2 min"
    )
    from app.services.recovery_service import _recovery_actions
    _recovery_actions[action_id_1] = action1
    _recovery_actions[action_id_2] = action2
    
    # Approve action 1
    req1 = RecoveryApprovalRequest(approved=True, approver="John Doe", approval_mode="ui")
    updated1 = agent.process_approval(action_id_1, req1)
    assert updated1.status == RecoveryStatus.APPROVED
    assert updated1.approved_by == "John Doe"

    # Reject action 2
    req2 = RecoveryApprovalRequest(approved=False, approver="John Doe", approval_mode="ui")
    updated2 = agent.process_approval(action_id_2, req2)
    assert updated2.status == RecoveryStatus.REJECTED

@pytest.mark.asyncio
async def test_execution_safety_rules():
    agent = RecoveryVoiceAgent()
    action_id = "REC-TEST2"
    action = RecoveryAction(
        id=action_id,
        incident_id="dep-123",
        title="Test Rollback",
        description="description",
        steps=[],
        risk_level="low",
        status=RecoveryStatus.PENDING,  # Not approved yet!
        estimated_duration="2 min"
    )
    from app.services.recovery_service import _recovery_actions
    _recovery_actions[action_id] = action

    # Should raise error on unapproved execution
    with pytest.raises(HTTPException) as exc_info:
        await agent.execute_recovery(action_id)
    assert exc_info.value.status_code == 400
    assert "Explicit operator approval is required" in exc_info.value.detail

@pytest.mark.asyncio
async def test_execution_success():
    agent = RecoveryVoiceAgent()
    action_id = "REC-TEST3"
    action = RecoveryAction(
        id=action_id,
        incident_id="dep-123",
        title="Rollback Deployment",
        description="description",
        steps=[],
        risk_level="low",
        status=RecoveryStatus.APPROVED,  # Approved!
        estimated_duration="2 min"
    )
    from app.services.recovery_service import _recovery_actions
    _recovery_actions[action_id] = action

    updated = await agent.execute_recovery(action_id)
    assert updated.status == RecoveryStatus.VERIFIED
    assert updated.executed_at is not None

# ---------------------------------------------------------------------------
# Endpoint & API Route Tests
# ---------------------------------------------------------------------------

def test_api_plan_creation_and_routing():
    report_data = _make_report().model_dump()
    
    # Mock services internally
    with patch("app.routes.recovery._agent.create_recovery_plan") as mock_plan:
        mock_action = RecoveryAction(
            id="REC-MOCK123",
            incident_id="dep-12345",
            title="Rollback Deployment",
            description="Revert to last stable",
            steps=[],
            risk_level="low",
            status=RecoveryStatus.PENDING,
            estimated_duration="2 min",
            narrative="Checkout is offline."
        )
        mock_plan.return_value = mock_action
        
        # Test creation route
        resp = client.post("/recovery/plan", json=report_data)
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == "REC-MOCK123"
        assert data["status"] == "pending"

def test_api_approval_and_execution_lifecycle():
    action_id = "REC-API999"
    mock_action = RecoveryAction(
        id=action_id,
        incident_id="dep-12345",
        title="Rollback Deployment",
        description="Revert to last stable",
        steps=[],
        risk_level="low",
        status=RecoveryStatus.PENDING,
        estimated_duration="2 min"
    )
    
    # Store directly in active cache
    from app.services.recovery_service import _recovery_actions
    _recovery_actions[action_id] = mock_action
    
    # Submit approval
    approval_payload = {"approved": True, "approver": "DevOps Lead", "approvalMode": "voice"}
    resp = client.post(f"/recovery/{action_id}/approve", json=approval_payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"
    assert resp.json()["approvedBy"] == "DevOps Lead"
    
    # Trigger execution
    resp = client.post(f"/recovery/{action_id}/execute")
    assert resp.status_code == 200
    assert resp.json()["status"] == "verified"
    assert resp.json()["executedAt"] is not None

def test_api_audio_stream_endpoint():
    action_id = "REC-API888"
    from app.routes.recovery import _agent
    
    # Store audio blob directly in cache
    from app.services.recovery_service import _audio_blobs
    _audio_blobs[action_id] = b"MP3_AUDIO_HEADER_EXAMPLE"
    
    resp = client.get(f"/recovery/{action_id}/audio")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "audio/mpeg"
    assert resp.content == b"MP3_AUDIO_HEADER_EXAMPLE"
