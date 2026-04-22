from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Set, Optional, Union
from pathlib import Path
from pydantic import field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    APP_NAME: str = 'AI Bot Hub'
    APP_ENV: str = 'production'
    PORT: int = 8000
    BASE_URL: str = ''
    LOG_LEVEL: str = 'INFO'

    TELEGRAM_BOT_TOKEN: str = ''
    TELEGRAM_WEBHOOK_SECRET: str = 'change-me-now'
    TELEGRAM_ADMIN_IDS: str = ''
    DASHBOARD_PASSWORD: str = 'change-me'

    # AI Provider Settings
    AI_PROVIDER: str = 'gemini'  # gemini | openai_compatible | openrouter
    AI_API_KEY: str = '' # General API Key (used for Gemini/OpenAI)
    
    # OpenRouter Specific Settings
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_BASE_URL: str = 'https://openrouter.ai/api/v1'
    OPENROUTER_HTTP_REFERER: str = 'https://ai-bot-hub-production.up.railway.app'
    OPENROUTER_APP_NAME: str = 'AI Bot Hub'

    # OpenAI Compatible Provider Settings
    OPENAI_COMPAT_BASE_URL: str = 'https://api.openai.com/v1'
    OPENAI_COMPAT_VISION_INPUT_MODE: str = 'url'  # url | base64

    # Models
    AI_MODEL_TEXT: str = 'gemini-2.0-flash'
    AI_MODEL_VISION: str = 'gemini-2.0-flash'
    AI_MODEL_AUDIO: str = 'gemini-2.0-flash'
    AI_MODEL_VIDEO: str = 'gemini-2.0-flash'
    AI_MODEL_CODE: str = 'gemini-2.0-flash'
    
    # Generation Models
    AI_MODEL_GEN_IMAGE: str = 'openai/dall-e-3'
    AI_MODEL_GEN_VIDEO: str = 'luma/dream-machine'
    AI_MODEL_GEN_MUSIC: str = 'suno/chirp-v3-5'
    
    # Gemini-specific generation models
    AI_MODEL_GEMINI_IMAGE: str = 'imagen-3.0-generate-002'
    AI_MODEL_GEMINI_VIDEO: str = 'veo-2.0-generate'

    # Operational Limits
    GEMINI_MAX_INLINE_BYTES: int = 18 * 1024 * 1024
    REQUEST_TIMEOUT: float = 90.0
    MAX_HISTORY_TURNS: int = 10
    ENABLE_TYPING: bool = True
    DB_PATH: str = 'data/bot.db'
    MAX_TELEGRAM_MESSAGE_LEN: int = 4000
    DOWNLOAD_RETRIES: int = 3
    API_RETRIES: int = 3

    @field_validator('*', mode='before')
    @classmethod
    def strip_all_strings(cls, v: any) -> any:
        if isinstance(v, str):
            return v.strip()
        return v

    @property
    def admin_ids(self) -> Set[int]:
        if not self.TELEGRAM_ADMIN_IDS:
            return set()
        return {int(x.strip()) for x in self.TELEGRAM_ADMIN_IDS.split(',') if x.strip().isdigit()}

    def get_ai_api_key(self) -> str:
        """
        Returns the appropriate API key based on the provider.
        If provider is openrouter, it prioritizes OPENROUTER_API_KEY.
        Otherwise, it falls back to AI_API_KEY.
        """
        if self.AI_PROVIDER == 'openrouter':
            return self.OPENROUTER_API_KEY or self.AI_API_KEY
        return self.AI_API_KEY


settings = Settings()

# Path definitions
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / 'data'
STATIC_DIR = BASE_DIR / 'static'
TEMPLATES_DIR = BASE_DIR / 'templates'

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

# Update DB_PATH to use absolute path in data directory
if not Path(settings.DB_PATH).is_absolute():
    settings.DB_PATH = str(DATA_DIR / Path(settings.DB_PATH).name)
