from typing import Any, Dict, Awaitable, Callable
from aiogram import BaseMiddleware
from aiogram.types import Update
from bot.database.core import async_session

class DbSessionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        async with async_session() as session:
            data["session"] = session
            return await handler(event, data)
