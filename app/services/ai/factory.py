from app.config import settings
from .base import AIProvider
from .openai_provider import OpenAIProvider
# AnthropicProvider can be imported here later

def get_ai_provider() -> AIProvider:
    """
    Factory method to yield the dynamically selected AI architecture
    depending on .env variables. Defaults to OpenAI safely.
    """
    provider_name = getattr(settings, "LLM_PROVIDER", "openai").lower()
    
    if provider_name == "openai":
        return OpenAIProvider()
    elif provider_name == "anthropic":
        # return AnthropicProvider()
        raise NotImplementedError("Anthropic provider is not yet implemented")
    else:
        return OpenAIProvider()
