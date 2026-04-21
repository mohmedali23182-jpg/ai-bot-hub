from ..config import settings
from .base import AIProvider
from .gemini_provider import GeminiProvider
from .openai_compatible_provider import OpenAICompatibleProvider


def get_provider() -> AIProvider:
    provider = settings.AI_PROVIDER.strip().lower()
    if provider == 'gemini':
        return GeminiProvider()
    if provider == 'openai_compatible':
        return OpenAICompatibleProvider()
    raise ValueError(f'Unsupported AI_PROVIDER: {settings.AI_PROVIDER}')
