from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from ..config import settings
from .. import db
from ..services.handlers import process_update
from ..services.telegram import set_webhook, request as tg_request

router = APIRouter()
templates = Jinja2Templates(directory='app/templates')


@router.get('/', response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(
        request,
        'dashboard.html',
        {
            'request': request,
            'app_name': settings.APP_NAME,
            'stats': db.get_stats(),
            'messages': db.recent_messages(12),
            'config': settings,
        }
    )


@router.get('/healthz')
async def healthz():
    return {
        'ok': True,
        'app': settings.APP_NAME,
        'provider': settings.AI_PROVIDER,
        'telegram': bool(settings.TELEGRAM_BOT_TOKEN),
        'ai_key': bool(settings.AI_API_KEY),
        'base_url': settings.BASE_URL,
    }


@router.get('/metrics')
async def metrics():
    return db.get_stats()


@router.get('/telegram/webhook-info')
async def webhook_info():
    return await tg_request('getWebhookInfo')


@router.post('/admin/set-webhook')
async def admin_set_webhook(password: str = Form(...)):
    if password != settings.DASHBOARD_PASSWORD:
        raise HTTPException(status_code=403, detail='Invalid password')
    return JSONResponse(await set_webhook())


@router.post('/telegram/webhook/{secret}')
async def telegram_webhook(secret: str, request: Request, background_tasks: BackgroundTasks):
    if secret != settings.TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail='Invalid secret')
    payload = await request.json()
    background_tasks.add_task(process_update, payload)
    return {'ok': True}
