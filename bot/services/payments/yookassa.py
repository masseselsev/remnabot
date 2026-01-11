from bot.services.payments.base import PaymentGateway
import uuid

class YookassaGateway(PaymentGateway):
    async def create_payment(self, amount: float, currency: str, description: str, metadata: dict) -> tuple[str, str]:
        # Implementation would go here using yookassa SDK or API
        # return payment_id, confirmation_url
        pid = str(uuid.uuid4())
        return pid, "https://yookassa.ru/checkout/placeholder"

    async def check_payment(self, payment_id: str) -> bool:
        return True
