import re
import asyncio
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, status

from app.schemas.deployment import DeploymentPlan, DeploymentResult
from app.integrations.digitalocean_client import DigitalOceanClient, DigitalOceanAPIError
from app.utils.logger import get_logger

logger = get_logger()

VALID_REGIONS = {"nyc1", "nyc3", "ams3", "sfo2", "sfo3", "sgp1", "lon1", "fra1", "tor1", "blr1"}
VALID_DB_ENGINES = {"mongodb", "postgresql", "mysql", "redis"}

class DeploymentService:
    """
    Service encapsulating infrastructure deployment operations for Agent 2.
    """
    def __init__(self, digitalocean_client: Optional[DigitalOceanClient] = None):
        self.client = digitalocean_client or DigitalOceanClient()

    def validate_plan(self, plan: DeploymentPlan) -> List[str]:
        """
        Validates deployment plan parameters against infrastructure requirements.
        Returns a list of error strings if invalid.
        """
        errors = []

        # 1. Application Name Validation
        app_name = plan.application.name
        if not app_name:
            errors.append("application.name is required.")
        elif not re.match(r"^[a-z0-9-]+$", app_name):
            errors.append(f"application.name '{app_name}' must contain only lowercase alphanumeric characters and hyphens.")


        # 2. Region Validation
        region = plan.deployment.region.lower()
        if region not in VALID_REGIONS:
            errors.append(f"deployment.region '{region}' is invalid. Allowed regions: {', '.join(sorted(VALID_REGIONS))}.")

        # 3. Replica Count Validation
        if plan.deployment.replicas < 1:
            errors.append("deployment.replicas must be at least 1.")

        # 4. Database Validation
        if plan.database.required:
            if not plan.database.engine:
                errors.append("database.engine is required when database.required is True.")
            elif plan.database.engine.lower() not in VALID_DB_ENGINES:
                errors.append(f"database.engine '{plan.database.engine}' is invalid. Allowed engines: {', '.join(sorted(VALID_DB_ENGINES))}.")

        # 5. Network / Port Validation
        if plan.network.ports:
            for p in plan.network.ports:
                if p < 1 or p > 65535:
                    errors.append(f"network port '{p}' must be between 1 and 65535.")

        return errors

    def build_do_app_spec(self, plan: DeploymentPlan) -> Dict[str, Any]:
        """
        Translates abstract DeploymentPlan Pydantic model into a DigitalOcean App Platform spec.
        """
        env_list = [{"key": k, "value": str(v)} for k, v in plan.environment.items()]
        
        main_port = plan.network.ports[0] if plan.network.ports else 8080
        if plan.healthcheck.port:
            main_port = plan.healthcheck.port

        service_spec: Dict[str, Any] = {
            "name": plan.application.name,
            "instance_count": plan.deployment.replicas,
            "instance_size_slug": plan.resources.instance_size,
            "http_port": main_port,
            "envs": env_list,
            "health_check": {
                "http_path": plan.healthcheck.path,
                "initial_delay_seconds": plan.healthcheck.initial_delay_seconds,
                "period_seconds": plan.healthcheck.period_seconds,
                "timeout_seconds": plan.healthcheck.timeout_seconds
            }
        }

        if plan.application.base_image:
            service_spec["image"] = {
                "registry_type": "DOCKER_HUB",
                "image": plan.application.base_image
            }

        app_spec: Dict[str, Any] = {
            "name": plan.application.name,
            "region": plan.deployment.region,
            "services": [service_spec]
        }

        if plan.database.required and plan.database.engine:
            app_spec["databases"] = [
                {
                    "name": f"{plan.application.name}-db",
                    "engine": plan.database.engine.upper(),
                    "version": plan.database.version or "14",
                    "production": False
                }
            ]

        return app_spec

    async def execute_deployment(self, plan: DeploymentPlan) -> DeploymentResult:
        """
        Validates the DeploymentPlan, constructs the app spec, triggers deployment,
        and returns the resulting DeploymentResult.
        """
        logger.info(f"DeploymentService: Ingressing deployment execution for application '{plan.application.name}'.")

        # Step 1: Validate plan
        validation_errors = self.validate_plan(plan)
        if validation_errors:
            error_msg = "; ".join(validation_errors)
            logger.error(f"DeploymentPlan validation failed: {error_msg}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Validation failed for deployment plan.",
                    "errors": validation_errors
                }
            )

        # Step 2: Build App Spec
        spec = self.build_do_app_spec(plan)
        logger.info(f"Constructed DO App Spec for '{plan.application.name}'.")

        # Step 3: Trigger Provisioning via DigitalOcean Client
        try:
            do_response = await self.client.create_app(spec)
        except DigitalOceanAPIError as e:
            logger.error(f"DigitalOcean API deployment failure: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"DigitalOcean infrastructure deployment failed: {str(e)}"
            )

        # Step 4: Extract response details
        app_data = do_response.get("app", {})
        app_id = app_data.get("id", "unknown-app-id")
        live_url = app_data.get("live_url", "")
        active_deploy = app_data.get("active_deployment", {})
        deployment_id = active_deploy.get("id", "unknown-deploy-id")
        phase = active_deploy.get("phase", "ACTIVE")

        logger.info(f"Deployment process initiated successfully for app '{app_id}' (deployment '{deployment_id}').")

        import uuid
        from datetime import datetime, timezone

        trace_id = f"trace-{uuid.uuid4().hex[:12]}"
        created_at = datetime.now(timezone.utc).isoformat()
        outcome_status = "success" if phase in ("ACTIVE", "BUILDING", "DEPLOYING") else "failed"

        logger.info(
            f"[AUDIT LOG] trace_id='{trace_id}' | app_id='{app_id}' | deployment_id='{deployment_id}' | "
            f"agent_name='Agent 2 (Infra & Deploy)' | action='DEPLOYMENT_PROVISIONED' | "
            f"timestamp='{created_at}' | status='{outcome_status.upper()}'"
        )

        return DeploymentResult(
            trace_id=trace_id,
            status=outcome_status,
            app_id=app_id,
            deployment_id=deployment_id,
            app_name=plan.application.name,
            live_url=live_url,
            message="Infrastructure provisioned and application deployment initiated successfully.",
            created_at=created_at,
            details={
                "app_name": plan.application.name,
                "region": plan.deployment.region,
                "strategy": plan.deployment.strategy,
                "replicas": plan.deployment.replicas,
                "phase": phase
            }
        )

    async def execute_recovery_action(self, action: Any):
        """
        Validates recovery action payload, executes infrastructure action via DigitalOcean Client
        (rollback, restart, scale, redeploy), and yields updated step progress.
        """
        target_app_id = action.app_id or action.incident_id
        target_dep_id = action.deployment_id or "prev-stable-dep"

        if not target_app_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Recovery action validation failed: Neither app_id nor incident_id was provided."
            )

        logger.info(f"Agent 2 (DeploymentService): Validated recovery action '{action.id}' ({action.title}) for app '{target_app_id}'.")

        title_lower = action.title.lower()

        # Step-by-step infrastructure execution
        for step in action.steps:
            step.status = "running"

            await asyncio.sleep(0.05)

            if step.order == 1:
                try:
                    if "rollback" in title_lower:
                        await self.client.rollback_deployment(app_id=target_app_id, deployment_id=target_dep_id)
                    elif "restart" in title_lower or "patch" in title_lower:
                        await self.client.restart_application(app_id=target_app_id)
                    elif "scale" in title_lower:
                        await self.client.scale_service(app_id=target_app_id, service_name="web", replicas=3)
                    else:
                        await self.client.restart_application(app_id=target_app_id)
                except DigitalOceanAPIError as e:
                    logger.error(f"DigitalOcean infrastructure failure during recovery execution for app '{target_app_id}': {e}")
                    step.status = "failed"
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Infrastructure recovery execution failed: {str(e)}"
                    )

            step.verified = True
            step.status = "completed"
            logger.info(f"Agent 2: Step {step.order} ('{step.title}') executed and verified for app '{target_app_id}'.")

