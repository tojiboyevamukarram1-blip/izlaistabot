import asyncio
import hashlib
import logging
from typing import Any, Dict, List, Optional
import yt_dlp

from bot.config import settings
from bot.extractors.base import BaseExtractor
from bot.extractors.models import (
    MediaFormat,
    MediaItem,
    MediaMetadata,
    MediaType,
    Platform,
)

logger = logging.getLogger(__name__)


class InstagramExtractor(BaseExtractor):
    """Extractor for Instagram Reels, public video posts, and carousels using yt-dlp."""

    def __init__(self):
        self.ydl_opts: Dict[str, Any] = {
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "noplaylist": False,
            "socket_timeout": settings.request_timeout,
            "http_headers": {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/128.0.0.0 Safari/537.36"
                ),
            },
        }
        if settings.cookies_file and settings.cookies_file.exists():
            self.ydl_opts["cookiefile"] = str(settings.cookies_file)

    def _sync_extract_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Synchronous yt-dlp call."""
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
        except Exception as e:
            logger.warning(f"yt-dlp Instagram extraction failed for {url}: {e}")
            return None

    async def extract_metadata(self, url: str) -> Optional[MediaMetadata]:
        """Asynchronously extracts Instagram media metadata."""
        try:
            info = await asyncio.to_thread(self._sync_extract_info, url)
            if not info:
                return None

            title = info.get("description") or info.get("title") or "Instagram Post"
            author = info.get("uploader") or info.get("channel") or "Instagram"
            duration = info.get("duration")
            thumbnail = info.get("thumbnail")
            cache_hash = hashlib.md5(url.encode()).hexdigest()[:12]

            # Check if this is a carousel with multiple entries
            entries = info.get("entries")
            if entries and len(entries) > 1:
                items: List[MediaItem] = []
                for entry in entries:
                    if not entry:
                        continue
                    item_url = entry.get("url") or (entry.get("formats", [{}])[-1].get("url") if entry.get("formats") else None)
                    if not item_url:
                        continue

                    # Determine if this entry is video or photo
                    is_video = bool(entry.get("vcodec") and entry.get("vcodec") != "none" and entry.get("ext") in ("mp4", "webm"))
                    items.append(
                        MediaItem(
                            url=item_url,
                            type=MediaType.VIDEO if is_video else MediaType.PHOTO,
                            thumbnail=entry.get("thumbnail"),
                        )
                    )

                if items:
                    return MediaMetadata(
                        platform=Platform.INSTAGRAM,
                        url=url,
                        title=title[:80],
                        author=author,
                        duration=duration,
                        thumbnail=thumbnail,
                        formats=[],
                        items=items,
                        is_carousel=True,
                        media_type=MediaType.CAROUSEL,
                        cache_key=f"ig:{cache_hash}",
                    )

            # Single Video or Reel or Photo
            raw_formats = info.get("formats", [])
            filesize = info.get("filesize") or info.get("filesize_approx")
            if not filesize and raw_formats:
                filesize = raw_formats[-1].get("filesize") or raw_formats[-1].get("filesize_approx")

            # Check if single entry is an image or video
            is_image = info.get("ext") in ("jpg", "jpeg", "png", "webp") or not raw_formats or (raw_formats and raw_formats[-1].get("vcodec") == "none" and raw_formats[-1].get("acodec") == "none")

            if is_image:
                direct_url = info.get("url") or thumbnail or (raw_formats[-1].get("url") if raw_formats else "")
                return MediaMetadata(
                    platform=Platform.INSTAGRAM,
                    url=url,
                    title=title[:80],
                    author=author,
                    duration=None,
                    thumbnail=thumbnail,
                    formats=[
                        MediaFormat(
                            format_id="original",
                            resolution="Asl rasm",
                            ext=info.get("ext", "jpg"),
                            filesize=filesize,
                            note="Asl rasm",
                            is_audio=False,
                        )
                    ],
                    items=[MediaItem(url=direct_url, type=MediaType.PHOTO)],
                    is_carousel=False,
                    media_type=MediaType.PHOTO,
                    cache_key=f"ig:{cache_hash}",
                )

            # Video or Reel
            formats = [
                MediaFormat(
                    format_id="best",
                    resolution="HD Video",
                    ext="mp4",
                    filesize=filesize,
                    note="Eng yaxshi sifat",
                    is_audio=False,
                )
            ]

            return MediaMetadata(
                platform=Platform.INSTAGRAM,
                url=url,
                title=title[:80],
                author=author,
                duration=duration,
                thumbnail=thumbnail,
                formats=formats,
                items=[],
                is_carousel=False,
                media_type=MediaType.VIDEO,
                cache_key=f"ig:{cache_hash}",
            )

        except Exception as e:
            logger.error(f"Error extracting Instagram metadata for {url}: {e}", exc_info=True)
            return None
