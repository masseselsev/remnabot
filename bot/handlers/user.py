from aiogram import Router, types, F
from aiogram.filters import CommandStart, StateFilter
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from bot.database.core import get_session
from bot.database import models
from bot.config import config
from fluent.runtime import FluentLocalization
from datetime import datetime, timezone, timedelta
from dateutil import parser

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.services.settings import SettingsService
from bot.utils.crypto import get_crypto_link
import structlog

router = Router()

class UserStates(StatesGroup):
    trial_promo = State()

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
    """
    from bot.services.remnawave import api
    import structlog
    logger = structlog.get_logger()

    try:
        candidates = []
        
        # 1. Try get_user_by_telegram_id (sometimes returns list, sometimes dict)
        try:
            direct = await api.get_user_by_telegram_id(user_id)
            if isinstance(direct, dict) and direct.get('uuid'):
                candidates.append(direct)
            elif isinstance(direct, list):
                candidates.extend(direct)
        except Exception:
            pass
            
        # 2. Add users from search to ensure we catch manual accounts that might be missed by direct ID lookup
        try:
            resp = await api.get_users(search=str(user_id))
            if isinstance(resp, list):
                candidates.extend(resp)
            elif isinstance(resp, dict):
                cands = resp.get('users') or resp.get('data') or resp.get('items') or []
                if isinstance(cands, list):
                    candidates.extend(cands)
                elif isinstance(resp, dict) and resp.get('uuid'):
                    candidates.append(resp)
        except Exception:
            pass

        standard = None
        manual = []
        target_username = f"tg_{user_id}"
        
        # Deduplicate candidates by uuid
        unique_candidates = {c['uuid']: c for c in candidates if isinstance(c, dict) and 'uuid' in c}.values()
        
        for u in unique_candidates:
            tid = u.get('telegramId')
            uname = u.get('username')
            
            is_match = False
            # API search is fuzzy, so verify ID or exact username
            if str(tid) == str(user_id): is_match = True
            if uname == target_username: is_match = True
            
            if is_match:
                if uname == target_username:
                    standard = u
                else:
                    manual.append(u)
            
        manual.sort(key=lambda x: x.get('username', '').lower())
        return standard, manual
    except Exception as e:
        logger.error("check_accounts_error", error=str(e), user_id=user_id)
        return None, []

@router.message(CommandStart(), StateFilter("*"))
async def cmd_start(message: types.Message, state: FSMContext, session, l10n: FluentLocalization):
    await state.clear()

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

    # Welcome message from settings
    lang_code = l10n._locales[0] if hasattr(l10n, '_locales') else 'ru'
    welcome_setting = await SettingsService.get_setting(f"welcome_msg_{lang_code}")
    
    if not welcome_setting:
        fallback_msg = "Welcome, {$name}!" if lang_code == 'en' else "Добро пожаловать, {$name}!"
        welcome_text = fallback_msg.replace("{$name}", message.from_user.first_name)
    else:
        welcome_text = welcome_setting.replace("{$name}", message.from_user.first_name)
    
    # Combined Message construction
    full_text = welcome_text
    
    # Keyboard
    btn_shop = l10n.format_value("btn-shop")
    btn_profile = l10n.format_value("btn-profile")
    btn_trial = l10n.format_value("btn-trial")
    btn_support = l10n.format_value("btn-support")
    btn_instruction = l10n.format_value("btn-instruction")
    btn_disclaimer = l10n.format_value("btn-disclaimer")
    
    kb = [
        [types.KeyboardButton(text=btn_profile), types.KeyboardButton(text=btn_trial)],
        [types.KeyboardButton(text=btn_support), types.KeyboardButton(text=btn_instruction)],
        [types.KeyboardButton(text=btn_disclaimer)]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    # Now append subscriptions to full_text if they exist
    try:
        from bot.services.remnawave import api
        from html import escape
        
        std_acc, manual_accs = await check_existing_accounts(message.from_user.id)
        all_accs = []
        if std_acc: all_accs.append(std_acc)
        all_accs.extend(manual_accs)
        
        # Deduplicate by UUID
        unique_accs = {a['uuid']: a for a in all_accs}.values()
        
        now_utc = datetime.now(timezone.utc)
        msk_tz = timezone(timedelta(hours=3))
        
        if unique_accs:
            sub_title = l10n.format_value('start-active-sub-title') or 'ℹ️ <b>Активные подписки:</b>'
            sub_lines = [f"\n{sub_title}"]
            
            for idx, acc in enumerate(unique_accs, 1):
                expire_at = acc.get('expireAt')
                is_active = False
                exp_date = "Unlimited"
                
                if expire_at:
                    dt = parser.isoparse(expire_at)
                    if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
                    if dt > now_utc:
                        is_active = True
                        exp_date = dt.astimezone(msk_tz).strftime("%Y-%m-%d %H:%M MSK")
                else:
                    is_active = True # Unlimited
                    
                if is_active:
                    # Traffic
                    limit_bytes = acc.get('trafficLimitBytes') or 0
                    used_bytes = acc.get('userTraffic', {}).get('usedTrafficBytes') or 0
                    limit_gb = round(int(limit_bytes) / (1024**3), 1)
                    used_gb = round(int(used_bytes) / (1024**3), 2)
                    
                    percent = 0
                    if limit_bytes > 0:
                        percent = round((used_bytes / limit_bytes) * 100, 1)
                    
                    bar_str = get_traffic_bar(percent)
                    traffic_str = l10n.format_value("profile-traffic", {"used": used_gb, "limit": limit_gb, "percent": percent, "bar": bar_str})
                    link = acc.get('subscriptionUrl') or f"{config.remnawave_url}/sub/{acc['uuid']}"
                    
                    if "TRIAL_YES" in (acc.get('tag') or ""):
                        link = await get_crypto_link(link)

                    uname = acc.get('username', 'Unknown')
                    
                    item = [
                        f"{idx}. 👤 <b>{escape(uname)}</b>",
                        f"📅 {l10n.format_value('profile-expiry-caption') or 'До:'} {exp_date}",
                        f"{traffic_str}",
                        f"🔗 <code>{link}</code>"
                    ]
                    sub_lines.append("\n".join(item))

            if len(sub_lines) > 1:
                full_text += "\n" + "\n\n──────────────────────────\n".join(sub_lines)

    except Exception as e:
        logger.debug("start_active_subs_info_failed", error=str(e))
        
    await message.answer(full_text, reply_markup=keyboard, parse_mode="HTML", disable_web_page_preview=True)


@router.message(F.text == "🎁 3 дня бесплатно!")
@router.message(F.text == "🎁 3-day trial!")
@router.message(F.text == "🎁 3 days free!")
@router.message(F.text == "🎁 Try for free")
@router.message(F.text == "🎁 Попробовать бесплатно")
async def process_trial(message: types.Message, state: FSMContext, session, l10n: FluentLocalization):
    user = await session.get(models.User, message.from_user.id)
    
    if not user or not user.disclaimer_accepted:
        await message.answer(l10n.format_value("disclaimer-not-accepted-msg"), parse_mode="HTML")
        return
    
    from bot.services.remnawave import api
    from bot.config import config
    
    # 1. Check if user already has a trial via API (Source of Truth)
    rw_user = None
    if user.remnawave_uuid:
        try:
            rw_user = await api.get_user(user.remnawave_uuid)
        except: pass
    
    if not rw_user:
        try:
            # Search by dedicated name
            search_name = f"tg_{user.id}"
            candidates = await api.get_users(search=search_name)
            
            # Extract list from various possible response formats
            users_list = []
            if isinstance(candidates, list): users_list = candidates
            elif isinstance(candidates, dict):
                 for key in ['users', 'data', 'items', 'response']:
                     if key in candidates:
                         val = candidates[key]
                         if isinstance(val, list): users_list = val
                         elif isinstance(val, dict) and 'users' in val: users_list = val['users']
                         break
            
            for u in users_list:
                if u.get('username') == search_name:
                    rw_user = u
                    user.remnawave_uuid = u.get('uuid') or u.get('id')
                    await session.commit()
                    break
        except: pass

    if rw_user:
        tags = rw_user.get('tag') or ""
        if "TRIAL_YES" in tags:
            # User already has trial. Show info.
            # We reuse the display logic from execute_trial_creation but with msg-active instead of msg-activated
            try:
                # We need to render the trial info similar to execute_trial_creation
                # (I'll define a small helper or just do it here to avoid duplication issues)
                await show_active_trial_info(message, rw_user, user.remnawave_uuid, l10n)
                return
            except Exception as e:
                import structlog
                logger = structlog.get_logger()
                logger.error("show_trial_info_failed", error=str(e))

    # 2. No active trial found on remote -> Proceed to promo request
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=l10n.format_value("btn-cancel"), callback_data="cancel_trial_promo")]
    ])
    await message.answer(l10n.format_value("trial-promo-request"), reply_markup=kb)
    await state.set_state(UserStates.trial_promo)

@router.callback_query(F.data == "cancel_trial_promo")
async def cancel_trial_promo(callback: types.CallbackQuery, state: FSMContext, l10n: FluentLocalization):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer(l10n.format_value("trial-promo-cancelled"))
    await callback.answer()

async def show_active_trial_info(messageable, data, uuid, l10n: FluentLocalization):
    from bot.config import config
    from dateutil import parser
    from datetime import datetime, timezone, timedelta
    
    link = data.get('subscriptionUrl')
    if not link:
        link = f"{config.remnawave_url}/sub/{uuid}"
    
    # Always encrypt for this trial info display
    link = await get_crypto_link(link)
    
    traffic_bytes = data.get('trafficLimitBytes') or data.get('dataLimit') or 0
    traffic_gb = round(int(traffic_bytes) / (1024**3), 1)
    
    expire_at_str = data.get('expireAt')
    expire_display = "Unlimited"
    
    if expire_at_str:
        try:
            dt = parser.isoparse(expire_at_str)
            if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
            msk_tz = timezone(timedelta(hours=3))
            dt_msk = dt.astimezone(msk_tz)
            expire_display = dt_msk.strftime("%Y-%m-%d %H:%M MSK")
        except: pass

    msg_active = l10n.format_value("trial-active")
    msg_traffic = l10n.format_value("trial-traffic", {"gb": traffic_gb})
    msg_expires = l10n.format_value("trial-expires", {"date": expire_display})
    msg_link = l10n.format_value("trial-link-caption")
          
    instruction = l10n.format_value('trial-instruction-hint')


    await messageable.answer(
        f"{msg_active}\n\n"
        f"{msg_traffic}\n"
        f"{msg_expires}\n\n"
        f"{msg_link}\n<code>{link}</code>\n\n"
        f"{instruction}",
        disable_web_page_preview=True,
        parse_mode="HTML"
    )

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
            found_user_data = await api.get_user(rw_uuid)
            if not found_user_data or not isinstance(found_user_data, dict):
                found_user_data = None
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
            
        bar_str = get_traffic_bar(percent)

            
        t_tariff = l10n.format_value("profile-tariff", {"name": tariff_name})
        t_traffic = l10n.format_value("profile-traffic", {"used": used_gb, "limit": limit_gb, "percent": percent, "bar": bar_str})
        
        traffic_info = f"\n{t_tariff}\n{t_traffic}"
        
        # Link for main account
        from bot.config import config
        main_link = found_user_data.get('subscriptionUrl')
        if not main_link:
             main_link = f"{config.remnawave_url}/sub/{user.remnawave_uuid}"
        
        # Encrypt if it's a trial
        if "TRIAL_YES" in (found_user_data.get('tag') or ""):
            main_link = await get_crypto_link(main_link)

        t_link = l10n.format_value("profile-link", {"link": main_link})
        traffic_info += f"\n{t_link}"

    # Additional Accounts Visibility
    std_acc, manual_accs = await check_existing_accounts(user.id)
    additional_accs = []
    current_uuid = user.remnawave_uuid
    
    # Add manual accounts if they are not current
    for m in manual_accs:
        muuid = m.get('uuid')
        if muuid != current_uuid:
            additional_accs.append(m)
            
    # Add standard account if it exists but is not current
    if std_acc and std_acc.get('uuid') != current_uuid:
        additional_accs.append(std_acc)
        
    additional_info = ""
    if additional_accs:
        additional_items = []
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
                
            bar_str = get_traffic_bar(percent)

                
            t_traffic = l10n.format_value("profile-traffic", {"used": used_gb, "limit": limit_gb, "percent": percent, "bar": bar_str})
            
            # Link
            from bot.config import config
            link = acc.get('subscriptionUrl')
            if not link:
                link = f"{config.remnawave_url}/sub/{acc.get('uuid')}"
            
            if "TRIAL_YES" in (acc.get('tag') or ""):
                link = await get_crypto_link(link)

            t_link = l10n.format_value("profile-link", {"link": link})
            
            item_text = l10n.format_value("profile-account-item", {
                "username": u_name, 
                "expiry": exp_str,
                "traffic": t_traffic,
                "link": t_link
            })
            additional_items.append(item_text)
            
        if additional_items:
            additional_info = "\n\n" + l10n.format_value("profile-additional-accounts") + "\n"
            additional_info += "\n──────────────────────────\n".join(additional_items)

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

@router.message(F.text == "📖 Instruction")
@router.message(F.text == "📖 Инструкция")
async def cmd_instruction_msg(message: types.Message, l10n: FluentLocalization):
    instruction = (
        f"{l10n.format_value('trial-instruction-title')}\n"
        f"{l10n.format_value('trial-instruction-profile-hint')}\n\n"
        f"{l10n.format_value('trial-instruction-http-subtitle')}\n"
        f"{l10n.format_value('trial-instruction-http-steps')}\n\n"
        f"{l10n.format_value('trial-instruction-happ-subtitle')}\n"
        f"{l10n.format_value('trial-instruction-apps')}\n"
        f"{l10n.format_value('trial-instruction-steps')}\n\n"
        f"{l10n.format_value('trial-instruction-promo-subtitle')}\n"
        f"{l10n.format_value('trial-instruction-promo-steps')}"
    )
    await message.answer(instruction, disable_web_page_preview=True, parse_mode="HTML")
 
@router.message(F.text == "⚖️ About Project")
@router.message(F.text == "⚖️ О проекте")
async def cmd_disclaimer(message: types.Message, session, l10n: FluentLocalization):
    user = await session.get(models.User, message.from_user.id)
    kb = None
    if user and not user.disclaimer_accepted:
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text=l10n.format_value("btn-accept-disclaimer"), callback_data="accept_disclaimer")]
        ])
    await message.answer(l10n.format_value("disclaimer-text"), reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "accept_disclaimer")
async def process_accept_disclaimer(callback: types.CallbackQuery, session, l10n: FluentLocalization):
    user = await session.get(models.User, callback.from_user.id)
    if user:
        user.disclaimer_accepted = True
        await session.commit()
    
    await callback.message.edit_text(l10n.format_value("disclaimer-accepted-msg"), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data == "change_lang")
async def show_language_selector(callback: types.CallbackQuery, l10n: FluentLocalization):
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=l10n.format_value("lang-en"), callback_data="set_lang_en")],
        [types.InlineKeyboardButton(text=l10n.format_value("lang-ru"), callback_data="set_lang_ru")],
        [types.InlineKeyboardButton(text=l10n.format_value("btn-back"), callback_data="back_profile")]
    ])
    await callback.message.edit_text(l10n.format_value("lang-selector-title"), reply_markup=kb)

@router.callback_query(F.data == "delete_msg")
async def delete_msg(callback: types.CallbackQuery):
    await callback.message.delete()

@router.callback_query(F.data.startswith("set_lang_"))
async def set_language(callback: types.CallbackQuery, session, l10n: FluentLocalization):
    lang_code = callback.data.split("_")[2]
    user = await session.get(models.User, callback.from_user.id)
    if user:
        user.language_code = lang_code
        await session.commit()
    else:
        from bot.database.models import User
        # If user doesn't exist for some reason, create them so preferences stick
        new_user = User(
            id=callback.from_user.id,
            username=callback.from_user.username,
            full_name=callback.from_user.full_name,
            language_code=lang_code
        )
        session.add(new_user)
        await session.commit()

    
    # We must use the l10n object that matches the new language
    # or rely on the middleware to provide it if we answered later.
    # But since we need it NOW to build the keyboard, we should ideally
    # get a localized version. 
    # For now, let's just use the provided l10n if it's already switched, 
    # or simpler: hardcode or re-fetch.
    # Actually, the middleware usually provides l10n based on DB. 
    # Fetch correct l10n for new language
    from bot.middlewares.i18n import I18nMiddleware
    # Actually, easier to just manually select based on lang_code
    # since we know the middleware's loader logic.
    # But a cleaner way:
    if lang_code == "ru":
        new_l10n = FluentLocalization(["ru"], ["messages.ftl"], I18nMiddleware.get_loader())
    else:
        new_l10n = FluentLocalization(["en"], ["messages.ftl"], I18nMiddleware.get_loader())

    text = new_l10n.format_value("lang-changed-msg")
    btn_profile = new_l10n.format_value("btn-profile")
    btn_trial = new_l10n.format_value("btn-trial")
    btn_support = new_l10n.format_value("btn-support")
    btn_instruction = new_l10n.format_value("btn-instruction")
    btn_disclaimer = new_l10n.format_value("btn-disclaimer")

    kb = [
        [types.KeyboardButton(text=btn_profile), types.KeyboardButton(text=btn_trial)],
        [types.KeyboardButton(text=btn_support), types.KeyboardButton(text=btn_instruction)],
        [types.KeyboardButton(text=btn_disclaimer)]
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
        all_accs.sort(key=lambda x: x.get('username', '').lower())
        
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
        
    # Back button logic
    back_callback = "back_profile"
    if callback.data.startswith("dev_acc_"):
        back_callback = "my_devices"

    if not devices:
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
             [types.InlineKeyboardButton(text=l10n.format_value("btn-back"), callback_data=back_callback)] 
        ])
        await callback.message.edit_text(l10n.format_value("devices-empty"), reply_markup=kb, parse_mode="HTML")
        await callback.answer()
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
    
    # Back button logic (already calculated above)
    kb_rows.append([types.InlineKeyboardButton(text=l10n.format_value("btn-back"), callback_data=back_callback)])
    
    msg_text = l10n.format_value("devices-title")
    await callback.message.edit_text(msg_text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb_rows), parse_mode="Markdown")
    await callback.answer()

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
        await callback.answer(l10n.format_value("error-context-lost"), show_alert=True)
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
        await callback.answer(l10n.format_value("error-context-lost"), show_alert=True)
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
         await callback.answer(l10n.format_value("error-context-lost"), show_alert=True)
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
        await callback.answer(l10n.format_value("error-profile-load"), show_alert=True)
    await callback.answer()


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
async def request_new_trial_explicit(callback: types.CallbackQuery, state: FSMContext, session, l10n: FluentLocalization):
    await callback.message.answer(l10n.format_value("trial-promo-request"))
    await state.set_state(UserStates.trial_promo)
    await callback.answer()

@router.message(UserStates.trial_promo)
async def process_trial_promo(message: types.Message, state: FSMContext, session, l10n: FluentLocalization):
    if message.text and message.text.startswith("/"):
        # Let command handlers handle it if they have state="*" or priority
        # But since aiogram state handlers have priority, we must clear state and return
        await state.clear()
        return

    promo_code = message.text.strip()
    user = await session.get(models.User, message.from_user.id)
    
    is_valid = False
    
    # Built-in: Current date (GMT+3)
    now_gmt3 = datetime.now(timezone.utc) + timedelta(hours=3)
    today_code = now_gmt3.strftime("%d.%m.%Y")
    
    if promo_code == today_code:
        is_valid = True
    else:
        # Check DB
        stmt = select(models.Promocode).where(models.Promocode.code == promo_code, models.Promocode.is_trial_only == True)
        result = await session.execute(stmt)
        promo = result.scalar_one_or_none()
        
        if promo:
            if promo.max_uses == 0 or promo.used_count < promo.max_uses:
                # Check expiry if exists
                if promo.active_until and promo.active_until < datetime.now(timezone.utc):
                    is_valid = False
                else:
                    is_valid = True
                    promo.used_count += 1

    if promo_code.startswith("tg_") and not is_valid:
        # Forbidden use of tg_ usernames as promos
        is_valid = False
    elif not is_valid:
        # Check if username format allowed as promo (not ending in -XX)
        import re
        if re.search(r"-\d{2}$", promo_code):
             is_valid = False
        else:
             # Check Remnawave API for existing username
             from bot.services.remnawave import api
             try:
                 users_resp = await api.get_users(search=promo_code)
                 candidates = []
                 if isinstance(users_resp, list):
                     candidates = users_resp
                 elif isinstance(users_resp, dict):
                     candidates = users_resp.get('users') or users_resp.get('data') or users_resp.get('items') or (users_resp.get('response', {}).get('users') if isinstance(users_resp.get('response'), dict) else [])
                 
                 if isinstance(candidates, list):
                     for u in candidates:
                         if u.get('username') == promo_code:
                             is_valid = True
                             break
             except Exception as e:
                 logger.error("promo_username_check_failed", error=str(e))

    if is_valid:
        await state.clear()
        tg_username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
        note = f"User: {tg_username}, Promo: {promo_code}"
        await execute_trial_creation(message, session, l10n, user, note=note)
    else:
        await message.answer(l10n.format_value("trial-promo-invalid"))

async def execute_trial_creation(messageable, session, l10n: FluentLocalization, user: models.User, note: str = None):
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
    
    success = await fulfill_order(order.id, session, note=note)
    if success:
        # Get connection info (Subscription URL)
        # Fetch fresh user data to get the correct subscription link
        try:
             data = await api.get_user(user.remnawave_uuid)
             
             link = data.get('subscriptionUrl')
             if not link:
                 link = f"{config.remnawave_url}/sub/{user.remnawave_uuid}"
            
             # Encrypt trial link
             link = await get_crypto_link(link)
            
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
             link = await get_crypto_link(f"{config.remnawave_url}/sub/{user.remnawave_uuid}")
             traffic_gb = tariff.traffic_limit_gb
             expire_display = f"{tariff.duration_days} Days"
             
        msg_activated = l10n.format_value("trial-activated")
        msg_traffic = l10n.format_value("trial-traffic", {"gb": traffic_gb})
        msg_expires = l10n.format_value("trial-expires", {"date": expire_display})
        msg_link = l10n.format_value("trial-link-caption")
              
        instruction = l10n.format_value('trial-instruction-hint')

        await messageable.answer(
            f"{msg_activated}\n\n"
            f"{msg_traffic}\n"
            f"{msg_expires}\n\n"
            f"{msg_link}\n<code>{link}</code>\n\n"
            f"{instruction}",
            disable_web_page_preview=True,
            parse_mode="HTML"
        )
    else:
        await messageable.answer(l10n.format_value("trial-failed-msg"))


