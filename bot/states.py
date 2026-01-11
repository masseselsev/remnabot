from aiogram.fsm.state import State, StatesGroup

class ShopState(StatesGroup):
    selecting_tariff = State()
    entering_promo = State()
    selecting_payment = State()
    waiting_payment = State()
