from bot.services.payments.base import PaymentGateway
import uuid

class TributeGateway(PaymentGateway):
    async def create_payment(self, amount: float, currency: str, description: str, metadata: dict) -> tuple[str, str]:
        # Implementation would go here
        pid = str(uuid.uuid4())
        return pid, "https://tribute.tg/checkout/placeholder"

    async def check_payment(self, payment_id: str) -> bool:
        return True
