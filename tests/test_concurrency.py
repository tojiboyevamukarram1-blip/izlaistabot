import asyncio
import pytest
from bot.config import settings
from bot.downloader.manager import DownloadManager


@pytest.mark.asyncio
async def test_download_manager_bounded_concurrency():
    """Ensure download manager respects max_concurrent_downloads."""
    manager = DownloadManager()
    peak_active = 0
    completed = 0
    total_tasks = 10

    async def mock_worker():
        nonlocal peak_active, completed
        async with manager.semaphore:
            async with manager._lock:
                manager.active_count += 1
                if manager.active_count > peak_active:
                    peak_active = manager.active_count

            # Simulate download task
            await asyncio.sleep(0.05)

            async with manager._lock:
                manager.active_count -= 1
                completed += 1

    await asyncio.gather(*[mock_worker() for _ in range(total_tasks)])

    assert completed == total_tasks
    assert peak_active <= settings.max_concurrent_downloads
    assert await manager.get_active_downloads() == 0
