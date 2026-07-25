import pytest
from unittest.mock import AsyncMock, MagicMock

from app.schemas.deployment import DeploymentPlan, DeploymentResult, ApplicationSpec
from app.schemas.incident import IncidentAnalysisRequest, IncidentReport
from app.services.pipeline_bridge_service import PipelineBridgeService
from app.agents.infra_deploy import InfraDeployAgent


def test_pipeline_bridge_transformation():
    """Verify PipelineBridgeService preserves trace_id, app_id, deployment_id, app_name, status, live_url, created_at, and details."""
    result = DeploymentResult(
        trace_id="trace-123456",
        status="success",
        app_id="do-app-9999",
        deployment_id="deploy-8888",
        app_name="checkout-service",
        live_url="https://checkout.ondigitalocean.app",
        message="Deployed successfully",
        created_at="2026-07-25T11:00:00Z",
        details={"region": "nyc3", "replicas": 2}
    )

    request = PipelineBridgeService.transform_deployment_to_incident_request(result)

    assert isinstance(request, IncidentAnalysisRequest)
    assert request.trace_id == "trace-123456"
    assert request.app_id == "do-app-9999"
    assert request.deployment_id == "deploy-8888"
    assert request.app_name == "checkout-service"
    assert request.deployment_status == "success"
    assert request.infrastructure_metadata["live_url"] == "https://checkout.ondigitalocean.app"
    assert request.infrastructure_metadata["created_at"] == "2026-07-25T11:00:00Z"
    assert request.infrastructure_metadata["region"] == "nyc3"
    assert len(request.events) >= 1
    assert request.events[0].event_type == "DEPLOY_COMPLETED"


@pytest.mark.asyncio
async def test_agent2_to_agent3_automatic_transmission():
    """Verify Agent 2 automatically sends metadata to Agent 3 upon active deployment."""
    mock_deploy_service = MagicMock()
    mock_deploy_result = DeploymentResult(
        trace_id="trace-abc123",
        status="success",
        app_id="do-app-100",
        deployment_id="deploy-200",
        app_name="payment-api",
        live_url="https://payment.ondigitalocean.app",
        message="Active",
        created_at="2026-07-25T11:05:00Z",
        details={"phase": "ACTIVE"}
    )
    mock_deploy_service.execute_deployment = AsyncMock(return_value=mock_deploy_result)

    mock_rca_agent = MagicMock()
    mock_rca_agent.run = AsyncMock(return_value=MagicMock(spec=IncidentReport))

    agent2 = InfraDeployAgent(
        deployment_service=mock_deploy_service,
        root_cause_agent=mock_rca_agent
    )

    plan = DeploymentPlan(
        application=ApplicationSpec(name="payment-api", runtime="python")
    )

    result = await agent2.deploy(plan)

    assert result.status == "success"
    assert mock_rca_agent.run.called
    
    # Check the IncidentAnalysisRequest payload delivered to Agent 3
    called_request = mock_rca_agent.run.call_args[0][0]
    assert isinstance(called_request, IncidentAnalysisRequest)
    assert called_request.trace_id == "trace-abc123"
    assert called_request.app_id == "do-app-100"
    assert called_request.deployment_id == "deploy-200"
    assert called_request.app_name == "payment-api"
    assert called_request.deployment_status == "success"
    assert called_request.infrastructure_metadata["live_url"] == "https://payment.ondigitalocean.app"
