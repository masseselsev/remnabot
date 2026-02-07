from aiogram import Router, types, F
from aiogram.filters import CommandStart
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from bot.database.core import get_session
from bot.database import models
from bot.config import config
from fluent.runtime import FluentLocalization
from datetime import datetime, timezone, timedelta
from dateutil import parser

router = Router()

async def check_existing_accounts(user_id: int):
    """
    Searches for accounts by Telegram ID.
    Returns: (standard_account, manual_accounts_list)
    standard_account: Account with username "tg_{user_id}"
    manual_accounts_list: List of other accounts with matching telegramId
    """
    from bot.services.remnawave import api
    import structlog
    logger = structlog.get_logger()

    try:
        # Use search to find user by ID (more reliable than fetching all)
        users = await api.get_users(search=str(user_id))
        
        candidates = []
        if isinstance(users, list): candidates = users
        elif isinstance(users, dict):
             if 'response' in users:
                 r = users['response']
                 if isinstance(r, list): candidates = r
                 elif isinstance(r, dict):
                     candidates = r.get('users', []) or r.get('data', [])

        standard = None
        manual = []
        
        target_username = f"tg_{user_id}"
        
        # DEBUG
        print(f"DEBUG: check_existing_accounts candidates: {len(candidates)}")
        
        for u in candidates:
            # Check explicit telegramId match (robust) or username match
            tid = u.get('telegramId')
            uname = u.get('username')
            
            # API search is fuzzy, so verify ID or exact username
            is_match = False
            if str(tid) == str(user_id): is_match = True
            if uname == target_username: is_match = True
            
            if is_match:
                if uname == target_username:
                    standard = u
                else:
                    manual.append(u)
            
        return standard, manual
    except Exception as e:
        logger.error("check_accounts_error", error=str(e), user_id=user_id)
        return None, []

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
        # Flush to get ID if needed
        await session.flush()

    # Account Discovery (Auto-Link)
    found_manual_acc = None
    if not user.remnawave_uuid:
        std_acc, man_acc_list = await check_existing_accounts(message.from_user.id)
        if std_acc:
            user.remnawave_uuid = std_acc['uuid']
            # We don't need to notify "Linked", just proceed as normal
        elif man_acc_list:
            # Pick the first one for notification
            found_manual_acc = man_acc_list[0]
            
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

    # 1. Manual Account Discovery Notification
    if found_manual_acc:
         # Calculate expiry for display
         exp_date = "Unlimited"
         expire_at = found_manual_acc.get('expireAt')
         if expire_at:
             try:
                 dt = parser.isoparse(expire_at)
                 if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
                 msk_tz = timezone(timedelta(hours=3))
                 exp_date = dt.astimezone(msk_tz).strftime("%Y-%m-%d")
             except: pass
             
         msg_text = l10n.format_value("account-found-manual", {
             "username": found_manual.get('username', 'Unknown'),
             "tariff": "Manual/Imported", 
             "expire": exp_date
         })
         
         ikb = types.InlineKeyboardMarkup(inline_keyboard=[
             [types.InlineKeyboardButton(text=l10n.format_value("btn-create-new"), callback_data="req_trial_new")],
             [types.InlineKeyboardButton(text=l10n.format_value("btn-use-existing"), callback_data=f"link_acc_{found_manual['uuid']}")]
         ])
         await message.answer(msg_text, reply_markup=ikb, parse_mode="Markdown")

    # Check for active subscription (notify newly granted users)
    if user.remnawave_uuid:
        try:
             from bot.services.remnawave import api
             from html import escape
             from dateutil import parser
             from datetime import datetime, timezone, timedelta
             
             # Get API User
             rw_user = await api.get_user(user.remnawave_uuid)
             data = rw_user.get('response', rw_user)
             
             if not data: return 

             # Check Expiry
             expire_at = data.get('expireAt')
             is_active = False
             date_str = "Unlimited"
             
             if expire_at:
                 dt = parser.isoparse(expire_at)
                 if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
                 now_utc = datetime.now(timezone.utc)
                 
                 if dt > now_utc:
                     is_active = True
                     # Format Date
                     msk_tz = timezone(timedelta(hours=3))
                     date_str = dt.astimezone(msk_tz).strftime("%Y-%m-%d %H:%M MSK")
             
             if is_active:
                 # Get Tariff Name from DB (Last Paid Order)
                 stmt_order = select(models.Order).options(selectinload(models.Order.tariff)).where(
                    models.Order.user_id == user.id, 
                    models.Order.status == models.OrderStatus.PAID
                 ).order_by(models.Order.created_at.desc()).limit(1)
                 result_order = await session.execute(stmt_order)
                 last_order = result_order.scalar_one_or_none()
                 tariff_name = last_order.tariff.name if last_order and last_order.tariff else "Unknown"
                 
                 # Prepare Message
                 link = data.get('subscriptionUrl') or f"{config.remnawave_url}/sub/{user.remnawave_uuid}"
                 
                 msg = l10n.format_value("start-active-sub", {
                     "tariff": escape(tariff_name),
                     "date": date_str,
                     "link": link
                 })
                 await message.answer(msg, parse_mode="HTML")
                 
        except Exception:
            pass

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
                    found_user_data = raw
             except Exception:
                # If 404 or other error, assume user not found via UUID
                found_user_data = None
        
        if not found_user_data:
             std_acc, man_acc_list = await check_existing_accounts(user.id)
             
             if std_acc:
                 found_user_data = std_acc
                 user.remnawave_uuid = std_acc['uuid']
                 await session.commit()
                 
             elif man_acc_list:
                 # Found manual accounts but no standard one.
                 # Offer choice to user.
                 found_manual = man_acc_list[0]
                 
                 exp_date = "Unlimited"
                 expire_at = found_manual.get('expireAt')
                 if expire_at:
                     try:
                         dt = parser.isoparse(expire_at)
                         if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
                         msk_tz = timezone(timedelta(hours=3))
                         exp_date = dt.astimezone(msk_tz).strftime("%Y-%m-%d")
                     except: pass
                     
                 msg_text = l10n.format_value("account-found-manual", {
                     "username": found_manual.get('username', 'Unknown'),
                     "tariff": "Manual/Imported", 
                     "expire": exp_date
                 })
                 
                 ikb = types.InlineKeyboardMarkup(inline_keyboard=[
                     [types.InlineKeyboardButton(text=l10n.format_value("btn-create-new"), callback_data="req_trial_new")],
                     [types.InlineKeyboardButton(text=l10n.format_value("btn-use-existing"), callback_data=f"link_acc_{found_manual['uuid']}")]
                 ])
                 await message.answer(msg_text, reply_markup=ikb, parse_mode="Markdown")
                 return

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
                        f"{msg_link}\n{link}",
                        disable_web_page_preview=True
                     )
                     return
             
             # If found_user_data is None but we are here -> Fallthrough to create new order.
             pass

    except Exception as e:
        logger.error("trial_check_error", error=str(e))
        await message.answer("❌ Service temporarily unavailable. Please try again later.")
        return

    # Proceed to create order using helper
    await execute_trial_creation(message, session, l10n, user)

async def generate_profile_content(user_id, session, l10n):
    user = await session.get(models.User, user_id)
    if not user: return None, None
    
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
                
                msk_tz = timezone(timedelta(hours=3))
                date_str = dt.astimezone(msk_tz).strftime("%Y-%m-%d %H:%M MSK")
                
                now_utc = datetime.now(timezone.utc)
                if dt > now_utc:
                    formatted_status = l10n.format_value("profile-expiry", {"date": date_str})
                else:
                    formatted_status = l10n.format_value("subscription-expired", {"date": date_str})
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
            
        # Traffic Bar (Green -> Yellow -> Orange -> Red)
        bar_parts = []
        for i in range(5):
             low = i * 20
             high = (i + 1) * 20
             if percent >= high:
                 bar_parts.append("🟥")
             elif percent <= low:
                 bar_parts.append("🟩")
             elif (percent - low) < 10:
                 bar_parts.append("🟨")
             else:
                 bar_parts.append("🟧")
        bar_str = "".join(bar_parts)
            
        t_tariff = l10n.format_value("profile-tariff", {"name": tariff_name})
        t_traffic = l10n.format_value("profile-traffic", {"used": used_gb, "limit": limit_gb, "percent": percent, "bar": bar_str})
        
        traffic_info = f"\n{t_tariff}\n{t_traffic}"
        
        # Link for main account
        from bot.config import config
        main_link = found_user_data.get('subscriptionUrl')
        if not main_link:
             main_link = f"{config.remnawave_url}/sub/{user.remnawave_uuid}"
        
        t_link = l10n.format_value("profile-link", {"link": main_link})
        traffic_info += f"\n{t_link}"

    # Additional Accounts Visibility
    # DEBUG: Print to stdout so we can see in docker logs
    print(f"DEBUG: Generating profile for {user.id} ({user.username})")
    
    std_acc, manual_accs = await check_existing_accounts(user.id)
    print(f"DEBUG: check_existing_accounts returned: STD={std_acc is not None}, MANUAL={len(manual_accs)}")
    if manual_accs:
        print(f"DEBUG: Manual accs: {[m.get('username') for m in manual_accs]}")
        
    additional_accs = []
    current_uuid = user.remnawave_uuid
    print(f"DEBUG: Current UUID: {current_uuid}")
    
    # Add manual accounts if they are not current
    for m in manual_accs:
        muuid = m.get('uuid')
        print(f"DEBUG: Checking manual acc: {m.get('username')} uuid={muuid}")
        if muuid != current_uuid:
            additional_accs.append(m)
        else:
            print("DEBUG: Skipped matching UUID")
            
    # Add standard account if it exists but is not current
    if std_acc and std_acc.get('uuid') != current_uuid:
        additional_accs.append(std_acc)

    print(f"DEBUG: Final additional_accs count: {len(additional_accs)}")
        
    additional_info = ""
    if additional_accs:
        additional_info = "\n\n" + l10n.format_value("profile-additional-accounts") + "\n"
        for acc in additional_accs:
            u_name = acc.get('username', 'Unknown')
            
            # Expiry
            exp_str = l10n.format_value("subscription-none") # Default if missing
            if acc.get('expireAt'):
                try:
                    edt = parser.isoparse(acc.get('expireAt'))
                    if edt.tzinfo is None: edt = edt.replace(tzinfo=timezone.utc)
                    msk_tz = timezone(timedelta(hours=3))
                    date_str = edt.astimezone(msk_tz).strftime("%Y-%m-%d %H:%M MSK")
                    
                    now_utc = datetime.now(timezone.utc)
                    if edt > now_utc:
                        exp_str = l10n.format_value("profile-expiry", {"date": date_str})
                    else:
                        exp_str = l10n.format_value("subscription-expired", {"date": date_str})
                        
                except: pass
                
            # Traffic
            limit_bytes = acc.get('trafficLimitBytes') or 0
            used_bytes = acc.get('userTraffic', {}).get('usedTrafficBytes') or 0
            limit_gb = round(int(limit_bytes) / (1024**3), 1)
            used_gb = round(int(used_bytes) / (1024**3), 2)
            
            percent = 0
            if limit_bytes > 0:
                percent = round((used_bytes / limit_bytes) * 100, 1)
                
            bar_parts = []
            for i in range(5):
                 low = i * 20
                 high = (i + 1) * 20
                 if percent >= high:
                     bar_parts.append("🟥")
                 elif percent <= low:
                     bar_parts.append("🟩")
                 elif (percent - low) < 10:
                     bar_parts.append("🟨")
                 else:
                     bar_parts.append("🟧")
            bar_str = "".join(bar_parts)
                
            t_traffic = l10n.format_value("profile-traffic", {"used": used_gb, "limit": limit_gb, "percent": percent, "bar": bar_str})
            
            # Link
            from bot.config import config
            link = acc.get('subscriptionUrl')
            if not link:
                link = f"{config.remnawave_url}/sub/{acc.get('uuid')}"
            
            t_link = l10n.format_value("profile-link", {"link": link})
            
            additional_info += l10n.format_value("profile-account-item", {
                "username": u_name, 
                "expiry": exp_str,
                "traffic": t_traffic,
                "link": t_link
            }) + "\n"

    text = (
        f"{l10n.format_value('profile-id', {'id': user.id})}\n"
        f"{formatted_status}"
        f"{traffic_info}"
        f"{additional_info}"
    )
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=l10n.format_value("btn-devices"), callback_data="my_devices")],
        [types.InlineKeyboardButton(text="🌐 Language / Язык", callback_data="change_lang")]
    ])
    
    return text, kb

@router.message(F.text == "👤 Profile")
@router.message(F.text == "👤 Профиль")
async def process_profile(message: types.Message, session, l10n: FluentLocalization):
    text, kb = await generate_profile_content(message.from_user.id, session, l10n)
    if text:
        await message.answer(text, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)

@router.callback_query(F.data == "change_lang")
async def show_language_selector(callback: types.CallbackQuery, l10n: FluentLocalization):
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🇺🇸 English", callback_data="set_lang_en")],
        [types.InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang_ru")],
        [types.InlineKeyboardButton(text=l10n.format_value("btn-back"), callback_data="back_profile")]
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

@router.callback_query(F.data == "my_devices")
@router.callback_query(F.data.startswith("dev_acc_"))
async def show_devices_list(callback: types.CallbackQuery, session, l10n: FluentLocalization):
    user = await session.get(models.User, callback.from_user.id)
    if not user.remnawave_uuid:
        await callback.answer(l10n.format_value("subscription-none"), show_alert=True)
        return

    # 1. Determine target account UUID
    target_uuid = None
    if callback.data.startswith("dev_acc_"):
        target_uuid = callback.data.split("_", 2)[2]
    else:
        # Initial entry: Check if we need selection menu
        std_acc, manual_accs = await check_existing_accounts(user.id)
        all_accs = []
        if std_acc: all_accs.append(std_acc)
        all_accs.extend(manual_accs)
        
        # Deduplicate by UUID just in case
        unique_accs = {a['uuid']: a for a in all_accs}.values()
        all_accs = list(unique_accs)
        
        if len(all_accs) > 1:
            # Show Selection Menu
            kb_rows = []
            for acc in all_accs:
                 u_name = acc.get('username', 'Unknown')
                 uuid = acc.get('uuid')
                 kb_rows.append([types.InlineKeyboardButton(text=f"👤 {u_name}", callback_data=f"dev_acc_{uuid}")])
            
            kb_rows.append([types.InlineKeyboardButton(text=l10n.format_value("btn-back"), callback_data="back_profile")])
            await callback.message.edit_text(l10n.format_value("devices-select-account"), reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb_rows))
            return
        elif len(all_accs) == 1:
            target_uuid = all_accs[0]['uuid']
        else:
            # Fallback to current if something weird happens
            target_uuid = user.remnawave_uuid

    # 2. Show Devices for Target UUID
    from bot.services.remnawave import api
    
    try:
        devices = await api.get_user_devices(target_uuid)
    except Exception as e:
        devices = []
        
    # UUID prefix for context in callbacks
    # We use first 8 chars of UUID to save space in callback_data
    uuid_prefix = target_uuid[:8]
    # We store map in memory or just rely on prefix? 
    # Actually, we need full UUID for delete. But callback length limit (64 bytes).
    # UUID (36) + "del_dev_" (8) = 44. HWID is long.
    # We must trust that target_uuid is user.remnawave_uuid OR verify usage.
    # We will pass target_uuid in a simplified way or rely on a "current selection" state?
    # Stateless is better.
    # Let's try: dev_{uuid_part}_{hwid_part}
    # But wait, 64 bytes is tight. 
    # Strategy: Pass `dev_X<index>` where index maps to a cache? No, stateless.
    # Let's use `d_<uuid-prefix>_<shorthwid>`?
    # Allow full uuid lookup via prefix?
    # user.py has no cache.
    # Let's Assume: We pass `target_uuid` in button "Back" navigation, but for item details...
    # We can use `d_{uuid_prefix}_{short_hwid}` and search efficiently.
        
    if not devices:
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
             [types.InlineKeyboardButton(text=l10n.format_value("btn-back"), callback_data=f"my_devices")] 
        ])
        await callback.message.edit_text(l10n.format_value("devices-empty"), reply_markup=kb, parse_mode="HTML")
        return

    kb_rows = []
    msk_tz = timezone(timedelta(hours=3)) 

    for dev in devices:
        model = dev.get('deviceModel', 'Unknown')
        platform = dev.get('platform', 'Unknown')
        hwid = dev.get('hwid')
        updated_at = dev.get('updatedAt')
        
        time_str = "?"
        if updated_at:
             try:
                 dt = parser.isoparse(updated_at)
                 if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
                 time_str = dt.astimezone(msk_tz).strftime("%d.%m %H:%M")
             except: pass
        
        btn_text = f"{model} ({platform}) {time_str}"
        if len(btn_text) > 30: btn_text = btn_text[:29] + "…"
        
        # Format: dev_{uuid_head}_{hwid_head}
        # uuid_head = 8 chars. hwid for WG is usually Key.
        # Ensure we can exact match later.
        # Store minimal unique data. 
        # Actually, if we just pass index in list? No, race condition.
        # Pass first 8 chars of HWID.
        cb_data = f"dev_{target_uuid[:8]}_{hwid[:10]}"
        kb_rows.append([types.InlineKeyboardButton(text=btn_text, callback_data=cb_data)])
    
    # Back button logic
    # If explicitly viewing account, back goes to "my_devices" (which checks list again)
    kb_rows.append([types.InlineKeyboardButton(text=l10n.format_value("btn-back"), callback_data="my_devices")])
    
    msg_text = l10n.format_value("devices-title")
    await callback.message.edit_text(msg_text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb_rows), parse_mode="Markdown")

@router.callback_query(F.data.startswith("dev_"))
async def show_device_details(callback: types.CallbackQuery, session, l10n: FluentLocalization):
    # Format: dev_{uuid_head}_{hwid_head}
    parts = callback.data.split("_")
    if len(parts) < 3: return # Validation
    
    uuid_part = parts[1]
    hwid_part = parts[2]
    
    user = await session.get(models.User, callback.from_user.id)
    if not user: return
    
    # Resolve full UUID from all possible accounts
    std_acc, manual_accs = await check_existing_accounts(user.id)
    all_accs = []
    if std_acc: all_accs.append(std_acc)
    all_accs.extend(manual_accs)
    
    target_uuid = None
    for acc in all_accs:
        if acc['uuid'].startswith(uuid_part):
            target_uuid = acc['uuid']
            break
            
    if not target_uuid:
        await callback.answer("❌ Account context lost.", show_alert=True)
        return
    
    # Fetch devices for THAT account
    from bot.services.remnawave import api
    try:
        devices = await api.get_user_devices(target_uuid)
    except:
        devices = []
    
    target_dev = None
    for d in devices:
        h = d.get('hwid')
        if h and h.startswith(hwid_part): # HWID part match
             target_dev = d
             break
    
    if not target_dev:
        await callback.answer(l10n.format_value("devices-empty"), show_alert=True)
        # Return to list of THAT account
        # We simulate callback with dev_acc_{uuid}
        cb = types.CallbackQuery(
            id=callback.id, 
            from_user=callback.from_user, 
            message=callback.message, 
            chat_instance=callback.chat_instance,
            data=f"dev_acc_{target_uuid}"
        )
        await show_devices_list(cb, session, l10n)
        return

    model = target_dev.get('deviceModel', 'Unknown')
    platform = target_dev.get('platform', 'Unknown')
    updated_at = target_dev.get('updatedAt')
    
    msk_tz = timezone(timedelta(hours=3))
    last_act = "Unknown"
    if updated_at:
         dt = parser.isoparse(updated_at)
         if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
         last_act = dt.astimezone(msk_tz).strftime("%d.%m.%Y %H:%M:%S")

    text = l10n.format_value("devices-item", {
        "model": model,
        "platform": platform,
        "last_active": last_act
    })
    
    # Delete using full HWID context: del_dev_{uuid_prefix}_{hwid_prefix}
    # Wait, for delete we need full hwid? 
    # API delete needs: hwid (full), userUuid (full).
    # We have full userUuid (target_uuid).
    # We DO NOT have full HWID in callback data if we truncated it previously?
    # Ah, `target_dev` HAS full HWID.
    # So we can pass full HWID in next step?
    # Length limit: 64. 
    # del_dev_ (8) + uuid_head(8) + _ (1) + hwid_head (10) = 27 chars. Safe.
    # No, we need context for CONFIRMATION.
    # Let's pass `del_{uuid_head}_{hwid_head}`. 
    # Then re-fetch in confirm step to get full HWID again. Ideally reliable.
    
    del_cb = f"del_{uuid_part}_{hwid_part}"
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=l10n.format_value("btn-delete-device"), callback_data=del_cb)],
        [types.InlineKeyboardButton(text=l10n.format_value("btn-back"), callback_data=f"dev_acc_{target_uuid}")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("del_"))
async def ask_delete_device(callback: types.CallbackQuery, session, l10n: FluentLocalization):
    # Format: del_{uuid_part}_{hwid_part}
    parts = callback.data.split("_")
    if len(parts) < 3: return
    
    uuid_part = parts[1]
    hwid_part = parts[2]
    
    user = await session.get(models.User, callback.from_user.id)
    # Resolve Account
    std_acc, manual_accs = await check_existing_accounts(user.id)
    all_accs = []
    if std_acc: all_accs.append(std_acc)
    all_accs.extend(manual_accs)
    
    target_uuid = None
    for acc in all_accs:
        if acc['uuid'].startswith(uuid_part):
            target_uuid = acc['uuid']
            break
            
    if not target_uuid:
        await callback.answer("❌ Account context lost.", show_alert=True)
        return

    # Fetch device to get Name + Full HWID
    model_name = "Device"
    full_hwid = None
    
    from bot.services.remnawave import api
    try:
         devices = await api.get_user_devices(target_uuid)
         for d in devices:
             h = d.get('hwid')
             if h and h.startswith(hwid_part):
                 model_name = d.get('deviceModel', 'Device')
                 full_hwid = h
                 break
    except: pass
    
    if not full_hwid:
         await callback.answer(l10n.format_value("device-delete-fail"), show_alert=True)
         return

    # Callback for confirmation: cdel_{uuid_part}_{hwid_part}
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text=l10n.format_value("btn-yes"), callback_data=f"cdel_{uuid_part}_{hwid_part}"),
            types.InlineKeyboardButton(text=l10n.format_value("btn-no"), callback_data=f"dev_{uuid_part}_{hwid_part}")
        ]
    ])
    await callback.message.edit_text(l10n.format_value("device-confirm-delete", {"model": model_name}), reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data.startswith("cdel_"))
async def process_delete_device_wrapper(callback: types.CallbackQuery, session, l10n: FluentLocalization):
     # Format: cdel_{uuid_part}_{hwid_part}
     parts = callback.data.split("_")
     if len(parts) < 3: return
     
     uuid_part = parts[1]
     hwid_part = parts[2]
     
     user = await session.get(models.User, callback.from_user.id)
     
     # Resolve Account
     std_acc, manual_accs = await check_existing_accounts(user.id)
     all_accs = []
     if std_acc: all_accs.append(std_acc)
     all_accs.extend(manual_accs)
    
     target_uuid = None
     for acc in all_accs:
        if acc['uuid'].startswith(uuid_part):
            target_uuid = acc['uuid']
            break
            
     if not target_uuid:
         await callback.answer("❌ Account context lost.", show_alert=True)
         return

     from bot.services.remnawave import api
     
     # Re-resolve Full HWID (Safe approach)
     full_hwid = None
     try:
          devices = await api.get_user_devices(target_uuid)
          for d in devices:
              h = d.get('hwid')
              if h and h.startswith(hwid_part):
                  full_hwid = h
                  break
     except: pass
     
     if not full_hwid:
          await callback.answer(l10n.format_value("device-delete-fail"), show_alert=True)
          return

     try:
         await api.delete_user_device(full_hwid, target_uuid)
         await callback.answer(l10n.format_value("device-deleted"), show_alert=True)
     except Exception:
         await callback.answer(l10n.format_value("device-delete-fail"), show_alert=True)
     
     # Return to list
     cb = types.CallbackQuery(
            id=callback.id, 
            from_user=callback.from_user, 
            message=callback.message, 
            chat_instance=callback.chat_instance,
            data=f"dev_acc_{target_uuid}"
        )
     await show_devices_list(cb, session, l10n)

@router.callback_query(F.data == "back_profile")
async def back_to_profile(callback: types.CallbackQuery, session, l10n: FluentLocalization):
    text, kb = await generate_profile_content(callback.from_user.id, session, l10n)
    if text:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)
    else:
        await callback.answer("Error loading profile", show_alert=True)


@router.callback_query(F.data.startswith("link_acc_"))
async def link_manual_account(callback: types.CallbackQuery, session, l10n: FluentLocalization):
    uuid = callback.data.split("_", 2)[2]
    user = await session.get(models.User, callback.from_user.id)
    if user:
        user.remnawave_uuid = uuid
        await session.commit()
    
    await callback.answer(l10n.format_value("trial-activated"), show_alert=True)
    
    # Refresh logic similar to back_to_profile
    await callback.message.delete()
    wrapper = types.Message(
        message_id=0, 
        date=datetime.now(), 
        chat=callback.message.chat, 
        from_user=callback.from_user
    )
    await process_profile(wrapper, session, l10n)

@router.callback_query(F.data == "req_trial_new")
async def request_new_trial_explicit(callback: types.CallbackQuery, session, l10n: FluentLocalization):
    user = await session.get(models.User, callback.from_user.id)
    # We call the helper. 
    # Note: execute_trial_creation expects a messageable object that has .answer()
    # callback.message is such object.
    await execute_trial_creation(callback.message, session, l10n, user)
    await callback.answer()

async def execute_trial_creation(messageable, session, l10n: FluentLocalization, user: models.User):
    import structlog
    from bot.services.remnawave import api
    from bot.config import config
    
    # Find trial tariff
    stmt = select(models.Tariff).where(models.Tariff.is_trial == True, models.Tariff.is_active == True)
    result = await session.execute(stmt)
    tariff = result.scalar_one_or_none()
    
    if not tariff:
        # Auto-create fallback if trial tariff is missing but logic requires it
        from bot.services.settings import SettingsService
        settings = await SettingsService.get_trial_settings()
        
        tariff = models.Tariff(
            name="Free Trial",
            price_rub=0.0,
            price_stars=0,
            price_usd=0.0,
            duration_days=settings['days'],
            traffic_limit_gb=int(settings['traffic']),
            squad_uuid=settings['squad_uuid'] if settings['squad_uuid'] not in ["0", "None"] else None,
            is_trial=True,
            is_active=True
        )
        session.add(tariff)
        await session.commit()

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
             
             # Fetch settings for correct display
             from bot.services.settings import SettingsService
             settings = await SettingsService.get_trial_settings()
             duration_days = settings.get("days", tariff.duration_days)
             
             expire_at_str = data.get('expireAt')
             # Use dynamic days
             expire_display = f"{duration_days} Days"
             
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
              
        await messageable.answer(
            f"{msg_activated}\n\n"
            f"{msg_traffic}\n"
            f"{msg_expires}\n\n"
            f"{msg_link}\n{link}",
            disable_web_page_preview=True
        )
    else:
        await messageable.answer("❌ Failed to activate trial. Please contact support.")


