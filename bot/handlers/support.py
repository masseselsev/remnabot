from aiogram import Router, types, F
from fluent.runtime import FluentLocalization
from aiogram.fsm.context import FSMContext
import structlog

logger = structlog.get_logger()
router = Router()

from aiogram.filters import StateFilter

@router.message(F.text == "🆘 Support (incl. project 🙃)", StateFilter("*"))
@router.message(F.text == "🆘 Поддержка (в т.ч. проекта 🙃)", StateFilter("*"))
async def cmd_support(message: types.Message, state: FSMContext, l10n: FluentLocalization):
    await state.clear()
    # Support Link (Invite link provided by user)
    support_link = "https://t.me/+dP0XLHQv-f8zMjk6"
    
    msg_text = l10n.format_value("support-help-text", {"link": support_link})
    btn_text = l10n.format_value("support-btn-label")
    
    # DEBUG: Help identify what locale is being used
    debug_locale = getattr(l10n, "locales", ["unknown"])[0] if hasattr(l10n, "locales") else "unknown"
    logger.info("support_handler_invoked", msg_text=msg_text, locale=debug_locale, user_id=message.from_user.id)
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=btn_text, url=support_link)]
    ])
    
    await message.answer(msg_text, reply_markup=kb)

