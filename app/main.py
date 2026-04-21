import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import settings, STATIC_DIR
from .db import init_db
from .logging_setup import configure_logging
from .web.routes import router

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.APP_NAME)
app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')
app.include_router(router)


@app.on_event('startup')
async def startup_event():
    init_db()
    
    # Secure validation of critical environment variables
    critical_vars = {
        'TELEGRAM_BOT_TOKEN': settings.TELEGRAM_BOT_TOKEN,
        'AI_API_KEY': settings.AI_API_KEY,
        'BASE_URL': settings.BASE_URL,
        'TELEGRAM_WEBHOOK_SECRET': settings.TELEGRAM_WEBHOOK_SECRET
    }
    
    missing = []
    for name, value in critical_vars.items():
        if not value or not value.strip():
            missing.append(name)
        else:
            # Log presence without revealing value
            logger.info('Environment variable %s is set and valid (length: %d)', name, len(value))

    if missing:
        logger.warning('CRITICAL: Missing or empty environment variables: %s. The bot may not function correctly.', ', '.join(missing))
    
    logger.info('App startup complete | provider=%s | base_url=%s', settings.AI_PROVIDER, settings.BASE_URL)
