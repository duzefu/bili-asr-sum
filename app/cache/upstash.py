from __future__ import annotations

import dataclasses
import json

import httpx

from app.cache.base import CachedContent, ContentCache, normalize_url_to_key


class UpstashCache(ContentCache):
    """
    Upstash Redis REST API 缓存实现。

    使用 HTTP REST 接口，无需额外依赖（项目已有 httpx）。
    API 文档：https://upstash.com/docs/redis/features/restapi
    """

    def __init__(self, rest_url: str, rest_token: str) -> None:
        self._url = rest_url.rstrip("/")
        self._client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {rest_token}",
                "Content-Type": "application/json",
            },
            timeout=10.0,
        )

    async def get(self, url: str) -> CachedContent | None:
        key = normalize_url_to_key(url)
        resp = await self._client.get(f"{self._url}/get/{key}")
        resp.raise_for_status()
        raw = resp.json().get("result")
        if raw is None:
            return None
        parsed = json.loads(raw)
        return CachedContent(**parsed)

    async def set(self, url: str, content: CachedContent, ttl: int) -> None:
        key = normalize_url_to_key(url)
        value = json.dumps(dataclasses.asdict(content), ensure_ascii=False)
        endpoint = f"{self._url}/set/{key}"
        params = {"EX": ttl} if ttl > 0 else {}
        resp = await self._client.post(endpoint, content=value, params=params)
        resp.raise_for_status()

    async def close(self) -> None:
        await self._client.aclose()
