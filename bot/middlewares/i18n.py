from typing import Any, Dict, Awaitable, Callable, Union
from aiogram import BaseMiddleware
from aiogram.types import Update, User
from fluent.runtime import FluentLocalization, FluentResourceLoader
from bot.database.core import async_session
from bot.database import models
from sqlalchemy import select

class I18nMiddleware(BaseMiddleware):
    def __init__(self):
        loader = FluentResourceLoader("bot/services/locales/{locale}")
        self.l10n_en = FluentLocalization(["en"], ["messages.ftl"], loader)
        self.l10n_ru = FluentLocalization(["ru"], ["messages.ftl"], loader)

    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any],
    ) -> Any:
        user: Union[User, None] = data.get("event_from_user")
        
        if not user:
            return await handler(event, data)

        # Get user language from DB or fallback to Telegram language
        async with async_session() as session:
            db_user = await session.scalar(select(models.User).where(models.User.id == user.id))
            
            if db_user:
                lang_code = db_user.language_code
            else:
                lang_code = user.language_code if user.language_code == "ru" else "en"
                # We do NOT create user here, strict separation, handlers should do get_or_create if needed 
                # OR we can do it here for convenience. Let's stick to handler logic for creation or explicit middleware.
                # Actually, for I18n it's better to just know the lang.
        
        # Inject localization
        if lang_code == "ru":
            data["l10n"] = self.l10n_ru
        else:
            data["l10n"] = self.l10n_en
            
        return await handler(event, data)
