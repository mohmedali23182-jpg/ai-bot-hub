import asyncio
import logging
from typing import Awaitable, Callable, TypeVar

T = TypeVar('T')
logger = logging.getLogger(__name__)


async def retry_async(fn: Callable[[], Awaitable[T]], retries: int = 2, delay: float = 1.0) -> T:
    last_exc = None
    for attempt in range(retries + 1):
        try:
            return await fn()
        except Exception as exc:
            last_exc = exc
            if attempt >= retries:
                break
            await asyncio.sleep(delay * (attempt + 1))
            logger.warning('Retrying after failure: %s', exc)
    raise last_exc  # type: ignore[misc]


def chunk_text(text: str, max_len: int) -> list[str]:
    text = text or ''
    if len(text) <= max_len:
        return [text]
    chunks = []
    current = []
    current_len = 0
    for line in text.splitlines(True):
        if current_len + len(line) > max_len and current:
            chunks.append(''.join(current))
            current = [line]
            current_len = len(line)
        else:
            current.append(line)
            current_len += len(line)
    if current:
        chunks.append(''.join(current))
    return chunks
