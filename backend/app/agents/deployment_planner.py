from typing import Optional
from app.schemas.deployment import PlannerRequest, DeploymentPlan, DeploymentResult
from app.services.planner_service import PlannerService
from app.agents.infra_deploy import infra_deploy_agent, InfraDeployAgent
from app.utils.logger import get_logger

logger = get_logger()

class DeploymentPlannerAgent:
    """
    Agent 1 (Deployment Planner Agent).
    Converts Dockerfile + User deployment intent into a validated DeploymentPlan JSON.
    Integrates directly with Agent 2 (Infra & Deploy Agent) to trigger deployment workflows.
    """
    def __init__(
        self,
        planner_service: Optional[PlannerService] = None,
        infra_agent: Optional[InfraDeployAgent] = None
    ):
        self.planner_service = planner_service or PlannerService()
        self.infra_agent = infra_agent or infra_deploy_agent

    async def create_plan(self, request: PlannerRequest) -> DeploymentPlan:
        """
        Executes Agent 1 pipeline to produce a validated DeploymentPlan.
        """
        return await self.planner_service.generate_plan(request)

    async def create_and_deploy(self, request: PlannerRequest) -> DeploymentResult:
        """
        Full Agent 1 -> Agent 2 integration workflow:
        1. Agent 1 generates the validated DeploymentPlan JSON.
        2. Passes the plan directly to Agent 2 (Infra & Deploy).
        3. Agent 2 validates the plan and executes the deployment workflow.
        4. Returns deployment status back to caller.
        """
        logger.info("Agent 1: Generating deployment plan for integration pipeline...")
        plan = await self.create_plan(request)
        logger.info(f"Agent 1: Successfully generated plan for '{plan.application.name}'. Passing plan directly to Agent 2...")
        result = await self.infra_agent.deploy(plan)
        logger.info(f"Agent 1 -> Agent 2 pipeline completed successfully for '{plan.application.name}'.")
        return result

# Singleton instance for route handler reuse
deployment_planner_agent = DeploymentPlannerAgent()

