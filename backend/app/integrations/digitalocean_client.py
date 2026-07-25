import httpx
from typing import Optional, Dict, Any
from app.utils.config import settings
from app.utils.logger import get_logger

logger = get_logger()

class DigitalOceanAPIError(Exception):
    """Raised when the DigitalOcean API returns an error or fails to respond."""
    pass

class DigitalOceanClient:
    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.DIGITALOCEAN_API_TOKEN
        self.base_url = "https://api.digitalocean.com/v2"

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    async def rollback_deployment(self, app_id: str, deployment_id: str) -> Dict[str, Any]:
        """
        Rollback a DigitalOcean app deployment to a previous deployment.
        """
        is_configured = self.token and self.token.strip() and self.token != "your_digitalocean_api_token_here"
        if not is_configured:
            logger.info(f"DigitalOcean API Token not configured. Simulating rollback for app '{app_id}' to deployment '{deployment_id}'.")
            return {
                "status": "success",
                "simulated": True,
                "message": f"Successfully rolled back application {app_id} to deployment {deployment_id} (simulated)."
            }

        url = f"{self.base_url}/apps/{app_id}/deployments"
        payload = {
            "rollback_to_deployment_id": deployment_id
        }

        logger.info(f"Triggering DigitalOcean rollback for app {app_id} to deployment {deployment_id}")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=self._headers())

            if response.status_code not in (200, 201, 202):
                error_msg = f"DigitalOcean API returned status {response.status_code}: {response.text}"
                logger.error(error_msg)
                raise DigitalOceanAPIError(error_msg)

            return response.json()
        except Exception as e:
            logger.error(f"Failed to communicate with DigitalOcean: {e}")
            raise DigitalOceanAPIError(f"DigitalOcean communication failure: {str(e)}") from e

    async def restart_application(self, app_id: str) -> Dict[str, Any]:
        """
        Force a rebuild/re-deploy to restart application instances.
        """
        is_configured = self.token and self.token.strip() and self.token != "your_digitalocean_api_token_here"
        if not is_configured:
            logger.info(f"DigitalOcean API Token not configured. Simulating restart for app '{app_id}'.")
            return {
                "status": "success",
                "simulated": True,
                "message": f"Successfully restarted application {app_id} (simulated)."
            }

        url = f"{self.base_url}/apps/{app_id}/deployments"
        payload = {
            "force_rebuild": True
        }

        logger.info(f"Triggering DigitalOcean restart (force rebuild) for app {app_id}")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=self._headers())

            if response.status_code not in (200, 201, 202):
                error_msg = f"DigitalOcean API returned status {response.status_code}: {response.text}"
                logger.error(error_msg)
                raise DigitalOceanAPIError(error_msg)

            return response.json()
        except Exception as e:
            logger.error(f"Failed to restart app via DigitalOcean: {e}")
            raise DigitalOceanAPIError(f"DigitalOcean communication failure: {str(e)}") from e

    async def scale_service(self, app_id: str, service_name: str, replicas: int) -> Dict[str, Any]:
        """
        Scale a specific service's instance count in the DigitalOcean app specification.
        """
        is_configured = self.token and self.token.strip() and self.token != "your_digitalocean_api_token_here"
        if not is_configured:
            logger.info(f"DigitalOcean API Token not configured. Simulating scaling for app '{app_id}' service '{service_name}' to {replicas} replicas.")
            return {
                "status": "success",
                "simulated": True,
                "message": f"Successfully scaled service {service_name} to {replicas} instances (simulated)."
            }

        get_url = f"{self.base_url}/apps/{app_id}"
        logger.info(f"Fetching current spec for DO app {app_id} to scale service {service_name}")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(get_url, headers=self._headers())
                if response.status_code != 200:
                    raise DigitalOceanAPIError(f"Failed to fetch app spec: {response.text}")
                
                app_data = response.json()
                spec = app_data.get("app", {}).get("spec", {})
                
                services = spec.get("services", [])
                found = False
                for svc in services:
                    if svc.get("name") == service_name:
                        svc["instance_count"] = replicas
                        found = True
                        break
                
                if not found:
                    raise DigitalOceanAPIError(f"Service '{service_name}' not found in app spec.")

                put_payload = {"spec": spec}
                put_response = await client.put(get_url, json=put_payload, headers=self._headers())
                if put_response.status_code not in (200, 202):
                    raise DigitalOceanAPIError(f"Failed to update app specification: {put_response.text}")
                
                return put_response.json()
        except Exception as e:
            logger.error(f"Failed to scale app via DigitalOcean: {e}")
            raise DigitalOceanAPIError(f"DigitalOcean communication failure: {str(e)}") from e

    async def create_app(self, spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates a new application on DigitalOcean App Platform using the provided spec.
        """
        is_configured = self.token and self.token.strip() and self.token != "your_digitalocean_api_token_here"
        if not is_configured:
            app_name = spec.get("name", "opsforge-app")
            logger.info(f"DigitalOcean API Token not configured. Simulating app creation for '{app_name}'.")
            return {
                "app": {
                    "id": f"do-app-simulated-{app_name}",
                    "live_url": f"https://{app_name}.ondigitalocean.app",
                    "active_deployment": {
                        "id": f"deploy-simulated-{app_name}-001",
                        "phase": "ACTIVE"
                    },
                    "spec": spec
                }
            }

        url = f"{self.base_url}/apps"
        payload = {"spec": spec}
        logger.info(f"Creating DigitalOcean App Platform application for '{spec.get('name')}'")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=self._headers())

            if response.status_code not in (200, 201, 202):
                error_msg = f"DigitalOcean API returned status {response.status_code}: {response.text}"
                logger.error(error_msg)
                raise DigitalOceanAPIError(error_msg)

            return response.json()
        except Exception as e:
            logger.error(f"Failed to create app via DigitalOcean: {e}")
            raise DigitalOceanAPIError(f"DigitalOcean communication failure: {str(e)}") from e

    async def get_deployment_status(self, app_id: str, deployment_id: str) -> Dict[str, Any]:
        """
        Fetches the current status/phase of a deployment for an application.
        """
        is_configured = self.token and self.token.strip() and self.token != "your_digitalocean_api_token_here"
        if not is_configured:
            logger.info(f"DigitalOcean API Token not configured. Simulating deployment status check for app '{app_id}' deployment '{deployment_id}'.")
            return {
                "deployment": {
                    "id": deployment_id,
                    "phase": "ACTIVE",
                    "progress": 100
                }
            }

        url = f"{self.base_url}/apps/{app_id}/deployments/{deployment_id}"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self._headers())

            if response.status_code != 200:
                error_msg = f"DigitalOcean API returned status {response.status_code}: {response.text}"
                logger.error(error_msg)
                raise DigitalOceanAPIError(error_msg)

            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch deployment status via DigitalOcean: {e}")
            raise DigitalOceanAPIError(f"DigitalOcean communication failure: {str(e)}") from e

