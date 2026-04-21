from app.config import settings

from .base import AIProvider
from .gemini_provider import GeminiProvider
from .openai_provider import OpenAIProvider


def get_ai_provider() -> AIProvider:
    """
    Factory method to yield the dynamically selected AI architecture
    depending on .env variables. Defaults to OpenAI safely.
    """
    provider_name = getattr(settings, "LLM_PROVIDER", "openai").lower()

    if provider_name == "openai":
        return OpenAIProvider()
    elif provider_name == "gemini":
        return GeminiProvider()
    elif provider_name == "anthropic":
        raise NotImplementedError("Anthropic provider is not yet implemented")
    else:
        return OpenAIProvider()
