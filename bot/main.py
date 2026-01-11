import asyncio
import structlog
from aiogram import Bot, Dispatcher
from bot.config import config
from bot.database.core import init_db
from bot.handlers import user, admin, shop, support
from bot.middlewares.i18n import I18nMiddleware
from bot.middlewares.db import DbSessionMiddleware

from bot.logging_setup import setup_logging

from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web
from urllib.parse import urlparse

logger = structlog.get_logger()

async def main():
    setup_logging()
    await init_db()
    
    bot = Bot(token=config.bot_token.get_secret_value())
    dp = Dispatcher()
    
    # Register middlewares
    dp.update.middleware(DbSessionMiddleware())
    dp.update.middleware(I18nMiddleware())
    
    # Register routers (handlers)
    dp.include_router(support.router)
    dp.include_router(user.router)
    dp.include_router(shop.router)
    dp.include_router(admin.router)

    if config.webhook_url:
        logger.info("Starting in WEBHOOK mode", url=config.webhook_url)
        
        # Determine path from URL
        webhook_path = urlparse(config.webhook_url).path
        if not webhook_path or webhook_path == "":
            webhook_path = "/"
            
        await bot.set_webhook(config.webhook_url, drop_pending_updates=True)
        
        app = web.Application()
        
        webhook_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
        )
        webhook_handler.register(app, path=webhook_path)
        
        setup_application(app, dp, bot=bot)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host=config.webhook_host, port=config.webhook_port)
        await site.start()
        
        logger.info("Webhook server running", host=config.webhook_host, port=config.webhook_port, path=webhook_path)
        
        # Keep app running
        await asyncio.Event().wait()
    else:
        logger.info("Starting in POLLING mode")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
