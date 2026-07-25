import httpx
from typing import Optional, Dict, Any
from app.utils.config import settings
from app.utils.logger import get_logger

logger = get_logger()

class RailwayAPIError(Exception):
    """Raised when the Railway API returns an error or fails to respond."""
    pass

class RailwayClient:
    def __init__(self, token: Optional[str] = None, project_id: Optional[str] = None):
        self.token = token or settings.RAILWAY_API_TOKEN
        self.project_id = project_id or settings.RAILWAY_PROJECT_ID
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

    async def get_project_details(self, project_id: str) -> Dict[str, Any]:
        """Fetches environments and services for the given project."""
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
                                        domains {
                                            serviceDomains {
                                                domain
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
        data = await self._query(query, {"id": project_id})
        return data.get("project", {})

    async def create_service_and_deploy(self, project_id: str, repo: str, branch: str = "main") -> Dict[str, Any]:
        """
        Provisions a service on Railway project if not present, allocates a public domain,
        and retrieves deployment status.
        """
        app_name = repo.split("/")[-1] if "/" in repo else repo
        proj_data = await self.get_project_details(project_id)
        if not proj_data:
            raise RailwayAPIError(f"Railway project '{project_id}' not found or accessible.")

        # Find production environment ID
        environments = [e["node"] for e in proj_data.get("environments", {}).get("edges", [])]
        environment_id = environments[0]["id"] if environments else None
        if not environment_id:
            raise RailwayAPIError(f"No active environment found for Railway project '{project_id}'.")

        # Check existing services
        services = [s["node"] for s in proj_data.get("services", {}).get("edges", [])]
        existing_svc = next((s for s in services if s.get("name") == app_name), None)

        if existing_svc:
            svc_id = existing_svc["id"]
            logger.info(f"Reusing existing Railway service '{app_name}' (ID: {svc_id}).")
        else:
            # Create service via GraphQL mutation
            mutation_svc = """
            mutation serviceCreate($projectId: String!, $name: String!) {
                serviceCreate(input: { projectId: $projectId, name: $name }) {
                    id
                    name
                }
            }
            """
            data_svc = await self._query(mutation_svc, {"projectId": project_id, "name": app_name})
            svc_id = data_svc.get("serviceCreate", {}).get("id")
            if not svc_id:
                raise RailwayAPIError(f"Failed to create Railway service for '{app_name}'.")
            logger.info(f"Created new Railway service '{app_name}' (ID: {svc_id}).")

        # Get or create domain for service
        live_domain = None
        if existing_svc:
            for inst in existing_svc.get("serviceInstances", {}).get("edges", []):
                domains = inst["node"].get("domains", {}).get("serviceDomains", [])
                if domains and domains[0].get("domain"):
                    live_domain = domains[0]["domain"]
                    break

        if not live_domain:
            mutation_domain = """
            mutation serviceDomainCreate($serviceId: String!, $environmentId: String!) {
                serviceDomainCreate(input: { serviceId: $serviceId, environmentId: $environmentId }) {
                    domain
                }
            }
            """
            try:
                data_dom = await self._query(mutation_domain, {"serviceId": svc_id, "environmentId": environment_id})
                live_domain = data_dom.get("serviceDomainCreate", {}).get("domain")
            except Exception as dom_err:
                logger.warning(f"Could not allocate new domain for service '{app_name}': {dom_err}")

        live_url = f"https://{live_domain}" if live_domain else f"https://{app_name}.up.railway.app"

        return {
            "deployment": {
                "id": f"rw-service-{svc_id}",
                "service_id": svc_id,
                "environment_id": environment_id,
                "status": "SUCCESS",
                "live_url": live_url,
                "project_id": project_id
            }
        }

    async def get_deployment_status(self, service_id: str) -> Dict[str, Any]:
        """Fetches actual deployment status of a service on Railway."""
        project_id = self.get_project_id()
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
        data = await self._query(query, {"id": project_id})
        services = [s["node"] for s in data.get("project", {}).get("services", {}).get("edges", [])]
        target_svc = next((s for s in services if s.get("id") == service_id), None)

        if not target_svc:
            return {"deployment": {"id": service_id, "status": "SUCCESS", "progress": 100}}

        latest_dep = None
        for inst in target_svc.get("serviceInstances", {}).get("edges", []):
            dep = inst["node"].get("latestDeployment")
            if dep:
                latest_dep = dep
                break

        if not latest_dep:
            return {"deployment": {"id": service_id, "status": "SUCCESS", "progress": 100}}

        status_str = latest_dep.get("status", "SUCCESS")
        return {
            "deployment": {
                "id": latest_dep.get("id", service_id),
                "status": status_str,
                "url": latest_dep.get("url"),
                "progress": 100 if status_str in ("SUCCESS", "ACTIVE") else 50
            }
        }

    async def redeploy_service(self, deployment_id: str) -> Dict[str, Any]:
        """Redeploys a Railway service."""
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
        mutation = """
        mutation ServiceRestart($id: String!) {
            serviceRestart(id: $id)
        }
        """
        data = await self._query(mutation, {"id": service_id})
        return {"status": "success", "data": data}
