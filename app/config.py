from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Set, Optional
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
    AI_API_KEY: str = ''
    AI_MODEL_TEXT: str = 'gemini-2.0-flash'
    AI_MODEL_VISION: str = 'gemini-2.0-flash'
    AI_MODEL_AUDIO: str = 'gemini-2.0-flash'
    AI_MODEL_VIDEO: str = 'gemini-2.0-flash'
    AI_MODEL_CODE: str = 'gemini-2.0-flash'

    # OpenAI Compatible Provider Settings
    OPENAI_COMPAT_BASE_URL: str = 'https://api.openai.com/v1'
    OPENAI_COMPAT_VISION_INPUT_MODE: str = 'url'  # url | text_only

    # OpenRouter Specific Settings
    OPENROUTER_BASE_URL: str = 'https://openrouter.ai/api/v1'
    OPENROUTER_HTTP_REFERER: str = 'https://github.com/mohmedali23182-jpg/ai-bot-hub'
    OPENROUTER_APP_NAME: str = 'AI Bot Hub'

    # Operational Limits
    GEMINI_MAX_INLINE_BYTES: int = 18 * 1024 * 1024
    REQUEST_TIMEOUT: float = 90.0
    MAX_HISTORY_TURNS: int = 10
    ENABLE_TYPING: bool = True
    DB_PATH: str = 'data/bot.db'
    MAX_TELEGRAM_MESSAGE_LEN: int = 4096
    DOWNLOAD_RETRIES: int = 3
    API_RETRIES: int = 3

    @field_validator('TELEGRAM_BOT_TOKEN', 'AI_API_KEY', 'BASE_URL', 'TELEGRAM_WEBHOOK_SECRET', mode='before')
    @classmethod
    def strip_sensitive_vars(cls, v: str) -> str:
        if isinstance(v, str):
            # Remove any surrounding whitespace or newlines
            return v.strip()
        return v

    @property
    def admin_ids(self) -> Set[int]:
        if not self.TELEGRAM_ADMIN_IDS:
            return set()
        return {int(x.strip()) for x in self.TELEGRAM_ADMIN_IDS.split(',') if x.strip().isdigit()}


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
