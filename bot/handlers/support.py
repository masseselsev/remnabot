from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from fluent.runtime import FluentLocalization
from sqlalchemy import select
from bot.database.core import get_session
from bot.database import models
from bot.config import config
import structlog

logger = structlog.get_logger()
router = Router()

class SupportStates(StatesGroup):
    active = State()

# --- User Side ---

@router.message(F.text == "🆘 Support")
@router.message(F.text == "🆘 Поддержка")
async def cmd_support(message: types.Message, state: FSMContext, session, l10n: FluentLocalization):
    await state.set_state(SupportStates.active)
    
    kb = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text=l10n.format_value("btn-cancel"))]],
        resize_keyboard=True
    )
    
    # Fetch history
    stmt = select(models.SupportMessage).where(
        models.SupportMessage.user_id == message.from_user.id
    ).order_by(models.SupportMessage.created_at.desc()).limit(7)
    
    result = await session.execute(stmt)
    history = result.scalars().all()
    
    history_text = ""
    if history:
        recap_title = l10n.format_value("support-recap-title")
        history_text = f"\n\n{recap_title}\n"
        
        for msg in reversed(history):
             sender = l10n.format_value("support-you") if msg.sender == "user" else l10n.format_value("support-agent")
             content = msg.text if msg.text else l10n.format_value("support-media")
             history_text += f"▫️ {sender}: {content}\n"
    
    await message.answer(l10n.format_value("support-welcome") + history_text, reply_markup=kb)

@router.message(Command("start"), SupportStates.active)
@router.message(F.text == "❌ Cancel")
@router.message(F.text == "❌ Отмена")
async def cmd_cancel(message: types.Message, state: FSMContext, l10n: FluentLocalization):
    await state.clear()
    
    # Restore Main Menu
    btn_shop = l10n.format_value("btn-shop")
    btn_profile = l10n.format_value("btn-profile")
    btn_trial = l10n.format_value("btn-trial")
    btn_support = l10n.format_value("btn-support")
    
    kb = [
        [types.KeyboardButton(text=btn_shop), types.KeyboardButton(text=btn_profile)],
        [types.KeyboardButton(text=btn_trial), types.KeyboardButton(text=btn_support)]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    await message.answer(l10n.format_value("support-exit"), reply_markup=keyboard)


@router.message(SupportStates.active)
async def process_support_message(message: types.Message, bot: Bot, session, l10n: FluentLocalization):
    # Forward to Admin Group
    try:
        # We use copy_message to avoid "Forward from hidden user" issues where we can't reply easily without ID mapping.
        # But we also add a header with User Info to help admins identify context.
        
        user_info = f"Ticket from {message.from_user.full_name} (ID: {message.from_user.id})"
        if message.from_user.username:
            user_info += f" @{message.from_user.username}"
            
        # Send header first? Or Reply to header?
        # Let's send the message and reply to it? Or just send copy.
        # If we send copy, it looks like it came from the bot.
        
        # Strategy:
        # 1. Send copy of user message to Admin Group.
        # 2. Store mapping (AdminMsgID -> UserID).
        # 3. Admins reply to that copy.
        
        # To make it prettier, we can assume admins see the copied message.
        # But admins need to know WHO sent it.
        # So maybe we send a text message: "#Ticket User: ...\nContent: ..." if text?
        # But what if image?
        
        # Best practice: Forward (if possible) OR Copy with caption modification?
        # If we Copy, we lose "Forwarded from". But we gain control.
        
        # Let's try: Copy Message. And immediately reply to it with "User Info" button or text?
        # No, simpler:
        # Send Copy.
        # Save ID.
        # Append User Link to caption? (Only works for media/text).
        
        # Simple reliable way:
        # Send text header: "📩 New Message from User ID {id}"
        # Then forward/copy the message?
        # That creates 2 messages for 1 user message. Spammy.
        
        # Let's just USE COPY_MESSAGE.
        # And we rely on our DB mapping to know who it is.
        # We can add a "Quote" of the user in the admin chat?
        
        # Let's do this:
        # copy_message to Admin Group.
        # If it's text, we PREPEND info? "User (ID): \n text".
        # If it's media, we append to caption?
        
        # Actually, let's just Forward.
        # Even if user is hidden, `message.forward_from` is None.
        # But `SupportMessage` maps AdminMessageID -> UserID.
        # So when admin replies to the Forward, we lookup our DB.
        # We DON'T need `forward_from` in the reply handler if we have the mapping!
        # Because we map the *message in admin chat* to the user.
        
        forwarded = await message.forward(config.admin_group_id)
        
        # Save mapping
        mapping = models.SupportMessage(
            admin_message_id=forwarded.message_id,
            user_id=message.from_user.id,
            user_message_id=message.message_id,
            text=message.text or message.caption,
            sender="user"
        )
        session.add(mapping)
        await session.commit()
        
        await message.answer(l10n.format_value("support-sent"))
        
    except Exception as e:
        logger.error("support_forward_error", error=str(e))
        await message.answer("❌ Error sending message. Please try again.")

# --- Admin Side ---

@router.message(F.chat.id == config.admin_group_id, F.reply_to_message)
async def process_admin_reply(message: types.Message, bot: Bot, session, l10n: FluentLocalization):
    # Check if reply is to a ticket message
    reply = message.reply_to_message
    
    stmt = select(models.SupportMessage).where(models.SupportMessage.admin_message_id == reply.message_id)
    result = await session.execute(stmt)
    ticket_msg = result.scalar_one_or_none()
    
    if not ticket_msg:
        # Reply to something else (e.g. admin chat discussion), ignore.
        return
        
    # It is a reply to a user ticket
    user_id = ticket_msg.user_id
    
    try:
        # Send reply to user
        # We can just copy the admin's message back to the user.
        # Or format it "Support: ..."
        
        if message.text:
            text_content = f"👨‍💻 Support: {message.text}"
            sent_msg = await bot.send_message(user_id, text_content)
        else:
            # Media logic: copy
            sent_msg = await message.copy_to(user_id)
            
        # Save Admin Message to DB for history
        admin_reply_entry = models.SupportMessage(
            admin_message_id=message.message_id, # The reply message in admin group
            user_id=user_id,
            user_message_id=sent_msg.message_id, # The message sent to user
            text=message.text or message.caption,
            sender="admin"
        )
        session.add(admin_reply_entry)
        await session.commit()
            
        # Optional: React to admin message to confirm delivery
        # await message.react([types.ReactionTypeEmoji(emoji="👍")]) 
        # (Requires newer aiogram)
        
    except Exception as e:
        logger.error("support_reply_error", error=str(e))
        await message.reply(f"❌ Failed to send reply to user {user_id}: {e}")
