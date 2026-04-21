from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any


class AIProvider(ABC):
    @abstractmethod
    async def generate_text(self, chat_id: int, text: str, mode: str) -> str:
        """
        Generates text based on chat history and current user input.
        """
        raise NotImplementedError

    @abstractmethod
    async def generate_multimodal(
        self, 
        prompt: str, 
        mode: str, 
        file_bytes: bytes, 
        mime_type: str, 
        file_url: Optional[str] = None
    ) -> str:
        """
        Generates content from multimodal input (images, audio, video, docs).
        """
        raise NotImplementedError

    def _pick_model(self, mode: str) -> str:
        """
        Helper to pick the correct model name from settings based on mode.
        """
        from ..config import settings
        return {
            'text': settings.AI_MODEL_TEXT,
            'image': settings.AI_MODEL_VISION,
            'audio': settings.AI_MODEL_AUDIO,
            'video': settings.AI_MODEL_VIDEO,
            'code': settings.AI_MODEL_CODE,
        }.get(mode, settings.AI_MODEL_TEXT)

    def _system_prompt(self, mode: str) -> str:
        """
        Helper to provide consistent system prompts across providers.
        """
        prompts = {
            'text': 'أنت مساعد عربي احترافي. كن واضحا ودقيقا ومنظما.',
            'image': 'أنت خبير تحليل صور. استخرج النصوص ووصف العناصر بدقة دون تخمين.',
            'audio': 'أنت خبير صوت. فرّغ المحتوى إن أمكن ثم لخّصه واستخرج أهم النقاط.',
            'video': 'أنت خبير فيديو. لخّص المشاهد والمحتوى النصي الظاهر.',
            'code': 'أنت مهندس برمجيات خبير. أعط حلولاً قوية وآمنة وقابلة للتوسعة.',
        }
        return prompts.get(mode, prompts['text'])
