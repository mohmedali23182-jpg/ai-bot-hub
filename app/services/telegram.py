import logging
from typing import Any, Dict, Optional, Tuple
import httpx

from ..config import settings
from ..utils import retry_async

logger = logging.getLogger(__name__)


def tg_api(method: str) -> str:
    if not settings.TELEGRAM_BOT_TOKEN:
        raise ValueError('TELEGRAM_BOT_TOKEN is not set')
    return f'https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/{method}'


async def request(method: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error('Cannot make Telegram request: TELEGRAM_BOT_TOKEN is missing')
        return {'ok': False, 'error': 'TELEGRAM_BOT_TOKEN_MISSING'}
    async def _call():
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            r = await client.post(tg_api(method), json=payload or {})
            r.raise_for_status()
            return r.json()
    return await retry_async(_call, retries=settings.API_RETRIES, delay=1.0)


async def send_chat_action(chat_id: int, action: str = 'typing') -> None:
    try:
        await request('sendChatAction', {'chat_id': chat_id, 'action': action})
    except Exception as exc:
        logger.warning('sendChatAction failed: %s', exc)


async def send_message(chat_id: int, text: str, reply_to_message_id: Optional[int] = None) -> None:
    keyboard = {
        'keyboard': [
            ['/mode_text', '/mode_image'],
            ['/mode_audio', '/mode_video'],
            ['/mode_code', '/help'],
        ],
        'resize_keyboard': True,
    }
    from ..utils import chunk_text
    for chunk in chunk_text(text, settings.MAX_TELEGRAM_MESSAGE_LEN):
        await request('sendMessage', {
            'chat_id': chat_id,
            'text': chunk or ' ',
            'reply_to_message_id': reply_to_message_id,
            'reply_markup': keyboard,
        })
        reply_to_message_id = None


async def get_file_url(file_id: str) -> str:
    data = await request('getFile', {'file_id': file_id})
    file_path = data['result']['file_path']
    return f'https://api.telegram.org/file/bot{settings.TELEGRAM_BOT_TOKEN}/{file_path}'


async def download_file(file_id: str) -> Tuple[bytes, str, str]:
    file_url = await get_file_url(file_id)

    async def _call():
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            r = await client.get(file_url)
            r.raise_for_status()
            return r.content, r.headers.get('content-type', 'application/octet-stream'), file_url

    return await retry_async(_call, retries=settings.DOWNLOAD_RETRIES, delay=1.0)


async def set_webhook() -> Dict[str, Any]:
    if not settings.BASE_URL:
        logger.error('Cannot set webhook: BASE_URL is missing')
        return {'ok': False, 'error': 'BASE_URL_MISSING'}
    webhook_url = f"{settings.BASE_URL.rstrip('/')}/telegram/webhook/{settings.TELEGRAM_WEBHOOK_SECRET}"
    logger.info('Setting webhook to: %s', webhook_url)
    return await request('setWebhook', {'url': webhook_url})
