import abc
import structlog
import uuid
import asyncio
from functools import partial
from yookassa import Configuration, Payment
from bot.config import config
from bot.database import models

logger = structlog.get_logger()

class PaymentService(abc.ABC):
    @abc.abstractmethod
    async def create_payment(self, amount: float, description: str, metadata: dict) -> tuple[str, str]:
        """Returns (payment_id, confirmation_url)"""
        pass
        
    @abc.abstractmethod
    async def check_payment(self, payment_id: str) -> bool:
        """Returns True if paid"""
        pass

class YooKassaService(PaymentService):
    def __init__(self):
        if config.yookassa_shop_id and config.yookassa_secret_key:
            Configuration.account_id = config.yookassa_shop_id
            Configuration.secret_key = config.yookassa_secret_key.get_secret_value()
        else:
            logger.warning("yookassa_credentials_missing", msg="Please set YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY in .env")

    async def create_payment(self, amount: float, description: str, metadata: dict) -> tuple[str, str]:
        idempotency_key = str(uuid.uuid4())
        
        payment_data = {
            "amount": {
                "value": f"{amount:.2f}",
                "currency": "RUB"
            },
            "confirmation": {
                "type": "redirect",
                "return_url": config.bot_link
            },
            "capture": True,
            "description": description,
            "metadata": metadata
        }
        
        try:
            loop = asyncio.get_running_loop()
            payment = await loop.run_in_executor(None, partial(Payment.create, payment_data, idempotency_key))
            return payment.id, payment.confirmation.confirmation_url
        except Exception as e:
            logger.error("yookassa_create_error", error=str(e))
            raise e

    async def check_payment(self, payment_id: str) -> bool:
        try:
            loop = asyncio.get_running_loop()
            payment = await loop.run_in_executor(None, partial(Payment.find_one, payment_id))
            return payment.status == "succeeded"
        except Exception as e:
             logger.error("yookassa_check_error", error=str(e))
             return False

class StarsService(PaymentService):
    async def create_payment(self, amount: float, description: str, metadata: dict) -> tuple[str, str]:
        # Stars payment doesn't require API call to create, we just create an Invoice ID (payload)
        payment_id = str(uuid.uuid4())
        # No external URL for stars, the bot sends the invoice directly
        return payment_id, ""

    async def check_payment(self, payment_id: str) -> bool:
        # Check logic is handled via pre_checkout_query and successful_payment updates usually.
        # But if we need to verify manually, we can't easily with Stars API unless we store state.
        # For now, presume handled by updates.
        return False

def get_payment_service(provider: models.PaymentProvider):
    if provider == models.PaymentProvider.YOOKASSA:
        return YooKassaService()
    elif provider == models.PaymentProvider.STARS:
        return StarsService()
    
    # Fallback or error
    if provider == models.PaymentProvider.MANUAL:
         pass
         
    return YooKassaService() # Default to YooKassa for now
