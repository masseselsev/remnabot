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
from aiogram.fsm.context import FSMContext
from bot.services.users import UserService
from bot.services.settings import SettingsService
import structlog

router = Router()

logger = structlog.get_logger()

def get_traffic_bar(percent: float) -> str:
    """
    Logic: 5 blocks (20% each).
    Each 20% block color matches the REMAINING capacity in that block:
    - 20-16 remaining: Green 🟩
    - 15-11 remaining: Yellow 🟨
    - 10-6 remaining: Orange 🟧
    - 5-0 remaining: Red 🟥
    Full used blocks to the left are Red 🟥.
    Full unused blocks to the right are Green 🟩.
    """
    bar = []
    for i in range(5):
        block_start = i * 20
        block_end = (i + 1) * 20
        
        if percent >= block_end:
            # Entirely used
            bar.append("🟥")
        elif percent <= block_start:
            # Entirely unused
            bar.append("🟩")
        else:
            # Current block (partially used)
            used_in_block = percent - block_start
            remaining_in_block = 20 - used_in_block
            
            if remaining_in_block >= 16:
                bar.append("🟩")
            elif remaining_in_block >= 11:
                bar.append("🟨")
            elif remaining_in_block >= 6:
                bar.append("🟧")
            else:
                bar.append("🟥")
    return "".join(bar)

async def check_existing_accounts(user_id: int):
    """
    Searches for accounts by Telegram ID.
    Returns: (standard_account, manual_accounts_list)
    standard_account: Account with username "tg_{user_id}"
    manual_accounts_list: List of other accounts with matching telegramId
    """
    from bot.services.remnawave import api
    try:
        # Attempt direct lookup by Telegram ID first
        candidates = []
        try:
            direct_user = await api.get_user_by_telegram_id(user_id)
            if isinstance(direct_user, list):
                candidates = direct_user
            elif direct_user and isinstance(direct_user, dict) and (direct_user.get('uuid') or direct_user.get('username')):
                candidates = [direct_user]
                
            if not candidates:
                raise ValueError("Empty response")
        except Exception:
            # Fallback to search
            resp = await api.get_users(search=str(user_id))
            if isinstance(resp, list):
                candidates = resp
            elif isinstance(resp, dict):
                candidates = resp.get('users') or resp.get('data') or resp.get('items') or []
        
        standard = None
        manual = []
        target_username = f"tg_{user_id}"
        
        for u in candidates:
            tid = u.get('telegramId')
            uname = u.get('username')
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
async def cmd_start(message: types.Message, state: FSMContext, session, l10n: FluentLocalization):
    user = await UserService.get_or_create_user(message.from_user.id, message.from_user.username)
    
    # Account Discovery (Auto-Link)
    found_manual_acc = None
    if not user.remnawave_uuid:
        std_acc, man_acc_list = await check_existing_accounts(message.from_user.id)
        if std_acc:
            user.remnawave_uuid = std_acc['uuid']
        elif man_acc_list:
            found_manual_acc = man_acc_list[0]
            
    await session.commit()

    # Welcome message from settings
    lang_code = l10n._locales[0] if hasattr(l10n, '_locales') else 'ru'
    welcome_setting = await SettingsService.get_setting(f"welcome_msg_{lang_code}")
    
    if not welcome_setting:
        fallback_msg = "Welcome, {$name}!" if lang_code == 'en' else "Добро пожаловать, {$name}!"
        welcome_text = fallback_msg.replace("{$name}", message.from_user.first_name)
    else:
        welcome_text = welcome_setting.replace("{$name}", message.from_user.first_name)
    
    # Keyboard
    btn_shop = l10n.format_value("btn-shop")
    btn_profile = l10n.format_value("btn-profile")
    btn_trial = l10n.format_value("btn-trial")
    btn_support = l10n.format_value("btn-support")
    
    kb = [
        [types.KeyboardButton(text=btn_shop), types.KeyboardButton(text=btn_profile)],
        [types.KeyboardButton(text=btn_trial), types.KeyboardButton(text=btn_support)]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="HTML")

    # Manual Account Discovery Notification
    if found_manual_acc:
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
             "username": found_manual_acc.get('username', 'Unknown'),
             "tariff": "Manual/Imported", 
             "expire": exp_date
         })
         
         ikb = types.InlineKeyboardMarkup(inline_keyboard=[
             [types.InlineKeyboardButton(text=l10n.format_value("btn-create-new"), callback_data="req_trial_new")],
             [types.InlineKeyboardButton(text=l10n.format_value("btn-use-existing"), callback_data=f"link_acc_{found_manual_acc['uuid']}")]
         ])
         await message.answer(msg_text, reply_markup=ikb, parse_mode="Markdown")

    # Check for ALL active subscriptions
    try:
        from bot.services.remnawave import api
        from html import escape
        from dateutil import parser
        from datetime import datetime, timezone, timedelta
        
        std_acc, manual_accs = await check_existing_accounts(user.id)
        all_accs = []
        if std_acc: all_accs.append(std_acc)
        all_accs.extend(manual_accs)
        
        # Deduplicate
        unique_accs = list({a['uuid']: a for a in all_accs}.values())
        
        if unique_accs:
            now_utc = datetime.now(timezone.utc)
            msk_tz = timezone(timedelta(hours=3))
            
            # Filter only active ones
            active_list = []
            for acc in unique_accs:
                expire_at = acc.get('expireAt')
                if not expire_at:
                    active_list.append(acc)
                else:
                    dt = parser.isoparse(expire_at)
                    if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
                    if dt > now_utc:
                        active_list.append(acc)
            
            if active_list:
                msg_lines = [l10n.format_value("start-active-sub-title")]
                
                for idx, acc in enumerate(active_list, 1):
                    exp_at = acc.get('expireAt')
                    exp_str = l10n.format_value("subscription-none")
                    if exp_at:
                        try:
                            edt = parser.isoparse(exp_at)
                            if edt.tzinfo is None: edt = edt.replace(tzinfo=timezone.utc)
                            date_str = edt.astimezone(msk_tz).strftime("%Y-%m-%d %H:%M MSK")
                            exp_str = l10n.format_value("profile-expiry", {"date": date_str})
                        except: pass
                    else:
                        exp_str = l10n.format_value("profile-expiry", {"date": "Unlimited"})
                        
                    # Traffic
                    limit_bytes = acc.get('trafficLimitBytes') or 0
                    used_bytes = acc.get('userTraffic', {}).get('usedTrafficBytes') or 0
                    limit_gb = round(int(limit_bytes) / (1024**3), 1)
                    used_gb = round(int(used_bytes) / (1024**3), 2)
                    percent = round((used_bytes / limit_bytes) * 100, 1) if limit_bytes > 0 else 0
                    
                    bar_str = get_traffic_bar(percent)
                    traffic_str = l10n.format_value("profile-traffic", {"used": used_gb, "limit": limit_gb, "percent": percent, "bar": bar_str})
                    link = acc.get('subscriptionUrl') or f"{config.remnawave_url}/sub/{acc['uuid']}"
                    link_str = l10n.format_value("profile-link", {"link": link})
                    uname = acc.get('username', 'Unknown')
                    
                    item = l10n.format_value("start-active-sub-item", {
                        "index": idx,
                        "username": escape(uname),
                        "expiry": exp_str,
                        "traffic": traffic_str,
                        "link": link_str
                    })
                    msg_lines.append(item)

                await message.answer("\n".join(msg_lines), parse_mode="HTML", disable_web_page_preview=True)

    except Exception as e:
        logger.debug("start_active_subs_info_failed", error=str(e))

@router.message(F.text.in_(["🎁 Try for free", "🎁 Попробовать бесплатно"]))
async def process_trial(message: types.Message, session, l10n: FluentLocalization):
    user = await session.get(models.User, message.from_user.id)
    from bot.services.remnawave import api
    try:
        rw_uuid = user.remnawave_uuid
        found_user_data = None
        if rw_uuid:
             try:
                found_user_data = await api.get_user(rw_uuid)
             except: pass
        
        if not found_user_data:
             std_acc, man_acc_list = await check_existing_accounts(user.id)
             if std_acc:
                 found_user_data = std_acc
                 user.remnawave_uuid = std_acc['uuid']
                 await session.commit()
             elif man_acc_list:
                 found_manual = man_acc_list[0]
                 return

        tags = found_user_data.get('tag') or "" if found_user_data else ""
        if (found_user_data and "TRIAL_YES" in tags) or user.is_trial_used:
             return

    except Exception as e:
        logger.error("trial_check_error", error=str(e))
        return

async def generate_profile_content(user_id, session, l10n):
    user = await session.get(models.User, user_id)
    if not user: return None, None
    from bot.services.remnawave import api
    rw_uuid = user.remnawave_uuid
    found_user_data = None
    if rw_uuid:
        try:
            found_user_data = await api.get_user(rw_uuid)
        except: pass
    
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
        expire_at_str = found_user_data.get('expireAt')
        if expire_at_str:
            try:
                dt = parser.isoparse(expire_at_str)
                if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
                msk_tz = timezone(timedelta(hours=3))
                date_str = dt.astimezone(msk_tz).strftime("%Y-%m-%d %H:%M MSK")
                now_utc = datetime.now(timezone.utc)
                if dt > now_utc:
                    formatted_status = l10n.format_value("profile-expiry", {"date": date_str})
                else:
                    formatted_status = l10n.format_value("subscription-expired", {"date": date_str})
            except: pass
        
        limit_bytes = found_user_data.get('trafficLimitBytes') or 0
        used_bytes = found_user_data.get('userTraffic', {}).get('usedTrafficBytes') or 0
        limit_gb = round(int(limit_bytes) / (1024**3), 1)
        used_gb = round(int(used_bytes) / (1024**3), 2)
        percent = round((used_bytes / limit_bytes) * 100, 1) if limit_bytes > 0 else 0
        bar_str = get_traffic_bar(percent)
        t_tariff = l10n.format_value("profile-tariff", {"name": tariff_name})
        t_traffic = l10n.format_value("profile-traffic", {"used": used_gb, "limit": limit_gb, "percent": percent, "bar": bar_str})
        traffic_info = f"\n{t_tariff}\n{t_traffic}"
        main_link = found_user_data.get('subscriptionUrl') or f"{config.remnawave_url}/sub/{user.remnawave_uuid}"
        traffic_info += f"\n{l10n.format_value('profile-link', {'link': main_link})}"

    std_acc, manual_accs = await check_existing_accounts(user.id)
    additional_accs = [m for m in manual_accs if m.get('uuid') != user.remnawave_uuid]
    if std_acc and std_acc.get('uuid') != user.remnawave_uuid:
        additional_accs.append(std_acc)
        
    additional_info = ""
    if additional_accs:
        additional_info = "\n\n" + l10n.format_value("profile-additional-accounts") + "\n"
        for acc in additional_accs:
            exp_str = l10n.format_value("subscription-none")
            if acc.get('expireAt'):
                try:
                    edt = parser.isoparse(acc.get('expireAt'))
                    if edt.tzinfo is None: edt = edt.replace(tzinfo=timezone.utc)
                    msk_tz = timezone(timedelta(hours=3))
                    date_str = edt.astimezone(msk_tz).strftime("%Y-%m-%d %H:%M MSK")
                    if edt > datetime.now(timezone.utc):
                        exp_str = l10n.format_value("profile-expiry", {"date": date_str})
                    else:
                        exp_str = l10n.format_value("subscription-expired", {"date": date_str})
                except: pass
            limit_bytes = acc.get('trafficLimitBytes') or 0
            used_bytes = acc.get('userTraffic', {}).get('usedTrafficBytes') or 0
            limit_gb = round(int(limit_bytes) / (1024**3), 1)
            used_gb = round(int(used_bytes) / (1024**3), 2)
            percent = round((used_bytes / limit_bytes) * 100, 1) if limit_bytes > 0 else 0
            bar_str = get_traffic_bar(percent)
            t_traffic = l10n.format_value("profile-traffic", {"used": used_gb, "limit": limit_gb, "percent": percent, "bar": bar_str})
            link = acc.get('subscriptionUrl') or f"{config.remnawave_url}/sub/{acc.get('uuid')}"
            additional_info += l10n.format_value("profile-account-item", {
                "username": acc.get('username', 'Unknown'), 
                "expiry": exp_str,
                "traffic": t_traffic,
                "link": l10n.format_value("profile-link", {"link": link})
            }) + "\n"

    text = f"{l10n.format_value('profile-id', {'id': user.id})}\n{formatted_status}{traffic_info}{additional_info}"
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=l10n.format_value("btn-devices"), callback_data="my_devices")],
        [types.InlineKeyboardButton(text="🌐 Language / Язык", callback_data="change_lang")]
    ])
    return text, kb

@router.message(F.text.in_(["👤 Profile", "👤 Профиль"]))
async def process_profile(message: types.Message, session, l10n: FluentLocalization):
    text, kb = await generate_profile_content(message.from_user.id, session, l10n)
    if text: await message.answer(text, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=True)
