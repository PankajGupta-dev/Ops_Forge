import sys
import os
import unittest
import logging
from unittest.mock import AsyncMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from app.main import app
from app.agents.deployment_planner import deployment_planner_agent
from app.schemas.deployment import DeploymentPlan, ApplicationSpec, DeploymentConfig
from app.integrations.railway_client import RailwayAPIError


client = TestClient(app)

SAMPLE_DOCKERFILE = """
FROM python:3.11-slim
WORKDIR /app
COPY . .
EXPOSE 8080
CMD ["python", "main.py"]
"""

VALID_PLAN_PAYLOAD = {
    "application": {
        "name": "my-service-app",
        "runtime": "python",
        "base_image": "python:3.11-slim",
        "exposed_ports": [8080]
    },
    "deployment": {
        "platform": "railway",
        "region": "nyc3",
        "strategy": "rolling",
        "replicas": 2
    },
    "resources": {
        "cpu": "500m",
        "ram": "1Gi",
        "instance_size": "basic-xs"
    },
    "autoscaling": {
        "enabled": False,
        "min_instances": 1,
        "max_instances": 3
    },
    "database": {
        "required": False
    },
    "network": {
        "ports": [8080],
        "public_http": True
    },
    "environment": {
        "ENV": "production"
    },
    "healthcheck": {
        "path": "/healthz",
        "port": 8080
    }
}


class TestAgent1Agent2Integration(unittest.TestCase):

    def test_successful_deployment_request_pipeline(self):
        """
        Test 1: Successful deployment request (Agent 1 -> Agent 2 pipeline).
        """
        mock_plan = DeploymentPlan(
            application=ApplicationSpec(
                name="integrated-web-service",
                runtime="python",
                base_image="python:3.11-slim"
            ),
            deployment=DeploymentConfig(region="nyc3", replicas=2)
        )

        original_generate = deployment_planner_agent.planner_service.generate_plan
        deployment_planner_agent.planner_service.generate_plan = AsyncMock(return_value=mock_plan)

        try:
            request_payload = {
                "description": "Deploy python web service with 2 replicas",
                "dockerfile": SAMPLE_DOCKERFILE
            }

            response = client.post("/deploy", json=request_payload)
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "success")
            self.assertIn("rw-svc-integrated-web-service", data["app_id"])
            self.assertIn("https://", data["live_url"])
            self.assertIn("Deployment completed successfully on Railway", data["message"])
        finally:
            deployment_planner_agent.planner_service.generate_plan = original_generate

    def test_successful_deployment_response_direct_plan(self):
        """
        Test 2: Successful deployment response when supplying DeploymentPlan directly to Agent 2.
        """
        response = client.post("/deploy", json=VALID_PLAN_PAYLOAD)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["app_name"], "my-service-app")
        self.assertIn("https://", data["live_url"])
        self.assertEqual(data["details"]["replicas"], 2)

    def test_invalid_deployment_plan(self):
        """
        Test 3: Invalid deployment plan rejection by Agent 2 validator.
        """
        invalid_plan = dict(VALID_PLAN_PAYLOAD)
        invalid_plan["application"] = {
            "name": "INVALID_APP_NAME_WITH_CAPS!",
            "runtime": "python"
        }

        response = client.post("/deploy", json=invalid_plan)
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["detail"]["message"], "Validation failed for deployment plan.")
        self.assertTrue(any("must contain only lowercase alphanumeric characters" in err for err in data["detail"]["errors"]))

    def test_missing_required_fields(self):
        """
        Test 4: Missing required fields in PlannerRequest.
        """
        # Empty Dockerfile
        response1 = client.post("/deploy", json={"description": "Deploy service", "dockerfile": ""})
        self.assertEqual(response1.status_code, 400)
        self.assertIn("Dockerfile content cannot be empty", response1.json()["detail"])

        # Empty Description
        response2 = client.post("/deploy", json={"description": "   ", "dockerfile": SAMPLE_DOCKERFILE})
        self.assertEqual(response2.status_code, 400)
        self.assertIn("Deployment description cannot be empty", response2.json()["detail"])

    def test_agent2_deployment_failure_error_propagation(self):
        """
        Test 5 & 6: Agent 2 deployment failure handling and trace preservation.
        """
        mock_plan = DeploymentPlan(
            application=ApplicationSpec(
                name="failing-app",
                runtime="python"
            )
        )

        orig_generate = deployment_planner_agent.planner_service.generate_plan
        orig_poll = deployment_planner_agent.infra_agent.deployment_service.railway_client.poll_deployment_until_terminal

        deployment_planner_agent.planner_service.generate_plan = AsyncMock(return_value=mock_plan)
        deployment_planner_agent.infra_agent.deployment_service.railway_client.poll_deployment_until_terminal = AsyncMock(
            return_value={"status": "FAILED", "deployment_id": "dep-fail-001", "message": "Build failed"}
        )

        try:
            response = client.post("/deploy", json=VALID_PLAN_PAYLOAD)

            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["status"], "failed")
            self.assertIn("trace-", data["trace_id"])
            self.assertIn("Railway deployment failed", data["message"])
        finally:
            deployment_planner_agent.planner_service.generate_plan = orig_generate
            deployment_planner_agent.infra_agent.deployment_service.railway_client.poll_deployment_until_terminal = orig_poll

    def test_logging_during_integration_flow(self):
        """
        Test 7: Logging output verification across Agent 1 and Agent 2 pipeline.
        """
        mock_plan = DeploymentPlan(
            application=ApplicationSpec(
                name="logging-test-app",
                runtime="python"
            )
        )

        orig_generate = deployment_planner_agent.planner_service.generate_plan
        deployment_planner_agent.planner_service.generate_plan = AsyncMock(return_value=mock_plan)

        try:
            with self.assertLogs(level=logging.INFO) as log_context:
                request_payload = {
                    "description": "Test logging pipeline execution",
                    "dockerfile": SAMPLE_DOCKERFILE
                }

                response = client.post("/deploy", json=request_payload)
                self.assertEqual(response.status_code, 200)

                log_messages = log_context.output
                self.assertTrue(any("Triggering integrated Agent 1 -> Agent 2 deployment pipeline" in msg for msg in log_messages))
                self.assertTrue(any("Agent 1: Generating deployment plan for integration pipeline" in msg for msg in log_messages))
                self.assertTrue(any("Agent 2 (Infra & Deploy) received plan for application 'logging-test-app'" in msg for msg in log_messages))
        finally:
            deployment_planner_agent.planner_service.generate_plan = orig_generate


if __name__ == "__main__":
    unittest.main()
