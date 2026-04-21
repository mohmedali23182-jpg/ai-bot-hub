import logging
from typing import Optional
from ..config import settings
from .base import AIProvider
from .gemini_provider import GeminiProvider
from .openai_compatible_provider import OpenAICompatibleProvider

logger = logging.getLogger(__name__)

def get_provider() -> Optional[AIProvider]:
    provider_name = settings.AI_PROVIDER.strip().lower()
    
    try:
        if provider_name == 'gemini':
            return GeminiProvider()
            
        if provider_name == 'openai_compatible':
            return OpenAICompatibleProvider(
                base_url=settings.OPENAI_COMPAT_BASE_URL,
                is_openrouter=False
            )
            
        if provider_name == 'openrouter':
            return OpenAICompatibleProvider(
                base_url=settings.OPENROUTER_BASE_URL,
                is_openrouter=True
            )
            
        logger.error('Unsupported AI_PROVIDER: %s', provider_name)
        return None
        
    except Exception as exc:
        logger.exception('Failed to initialize provider %s: %s', provider_name, exc)
        return None
