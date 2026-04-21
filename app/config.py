from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Set


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

    AI_PROVIDER: str = 'gemini'  # gemini | openai_compatible
    AI_API_KEY: str = ''
    AI_MODEL_TEXT: str = 'gemini-2.5-flash'
    AI_MODEL_VISION: str = 'gemini-2.5-flash'
    AI_MODEL_AUDIO: str = 'gemini-2.5-flash'
    AI_MODEL_VIDEO: str = 'gemini-2.5-flash'
    AI_MODEL_CODE: str = 'gemini-2.5-flash'
    OPENAI_COMPAT_BASE_URL: str = 'https://api.openai.com/v1'
    OPENAI_COMPAT_VISION_INPUT_MODE: str = 'url'  # url | text_only

    GEMINI_MAX_INLINE_BYTES: int = 18 * 1024 * 1024
    REQUEST_TIMEOUT: float = 90.0
    MAX_HISTORY_TURNS: int = 8
    ENABLE_TYPING: bool = True
    DB_PATH: str = 'bot.db'
    MAX_TELEGRAM_MESSAGE_LEN: int = 4096
    DOWNLOAD_RETRIES: int = 3
    API_RETRIES: int = 2

    @property
    def admin_ids(self) -> Set[int]:
        return {int(x.strip()) for x in self.TELEGRAM_ADMIN_IDS.split(',') if x.strip().isdigit()}


settings = Settings()
