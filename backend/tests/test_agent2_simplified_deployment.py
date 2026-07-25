import sys
import os
import unittest
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.schemas.deployment import DeploymentPlan, ApplicationSpec, DeploymentConfig, DeploymentResult
from app.services.deployment_service import DeploymentService
from app.integrations.railway_client import RailwayClient, RailwayAPIError
from app.agents.infra_deploy import InfraDeployAgent

class TestAgent2SimplifiedDeployment(unittest.IsolatedAsyncioTestCase):
    """
    Comprehensive integration tests for Agent 2 simplified deployment pipeline:
    1. Repository clone
    2. Docker build
    3. GHCR authentication & image push
    4. Railway deployment update
    5. Deployment polling until terminal state
    6. Deployment failure handling & trace preservation
    7. Deployment URL retrieval
    """

    async def asyncSetUp(self):
        self.mock_railway_client = MagicMock(spec=RailwayClient)
        self.mock_railway_client.get_service_id = MagicMock(return_value="srv-test-railway-123")
        self.mock_railway_client.get_project_id = MagicMock(return_value="proj-test-railway-456")
        self.mock_railway_client.update_service_image = AsyncMock(return_value={"status": "success"})
        self.mock_railway_client.poll_deployment_until_terminal = AsyncMock(return_value={
            "status": "SUCCESS",
            "deployment_id": "dep-railway-999",
            "url": "https://test-app.up.railway.app"
        })
        self.mock_railway_client.get_public_url = AsyncMock(return_value="https://test-app.up.railway.app")

        self.deployment_service = DeploymentService(railway_client=self.mock_railway_client)

    async def test_successful_simplified_deployment_pipeline(self):
        """
        Tests complete successful pipeline:
        repo clone -> Dockerfile verify -> Docker build -> GHCR auth & push -> Railway update -> Polling -> URL retrieval
        """
        async def mock_run_cmd(cmd, cwd=None, input_str=None):
            if "clone" in cmd:
                target_dir = cmd[-1]
                os.makedirs(target_dir, exist_ok=True)
                with open(os.path.join(target_dir, "Dockerfile"), "w") as f:
                    f.write("FROM python:3.11-slim\nWORKDIR /app\n")
            return (0, "Success", "")

        with patch.object(DeploymentService, "_run_command", side_effect=mock_run_cmd):
            plan = DeploymentPlan(
                application=ApplicationSpec(name="test-web-app", runtime="python"),
                deployment=DeploymentConfig(replicas=1)
            )

            result = await self.deployment_service.execute_deployment(
                plan=plan,
                repository="PankajGupta-dev/demo-app",
                branch="main"
            )

            # 1. Assert result metadata
            self.assertEqual(result.status, "success")
            self.assertTrue(result.trace_id.startswith("trace-"))
            self.assertEqual(result.app_id, "srv-test-railway-123")
            self.assertEqual(result.deployment_id, "dep-railway-999")
            self.assertEqual(result.live_url, "https://test-app.up.railway.app")
            self.assertIsNotNone(result.build_duration)
            self.assertIsNotNone(result.deployment_duration)

            # 2. Assert Railway API invocations
            self.mock_railway_client.update_service_image.assert_called_once()
            self.mock_railway_client.poll_deployment_until_terminal.assert_called_once_with(service_id="srv-test-railway-123")
            self.mock_railway_client.get_public_url.assert_called_once_with(service_id="srv-test-railway-123")

    @patch.object(DeploymentService, "_run_command")
    async def test_dockerfile_missing_failure(self, mock_run_cmd):
        """
        Tests handling when Dockerfile is missing in repository.
        Must return status='failed', preserve trace_id, and halt pipeline.
        """
        async def mock_clone(cmd, cwd=None, input_str=None):
            if "clone" in cmd:
                target_dir = cmd[-1]
                os.makedirs(target_dir, exist_ok=True)
                # Intentionally leave Dockerfile missing
            return (0, "Cloned", "")

        mock_run_cmd.side_effect = mock_clone

        plan = DeploymentPlan(
            application=ApplicationSpec(name="missing-dockerfile-app", runtime="node")
        )

        result = await self.deployment_service.execute_deployment(
            plan=plan,
            repository="PankajGupta-dev/missing-dockerfile-repo",
            branch="main"
        )

        self.assertEqual(result.status, "failed")
        self.assertTrue(result.trace_id.startswith("trace-"))
        self.assertIn("Dockerfile missing", result.message)
        # Should not attempt Railway update if Dockerfile is missing
        self.mock_railway_client.update_service_image.assert_not_called()

    async def test_railway_deployment_terminal_failure(self):
        """
        Tests polling when Railway deployment reaches a terminal FAILED state.
        """
        async def mock_run_cmd(cmd, cwd=None, input_str=None):
            if "clone" in cmd:
                target_dir = cmd[-1]
                os.makedirs(target_dir, exist_ok=True)
                with open(os.path.join(target_dir, "Dockerfile"), "w") as f:
                    f.write("FROM python:3.11-slim\n")
            return (0, "Success", "")

        self.mock_railway_client.poll_deployment_until_terminal = AsyncMock(return_value={
            "status": "FAILED",
            "deployment_id": "dep-failed-001",
            "message": "Application crashed on boot"
        })

        with patch.object(DeploymentService, "_run_command", side_effect=mock_run_cmd):
            plan = DeploymentPlan(
                application=ApplicationSpec(name="crashing-app", runtime="python")
            )

            result = await self.deployment_service.execute_deployment(
                plan=plan,
                repository="PankajGupta-dev/demo",
                branch="main"
            )

            self.assertEqual(result.status, "failed")
            self.assertTrue(result.trace_id.startswith("trace-"))
            self.assertIn("FAILED", result.message)
            self.assertEqual(result.details["terminal_state"], "FAILED")

    async def test_agent2_agent3_handoff_prevention_on_failure(self):
        """
        Verifies Agent 2 does NOT send metadata to Agent 3 if deployment fails.
        """
        mock_rca_agent = MagicMock()
        mock_rca_agent.run = AsyncMock()

        self.mock_railway_client.poll_deployment_until_terminal = AsyncMock(return_value={
            "status": "CRASHED",
            "deployment_id": "dep-crashed-002"
        })

        agent2 = InfraDeployAgent(
            deployment_service=self.deployment_service,
            root_cause_agent=mock_rca_agent
        )

        plan = DeploymentPlan(
            application=ApplicationSpec(name="crashed-service", runtime="python")
        )

        result = await agent2.deploy(plan)

        self.assertEqual(result.status, "failed")
        self.assertTrue(result.trace_id.startswith("trace-"))
        mock_rca_agent.run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
