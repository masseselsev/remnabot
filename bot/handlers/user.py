from aiogram import Router, types, F
from aiogram.filters import CommandStart
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from bot.database.core import get_session
from bot.database import models
from bot.config import config
from fluent.runtime import FluentLocalization

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message, l10n: FluentLocalization, session):
    # Create or update user
    stmt = select(models.User).where(models.User.id == message.from_user.id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = models.User(
            id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            language_code="ru" if message.from_user.language_code == "ru" else "en"
        )
        session.add(user)
        await session.commit()

    # Welcome message
    text = l10n.format_value("start-welcome", {"name": message.from_user.first_name})
    
    # Keyboard
    kb = [
        [types.KeyboardButton(text=l10n.format_value("btn-shop")), types.KeyboardButton(text=l10n.format_value("btn-profile"))],
        [types.KeyboardButton(text=l10n.format_value("btn-trial")), types.KeyboardButton(text=l10n.format_value("btn-support"))]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

    
    await message.answer(text, reply_markup=keyboard)

@router.message(F.text == "🎁 Try for free")
@router.message(F.text == "🎁 Попробовать бесплатно")
async def process_trial(message: types.Message, session, l10n: FluentLocalization):
    # Fetch user from DB
    user = await session.get(models.User, message.from_user.id)
    
    # Check if user used trial via Remnawave
    from bot.services.remnawave import api
    import structlog
    logger = structlog.get_logger()

    # We allow the process to start. The fulfillment logic handles the actual "trial used" check properly now 
    # (checking Remnawave tags) but we want to fail fast if we KNOW they used it.
    # However, to be "Source of Truth", we should query API here.
    
    # Check Remnawave status
    try:
        if user.is_trial_used:
             # Local DB says used. Check if expired or just active.
             # We should probably trust DB to prevent re-issue, 
             # but we still want to show "Active" status if they click it again.
             pass

        # We need UUID to check user. If we don't have it locally, we search.
        rw_uuid = user.remnawave_uuid
        
        found_user_data = None
        if rw_uuid:
             try:
                raw_user = await api.get_user(rw_uuid)
                # Unwrap if needed
                if raw_user and 'response' in raw_user:
                    found_user_data = raw_user['response']
                else:
                    found_user_data = raw_user
             except Exception:
                # If 404 or other error, assume user not found via UUID
                found_user_data = None
        
        if not found_user_data:
             # Search by username
             users = await api.get_users(search=f"tg_{user.id}")
             
             # Parse result (nested response handling reused or simplified)
             candidates = []
             if isinstance(users, list): candidates = users
             elif isinstance(users, dict):
                 if 'response' in users:
                     if 'users' in users['response']: candidates = users['response']['users']
                     elif 'internalSquads' in users['response']: candidates = users['response']['internalSquads'] 
                     elif 'data' in users['response']: candidates = users['response']['data']
             
             logger.info("username_search_debug", 
                        search_query=f"tg_{user.id}", 
                        raw_type=str(type(users)),
                        candidates_count=len(candidates))

             for u in candidates:
                 u_name = u.get('username')
                 target = f"tg_{user.id}"
                 # logger.debug("checking_candidate", candidate=u_name, target=target)
                 if u_name == target:
                     found_user_data = u
                     break
        
        if not found_user_data:
             # Search by username logic (already done above, assuming found_user_data is result)
             pass

        # === Verification Block ===
        tags = ""
        if found_user_data:
            tags = found_user_data.get('tag') or ""

        logger.info("trial_check_debug", 
                   user_id=user.id,
                   rw_uuid=rw_uuid,
                   found_in_api=bool(found_user_data),
                   local_is_used=user.is_trial_used, 
                   api_tags=tags)

        # 1. Block conditions: Tag exists OR Local DB says used
        if (found_user_data and "TRIAL_YES" in tags) or user.is_trial_used:
             
             # Determine Expiry
             expire_dt = None
             from dateutil import parser
             from datetime import datetime, timedelta, timezone
             
             if found_user_data:
                 expire_at_str = found_user_data.get('expireAt')
                 if expire_at_str:
                     try:
                         expire_dt = parser.isoparse(expire_at_str)
                     except: pass
             
             # If no API expiry but local says used, we have limited options.
             # If user.is_trial_used is True but API returned Nothing (404), 
             # it means user was deleted manually from panel.
             # In this case, we SHOULD treat them as new users? Or block?
             # If we block: they can never use bot again.
             # If we allow: they circumvent trial limits.
             # Let's BLOCK for now, as safety first.
             # BUT enable "Active" display if we can recover data (we can't).
             
             now_utc = datetime.now(timezone.utc)
             is_expired = False
             
             if expire_dt:
                 if expire_dt.tzinfo is None:
                     expire_dt = expire_dt.replace(tzinfo=timezone.utc)
                 if expire_dt < now_utc:
                     is_expired = True
             elif user.is_trial_used and not found_user_data:
                  # CASE: Local DB says used, but API says User Not Found (Deleted).
                  # User Request: Rely on API as source of truth to avoid desync.
                  # Action: Allow re-creation (pass through blocks).
                  # We simply do nothing here, falling through to order creation.
                  pass 
             
             if found_user_data: # Only show info if we have data
                 date_str = "Unlimited"
                 if expire_dt:
                     msk_tz = timezone(timedelta(hours=3))
                     expire_msk = expire_dt.astimezone(msk_tz)
                     formatted_date = expire_msk.strftime("%Y-%m-%d %H:%M MSK")
                     
                     # Calculate remaining days (fractional)
                     delta = expire_dt - now_utc
                     total_seconds = delta.total_seconds()
                     
                     if total_seconds <= 0:
                         time_str = l10n.format_value("trial-less-day") # Or 0 days
                     else:
                         days_float = total_seconds / 86400
                         time_str = l10n.format_value("trial-days", {"count": f"{days_float:.1f}"})
                         
                     date_str = f"{time_str} ({formatted_date})"

                 if is_expired:
                     await message.answer(l10n.format_value("trial-expired", {"date": date_str}))
                     return
                 else:
                     link = found_user_data.get('subscriptionUrl')
                     if not link:
                          link = f"{config.remnawave_url}/sub/{found_user_data.get('uuid')}"
                     
                     traffic_bytes = found_user_data.get('trafficLimitBytes') or 0
                     traffic_gb = round(int(traffic_bytes) / (1024**3), 1)
                     
                     msg_active = l10n.format_value("trial-active")
                     msg_traffic = l10n.format_value("trial-traffic", {"gb": traffic_gb})
                     msg_expires = l10n.format_value("trial-expires", {"date": date_str})
                     msg_link = l10n.format_value("trial-link-caption")
                     
                     await message.answer(
                        f"{msg_active}\n\n"
                        f"{msg_traffic}\n"
                        f"{msg_expires}\n\n"
                        f"{msg_link}\n{link}"
                     )
                     return
             
             # If found_user_data is None but we are here -> Fallthrough to create new order.
             pass

        # If we are here -> Proceed to create order
        pass

    except Exception as e:
        logger.error("trial_check_error", error=str(e))
        await message.answer("❌ Service temporarily unavailable. Please try again later.")
        return

    # Find trial tariff
    stmt = select(models.Tariff).where(models.Tariff.is_trial == True, models.Tariff.is_active == True)
    result = await session.execute(stmt)
    tariff = result.scalar_one_or_none()
    
    if not tariff:
        await message.answer("😔 No trial available currently.")
        return

    # Create dummy order and fulfill
    from bot.services.orders import create_order, fulfill_order
    order = await create_order(user.id, tariff.id, 0.0, models.PaymentProvider.MANUAL, session)
    
    success = await fulfill_order(order.id, session)
    if success:
        # Get connection info (Subscription URL)
        # Fetch fresh user data to get the correct subscription link
        try:
             rw_user = await api.get_user(user.remnawave_uuid)
             # Extract data handling nesting
             data = rw_user.get('response') if 'response' in rw_user else rw_user
             
             link = data.get('subscriptionUrl')
             if not link:
                 link = f"{config.remnawave_url}/sub/{user.remnawave_uuid}"
            
             # Parse details
             traffic_bytes = data.get('trafficLimitBytes') or data.get('dataLimit') or 0
             traffic_gb = round(int(traffic_bytes) / (1024**3), 1)
             
             expire_at_str = data.get('expireAt')
             expire_display = f"{tariff.duration_days} Days"
             
             if expire_at_str:
                 try:
                     from dateutil import parser
                     from datetime import timedelta, timezone
                     
                     dt = parser.isoparse(expire_at_str)
                     # Ensure UTC awareness
                     if dt.tzinfo is None:
                         dt = dt.replace(tzinfo=timezone.utc)
                         
                     # Convert to MSK (UTC+3)
                     msk_tz = timezone(timedelta(hours=3))
                     dt_msk = dt.astimezone(msk_tz)
                     
                     date_str = dt_msk.strftime("%Y-%m-%d %H:%M MSK")
                     expire_display += f" ({date_str})"
                 except Exception:
                     pass

        except Exception:
             link = f"{config.remnawave_url}/sub/{user.remnawave_uuid}"
             traffic_gb = tariff.traffic_limit_gb
             expire_display = f"{tariff.duration_days} Days"
             
        msg_activated = l10n.format_value("trial-activated")
        msg_traffic = l10n.format_value("trial-traffic", {"gb": traffic_gb})
        msg_expires = l10n.format_value("trial-expires", {"date": expire_display})
        msg_link = l10n.format_value("trial-link-caption")
              
        await message.answer(
            f"{msg_activated}\n\n"
            f"{msg_traffic}\n"
            f"{msg_expires}\n\n"
            f"{msg_link}\n{link}"
        )
    else:
        await message.answer("❌ Failed to activate trial. Please contact support.")

@router.message(F.text == "👤 Profile")
@router.message(F.text == "👤 Профиль")
async def process_profile(message: types.Message, session, l10n: FluentLocalization):
    user = await session.get(models.User, message.from_user.id)
    
    # Fetch status from Remnawave
    from bot.services.remnawave import api
    from dateutil import parser
    from datetime import datetime, timezone, timedelta

    rw_uuid = user.remnawave_uuid
    found_user_data = None
    
    if rw_uuid:
        try:
            raw = await api.get_user(rw_uuid)
            if raw and 'response' in raw:
                found_user_data = raw['response']
            else:
                found_user_data = raw
        except:
            found_user_data = None
    
    # Tariff Name from local DB
    stmt = select(models.Order).options(selectinload(models.Order.tariff)).where(
        models.Order.user_id == user.id, 
        models.Order.status == models.OrderStatus.PAID
    ).order_by(models.Order.created_at.desc()).limit(1)
    
    result = await session.execute(stmt)
    last_order = result.scalar_one_or_none()
    tariff_name = last_order.tariff.name if last_order and last_order.tariff else "Unknown"

    formatted_status = l10n.format_value("subscription-none")
    traffic_info = ""
    
    if found_user_data:
        # Expiry
        expire_at_str = found_user_data.get('expireAt')
        if expire_at_str:
            try:
                dt = parser.isoparse(expire_at_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                
                now_utc = datetime.now(timezone.utc)
                if dt > now_utc:
                    msk_tz = timezone(timedelta(hours=3))
                    date_str = dt.astimezone(msk_tz).strftime("%Y-%m-%d %H:%M MSK")
                    formatted_status = l10n.format_value("subscription-active", {"date": date_str})
            except:
                pass
        
        # Traffic
        limit_bytes = found_user_data.get('trafficLimitBytes') or 0
        used_bytes = found_user_data.get('userTraffic', {}).get('usedTrafficBytes') or 0
        
        limit_gb = round(int(limit_bytes) / (1024**3), 1)
        used_gb = round(int(used_bytes) / (1024**3), 2)
        
        percent = 0
        if limit_bytes > 0:
            percent = round((used_bytes / limit_bytes) * 100, 1)
            
        t_tariff = l10n.format_value("profile-tariff", {"name": tariff_name})
        t_traffic = l10n.format_value("profile-traffic", {"used": used_gb, "limit": limit_gb, "percent": percent})
        
        traffic_info = f"\n{t_tariff}\n{t_traffic}"

    text = (
        f"{l10n.format_value('profile-title')}\n"
        f"{l10n.format_value('profile-id', {'id': user.id})}\n"
        f"{l10n.format_value('profile-balance', {'balance': user.balance})}\n"
        f"{formatted_status}"
        f"{traffic_info}"
    )
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🌐 Language / Язык", callback_data="change_lang")]
    ])
    
    await message.answer(text, reply_markup=kb)

@router.callback_query(F.data == "change_lang")
async def show_language_selector(callback: types.CallbackQuery):
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🇺🇸 English", callback_data="set_lang_en")],
        [types.InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang_ru")],
        [types.InlineKeyboardButton(text="🔙 Cancel", callback_data="delete_msg")]
    ])
    await callback.message.edit_text("Select language / Выберите язык:", reply_markup=kb)

@router.callback_query(F.data == "delete_msg")
async def delete_msg(callback: types.CallbackQuery):
    await callback.message.delete()

@router.callback_query(F.data.startswith("set_lang_"))
async def set_language(callback: types.CallbackQuery, session):
    lang_code = callback.data.split("_")[2]
    user = await session.get(models.User, callback.from_user.id)
    if user:
        user.language_code = lang_code
        await session.commit()
    
    if lang_code == "ru":
        text = "✅ Язык изменен на Русский.\nМеню обновлено."
        btn_shop = "🛒 Купить VPN"
        btn_profile = "👤 Профиль"
        btn_trial = "🎁 Попробовать бесплатно"
        btn_support = "🆘 Поддержка"
    else:
        text = "✅ Language changed to English.\nMenu updated."
        btn_shop = "🛒 Buy VPN"
        btn_profile = "👤 Profile"
        btn_trial = "🎁 Try for free"
        btn_support = "🆘 Support"

    # Update Reply Keyboard
    kb = [
        [types.KeyboardButton(text=btn_shop), types.KeyboardButton(text=btn_profile)],
        [types.KeyboardButton(text=btn_trial), types.KeyboardButton(text=btn_support)]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    await callback.message.delete()
    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


