from aiohttp import web
from yookassa.domain.notification import WebhookNotification
from bot.services.orders import fulfill_order
from bot.database.core import get_session
import structlog

logger = structlog.get_logger()

async def handle_yookassa(request: web.Request):
    try:
        body = await request.json()
        logger.info("yookassa_webhook", body=body)
        
        notification = WebhookNotification(body)
        event = notification.event
        object = notification.object
        
        if event == "payment.succeeded":
            payment_id = object.id
            metadata = object.metadata
            order_id = int(metadata.get("order_id", 0))
            
            if order_id > 0:
                async with get_session() as session:
                    await fulfill_order(order_id, session, payment_id=payment_id)
                    
        return web.Response(text="OK")
    except Exception as e:
        logger.error("yookassa_webhook_error", error=str(e))
        return web.Response(status=500)
