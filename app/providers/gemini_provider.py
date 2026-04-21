import base64
import logging
from typing import Any, Dict, List, Optional
import httpx

from ..config import settings
from .. import db
from .base import AIProvider

logger = logging.getLogger(__name__)


class GeminiProvider(AIProvider):
    def _extract_text(self, data: Dict[str, Any]) -> str:
        candidates = data.get('candidates', [])
        if not candidates:
            # Check for error in response
            error = data.get('error', {})
            if error:
                msg = error.get('message', 'خطأ غير معروف')
                logger.error("Gemini API Error: %s", msg)
                return f"❌ خطأ من جوجل: {msg}"
            
            # Check for safety ratings or other reasons for no candidates
            if 'promptFeedback' in data:
                reason = data['promptFeedback'].get('blockReason', 'Unknown')
                return f"⚠️ تم حجب الرد من قبل المزود (السبب: {reason})."
                
            return 'لم يصل رد من مزود الذكاء.'
            
        parts = candidates[0].get('content', {}).get('parts', [])
        texts = [p.get('text', '') for p in parts if p.get('text')]
        return '\n'.join(texts).strip() if texts else 'تمت المعالجة لكن لم يصل نص قابل للعرض.'

    def _history(self, chat_id: int) -> List[Dict[str, Any]]:
        contents = []
        for row in db.get_history(chat_id, settings.MAX_HISTORY_TURNS):
            role = 'model' if row['role'] == 'model' else 'user'
            text = row['text'] or f"[{row['kind']}]"
            contents.append({'role': role, 'parts': [{'text': text}]})
        return contents

    async def generate_text(self, chat_id: int, text: str, mode: str) -> str:
        payload = {
            'system_instruction': {'parts': [{'text': self._system_prompt(mode)}]},
            'contents': self._history(chat_id) + [{'role': 'user', 'parts': [{'text': text}]}],
            'generationConfig': {
                'temperature': 0.7, 
                'topP': 0.9, 
                'maxOutputTokens': 2048
            },
        }
        
        api_key = settings.get_ai_api_key()
        headers = {'x-goog-api-key': api_key, 'Content-Type': 'application/json'}
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{self._pick_model(mode)}:generateContent'
        
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                logger.error("Gemini Error: %d - %s", resp.status_code, resp.text)
            resp.raise_for_status()
            return self._extract_text(resp.json())

    async def generate_multimodal(self, prompt: str, mode: str, file_bytes: bytes, mime_type: str, file_url: Optional[str] = None) -> str:
        if len(file_bytes) > settings.GEMINI_MAX_INLINE_BYTES:
            raise ValueError(f'الملف كبير جداً ({len(file_bytes) // 1024 // 1024}MB). الحد الأقصى هو {settings.GEMINI_MAX_INLINE_BYTES // 1024 // 1024}MB.')

        payload = {
            'system_instruction': {'parts': [{'text': self._system_prompt(mode)}]},
            'contents': [{
                'role': 'user',
                'parts': [
                    {'inline_data': {'mime_type': mime_type, 'data': base64.b64encode(file_bytes).decode('utf-8')}},
                    {'text': prompt or self._system_prompt(mode)},
                ]
            }],
            'generationConfig': {
                'temperature': 0.5, 
                'topP': 0.9, 
                'maxOutputTokens': 2048
            },
        }
        
        api_key = settings.get_ai_api_key()
        headers = {'x-goog-api-key': api_key, 'Content-Type': 'application/json'}
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{self._pick_model(mode)}:generateContent'
        
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                logger.error("Gemini Multimodal Error: %d - %s", resp.status_code, resp.text)
            resp.raise_for_status()
            return self._extract_text(resp.json())

    # Production specialized methods
    async def analyze_image(self, prompt: str, file_bytes: bytes, mime_type: str, file_url: Optional[str] = None) -> str:
        return await self.generate_multimodal(prompt, "image", file_bytes, mime_type, file_url)

    async def analyze_audio(self, prompt: str, file_bytes: bytes, mime_type: str, file_url: Optional[str] = None) -> str:
        return await self.generate_multimodal(prompt, "audio", file_bytes, mime_type, file_url)

    async def analyze_video(self, prompt: str, file_bytes: bytes, mime_type: str, file_url: Optional[str] = None) -> str:
        return await self.generate_multimodal(prompt, "video", file_bytes, mime_type, file_url)
