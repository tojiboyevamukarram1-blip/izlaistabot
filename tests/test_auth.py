from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from aiogram.types import CallbackQuery, Message, User

from bot.config import settings
from bot.locales import uz
from bot.middlewares.auth import AuthMiddleware


@pytest.mark.asyncio
async def test_auth_middleware_owner_allowed():
    middleware = AuthMiddleware()
    owner_id = 111222333

    with patch.object(settings, "owner_id", owner_id):
        # Create mock Message from owner
        mock_user = MagicMock(spec=User)
        mock_user.id = owner_id
        mock_user.username = "owner_user"

        mock_message = MagicMock(spec=Message)
        mock_message.from_user = mock_user

        handler = AsyncMock(return_value="OK")
        result = await middleware(handler, mock_message, {})

        assert result == "OK"
        handler.assert_awaited_once_with(mock_message, {})


@pytest.mark.asyncio
async def test_auth_middleware_non_owner_rejected():
    middleware = AuthMiddleware()
    owner_id = 111222333
    stranger_id = 999888777

    with patch.object(settings, "owner_id", owner_id):
        mock_user = MagicMock(spec=User)
        mock_user.id = stranger_id
        mock_user.username = "stranger_user"
        mock_user.full_name = "Stranger"

        mock_message = MagicMock(spec=Message)
        mock_message.from_user = mock_user
        mock_message.answer = AsyncMock()

        handler = AsyncMock(return_value="OK")
        result = await middleware(handler, mock_message, {})

        # Handler should NOT be called
        handler.assert_not_called()
        # Message answer should be called with ACCESS_DENIED
        mock_message.answer.assert_awaited_once_with(uz.ACCESS_DENIED, parse_mode="HTML")
        assert result is None


@pytest.mark.asyncio
async def test_auth_middleware_callback_rejected():
    middleware = AuthMiddleware()
    owner_id = 111222333
    stranger_id = 555444333

    with patch.object(settings, "owner_id", owner_id):
        mock_user = MagicMock(spec=User)
        mock_user.id = stranger_id
        mock_user.username = "stranger"

        mock_cb = MagicMock(spec=CallbackQuery)
        mock_cb.from_user = mock_user
        mock_cb.answer = AsyncMock()

        handler = AsyncMock()
        await middleware(handler, mock_cb, {})

        handler.assert_not_called()
        mock_cb.answer.assert_awaited_once_with(uz.ACCESS_DENIED, show_alert=True)
