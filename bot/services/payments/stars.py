from bot.services.payments.base import PaymentGateway
import uuid

class StarsGateway(PaymentGateway):
    async def create_payment(self, amount: float, currency: str, description: str, metadata: dict) -> tuple[str, str]:
        # For Stars, we return a link to proper invoice bot or internal invoice
        # Since this is a bot, we usually send invoice message.
        # But this interface demands URL.
        # Stars are handling differently (send_invoice method).
        # We might need to refactor our abstraction or return a special "action" object.
        # For now, let's just return a dummy string to print.
        pid = str(uuid.uuid4())
        return pid, "https://t.me/invoice/stars-mock"

    async def check_payment(self, payment_id: str) -> bool:
        return True
