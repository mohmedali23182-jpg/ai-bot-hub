import base64
from typing import Any, Dict, List, Optional
import httpx

from ..config import settings
from .. import db
from .base import AIProvider


class OpenAICompatibleProvider(AIProvider):
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
            'image': 'أنت خبير تحليل صور. استخرج النصوص والعناصر المهمة بدقة.',
            'audio': 'أنت خبير تحليل صوت. لخّص المحتوى واستخرج أهم النقاط.',
            'video': 'أنت خبير تحليل فيديو. لخّص المشاهد والمحتوى الظاهر.',
            'code': 'أنت مهندس برمجيات خبير. أعط حلولاً قوية وآمنة وقابلة للتوسعة.',
        }
        return prompts.get(mode, prompts['text'])

    def _messages(self, chat_id: int, user_text: str, mode: str) -> List[Dict[str, Any]]:
        msgs: List[Dict[str, Any]] = [{'role': 'system', 'content': self._system_prompt(mode)}]
        for row in db.get_history(chat_id, settings.MAX_HISTORY_TURNS):
            if row['text']:
                role = 'assistant' if row['role'] == 'model' else 'user'
                msgs.append({'role': role, 'content': row['text']})
        msgs.append({'role': 'user', 'content': user_text})
        return msgs

    async def generate_text(self, chat_id: int, text: str, mode: str) -> str:
        payload = {
            'model': self._pick_model(mode),
            'messages': self._messages(chat_id, text, mode),
            'temperature': 0.5,
        }
        headers = {'Authorization': f'Bearer {settings.AI_API_KEY}', 'Content-Type': 'application/json'}
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            resp = await client.post(f"{settings.OPENAI_COMPAT_BASE_URL.rstrip('/')}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data['choices'][0]['message']['content']

    async def generate_multimodal(self, prompt: str, mode: str, file_bytes: bytes, mime_type: str, file_url: Optional[str] = None) -> str:
        headers = {'Authorization': f'Bearer {settings.AI_API_KEY}', 'Content-Type': 'application/json'}

        if mode == 'image' and file_url and settings.OPENAI_COMPAT_VISION_INPUT_MODE == 'url':
            content: List[Dict[str, Any]] = [
                {'type': 'text', 'text': prompt},
                {'type': 'image_url', 'image_url': {'url': file_url}},
            ]
        else:
            short_note = 'المدخل متعدد الوسائط في هذا المزود مضبوط بوضع مرن. إن لم يدعم الملف مباشرة، سيُعالج كنص أو وصف مبدئي.'
            content = [{'type': 'text', 'text': f'{prompt}\n\n{short_note}'}]

        payload = {
            'model': self._pick_model(mode),
            'messages': [
                {'role': 'system', 'content': self._system_prompt(mode)},
                {'role': 'user', 'content': content},
            ],
            'temperature': 0.4,
        }
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            resp = await client.post(f"{settings.OPENAI_COMPAT_BASE_URL.rstrip('/')}/chat/completions", headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data['choices'][0]['message']['content']
