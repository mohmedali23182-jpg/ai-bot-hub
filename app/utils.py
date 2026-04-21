import asyncio
import logging
import random
from typing import Awaitable, Callable, TypeVar, Optional, List

T = TypeVar('T')
logger = logging.getLogger(__name__)


async def retry_async(
    fn: Callable[[], Awaitable[T]], 
    retries: int = 3, 
    initial_delay: float = 1.0,
    max_delay: float = 10.0,
    backoff_factor: float = 2.0,
    jitter: bool = True
) -> T:
    """
    Retries an async function with exponential backoff.
    """
    last_exc = None
    delay = initial_delay
    
    for attempt in range(retries + 1):
        try:
            return await fn()
        except Exception as exc:
            last_exc = exc
            if attempt >= retries:
                break
            
            # Calculate next delay with backoff
            current_delay = delay
            if jitter:
                current_delay *= (0.5 + random.random())
            
            logger.warning(
                'Attempt %d/%d failed: %s. Retrying in %.2fs...', 
                attempt + 1, retries + 1, exc, current_delay
            )
            
            await asyncio.sleep(current_delay)
            
            # Update delay for next time
            delay = min(delay * backoff_factor, max_delay)
            
    if last_exc:
        raise last_exc
    raise RuntimeError("Retry loop finished without result or exception")


def chunk_text(text: str, max_len: int) -> List[str]:
    """
    Smartly chunks text by lines or characters if a single line is too long.
    """
    if not text:
        return [" "]
        
    if len(text) <= max_len:
        return [text]
        
    chunks = []
    current_chunk = []
    current_len = 0
    
    for line in text.splitlines(keepends=True):
        # If a single line is longer than max_len, we must split it by characters
        if len(line) > max_len:
            # First, flush current chunk
            if current_chunk:
                chunks.append("".join(current_chunk))
                current_chunk = []
                current_len = 0
            
            # Then split the long line
            for i in range(0, len(line), max_len):
                chunks.append(line[i:i+max_len])
            continue

        if current_len + len(line) > max_len:
            chunks.append("".join(current_chunk))
            current_chunk = [line]
            current_len = len(line)
        else:
            current_chunk.append(line)
            current_len += len(line)
            
    if current_chunk:
        chunks.append("".join(current_chunk))
        
    return chunks or [" "]
