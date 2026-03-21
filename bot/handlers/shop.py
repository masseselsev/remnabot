from aiogram import Router, types, F
from fluent.runtime import FluentLocalization
import structlog

logger = structlog.get_logger()
router = Router()

@router.message(F.text == "🛒 Buy VPN")
@router.message(F.text == "🛒 Купить VPN")
async def show_tariffs(message: types.Message, l10n: FluentLocalization):
    await message.answer("🛒 Temporary unavailable / Временно недоступно")
