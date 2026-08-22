"""A tiny JSON TTL cache with a Redis backend and an in-process fallback.

Used to avoid re-fetching slow, rate-limited third-party responses (Discogs
release + price-suggestion payloads) across hunts. When REDIS_URL is set the
cache is shared across replicas and survives restarts; otherwise it's a simple
per-process dict with expiry — fine for local dev.
"""
from __future__ import annotations

import json
import time
from typing import Any, Optional

from app.core.config import settings

_PREFIX = "cache:"


class _MemoryCache:
    def __init__(self) -> None:
        self._data: dict[str, tuple[float, str]] = {}

    def get(self, key: str) -> Optional[str]:
        entry = self._data.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if expires_at < time.time():
            self._data.pop(key, None)
            return None
        return value

    def set(self, key: str, value: str, ttl: int) -> None:
        self._data[key] = (time.time() + ttl, value)


class _RedisCache:
    def __init__(self, client) -> None:
        self._redis = client

    def get(self, key: str) -> Optional[str]:
        try:
            raw = self._redis.get(_PREFIX + key)
        except Exception:
            return None
        if raw is None:
            return None
        return raw.decode() if isinstance(raw, bytes) else raw

    def set(self, key: str, value: str, ttl: int) -> None:
        try:
            self._redis.set(_PREFIX + key, value, ex=ttl)
        except Exception:
            pass


_cache = None


def _backend():
    global _cache
    if _cache is not None:
        return _cache
    if settings.redis_url:
        try:
            import redis

            _cache = _RedisCache(redis.Redis.from_url(settings.redis_url))
            return _cache
        except Exception:
            pass
    _cache = _MemoryCache()
    return _cache


def cache_get_json(key: str) -> Any | None:
    raw = _backend().get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def cache_set_json(key: str, value: Any, ttl: int) -> None:
    try:
        _backend().set(key, json.dumps(value), ttl)
    except (TypeError, ValueError):
        pass
