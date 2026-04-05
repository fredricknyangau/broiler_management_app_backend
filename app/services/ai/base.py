from abc import ABC, abstractmethod
from typing import Dict, Any

class AIProvider(ABC):
    """
    Abstract Base Class representing an agnostic large language model provider.
    Subclasses should handle provider-specific authentication, HTTP parsing, and structured completions.
    """

    @abstractmethod
    async def generate_structured_response(self, system_prompt: str, user_prompt: str, json_schema: Dict[str, Any], image_base64: str = None) -> Dict[str, Any]:
        """
        Request a structured JSON response from the LLM provider.
        """
        pass
    @abstractmethod
    async def transcribe_audio(self, audio_bytes: bytes, filename: str) -> str:
        """
        Convert audio bytes to text transcript.
        """
        pass
