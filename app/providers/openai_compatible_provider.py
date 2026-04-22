import base64
import logging
from typing import Any, Dict, List, Optional
import httpx

from ..config import settings
from .. import db
from .base import AIProvider

logger = logging.getLogger(__name__)


class OpenAICompatibleProvider(AIProvider):
    def __init__(self, base_url: str, is_openrouter: bool = False):
        self.base_url = base_url.rstrip('/')
        self.is_openrouter = is_openrouter

    def _get_headers(self) -> Dict[str, str]:
        api_key = settings.get_ai_api_key()
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        if self.is_openrouter:
            headers['HTTP-Referer'] = settings.OPENROUTER_HTTP_REFERER
            headers['X-Title'] = settings.OPENROUTER_APP_NAME
        return headers

    def _messages(self, chat_id: int, user_text: str, mode: str) -> List[Dict[str, Any]]:
        messages = [{'role': 'system', 'content': self._system_prompt(mode)}]
        
        history = db.get_history(chat_id, settings.MAX_HISTORY_TURNS)
        for row in history:
            role = 'assistant' if row['role'] == 'model' else 'user'
            content = row['text'] or f"[{row['kind']}]"
            messages.append({'role': role, 'content': content})
            
        messages.append({'role': 'user', 'content': user_text})
        return messages

    def _extract_text(self, data: Dict[str, Any]) -> str:
        try:
            choices = data.get('choices', [])
            if not choices:
                error = data.get('error', {})
                if error:
                    msg = error.get('message', 'خطأ غير معروف')
                    logger.error("Provider Error: %s", msg)
                    return f"❌ خطأ من المزود: {msg}"
                return 'لم يصل رد من مزود الذكاء.'
            
            content = choices[0].get('message', {}).get('content', '')
            return content.strip() if content else 'تمت المعالجة لكن لم يصل نص قابل للعرض.'
        except Exception as exc:
            logger.error("Error extracting text: %s", exc)
            return "❌ حدث خطأ أثناء قراءة الرد."

    async def generate_text(self, chat_id: int, text: str, mode: str) -> str:
        payload = {
            'model': self._pick_model(mode),
            'messages': self._messages(chat_id, text, mode),
            'temperature': 0.7,
            'max_tokens': 2048,
        }
        
        url = f'{self.base_url}/chat/completions'
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            resp = await client.post(url, headers=self._get_headers(), json=payload)
            if resp.status_code != 200:
                logger.error("OpenAI-Compatible Error: %d - %s", resp.status_code, resp.text)
            resp.raise_for_status()
            return self._extract_text(resp.json())

    async def generate_multimodal(self, prompt: str, mode: str, file_bytes: bytes, mime_type: str, file_url: Optional[str] = None) -> str:
        model = self._pick_model(mode)
        
        # Build content based on availability of URL or bytes
        content = [{'type': 'text', 'text': prompt or self._system_prompt(mode)}]
        
        if mode == 'image':
            if settings.OPENAI_COMPAT_VISION_INPUT_MODE == 'url' and file_url:
                content.append({'type': 'image_url', 'image_url': {'url': file_url}})
            else:
                b64_data = base64.b64encode(file_bytes).decode('utf-8')
                content.append({'type': 'image_url', 'image_url': {'url': f'data:{mime_type};base64,{b64_data}'}})
        else:
            # Fallback for non-image multimodal
            content.append({'type': 'text', 'text': f'\n[ملاحظة: هذا الملف من نوع {mime_type} وقد لا يدعمه المزود الحالي بالكامل.]'})

        payload = {
            'model': model,
            'messages': [
                {'role': 'system', 'content': self._system_prompt(mode)},
                {'role': 'user', 'content': content}
            ],
            'temperature': 0.5,
            'max_tokens': 2048,
        }
        
        url = f'{self.base_url}/chat/completions'
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            resp = await client.post(url, headers=self._get_headers(), json=payload)
            if resp.status_code != 200:
                logger.error("OpenAI-Compatible Multimodal Error: %d - %s", resp.status_code, resp.text)
            resp.raise_for_status()
            return self._extract_text(resp.json())

    async def generate_image(self, prompt: str) -> str:
        payload = {
            'model': settings.AI_MODEL_GEN_IMAGE,
            'prompt': prompt,
            'n': 1,
            'size': '1024x1024'
        }
        
        # Note: OpenRouter often handles image generation via chat/completions with specific models
        # or via a standard /images/generations endpoint if supported by the underlying provider.
        url = f'{self.base_url}/images/generations'
        
        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
                resp = await client.post(url, headers=self._get_headers(), json=payload)
                if resp.status_code != 200:
                    # Fallback for OpenRouter chat-based image generation if standard endpoint fails
                    if self.is_openrouter:
                        logger.info("Retrying image generation via chat endpoint for OpenRouter")
                        return await self._generate_media_via_chat(prompt, settings.AI_MODEL_GEN_IMAGE)
                    
                    logger.error("Image Gen Error: %d - %s", resp.status_code, resp.text)
                    resp.raise_for_status()
                
                data = resp.json()
                return data.get('data', [])[0].get('url', '❌ لم يتم العثور على رابط للصورة.')
        except Exception as exc:
            logger.error("Error generating image: %s", exc)
            if self.is_openrouter:
                return await self._generate_media_via_chat(prompt, settings.AI_MODEL_GEN_IMAGE)
            return f"❌ حدث خطأ أثناء توليد الصورة: {str(exc)}"

    async def generate_video(self, prompt: str) -> str:
        # Video generation is highly provider-specific. Using chat fallback for OpenRouter
        if self.is_openrouter:
            return await self._generate_media_via_chat(prompt, settings.AI_MODEL_GEN_VIDEO)
        return "⏳ ميزة توليد الفيديو غير مدعومة مباشرة عبر هذا المزود حالياً."

    async def generate_music(self, prompt: str) -> str:
        if self.is_openrouter:
            return await self._generate_media_via_chat(prompt, settings.AI_MODEL_GEN_MUSIC)
        return "⏳ ميزة توليد الموسيقى غير مدعومة مباشرة عبر هذا المزود حالياً."

    async def _generate_media_via_chat(self, prompt: str, model: str) -> str:
        """Helper for providers like OpenRouter that return media URLs in chat responses."""
        payload = {
            'model': model,
            'messages': [{'role': 'user', 'content': prompt}],
        }
        url = f'{self.base_url}/chat/completions'
        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
                resp = await client.post(url, headers=self._get_headers(), json=payload)
                resp.raise_for_status()
                result = self._extract_text(resp.json())
                # Many models return Markdown like ![image](url), we try to extract the URL
                import re
                urls = re.findall(r'https?://\S+', result)
                if urls:
                    # Clean potential markdown wrapping
                    clean_url = urls[0].split(')')[0].split('"')[0].split("'")[0]
                    return clean_url
                return result
        except Exception as exc:
            logger.error("Media chat fallback failed: %s", exc)
            return f"❌ فشل توليد الوسائط: {str(exc)}"
