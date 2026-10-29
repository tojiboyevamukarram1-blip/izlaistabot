import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.config import settings
from bot.locales import uz

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """Enforces owner-only access when OWNER_ID is configured."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if settings.owner_id is None:
            # If no owner_id configured, allow execution
            return await handler(event, data)

        user_id = None
        user_name = "unknown"

        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
            user_name = event.from_user.username or event.from_user.full_name
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id
            user_name = event.from_user.username or event.from_user.full_name

        if user_id != settings.owner_id:
            logger.warning(
                f"Unauthorized access rejected: user_id={user_id}, username=@{user_name}"
            )
            if isinstance(event, Message):
                await event.answer(uz.ACCESS_DENIED, parse_mode="HTML")
            elif isinstance(event, CallbackQuery):
                await callback_alert(event, uz.ACCESS_DENIED)
            return

        return await handler(event, data)


async def callback_alert(callback: CallbackQuery, text: str):
    try:
        await callback.answer(text, show_alert=True)
    except Exception:
        pass
