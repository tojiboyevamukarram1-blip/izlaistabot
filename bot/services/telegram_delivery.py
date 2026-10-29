import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Union
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.types import (
    FSInputFile,
    InputMediaAudio,
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
    Message,
)

from bot.downloader.ffmpeg_utils import extract_thumbnail, get_video_info
from bot.extractors.models import MediaType
from bot.services.cache import cache_service

logger = logging.getLogger(__name__)


async def safe_edit_text(
    bot: Bot,
    chat_id: int,
    message_id: int,
    text: str,
    reply_markup=None,
) -> bool:
    """Safely updates Telegram message text, catching Telegram rate limit exceptions."""
    try:
        await bot.edit_message_text(
            text=text,
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
        return True
    except TelegramRetryAfter as e:
        logger.debug(f"Telegram retry after {e.retry_after}s while editing message")
        return False
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            return True
        logger.debug(f"Bad request editing message: {e}")
        return False
    except Exception as e:
        logger.debug(f"Failed to edit message: {e}")
        return False


class TelegramDeliveryService:
    """Handles sending media to Telegram with automatic fallback and file_id caching."""

    async def send_cached_media(
        self,
        bot: Bot,
        chat_id: int,
        cached_info: dict,
        caption: str = "",
    ) -> Optional[Message]:
        """Delivers media instantly using previously uploaded Telegram file_id."""
        file_id = cached_info.get("file_id")
        media_type = cached_info.get("media_type")
        if not file_id:
            return None

        try:
            if media_type == MediaType.VIDEO:
                return await bot.send_video(
                    chat_id=chat_id,
                    video=file_id,
                    caption=caption,
                    parse_mode="HTML",
                    supports_streaming=True,
                )
            elif media_type == MediaType.AUDIO:
                return await bot.send_audio(
                    chat_id=chat_id,
                    audio=file_id,
                    caption=caption,
                    parse_mode="HTML",
                )
            elif media_type == MediaType.PHOTO:
                return await bot.send_photo(
                    chat_id=chat_id,
                    photo=file_id,
                    caption=caption,
                    parse_mode="HTML",
                )
            else:
                return await bot.send_document(
                    chat_id=chat_id,
                    document=file_id,
                    caption=caption,
                    parse_mode="HTML",
                )
        except Exception as e:
            logger.warning(f"Failed to send cached file_id {file_id}: {e}")
            return None

    async def deliver_single_file(
        self,
        bot: Bot,
        chat_id: int,
        file_path: Path,
        media_type: MediaType,
        title: str = "",
        author: str = "",
        duration: Optional[int] = None,
        as_document: bool = False,
        cache_key: Optional[str] = None,
        format_id: Optional[str] = None,
    ) -> Message:
        """Sends a single downloaded media file to user."""
        caption = f"🎬 <b>{title}</b>\n👤 {author}" if title else ""
        input_file = FSInputFile(str(file_path))

        msg = None
        delivered_type = media_type

        # As document
        if as_document or media_type == MediaType.DOCUMENT:
            msg = await bot.send_document(
                chat_id=chat_id,
                document=input_file,
                caption=caption,
                parse_mode="HTML",
            )
            delivered_type = MediaType.DOCUMENT

        # Audio
        elif media_type == MediaType.AUDIO or file_path.suffix.lower() in (".mp3", ".m4a", ".aac"):
            msg = await bot.send_audio(
                chat_id=chat_id,
                audio=input_file,
                caption=caption,
                title=title[:100] if title else None,
                performer=author[:100] if author else None,
                duration=duration,
                parse_mode="HTML",
            )
            delivered_type = MediaType.AUDIO

        # Photo
        elif media_type == MediaType.PHOTO or file_path.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            try:
                msg = await bot.send_photo(
                    chat_id=chat_id,
                    photo=input_file,
                    caption=caption,
                    parse_mode="HTML",
                )
                delivered_type = MediaType.PHOTO
            except Exception as photo_err:
                logger.warning(f"send_photo failed, falling back to document: {photo_err}")
                msg = await bot.send_document(
                    chat_id=chat_id,
                    document=input_file,
                    caption=caption,
                    parse_mode="HTML",
                )
                delivered_type = MediaType.DOCUMENT

        # Video
        else:
            thumb_path = file_path.parent / "thumb.jpg"
            if not thumb_path.exists():
                await extract_thumbnail(file_path, thumb_path)

            vid_w, vid_h, vid_dur = await get_video_info(file_path)
            eff_dur = vid_dur if vid_dur else duration

            last_video_err = None
            for send_attempt in range(1, 3):
                try:
                    video_input = FSInputFile(str(file_path))
                    thumb_input = FSInputFile(str(thumb_path)) if thumb_path.exists() else None
                    msg = await bot.send_video(
                        chat_id=chat_id,
                        video=video_input,
                        caption=caption,
                        duration=eff_dur,
                        width=vid_w,
                        height=vid_h,
                        thumbnail=thumb_input,
                        supports_streaming=True,
                        parse_mode="HTML",
                    )
                    delivered_type = MediaType.VIDEO
                    break
                except Exception as video_err:
                    last_video_err = video_err
                    logger.warning(
                        f"send_video attempt {send_attempt} failed: {video_err}"
                    )
                    if send_attempt < 2:
                        await asyncio.sleep(2)

            if not msg:
                logger.error(f"send_video failed permanently: {last_video_err}")
                raise last_video_err

        # Cache file_id for future instant access
        if msg and cache_key and format_id:
            try:
                file_id = None
                if msg.video:
                    file_id = msg.video.file_id
                elif msg.audio:
                    file_id = msg.audio.file_id
                elif msg.photo:
                    file_id = msg.photo[-1].file_id
                elif msg.document:
                    file_id = msg.document.file_id

                if file_id:
                    await cache_service.set_cached_file_id(
                        cache_key=cache_key,
                        format_id=format_id,
                        file_id=file_id,
                        media_type=delivered_type.value,
                    )
            except Exception as cache_err:
                logger.debug(f"Could not cache file_id: {cache_err}")

        return msg

    async def deliver_album(
        self,
        bot: Bot,
        chat_id: int,
        file_paths: List[Path],
        media_types: List[MediaType],
        caption: str = "",
    ) -> List[Message]:
        """Delivers a group of files as an album/media group (max 10 items per group)."""
        messages = []
        chunk_size = 10

        for i in range(0, len(file_paths), chunk_size):
            chunk_files = file_paths[i : i + chunk_size]
            chunk_types = media_types[i : i + chunk_size]

            media_group = []
            for j, (fpath, mtype) in enumerate(zip(chunk_files, chunk_types)):
                item_caption = caption if (i == 0 and j == 0) else None
                input_file = FSInputFile(str(fpath))

                if mtype == MediaType.VIDEO or fpath.suffix.lower() in (".mp4", ".mov", ".mkv"):
                    media_group.append(
                        InputMediaVideo(
                            media=input_file,
                            caption=item_caption,
                            parse_mode="HTML",
                            supports_streaming=True,
                        )
                    )
                else:
                    media_group.append(
                        InputMediaPhoto(
                            media=input_file,
                            caption=item_caption,
                            parse_mode="HTML",
                        )
                    )

            if media_group:
                msgs = await bot.send_media_group(chat_id=chat_id, media=media_group)
                messages.extend(msgs)

        return messages


telegram_delivery = TelegramDeliveryService()
