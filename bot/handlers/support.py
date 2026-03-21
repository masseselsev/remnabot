from aiogram import Router, types, F
from fluent.runtime import FluentLocalization
from bot.database import models
import structlog

logger = structlog.get_logger()
router = Router()

@router.message(F.text == "🆘 Support")
@router.message(F.text == "🆘 Поддержка")
async def cmd_support(message: types.Message, l10n: FluentLocalization):
    # Support Link
    # ID provided: -1003332473875
    # Since we can't open link from reply keyboard, we send a message with an inline button.
    # Note: Private channels use https://t.me/c/<id_without_100>/999999999 (or 1)
    # But usually a join link is better. For now we use the ID as reference. 
    # Link: https://t.me/c/3332473875/1
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="💬 Open Support Chat / Открыть чат", url="https://t.me/c/3332473875/1")]
    ])
    
    msg_text = (
        "По всем вопросам обращайтесь в чат поддержки:\n"
        "For any questions, please contact support chat:"
    )
    await message.answer(msg_text, reply_markup=kb)
