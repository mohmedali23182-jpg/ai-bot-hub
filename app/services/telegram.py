import logging
from typing import Any, Dict, Optional, Tuple, List, Union
import httpx
import asyncio

from ..config import settings
from ..utils import retry_async, chunk_text

logger = logging.getLogger(__name__)


def tg_api(method: str) -> str:
    if not settings.TELEGRAM_BOT_TOKEN:
        raise ValueError('TELEGRAM_BOT_TOKEN is not set')
    return f'https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/{method}'


async def request(method: str, payload: Optional[Dict[str, Any]] = None, files: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error('Cannot make Telegram request: TELEGRAM_BOT_TOKEN is missing')
        return {'ok': False, 'error': 'TELEGRAM_BOT_TOKEN_MISSING'}
    
    async def _call():
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            if files:
                r = await client.post(tg_api(method), data=payload or {}, files=files)
            else:
                r = await client.post(tg_api(method), json=payload or {})
            
            # Handle rate limits and server errors specifically
            if r.status_code == 429:
                retry_after = int(r.headers.get('Retry-After', 2))
                logger.warning('Telegram Rate Limit (429). Retry-After: %d', retry_after)
                await asyncio.sleep(retry_after)
                raise httpx.HTTPStatusError('Telegram Rate Limit', request=r.request, response=r)
            
            if r.status_code >= 500:
                logger.warning('Telegram Server Error (%d)', r.status_code)
                raise httpx.HTTPStatusError('Telegram Server Error', request=r.request, response=r)
            
            r.raise_for_status()
            data = r.json()
            if not data.get('ok'):
                logger.error('Telegram API Error: %s', data.get('description'))
                return data
            return data

    try:
        return await retry_async(_call, retries=settings.API_RETRIES, initial_delay=1.0)
    except Exception as exc:
        logger.error('Telegram request failed after retries: %s', exc)
        return {'ok': False, 'error': str(exc)}


async def send_chat_action(chat_id: int, action: str = 'typing') -> None:
    try:
        await request('sendChatAction', {'chat_id': chat_id, 'action': action})
    except Exception as exc:
        logger.warning('sendChatAction failed: %s', exc)


async def send_message(chat_id: int, text: str, reply_to_message_id: Optional[int] = None, parse_mode: str = 'Markdown') -> None:
    keyboard = {
        'keyboard': [
            ['/mode_text', '/mode_code'],
            ['/mode_gen_image', '/mode_gen_video'],
            ['/clear', '/help'],
        ],
        'resize_keyboard': True,
    }
    
    # Handle empty text
    if not text or not text.strip():
        text = "⚠️ لم يصل رد نصي من المزود."

    chunks = chunk_text(text, settings.MAX_TELEGRAM_MESSAGE_LEN)
    for i, chunk in enumerate(chunks):
        payload = {
            'chat_id': chat_id,
            'text': chunk,
            'reply_to_message_id': reply_to_message_id if i == 0 else None,
            'reply_markup': keyboard if i == len(chunks) - 1 else None,
            'parse_mode': parse_mode
        }
        
        # Try Markdown first, if it fails, try plain text
        res = await request('sendMessage', payload)
        if not res.get('ok') and 'can\'t parse entities' in str(res.get('description', '')).lower():
            logger.warning("Markdown parsing failed in chat %d, falling back to plain text", chat_id)
            payload.pop('parse_mode', None)
            await request('sendMessage', payload)


async def send_photo(chat_id: int, photo_data: Union[str, bytes], caption: Optional[str] = None, reply_to_message_id: Optional[int] = None) -> None:
    payload = {
        'chat_id': chat_id,
        'caption': caption,
        'reply_to_message_id': reply_to_message_id
    }
    files = None
    if isinstance(photo_data, bytes):
        files = {'photo': ('image.jpg', photo_data, 'image/jpeg')}
    else:
        payload['photo'] = photo_data
    await request('sendPhoto', payload=payload, files=files)


async def send_video_url(chat_id: int, video_data: Union[str, bytes], caption: Optional[str] = None, reply_to_message_id: Optional[int] = None) -> None:
    payload = {
        'chat_id': chat_id,
        'caption': caption,
        'reply_to_message_id': reply_to_message_id
    }
    files = None
    if isinstance(video_data, bytes):
        files = {'video': ('video.mp4', video_data, 'video/mp4')}
    else:
        payload['video'] = video_data
    await request('sendVideo', payload=payload, files=files)


async def send_audio_url(chat_id: int, audio_data: Union[str, bytes], caption: Optional[str] = None, reply_to_message_id: Optional[int] = None) -> None:
    payload = {
        'chat_id': chat_id,
        'caption': caption,
        'reply_to_message_id': reply_to_message_id
    }
    files = None
    if isinstance(audio_data, bytes):
        files = {'audio': ('audio.mp3', audio_data, 'audio/mpeg')}
    else:
        payload['audio'] = audio_data
    await request('sendAudio', payload=payload, files=files)


async def get_file_url(file_id: str) -> str:
    data = await request('getFile', {'file_id': file_id})
    if not data.get('ok'):
        raise ValueError(f"Failed to get file info: {data.get('description')}")
    file_path = data['result']['file_path']
    return f'https://api.telegram.org/file/bot{settings.TELEGRAM_BOT_TOKEN}/{file_path}'


async def download_file(file_id: str) -> Tuple[bytes, str, str]:
    file_url = await get_file_url(file_id)

    async def _call():
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            r = await client.get(file_url)
            r.raise_for_status()
            return r.content, r.headers.get('content-type', 'application/octet-stream'), file_url

    content, mime, url = await retry_async(_call, retries=settings.DOWNLOAD_RETRIES, initial_delay=1.0)
    return content, mime, url


async def set_webhook() -> Dict[str, Any]:
    if not settings.BASE_URL:
        logger.error('Cannot set webhook: BASE_URL is missing')
        return {'ok': False, 'error': 'BASE_URL_MISSING'}
    
    webhook_url = f"{settings.BASE_URL.rstrip('/')}/telegram/webhook/{settings.TELEGRAM_WEBHOOK_SECRET}"
    logger.info('Setting webhook to: %s', webhook_url)
    
    payload = {
        'url': webhook_url,
        'secret_token': settings.TELEGRAM_WEBHOOK_SECRET,
        'allowed_updates': ['message', 'edited_message', 'callback_query']
    }
    return await request('setWebhook', payload)
