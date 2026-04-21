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
    logger.info('App startup complete | provider=%s | base_url=%s', settings.AI_PROVIDER, settings.BASE_URL)
    missing = []
    if not settings.TELEGRAM_BOT_TOKEN:
        missing.append('TELEGRAM_BOT_TOKEN')
    if not settings.AI_API_KEY:
        missing.append('AI_API_KEY')
    if not settings.BASE_URL:
        missing.append('BASE_URL')
    if missing:
        logger.warning('Missing env vars: %s', ', '.join(missing))
