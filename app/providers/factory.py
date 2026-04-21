from ..config import settings
from .base import AIProvider
from .gemini_provider import GeminiProvider
from .openai_compatible_provider import OpenAICompatibleProvider


import logging

logger = logging.getLogger(__name__)

def get_provider() -> AIProvider | None:
    provider = settings.AI_PROVIDER.strip().lower()
    if provider == 'gemini':
        return GeminiProvider()
    elif provider == 'openai_compatible':
        return OpenAICompatibleProvider()
    else:
        logger.error('Unsupported AI_PROVIDER: %s. Please check your AI_PROVIDER setting.', settings.AI_PROVIDER)
        return None