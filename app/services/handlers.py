import logging
import mimetypes
from ..config import settings
from .. import db
from ..providers.factory import get_provider
from . import telegram
from .router import welcome_text, help_text, prompt_for_kind

logger = logging.getLogger(__name__)
provider = get_provider()


async def process_update(update: dict) -> None:
    message = update.get('message') or update.get('edited_message')
    if not message:
        return

    chat_id = int(message['chat']['id'])
    message_id = int(message['message_id'])
    text = (message.get('text') or message.get('caption') or '').strip()
    mode = db.get_mode(chat_id)

    if settings.ENABLE_TYPING:
        await telegram.send_chat_action(chat_id)

    if text.startswith('/'):
        cmd = text.split()[0].lower()
        mode_map = {
            '/mode_text': 'text',
            '/mode_image': 'image',
            '/mode_audio': 'audio',
            '/mode_video': 'video',
            '/mode_code': 'code',
        }
        if cmd == '/start':
            db.bump_stat('cmd_start')
            return await telegram.send_message(chat_id, welcome_text(), message_id)
        if cmd == '/help':
            db.bump_stat('cmd_help')
            return await telegram.send_message(chat_id, help_text(), message_id)
        if cmd == '/clear':
            db.clear_history(chat_id)
            return await telegram.send_message(chat_id, 'تم مسح سياق المحادثة.', message_id)
        if cmd == '/status':
            return await telegram.send_message(
                chat_id,
                f'جاهز\\nprovider={settings.AI_PROVIDER}\\nmode={mode}\\nbase_url={settings.BASE_URL}',
                message_id,
            )
        if cmd == '/dashboard':
            return await telegram.send_message(chat_id, f"لوحة التحكم: {settings.BASE_URL.rstrip('/')}/", message_id)
        if cmd in mode_map:
            db.set_mode(chat_id, mode_map[cmd])
            db.bump_stat(f"mode_{mode_map[cmd]}")
            return await telegram.send_message(chat_id, f"تم التبديل إلى وضع: {mode_map[cmd]}", message_id)

    try:
        if message.get('photo'):
            db.bump_stat('image_requests')
            photo = message['photo'][-1]
            data, content_type, file_url = await telegram.download_file(photo['file_id'])
            result = await provider.generate_multimodal(prompt_for_kind('image', text), 'image', data, content_type or 'image/jpeg', file_url=file_url)
            db.add_message(chat_id, 'user', text or '[image]', 'image')
            db.add_message(chat_id, 'model', result, 'image')
            return await telegram.send_message(chat_id, result, message_id)

        if message.get('voice') or message.get('audio'):
            db.bump_stat('audio_requests')
            media = message.get('voice') or message.get('audio')
            data, ct, file_url = await telegram.download_file(media['file_id'])
            mime_type = media.get('mime_type') or ct or 'audio/ogg'
            result = await provider.generate_multimodal(prompt_for_kind('audio', text), 'audio', data, mime_type, file_url=file_url)
            db.add_message(chat_id, 'user', text or '[audio]', 'audio')
            db.add_message(chat_id, 'model', result, 'audio')
            return await telegram.send_message(chat_id, result, message_id)

        if message.get('video'):
            db.bump_stat('video_requests')
            media = message['video']
            data, ct, file_url = await telegram.download_file(media['file_id'])
            mime_type = media.get('mime_type') or ct or 'video/mp4'
            result = await provider.generate_multimodal(prompt_for_kind('video', text), 'video', data, mime_type, file_url=file_url)
            db.add_message(chat_id, 'user', text or '[video]', 'video')
            db.add_message(chat_id, 'model', result, 'video')
            return await telegram.send_message(chat_id, result, message_id)

        if message.get('document'):
            db.bump_stat('document_requests')
            doc = message['document']
            data, ct, file_url = await telegram.download_file(doc['file_id'])
            guessed = doc.get('mime_type') or ct or mimetypes.guess_type(doc.get('file_name', ''))[0] or 'application/octet-stream'
            effective_mode = 'code' if guessed.startswith('text/') else mode
            result = await provider.generate_multimodal(prompt_for_kind('document', text), effective_mode, data, guessed, file_url=file_url)
            db.add_message(chat_id, 'user', text or '[document]', 'document')
            db.add_message(chat_id, 'model', result, 'document')
            return await telegram.send_message(chat_id, result, message_id)

        if message.get('text'):
            effective_mode = 'code' if mode == 'code' else 'text'
            db.bump_stat(f'{effective_mode}_requests')
            result = await provider.generate_text(chat_id, text, effective_mode)
            db.add_message(chat_id, 'user', text, effective_mode)
            db.add_message(chat_id, 'model', result, effective_mode)
            return await telegram.send_message(chat_id, result, message_id)

        await telegram.send_message(chat_id, 'هذا النوع غير مدعوم حالياً في هذا الإصدار.', message_id)
    except Exception as exc:
        logger.exception('Failed to process update')
        db.bump_stat('processing_errors')
        await telegram.send_message(chat_id, f'حدث خطأ أثناء المعالجة: {exc}', message_id)
