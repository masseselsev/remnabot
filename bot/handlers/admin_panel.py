from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from fluent.runtime import FluentLocalization
from bot.config import config
from bot.services.settings import SettingsService
from bot.database import models
from sqlalchemy import select, delete
from bot.services.remnawave import api
from datetime import datetime, timedelta
from html import escape
import structlog

logger = structlog.get_logger()

router = Router()

class AdminStates(StatesGroup):
    menu = State()
    edit_trial_days = State()
    edit_trial_traffic = State()
    edit_trial_plan = State()
    
    # Custom Plans
    cp_name = State()
    cp_squad = State()
    cp_traffic = State()
    cp_duration = State()
    cp_tag = State()
    
    # Provisioning
    prov_username = State()
    prov_tgid = State()
    prov_desc = State()
    prov_confirm = State()

    # User Search
    search_user_id = State()

    # Standard Tariffs
    t_name = State()
    t_price_rub = State()
    t_price_stars = State()
    t_price_usd = State()
    t_days = State()
    t_traffic = State()
    t_squad = State()
    t_grant_id = State()
    
    # Welcome Message Settings
    welcome_select_lang = State()
    welcome_input_text = State()

    # Promo Codes
    promo_code = State()
    promo_uses = State()

async def get_main_kb(l10n: FluentLocalization):
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=l10n.format_value("admin-btn-tariffs"), callback_data="admin_tariffs_list")],
        [types.InlineKeyboardButton(text=l10n.format_value("admin-btn-trial"), callback_data="admin_trial")],
        [types.InlineKeyboardButton(text=l10n.format_value("admin-btn-cp"), callback_data="admin_cp_list")],
        [types.InlineKeyboardButton(text="🔍 View User by TgID", callback_data="admin_search_user")],
        [types.InlineKeyboardButton(text="🎟 Promo Codes", callback_data="admin_promos_list")],
        [types.InlineKeyboardButton(text=l10n.format_value("admin-btn-welcome"), callback_data="admin_welcome_mgmt")],
        [types.InlineKeyboardButton(text=l10n.format_value("admin-btn-exit"), callback_data="admin_exit")]
    ])

# ... cmd_admin ...

@router.message(Command("admin"), StateFilter("*"))
async def cmd_admin(message: types.Message, state: FSMContext, l10n: FluentLocalization):
    if message.from_user.id not in config.admin_ids:
        return
        
    await state.clear()
    await message.answer(l10n.format_value("admin-title"), reply_markup=await get_main_kb(l10n), parse_mode="Markdown")

@router.callback_query(F.data == "admin_exit")
async def admin_exit(callback: types.CallbackQuery, state: FSMContext, l10n: FluentLocalization):
    await state.clear()
    await callback.message.delete()
    
    # Restore Main Menu
    btn_shop = l10n.format_value("btn-shop")
    btn_profile = l10n.format_value("btn-profile")
    btn_trial = l10n.format_value("btn-trial")
    btn_support = l10n.format_value("btn-support")
    
    kb = [
        [types.KeyboardButton(text=btn_profile), types.KeyboardButton(text=btn_trial), types.KeyboardButton(text=btn_support)]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    await callback.message.answer(l10n.format_value("admin-exit-msg"), reply_markup=keyboard)

@router.callback_query(F.data == "admin_menu")
async def back_to_menu(callback: types.CallbackQuery, state: FSMContext, l10n: FluentLocalization):
    await state.clear()
    await callback.message.edit_text(l10n.format_value("admin-title"), reply_markup=await get_main_kb(l10n), parse_mode="Markdown")

# --- Welcome Message Settings ---

@router.callback_query(F.data == "admin_welcome_mgmt")
async def admin_welcome_menu(callback: types.CallbackQuery, state: FSMContext, l10n: FluentLocalization):
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=l10n.format_value("admin-welcome-ru"), callback_data="adm_w_edit_ru")],
        [types.InlineKeyboardButton(text=l10n.format_value("admin-welcome-en"), callback_data="adm_w_edit_en")],
        [types.InlineKeyboardButton(text=l10n.format_value("btn-back"), callback_data="admin_menu")]
    ])
    await callback.message.edit_text(l10n.format_value("admin-welcome-title"), reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data.startswith("adm_w_edit_"))
async def admin_welcome_edit_start(callback: types.CallbackQuery, state: FSMContext, l10n: FluentLocalization):
    lang = callback.data.split("_")[3] # ru or en
    await state.update_data(edit_welcome_lang=lang)
    
    current_key = f"welcome_msg_{lang}"
    current_val = await SettingsService.get_setting(current_key, "Welcome, {$name}!") # Default if not set
    
    await state.set_state(AdminStates.welcome_input_text)
    await callback.message.edit_text(
        l10n.format_value("admin-welcome-ask", {"current": current_val}),
        parse_mode="HTML",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text=l10n.format_value("btn-cancel"), callback_data="admin_welcome_mgmt")]])
    )

@router.message(AdminStates.welcome_input_text)
async def admin_welcome_save(message: types.Message, state: FSMContext, l10n: FluentLocalization):
    data = await state.get_data()
    lang = data.get("edit_welcome_lang")
    if not lang: return
    
    new_text = message.text.strip()
    await SettingsService.set_setting(f"welcome_msg_{lang}", new_text)
    
    await message.answer(l10n.format_value("admin-welcome-success"))
    await state.clear()
    # Go back to admin menu
    await cmd_admin(message, state, l10n)

# --- User Search ---

@router.callback_query(F.data == "admin_search_user")
async def admin_search_user_start(callback: types.CallbackQuery, state: FSMContext, l10n: FluentLocalization):
    await state.set_state(AdminStates.search_user_id)
    await callback.message.edit_text("Enter Telegram ID of the user to view:", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text=l10n.format_value("btn-cancel"), callback_data="admin_menu")]]))

@router.message(F.contact | F.forward_origin)
async def admin_intercept_contact_or_forward(message: types.Message, state: FSMContext, session, l10n: FluentLocalization):
    if message.from_user.id not in config.admin_ids:
        return
        
    target_id = None
    if message.contact:
        target_id = message.contact.user_id
    elif message.forward_origin:
        if message.forward_origin.type == 'user':
            target_id = message.forward_origin.sender_user.id
        else:
            await message.answer(l10n.format_value("admin-error-no-tgid"))
            return
        
    if not target_id:
        await message.answer(l10n.format_value("admin-error-no-tgid"))
        return
        
    await state.set_state(AdminStates.search_user_id)
    await admin_search_user_process(message, state, session, l10n, override_id=target_id)


@router.message(AdminStates.search_user_id)
async def admin_search_user_process(message: types.Message, state: FSMContext, session, l10n: FluentLocalization, override_id: int = None):
    try:
        target_id = override_id if override_id is not None else int(message.text.strip())
    except ValueError:
        await message.answer(l10n.format_value("admin-error-invalid-tgid"))
        return
        
    await message.answer(f"Fetching data for {target_id}...")
    await state.update_data(search_target_id=target_id)
    
    from bot.handlers.user import check_existing_accounts
    from bot.services.remnawave import api
    from dateutil import parser
    from datetime import datetime, timezone, timedelta
    
    db_user = await session.get(models.User, target_id)
    std_acc, manual_accs = await check_existing_accounts(target_id)
    all_accs = []
    if std_acc: all_accs.append(std_acc)
    all_accs.extend(manual_accs)
    all_accs.sort(key=lambda x: x.get('username', '').lower())
    
    if not all_accs and not db_user:
        await message.answer(f"User {target_id} not found in DB or Panel.")
        await cmd_admin(message, state, l10n)
        return
        
    text = f"👤 <b>User Info: {target_id}</b>\n"
    if db_user:
        text += f"Username: @{db_user.username or 'N/A'}\n"
        text += f"DB Main UUID: <code>{db_user.remnawave_uuid or 'N/A'}</code>\n"
    
    text += "\n📦 <b>Accounts:</b>\n"
    if not all_accs:
        text += "No accounts found in panel.\n"
        
    msk_tz = timezone(timedelta(hours=3))
    
    for acc in all_accs:
        uuid = acc.get('uuid')
        uname = acc.get('username')
        
        limit_b = acc.get('trafficLimitBytes') or 0
        used_b = acc.get('userTraffic', {}).get('usedTrafficBytes') or 0
        limit_gb = limit_b / (1024**3) if limit_b else 0
        used_gb = used_b / (1024**3)
        
        exp_at = acc.get('expireAt')
        exp_str = "Unlimited"
        if exp_at:
            try:
                dt = parser.isoparse(exp_at)
                if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
                exp_str = dt.astimezone(msk_tz).strftime("%Y-%m-%d %H:%M")
            except: pass
            
        text += f"\n🔹 <b>{uname}</b> (<code>{uuid[:8]}...</code>)\n"
        text += f"   Traffic: {used_gb:.2f}GB / {limit_gb:.1f}GB\n"
        text += f"   Expire: {exp_str}\n"
        
        try:
            devices = await api.get_user_devices(uuid)
        except:
            devices = []
            
        if not devices:
            text += "   Devices: 0\n"
        else:
            text += f"   Devices ({len(devices)}):\n"
            for d in devices:
                model = d.get('deviceModel', 'Unknown')
                plat = d.get('platform', 'Unknown')
                upd = d.get('updatedAt')
                upd_str = "?"
                if upd:
                    try:
                        udt = parser.isoparse(upd)
                        if udt.tzinfo is None: udt = udt.replace(tzinfo=timezone.utc)
                        upd_str = udt.astimezone(msk_tz).strftime("%d.%m %H:%M")
                    except: pass
                text += f"    - {model} ({plat}) [Act: {upd_str}]\n"

    kb_rows = []
    for acc in all_accs:
        uuid = acc.get('uuid')
        uname = acc.get('username')
        kb_rows.append([types.InlineKeyboardButton(text=f"📱 Devices: {uname}", callback_data=f"adm_dacc_{uuid}")])
        
    kb_rows.append([types.InlineKeyboardButton(text=l10n.format_value("admin-cp-back-btn"), callback_data="admin_menu")])

    await message.answer(text, parse_mode="HTML", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb_rows))
    # Do not call cmd_admin, we leave them here to click the device buttons if they want


@router.callback_query(F.data.startswith("adm_dacc_"))
async def admin_show_devices_list(callback: types.CallbackQuery, state: FSMContext, l10n: FluentLocalization):
    target_uuid = callback.data.split("_", 2)[2]
    await state.update_data(admin_manage_uuid=target_uuid)
    
    from bot.services.remnawave import api
    from dateutil import parser
    from datetime import datetime, timezone, timedelta
    
    try:
        devices = await api.get_user_devices(target_uuid)
    except Exception:
        devices = []
        
    if not devices:
        await callback.answer(l10n.format_value("admin-error-no-devices"), show_alert=True)
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
        
        # pass hwid up to 10 chars, fetch full later
        cb_data = f"adm_ddev_{hwid[:10]}"
        kb_rows.append([types.InlineKeyboardButton(text=btn_text, callback_data=cb_data)])
    kb_rows.append([types.InlineKeyboardButton(text="🔙 Back", callback_data="adm_back_user_search")])
        
    # No convenient back button without re-generating profile, but this replaces the message inline or opens a new one
    await callback.message.edit_text("Select a device to view or manage:", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb_rows))


@router.callback_query(F.data == "adm_back_user_search")
async def admin_back_user_search(callback: types.CallbackQuery, state: FSMContext, session, l10n: FluentLocalization):
    data = await state.get_data()
    target_id = data.get('search_target_id')
    if not target_id:
        await callback.answer(l10n.format_value("admin-error-context-lost"), show_alert=True)
        return
    
    # We must delete current msg and send new one as a message.answer or just re-run search logic
    # To keep it simple, we just re-run search logic (this will send a NEW message, which is fine)
    await callback.message.delete()
    await admin_search_user_process(callback.message, state, session, l10n, override_id=target_id)


@router.callback_query(F.data.startswith("adm_ddev_"))
async def admin_device_details(callback: types.CallbackQuery, state: FSMContext, l10n: FluentLocalization):
    hwid_part = callback.data.split("_")[2]
    data = await state.get_data()
    target_uuid = data.get('admin_manage_uuid')
    
    if not target_uuid:
        await callback.answer("Context lost. Search user again.", show_alert=True)
        return
        
    from bot.services.remnawave import api
    from dateutil import parser
    from datetime import timezone, timedelta
    
    try:
        devices = await api.get_user_devices(target_uuid)
    except Exception:
        devices = []
        
    target_dev = None
    for d in devices:
        if d.get('hwid', '').startswith(hwid_part):
            target_dev = d
            break
            
    if not target_dev:
        await callback.answer(l10n.format_value("admin-error-device-not-found"), show_alert=True)
        return
        
    # Store full hwid for deletion
    await state.update_data(admin_manage_hwid=target_dev.get('hwid'))
        
    model = target_dev.get('deviceModel', 'Unknown')
    platform = target_dev.get('platform', 'Unknown')
    upd = target_dev.get('updatedAt')
    ip = target_dev.get('lastIp', 'Unknown')
    
    upd_str = "Unknown"
    if upd:
        dt = parser.isoparse(upd)
        if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
        upd_str = dt.astimezone(timezone(timedelta(hours=3))).strftime("%d.%m.%Y %H:%M:%S")

    text = f"📱 <b>Device Info</b>\n" \
           f"Model: {model}\n" \
           f"Platform: {platform}\n" \
           f"IP: {ip}\n" \
           f"Last Active: {upd_str}"
           
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🗑 Delete Device", callback_data="adm_del_dev")],
        [types.InlineKeyboardButton(text="🔙 Back", callback_data=f"adm_dacc_{target_uuid}")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "adm_del_dev")
async def admin_delete_device(callback: types.CallbackQuery, state: FSMContext, l10n: FluentLocalization):
    data = await state.get_data()
    target_uuid = data.get('admin_manage_uuid')
    target_hwid = data.get('admin_manage_hwid')
    
    if not target_uuid or not target_hwid:
        await callback.answer("Context lost.", show_alert=True)
        return
        
    from bot.services.remnawave import api
    
    try:
        await api.delete_user_device(target_hwid, target_uuid)
        await callback.answer(l10n.format_value("admin-success-device-deleted"), show_alert=True)
        # Return to device list
        await admin_show_devices_list(callback=types.CallbackQuery(
            id=callback.id,
            from_user=callback.from_user,
            chat_instance=callback.chat_instance,
            message=callback.message,
            data=f"adm_dacc_{target_uuid}"
        ), state=state, l10n=l10n)
    except Exception as e:
        await callback.answer(f"Failed to delete: {e}", show_alert=True)

# --- Trial Settings ---

@router.callback_query(F.data == "admin_trial")
async def trial_settings_menu(callback: types.CallbackQuery, state: FSMContext, l10n: FluentLocalization):
    settings = await SettingsService.get_trial_settings()
    
    # Resolve Squad Name
    squad_val = settings['squad_uuid']
    squad_display = squad_val
    if squad_val and squad_val != "0" and squad_val != "None":
        try:
             squad_data = await api.get_squad(squad_val)
             s = squad_data.get('response', squad_data)
             
             name = s.get('slug') or s.get('name') or "Unnamed"
             squad_display = f"{name} ({squad_val})"
        except Exception:
             pass

    text = f"{l10n.format_value('admin-trial-title')}\n\n" + \
           l10n.format_value("admin-trial-info", {
               "days": settings['days'],
               "traffic": settings['traffic'],
               "squad": squad_display
           })
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=l10n.format_value("admin-btn-edit-days"), callback_data="a_edit_days"),
         types.InlineKeyboardButton(text=l10n.format_value("admin-btn-edit-traffic"), callback_data="a_edit_traffic")],
        [types.InlineKeyboardButton(text=l10n.format_value("admin-btn-edit-squad"), callback_data="a_edit_squad")],
        [types.InlineKeyboardButton(text=l10n.format_value("admin-cp-back-btn"), callback_data="admin_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

# Edit Handlers

@router.callback_query(F.data == "a_edit_days")
async def ask_days(callback: types.CallbackQuery, state: FSMContext, l10n: FluentLocalization):
    await state.set_state(AdminStates.edit_trial_days)
    await callback.message.edit_text(l10n.format_value("admin-ask-days"), reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text=l10n.format_value("btn-cancel"), callback_data="admin_trial")]]))

@router.message(AdminStates.edit_trial_days)
async def set_days(message: types.Message, state: FSMContext, l10n: FluentLocalization):
    try:
        val = int(message.text)
        await SettingsService.set_setting("trial_days", str(val))
        await message.answer(l10n.format_value("admin-set-days-success", {"val": val}))
        await cmd_admin(message, state, l10n) 
    except ValueError:
        await message.answer(l10n.format_value("admin-set-days-error"))

@router.callback_query(F.data == "a_edit_traffic")
async def ask_traffic(callback: types.CallbackQuery, state: FSMContext, l10n: FluentLocalization):
    await state.set_state(AdminStates.edit_trial_traffic)
    await callback.message.edit_text(l10n.format_value("admin-ask-traffic"), reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text=l10n.format_value("btn-cancel"), callback_data="admin_trial")]]))

@router.message(AdminStates.edit_trial_traffic)
async def set_traffic(message: types.Message, state: FSMContext, l10n: FluentLocalization):
    try:
        val = float(message.text)
        await SettingsService.set_setting("trial_traffic_gb", str(val))
        await message.answer(l10n.format_value("admin-set-traffic-success", {"val": val}))
        await cmd_admin(message, state, l10n)
    except ValueError:
        await message.answer(l10n.format_value("admin-set-traffic-error"))

@router.callback_query(F.data == "a_edit_squad")
async def ask_squad(callback: types.CallbackQuery, state: FSMContext, l10n: FluentLocalization):
    await state.set_state(AdminStates.edit_trial_plan) # Reuse state or rename? Reuse is fine but confusing. Let's keep state name.
    await callback.message.edit_text(l10n.format_value("admin-ask-squad"), reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text=l10n.format_value("btn-cancel"), callback_data="admin_trial")]]))

@router.message(AdminStates.edit_trial_plan)
async def set_squad(message: types.Message, state: FSMContext, l10n: FluentLocalization):
    await SettingsService.set_setting("trial_squad_uuid", message.text.strip())
    await message.answer(l10n.format_value("admin-set-squad-success", {"val": message.text}))
    await cmd_admin(message, state, l10n)

# --- Custom Plans (Special Tariffs) ---

@router.callback_query(F.data == "admin_cp_list")
async def cp_list(callback: types.CallbackQuery, state: FSMContext, session, l10n: FluentLocalization):
    stmt = select(models.SpecialTariff).order_by(models.SpecialTariff.id)
    result = await session.execute(stmt)
    tariffs = result.scalars().all()
    
    kb_rows = []
    for t in tariffs:
        kb_rows.append([types.InlineKeyboardButton(text=f"💎 {t.name}", callback_data=f"cp_view_{t.id}")])
    
    kb_rows.append([types.InlineKeyboardButton(text=l10n.format_value("admin-cp-create-btn"), callback_data="cp_create")])
    kb_rows.append([types.InlineKeyboardButton(text=l10n.format_value("admin-cp-back-btn"), callback_data="admin_menu")])
    
    text = f"{l10n.format_value('admin-cp-title')}\n{l10n.format_value('admin-cp-list-desc')}"
    await callback.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb_rows), parse_mode="Markdown")

# Create Wizard

@router.callback_query(F.data == "cp_create")
async def cp_start_create(callback: types.CallbackQuery, state: FSMContext, l10n: FluentLocalization):
    await state.set_state(AdminStates.cp_name)
    await callback.message.edit_text(l10n.format_value("admin-cp-create-step1"), reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text=l10n.format_value("admin-cp-back-btn"), callback_data="admin_cp_list")]]), parse_mode="Markdown")

@router.message(AdminStates.cp_name)
async def cp_set_name(message: types.Message, state: FSMContext, l10n: FluentLocalization):
    await state.update_data(name=message.text)
    await state.set_state(AdminStates.cp_squad)
    await message.answer(l10n.format_value("admin-cp-create-step2"))

@router.message(AdminStates.cp_squad)
async def cp_set_squad(message: types.Message, state: FSMContext, l10n: FluentLocalization):
    await state.update_data(squad=message.text.strip())
    await state.set_state(AdminStates.cp_traffic)
    await message.answer(l10n.format_value("admin-cp-create-step3"))

@router.message(AdminStates.cp_traffic)
async def cp_set_traffic(message: types.Message, state: FSMContext, l10n: FluentLocalization):
    try:
        val = float(message.text)
        await state.update_data(traffic=val)
        await state.set_state(AdminStates.cp_duration)
        await message.answer(l10n.format_value("admin-cp-create-step4"))
    except ValueError:
        await message.answer(l10n.format_value("admin-cp-val-error"))

@router.message(AdminStates.cp_duration)
async def cp_set_duration(message: types.Message, state: FSMContext, l10n: FluentLocalization):
    try:
        val = int(message.text)
        await state.update_data(duration=val)
        await state.set_state(AdminStates.cp_tag)
        await message.answer(l10n.format_value("admin-cp-create-step5"))
    except ValueError:
        await message.answer(l10n.format_value("admin-cp-val-error"))



@router.message(AdminStates.cp_tag)
async def cp_finish_create(message: types.Message, state: FSMContext, session, l10n: FluentLocalization):
    tag = message.text.strip()
    if tag == "0": tag = None
    
    data = await state.get_data()
    
    if data.get('edit_tariff_id'):
        tariff = await session.get(models.SpecialTariff, data['edit_tariff_id'])
        if tariff:
            tariff.name = data['name']
            tariff.squad_uuid = data['squad']
            tariff.traffic_gb = data['traffic']
            tariff.duration_months = data['duration']
            tariff.tag = tag
            await session.commit()
            await message.answer(l10n.format_value("admin-cp-created", {"name": tariff.name}))
    else:
        new_tariff = models.SpecialTariff(
            name=data['name'],
            squad_uuid=data['squad'],
            traffic_gb=data['traffic'],
            duration_months=data['duration'],
            tag=tag
        )
        session.add(new_tariff)
        await session.commit()
        await message.answer(l10n.format_value("admin-cp-created", {"name": new_tariff.name}))
        
    await state.update_data(edit_tariff_id=None)
    await cmd_admin(message, state, l10n)

@router.callback_query(F.data.startswith("cp_edit_"))
async def cp_edit_start(callback: types.CallbackQuery, state: FSMContext, l10n: FluentLocalization):
    try:
        tid = int(callback.data.split("_")[2])
        await state.update_data(edit_tariff_id=tid)
        await cp_start_create(callback, state, l10n)
    except:
        pass

# View Tariff

@router.callback_query(F.data.startswith("cp_view_"))
async def cp_view(callback: types.CallbackQuery, state: FSMContext, session, l10n: FluentLocalization):
    try:
        tariff_id = int(callback.data.split("_")[2])
    except (IndexError, ValueError):
        await callback.answer(l10n.format_value("admin-invalid-id"))
        return

    tariff = await session.get(models.SpecialTariff, tariff_id)
    
    if not tariff:
        await callback.answer(l10n.format_value("admin-cp-not-found"))
        await cp_list(callback, state, session, l10n)
        return

    dur_display = "∞" if tariff.duration_months == 0 else f"{tariff.duration_months} {l10n.format_value('admin-month-short')}"

    # Resolve Squad Name
    squad_display = tariff.squad_uuid or "N/A"
    if tariff.squad_uuid and tariff.squad_uuid != "0":
        try:
             squad_data = await api.get_squad(tariff.squad_uuid)
             s = squad_data.get('response', squad_data)
             
             name = s.get('slug') or s.get('name') or "Unnamed"
             squad_display = f"{name} ({tariff.squad_uuid})"
        except Exception:
             pass

    text = (
        f"{l10n.format_value('admin-cp-view-title', {'name': tariff.name})}\n\n"
        f"{l10n.format_value('admin-cp-view-squad', {'squad': squad_display})}\n"
        f"{l10n.format_value('admin-cp-view-traffic', {'traffic': tariff.traffic_gb})}\n"
        f"{l10n.format_value('admin-cp-view-duration', {'duration': dur_display})}\n"
        f"{l10n.format_value('admin-cp-view-tag', {'tag': tariff.tag or 'None'})}"
    )
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=l10n.format_value("admin-cp-btn-grant"), callback_data=f"cp_grant_{tariff.id}")],
        [types.InlineKeyboardButton(text=l10n.format_value("admin-cp-btn-edit"), callback_data=f"cp_edit_{tariff.id}")],
        [types.InlineKeyboardButton(text=l10n.format_value("admin-cp-btn-delete"), callback_data=f"cp_delete_{tariff.id}")],
        [types.InlineKeyboardButton(text=l10n.format_value("admin-cp-back-btn"), callback_data="admin_cp_list")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data.startswith("cp_delete_"))
async def cp_delete(callback: types.CallbackQuery, state: FSMContext, session, l10n: FluentLocalization):
    tariff_id = int(callback.data.split("_")[2])
    stmt = delete(models.SpecialTariff).where(models.SpecialTariff.id == tariff_id)
    await session.execute(stmt)
    await session.commit()
    await callback.answer(l10n.format_value("admin-deleted"))
    await cp_list(callback, state, session, l10n)

# Grant Wizard

@router.callback_query(F.data.startswith("cp_grant_"))
async def cp_grant_start(callback: types.CallbackQuery, state: FSMContext, session, l10n: FluentLocalization):
    tariff_id = int(callback.data.split("_")[2])
    tariff = await session.get(models.SpecialTariff, tariff_id)
    if not tariff: return
    
    await state.update_data(grant_tariff_id=tariff.id)
    await state.set_state(AdminStates.prov_username)
    await callback.message.edit_text(l10n.format_value("admin-cp-grant-step1", {"name": tariff.name}), reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text=l10n.format_value("admin-cp-back-btn"), callback_data=f"cp_view_{tariff.id}")]]), parse_mode="Markdown")

@router.message(AdminStates.prov_username)
async def cp_grant_username(message: types.Message, state: FSMContext, l10n: FluentLocalization):
    await state.update_data(username=message.text.strip())
    await state.set_state(AdminStates.prov_tgid)
    await message.answer(l10n.format_value("admin-cp-grant-step2"))

@router.message(AdminStates.prov_tgid)
async def cp_grant_tgid(message: types.Message, state: FSMContext, l10n: FluentLocalization):
    try:
        val = int(message.text)
        await state.update_data(tgid=val)
        await state.set_state(AdminStates.prov_desc)
        await message.answer(l10n.format_value("admin-cp-grant-step3"))
    except ValueError:
        await message.answer(l10n.format_value("admin-cp-val-error"))

@router.message(AdminStates.prov_desc)
async def cp_grant_desc(message: types.Message, state: FSMContext, session, l10n: FluentLocalization):
    desc = message.text.strip()
    if desc == "0": desc = ""
    await state.update_data(desc=desc)
    
    data = await state.get_data()
    tariff = await session.get(models.SpecialTariff, data['grant_tariff_id'])
    
    text = l10n.format_value("admin-cp-grant-confirm", {
        "name": tariff.name,
        "username": data['username'],
        "tgid": data['tgid'],
        "desc": data['desc']
    })
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=l10n.format_value("admin-cp-btn-confirm"), callback_data="admin_cp_grant_done")],
        [types.InlineKeyboardButton(text=l10n.format_value("admin-cp-btn-cancel"), callback_data="admin_cp_list")]
    ])
    
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "admin_cp_grant_done")
async def cp_grant_execute(callback: types.CallbackQuery, state: FSMContext, session, l10n: FluentLocalization):
    data = await state.get_data()
    tariff = await session.get(models.SpecialTariff, data['grant_tariff_id'])
    
    username = data['username']
    tgid = data['tgid']
    desc = data['desc']
    
    await callback.message.edit_text(l10n.format_value("admin-wait"))
    
    # 1. Calc Duration
    if tariff.duration_months == 0:
        expire_dt = datetime(2099, 2, 19)
    else:
        # Heuristic: months * 30 + floor(months/2)
        days = (tariff.duration_months * 30) + (tariff.duration_months // 2)
        expire_dt = datetime.utcnow() + timedelta(days=days)
        
    try:
        # 2. Create User
        resp = await api.create_custom_user(username, desc)
        # Handle nesting: 'response' -> 'uuid'
        if 'response' in resp:
            uuid = resp['response'].get('uuid') or resp['response'].get('id')
        else:
            uuid = resp.get('uuid') or resp.get('id')
            
        if not uuid:
            raise Exception("No UUID in response")
            
        # 3. Update User
        updates = {
            "trafficLimitBytes": int(tariff.traffic_gb * 1024 * 1024 * 1024),
            "trafficLimitStrategy": "MONTH" if tariff.traffic_gb > 0 else "NO_RESET", 
            "expireAt": expire_dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ").replace("000Z", "Z"),
            "onHold": False
        }
        if tariff.tag:
            updates["tag"] = tariff.tag
        
        if tgid > 0:
            updates["telegramId"] = tgid
            
        await api.update_user(uuid, updates)
        
        # 4. Squad
        if tariff.squad_uuid and tariff.squad_uuid != "0":
             await api.add_user_to_squad(uuid, tariff.squad_uuid)
             
        # 5. Local DB (TG ID)
        if tgid > 0:
            user = await session.get(models.User, tgid)
            if not user:
                # Create
                user = models.User(id=tgid, username=f"imported_{username}", remnawave_uuid=uuid)
                session.add(user)
            else:
                # Update link
                user.remnawave_uuid = uuid
            await session.commit()
            
        # 6. Report
        # 6. Report
        # Try to get subscription link from response
        sub_link = None
        if 'response' in resp:
             sub_link = resp['response'].get('subscriptionUrl')
        else:
             sub_link = resp.get('subscriptionUrl')
             
        if not sub_link:
            # Fallback if API doesn't return it
            sub_link = f"{config.remnawave_url}/sub/{uuid}"

        expire_str = "∞" if tariff.duration_months == 0 else expire_dt.strftime('%d.%m.%Y')
        
        msg = l10n.format_value("admin-cp-grant-success", {
            "username": username,
            "link": sub_link,
            "traffic": tariff.traffic_gb,
            "expire": expire_str
        })
        
        await callback.message.edit_text(msg, parse_mode="Markdown")
        # Add button "To Menu"
        kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text=l10n.format_value("admin-cp-btn-to-menu"), callback_data="admin_cp_list")]])
        await callback.message.edit_reply_markup(reply_markup=kb)
        
    except Exception as e:
        logger.error("grant_error", error=str(e))
        await callback.message.edit_text(l10n.format_value("admin-error", {"error": str(e)}), reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text=l10n.format_value("admin-cp-btn-to-menu"), callback_data="admin_cp_list")]]))

# --- Standard Tariffs Management ---

@router.callback_query(F.data == "admin_tariffs_list")
async def admin_tariffs_list(callback: types.CallbackQuery, state: FSMContext, session, l10n: FluentLocalization):
    stmt = select(models.Tariff).order_by(models.Tariff.price_rub)
    result = await session.execute(stmt)
    tariffs = result.scalars().all()
    
    kb_rows = []
    for t in tariffs:
        # 100₽ | 50* | 1.5$
        curr = f"{int(t.price_rub)}₽/{t.price_stars}⭐️/{t.price_usd}$"
        kb_rows.append([types.InlineKeyboardButton(text=f"{t.name} ({curr})", callback_data=f"t_view_{t.id}")])
    
    kb_rows.append([types.InlineKeyboardButton(text=l10n.format_value("admin-t-create-btn"), callback_data="t_create")])
    kb_rows.append([types.InlineKeyboardButton(text=l10n.format_value("admin-cp-back-btn"), callback_data="admin_menu")])
    
    await callback.message.edit_text(l10n.format_value("admin-t-list-title"), reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb_rows))

@router.callback_query(F.data == "t_create")
async def t_create_start(callback: types.CallbackQuery, state: FSMContext, l10n: FluentLocalization):
    await state.set_state(AdminStates.t_name)
    await callback.message.edit_text(l10n.format_value("admin-t-create-name"), reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text=l10n.format_value("admin-t-create-cancel"), callback_data="admin_tariffs_list")]]))

@router.message(AdminStates.t_name)
async def t_set_name(message: types.Message, state: FSMContext, l10n: FluentLocalization):
    await state.update_data(name=message.text)
    await state.set_state(AdminStates.t_price_rub)
    await message.answer(l10n.format_value("admin-t-create-rub"))

@router.message(AdminStates.t_price_rub)
async def t_set_rub(message: types.Message, state: FSMContext, l10n: FluentLocalization):
    try:
        val = float(message.text)
        await state.update_data(rub=val)
        await state.set_state(AdminStates.t_price_stars)
        await message.answer(l10n.format_value("admin-t-create-stars"))
    except ValueError:
        await message.answer(l10n.format_value("admin-t-val-number"))

@router.message(AdminStates.t_price_stars)
async def t_set_stars(message: types.Message, state: FSMContext, l10n: FluentLocalization):
    try:
        val = int(message.text)
        await state.update_data(stars=val)
        await state.set_state(AdminStates.t_price_usd)
        await message.answer(l10n.format_value("admin-t-create-usd"))
    except ValueError:
        await message.answer(l10n.format_value("admin-t-val-int"))

@router.message(AdminStates.t_price_usd)
async def t_set_usd(message: types.Message, state: FSMContext, l10n: FluentLocalization):
    try:
        val = float(message.text)
        await state.update_data(usd=val)
        await state.set_state(AdminStates.t_days)
        await message.answer(l10n.format_value("admin-t-create-days"))
    except ValueError:
        await message.answer(l10n.format_value("admin-t-val-number"))

@router.message(AdminStates.t_days)
async def t_set_days(message: types.Message, state: FSMContext, l10n: FluentLocalization):
    try:
        val = int(message.text)
        await state.update_data(days=val)
        await state.set_state(AdminStates.t_traffic)
        await message.answer(l10n.format_value("admin-t-create-traffic"))
    except ValueError:
         await message.answer(l10n.format_value("admin-t-val-int"))

@router.message(AdminStates.t_traffic)
async def t_set_traffic(message: types.Message, state: FSMContext, session, l10n: FluentLocalization):
    try:
        limit = int(message.text)
        await state.update_data(traffic=limit)
        await state.set_state(AdminStates.t_squad)
        await message.answer(l10n.format_value("admin-t-ask-squad"))
    except ValueError:
        await message.answer(l10n.format_value("admin-t-val-int"))

@router.message(AdminStates.t_squad)
async def t_set_squad(message: types.Message, state: FSMContext, session, l10n: FluentLocalization):
    try:
        squad_uuid = message.text.strip()
        if squad_uuid == "0":
            squad_uuid = None
            
        data = await state.get_data()
        limit = data['traffic']
        
        t = models.Tariff(
            name=data['name'],
            price_rub=data['rub'],
            price_stars=data['stars'],
            price_usd=data['usd'],
            duration_days=data['days'],
            traffic_limit_gb=limit if limit > 0 else None,
            squad_uuid=squad_uuid,
            is_trial=False,
            is_active=True
        )
        session.add(t)
        await session.commit()
        
        await message.answer(l10n.format_value("admin-t-created", {"name": t.name}), reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text=l10n.format_value("admin-t-list-btn"), callback_data="admin_tariffs_list")]]))
        await state.clear()
        
    except Exception as e:
        await message.answer(f"Error: {e}")

@router.callback_query(F.data.startswith("t_view_"))
async def t_view(callback: types.CallbackQuery, state: FSMContext, session, l10n: FluentLocalization):
    tid = int(callback.data.split("_")[2])
    t = await session.get(models.Tariff, tid)
    
    if not t:
        await callback.answer(l10n.format_value("admin-cp-not-found"))
        return
    
    # Resolve Squad Name
    squad_display = t.squad_uuid or "Default"
    if t.squad_uuid and t.squad_uuid != "0":
        try:
             squad_data = await api.get_squad(t.squad_uuid)
             # Handle response wrapper if present
             s = squad_data.get('response', squad_data)
             
             name = s.get('slug') or s.get('name') or "Unnamed"
             squad_display = f"{name} ({t.squad_uuid})"
        except Exception:
             pass
        
    text = (
        f"{l10n.format_value('admin-t-view-title', {'name': t.name})}\n"
        f"{l10n.format_value('admin-t-view-prices', {'rub': t.price_rub, 'stars': t.price_stars, 'usd': t.price_usd})}\n"
        f"{l10n.format_value('admin-t-view-duration', {'days': t.duration_days})}\n"
        f"{l10n.format_value('admin-t-view-squad', {'squad': squad_display})}\n"
        f"{l10n.format_value('admin-t-view-traffic', {'traffic': t.traffic_limit_gb or 'Unlimited'})}"
    )
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=l10n.format_value("admin-t-btn-grant"), callback_data=f"t_grant_{t.id}")],
        [types.InlineKeyboardButton(text=l10n.format_value("admin-cp-btn-delete"), callback_data=f"t_del_{t.id}")],
        [types.InlineKeyboardButton(text=l10n.format_value("admin-cp-back-btn"), callback_data="admin_tariffs_list")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data.startswith("t_grant_"))
async def t_grant_start(callback: types.CallbackQuery, state: FSMContext, l10n: FluentLocalization):
    tid = int(callback.data.split("_")[2])
    await state.update_data(grant_tariff_id=tid)
    await state.set_state(AdminStates.t_grant_id)
    await callback.message.answer(l10n.format_value("admin-t-grant-ask"), reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text=l10n.format_value("admin-cp-btn-cancel"), callback_data="admin_tariffs_list")]]))
    await callback.answer()

@router.message(AdminStates.t_grant_id)
async def t_grant_process(message: types.Message, state: FSMContext, session, l10n: FluentLocalization):
    try:
        data = await state.get_data()
        tid = data['grant_tariff_id']
        target_user_id = int(message.text.strip())
        
        # Check user exists, create if not
        u = await session.get(models.User, target_user_id)
        if not u:
            # Create user placeholder
            u = models.User(id=target_user_id, language_code="en") # Default EN
            session.add(u)
            await session.flush()

        tariff = await session.get(models.Tariff, tid)
        if not tariff:
            await message.answer(l10n.format_value("admin-error-tariff-not-found"))
            return

        # Create paid order manually
        from bot.services.orders import create_order, fulfill_order
        from bot.services.remnawave import api
        
        # Create order with 0 price (gift)
        order = await create_order(
            user_id=target_user_id,
            tariff_id=tid,
            amount=0.0,
            provider=models.PaymentProvider.MANUAL,
            session=session
        )
        
        order.invoice_id = f"manual_grant_{message.from_user.id}_{datetime.utcnow().timestamp()}"
        await session.commit()
        
        # Fulfill
        success = await fulfill_order(order.id, session)
        
        if success:
             # Refresh user to get remnawave_uuid
             await session.refresh(u)
             
             # Fetch sub link
             link = "N/A"
             if u.remnawave_uuid:
                 try:
                     rw_user = await api.get_user(u.remnawave_uuid)
                     user_data = rw_user.get('response', rw_user)
                     link = user_data.get('subscriptionUrl') or user_data.get('subUrl') or user_data.get('subscription_url') or "Link not found in API"
                 except Exception as e:
                     link = f"Error fetching link: {e}"
             
             display_username = f" (@{escape(u.username)})" if u.username else ""
             
             msg_text = l10n.format_value("admin-t-grant-success-full", {
                 "tariff": escape(tariff.name),
                 "user_id": target_user_id,
                 "username": display_username,
                 "days": tariff.duration_days,
                 "traffic": tariff.traffic_limit_gb or "∞",
                 "link": link
             })
             
             await message.answer(msg_text, parse_mode="HTML")
             
             # Notify user
             try:
                 await message.bot.send_message(target_user_id, f"🎁 You have been granted a subscription: {tariff.name}!")
             except:
                 # User blocked bot or not started
                 pass
        else:
             await message.answer(l10n.format_value("admin-t-grant-error", {"error": "Fulfillment failed"}))
             
        await state.clear()
        
    except ValueError:
        await message.answer(l10n.format_value("admin-t-val-int"))
    except Exception as e:
        logger.error("grant_tariff_error", error=str(e))
        await message.answer(l10n.format_value("admin-t-grant-error", {"error": str(e)}))
    
    await cmd_admin(message, state, l10n)

from sqlalchemy.exc import IntegrityError

@router.callback_query(F.data.startswith("t_del_"))
async def t_delete(callback: types.CallbackQuery, session, l10n: FluentLocalization):
    tid = int(callback.data.split("_")[2])
    try:
        # 1. CASCADE: Delete associated orders first
        # USER REQUESTED: "if tariff is deleted, orders should be too"
        del_orders_stmt = delete(models.Order).where(models.Order.tariff_id == tid)
        await session.execute(del_orders_stmt)
        
        # 2. Delete tariff
        stmt = delete(models.Tariff).where(models.Tariff.id == tid)
        await session.execute(stmt)
        await session.commit()
        
        await callback.answer(l10n.format_value("admin-t-deleted", {"name": "Deleted"}))
        # Refresh list
        await callback.message.delete()
        await cmd_tariffs_list(callback.message, None, session, l10n)
        
    except Exception as e:
        await session.rollback()
        await callback.answer(f"Error: {e}", show_alert=True)

# --- Promo Codes Management ---

@router.callback_query(F.data == "admin_promos_list")
async def admin_promos_list(callback: types.CallbackQuery, session, l10n: FluentLocalization):
    stmt = select(models.Promocode).where(models.Promocode.is_trial_only == True)
    result = await session.execute(stmt)
    promos = result.scalars().all()
    
    text = "🎟 **Trial Promo Codes**\n\n"
    if not promos:
        text += "No promo codes found."
    else:
        for p in promos:
            text += f"• <code>{p.code}</code> - {p.used_count}/{p.max_uses or '∞'} uses\n"
            text += f"  [Delete: /del_promo_{p.code}]\n\n"
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="➕ Add Promo", callback_data="admin_promo_add")],
        [types.InlineKeyboardButton(text="🔙 Back", callback_data="admin_panel")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "admin_promo_add")
async def admin_promo_add_start(callback: types.CallbackQuery, state: FSMContext, l10n: FluentLocalization):
    await callback.message.edit_text("Enter the promo code string (e.g. TRIAL2026):")
    await state.set_state(AdminStates.promo_code)

@router.message(AdminStates.promo_code)
async def admin_promo_input_code(message: types.Message, state: FSMContext, l10n: FluentLocalization):
    if message.from_user.id not in config.admin_ids: return
    code = message.text.strip()
    await state.update_data(promo_code=code)
    await message.answer(f"Promo Code: {code}\nNow enter maximum number of uses (0 for unlimited):")
    await state.set_state(AdminStates.promo_uses)

@router.message(AdminStates.promo_uses)
async def admin_promo_input_uses(message: types.Message, state: FSMContext, session, l10n: FluentLocalization):
    if message.from_user.id not in config.admin_ids: return
    try:
        uses = int(message.text.strip())
        data = await state.get_data()
        code = data.get("promo_code")
        
        promo = models.Promocode(
            code=code,
            max_uses=uses,
            is_trial_only=True,
            value=0.0,
            is_percent=True
        )
        session.add(promo)
        await session.commit()
        
        await message.answer(f"✅ Promo code ` {code} ` created with {uses or 'unlimited'} uses.")
        await state.clear()
        await cmd_admin(message, state, l10n)
        
    except ValueError:
        await message.answer(l10n.format_value("admin-error-invalid-number"))
    except Exception as e:
        await session.rollback()
        await message.answer(f"Error creating promo code: {e}")

@router.message(F.text.startswith("/del_promo_"))
async def admin_promo_delete(message: types.Message, session, state: FSMContext, l10n: FluentLocalization):
    if message.from_user.id not in config.admin_ids: return
    code = message.text.replace("/del_promo_", "").strip()
    from sqlalchemy import delete
    stmt = delete(models.Promocode).where(models.Promocode.code == code, models.Promocode.is_trial_only == True)
    await session.execute(stmt)
    await session.commit()
    await message.answer(f"✅ Promo code ` {code} ` deleted.")
    await cmd_admin(message, state, l10n)
