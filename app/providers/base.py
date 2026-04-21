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

    # Specialized methods for production-ready routing
    async def analyze_image(self, prompt: str, file_bytes: bytes, mime_type: str, file_url: Optional[str] = None) -> str:
        return await self.generate_multimodal(prompt, "image", file_bytes, mime_type, file_url)

    async def analyze_audio(self, prompt: str, file_bytes: bytes, mime_type: str, file_url: Optional[str] = None) -> str:
        return await self.generate_multimodal(prompt, "audio", file_bytes, mime_type, file_url)

    async def analyze_video(self, prompt: str, file_bytes: bytes, mime_type: str, file_url: Optional[str] = None) -> str:
        return await self.generate_multimodal(prompt, "video", file_bytes, mime_type, file_url)

    async def generate_code(self, chat_id: int, prompt: str) -> str:
        return await self.generate_text(chat_id, prompt, "code")

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
            'text': 'أنت مساعد ذكاء اصطناعي عربي متطور. قدم إجابات دقيقة، مفيدة، ومنظمة بشكل جيد.',
            'image': 'أنت خبير في تحليل الصور والوسائط البصرية. صف العناصر بدقة، استخرج النصوص، وأجب عن التساؤلات المتعلقة بالصورة.',
            'audio': 'أنت خبير في تحليل الصوتيات. قم بتفريغ المحتوى الصوتي، تلخيصه، واستخراج النقاط الرئيسية منه.',
            'video': 'أنت خبير في تحليل الفيديو. صف المشاهد، لخص الأحداث، واستخرج المعلومات النصية أو البصرية الهامة.',
            'code': 'أنت مهندس برمجيات Senior. قدم حلولاً برمجية نظيفة، آمنة، وفعالة مع شرح واضح للمنطق البرمجي.',
        }
        return prompts.get(mode, prompts.get('text', 'أنت مساعد ذكي.'))
