import asyncio
import httpx
from typing import Optional, Dict, Any
from app.utils.config import settings
from app.utils.logger import get_logger

logger = get_logger()

class GitHubActionsError(Exception):
    """Raised when GitHub Actions API returns an error or fails to respond."""
    pass

class GitHubActionsClient:
    def __init__(self, token: Optional[str] = None):
        from app.services.deployment_service import _get_active_github_token
        self.token = token or settings.GITHUB_TOKEN or _get_active_github_token()
        self.base_url = "https://api.github.com"
        self.workflow_filename = settings.GITHUB_ACTIONS_WORKFLOW

    def _headers(self) -> Dict[str, str]:
        if not self.token or not self.token.strip():
            raise GitHubActionsError("GitHub authorization token is required to dispatch deployment workflows. Please log in with GitHub or set GITHUB_TOKEN in .env.")
        return {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "OpsForge-App",
            "Authorization": f"Bearer {self.token.strip()}",
        }

    async def verify_workflow_file_exists(self, owner: str, repo: str, ref: str = "main") -> bool:
        """Verifies that the workflow file exists in the repository."""
        url = f"{self.base_url}/repos/{owner}/{repo}/contents/.github/workflows/{self.workflow_filename}?ref={ref}"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(url, headers=self._headers())

            if response.status_code == 404:
                raise GitHubActionsError(
                    f"Workflow file '.github/workflows/{self.workflow_filename}' not found in repository '{owner}/{repo}' on branch '{ref}'."
                )
            if response.status_code != 200:
                raise GitHubActionsError(
                    f"GitHub API error verifying workflow file (HTTP {response.status_code}): {response.text}"
                )
            return True
        except GitHubActionsError:
            raise
        except Exception as e:
            raise GitHubActionsError(f"Failed to check workflow file in GitHub: {str(e)}") from e

    async def trigger_workflow_dispatch(
        self,
        owner: str,
        repo: str,
        ref: str = "main",
        inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Triggers a workflow dispatch event on GitHub repository.
        POST /repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches
        """
        if not self.token or not self.token.strip():
            raise GitHubActionsError("GitHub authorization token is required for workflow dispatch.")

        # Step 1: Check workflow file existence
        await self.verify_workflow_file_exists(owner, repo, ref)

        # Step 2: Dispatch workflow
        url = f"{self.base_url}/repos/{owner}/{repo}/actions/workflows/{self.workflow_filename}/dispatches"
        payload = {
            "ref": ref,
            "inputs": inputs or {}
        }

        logger.info(f"Triggering GitHub Actions workflow '{self.workflow_filename}' for {owner}/{repo} on ref '{ref}'.")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=self._headers())

            if response.status_code not in (204, 201, 200):
                error_msg = f"GitHub Actions API returned HTTP status {response.status_code}: {response.text}"
                logger.error(error_msg)
                raise GitHubActionsError(error_msg)

            logger.info(f"Successfully dispatched GitHub Actions workflow '{self.workflow_filename}' for {owner}/{repo}@{ref}.")
            return {
                "status": "dispatched",
                "message": f"Successfully dispatched workflow '{self.workflow_filename}' for {owner}/{repo}@{ref}."
            }
        except Exception as e:
            if isinstance(e, GitHubActionsError):
                raise
            logger.error(f"Failed to trigger GitHub Actions workflow: {e}")
            raise GitHubActionsError(f"GitHub Actions dispatch failure: {str(e)}") from e

    async def get_latest_run_status(
        self,
        owner: str,
        repo: str,
        ref: str = "main"
    ) -> Dict[str, Any]:
        """Fetches the latest workflow run status for a repo."""
        if not self.token or not self.token.strip():
            raise GitHubActionsError("GitHub authorization token is required.")

        url = f"{self.base_url}/repos/{owner}/{repo}/actions/runs?branch={ref}&per_page=1"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self._headers())

            if response.status_code != 200:
                raise GitHubActionsError(f"GitHub API error fetching runs (HTTP {response.status_code}): {response.text}")

            data = response.json()
            runs = data.get("workflow_runs", [])
            if not runs:
                return {"status": "queued", "conclusion": None}

            latest = runs[0]
            return {
                "status": latest.get("status", "completed"),
                "conclusion": latest.get("conclusion"),
                "run_id": str(latest.get("id", "")),
                "html_url": latest.get("html_url", ""),
            }
        except Exception as e:
            if isinstance(e, GitHubActionsError):
                raise
            logger.error(f"Error fetching GitHub workflow status: {e}")
            raise GitHubActionsError(f"GitHub workflow status failure: {str(e)}") from e

    async def wait_for_workflow_completion(
        self,
        owner: str,
        repo: str,
        ref: str = "main",
        timeout_seconds: int = 180,
        poll_interval: int = 5
    ) -> Dict[str, Any]:
        """
        Polls GitHub Actions workflow runs until the run finishes.
        Raises GitHubActionsError if the run fails or times out.
        """
        start_time = asyncio.get_event_loop().time()
        logger.info(f"Waiting for GitHub Actions workflow run completion for {owner}/{repo}@{ref}...")

        # Initial wait for GitHub Actions queue
        await asyncio.sleep(3)

        while (asyncio.get_event_loop().time() - start_time) < timeout_seconds:
            run_info = await self.get_latest_run_status(owner, repo, ref)
            status_val = run_info.get("status")
            conclusion = run_info.get("conclusion")

            logger.info(f"GitHub Actions run '{run_info.get('run_id')}' status: '{status_val}' | conclusion: '{conclusion}'")

            if status_val == "completed":
                if conclusion == "success":
                    logger.info(f"GitHub Actions workflow completed successfully: {run_info.get('html_url')}")
                    return run_info
                else:
                    error_msg = f"GitHub Actions deployment workflow failed with conclusion '{conclusion}'. View logs: {run_info.get('html_url')}"
                    logger.error(error_msg)
                    raise GitHubActionsError(error_msg)

            await asyncio.sleep(poll_interval)

        raise GitHubActionsError(f"GitHub Actions deployment timed out after {timeout_seconds}s waiting for completion.")
