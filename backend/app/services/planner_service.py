import json
import os
from typing import Optional, Dict, Any
from fastapi import HTTPException

from app.schemas.deployment import PlannerRequest, DeploymentPlan
from app.utils.docker_parser import parse_dockerfile, DockerfileAnalysis
from app.integrations.gemini_client import GeminiClient, GeminiAPIError
from app.utils.logger import get_logger

logger = get_logger()

PROMPT_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts", "deployment.txt")

class PlannerService:
    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.gemini_client = gemini_client or GeminiClient()
        self._system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        if os.path.exists(PROMPT_FILE_PATH):
            with open(PROMPT_FILE_PATH, "r", encoding="utf-8") as f:
                return f.read()
        return "You are OpsForge Agent 1. Output strict JSON DeploymentPlan matching schema."

    def build_prompt(self, request: PlannerRequest, analysis: DockerfileAnalysis, retry_error: Optional[str] = None) -> str:
        prompt_parts = [
            "=== USER DEPLOYMENT REQUEST ===",
            f"Description: {request.description.strip()}",
            "",
            "=== PARSED DOCKERFILE ANALYSIS (DETERMINISTIC) ===",
            f"Runtime: {analysis.runtime or 'Unknown'}",
            f"Base Image: {analysis.base_image or 'Unknown'}",
            f"Language: {analysis.language or 'Unknown'}",
            f"Framework: {analysis.framework or 'Unknown'}",
            f"Working Directory: {analysis.working_dir or 'Unknown'}",
            f"Exposed Ports: {analysis.exposed_ports}",
            f"Entry Command: {analysis.entry_command}",
            f"Entrypoint: {analysis.entrypoint}",
            f"Package Manager: {analysis.package_manager or 'Unknown'}",
            f"Healthcheck: {analysis.healthcheck or 'None'}",
            f"Declared Env Vars: {json.dumps(analysis.env_vars)}",
            "",
            "=== RAW DOCKERFILE CONTENT ===",
            request.dockerfile.strip(),
            "",
            "INSTRUCTIONS:",
            "Synthesize the user description and parsed Dockerfile into a single validated JSON DeploymentPlan object.",
            "Do NOT invent application source code details.",
        ]

        if retry_error:
            prompt_parts.extend([
                "",
                "=== PREVIOUS ATTEMPT FAILED SCHEMA VALIDATION ===",
                f"Error details: {retry_error}",
                "Please correct your JSON output to conform strictly to the Pydantic schema types."
            ])

        return "\n".join(prompt_parts)

    def _clean_json_response(self, text: str) -> str:
        """Strips markdown code fences if present despite system instructions."""
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        elif cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        return cleaned.strip()

    async def generate_plan(self, request: PlannerRequest) -> DeploymentPlan:
        # Step 1: Input Validation
        if not request.dockerfile or not request.dockerfile.strip():
            logger.error("Request rejected: Dockerfile content is empty.")
            raise HTTPException(status_code=400, detail="Dockerfile content cannot be empty.")
        
        if not request.description or not request.description.strip():
            logger.error("Request rejected: Deployment description is empty.")
            raise HTTPException(status_code=400, detail="Deployment description cannot be empty.")

        logger.info("Ingressed valid PlannerRequest.")

        # Step 2: Deterministic Dockerfile Parsing
        docker_analysis = parse_dockerfile(request.dockerfile)

        # Step 3: First Generation Attempt
        prompt = self.build_prompt(request, docker_analysis)

        try:
            raw_response = await self.gemini_client.generate_json(
                prompt=prompt,
                system_instruction=self._system_prompt
            )
        except GeminiAPIError as e:
            logger.error(f"Gemini generation error: {e}")
            raise HTTPException(status_code=502, detail=f"Gemini API failure: {str(e)}")

        cleaned_json = self._clean_json_response(raw_response)

        # Step 4: Pydantic Validation (Attempt 1)
        try:
            parsed_dict = json.loads(cleaned_json)
            plan = DeploymentPlan.model_validate(parsed_dict)
            logger.info("Successfully validated DeploymentPlan on first attempt.")
            return plan
        except (json.JSONDecodeError, Exception) as first_err:
            error_msg = f"Validation failed on first attempt: {str(first_err)}"
            logger.warning(error_msg)

        # Step 5: Retry Attempt (Single Retry with Feedback)
        logger.info("Initiating single retry attempt with validation feedback.")
        retry_prompt = self.build_prompt(request, docker_analysis, retry_error=str(first_err))

        try:
            retry_response = await self.gemini_client.generate_json(
                prompt=retry_prompt,
                system_instruction=self._system_prompt
            )
            retry_cleaned = self._clean_json_response(retry_response)
            parsed_dict = json.loads(retry_cleaned)
            plan = DeploymentPlan.model_validate(parsed_dict)
            logger.info("Successfully validated DeploymentPlan on retry attempt.")
            return plan
        except (json.JSONDecodeError, Exception) as retry_err:
            final_err_msg = f"DeploymentPlan validation failed after retry: {str(retry_err)}"
            logger.error(final_err_msg)
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "Failed to parse or validate LLM deployment plan response.",
                    "details": str(retry_err)
                }
            )
