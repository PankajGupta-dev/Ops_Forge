import httpx
from typing import Dict, Any, Optional
from app.utils.config import settings
from app.utils.logger import get_logger

logger = get_logger()

class GeminiAPIError(Exception):
    """Raised when the LLM API (Groq / Gemini) returns an error or fails to respond."""
    pass

class GeminiClient:
    """
    LLM Client powered by Groq API (llama-3.3-70b-versatile).
    Maintains full interface compatibility for Agent 1, Agent 3, and Agent 4.
    """
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GROQ_API_KEY or settings.GEMINI_API_KEY
        self.model = model or settings.GROQ_MODEL or "llama-3.3-70b-versatile"
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"

    async def generate_json(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """
        Sends a prompt to Groq API requesting structured JSON output using llama-3.3-70b-versatile.
        Returns the raw text content of the LLM response.
        """
        if not self.api_key:
            logger.error("GROQ_API_KEY is not configured in environment settings.")
            raise GeminiAPIError("GROQ_API_KEY is missing. Please configure it in your .env file.")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }

        logger.info(f"Dispatching request to Groq API (model: {self.model})")

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(self.base_url, json=payload, headers=headers)

            if response.status_code != 200:
                error_msg = f"Groq API returned status {response.status_code}: {response.text}"
                logger.error(error_msg)
                raise GeminiAPIError(error_msg)

            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                raise GeminiAPIError("Groq API returned no response choices.")

            content = choices[0].get("message", {}).get("content", "").strip()
            if not content:
                raise GeminiAPIError("Groq choice contains no content.")

            logger.info("Successfully received Groq API response.")
            return content

        except httpx.TimeoutException as e:
            logger.error(f"Groq API request timed out: {e}")
            raise GeminiAPIError("Groq API request timed out.") from e
        except httpx.RequestError as e:
            logger.error(f"Groq API network error: {e}")
            raise GeminiAPIError(f"Network error communicating with Groq API: {str(e)}") from e

# Alias for explicit imports
GroqClient = GeminiClient
