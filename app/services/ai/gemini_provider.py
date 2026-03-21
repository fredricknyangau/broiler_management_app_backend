import httpx
from typing import Dict, Any
from .base import AIProvider
from app.config import settings
import json
import logging

logger = logging.getLogger(__name__)

class GeminiProvider(AIProvider):
    def __init__(self, api_key: str = None):
        self.api_key = api_key or getattr(settings, "LLM_API_KEY", "")
        self.model = getattr(settings, "GEMINI_MODEL", "gemini-1.5-flash")
        self.base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

    async def generate_structured_response(self, system_prompt: str, user_prompt: str, json_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hit Google Gemini 1.5 using manual HTTP.
        """
        if not self.api_key:
            raise ValueError("LLM_API_KEY not configured for Gemini")

        url = f"{self.base_url}?key={self.api_key}"
        headers = {"Content-Type": "application/json"}
        combined_text = f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\nUSER PROMPT:\n{user_prompt}"

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": combined_text}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json"
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
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


