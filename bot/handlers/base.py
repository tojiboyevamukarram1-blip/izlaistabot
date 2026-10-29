from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot.config import settings
from bot.downloader.manager import download_manager
from bot.locales import uz
from bot.services.cache import cache_service

base_router = Router()


@base_router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command."""
    await message.answer(uz.START_MESSAGE, parse_mode="HTML")


@base_router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command."""
    await message.answer(uz.HELP_MESSAGE, parse_mode="HTML")


@base_router.message(Command("status"))
async def cmd_status(message: Message):
    """Handle /status command."""
    active = await download_manager.get_active_downloads()
    text = uz.STATUS_MESSAGE.format(
        active_downloads=active,
        max_downloads=settings.max_concurrent_downloads,
        cache_status=cache_service.status_string,
        max_size_mb=settings.max_file_size_mb,
        max_duration_min=settings.max_duration_seconds // 60,
    )
    await message.answer(text, parse_mode="HTML")


@base_router.message(Command("cancel"))
async def cmd_cancel(message: Message):
    """Handle /cancel command."""
    await message.answer(uz.CANCEL_SUCCESS)
