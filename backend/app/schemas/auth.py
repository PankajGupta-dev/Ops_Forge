"""
Pydantic schemas for GitHub OAuth and Authentication module.
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class GitHubLoginResponse(BaseModel):
    """Response model for GET /auth/github/login"""
    login_url: str = Field(..., description="GitHub OAuth authorization redirect URL")


class UserProfile(BaseModel):
    """Authenticated user profile representation."""
    github_id: int = Field(..., description="Unique GitHub user ID")
    username: str = Field(..., description="GitHub username (login)")
    name: Optional[str] = Field(None, description="User full name")
    email: Optional[str] = Field(None, description="User email address")
    avatar_url: Optional[str] = Field(None, description="GitHub avatar image URL")
    html_url: Optional[str] = Field(None, description="GitHub profile page URL")


class AuthTokenResponse(BaseModel):
    """Response model returned after successful GitHub OAuth callback or token exchange."""
    access_token: str = Field(..., description="Signed JWT authorization token")
    token_type: str = Field(default="bearer", description="Token type")
    user: UserProfile = Field(..., description="Authenticated user profile details")


class RepositoryItem(BaseModel):
    """GitHub repository representation returned by GET /auth/repos."""
    id: int = Field(..., description="Repository ID")
    name: str = Field(..., description="Repository name")
    full_name: str = Field(..., description="Full repository path (owner/repo)")
    default_branch: str = Field(default="main", description="Default git branch")
    visibility: str = Field(default="public", description="Repository visibility (public/private)")
    clone_url: str = Field(..., description="HTTPS clone URL")
    html_url: Optional[str] = Field(None, description="GitHub repository web URL")
    description: Optional[str] = Field(None, description="Repository description")


class BranchItem(BaseModel):
    """GitHub branch representation returned by GET /auth/repos/{owner}/{repo}/branches."""
    name: str = Field(..., description="Branch name (e.g., main, master, dev)")
    protected: bool = Field(default=False, description="Whether branch is protected")

