import base64
from typing import Any, Dict, List, Optional
import httpx

from ..config import settings
from .. import db
from .base import AIProvider


class GeminiProvider(AIProvider):
    def _pick_model(self, mode: str) -> str:
        return {
            'text': settings.AI_MODEL_TEXT,
            'image': settings.AI_MODEL_VISION,
            'audio': settings.AI_MODEL_AUDIO,
            'video': settings.AI_MODEL_VIDEO,
            'code': settings.AI_MODEL_CODE,
        }.get(mode, settings.AI_MODEL_TEXT)

    def _system_prompt(self, mode: str) -> str:
        prompts = {
            'text': 'أنت مساعد عربي احترافي. كن واضحا ودقيقا ومنظما.',
            'image': 'أنت خبير تحليل صور. استخرج النصوص ووصف العناصر بدقة دون تخمين.',
            'audio': 'أنت خبير صوت. فرّغ المحتوى إن أمكن ثم لخّصه واستخرج أهم النقاط.',
            'video': 'أنت خبير فيديو. لخّص المشاهد والمحتوى النصي الظاهر.',
            'code': 'أنت مهندس برمجيات خبير. أعط حلولاً قوية وآمنة وقابلة للتوسعة.',
        }
        return prompts.get(mode, prompts['text'])

    def _extract_text(self, data: Dict[str, Any]) -> str:
        candidates = data.get('candidates', [])
        if not candidates:
            return 'لم يصل رد من مزود الذكاء.'
        parts = candidates[0].get('content', {}).get('parts', [])
        texts = [p.get('text', '') for p in parts if p.get('text')]
        return '\n'.join(texts).strip() if texts else 'تمت المعالجة لكن لم يصل نص قابل للعرض.'

    def _history(self, chat_id: int) -> List[Dict[str, Any]]:
        contents = []
        for row in db.get_history(chat_id, settings.MAX_HISTORY_TURNS):
            if row['text']:
                contents.append({'role': row['role'], 'parts': [{'text': row['text']}]})
        return contents

    async def generate_text(self, chat_id: int, text: str, mode: str) -> str:
        payload = {
            'system_instruction': {'parts': [{'text': self._system_prompt(mode)}]},
            'contents': self._history(chat_id) + [{'role': 'user', 'parts': [{'text': text}]}],
            'generationConfig': {'temperature': 0.5, 'topP': 0.9, 'maxOutputTokens': 2048},
        }
        headers = {'x-goog-api-key': settings.AI_API_KEY, 'Content-Type': 'application/json'}
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{self._pick_model(mode)}:generateContent'
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return self._extract_text(resp.json())

    async def generate_multimodal(self, prompt: str, mode: str, file_bytes: bytes, mime_type: str, file_url: Optional[str] = None) -> str:
        if len(file_bytes) > settings.GEMINI_MAX_INLINE_BYTES:
            raise ValueError('الملف أكبر من الحد المسموح للمعالجة المباشرة في هذا الإصدار.')

        payload = {
            'system_instruction': {'parts': [{'text': self._system_prompt(mode)}]},
            'contents': [{
                'role': 'user',
                'parts': [
                    {'inline_data': {'mime_type': mime_type, 'data': base64.b64encode(file_bytes).decode('utf-8')}},
                    {'text': prompt},
                ]
            }],
            'generationConfig': {'temperature': 0.4, 'topP': 0.9, 'maxOutputTokens': 2048},
        }
        headers = {'x-goog-api-key': settings.AI_API_KEY, 'Content-Type': 'application/json'}
        url = f'https://generativelanguage.googleapis.com/v1beta/models/{self._pick_model(mode)}:generateContent'
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return self._extract_text(resp.json())
