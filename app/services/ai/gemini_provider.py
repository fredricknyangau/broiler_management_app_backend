import json
import logging
from typing import Any, Dict

import httpx

from app.config import settings

from .base import AIProvider

logger = logging.getLogger(__name__)


class GeminiProvider(AIProvider):
    def __init__(self, api_key: str = None):
        self.api_key = api_key or getattr(settings, "LLM_API_KEY", "")
        self.model = getattr(settings, "GEMINI_MODEL", "gemini-1.5-flash")
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    async def generate_structured_response(
        self,
        system_prompt: str,
        user_prompt: str,
        json_schema: Dict[str, Any],
        image_base64: str = None,
    ) -> Dict[str, Any]:
        """
        Hit Google Gemini 1.5 using manual HTTP.
        """
        if not self.api_key:
            raise ValueError("LLM_API_KEY not configured for Gemini")

        url = f"{self.base_url}?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        combined_text = (
            f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\nUSER PROMPT:\n{user_prompt}"
        )

        parts = [{"text": combined_text}]
        if image_base64:
            parts.append(
                {
                    "inlineData": {
                        "mimeType": "image/jpeg",  # Default to jpeg
                        "data": image_base64,
                    }
                }
            )

        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.error(f"Gemini API Http Error: {e.response.status_code}")
                raise ValueError(
                    f"Gemini API Error: HTTP {e.response.status_code}"
                ) from None
            except Exception as e:
                logger.error(f"Gemini API Connection failed: {str(e)}")
                raise ValueError("Gemini API connection failed") from None

            data = response.json()

            try:
                raw_content = data["candidates"][0]["content"]["parts"][0]["text"]
                return json.loads(raw_content)
            except (KeyError, IndexError) as e:
                logger.error(f"Gemini response structure mismatch: {data}")
                raise ValueError("AI Provider returned malformed response tree") from e
            except json.JSONDecodeError as e:
                logger.error(f"Gemini returned invalid JSON: {data}")
                raise ValueError("AI Provider returned invalid JSON string") from e

    async def transcribe_audio(
        self, audio_bytes: bytes, filename: str = "audio.wav"
    ) -> str:
        """
        Transcribe audio using Google Gemini multimodal capabilities.
        """
        import base64

        if not self.api_key:
            raise ValueError("LLM_API_KEY not configured for Gemini")

        url = f"{self.base_url}?key={self.api_key}"
        headers = {"Content-Type": "application/json"}

        mime_type = "audio/mpeg" if filename.endswith(".mp3") else "audio/wav"
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": "Please transcribe this audio exactly as heard. Return only the transcript text."
                        },
                        {"inlineData": {"mimeType": mime_type, "data": audio_base64}},
                    ],
                }
            ],
            "generationConfig": {"temperature": 0.0},
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
                return data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                logger.error(f"Gemini Transcription Error: {e}")
                raise ValueError(f"Gemini transcription failed: {str(e)}")
