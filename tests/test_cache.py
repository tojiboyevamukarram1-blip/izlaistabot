import asyncio
import pytest
from bot.services.cache import CacheService, MemoryCache


@pytest.mark.asyncio
async def test_memory_cache_get_set():
    cache = MemoryCache()
    await cache.set("key1", "val1", ex=60)
    assert await cache.get("key1") == "val1"
    assert await cache.get("nonexistent") is None


@pytest.mark.asyncio
async def test_memory_cache_expiration():
    cache = MemoryCache()
    await cache.set("temp_key", "temporary", ex=1)
    assert await cache.get("temp_key") == "temporary"
    await asyncio.sleep(1.1)
    assert await cache.get("temp_key") is None


@pytest.mark.asyncio
async def test_rate_limiting_sliding_window():
    cache = MemoryCache()
    user_id = 12345
    max_reqs = 3
    window = 2

    # First 3 should pass
    assert await cache.check_rate_limit(user_id, max_reqs, window) is True
    assert await cache.check_rate_limit(user_id, max_reqs, window) is True
    assert await cache.check_rate_limit(user_id, max_reqs, window) is True

    # 4th should be blocked
    assert await cache.check_rate_limit(user_id, max_reqs, window) is False

    # Wait for window to expire
    await asyncio.sleep(2.1)
    # Should be allowed again
    assert await cache.check_rate_limit(user_id, max_reqs, window) is True


@pytest.mark.asyncio
async def test_cache_service_json_and_file_id():
    service = CacheService()
    # By default, use memory fallback
    meta_data = {"title": "Test Title", "duration": 180}
    await service.set_json("test_meta_key", meta_data, ttl=60)

    retrieved = await service.get_json("test_meta_key")
    assert retrieved == meta_data

    # File ID caching
    await service.set_cached_file_id("cache123", "v_0", "telegram_file_id_xyz", "video")
    cached_file = await service.get_cached_file_id("cache123", "v_0")
    assert cached_file is not None
    assert cached_file["file_id"] == "telegram_file_id_xyz"
    assert cached_file["media_type"] == "video"
