import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.utils.docker_parser import parse_dockerfile
from app.schemas.deployment import PlannerRequest, DeploymentPlan

client = TestClient(app)

SAMPLE_DOCKERFILE = """
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
ENV PORT=8080
ENV NODE_ENV=production
EXPOSE 8080
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
"""

def test_docker_parser_deterministic():
    analysis = parse_dockerfile(SAMPLE_DOCKERFILE)
    assert analysis.runtime == "python"
    assert analysis.base_image == "python:3.11-slim"
    assert analysis.language == "python"
    assert analysis.exposed_ports == [8080]
    assert analysis.env_vars.get("PORT") == "8080"
    assert analysis.entry_command == ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

def test_api_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_api_empty_dockerfile_validation():
    response = client.post("/plan", json={"description": "Deploy app", "dockerfile": ""})
    assert response.status_code == 400
    assert "Dockerfile content cannot be empty" in response.json()["detail"]

def test_api_empty_description_validation():
    response = client.post("/plan", json={"description": "   ", "dockerfile": SAMPLE_DOCKERFILE})
    assert response.status_code == 400
    assert "Deployment description cannot be empty" in response.json()["detail"]
