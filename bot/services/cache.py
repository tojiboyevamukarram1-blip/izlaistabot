import asyncio
import json
import logging
import time
from typing import Any, Dict, Optional
import redis.asyncio as aioredis

from bot.config import settings

logger = logging.getLogger(__name__)


class MemoryCache:
    """In-memory cache fallback when Redis is not available."""

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._expires: Dict[str, float] = {}
        self._rate_limits: Dict[str, list] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[str]:
        async with self._lock:
            now = time.time()
            if key in self._expires and self._expires[key] < now:
                self._data.pop(key, None)
                self._expires.pop(key, None)
                return None
            return self._data.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        async with self._lock:
            self._data[key] = value
            if ex:
                self._expires[key] = time.time() + ex
            elif key in self._expires:
                del self._expires[key]
            return True

    async def check_rate_limit(self, user_id: int, max_requests: int, window: int) -> bool:
        """Sliding window in-memory rate limiter."""
        async with self._lock:
            now = time.time()
            key = f"rate:{user_id}"
            timestamps = self._rate_limits.get(key, [])
            # filter out timestamps older than window
            valid_timestamps = [t for t in timestamps if now - t < window]
            if len(valid_timestamps) >= max_requests:
                self._rate_limits[key] = valid_timestamps
                return False  # rate limit exceeded
            valid_timestamps.append(now)
            self._rate_limits[key] = valid_timestamps
            return True


class CacheService:
    """Unified cache service with Redis and fallback to MemoryCache."""

    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self.memory: MemoryCache = MemoryCache()
        self.use_redis: bool = False

    async def connect(self) -> None:
        """Attempt connection to Redis, fallback gracefully if unavailable."""
        if not settings.redis_url:
            logger.info("No Redis URL configured, using in-memory cache.")
            return

        try:
            client = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2.0,
            )
            await client.ping()
            self.redis = client
            self.use_redis = True
            logger.info(f"Connected to Redis at {settings.redis_url}")
        except Exception as e:
            logger.warning(f"Could not connect to Redis ({e}). Falling back to in-memory cache.")
            self.use_redis = False
            self.redis = None

    async def close(self) -> None:
        """Close connections on shutdown."""
        if self.redis:
            try:
                await self.redis.aclose()
            except Exception:
                pass

    @property
    def status_string(self) -> str:
        return "Redis (Tashqi)" if self.use_redis else "Xotira (In-Memory)"

    async def get(self, key: str) -> Optional[str]:
        if self.use_redis and self.redis:
            try:
                return await self.redis.get(key)
            except Exception as e:
                logger.debug(f"Redis get error: {e}")
        return await self.memory.get(key)

    async def set(self, key: str, value: str, ttl: int = 3600) -> None:
        if self.use_redis and self.redis:
            try:
                await self.redis.set(key, value, ex=ttl)
                return
            except Exception as e:
                logger.debug(f"Redis set error: {e}")
        await self.memory.set(key, value, ex=ttl)

    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        raw = await self.get(key)
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                return None
        return None

    async def set_json(self, key: str, value: Dict[str, Any], ttl: int = 3600) -> None:
        try:
            raw = json.dumps(value)
            await self.set(key, raw, ttl=ttl)
        except Exception as e:
            logger.error(f"Failed to serialize JSON for cache: {e}")

    async def check_rate_limit(self, user_id: int, max_requests: int, window: int) -> bool:
        """Checks rate limit for user. Returns True if allowed, False if exceeded."""
        if self.use_redis and self.redis:
            try:
                key = f"rate:{user_id}"
                current = await self.redis.incr(key)
                if current == 1:
                    await self.redis.expire(key, window)
                return current <= max_requests
            except Exception as e:
                logger.debug(f"Redis rate limit error: {e}, falling back to memory")

        return await self.memory.check_rate_limit(user_id, max_requests, window)

    # Telegram file_id caching
    async def get_cached_file_id(self, cache_key: str, format_id: str) -> Optional[Dict[str, str]]:
        key = f"file_id:{cache_key}:{format_id}"
        return await self.get_json(key)

    async def set_cached_file_id(
        self,
        cache_key: str,
        format_id: str,
        file_id: str,
        media_type: str,
        ttl: int = 7 * 86400,
    ) -> None:
        key = f"file_id:{cache_key}:{format_id}"
        payload = {"file_id": file_id, "media_type": media_type}
        await self.set_json(key, payload, ttl=ttl)


cache_service = CacheService()
