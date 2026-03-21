import httpx
from typing import Dict, Any
from .base import AIProvider
from app.config import settings
import json
import logging

logger = logging.getLogger(__name__)

class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str = None):
        self.api_key = api_key or getattr(settings, "LLM_API_KEY", "")
        self.base_url = "https://api.openai.com/v1/chat/completions"

    async def generate_structured_response(self, system_prompt: str, user_prompt: str, json_schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Hit OpenAI and force the JSON parser mapping to our payload constraints.
        """
        if not self.api_key:
            raise ValueError("LLM_API_KEY not configured for OpenAI")
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-4-turbo-preview",  # Using a robust model for reasoning
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            raw_content = data["choices"][0]["message"]["content"]
            
            try:
                return json.loads(raw_content)
            except json.JSONDecodeError as e:
                logger.error(f"OpenAI returned malformed JSON: {raw_content}")
                raise ValueError("AI Provider returned invalid JSON") from e
