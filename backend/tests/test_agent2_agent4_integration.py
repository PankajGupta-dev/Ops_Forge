import pytest
from unittest.mock import AsyncMock, MagicMock

from app.schemas.recovery import RecoveryAction, RecoveryStep, RecoveryStatus, RecoveryApprovalRequest
from app.agents.infra_deploy import InfraDeployAgent
from app.agents.recovery_voice import RecoveryVoiceAgent
from app.services.deployment_service import DeploymentService
from app.services.recovery_service import RecoveryService, _recovery_actions


@pytest.mark.asyncio
async def test_agent4_to_agent2_recovery_execution():
    """Verify that Agent 4 sends approved recovery action to Agent 2 for validation and infrastructure execution."""
    mock_do_client = MagicMock()
    mock_do_client.rollback_deployment = AsyncMock(return_value={"status": "success"})
    mock_do_client.restart_application = AsyncMock(return_value={"status": "success"})
    mock_do_client.scale_service = AsyncMock(return_value={"status": "success"})

    deployment_service = DeploymentService(digitalocean_client=mock_do_client)
    agent2 = InfraDeployAgent(deployment_service=deployment_service)

    recovery_service = RecoveryService(infra_agent=agent2)
    agent4 = RecoveryVoiceAgent()
    agent4.recovery_service = recovery_service

    action_id = "REC-INTEG-001"
    action = RecoveryAction(
        id=action_id,
        trace_id="trace-12345",
        app_id="do-app-5555",
        deployment_id="deploy-6666",
        incident_id="deploy-6666",
        title="Rollback Deployment",
        description="Rollback to previous deployment",
        steps=[
            RecoveryStep(id="step-1", order=1, title="Rollback app spec", command="doctl apps update", verified=False, status="pending")
        ],
        risk_level="low",
        status=RecoveryStatus.APPROVAL_PENDING,
        estimated_duration="2 min"
    )
    _recovery_actions[action_id] = action

    # 1. Submit operator approval
    approval_req = RecoveryApprovalRequest(approved=True, approver="Lead SRE", approval_mode="ui")
    approved_action = agent4.process_approval(action_id, approval_req)
    assert approved_action.status == RecoveryStatus.APPROVED

    # 2. Trigger execution via Agent 4 (which dispatches to Agent 2)
    executed_action = await agent4.execute_recovery(action_id)

    # 3. Assert live progress and final status
    assert executed_action.status == RecoveryStatus.VERIFIED
    assert executed_action.steps[0].verified is True
    assert executed_action.steps[0].status == "completed"
    assert mock_do_client.rollback_deployment.called
    assert mock_do_client.rollback_deployment.call_args[1]["app_id"] == "do-app-5555"
    assert mock_do_client.rollback_deployment.call_args[1]["deployment_id"] == "deploy-6666"


@pytest.mark.asyncio
async def test_agent2_recovery_validation_failure():
    """Verify Agent 2 validates recovery payloads and rejects missing app_id/deployment_id."""
    deployment_service = DeploymentService()
    agent2 = InfraDeployAgent(deployment_service=deployment_service)

    invalid_action = RecoveryAction(
        id="REC-INVALID",
        trace_id="trace-00000",
        app_id=None,
        deployment_id=None,
        incident_id="",
        title="Restart Application",
        description="Restart app",
        steps=[],
        risk_level="low",
        status=RecoveryStatus.APPROVED,
        estimated_duration="1 min"
    )

    with pytest.raises(Exception) as exc_info:
        await agent2.execute_recovery(invalid_action)
    
    assert "Neither app_id nor incident_id was provided" in str(exc_info.value.detail)
