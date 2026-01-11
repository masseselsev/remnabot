from bot.services.payments.base import PaymentGateway
from bot.services.payments.stars import StarsGateway
from bot.services.payments.yookassa import YookassaGateway
from bot.services.payments.platega import PlategaGateway
from bot.services.payments.tribute import TributeGateway
from bot.config import config

class PaymentService:
    def __init__(self):
        self._gateways = {
            "pay_stars": StarsGateway(),
            "pay_yookassa": YookassaGateway(),
            "pay_platega": PlategaGateway(),
            "pay_tribute": TributeGateway(),
        }

    def get_gateway(self, method_key: str) -> PaymentGateway:
        return self._gateways.get(method_key)

payment_service = PaymentService()
