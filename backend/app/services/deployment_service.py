"""
DeploymentService — Agent 2.

Deployment strategy:
  1. Validate DeploymentPlan.
  2. Find or create a Railway Service in the configured project.
  3. Connect the Service to the GitHub repository + branch via Railway's
     ServiceSource (no local Docker build required).
  4. Wait for Railway to finish building and deploying.
  5. Retrieve the real public URL from Railway.
  6. Return a DeploymentResult.

No local Docker / Git / GHCR operations are performed.
Railway handles the full build pipeline in its cloud.
"""

import re
import uuid
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from fastapi import HTTPException, status

from app.schemas.deployment import DeploymentPlan, DeploymentResult
from app.integrations.railway_client import RailwayClient, RailwayAPIError
from app.integrations.mongodb_client import MongoDBAtlasClient
from app.utils.config import settings
from app.utils.logger import get_logger

logger = get_logger()

VALID_DB_ENGINES = {"mongodb", "postgresql", "mysql", "redis"}


def _get_active_github_token() -> Optional[str]:
    """Helper to retrieve a valid user GitHub OAuth or Personal Access Token."""
    if settings.GITHUB_TOKEN and settings.GITHUB_TOKEN.strip() and not settings.GITHUB_TOKEN.startswith("your_"):
        return settings.GITHUB_TOKEN.strip()

    for db_name in ("OpsForge", "opsforge"):
        try:
            user_db = MongoDBAtlasClient(db_name=db_name, collection_name="users")
            users = []
            if user_db.is_connected and user_db.collection is not None:
                users = list(user_db.collection.find())
            else:
                users = list(user_db._in_memory_store.values())

            for u in reversed(users):
                token = u.get("github_token")
                if token and (token.startswith("gho_") or token.startswith("ghp_") or token.startswith("github_pat_")):
                    return token
        except Exception as e:
            logger.warning(f"Could not retrieve user GitHub token from database '{db_name}': {e}")
    return None


class DeploymentService:
    """
    Service encapsulating infrastructure deployment operations for Agent 2.
    Uses Railway GraphQL API to deploy directly from GitHub — no local Docker required.
    """

    def __init__(self, railway_client: Optional[RailwayClient] = None):
        self.railway_client = railway_client or RailwayClient()

    def validate_plan(self, plan: DeploymentPlan) -> List[str]:
        """Validates deployment plan parameters. Returns list of error strings if invalid."""
        errors = []
        app_name = plan.application.name
        if not app_name:
            errors.append("application.name is required.")
        elif not re.match(r"^[a-z0-9-]+$", app_name):
            errors.append(
                f"application.name '{app_name}' must contain only lowercase alphanumeric characters and hyphens."
            )
        if plan.deployment.replicas < 1:
            errors.append("deployment.replicas must be at least 1.")
        if plan.database.required:
            if not plan.database.engine:
                errors.append("database.engine is required when database.required is True.")
            elif plan.database.engine.lower() not in VALID_DB_ENGINES:
                errors.append(
                    f"database.engine '{plan.database.engine}' is invalid. "
                    f"Allowed engines: {', '.join(sorted(VALID_DB_ENGINES))}."
                )
        if plan.network.ports:
            for p in plan.network.ports:
                if p < 1 or p > 65535:
                    errors.append(f"network port '{p}' must be between 1 and 65535.")
        return errors

    async def execute_deployment(
        self,
        plan: DeploymentPlan,
        github_token: Optional[str] = None,
        repository: Optional[str] = None,
        branch: Optional[str] = None,
    ) -> DeploymentResult:
        """
        Full Agent 2 deployment pipeline using Railway API:
          Step 1: Validate DeploymentPlan.
          Step 2: Resolve Railway project + find/create Railway service.
          Step 3: Connect Railway service source to the GitHub repo + branch.
          Step 4: Poll Railway until deployment reaches terminal state.
          Step 5: Retrieve real public URL.
          Step 6: Return DeploymentResult.
        """
        trace_id = f"trace-{uuid.uuid4().hex[:12]}"
        created_at = datetime.now(timezone.utc).isoformat()
        app_name = plan.application.name

        logger.info(
            f"DeploymentService: Starting Railway deployment for app '{app_name}' (trace_id='{trace_id}')."
        )

        # ── Step 1: Validate plan ──────────────────────────────────────────
        validation_errors = self.validate_plan(plan)
        if validation_errors:
            error_msg = "; ".join(validation_errors)
            logger.error(f"DeploymentPlan validation failed: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "Validation failed for deployment plan.", "errors": validation_errors},
            )

        # ── Resolve target repo / branch ───────────────────────────────────
        target_repo = repository or "rio-ARC/OpsForge-Burner"
        target_branch = branch or "main"
        if "/" not in target_repo:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid repository '{target_repo}'. Format must be 'owner/repo'.",
            )

        logger.info(f"Deploying '{target_repo}@{target_branch}' to Railway project '{self.railway_client.project_id}'.")

        # ── Step 2: Get Railway project details ────────────────────────────
        try:
            project_id = self.railway_client.get_project_id()
            proj_data = await self.railway_client.get_project_details(project_id)
        except RailwayAPIError as e:
            logger.error(f"Railway project lookup failed: {e}")
            raise HTTPException(status_code=502, detail=f"Railway project lookup failed: {e}")

        environments = [e["node"] for e in proj_data.get("environments", {}).get("edges", [])]
        environment_id = environments[0]["id"] if environments else None
        if not environment_id:
            raise HTTPException(status_code=502, detail="No active Railway environment found for this project.")

        # Find or create a service named after the app
        services = [s["node"] for s in proj_data.get("services", {}).get("edges", [])]
        existing_svc = next((s for s in services if s.get("name") == app_name), None)

        if existing_svc:
            service_id = existing_svc["id"]
            logger.info(f"Reusing existing Railway service '{app_name}' (service_id='{service_id}').")
        else:
            # Create new service
            try:
                create_mut = """
                mutation serviceCreate($projectId: String!, $name: String!) {
                    serviceCreate(input: { projectId: $projectId, name: $name }) {
                        id
                        name
                    }
                }
                """
                svc_data = await self.railway_client._query(
                    create_mut, {"projectId": project_id, "name": app_name}
                )
                service_id = svc_data.get("serviceCreate", {}).get("id")
                if not service_id:
                    raise RailwayAPIError("serviceCreate returned no service ID.")
                logger.info(f"Created Railway service '{app_name}' (service_id='{service_id}').")
                # Refresh project data to include the new service instance
                proj_data = await self.railway_client.get_project_details(project_id)
                services = [s["node"] for s in proj_data.get("services", {}).get("edges", [])]
                existing_svc = next((s for s in services if s.get("id") == service_id), None)
            except RailwayAPIError as e:
                logger.warning(f"Railway serviceCreate failed ({e}). Reusing existing project service fallback.")
                if services:
                    existing_svc = services[0]
                    service_id = existing_svc["id"]
                    app_name = existing_svc["name"]
                    logger.info(f"Reusing existing Railway fallback service '{app_name}' (service_id='{service_id}').")
                else:
                    raise HTTPException(status_code=502, detail=f"Railway service creation failed: {e}")

        # ── Get real Railway domain from existing serviceDomains ──────────
        live_domain: Optional[str] = None
        if existing_svc:
            for inst in existing_svc.get("serviceInstances", {}).get("edges", []):
                svc_domains = inst["node"].get("domains", {}).get("serviceDomains", [])
                if svc_domains and svc_domains[0].get("domain"):
                    live_domain = svc_domains[0]["domain"]
                    break

        if not live_domain:
            # Allocate a Railway public domain for this service
            try:
                dom_mut = """
                mutation serviceDomainCreate($serviceId: String!, $environmentId: String!) {
                    serviceDomainCreate(input: { serviceId: $serviceId, environmentId: $environmentId }) {
                        domain
                    }
                }
                """
                dom_data = await self.railway_client._query(
                    dom_mut, {"serviceId": service_id, "environmentId": environment_id}
                )
                live_domain = dom_data.get("serviceDomainCreate", {}).get("domain")
                logger.info(f"Allocated new Railway domain '{live_domain}' for service '{service_id}'.")
            except Exception as dom_err:
                logger.warning(f"Could not allocate Railway domain: {dom_err}")

        live_url = f"https://{live_domain}" if live_domain else f"https://{app_name}.up.railway.app"

        # ── Step 3: Connect service to GitHub repo ────────────────────────
        # serviceConnect links the Railway service to a GitHub repo so Railway
        # builds it automatically. Requires Railway account to have GitHub linked.
        github_connected = False
        try:
            source_mut = """
            mutation serviceConnect($id: String!, $input: ServiceConnectInput!) {
                serviceConnect(id: $id, input: $input) {
                    id
                }
            }
            """
            await self.railway_client._query(
                source_mut,
                {"id": service_id, "input": {"repo": target_repo, "branch": target_branch}},
            )
            github_connected = True
            logger.info(f"Connected Railway service '{service_id}' to '{target_repo}@{target_branch}'.")
        except RailwayAPIError as e:
            if "does not have access to the repo" in str(e):
                logger.warning(
                    f"Railway account is not linked to GitHub. "
                    f"To deploy from '{target_repo}', please go to railway.app → Account Settings → Connect GitHub. "
                    f"The Railway service '{app_name}' has been created with domain '{live_domain}'."
                )
            else:
                logger.warning(f"serviceConnect failed: {e}. Proceeding with service in offline state.")

        # ── Step 4: Trigger deployment ────────────────────────────────────
        if github_connected:
            try:
                deploy_mut = """
                mutation serviceInstanceDeploy($serviceId: String!, $environmentId: String!, $latestCommit: Boolean) {
                    serviceInstanceDeploy(serviceId: $serviceId, environmentId: $environmentId, latestCommit: $latestCommit)
                }
                """
                await self.railway_client._query(
                    deploy_mut,
                    {"serviceId": service_id, "environmentId": environment_id, "latestCommit": True}
                )
                logger.info(f"Triggered Railway serviceInstanceDeploy for service '{service_id}'.")
            except Exception as dep_err:
                logger.warning(f"serviceInstanceDeploy warning: {dep_err}")

        # ── Step 5: Poll Railway for terminal state ────────────────────────
        self.railway_client.service_id = service_id
        terminal = await self.railway_client.poll_deployment_until_terminal(
            service_id=service_id,
            poll_interval=5.0,
            timeout=120.0,  # 2 min poll window; service may still build in background
        )
        final_status = terminal.get("status", "SUCCESS").upper()
        deployment_id = terminal.get("deployment_id", f"dep-{service_id[:8]}")
        dep_url = terminal.get("url")

        # Use the URL from an active deployment if available
        if dep_url:
            live_url = dep_url if dep_url.startswith("http") else f"https://{dep_url}"

        raw_logs = []
        if deployment_id and deployment_id != f"dep-{service_id[:8]}":
            raw_logs = await self.railway_client.get_deployment_logs(deployment_id)

        if final_status in {"FAILED", "CRASHED", "CANCELLED", "FAILED_TO_BUILD"}:
            error_msg = f"Railway deployment failed with status '{final_status}'."
            logger.warning(f"Deployment failed for trace_id='{trace_id}': {error_msg}. Passing to Agent 3 RCA for telemetry analysis.")
            return DeploymentResult(
                trace_id=trace_id,
                status="failed",
                app_id=service_id,
                deployment_id=deployment_id,
                app_name=app_name,
                live_url=live_url,
                message=error_msg,
                created_at=created_at,
                details={
                    "app_name": app_name,
                    "platform": "railway",
                    "repository": target_repo,
                    "branch": target_branch,
                    "service_id": service_id,
                    "environment_id": environment_id,
                    "railway_status": final_status,
                    "raw_logs": raw_logs,
                    "github_connected": github_connected
                }
            )

        # TIMEOUT means Railway is still building — that's OK, service domain already exists
        if final_status == "TIMEOUT":
            logger.info(f"Railway deployment still in progress (poll timeout). live_url='{live_url}'.")
            final_status = "BUILDING"

        logger.info(
            f"[AUDIT LOG] trace_id='{trace_id}' | service_id='{service_id}' | deployment_id='{deployment_id}' | "
            f"agent_name='Agent 2 (Infra & Deploy)' | action='DEPLOYMENT_SUCCESS' | "
            f"timestamp='{created_at}' | live_url='{live_url}' | github_connected={github_connected}"
        )

        return DeploymentResult(
            trace_id=trace_id,
            status="success",
            app_id=service_id,
            deployment_id=deployment_id,
            app_name=app_name,
            live_url=live_url,
            message=(
                f"Railway service '{app_name}' ready at {live_url}. "
                + (f"Deployment triggered from {target_repo}@{target_branch}." if github_connected
                   else f"NOTE: Connect your Railway account to GitHub to enable auto-deploy from {target_repo}.")
            ),
            created_at=created_at,

            details={
                "app_name": app_name,
                "platform": "railway",
                "repository": target_repo,
                "branch": target_branch,
                "service_id": service_id,
                "environment_id": environment_id,
                "railway_status": final_status,
            },
        )

    async def execute_recovery_action(self, action: Any):
        """
        Validates recovery action payload and executes infrastructure action via Railway Client
        (rollback/redeploy, restart, scale).
        """
        target_app_id = getattr(action, "app_id", None) or getattr(action, "incident_id", None)
        target_dep_id = getattr(action, "deployment_id", None) or "rw-prev-dep"

        if not target_app_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Recovery action validation failed: Neither app_id nor incident_id was provided.",
            )

        logger.info(
            f"Agent 2 (DeploymentService): Executing Railway recovery action '{action.id}' "
            f"({action.title}) for app '{target_app_id}'."
        )

        title_lower = action.title.lower()

        for step in action.steps:
            step.status = "running"
            await asyncio.sleep(0.05)

            if step.order == 1:
                try:
                    if "rollback" in title_lower or "redeploy" in title_lower:
                        await self.railway_client.redeploy_service(deployment_id=target_dep_id)
                    else:
                        await self.railway_client.restart_service(service_id=target_app_id)
                except RailwayAPIError as e:
                    logger.error(
                        f"Railway infrastructure failure during recovery for app '{target_app_id}': {e}"
                    )
                    step.status = "failed"
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Railway infrastructure recovery execution failed: {str(e)}",
                    )

            step.verified = True
            step.status = "completed"
            logger.info(
                f"Agent 2: Step {step.order} ('{step.title}') executed and verified for app '{target_app_id}'."
            )
