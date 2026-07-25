from typing import Union
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.deployment import PlannerRequest, DeploymentPlan, DeploymentResult
from app.agents.deployment_planner import deployment_planner_agent, DeploymentPlannerAgent
from app.agents.infra_deploy import infra_deploy_agent, InfraDeployAgent
from app.utils.logger import get_logger

logger = get_logger()

router = APIRouter(tags=["Deployment Pipeline (Agent 1 & Agent 2)"])

def get_planner_agent() -> DeploymentPlannerAgent:
    return deployment_planner_agent

def get_infra_agent() -> InfraDeployAgent:
    return infra_deploy_agent

@router.post(
    "/plan",
    response_model=DeploymentPlan,
    status_code=status.HTTP_200_OK,
    summary="Generate a validated DeploymentPlan from Dockerfile and intent (Agent 1)"
)
@router.post(
    "/deploy/plan",
    response_model=DeploymentPlan,
    status_code=status.HTTP_200_OK,
    include_in_schema=False
)
async def generate_deployment_plan(
    request: PlannerRequest,
    agent: DeploymentPlannerAgent = Depends(get_planner_agent)
) -> DeploymentPlan:
    """
    Agent 1 Ingress Route.
    Receives description + raw Dockerfile, parses Dockerfile deterministically,
    queries Gemini for deployment topology reasoning, validates output via Pydantic,
    and returns a clean machine-readable DeploymentPlan JSON ready for Agent 2 consumption.
    """
    logger.info("Received POST /plan request.")
    return await agent.create_plan(request)

@router.post(
    "/deploy",
    response_model=DeploymentResult,
    status_code=status.HTTP_200_OK,
    summary="Execute deployment workflow (Agent 1 -> Agent 2 pipeline or direct Agent 2 plan deployment)"
)
async def execute_deployment_workflow(
    payload: Union[PlannerRequest, DeploymentPlan],
    planner: DeploymentPlannerAgent = Depends(get_planner_agent),
    infra: InfraDeployAgent = Depends(get_infra_agent)
) -> DeploymentResult:
    """
    Agent 1 & Agent 2 Integrated Deployment Route.
    - If a PlannerRequest (description + Dockerfile) is provided: Agent 1 generates the DeploymentPlan JSON
      and passes it directly to Agent 2 for validation and infrastructure execution.
    - If a DeploymentPlan is provided directly: Agent 2 validates the plan and executes infrastructure deployment.
    Returns deployment status back to the caller.
    """
    logger.info("Received POST /deploy request.")
    if isinstance(payload, PlannerRequest):
        logger.info("Triggering integrated Agent 1 -> Agent 2 deployment pipeline.")
        return await planner.create_and_deploy(payload)
    else:
        logger.info("Triggering direct Agent 2 deployment using provided DeploymentPlan.")
        return await infra.deploy(payload)

