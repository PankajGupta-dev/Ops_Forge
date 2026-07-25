"""
Auth Service — GitHub OAuth integration, JWT generation, user persistence in MongoDB, and GitHub repository fetching.
"""

import time
import logging
from typing import Dict, Any, List, Optional
import httpx
import jwt

from app.utils.config import settings
from app.utils.logger import get_logger
from app.integrations.mongodb_client import MongoDBAtlasClient
from app.schemas.auth import UserProfile, RepositoryItem, BranchItem

logger = get_logger()

# Dedicated MongoDB Atlas collection for OpsForge user accounts
user_db_client = MongoDBAtlasClient(db_name="OpsForge", collection_name="users")


class AuthService:
    """Service handling GitHub OAuth workflow, JWT management, and GitHub API proxies."""

    @staticmethod
    def get_github_auth_url() -> str:
        """Constructs the GitHub OAuth authorization URL."""
        client_id = settings.GITHUB_CLIENT_ID
        callback_url = settings.GITHUB_CALLBACK_URL
        scope = "user,repo"
        return (
            f"https://github.com/login/oauth/authorize?"
            f"client_id={client_id}&redirect_uri={callback_url}&scope={scope}"
        )

    @staticmethod
    async def exchange_code_for_token(code: str) -> str:
        """Exchanges authorization code for GitHub access token."""
        url = "https://github.com/login/oauth/access_token"
        payload = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": settings.GITHUB_CALLBACK_URL,
        }
        headers = {"Accept": "application/json"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                logger.error(f"GitHub token exchange failed: {response.text}")
                raise ValueError("Failed to exchange authorization code with GitHub.")

            data = response.json()
            access_token = data.get("access_token")
            if not access_token:
                error_desc = data.get("error_description", "No access_token returned")
                raise ValueError(f"GitHub OAuth error: {error_desc}")

            return access_token

    @staticmethod
    async def fetch_github_profile(github_token: str) -> Dict[str, Any]:
        """Fetches the authenticated user profile from GitHub API."""
        url = "https://api.github.com/user"
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "OpsForge-App",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                logger.error(f"GitHub profile fetch failed: {response.text}")
                raise ValueError("Failed to fetch user profile from GitHub.")

            return response.json()

    @classmethod
    def save_or_update_user(cls, profile_data: Dict[str, Any], github_token: str) -> UserProfile:
        """Creates or updates the user record in MongoDB Atlas."""
        github_id = profile_data["id"]
        doc_id = f"user-{github_id}"

        user_doc = {
            "id": doc_id,
            "github_id": github_id,
            "username": profile_data.get("login", ""),
            "name": profile_data.get("name"),
            "email": profile_data.get("email"),
            "avatar_url": profile_data.get("avatar_url"),
            "html_url": profile_data.get("html_url"),
            "github_token": github_token,
            "updated_at": time.time(),
        }

        # Store in MongoDB via MongoDBAtlasClient
        user_db_client.insert_incident(user_doc)
        logger.info(f"Successfully saved/updated user {user_doc['username']} (ID: {github_id}) in MongoDB. "
                    f"Token stored: {'yes' if github_token else 'no'}, "
                    f"DB connected: {user_db_client.is_connected}")

        return UserProfile(
            github_id=github_id,
            username=user_doc["username"],
            name=user_doc["name"],
            email=user_doc["email"],
            avatar_url=user_doc["avatar_url"],
            html_url=user_doc["html_url"],
        )

    @classmethod
    def get_user_by_github_id(cls, github_id: Any) -> Optional[Dict[str, Any]]:
        """Retrieves user document from MongoDB Atlas or fallback memory store."""
        doc_id = f"user-{github_id}"
        gid_int = int(github_id) if str(github_id).isdigit() else github_id
        query = {"$or": [{"id": doc_id}, {"github_id": gid_int}, {"github_id": str(github_id)}]}

        logger.info(f"Looking up user by github_id={github_id} (type={type(github_id).__name__}), "
                    f"doc_id={doc_id}, DB connected: {user_db_client.is_connected}")

        user_db_client.ensure_connected()
        if user_db_client.is_connected and user_db_client.collection is not None:
            try:
                user_doc = user_db_client.collection.find_one(query)
                if user_doc:
                    has_token = bool(user_doc.get("github_token"))
                    logger.info(f"Found user '{user_doc.get('username')}' in MongoDB Atlas. "
                                f"Has github_token: {has_token}")
                    return user_doc
                else:
                    logger.warning(f"User not found in MongoDB Atlas for query: {query}")
            except Exception as e:
                logger.error(f"MongoDB search failed: {e}")

        # Check in-memory fallback
        mem_doc = user_db_client._in_memory_store.get(doc_id)
        if mem_doc:
            logger.info(f"Found user in in-memory store. Has github_token: {bool(mem_doc.get('github_token'))}")
        else:
            logger.warning(f"User not found in in-memory store either. "
                           f"Memory store keys: {list(user_db_client._in_memory_store.keys())}")
        return mem_doc

    @staticmethod
    def create_jwt_token(github_id: int, username: str) -> str:
        """Generates a signed JWT access token for authentication."""
        payload = {
            "sub": str(github_id),
            "github_id": github_id,
            "username": username,
            "iat": int(time.time()),
            "exp": int(time.time()) + (7 * 24 * 3600),  # 7-day expiration
        }
        return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    @staticmethod
    def verify_jwt_token(token: str) -> Dict[str, Any]:
        """Decodes and validates a JWT access token."""
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise ValueError("Authentication token has expired.")
        except jwt.InvalidTokenError:
            raise ValueError("Invalid authentication token.")

    @classmethod
    async def fetch_user_repos(cls, github_token: str) -> List[RepositoryItem]:
        """Fetches the user's GitHub repositories."""
        url = "https://api.github.com/user/repos?sort=updated&per_page=100"
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "OpsForge-App",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                logger.error(f"GitHub repos fetch failed: {response.text}")
                raise ValueError("Failed to fetch repositories from GitHub.")

            repos_data = response.json()
            items = []
            for repo in repos_data:
                items.append(
                    RepositoryItem(
                        id=repo["id"],
                        name=repo["name"],
                        full_name=repo["full_name"],
                        default_branch=repo.get("default_branch", "main"),
                        visibility=repo.get("visibility", "public" if not repo.get("private") else "private"),
                        clone_url=repo.get("clone_url", ""),
                        html_url=repo.get("html_url"),
                        description=repo.get("description"),
                    )
                )
            return items

    @classmethod
    async def fetch_repo_branches(cls, github_token: str, owner: str, repo: str) -> List[BranchItem]:
        """Fetches available branches for a GitHub repository."""
        url = f"https://api.github.com/repos/{owner}/{repo}/branches?per_page=100"
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "OpsForge-App",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers=headers)
            if response.status_code != 200:
                logger.error(f"GitHub branches fetch failed: {response.text}")
                raise ValueError("Failed to fetch branches from GitHub.")

            branches_data = response.json()
            items = []
            for branch in branches_data:
                items.append(
                    BranchItem(
                        name=branch["name"],
                        protected=branch.get("protected", False),
                    )
                )
            return items

