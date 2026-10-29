import asyncio
import json
import logging
import shutil
from pathlib import Path
from typing import Optional, Tuple
import mutagen
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3

from bot.config import settings

logger = logging.getLogger(__name__)


async def convert_to_mp3(
    input_path: Path,
    output_path: Path,
    title: Optional[str] = None,
    artist: Optional[str] = None,
) -> bool:
    """
    Converts audio/video file to 192kbps MP3 and injects ID3 tags.
    """
    try:
        cmd = [
            settings.resolved_ffmpeg_path,
            "-y",
            "-i",
            str(input_path),
            "-vn",
            "-acodec",
            "libmp3lame",
            "-ab",
            "192k",
            "-ar",
            "44100",
            str(output_path),
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            logger.error(f"FFmpeg MP3 conversion failed (code {proc.returncode}): {stderr.decode(errors='ignore')}")
            return False

        # Add ID3 metadata
        try:
            audio = MP3(str(output_path), ID3=EasyID3)
            try:
                audio.add_tags(ID3=EasyID3)
            except Exception:
                pass
            if title:
                audio["title"] = title[:100]
            if artist:
                audio["artist"] = artist[:100]
            audio.save()
        except Exception as tag_err:
            logger.debug(f"Could not write ID3 tags: {tag_err}")

        return True
    except Exception as e:
        logger.error(f"Error in convert_to_mp3: {e}", exc_info=True)
        return False


async def remux_mp4_faststart(input_path: Path, output_path: Path) -> bool:
    """Remuxes MP4 with +faststart flag."""
    return await ensure_compatible_mp4(input_path, output_path)


async def ensure_compatible_mp4(input_path: Path, output_path: Path) -> bool:
    """
    Ensures the video is in standard MP4 (H.264 / AAC +faststart) format
    so Telegram can play it natively as a video stream rather than a document.
    """
    # 1. Try fast stream copy if already compatible
    cmd_copy = [
        settings.resolved_ffmpeg_path,
        "-y",
        "-i",
        str(input_path),
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd_copy,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.communicate()
        if proc.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0:
            return True
    except Exception as e:
        logger.debug(f"Fast copy remux failed: {e}")

    # 2. Re-encode to standard H.264 + AAC MP4 with faststart (handles webm/vp9/mkv)
    cmd_encode = [
        settings.resolved_ffmpeg_path,
        "-y",
        "-i",
        str(input_path),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd_encode,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.communicate()
        return proc.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0
    except Exception as e:
        logger.error(f"FFmpeg MP4 transcode failed: {e}")
        return False


async def compress_video_to_size(
    input_path: Path, output_path: Path, target_mb: float = 43.0
) -> bool:
    """
    Compresses video to fit under target_mb (default 48MB for Telegram 50MB limit).
    """
    try:
        w, h, dur = await get_video_info(input_path)
        if not dur or dur <= 0:
            dur = 600

        target_bytes = target_mb * 1024 * 1024
        total_bitrate = int((target_bytes * 8) / dur)
        audio_bitrate = min(64000, max(32000, int(total_bitrate * 0.15)))
        video_bitrate = max(40000, int(total_bitrate - audio_bitrate))

        cmd = [
            settings.resolved_ffmpeg_path,
            "-y",
            "-i",
            str(input_path),
            "-c:v",
            "libx264",
            "-b:v",
            str(video_bitrate),
            "-maxrate",
            str(int(video_bitrate * 1.25)),
            "-bufsize",
            str(int(video_bitrate * 2)),
            "-preset",
            "veryfast",
            "-vf",
            "scale='min(854,iw)':-2",
            "-c:a",
            "aac",
            "-b:a",
            str(audio_bitrate),
            "-movflags",
            "+faststart",
            str(output_path),
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.communicate()
        return (
            proc.returncode == 0
            and output_path.exists()
            and output_path.stat().st_size <= settings.max_file_size_bytes
        )
    except Exception as e:
        logger.error(f"Compression failed: {e}")
        return False


async def get_video_info(video_path: Path) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """Extracts (width, height, duration) using ffprobe."""
    ffprobe_path = shutil.which("ffprobe") or "ffprobe"
    cmd = [
        ffprobe_path,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,duration",
        "-of",
        "json",
        str(video_path),
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0:
            data = json.loads(stdout.decode(errors="ignore"))
            streams = data.get("streams", [])
            if streams:
                w = streams[0].get("width")
                h = streams[0].get("height")
                dur = streams[0].get("duration")
                return (
                    int(w) if w else None,
                    int(h) if h else None,
                    int(float(dur)) if dur else None,
                )
    except Exception as e:
        logger.debug(f"ffprobe extraction failed: {e}")
    return (None, None, None)


async def extract_thumbnail(video_path: Path, thumb_path: Path) -> Optional[Path]:
    """
    Extracts a frame from video as a JPEG thumbnail.
    """
    try:
        cmd = [
            settings.resolved_ffmpeg_path,
            "-y",
            "-ss",
            "00:00:01",
            "-i",
            str(video_path),
            "-vframes",
            "1",
            "-q:v",
            "2",
            str(thumb_path),
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.communicate()
        if proc.returncode == 0 and thumb_path.exists() and thumb_path.stat().st_size > 0:
            return thumb_path
    except Exception as e:
        logger.debug(f"Thumbnail extraction failed: {e}")
    return None
