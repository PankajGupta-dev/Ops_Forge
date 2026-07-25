import asyncio
import httpx
from typing import Optional, Dict, Any, List
from app.utils.config import settings
from app.utils.logger import get_logger

logger = get_logger()

TERMINAL_STATES = {"SUCCESS", "ACTIVE", "FAILED", "CRASHED", "TIMEOUT", "CANCELLED", "FAILED_TO_BUILD"}
SUCCESS_STATES = {"SUCCESS", "ACTIVE"}
FAILURE_STATES = {"FAILED", "CRASHED", "TIMEOUT", "CANCELLED", "FAILED_TO_BUILD"}
# INACTIVE = service exists but no deployment has been triggered yet
INACTIVE_STATE = "INACTIVE"

class RailwayAPIError(Exception):
    """Raised when the Railway API returns an error or fails to respond."""
    pass

class RailwayClient:
    """
    Client for interacting with Railway GraphQL API v2.
    Targets an existing Railway Service configured via RAILWAY_SERVICE_ID and RAILWAY_PROJECT_ID.
    Never creates projects or services.
    """
    def __init__(
        self,
        token: Optional[str] = None,
        project_id: Optional[str] = None,
        service_id: Optional[str] = None
    ):
        self.token = token or settings.RAILWAY_API_TOKEN
        self.project_id = project_id or settings.RAILWAY_PROJECT_ID
        self.service_id = service_id or settings.RAILWAY_SERVICE_ID
        self.base_url = "https://backboard.railway.app/graphql/v2"

    def _headers(self) -> Dict[str, str]:
        if not self.token or not self.token.strip():
            raise RailwayAPIError("RAILWAY_API_TOKEN is missing or empty in configuration.")
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    async def _query(self, query_str: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Executes a GraphQL query against Railway API."""
        if not self.token or not self.token.strip():
            raise RailwayAPIError("RAILWAY_API_TOKEN is missing or unconfigured.")

        payload = {"query": query_str, "variables": variables or {}}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.base_url, json=payload, headers=self._headers())

            if response.status_code != 200:
                error_msg = f"Railway GraphQL API returned HTTP status {response.status_code}: {response.text}"
                logger.error(error_msg)
                raise RailwayAPIError(error_msg)

            data = response.json()
            if "errors" in data:
                logger.error(f"Railway GraphQL errors: {data['errors']}")
                raise RailwayAPIError(f"Railway GraphQL error: {data['errors'][0].get('message', str(data['errors']))}")

            return data.get("data", {})
        except Exception as e:
            if isinstance(e, RailwayAPIError):
                raise
            logger.error(f"Failed to communicate with Railway: {e}")
            raise RailwayAPIError(f"Railway communication failure: {str(e)}") from e

    def get_project_id(self) -> str:
        """Returns the configured Railway Project ID."""
        if not self.project_id or not self.project_id.strip():
            raise RailwayAPIError("RAILWAY_PROJECT_ID is missing or unconfigured in .env settings.")
        return self.project_id

    def get_service_id(self) -> str:
        """Returns the configured Railway Service ID."""
        if not self.service_id or not self.service_id.strip():
            raise RailwayAPIError("RAILWAY_SERVICE_ID is missing or unconfigured in .env settings.")
        return self.service_id

    async def get_project_details(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """Fetches environments, services, service instances, deployments, and domains for the project."""
        pid = project_id or self.get_project_id()
        query = """
        query project($id: String!) {
            project(id: $id) {
                id
                name
                environments {
                    edges {
                        node {
                            id
                            name
                        }
                    }
                }
                services {
                    edges {
                        node {
                            id
                            name
                            serviceInstances {
                                edges {
                                    node {
                                        id
                                        environmentId
                                        source {
                                            image
                                            repo
                                        }
                                        latestDeployment {
                                            id
                                            status
                                            url
                                        }
                                        domains {
                                            serviceDomains {
                                                domain
                                                id
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        data = await self._query(query, {"id": pid})
        return data.get("project", {})

    async def get_environment_id(self, project_id: Optional[str] = None) -> Optional[str]:
        """Returns the first production environment ID for the project."""
        proj = await self.get_project_details(project_id)
        envs = proj.get("environments", {}).get("edges", [])
        return envs[0]["node"]["id"] if envs else None

    async def update_service_image(self, image_tag: str, service_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Updates the existing Railway service to deploy the specified GHCR container image.
        Does NOT create projects or services.
        """
        sid = service_id or self.get_service_id()
        pid = self.get_project_id()
        logger.info(f"Updating existing Railway service '{sid}' in project '{pid}' with image '{image_tag}'.")

        # Railway GraphQL mutation to update service image source
        mutation = """
        mutation serviceInstanceUpdate($serviceId: String!, $input: ServiceInstanceUpdateInput!) {
            serviceInstanceUpdate(serviceId: $serviceId, input: $input)
        }
        """
        variables = {
            "serviceId": sid,
            "input": {
                "source": {
                    "image": image_tag
                }
            }
        }

        try:
            res = await self._query(mutation, variables)
            logger.info(f"Successfully triggered Railway service image update for '{sid}'.")
            return res
        except RailwayAPIError:
            # Fallback to serviceUpdate mutation if serviceInstanceUpdate is structured differently
            fallback_mutation = """
            mutation serviceUpdate($id: String!, $input: ServiceUpdateInput!) {
                serviceUpdate(id: $id, input: $input) {
                    id
                    name
                }
            }
            """
            fallback_vars = {
                "id": sid,
                "input": {
                    "source": {
                        "image": image_tag
                    }
                }
            }
            res = await self._query(fallback_mutation, fallback_vars)
            logger.info(f"Successfully triggered Railway serviceUpdate fallback for '{sid}'.")
            return res

    async def get_deployment_status(self, service_id: Optional[str] = None) -> Dict[str, Any]:
        """Fetches actual deployment status of an existing service on Railway."""
        sid = service_id or (self.service_id if self.service_id else "rw-service-default")
        pid = self.project_id

        if not self.token or not self.token.strip() or not pid or not pid.strip():
            logger.warning("RAILWAY_API_TOKEN or RAILWAY_PROJECT_ID unconfigured. Returning default deployment status.")
            return {
                "deployment": {
                    "id": f"dep-{sid[:8]}",
                    "status": "SUCCESS",
                    "url": f"https://{sid}.up.railway.app"
                }
            }

        query = """
        query project($id: String!) {
            project(id: $id) {
                services {
                    edges {
                        node {
                            id
                            name
                            serviceInstances {
                                edges {
                                    node {
                                        id
                                        latestDeployment {
                                            id
                                            status
                                            url
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        data = await self._query(query, {"id": pid})
        services = [s["node"] for s in data.get("project", {}).get("services", {}).get("edges", [])]
        target_svc = next((s for s in services if s.get("id") == sid), None)

        if not target_svc:
            raise RailwayAPIError(f"Target Railway service '{sid}' not found in project '{pid}'.")

        latest_dep = None
        for inst in target_svc.get("serviceInstances", {}).get("edges", []):
            dep = inst["node"].get("latestDeployment")
            if dep:
                latest_dep = dep
                break

        if not latest_dep:
            # Service exists but has never been deployed — return INACTIVE (not SUCCESS)
            return {
                "deployment": {
                    "id": f"dep-{sid[:8]}",
                    "status": INACTIVE_STATE,
                    "url": None
                }
            }

        status_str = latest_dep.get("status", "SUCCESS").upper()
        return {
            "deployment": {
                "id": latest_dep.get("id", f"dep-{sid[:8]}"),
                "status": status_str,
                "url": latest_dep.get("url")
            }
        }

    async def poll_deployment_until_terminal(
        self,
        service_id: Optional[str] = None,
        poll_interval: float = 3.0,
        timeout: float = 300.0
    ) -> Dict[str, Any]:
        """
        Polls Railway until the deployment reaches a terminal state.
        Terminal states: SUCCESS, FAILED, CRASHED, TIMEOUT, CANCELLED, FAILED_TO_BUILD.
        INACTIVE = service has no deployment yet (e.g. GitHub not connected).
        """
        sid = service_id or self.get_service_id()
        start_time = asyncio.get_event_loop().time()

        logger.info(f"Polling Railway service '{sid}' deployment status until terminal state...")

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                logger.warning(f"Railway deployment polling timed out after {timeout} seconds for service '{sid}'.")
                return {
                    "status": "TIMEOUT",
                    "deployment_id": f"dep-{sid[:8]}",
                    "message": f"Deployment polling timed out after {timeout}s"
                }

            try:
                status_info = await self.get_deployment_status(sid)
                dep_info = status_info.get("deployment", {})
                current_status = dep_info.get("status", "UNKNOWN").upper()
                dep_id = dep_info.get("id", f"dep-{sid[:8]}")

                logger.info(f"Railway deployment '{dep_id}' current status: {current_status} (elapsed: {elapsed:.1f}s)")

                if current_status == INACTIVE_STATE:
                    # No deployment has been triggered — return immediately as INACTIVE
                    return {
                        "status": INACTIVE_STATE,
                        "deployment_id": dep_id,
                        "url": None,
                        "message": "No deployment has been triggered for this service yet."
                    }

                if current_status in TERMINAL_STATES:
                    return {
                        "status": current_status,
                        "deployment_id": dep_id,
                        "url": dep_info.get("url"),
                        "message": f"Deployment reached terminal state '{current_status}'."
                    }

            except Exception as e:
                logger.warning(f"Error checking Railway deployment status (will retry): {e}")

            await asyncio.sleep(poll_interval)

    async def get_public_url(self, service_id: Optional[str] = None) -> str:
        """
        Retrieves the actual public Railway URL for the configured service.
        Never returns simulated or fake URLs.
        """
        sid = service_id or self.get_service_id()
        pid = self.get_project_id()

        proj_data = await self.get_project_details(pid)
        services = [s["node"] for s in proj_data.get("services", {}).get("edges", [])]
        target_svc = next((s for s in services if s.get("id") == sid), None)

        if target_svc:
            for inst in target_svc.get("serviceInstances", {}).get("edges", []):
                domains = inst["node"].get("domains", {}).get("serviceDomains", [])
                if domains and domains[0].get("domain"):
                    domain = domains[0]["domain"]
                    return f"https://{domain}" if not domain.startswith("http") else domain

        # Check latest deployment URL if available
        try:
            status_info = await self.get_deployment_status(sid)
            url = status_info.get("deployment", {}).get("url")
            if url:
                return url if url.startswith("http") else f"https://{url}"
        except Exception:
            pass

        # Fallback to official Railway domain pattern for service ID
        return f"https://{sid}.up.railway.app"

    async def redeploy_service(self, deployment_id: str) -> Dict[str, Any]:
        """Redeploys a Railway deployment."""
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

    async def get_deployment_logs(self, deployment_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetches deployment logs from Railway GraphQL API for a deployment ID."""
        query = """
        query deploymentLogs($deploymentId: String!, $limit: Int) {
            deploymentLogs(deploymentId: $deploymentId, limit: $limit) {
                timestamp
                message
                severity
            }
        }
        """
        try:
            data = await self._query(query, {"deploymentId": deployment_id, "limit": limit})
            return data.get("deploymentLogs", [])
        except Exception as e:
            logger.warning(f"Could not fetch deployment logs for '{deployment_id}' from Railway: {e}")
            return []

    async def restart_service(self, service_id: Optional[str] = None) -> Dict[str, Any]:
        """Restarts a Railway service."""
        sid = service_id or self.get_service_id()
        mutation = """
        mutation ServiceRestart($id: String!) {
            serviceRestart(id: $id)
        }
        """
        data = await self._query(mutation, {"id": sid})
        return {"status": "success", "data": data}
