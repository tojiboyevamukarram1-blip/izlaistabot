import asyncio
import hashlib
import logging
from typing import Any, Dict, List, Optional
import yt_dlp

from bot.config import settings
from bot.extractors.base import BaseExtractor
from bot.extractors.models import (
    MediaFormat,
    MediaMetadata,
    MediaType,
    Platform,
)

logger = logging.getLogger(__name__)

STANDARD_RESOLUTIONS = [2160, 1440, 1080, 720, 480, 360, 240, 144]


class YouTubeExtractor(BaseExtractor):
    """Extractor for YouTube videos and Shorts using yt-dlp."""

    def __init__(self):
        self.ydl_opts: Dict[str, Any] = {
            "skip_download": True,
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "noplaylist": True,
            "socket_timeout": settings.request_timeout,
        }
        if settings.cookies_file and settings.cookies_file.exists():
            self.ydl_opts["cookiefile"] = str(settings.cookies_file)

    def _sync_extract_info(self, url: str) -> Optional[Dict[str, Any]]:
        """Synchronously extracts metadata using yt-dlp."""
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                return ydl.extract_info(url, download=False)
        except Exception as e:
            logger.warning(f"yt-dlp extract_info failed for {url}: {e}")
            return None

    async def extract_metadata(self, url: str) -> Optional[MediaMetadata]:
        """Asynchronously extracts YouTube video metadata and available formats."""
        try:
            info = await asyncio.to_thread(self._sync_extract_info, url)
            if not info:
                return None

            raw_formats = info.get("formats", [])
            title = info.get("title", "YouTube Video")
            author = info.get("uploader") or info.get("channel") or "YouTube"
            duration = info.get("duration")
            thumbnail = info.get("thumbnail")

            # Check if duration exceeds maximum limit
            if duration and duration > settings.max_duration_seconds:
                logger.info(f"Video {url} duration {duration}s exceeds limit {settings.max_duration_seconds}s")

            # Find best audio format for merging and size estimation
            best_audio = None
            audio_formats = [
                f for f in raw_formats
                if f.get("vcodec") == "none" and f.get("acodec") != "none"
            ]
            if audio_formats:
                # Sort by abr (audio bitrate) or filesize
                audio_formats.sort(key=lambda x: (x.get("abr") or 0, x.get("filesize") or 0), reverse=True)
                best_audio = audio_formats[0]

            audio_size = 0
            if best_audio:
                audio_size = best_audio.get("filesize") or best_audio.get("filesize_approx") or 0

            # Find genuine available resolutions
            video_formats = [
                f for f in raw_formats
                if f.get("vcodec") != "none" and f.get("height")
            ]

            available_formats: List[MediaFormat] = []
            seen_resolutions = set()

            for target_height in STANDARD_RESOLUTIONS:
                # Match formats close to target height (within 5% tolerance for aspect ratios like 1920x1076)
                matching = [
                    f for f in video_formats
                    if abs((f.get("height") or 0) - target_height) <= max(2, target_height * 0.04)
                ]
                if not matching:
                    continue

                res_label = f"{target_height}p"
                if res_label in seen_resolutions:
                    continue
                seen_resolutions.add(res_label)

                # Prioritize MP4 container with H.264 (avc1) for maximum Telegram compatibility
                def format_score(f: Dict[str, Any]) -> tuple:
                    ext_score = 2 if f.get("ext") == "mp4" else 1
                    vcodec = str(f.get("vcodec", "")).lower()
                    codec_score = 2 if "avc" in vcodec or "h264" in vcodec else 1
                    fps = f.get("fps") or 30
                    return (ext_score, codec_score, fps)

                matching.sort(key=format_score, reverse=True)
                best_match = matching[0]

                raw_video_size = best_match.get("filesize") or best_match.get("filesize_approx") or 0
                total_size = raw_video_size + audio_size if best_match.get("acodec") == "none" else raw_video_size

                # Format ID specification for yt-dlp downloader:
                # If video has no audio, download video+bestaudio and merge
                if best_match.get("acodec") == "none":
                    effective_fmt_id = f"{best_match['format_id']}+bestaudio/best"
                    requires_merge = True
                else:
                    effective_fmt_id = str(best_match["format_id"])
                    requires_merge = False

                media_format = MediaFormat(
                    format_id=effective_fmt_id,
                    resolution=res_label,
                    ext="mp4",
                    filesize=total_size if total_size > 0 else None,
                    note=f"{best_match.get('fps', 30)}fps",
                    is_audio=False,
                    vcodec=best_match.get("vcodec"),
                    acodec=best_match.get("acodec"),
                    requires_merge=requires_merge,
                )
                available_formats.append(media_format)

            # Audio options
            # 1. MP3 Audio
            available_formats.append(
                MediaFormat(
                    format_id="bestaudio/best",
                    resolution="MP3",
                    ext="mp3",
                    filesize=audio_size if audio_size > 0 else None,
                    note="MP3 192kbps",
                    is_audio=True,
                )
            )

            # 2. Original Audio
            if best_audio:
                orig_ext = best_audio.get("ext") or "m4a"
                available_formats.append(
                    MediaFormat(
                        format_id=str(best_audio.get("format_id", "bestaudio")),
                        resolution="Asl audio",
                        ext=orig_ext,
                        filesize=audio_size if audio_size > 0 else None,
                        note=f"{best_audio.get('acodec', orig_ext)}",
                        is_audio=True,
                    )
                )

            cache_hash = hashlib.md5(url.encode()).hexdigest()[:12]

            return MediaMetadata(
                platform=Platform.YOUTUBE,
                url=url,
                title=title,
                author=author,
                duration=duration,
                thumbnail=thumbnail,
                formats=available_formats,
                items=[],
                is_carousel=False,
                media_type=MediaType.VIDEO,
                cache_key=f"yt:{cache_hash}",
            )

        except Exception as e:
            logger.error(f"Error extracting YouTube metadata for {url}: {e}", exc_info=True)
            return None
