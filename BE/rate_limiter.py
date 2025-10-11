import time
import asyncio
from fastapi import HTTPException
from .config import settings

# Simple in-memory token-bucket rate limiter per client (IP or session-id)
_tokens = {}
_last = {}
_lock = asyncio.Lock()

async def allow_request(key: str) -> bool:
    """Return True if allowed. Single-process only.
    key can be client IP or session id.
    """
    async with _lock:
        now = time.monotonic()
        tokens = _tokens.get(key, settings.RATE_LIMIT_TOKENS)
        last = _last.get(key, now)

        # refill
        elapsed = now - last
        refill = (elapsed / settings.RATE_LIMIT_REFILL_SECONDS) * settings.RATE_LIMIT_TOKENS
        tokens = min(settings.RATE_LIMIT_TOKENS, tokens + refill)
        _last[key] = now

        if tokens >= 1:
            _tokens[key] = tokens - 1
            return True
        else:
            _tokens[key] = tokens
            return False

async def check_rate_limit_dependency(key: str):
    allowed = await allow_request(key)
    if not allowed:
        raise HTTPException(status_code=429, detail="Too many requests")