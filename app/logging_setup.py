import logging
import sys
import re
from .config import settings

class SecretMasker(logging.Filter):
    def __init__(self, secrets=None):
        super().__init__()
        self.secrets = secrets or []

    def filter(self, record):
        # Handle formatted message
        message = record.getMessage()
        for secret in self.secrets:
            if secret and len(secret) > 4:
                # Mask secret but keep first/last 2 chars
                masked = secret[:2] + '*' * (len(secret) - 4) + secret[-2:]
                message = message.replace(secret, masked)
        
        # Regex to catch typical token/key patterns
        message = re.sub(r'bot\d+:[a-zA-Z0-9_-]{35}', 'bot<TOKEN_MASKED>', message)
        
        # Override message and clear args to avoid re-formatting
        record.msg = message
        record.args = ()
        return True

def configure_logging():
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
        
    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    handler.setFormatter(formatter)
    
    # Add secret masking filter
    secrets_to_mask = [
        settings.TELEGRAM_BOT_TOKEN,
        settings.AI_API_KEY,
        settings.TELEGRAM_WEBHOOK_SECRET,
        settings.DASHBOARD_PASSWORD
    ]
    handler.addFilter(SecretMasker(secrets_to_mask))
    
    root_logger.addHandler(handler)
    
    # Quiet down noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    logging.info("Logging configured | level=%s", settings.LOG_LEVEL)
