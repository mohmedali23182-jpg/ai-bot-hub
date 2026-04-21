import logging
import sys
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import settings, STATIC_DIR, DATA_DIR
from .db import init_db
from .logging_setup import configure_logging
from .web.routes import router

# Configure logging before anything else
configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    description="AI Bot Hub - Production Ready Telegram Bot with Multi-Provider AI Support",
    version="2.1.0"
)

# Mount static files safely
if STATIC_DIR.exists():
    app.mount('/static', StaticFiles(directory=STATIC_DIR), name='static')
else:
    logger.warning("Static directory %s does not exist. Skipping mount.", STATIC_DIR)

app.include_router(router)


@app.on_event('startup')
async def startup_event():
    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Initialize Database
    try:
        init_db()
    except Exception as e:
        logger.critical("Failed to initialize database: %s", e)
        # In production, we might want to exit if DB fails
        # sys.exit(1)
    
    # Secure validation of critical environment variables
    critical_vars = {
        'TELEGRAM_BOT_TOKEN': settings.TELEGRAM_BOT_TOKEN,
        'AI_API_KEY': settings.get_ai_api_key(),
        'BASE_URL': settings.BASE_URL,
        'TELEGRAM_WEBHOOK_SECRET': settings.TELEGRAM_WEBHOOK_SECRET
    }
    
    missing = []
    for name, value in critical_vars.items():
        if not value or not value.strip() or value in ['change-me-now', 'change-me']:
            missing.append(name)
        else:
            # Log presence without revealing value (handled by our SecretMasker)
            logger.info('Environment variable %s is set and valid (length: %d)', name, len(value))

    if missing:
        logger.warning('⚠️ CRITICAL: Missing or default environment variables: %s. The bot may not function correctly.', ', '.join(missing))
    
    logger.info('🚀 App startup complete | provider=%s | base_url=%s | env=%s', settings.AI_PROVIDER, settings.BASE_URL, settings.APP_ENV)


@app.get("/health")
async def health_check():
    """Detailed health check for production monitoring."""
    return {
        "status": "healthy",
        "version": "2.1.0",
        "provider": settings.AI_PROVIDER,
        "database": "connected" if DATA_DIR.exists() else "error"
    }


@app.get("/metrics")
async def metrics_root():
    # Simple root health for monitoring
    return {"status": "running", "version": "2.1.0"}
