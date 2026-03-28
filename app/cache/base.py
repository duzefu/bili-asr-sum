from __future__ import annotations

import hashlib
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse


@dataclass
class CachedContent:
    title: str
    summary: str
    transcript_source: str          # "subtitle" | "asr"
    transcript: str | None          # 可选，受 CACHE_STORE_TRANSCRIPT 控制
    cached_at: str                  # ISO 8601 UTC


def normalize_url_to_key(url: str) -> str:
    """将视频 URL 规范化为缓存 key，同一视频的不同 URL 变体映射到同一 key。"""
    # Bilibili BV 号
    if m := re.search(r"BV([A-Za-z0-9]+)", url):
        return f"bilisum:content:bili:BV{m.group(1)}"
    # Bilibili av 号
    if m := re.search(r"[?/&]av(\d+)", url, re.IGNORECASE):
        return f"bilisum:content:bili:av{m.group(1)}"
    if m := re.search(r"/video/av(\d+)", url, re.IGNORECASE):
        return f"bilisum:content:bili:av{m.group(1)}"
    # YouTube 标准链接 watch?v=
    parsed = urlparse(url)
    if "youtube.com" in parsed.netloc:
        qs = parse_qs(parsed.query)
        if vid_list := qs.get("v"):
            return f"bilisum:content:yt:{vid_list[0]}"
    # YouTube 短链 youtu.be/<id>
    if "youtu.be" in parsed.netloc:
        vid = parsed.path.strip("/").split("/")[0]
        if vid:
            return f"bilisum:content:yt:{vid}"
    # 兜底：URL hash
    h = hashlib.sha256(url.strip().lower().encode()).hexdigest()[:16]
    return f"bilisum:content:url:{h}"


class ContentCache(ABC):
    @abstractmethod
    async def get(self, url: str) -> CachedContent | None:
        """按 URL 查找缓存，未命中返回 None。"""
        ...

    @abstractmethod
    async def set(self, url: str, content: CachedContent, ttl: int) -> None:
        """写入缓存，ttl 单位为秒，0 表示不设过期。"""
        ...

    @abstractmethod
    async def close(self) -> None:
        """释放资源（连接池等）。"""
        ...
