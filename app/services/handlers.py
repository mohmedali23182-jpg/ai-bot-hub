import logging
import mimetypes
import traceback
from ..config import settings
from .. import db
from ..providers.factory import get_provider
from . import telegram
from .router import welcome_text, help_text, prompt_for_kind

logger = logging.getLogger(__name__)

async def process_update(update: dict) -> None:
    try:
        await _process_update_safe(update)
    except Exception as exc:
        logger.exception('Critical error in process_update')
        db.bump_stat('critical_errors')
        message = update.get('message') or update.get('edited_message')
        if message:
            chat_id = message['chat']['id']
            await telegram.send_message(chat_id, "⚠️ حدث خطأ تقني غير متوقع. جاري العمل على إصلاحه.")

async def _process_update_safe(update: dict) -> None:
    message = update.get('message') or update.get('edited_message')
    if not message:
        return

    chat_id = int(message['chat']['id'])
    message_id = int(message['message_id'])
    text = (message.get('text') or message.get('caption') or '').strip()
    mode = db.get_mode(chat_id)

    # Command Handling
    if text.startswith('/'):
        cmd_parts = text.split()
        cmd = cmd_parts[0].lower()
        
        mode_map = {
            '/mode_text': 'text',
            '/mode_image': 'image',
            '/mode_audio': 'audio',
            '/mode_video': 'video',
            '/mode_code': 'code',
            '/mode_gen_image': 'gen_image',
            '/mode_gen_video': 'gen_video',
            '/mode_gen_music': 'gen_music',
        }
        
        if cmd == '/start':
            db.bump_stat('cmd_start')
            db.set_mode(chat_id, 'text') # Default to text on start
            return await telegram.send_message(chat_id, welcome_text(), message_id)
            
        if cmd == '/help':
            db.bump_stat('cmd_help')
            return await telegram.send_message(chat_id, help_text(), message_id)
            
        if cmd == '/clear':
            db.clear_history(chat_id)
            return await telegram.send_message(chat_id, '✅ تم مسح سياق المحادثة بنجاح.', message_id)
            
        if cmd == '/status':
            status_msg = (
                f"🤖 *حالة البوت:*\n\n"
                f"🔹 *المزود:* `{settings.AI_PROVIDER}`\n"
                f"🔹 *الوضع الحالي:* `{mode}`\n"
                f"🔹 *العنوان الأساسي:* `{settings.BASE_URL or 'غير محدد'}`\n"
                f"🔹 *الذاكرة:* `{settings.MAX_HISTORY_TURNS}` رسائل"
            )
            return await telegram.send_message(chat_id, status_msg, message_id)
            
        if cmd in mode_map:
            new_mode = mode_map[cmd]
            db.set_mode(chat_id, new_mode)
            db.bump_stat(f"mode_{new_mode}")
            return await telegram.send_message(chat_id, f"🔄 تم التبديل إلى وضع: *{new_mode}*", message_id)

    # Typing Indicator
    if settings.ENABLE_TYPING:
        # Choose action based on mode
        action = 'typing'
        if mode == 'gen_image': action = 'upload_photo'
        elif mode == 'gen_video': action = 'upload_video'
        elif mode == 'gen_music': action = 'upload_voice'
        await telegram.send_chat_action(chat_id, action)

    # Provider Check
    provider = get_provider()
    if not provider:
        return await telegram.send_message(chat_id, '❌ عذراً، لم يتم إعداد مزود الذكاء الاصطناعي بشكل صحيح. يرجى مراجعة الإعدادات.', message_id)

    try:
        # Multimodal & Specialized Handling
        result = None
        media_found = False
        
        # 1. Image Handling
        if message.get('photo'):
            media_found = True
            db.bump_stat('image_requests')
            photo = message['photo'][-1]
            data, content_type, file_url = await telegram.download_file(photo['file_id'])
            # Route to specialized analyze_image
            result = await provider.analyze_image(prompt_for_kind('image', text), data, content_type or 'image/jpeg', file_url=file_url)
            db.add_message(chat_id, 'user', text or '[image]', 'image')
            db.add_message(chat_id, 'model', result, 'image')

        # 2. Audio/Voice Handling
        elif message.get('voice') or message.get('audio'):
            media_found = True
            db.bump_stat('audio_requests')
            media = message.get('voice') or message.get('audio')
            
            if media.get('file_size', 0) > 20 * 1024 * 1024:
                return await telegram.send_message(chat_id, "⚠️ الملف الصوتي كبير جداً. الحد الأقصى هو 20 ميجابايت.", message_id)
                
            data, ct, file_url = await telegram.download_file(media['file_id'])
            mime_type = media.get('mime_type') or ct or 'audio/ogg'
            # Route to specialized analyze_audio
            result = await provider.analyze_audio(prompt_for_kind('audio', text), data, mime_type, file_url=file_url)
            db.add_message(chat_id, 'user', text or '[audio]', 'audio')
            db.add_message(chat_id, 'model', result, 'audio')

        # 3. Video Handling
        elif message.get('video'):
            media_found = True
            db.bump_stat('video_requests')
            media = message['video']
            
            if media.get('file_size', 0) > 20 * 1024 * 1024:
                return await telegram.send_message(chat_id, "⚠️ ملف الفيديو كبير جداً. الحد الأقصى هو 20 ميجابايت.", message_id)
                
            data, ct, file_url = await telegram.download_file(media['file_id'])
            mime_type = media.get('mime_type') or ct or 'video/mp4'
            # Route to specialized analyze_video
            result = await provider.analyze_video(prompt_for_kind('video', text), data, mime_type, file_url=file_url)
            db.add_message(chat_id, 'user', text or '[video]', 'video')
            db.add_message(chat_id, 'model', result, 'video')

        # 4. Document Handling
        elif message.get('document'):
            media_found = True
            db.bump_stat('document_requests')
            doc = message['document']
            
            if doc.get('file_size', 0) > 20 * 1024 * 1024:
                return await telegram.send_message(chat_id, "⚠️ الملف كبير جداً. الحد الأقصى هو 20 ميجابايت.", message_id)
                
            data, ct, file_url = await telegram.download_file(doc['file_id'])
            guessed = doc.get('mime_type') or ct or mimetypes.guess_type(doc.get('file_name', ''))[0] or 'application/octet-stream'
            effective_mode = 'code' if guessed.startswith('text/') or 'code' in guessed or mode == 'code' else 'text'
            
            if effective_mode == 'code':
                result = await provider.generate_code(chat_id, f"Analyze this code file: {text or ''}\nContent follows in multimodal stream.")
            else:
                result = await provider.generate_multimodal(prompt_for_kind('document', text), effective_mode, data, guessed, file_url=file_url)
            
            db.add_message(chat_id, 'user', text or f"[document: {doc.get('file_name', 'file')}]", 'document')
            db.add_message(chat_id, 'model', result, 'document')

        # 5. Text/Code/Generation Handling
        elif text:
            if mode == 'code':
                db.bump_stat('code_requests')
                result = await provider.generate_code(chat_id, text)
                await telegram.send_message(chat_id, result, message_id)
            
            elif mode == 'gen_image':
                db.bump_stat('gen_image_requests')
                result = await provider.generate_image(prompt=text)
                if result.startswith('http'):
                    await telegram.send_photo(chat_id, result, caption=f"🎨 تم توليد الصورة لطلبك: {text[:50]}...", reply_to_message_id=message_id)
                    result = None # Handled
                else:
                    await telegram.send_message(chat_id, result, message_id)
            
            elif mode == 'gen_video':
                db.bump_stat('gen_video_requests')
                result = await provider.generate_video(prompt=text)
                if result.startswith('http'):
                    await telegram.send_video_url(chat_id, result, caption=f"🎬 تم توليد الفيديو لطلبك: {text[:50]}...", reply_to_message_id=message_id)
                    result = None # Handled
                else:
                    await telegram.send_message(chat_id, result, message_id)

            elif mode == 'gen_music':
                db.bump_stat('gen_music_requests')
                result = await provider.generate_music(prompt=text)
                if result.startswith('http'):
                    await telegram.send_audio_url(chat_id, result, caption=f"🎵 تم توليد الموسيقى لطلبك: {text[:50]}...", reply_to_message_id=message_id)
                    result = None # Handled
                else:
                    await telegram.send_message(chat_id, result, message_id)

            else:
                db.bump_stat('text_requests')
                result = await provider.generate_text(chat_id, text, 'text')
                await telegram.send_message(chat_id, result, message_id)
            
            if result:
                db.add_message(chat_id, 'user', text, mode)
                db.add_message(chat_id, 'model', result, mode)
        
        elif not media_found and not text:
            await telegram.send_message(chat_id, '❓ عذراً، لم أفهم طلبك. يمكنك إرسال نص أو صورة أو صوت أو فيديو.', message_id)

    except Exception as exc:
        logger.error('Failed to process message: %s\n%s', exc, traceback.format_exc())
        db.bump_stat('processing_errors')
        
        # User-friendly production-ready error messages
        error_msg = "⚠️ عذراً، واجهت مشكلة أثناء معالجة طلبك."
        exc_str = str(exc).lower()
        if "429" in exc_str:
            error_msg = "⏳ الخدمة مشغولة حالياً بكثرة الطلبات. يرجى المحاولة مرة أخرى بعد قليل."
        elif "503" in exc_str or "504" in exc_str:
            error_msg = "🔌 يبدو أن هناك مشكلة في الاتصال بمزود الذكاء الاصطناعي. جاري المحاولة لاحقاً."
        elif "timeout" in exc_str:
            error_msg = "⏱️ استغرق الطلب وقتاً أطول من المعتاد. يرجى المحاولة مرة أخرى."
        elif "safety" in exc_str or "blocked" in exc_str:
            error_msg = "🛡️ عذراً، تم حجب هذا المحتوى من قبل سياسات الأمان الخاصة بالمزود."
            
        await telegram.send_message(chat_id, error_msg, message_id)
