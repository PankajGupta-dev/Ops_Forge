"""
Auth Routes — FastAPI endpoints for GitHub OAuth, profile verification, and repository listing.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Header, status
from fastapi.responses import RedirectResponse

from app.schemas.auth import GitHubLoginResponse, AuthTokenResponse, UserProfile, RepositoryItem, BranchItem
from app.services.auth_service import AuthService
from app.utils.config import settings
from app.utils.logger import get_logger

logger = get_logger()

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_current_user(authorization: Optional[str] = Header(None)) -> UserProfile:
    """Dependency helper to extract and validate the JWT Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header. Header format: 'Bearer <token>'"
        )

    token = authorization.split(" ")[1]
    try:
        payload = AuthService.verify_jwt_token(token)
        github_id = payload["github_id"]
        user_doc = AuthService.get_user_by_github_id(github_id)
        if not user_doc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account not found."
            )

        return UserProfile(
            github_id=user_doc["github_id"],
            username=user_doc["username"],
            name=user_doc.get("name"),
            email=user_doc.get("email"),
            avatar_url=user_doc.get("avatar_url"),
            html_url=user_doc.get("html_url"),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.get("/github/login", response_model=GitHubLoginResponse, summary="Initiate GitHub OAuth Login")
async def github_login(redirect: bool = Query(default=False, description="Set to True to issue an HTTP 307 redirect directly to GitHub")):
    """
    Generates the GitHub OAuth authorization URL.
    Returns JSON with login_url or redirects directly if redirect=true.
    """
    login_url = AuthService.get_github_auth_url()
    if redirect:
        return RedirectResponse(url=login_url)
    return GitHubLoginResponse(login_url=login_url)


@router.get("/github/callback", summary="GitHub OAuth Callback")
async def github_callback(code: str = Query(..., description="Authorization code from GitHub")):
    """
    Callback endpoint registered with GitHub OAuth app.
    Exchanges code for GitHub access token, fetches profile, saves user in MongoDB,
    generates JWT token, and redirects to frontend app with token parameter.
    """
    try:
        # 1. Exchange code for access token
        github_token = await AuthService.exchange_code_for_token(code)

        # 2. Fetch user profile from GitHub
        profile_data = await AuthService.fetch_github_profile(github_token)

        # 3. Save / update user in MongoDB Atlas
        user_profile = AuthService.save_or_update_user(profile_data, github_token)

        # 4. Generate JWT
        jwt_token = AuthService.create_jwt_token(user_profile.github_id, user_profile.username)

        # 5. Redirect to frontend with token parameter
        frontend_url = f"{settings.FRONTEND_URL}/dashboard?token={jwt_token}"
        return RedirectResponse(url=frontend_url)

    except ValueError as err:
        logger.error(f"OAuth Callback processing error: {err}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))
    except Exception as err:
        logger.error(f"Unexpected error during OAuth callback: {err}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Authentication failed.")


@router.get("/me", response_model=UserProfile, summary="Get Current User Profile")
async def get_me(user: UserProfile = Depends(get_current_user)):
    """
    Validates JWT token from Bearer header and returns the current user profile.
    """
    return user


@router.get("/repos", response_model=List[RepositoryItem], summary="Get User GitHub Repositories")
async def get_user_repos(authorization: Optional[str] = Header(None)):
    """
    Validates JWT token and fetches the user's GitHub repositories using their stored GitHub token.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header."
        )

    token = authorization.split(" ")[1]
    try:
        payload = AuthService.verify_jwt_token(token)
        github_id = payload["github_id"]
        user_doc = AuthService.get_user_by_github_id(github_id)
        if not user_doc or not user_doc.get("github_token"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User GitHub access token not found. Please log in again."
            )

        github_token = user_doc["github_token"]
        repos = await AuthService.fetch_user_repos(github_token)
        return repos

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching user repositories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve repositories from GitHub."
        )


@router.get("/repos/{owner}/{repo}/branches", response_model=List[BranchItem], summary="Get Repository Branches")
async def get_repo_branches(owner: str, repo: str, authorization: Optional[str] = Header(None)):
    """
    Validates JWT token and fetches branches for a specific repository using the user's stored GitHub token.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header."
        )

    token = authorization.split(" ")[1]
    try:
        payload = AuthService.verify_jwt_token(token)
        github_id = payload["github_id"]
        user_doc = AuthService.get_user_by_github_id(github_id)
        if not user_doc or not user_doc.get("github_token"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User GitHub access token not found. Please log in again."
            )

        github_token = user_doc["github_token"]
        branches = await AuthService.fetch_repo_branches(github_token, owner, repo)
        return branches

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        logger.error(f"Error fetching branches for {owner}/{repo}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve branches from GitHub."
        )

