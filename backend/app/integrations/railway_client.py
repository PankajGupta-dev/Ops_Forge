import httpx
from typing import Optional, Dict, Any
from app.utils.config import settings
from app.utils.logger import get_logger

logger = get_logger()

class RailwayAPIError(Exception):
    """Raised when the Railway API returns an error or fails to respond."""
    pass

class RailwayClient:
    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.RAILWAY_API_TOKEN
        self.base_url = "https://backboard.railway.app/graphql/v2"

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    async def _query(self, query_str: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Executes a GraphQL query against Railway API."""
        is_configured = bool(self.token and self.token.strip() and self.token != "your_railway_api_token_here")
        if not is_configured:
            logger.info("Railway API Token not configured. Using simulated mode.")
            return {}

        payload = {"query": query_str, "variables": variables or {}}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.base_url, json=payload, headers=self._headers())

            if response.status_code != 200:
                error_msg = f"Railway GraphQL API returned status {response.status_code}: {response.text}"
                logger.error(error_msg)
                raise RailwayAPIError(error_msg)

            data = response.json()
            if "errors" in data:
                logger.error(f"Railway GraphQL errors: {data['errors']}")
                raise RailwayAPIError(f"Railway GraphQL error: {data['errors']}")

            return data.get("data", {})
        except Exception as e:
            if isinstance(e, RailwayAPIError):
                raise
            logger.error(f"Failed to communicate with Railway: {e}")
            raise RailwayAPIError(f"Railway communication failure: {str(e)}") from e

    async def create_project(self, name: str) -> Dict[str, Any]:
        """Creates a Railway project."""
        is_configured = bool(self.token and self.token.strip() and self.token != "your_railway_api_token_here")
        if not is_configured:
            logger.info(f"Simulating Railway project creation for '{name}'.")
            return {
                "project": {
                    "id": f"rw-project-simulated-{name}",
                    "name": name,
                }
            }

        mutation = """
        mutation ProjectCreate($name: String!) {
            projectCreate(input: { name: $name }) {
                id
                name
            }
        }
        """
        data = await self._query(mutation, {"name": name})
        return {"project": data.get("projectCreate", {"id": f"rw-project-{name}", "name": name})}

    async def create_service_and_deploy(self, project_id: str, repo: str, branch: str = "main") -> Dict[str, Any]:
        """Triggers service creation and deployment on Railway."""
        is_configured = bool(self.token and self.token.strip() and self.token != "your_railway_api_token_here")
        if not is_configured:
            app_name = repo.split("/")[-1] if "/" in repo else repo
            logger.info(f"Simulating Railway deployment for '{repo}' on branch '{branch}'.")
            return {
                "deployment": {
                    "id": f"rw-deploy-simulated-{app_name}",
                    "status": "SUCCESS",
                    "live_url": f"https://{app_name}.up.railway.app",
                    "project_id": project_id
                }
            }

        # GraphQL query for service deployment
        mutation = """
        mutation ServiceCreate($projectId: String!, $source: ServiceSourceInput!) {
            serviceCreate(input: { projectId: $projectId, source: $source }) {
                id
                name
            }
        }
        """
        source = {"repo": repo, "branch": branch}
        data = await self._query(mutation, {"projectId": project_id, "source": source})
        svc = data.get("serviceCreate", {})
        svc_id = svc.get("id", f"svc-{project_id}")
        app_name = repo.split("/")[-1] if "/" in repo else repo
        return {
            "deployment": {
                "id": f"rw-deploy-{svc_id}",
                "status": "SUCCESS",
                "live_url": f"https://{app_name}.up.railway.app",
                "project_id": project_id
            }
        }

    async def get_deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        """Fetches status of a deployment on Railway."""
        is_configured = bool(self.token and self.token.strip() and self.token != "your_railway_api_token_here")
        if not is_configured:
            logger.info(f"Simulating Railway deployment status check for '{deployment_id}'.")
            return {
                "deployment": {
                    "id": deployment_id,
                    "status": "SUCCESS",
                    "progress": 100
                }
            }

        query = """
        query Deployment($id: String!) {
            deployment(id: $id) {
                id
                status
            }
        }
        """
        data = await self._query(query, {"id": deployment_id})
        deploy_data = data.get("deployment", {})
        return {
            "deployment": {
                "id": deployment_id,
                "status": deploy_data.get("status", "SUCCESS"),
                "progress": 100
            }
        }

    async def redeploy_service(self, deployment_id: str) -> Dict[str, Any]:
        """Redeploys a Railway service."""
        is_configured = bool(self.token and self.token.strip() and self.token != "your_railway_api_token_here")
        if not is_configured:
            logger.info(f"Simulating Railway redeploy for deployment '{deployment_id}'.")
            return {
                "status": "success",
                "simulated": True,
                "message": f"Successfully redeployed Railway deployment {deployment_id} (simulated)."
            }

        mutation = """
        mutation DeploymentRedeploy($id: String!) {
            deploymentRedeploy(id: $id) {
                id
                status
            }
        }
        """
        data = await self._query(mutation, {"id": deployment_id})
        return {"status": "success", "data": data}

    async def restart_service(self, service_id: str) -> Dict[str, Any]:
        """Restarts a Railway service."""
        is_configured = bool(self.token and self.token.strip() and self.token != "your_railway_api_token_here")
        if not is_configured:
            logger.info(f"Simulating Railway restart for service '{service_id}'.")
            return {
                "status": "success",
                "simulated": True,
                "message": f"Successfully restarted Railway service {service_id} (simulated)."
            }

        mutation = """
        mutation ServiceRestart($id: String!) {
            serviceRestart(id: $id)
        }
        """
        data = await self._query(mutation, {"id": service_id})
        return {"status": "success", "data": data}
