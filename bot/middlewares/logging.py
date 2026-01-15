from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
import structlog
import time

logger = structlog.get_logger()

class StructLoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # 1. Extract User Info
        user = data.get("event_from_user")
        
        # Bind context variables (these will appear in ALL logs within this request)
        if user:
            structlog.contextvars.bind_contextvars(
                user_id=user.id,
                username=user.username,
                full_name=user.full_name
            )
        
        # 2. Extract Event Details
        event_type = "unknown"
        event_details = {}
        
        if isinstance(event, Message):
            event_type = "message"
            if event.text:
                event_details["text"] = event.text
            elif event.web_app_data:
                event_details["web_app"] = event.web_app_data.data
        elif isinstance(event, CallbackQuery):
            event_type = "callback"
            event_details["data"] = event.data

        # 3. Log Start
        start_time = time.time()
        logger.info(
            "update_started", 
            event_type=event_type, 
            **event_details
        )
        
        try:
            # 4. Process Handler
            result = await handler(event, data)
            
            # 5. Log Success
            process_time = time.time() - start_time
            logger.info("update_finished", duration=f"{process_time:.3f}s")
            return result
            
        except Exception as e:
            # 6. Log Error
            logger.error("update_failed", error=str(e), exc_info=True)
            raise e
        finally:
            # 7. Cleanup Context
            structlog.contextvars.clear_contextvars()
