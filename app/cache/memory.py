from __future__ import annotations

import asyncio

from app.cache.base import CachedContent, ContentCache, normalize_url_to_key


class MemoryCache(ContentCache):
    """进程内内存缓存，服务重启后清空，忽略 TTL。"""

    def __init__(self) -> None:
        self._store: dict[str, CachedContent] = {}
        self._lock = asyncio.Lock()

    async def get(self, url: str) -> CachedContent | None:
        key = normalize_url_to_key(url)
        async with self._lock:
            return self._store.get(key)

    async def set(self, url: str, content: CachedContent, ttl: int) -> None:
        key = normalize_url_to_key(url)
        async with self._lock:
            self._store[key] = content

    async def close(self) -> None:
        pass
