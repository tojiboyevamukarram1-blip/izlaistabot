import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple
import aiohttp
import yt_dlp

from bot.config import settings
from bot.downloader.ffmpeg_utils import (
    compress_video_to_size,
    convert_to_mp3,
    ensure_compatible_mp4,
    remux_mp4_faststart,
)
from bot.security.sanitizer import sanitize_filename

logger = logging.getLogger(__name__)


class FileOversizedError(Exception):
    def __init__(self, size_bytes: int, limit_bytes: int):
        self.size_bytes = size_bytes
        self.limit_bytes = limit_bytes
        super().__init__(f"File size {size_bytes} exceeds limit {limit_bytes}")


class DownloadManager:
    """Manages concurrent downloads, progress reporting, and format conversions."""

    def __init__(self):
        self.semaphore = asyncio.Semaphore(settings.max_concurrent_downloads)
        self.active_count = 0
        self._lock = asyncio.Lock()

    async def get_active_downloads(self) -> int:
        async with self._lock:
            return self.active_count

    async def download_media(
        self,
        url: str,
        format_id: str,
        output_dir: Path,
        title: str,
        author: Optional[str] = None,
        is_audio: bool = False,
        is_mp3: bool = False,
        progress_callback: Optional[Callable[[float, str, str], Any]] = None,
    ) -> Path:
        """
        Downloads media with bounded concurrency and progress reporting.
        Returns the Path to the final processed file.
        """
        async with self.semaphore:
            async with self._lock:
                self.active_count += 1
            try:
                return await self._execute_download(
                    url=url,
                    format_id=format_id,
                    output_dir=output_dir,
                    title=title,
                    author=author,
                    is_audio=is_audio,
                    is_mp3=is_mp3,
                    progress_callback=progress_callback,
                )
            finally:
                async with self._lock:
                    self.active_count = max(0, self.active_count - 1)

    async def _execute_download(
        self,
        url: str,
        format_id: str,
        output_dir: Path,
        title: str,
        author: Optional[str] = None,
        is_audio: bool = False,
        is_mp3: bool = False,
        progress_callback: Optional[Callable[[float, str, str], Any]] = None,
    ) -> Path:
        clean_title = sanitize_filename(title, max_length=60, default="media")
        outtmpl = str(output_dir / f"{clean_title}.%(ext)s")

        last_update_time = [0.0]
        last_percent = [0.0]
        loop = asyncio.get_running_loop()

        def sync_hook(d: Dict[str, Any]):
            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes") or 0

                # Check on-the-fly size limit (allow headroom up to 6x for auto-compression)
                if downloaded > settings.max_file_size_bytes * 6:
                    raise FileOversizedError(downloaded, settings.max_file_size_bytes)

                percent = (downloaded / total * 100) if total > 0 else 0.0
                now = time.time()

                # Throttle progress updates (at least 2.5s and 5% change)
                if (now - last_update_time[0] >= 2.5) or (percent - last_percent[0] >= 10.0):
                    last_update_time[0] = now
                    last_percent[0] = percent

                    speed = d.get("speed")
                    speed_str = f"{speed / (1024 * 1024):.1f} MB/s" if speed else "Noma'lum"
                    eta = d.get("eta")
                    eta_str = f"{eta}s" if eta else "Noma'lum"

                    if progress_callback:
                        asyncio.run_coroutine_threadsafe(
                            progress_callback(round(percent, 1), speed_str, eta_str),
                            loop,
                        )

        ydl_opts: Dict[str, Any] = {
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
            "progress_hooks": [sync_hook],
            "noplaylist": True,
            "socket_timeout": settings.request_timeout,
            "ffmpeg_location": settings.resolved_ffmpeg_path,
            "merge_output_format": "mp4",
        }

        if settings.cookies_file and settings.cookies_file.exists():
            ydl_opts["cookiefile"] = str(settings.cookies_file)

        if is_mp3:
            ydl_opts["format"] = "bestaudio/best"
        elif format_id:
            ydl_opts["format"] = format_id

        def run_ytdlp() -> str:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                return filename

        max_attempts = 3
        last_error = None
        downloaded_file_str = None

        for attempt in range(1, max_attempts + 1):
            try:
                downloaded_file_str = await asyncio.to_thread(run_ytdlp)
                break
            except FileOversizedError:
                raise
            except Exception as exc:
                last_error = exc
                logger.warning(f"Download attempt {attempt}/{max_attempts} failed: {exc}")
                if attempt < max_attempts:
                    await asyncio.sleep(1.5 * attempt)
                else:
                    raise last_error

        downloaded_path = Path(downloaded_file_str)

        # In case yt-dlp changed extension (e.g. mp4, mkv, webm)
        if not downloaded_path.exists():
            candidates = list(output_dir.glob(f"{clean_title}.*"))
            if candidates:
                downloaded_path = candidates[0]
            else:
                raise FileNotFoundError(f"Downloaded file not found in {output_dir}")

        # If MP3 requested, convert to MP3
        if is_mp3:
            mp3_output = output_dir / f"{clean_title}.mp3"
            if downloaded_path.suffix.lower() != ".mp3":
                converted = await convert_to_mp3(
                    input_path=downloaded_path,
                    output_path=mp3_output,
                    title=title,
                    artist=author,
                )
                downloaded_path.unlink(missing_ok=True)
                if not converted or not mp3_output.exists():
                    raise RuntimeError("MP3 formatiga o'tkazishda xatolik yuz berdi.")
                downloaded_path = mp3_output

            # Check final size for audio
            if downloaded_path.stat().st_size > settings.max_file_size_bytes:
                size_b = downloaded_path.stat().st_size
                downloaded_path.unlink(missing_ok=True)
                raise FileOversizedError(size_b, settings.max_file_size_bytes)

            return downloaded_path

        # For video formats: guarantee standard MP4 (H.264/AAC +faststart) for native Telegram player
        if not is_audio and not is_mp3:
            mp4_path = output_dir / f"{clean_title}_player.mp4"
            if await ensure_compatible_mp4(downloaded_path, mp4_path):
                downloaded_path.unlink(missing_ok=True)
                downloaded_path = mp4_path

            # Check final size on disk
            final_size = downloaded_path.stat().st_size
            if final_size > settings.max_file_size_bytes:
                logger.info(
                    f"File size {final_size} exceeds {settings.max_file_size_bytes}. Auto-compressing..."
                )
                compressed_path = output_dir / f"{clean_title}_compressed.mp4"
                if await compress_video_to_size(downloaded_path, compressed_path, target_mb=43.0):
                    downloaded_path.unlink(missing_ok=True)
                    return compressed_path
                else:
                    downloaded_path.unlink(missing_ok=True)
                    raise FileOversizedError(final_size, settings.max_file_size_bytes)

            return downloaded_path

    async def download_direct_file(
        self,
        url: str,
        output_path: Path,
        progress_callback: Optional[Callable[[float, str, str], Any]] = None,
    ) -> Path:
        """Downloads direct image or video file via streaming aiohttp with automatic retries."""
        async with self.semaphore:
            referer = (
                "https://www.instagram.com/"
                if ("cdninstagram" in url or "instagram" in url or "fbcdn" in url)
                else (
                    "https://www.pinterest.com/"
                    if ("pinimg" in url or "pinterest" in url)
                    else "https://www.google.com/"
                )
            )
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "*/*",
                "Referer": referer,
            }
            max_attempts = 3
            last_err = None

            for attempt in range(1, max_attempts + 1):
                try:
                    async with aiohttp.ClientSession(headers=headers) as session:
                        async with session.get(url, timeout=settings.request_timeout) as resp:
                            if resp.status != 200:
                                raise RuntimeError(f"HTTP yuklash xatosi: status {resp.status}")

                            content_length = resp.content_length or 0
                            if content_length > settings.max_file_size_bytes:
                                raise FileOversizedError(content_length, settings.max_file_size_bytes)

                            downloaded = 0
                            last_update = 0.0

                            with open(output_path, "wb") as f:
                                async for chunk in resp.content.iter_chunked(64 * 1024):
                                    f.write(chunk)
                                    downloaded += len(chunk)

                                    if downloaded > settings.max_file_size_bytes:
                                        raise FileOversizedError(downloaded, settings.max_file_size_bytes)

                                    now = time.time()
                                    if progress_callback and (now - last_update >= 2.5) and content_length > 0:
                                        last_update = now
                                        pct = round((downloaded / content_length) * 100, 1)
                                        await progress_callback(pct, "", "")

                            return output_path
                except FileOversizedError:
                    raise
                except Exception as exc:
                    last_err = exc
                    logger.warning(f"Direct download attempt {attempt}/{max_attempts} failed: {exc}")
                    if output_path.exists():
                        output_path.unlink(missing_ok=True)
                    if attempt < max_attempts:
                        await asyncio.sleep(1.0 * attempt)
                    else:
                        raise last_err

            return output_path


download_manager = DownloadManager()
