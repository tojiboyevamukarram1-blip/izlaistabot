import asyncio
import hashlib
import json
import logging
import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse
import aiohttp
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
from bot.security.url_validator import validate_url_security

logger = logging.getLogger(__name__)

PWS_DATA_REGEX = re.compile(r'<script\s+id="__PWS_DATA__"\s+type="application/json">({.*?})</script>', re.DOTALL)
IMAGE_ORIGINAL_REGEX = re.compile(r'https://i\.pinimg\.com/(?:[0-9x]+|originals)/([a-zA-Z0-9/_.-]+\.(?:jpg|jpeg|png|webp))', re.IGNORECASE)


class PinterestExtractor(BaseExtractor):
    """Extractor for Pinterest images and videos."""

    def __init__(self):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def _resolve_pin_it_url(self, session: aiohttp.ClientSession, url: str) -> str:
        """Follow redirects for pin.it short links safely."""
        try:
            async with session.head(url, allow_redirects=True, timeout=10) as resp:
                resolved = str(resp.url)
                is_safe, _ = validate_url_security(resolved)
                if is_safe:
                    return resolved
        except Exception as e:
            logger.debug(f"Failed to resolve short url {url} with HEAD: {e}")

        try:
            async with session.get(url, allow_redirects=True, timeout=10) as resp:
                resolved = str(resp.url)
                is_safe, _ = validate_url_security(resolved)
                if is_safe:
                    return resolved
        except Exception as e:
            logger.warning(f"Failed to resolve short url {url} with GET: {e}")

        return url

    def _sync_ytdlp_extract(self, url: str) -> Optional[Dict[str, Any]]:
        """Fallback to yt-dlp if direct extraction fails."""
        try:
            ydl_opts = {
                "skip_download": True,
                "quiet": True,
                "no_warnings": True,
                "extract_flat": False,
                "socket_timeout": settings.request_timeout,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
        except Exception as e:
            logger.debug(f"yt-dlp Pinterest fallback failed for {url}: {e}")
            return None

    async def extract_metadata(self, url: str) -> Optional[MediaMetadata]:
        """Extracts Pinterest pin image or video."""
        cache_hash = hashlib.md5(url.encode()).hexdigest()[:12]

        async with aiohttp.ClientSession(headers=self.headers) as session:
            # 1. Resolve redirect if pin.it
            parsed = urlparse(url)
            host = (parsed.hostname or "").lower()
            if "pin.it" in host:
                url = await self._resolve_pin_it_url(session, url)

            # 2. Try direct HTML extraction
            try:
                async with session.get(url, timeout=settings.request_timeout) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        
                        # Look for JSON payload
                        match = PWS_DATA_REGEX.search(html)
                        title = "Pinterest Pin"
                        image_url = None
                        video_url = None

                        if match:
                            try:
                                data = json.loads(match.group(1))
                                props = data.get("props", {}).get("initialReduxState", {})
                                pins = props.get("pins", {})
                                for pin_id, pin_data in pins.items():
                                    title = pin_data.get("title") or pin_data.get("grid_title") or pin_data.get("description") or title
                                    # Check for video
                                    videos = pin_data.get("videos", {}).get("video_list", {})
                                    if videos:
                                        # Pick best video stream
                                        for vkey in ("V_720P", "V_EXP7", "V_EXP6", "V_HLSV4"):
                                            if vkey in videos and videos[vkey].get("url"):
                                                video_url = videos[vkey]["url"]
                                                break
                                        if not video_url:
                                            # fallback to any available
                                            first_v = next(iter(videos.values()), {})
                                            video_url = first_v.get("url")

                                    # Check for original image
                                    orig_img = pin_data.get("images", {}).get("orig", {}).get("url")
                                    if orig_img:
                                        image_url = orig_img
                                    break
                            except Exception as json_err:
                                logger.debug(f"JSON parsing error from Pinterest page: {json_err}")

                        # If not found in JSON, search regex for full-res image
                        if not image_url:
                            img_matches = IMAGE_ORIGINAL_REGEX.findall(html)
                            if img_matches:
                                image_url = f"https://i.pinimg.com/originals/{img_matches[0]}"

                        if video_url:
                            return MediaMetadata(
                                platform=Platform.PINTEREST,
                                url=url,
                                title=title[:80],
                                author="Pinterest",
                                duration=None,
                                thumbnail=image_url,
                                formats=[
                                    MediaFormat(
                                        format_id="best",
                                        resolution="HD Video",
                                        ext="mp4",
                                        note="Pinterest Video",
                                    )
                                ],
                                items=[MediaItem(url=video_url, type=MediaType.VIDEO)],
                                is_carousel=False,
                                media_type=MediaType.VIDEO,
                                cache_key=f"pin:{cache_hash}",
                            )

                        if image_url:
                            return MediaMetadata(
                                platform=Platform.PINTEREST,
                                url=url,
                                title=title[:80],
                                author="Pinterest",
                                duration=None,
                                thumbnail=image_url,
                                formats=[
                                    MediaFormat(
                                        format_id="photo",
                                        resolution="Rasm",
                                        ext="jpg",
                                        note="Telegram rasm",
                                    ),
                                    MediaFormat(
                                        format_id="doc",
                                        resolution="Asl sifat (Hujjat)",
                                        ext="jpg",
                                        note="Siqilmagan asl rasm",
                                    ),
                                ],
                                items=[MediaItem(url=image_url, type=MediaType.PHOTO)],
                                is_carousel=False,
                                media_type=MediaType.PHOTO,
                                cache_key=f"pin:{cache_hash}",
                            )
            except Exception as direct_err:
                logger.debug(f"Direct Pinterest extraction failed: {direct_err}")

        # 3. Fallback to yt-dlp
        info = await asyncio.to_thread(self._sync_ytdlp_extract, url)
        if info:
            title = info.get("title") or "Pinterest Media"
            formats = info.get("formats", [])
            video_url = info.get("url")
            thumbnail = info.get("thumbnail")
            ext = info.get("ext", "mp4")

            if ext in ("jpg", "png", "jpeg", "webp"):
                img_url = video_url or thumbnail
                return MediaMetadata(
                    platform=Platform.PINTEREST,
                    url=url,
                    title=title[:80],
                    author="Pinterest",
                    duration=None,
                    thumbnail=thumbnail,
                    formats=[
                        MediaFormat(format_id="photo", resolution="Rasm", ext=ext),
                        MediaFormat(format_id="doc", resolution="Asl sifat (Hujjat)", ext=ext),
                    ],
                    items=[MediaItem(url=img_url, type=MediaType.PHOTO)],
                    is_carousel=False,
                    media_type=MediaType.PHOTO,
                    cache_key=f"pin:{cache_hash}",
                )

            return MediaMetadata(
                platform=Platform.PINTEREST,
                url=url,
                title=title[:80],
                author="Pinterest",
                duration=info.get("duration"),
                thumbnail=thumbnail,
                formats=[
                    MediaFormat(
                        format_id="best",
                        resolution="Video",
                        ext="mp4",
                        filesize=info.get("filesize") or info.get("filesize_approx"),
                    )
                ],
                items=[],
                is_carousel=False,
                media_type=MediaType.VIDEO,
                cache_key=f"pin:{cache_hash}",
            )

        return None
