from __future__ import annotations

from app.cache.base import CachedContent, ContentCache

# 全局缓存单例，在 app lifespan 中由 get_content_cache() 初始化
content_cache: ContentCache | None = None


def get_content_cache(config) -> ContentCache:
    """根据配置构造缓存后端实例。"""
    if config.cache_backend == "upstash":
        if not config.upstash_redis_rest_url or not config.upstash_redis_rest_token:
            raise ValueError(
                "CACHE_BACKEND=upstash 需要同时设置 "
                "UPSTASH_REDIS_REST_URL 和 UPSTASH_REDIS_REST_TOKEN"
            )
        from app.cache.upstash import UpstashCache
        return UpstashCache(
            config.upstash_redis_rest_url,
            config.upstash_redis_rest_token,
        )
    from app.cache.memory import MemoryCache
    return MemoryCache()


__all__ = ["CachedContent", "ContentCache", "content_cache", "get_content_cache"]
