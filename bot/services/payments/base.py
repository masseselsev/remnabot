from abc import ABC, abstractmethod
from typing import Optional

class PaymentGateway(ABC):
    @abstractmethod
    async def create_payment(
        self, 
        amount: float, 
        currency: str, 
        description: str, 
        metadata: dict
    ) -> tuple[str, str]: 
        """Returns (payment_id, payment_url/invoice)"""
        pass

    @abstractmethod
    async def check_payment(self, payment_id: str) -> bool:
        pass
