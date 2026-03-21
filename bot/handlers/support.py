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
    # ID provided for DM: 1073332473875
    # Since we can't open link from reply keyboard, we send a message with an inline button.
    # Format: tg://user?id=1073332473875
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="💬 Open Support Chat / Открыть чат", url="tg://user?id=1073332473875")]
    ])
    
    msg_text = (
        "По всем вопросам обращайтесь в чат поддержки:\n"
        "For any questions, please contact support chat:"
    )
    await message.answer(msg_text, reply_markup=kb)
