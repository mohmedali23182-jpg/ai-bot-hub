from abc import ABC, abstractmethod
from typing import Optional


class AIProvider(ABC):
    @abstractmethod
    async def generate_text(self, chat_id: int, text: str, mode: str) -> str:
        raise NotImplementedError

    @abstractmethod
    async def generate_multimodal(self, prompt: str, mode: str, file_bytes: bytes, mime_type: str, file_url: Optional[str] = None) -> str:
        raise NotImplementedError
