import logging
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.config import settings
from bot.locales import uz
from bot.services.cache import cache_service

logger = logging.getLogger(__name__)


class ThrottlingMiddleware(BaseMiddleware):
    """Rate-limiting middleware using Redis or memory sliding window."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user_id = None

        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if user_id:
            # Bypass rate limit for owner and admin users
            if user_id == settings.owner_id or user_id in settings.admin_ids:
                return await handler(event, data)

            allowed = await cache_service.check_rate_limit(
                user_id=user_id,
                max_requests=settings.rate_limit_requests,
                window=settings.rate_limit_window,
            )

            if not allowed:
                logger.warning(f"User {user_id} exceeded rate limit")
                if isinstance(event, Message):
                    await event.answer(
                        uz.RATE_LIMIT_HIT.format(seconds=settings.rate_limit_window),
                        parse_mode="HTML",
                    )
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        uz.RATE_LIMIT_HIT.format(seconds=settings.rate_limit_window),
                        show_alert=True,
                    )
                return

        return await handler(event, data)
