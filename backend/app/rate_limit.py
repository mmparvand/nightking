from __future__ import annotations

import time

import redis
from fastapi import HTTPException, status

from .config import get_settings

_rl_redis = None


def _get_redis():
    global _rl_redis
    if _rl_redis is None:
        _rl_redis = redis.from_url(get_settings().redis_url)
    return _rl_redis


def enforce_rate_limit(key: str, limit: int, window_seconds: int = 60) -> None:
    if limit <= 0:
        return
    r = _get_redis()
    now = int(time.time())
    window_key = f"rl:{key}:{now // window_seconds}"
    count = r.incr(window_key)
    r.expire(window_key, window_seconds)
    if count > limit:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
