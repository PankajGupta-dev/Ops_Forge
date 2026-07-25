import os
from dotenv import load_dotenv, find_dotenv

# Load .env — search upward through parent directories to find the project-root .env
load_dotenv(find_dotenv(usecwd=True))

class Settings:
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GEMINI_API_KEY: str = os.getenv("GROQ_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GROQ_MODEL", "") or os.getenv("GEMINI_MODEL", "llama-3.3-70b-versatile")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
    BACKEND_HOST: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    RAILWAY_API_TOKEN: str = os.getenv("RAILWAY_API_TOKEN", "")
    RAILWAY_PROJECT_ID: str = os.getenv("RAILWAY_PROJECT_ID", "")
    RAILWAY_SERVICE_ID: str = os.getenv("RAILWAY_SERVICE_ID", "")
    GHCR_USERNAME: str = os.getenv("GHCR_USERNAME", "")
    GHCR_TOKEN: str = os.getenv("GHCR_TOKEN", "")
    GITHUB_ACTIONS_WORKFLOW: str = os.getenv("GITHUB_ACTIONS_WORKFLOW", "deploy.yml")
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
    ELEVENLABS_VOICE_ID: str = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    MONGODB_ATLAS_URI: str = os.getenv("MONGODB_ATLAS_URI", "")

    # GitHub OAuth & Security Configuration
    GITHUB_TOKEN: str = os.getenv("GITHUB_TOKEN", "")
    GITHUB_CLIENT_ID: str = os.getenv("GITHUB_CLIENT_ID", "")
    GITHUB_CLIENT_SECRET: str = os.getenv("GITHUB_CLIENT_SECRET", "")
    GITHUB_CALLBACK_URL: str = os.getenv("GITHUB_CALLBACK_URL", "http://localhost:8000/auth/github/callback")
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "opsforge_default_jwt_secret_key_2026")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")

    # Development flags
    SKIP_AGENT4: bool = os.getenv("SKIP_AGENT4", "false").lower() in ("true", "1", "yes")

settings = Settings()
