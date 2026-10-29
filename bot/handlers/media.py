import asyncio
import logging
import uuid
from pathlib import Path
from aiogram import F, Router
from aiogram.types import Message

from bot.config import settings
from bot.downloader.manager import FileOversizedError, download_manager
from bot.extractors import (
    InstagramExtractor,
    PinterestExtractor,
    Platform,
    YouTubeExtractor,
    detect_platform,
)
from bot.extractors.models import MediaType
from bot.locales import uz
from bot.security import (
    cleanup_directory,
    create_safe_task_dir,
    extract_first_url,
    is_supported_platform_url,
    validate_url_security,
)
from bot.services.telegram_delivery import safe_edit_text, telegram_delivery

logger = logging.getLogger(__name__)

media_router = Router()

yt_extractor = YouTubeExtractor()
ig_extractor = InstagramExtractor()
pin_extractor = PinterestExtractor()


@media_router.message(F.text)
async def handle_url_message(message: Message):
    """
    Processes media URLs and directly downloads and sends the video/photo
    without displaying any format selection buttons or intermediate prompts.
    """
    text = (message.text or "").strip()
    if text.startswith("/"):
        return  # Ignore slash commands

    url = extract_first_url(text)
    if not url:
        return

    # Check supported platform
    if not is_supported_platform_url(url):
        await message.answer(uz.UNSUPPORTED_PLATFORM, parse_mode="HTML")
        return

    # Security & SSRF check
    is_safe, error_msg = validate_url_security(url)
    if not is_safe:
        logger.warning(f"SSRF check failed for {url}: {error_msg}")
        await message.answer(uz.SSRF_BLOCKED, parse_mode="HTML")
        return

    # Initial acknowledgement
    status_msg = await message.answer(uz.DOWNLOADING_NO_PERCENT)
    user_id = message.from_user.id
    chat_id = message.chat.id
    task_id = f"task_{uuid.uuid4().hex[:10]}"
    task_dir = create_safe_task_dir(settings.temp_dir, user_id, task_id)

    async def progress_hook(pct: float, speed: str, eta: str):
        text_status = uz.DOWNLOADING_MEDIA.format(
            percent=pct,
            speed=speed if speed else "Hisoblanmoqda...",
            eta=eta if eta else "Biroz kuting",
        )
        await safe_edit_text(
            bot=message.bot,
            chat_id=chat_id,
            message_id=status_msg.message_id,
            text=text_status,
        )

    try:
        platform = detect_platform(url)

        # ====================================================
        # 1. YOUTUBE (Direct download best quality under 50MB)
        # ====================================================
        if platform == Platform.YOUTUBE:
            meta = await yt_extractor.extract_metadata(url)
            if not meta:
                await safe_edit_text(
                    bot=message.bot,
                    chat_id=chat_id,
                    message_id=status_msg.message_id,
                    text=uz.FETCHING_METADATA_ERROR,
                )
                return

            if meta.duration and meta.duration > settings.max_duration_seconds:
                await safe_edit_text(
                    bot=message.bot,
                    chat_id=chat_id,
                    message_id=status_msg.message_id,
                    text=uz.DURATION_TOO_LONG.format(
                        duration_min=meta.duration // 60,
                        limit_min=settings.max_duration_seconds // 60,
                    ),
                )
                return

            # Pick best video format that fits comfortably under Telegram 50MB limit
            video_formats = [f for f in meta.formats if not f.is_audio]
            dur = meta.duration or 0

            if dur > 2400:  # > 40 mins (e.g. 77 mins video)
                chosen_fmt_id = (
                    "bestvideo[height<=360]+bestaudio[abr<=64]/"
                    "bestvideo[height<=360]+bestaudio/"
                    "best[height<=360]/worst"
                )
            elif dur > 600:  # 10 - 40 mins
                chosen_fmt_id = (
                    "bestvideo[height<=480]+bestaudio[abr<=96]/"
                    "bestvideo[height<=480]+bestaudio/"
                    "best[height<=480]/worst"
                )
            elif video_formats:
                under_limit = [
                    f for f in video_formats
                    if f.effective_filesize and f.effective_filesize <= 46 * 1024 * 1024
                ]
                if under_limit:
                    chosen_fmt_id = under_limit[0].format_id
                else:
                    chosen_fmt_id = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
            else:
                chosen_fmt_id = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"

            file_path = await download_manager.download_media(
                url=meta.url,
                format_id=chosen_fmt_id,
                output_dir=task_dir,
                title=meta.title,
                author=meta.author,
                is_audio=False,
                is_mp3=False,
                progress_callback=progress_hook,
            )

            await safe_edit_text(
                bot=message.bot,
                chat_id=chat_id,
                message_id=status_msg.message_id,
                text=uz.UPLOADING_TELEGRAM,
            )

            await telegram_delivery.deliver_single_file(
                bot=message.bot,
                chat_id=chat_id,
                file_path=file_path,
                media_type=MediaType.VIDEO,
                title=meta.title,
                author=meta.author,
                duration=meta.duration,
            )

        # ====================================================
        # 2. INSTAGRAM (Reels, video posts, and carousels)
        # ====================================================
        elif platform == Platform.INSTAGRAM:
            meta = await ig_extractor.extract_metadata(url)
            if not meta:
                # Direct download fallback with yt-dlp
                file_path = await download_manager.download_media(
                    url=url,
                    format_id="best",
                    output_dir=task_dir,
                    title="Instagram Video",
                    author="Instagram",
                    progress_callback=progress_hook,
                )
                await safe_edit_text(
                    bot=message.bot,
                    chat_id=chat_id,
                    message_id=status_msg.message_id,
                    text=uz.UPLOADING_TELEGRAM,
                )
                await telegram_delivery.deliver_single_file(
                    bot=message.bot,
                    chat_id=chat_id,
                    file_path=file_path,
                    media_type=MediaType.VIDEO,
                    title="Instagram Video",
                    author="Instagram",
                )
            elif meta.is_carousel and meta.items:
                await safe_edit_text(
                    bot=message.bot,
                    chat_id=chat_id,
                    message_id=status_msg.message_id,
                    text=uz.INSTAGRAM_CAROUSEL_DOWNLOAD.format(count=len(meta.items)),
                )
                downloaded_paths = []
                downloaded_types = []

                for idx, item in enumerate(meta.items):
                    ext = "mp4" if item.type == MediaType.VIDEO else "jpg"
                    item_dest = task_dir / f"carousel_{idx:02d}.{ext}"
                    try:
                        await download_manager.download_direct_file(
                            url=item.url,
                            output_path=item_dest,
                        )
                        downloaded_paths.append(item_dest)
                        downloaded_types.append(item.type)
                    except Exception as item_err:
                        logger.warning(f"Error downloading carousel item {idx}: {item_err}")

                if downloaded_paths:
                    await safe_edit_text(
                        bot=message.bot,
                        chat_id=chat_id,
                        message_id=status_msg.message_id,
                        text=uz.UPLOADING_TELEGRAM,
                    )
                    caption = f"📸 <b>{meta.title}</b>\n👤 {meta.author}"
                    await telegram_delivery.deliver_album(
                        bot=message.bot,
                        chat_id=chat_id,
                        file_paths=downloaded_paths,
                        media_types=downloaded_types,
                        caption=caption,
                    )
            elif meta.media_type == MediaType.PHOTO and meta.items:
                # Single photo post
                photo_dest = task_dir / "instagram_photo.jpg"
                file_path = await download_manager.download_direct_file(
                    url=meta.items[0].url,
                    output_path=photo_dest,
                    progress_callback=progress_hook,
                )
                await safe_edit_text(
                    bot=message.bot,
                    chat_id=chat_id,
                    message_id=status_msg.message_id,
                    text=uz.UPLOADING_TELEGRAM,
                )
                await telegram_delivery.deliver_single_file(
                    bot=message.bot,
                    chat_id=chat_id,
                    file_path=file_path,
                    media_type=MediaType.PHOTO,
                    title=meta.title,
                    author=meta.author,
                )
            else:
                # Instagram Reel or single video
                file_path = await download_manager.download_media(
                    url=meta.url,
                    format_id="best",
                    output_dir=task_dir,
                    title=meta.title,
                    author=meta.author,
                    progress_callback=progress_hook,
                )
                await safe_edit_text(
                    bot=message.bot,
                    chat_id=chat_id,
                    message_id=status_msg.message_id,
                    text=uz.UPLOADING_TELEGRAM,
                )
                await telegram_delivery.deliver_single_file(
                    bot=message.bot,
                    chat_id=chat_id,
                    file_path=file_path,
                    media_type=MediaType.VIDEO,
                    title=meta.title,
                    author=meta.author,
                    duration=meta.duration,
                )

        # ====================================================
        # 3. PINTEREST (Direct photo or video)
        # ====================================================
        elif platform == Platform.PINTEREST:
            meta = await pin_extractor.extract_metadata(url)
            if not meta:
                await safe_edit_text(
                    bot=message.bot,
                    chat_id=chat_id,
                    message_id=status_msg.message_id,
                    text=uz.FETCHING_METADATA_ERROR,
                )
                return

            if meta.media_type == MediaType.VIDEO:
                item_url = meta.items[0].url if meta.items else meta.url
                out_vid = task_dir / "pinterest_video.mp4"
                if item_url.startswith("http") and ".mp4" in item_url:
                    file_path = await download_manager.download_direct_file(
                        url=item_url,
                        output_path=out_vid,
                        progress_callback=progress_hook,
                    )
                else:
                    file_path = await download_manager.download_media(
                        url=meta.url,
                        format_id="best",
                        output_dir=task_dir,
                        title=meta.title,
                        author="Pinterest",
                        progress_callback=progress_hook,
                    )
                await safe_edit_text(
                    bot=message.bot,
                    chat_id=chat_id,
                    message_id=status_msg.message_id,
                    text=uz.UPLOADING_TELEGRAM,
                )
                await telegram_delivery.deliver_single_file(
                    bot=message.bot,
                    chat_id=chat_id,
                    file_path=file_path,
                    media_type=MediaType.VIDEO,
                    title=meta.title,
                    author="Pinterest",
                )
            else:
                # Photo Pin
                item_url = meta.items[0].url if meta.items else meta.url
                out_img = task_dir / "pinterest_image.jpg"
                file_path = await download_manager.download_direct_file(
                    url=item_url,
                    output_path=out_img,
                    progress_callback=progress_hook,
                )
                await safe_edit_text(
                    bot=message.bot,
                    chat_id=chat_id,
                    message_id=status_msg.message_id,
                    text=uz.UPLOADING_TELEGRAM,
                )
                await telegram_delivery.deliver_single_file(
                    bot=message.bot,
                    chat_id=chat_id,
                    file_path=file_path,
                    media_type=MediaType.PHOTO,
                    title=meta.title,
                    author="Pinterest",
                )

        # Delete status message on completion
        try:
            await message.bot.delete_message(chat_id=chat_id, message_id=status_msg.message_id)
        except Exception:
            pass

    except FileOversizedError as e:
        await safe_edit_text(
            bot=message.bot,
            chat_id=chat_id,
            message_id=status_msg.message_id,
            text=uz.FILE_TOO_LARGE.format(
                size_mb=e.size_bytes / (1024 * 1024),
                limit_mb=settings.max_file_size_mb,
            ),
        )
    except Exception as e:
        err_str = str(e).lower()
        logger.error(f"Direct media handling failed for {url}: {e}", exc_info=True)
        if (
            "isn't available to everyone" in err_str
            or "certain audiences" in err_str
            or "login required" in err_str
        ):
            err_msg = uz.MEDIA_RESTRICTED
        elif "private" in err_str:
            err_msg = uz.MEDIA_PRIVATE
        elif "not found" in err_str or "deleted" in err_str:
            err_msg = uz.MEDIA_NOT_FOUND
        else:
            err_msg = uz.GENERIC_ERROR.format(error=str(e)[:80])

        await safe_edit_text(
            bot=message.bot,
            chat_id=chat_id,
            message_id=status_msg.message_id,
            text=err_msg,
        )
    finally:
        cleanup_directory(task_dir)
