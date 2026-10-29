import asyncio
import logging
import uuid
from pathlib import Path
from typing import Optional
from aiogram import F, Router
from aiogram.types import CallbackQuery

from bot.config import settings
from bot.downloader.manager import FileOversizedError, download_manager
from bot.extractors.models import MediaMetadata, MediaType, Platform
from bot.locales import uz
from bot.security.sanitizer import cleanup_directory, create_safe_task_dir
from bot.services.cache import cache_service
from bot.services.telegram_delivery import safe_edit_text, telegram_delivery

logger = logging.getLogger(__name__)

callback_router = Router()


@callback_router.callback_query(F.data == "cancel")
async def handle_cancel_callback(callback: CallbackQuery):
    """Handles cancellation button."""
    await callback.answer(uz.CANCEL_SUCCESS)
    try:
        await callback.message.delete()
    except Exception:
        await safe_edit_text(
            bot=callback.bot,
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            text=uz.CANCEL_SUCCESS,
        )


@callback_router.callback_query(F.data.startswith("dl:"))
async def handle_download_callback(callback: CallbackQuery):
    """Handles quality selection and download execution."""
    data_parts = callback.data.split(":")
    if len(data_parts) < 3:
        await callback.answer("Noto'g'ri so'rov.", show_alert=True)
        return

    action = data_parts[-1]
    cache_key = ":".join(data_parts[1:-1])
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id
    status_msg_id = callback.message.message_id

    # Retrieve cached metadata
    meta_dict = await cache_service.get_json(f"meta:{cache_key}")
    if not meta_dict:
        await callback.answer(
            "⚠️ So'rov eskirgan. Iltimos, havolani qaytadan yuboring.",
            show_alert=True,
        )
        return

    meta = MediaMetadata(**meta_dict)
    await callback.answer("⏳ Yuklab olish boshlanmoqda...")

    # 1. Check if Telegram file_id is already cached for this exact action
    cached_file = await cache_service.get_cached_file_id(cache_key, action)
    if cached_file:
        caption = f"🎬 <b>{meta.title}</b>\n👤 {meta.author}"
        sent = await telegram_delivery.send_cached_media(
            bot=callback.bot,
            chat_id=chat_id,
            cached_info=cached_file,
            caption=caption,
        )
        if sent:
            try:
                await callback.message.delete()
            except Exception:
                pass
            return

    # 2. Not cached: start download
    task_id = f"task_{uuid.uuid4().hex[:10]}"
    task_dir = create_safe_task_dir(settings.temp_dir, user_id, task_id)

    # Initial status update
    await safe_edit_text(
        bot=callback.bot,
        chat_id=chat_id,
        message_id=status_msg_id,
        text=uz.DOWNLOADING_NO_PERCENT,
    )

    async def progress_hook(pct: float, speed: str, eta: str):
        text = uz.DOWNLOADING_MEDIA.format(
            percent=pct,
            speed=speed if speed else "Hisoblanmoqda...",
            eta=eta if eta else "Biroz kuting",
        )
        await safe_edit_text(
            bot=callback.bot,
            chat_id=chat_id,
            message_id=status_msg_id,
            text=text,
        )

    try:
        # A) YouTube downloads
        if action.startswith("v_"):
            idx = int(action.split("_")[1])
            video_formats = [f for f in meta.formats if not f.is_audio]
            if idx >= len(video_formats):
                await safe_edit_text(
                    bot=callback.bot,
                    chat_id=chat_id,
                    message_id=status_msg_id,
                    text=uz.FORMAT_UNAVAILABLE,
                )
                return

            chosen_fmt = video_formats[idx]

            # Pre-check file size limit if known
            if chosen_fmt.effective_filesize and chosen_fmt.effective_filesize > settings.max_file_size_bytes:
                await safe_edit_text(
                    bot=callback.bot,
                    chat_id=chat_id,
                    message_id=status_msg_id,
                    text=uz.FILE_TOO_LARGE.format(
                        size_mb=chosen_fmt.effective_filesize / (1024 * 1024),
                        limit_mb=settings.max_file_size_mb,
                    ),
                )
                return

            file_path = await download_manager.download_media(
                url=meta.url,
                format_id=chosen_fmt.format_id,
                output_dir=task_dir,
                title=meta.title,
                author=meta.author,
                is_audio=False,
                is_mp3=False,
                progress_callback=progress_hook,
            )

            await safe_edit_text(
                bot=callback.bot,
                chat_id=chat_id,
                message_id=status_msg_id,
                text=uz.UPLOADING_TELEGRAM,
            )

            await telegram_delivery.deliver_single_file(
                bot=callback.bot,
                chat_id=chat_id,
                file_path=file_path,
                media_type=MediaType.VIDEO,
                title=meta.title,
                author=meta.author,
                duration=meta.duration,
                cache_key=cache_key,
                format_id=action,
            )

        elif action.startswith("a_"):
            idx = int(action.split("_")[1])
            audio_formats = [f for f in meta.formats if f.is_audio]
            if idx >= len(audio_formats):
                await safe_edit_text(
                    bot=callback.bot,
                    chat_id=chat_id,
                    message_id=status_msg_id,
                    text=uz.FORMAT_UNAVAILABLE,
                )
                return

            chosen_fmt = audio_formats[idx]
            is_mp3 = "mp3" in chosen_fmt.resolution.lower()

            file_path = await download_manager.download_media(
                url=meta.url,
                format_id=chosen_fmt.format_id,
                output_dir=task_dir,
                title=meta.title,
                author=meta.author,
                is_audio=True,
                is_mp3=is_mp3,
                progress_callback=progress_hook,
            )

            await safe_edit_text(
                bot=callback.bot,
                chat_id=chat_id,
                message_id=status_msg_id,
                text=uz.UPLOADING_TELEGRAM,
            )

            await telegram_delivery.deliver_single_file(
                bot=callback.bot,
                chat_id=chat_id,
                file_path=file_path,
                media_type=MediaType.AUDIO,
                title=meta.title,
                author=meta.author,
                duration=meta.duration,
                cache_key=cache_key,
                format_id=action,
            )

        # B) Pinterest downloads
        elif action in ("pin_photo", "pin_doc"):
            as_doc = (action == "pin_doc")
            item_url = meta.items[0].url if meta.items else meta.url
            ext = "jpg"
            out_file = task_dir / f"pinterest_pin.{ext}"

            file_path = await download_manager.download_direct_file(
                url=item_url,
                output_path=out_file,
                progress_callback=progress_hook,
            )

            await safe_edit_text(
                bot=callback.bot,
                chat_id=chat_id,
                message_id=status_msg_id,
                text=uz.UPLOADING_TELEGRAM,
            )

            await telegram_delivery.deliver_single_file(
                bot=callback.bot,
                chat_id=chat_id,
                file_path=file_path,
                media_type=MediaType.DOCUMENT if as_doc else MediaType.PHOTO,
                title=meta.title,
                author="Pinterest",
                as_document=as_doc,
                cache_key=cache_key,
                format_id=action,
            )

        elif action == "pin_vid":
            item_url = meta.items[0].url if meta.items else meta.url
            out_file = task_dir / "pinterest_video.mp4"

            if item_url.startswith("http") and ".mp4" in item_url:
                file_path = await download_manager.download_direct_file(
                    url=item_url,
                    output_path=out_file,
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
                bot=callback.bot,
                chat_id=chat_id,
                message_id=status_msg_id,
                text=uz.UPLOADING_TELEGRAM,
            )

            await telegram_delivery.deliver_single_file(
                bot=callback.bot,
                chat_id=chat_id,
                file_path=file_path,
                media_type=MediaType.VIDEO,
                title=meta.title,
                author="Pinterest",
                cache_key=cache_key,
                format_id=action,
            )

        # C) Instagram downloads
        elif action == "ig_vid":
            file_path = await download_manager.download_media(
                url=meta.url,
                format_id="best",
                output_dir=task_dir,
                title=meta.title,
                author=meta.author,
                progress_callback=progress_hook,
            )

            await safe_edit_text(
                bot=callback.bot,
                chat_id=chat_id,
                message_id=status_msg_id,
                text=uz.UPLOADING_TELEGRAM,
            )

            await telegram_delivery.deliver_single_file(
                bot=callback.bot,
                chat_id=chat_id,
                file_path=file_path,
                media_type=MediaType.VIDEO,
                title=meta.title,
                author=meta.author,
                duration=meta.duration,
                cache_key=cache_key,
                format_id=action,
            )

        elif action == "ig_carousel":
            await safe_edit_text(
                bot=callback.bot,
                chat_id=chat_id,
                message_id=status_msg_id,
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
                except Exception as down_err:
                    logger.warning(f"Error downloading carousel item {idx}: {down_err}")

            if downloaded_paths:
                await safe_edit_text(
                    bot=callback.bot,
                    chat_id=chat_id,
                    message_id=status_msg_id,
                    text=uz.UPLOADING_TELEGRAM,
                )
                caption = f"📸 <b>{meta.title}</b>\n👤 {meta.author}"
                await telegram_delivery.deliver_album(
                    bot=callback.bot,
                    chat_id=chat_id,
                    file_paths=downloaded_paths,
                    media_types=downloaded_types,
                    caption=caption,
                )

        # Delete status message on success
        try:
            await callback.bot.delete_message(chat_id=chat_id, message_id=status_msg_id)
        except Exception:
            pass

    except FileOversizedError as e:
        await safe_edit_text(
            bot=callback.bot,
            chat_id=chat_id,
            message_id=status_msg_id,
            text=uz.FILE_TOO_LARGE.format(
                size_mb=e.size_bytes / (1024 * 1024),
                limit_mb=settings.max_file_size_mb,
            ),
        )
    except Exception as e:
        logger.error(f"Download or delivery failed: {e}", exc_info=True)
        await safe_edit_text(
            bot=callback.bot,
            chat_id=chat_id,
            message_id=status_msg_id,
            text=uz.GENERIC_ERROR.format(error=str(e)[:80]),
        )
    finally:
        # Guarantee cleanup of temporary files
        cleanup_directory(task_dir)
