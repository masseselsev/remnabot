from aiogram import Router, types, F
from fluent.runtime import FluentLocalization
from bot.database import models
import structlog

logger = structlog.get_logger()
router = Router()

@router.message(F.text == "🆘 Support")
@router.message(F.text == "🆘 Поддержка")
async def cmd_support(message: types.Message, l10n: FluentLocalization):
    # Support Link (Invite link provided by user)
    # Since we can't open link from reply keyboard, we send a message with an inline button.
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="💬 Поддержка / Support", url="https://t.me/+dP0XLHQv-f8zMjk6")]
    ])
    
    msg_text = (
        "Для получения технической поддержки перейдите сюда: https://t.me/+dP0XLHQv-f8zMjk6\n"
        "и напишите в личные сообщения канала."
    )
    await message.answer(msg_text, reply_markup=kb)
