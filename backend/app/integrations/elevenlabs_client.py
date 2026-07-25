import httpx
from typing import Optional
from app.utils.config import settings
from app.utils.logger import get_logger

logger = get_logger()

class ElevenLabsAPIError(Exception):
    """Raised when the ElevenLabs API returns an error or fails to respond."""
    pass

class ElevenLabsClient:
    def __init__(self, api_key: Optional[str] = None, voice_id: Optional[str] = None):
        self.api_key = api_key or settings.ELEVENLABS_API_KEY
        self.voice_id = voice_id or settings.ELEVENLABS_VOICE_ID or "21m00Tcm4TlvDq8ikWAM"
        self.base_url = "https://api.elevenlabs.io/v1"

    async def text_to_speech(self, text: str) -> bytes:
        """
        Convert text to speech using ElevenLabs API.
        If no API key is configured or set to placeholder, runs in mock/simulation mode.
        """
        is_configured = self.api_key and self.api_key.strip() and self.api_key != "your_elevenlabs_api_key_here"
        
        if not is_configured:
            logger.info("ElevenLabs API Key not configured. Simulating TTS.")
            logger.info(f"Simulated TTS Speech text: '{text}'")
            # Return a simulated MP3 byte structure prefixing the text
            return b"MOCK_MP3_AUDIO_DATA:" + text.encode("utf-8")

        url = f"{self.base_url}/text-to-speech/{self.voice_id}"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "accept": "audio/mpeg"
        }
        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }

        logger.info(f"Sending TTS request to ElevenLabs (voice: {self.voice_id})")
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=headers)

            if response.status_code != 200:
                error_msg = f"ElevenLabs API returned status {response.status_code}: {response.text}"
                logger.error(error_msg)
                raise ElevenLabsAPIError(error_msg)

            logger.info("Successfully received ElevenLabs audio binary.")
            return response.content

        except httpx.TimeoutException as e:
            logger.error(f"ElevenLabs TTS request timed out: {e}")
            raise ElevenLabsAPIError("ElevenLabs TTS request timed out.") from e
        except httpx.RequestError as e:
            logger.error(f"ElevenLabs API network error: {e}")
            raise ElevenLabsAPIError(f"Network error communicating with ElevenLabs API: {str(e)}") from e
