import httpx
from typing import Dict, Any, Optional
from app.utils.config import settings
from app.utils.logger import get_logger

logger = get_logger()

class GeminiAPIError(Exception):
    """Raised when the Gemini API returns an error or fails to respond."""
    pass

class GeminiClient:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    async def generate_json(self, prompt: str, system_instruction: Optional[str] = None) -> str:
        """
        Sends a prompt to Gemini API requesting structured JSON output.
        Returns the raw text content of the LLM response.
        """
        if not self.api_key:
            logger.error("GEMINI_API_KEY is not configured in environment settings.")
            raise GeminiAPIError("GEMINI_API_KEY is missing. Please configure it in your .env file.")

        url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
        
        contents = [{
            "parts": [{"text": prompt}]
        }]

        payload: Dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2,
                "topP": 0.95
            }
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        logger.info(f"Dispatching request to Gemini API (model: {self.model})")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload)

            if response.status_code != 200:
                error_msg = f"Gemini API returned status {response.status_code}: {response.text}"
                logger.error(error_msg)
                raise GeminiAPIError(error_msg)

            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise GeminiAPIError("Gemini API returned no response candidates.")

            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                raise GeminiAPIError("Gemini candidate contains no content parts.")

            raw_text = parts[0].get("text", "").strip()
            logger.info("Successfully received Gemini API response.")
            return raw_text

        except httpx.TimeoutException as e:
            logger.error(f"Gemini API request timed out: {e}")
            raise GeminiAPIError("Gemini API request timed out.") from e
        except httpx.RequestError as e:
            logger.error(f"Gemini API network error: {e}")
            raise GeminiAPIError(f"Network error communicating with Gemini API: {str(e)}") from e
