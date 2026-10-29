import asyncio
import logging
import os
import signal
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from bot.config import settings
from bot.handlers import base_router, callback_router, media_router
from bot.middlewares import AuthMiddleware, ThrottlingMiddleware
from bot.security.sanitizer import cleanup_directory
from bot.services.cache import cache_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("media_bot")
_health_runner: web.AppRunner | None = None


async def start_health_server() -> None:
    """Starts a minimal HTTP health check server if PORT environment variable is set (Render/Cloud)."""
    global _health_runner
    port_str = os.getenv("PORT")
    if not port_str:
        return

    try:
        port = int(port_str)
        app = web.Application()

        async def ping_handler(request: web.Request) -> web.Response:
            return web.Response(text="Bot is running OK", content_type="text/plain")

        app.router.add_get("/", ping_handler)
        app.router.add_get("/health", ping_handler)

        _health_runner = web.AppRunner(app)
        await _health_runner.setup()
        site = web.TCPSite(_health_runner, "0.0.0.0", port)
        await site.start()
        logger.info(f"🌐 Cloud Health Check HTTP server listening on 0.0.0.0:{port}")
    except Exception as e:
        logger.warning(f"Failed to start health check server: {e}")


async def on_startup(bot: Bot) -> None:
    """Startup initialization tasks."""
    logger.info("Initializing bot services...")
    settings.temp_dir.mkdir(parents=True, exist_ok=True)
    await start_health_server()
    await cache_service.connect()
    await bot.delete_webhook(drop_pending_updates=True)
    bot_user = await bot.get_me()
    logger.info(f"Bot started successfully: @{bot_user.username} (ID: {bot_user.id})")
    if settings.owner_id:
        logger.info(f"🔒 PRIVATE BOT MODE: Enabled for OWNER_ID={settings.owner_id}")
    else:
        logger.warning("⚠️ OWNER_ID is not set! Bot will accept requests from all users.")
    logger.info(f"Cache status: {cache_service.status_string}")
    logger.info(f"Temp directory: {settings.temp_dir.resolve()}")


async def on_shutdown(bot: Bot) -> None:
    """Graceful shutdown tasks."""
    global _health_runner
    logger.info("Shutting down bot services...")
    if _health_runner:
        await _health_runner.cleanup()
    await cache_service.close()
    await bot.session.close()
    cleanup_directory(settings.temp_dir)
    logger.info("Shutdown completed cleanly.")


async def main() -> None:
    """Main application entrypoint."""
    if not settings.bot_token or settings.bot_token.startswith("123456789:ABC"):
        logger.error(
            "BOT_TOKEN is missing or set to placeholder! "
            "Please configure a valid BOT_TOKEN in .env or environment variables."
        )
        sys.exit(1)

    session = AiohttpSession(timeout=300.0)
    bot = Bot(
        token=settings.bot_token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Register middlewares (Auth first, then throttling)
    auth = AuthMiddleware()
    dp.message.middleware(auth)
    dp.callback_query.middleware(auth)

    throttling = ThrottlingMiddleware()
    dp.message.middleware(throttling)
    dp.callback_query.middleware(throttling)

    # Register routers (order matters: base commands -> callbacks -> media URL detector)
    dp.include_router(base_router)
    dp.include_router(callback_router)
    dp.include_router(media_router)

    # Register startup and shutdown lifecycle
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Process interrupted. Exiting.")
