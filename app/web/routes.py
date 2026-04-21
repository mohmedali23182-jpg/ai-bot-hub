import logging
from fastapi import APIRouter, Request, BackgroundTasks, Header, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from ..config import settings, TEMPLATES_DIR
from .. import db
from ..services.handlers import process_update
from ..services import telegram
from ..providers.factory import get_provider

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    stats = db.get_stats()
    recent = db.recent_messages(20)
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "app_name": settings.APP_NAME,
        "stats": stats,
        "messages": recent,
        "config": settings
    })


@router.get("/healthz")
async def healthz():
    """Enhanced health check for production monitoring."""
    status = {
        "app": "ok",
        "database": "ok",
        "provider": "ok",
        "telegram_token": "set" if settings.TELEGRAM_BOT_TOKEN else "missing",
        "ai_key": "set" if settings.AI_API_KEY else "missing",
    }
    
    # Check DB
    try:
        db.get_stats()
    except Exception as e:
        logger.error("Health check DB failed: %s", e)
        status["database"] = f"error: {str(e)}"
        
    # Check Provider
    try:
        if not get_provider():
            status["provider"] = "unsupported_or_error"
    except Exception as e:
        status["provider"] = f"error: {str(e)}"
        
    return status


@router.get("/metrics")
async def metrics():
    return db.get_stats()


@router.get("/telegram/webhook-info")
async def webhook_info():
    return await telegram.request('getWebhookInfo')


@router.post("/admin/set-webhook")
async def admin_set_webhook(password: str = Form(...)):
    if password != settings.DASHBOARD_PASSWORD:
        return JSONResponse({"ok": False, "error": "كلمة المرور غير صحيحة"}, status_code=403)
    
    res = await telegram.set_webhook()
    return res


@router.post("/telegram/webhook/{secret}")
async def telegram_webhook(
    secret: str, 
    request: Request, 
    background_tasks: BackgroundTasks,
    x_telegram_bot_api_secret_token: str = Header(None)
):
    # Double check secret in path and in header for extra security
    if secret != settings.TELEGRAM_WEBHOOK_SECRET:
        logger.warning("Invalid webhook secret in path: %s", secret)
        raise HTTPException(status_code=403, detail="Invalid secret")
        
    # Telegram sends the secret in X-Telegram-Bot-Api-Secret-Token header if set during setWebhook
    if x_telegram_bot_api_secret_token and x_telegram_bot_api_secret_token != settings.TELEGRAM_WEBHOOK_SECRET:
        logger.warning("Invalid X-Telegram-Bot-Api-Secret-Token header")
        raise HTTPException(status_code=403, detail="Invalid token header")

    try:
        update = await request.json()
    except Exception as e:
        logger.error("Failed to parse webhook JSON: %s", e)
        return {"ok": False, "error": "invalid json"}

    # Process in background to return 200 OK immediately to Telegram
    background_tasks.add_task(process_update, update)
    return {"ok": True}
