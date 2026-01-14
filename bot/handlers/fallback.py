from aiogram import Router, types
from fluent.runtime import FluentLocalization
from aiogram.filters import StateFilter

router = Router()

# Catch all messages (content_types=all, state=None by default unless specified)
# We want to catch everything that fell through other routers.
# IMPORTANT: By default aiogram handlers without state filter work for ANY state? 
# No, usually default is any state. But we want to be safe.
# Actually, if other routers checked for specific states and failed, and this one has no filter, it matches.

@router.message()
async def fallback_handler(message: types.Message, l10n: FluentLocalization):
    if message.chat.type == "private":
        try:
             text = l10n.format_value("bot-unknown-command")
        except:
             text = "ℹ️ Please select a menu item."
             
        await message.answer(text)
