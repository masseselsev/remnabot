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
from bot.handlers.user import UserStates

logger = structlog.get_logger()

router = Router()

class AdminStates(StatesGroup):
    menu = State()
    edit_trial_days = State()
    edit_trial_traffic = State()
    edit_trial_plan = State()
    
    # Tariffs (formerly Special Tariffs / Custom Plans)
    t_name = State()
    t_squad = State()
    t_traffic = State()
    t_duration = State()
    t_tag = State()
    
    # Change User Tariff Wizard
    ch_tar_select = State()
    ch_tar_dur = State()
    ch_tar_manual = State()
    ch_tar_confirm = State()
    
    # User Search
    search_user_id = State()
    
    # Manual Grant Flow
    prov_username = State()
    prov_tgid = State()
    prov_desc = State()

    # Welcome Message Settings
    welcome_select_lang = State()
    welcome_input_text = State()

    # Promo Codes
    promo_code = State()
    promo_uses = State()
    
    # Routing Settings
    routing_edit_desc = State()
    routing_add_btn_title = State()
    routing_add_btn_url = State()
    routing_edit_btn_title = State()
    routing_edit_btn_url = State()

async def resolve_squads_display(squad_uuid_str: str) -> str:
    if not squad_uuid_str or squad_uuid_str in ["0", "None"]:
        return "N/A"
    
    from bot.services.remnawave import api
    uuids = [s.strip() for s in squad_uuid_str.split(",") if s.strip()]
    if not uuids:
        return "N/A"
        
    names = []
    for uid in uuids:
        try:
            data = await api.get_squad(uid)
            s = data.get('response', data)
            name = s.get('slug') or s.get('name') or uid[:8]
            names.append(f"{name} ({uid[:8]}...)")
        except:
            names.append(f"??? ({uid[:8]}...)")
    
    return ", ".join(names)

async def get_main_kb(l10n: FluentLocalization):
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=l10n.format_value("admin-btn-tariffs"), callback_data="admin_tariffs_list")],
        [types.InlineKeyboardButton(text=l10n.format_value("admin-btn-trial"), callback_data="admin_trial")],
        [types.InlineKeyboardButton(text=l10n.format_value("admin-btn-search-user"), callback_data="admin_search_user")],
        [types.InlineKeyboardButton(text=l10n.format_value("admin-btn-promos"), callback_data="admin_promos_list")],
        [types.InlineKeyboardButton(text=l10n.format_value("admin-btn-welcome"), callback_data="admin_welcome_mgmt")],
        [types.InlineKeyboardButton(text=l10n.format_value("admin-btn-routing"), callback_data="admin_routing_menu")],
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
    btn_instruction = l10n.format_value("btn-instruction")
    
    kb = [
        [types.KeyboardButton(text=btn_profile), types.KeyboardButton(text=btn_trial)],
        [types.KeyboardButton(text=btn_support), types.KeyboardButton(text=btn_instruction)]
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
    default_welcome = "Привет, {$name}! 🪿" if lang == "ru" else "Welcome, {$name}! 🪿"
    current_val = await SettingsService.get_setting(current_key, default_welcome)
    
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

@router.message((F.contact | F.forward_origin), ~StateFilter(UserStates.trial_friend_contact))
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
        kb_rows.append([types.InlineKeyboardButton(text=f"🔄 Сменить тариф: {uname}", callback_data=f"adm_chtar_{uuid}")])
        
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
    kb_rows.append([types.InlineKeyboardButton(text=l10n.format_value("btn-back"), callback_data="adm_back_user_search")])
        
    # No convenient back button without re-generating profile, but this replaces the message inline or opens a new one
    await callback.message.edit_text(l10n.format_value("devices-select-account"), reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb_rows))


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
        await callback.answer(l10n.format_value("admin-error-context-lost"), show_alert=True)
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
        await callback.answer(l10n.format_value("admin-error-context-lost"), show_alert=True)
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
    squad_display = await resolve_squads_display(squad_val)

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

# --- Tariffs Management (replacing old Special Tariffs) ---

@router.callback_query(F.data == "admin_tariffs_list")
async def tariff_list(callback: types.CallbackQuery, state: FSMContext, session, l10n: FluentLocalization):
    stmt = select(models.Tariff).order_by(models.Tariff.id)
    result = await session.execute(stmt)
    tariffs = result.scalars().all()
    
    kb_rows = []
    for t in tariffs:
        kb_rows.append([types.InlineKeyboardButton(text=f"💎 {t.name}", callback_data=f"t_view_{t.id}")])
    
    kb_rows.append([types.InlineKeyboardButton(text=l10n.format_value("admin-cp-create-btn"), callback_data="t_create")])
    kb_rows.append([types.InlineKeyboardButton(text=l10n.format_value("admin-cp-back-btn"), callback_data="admin_menu")])
    
    text = f"{l10n.format_value('admin-cp-title')}\n{l10n.format_value('admin-cp-list-desc')}"
    await callback.message.edit_text(text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb_rows), parse_mode="Markdown")

@router.callback_query(F.data == "t_create")
async def t_start_create(callback: types.CallbackQuery, state: FSMContext, l10n: FluentLocalization):
    await state.set_state(AdminStates.t_name)
    await callback.message.edit_text(l10n.format_value("admin-cp-create-step1"), reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text=l10n.format_value("admin-cp-back-btn"), callback_data="admin_tariffs_list")]]), parse_mode="Markdown")

@router.message(AdminStates.t_name)
async def t_set_name(message: types.Message, state: FSMContext, l10n: FluentLocalization):
    await state.update_data(name=message.text)
    await state.set_state(AdminStates.t_squad)
    await message.answer(l10n.format_value("admin-cp-create-step2"))

@router.message(AdminStates.t_squad)
async def t_set_squad(message: types.Message, state: FSMContext, l10n: FluentLocalization):
    await state.update_data(squad=message.text.strip())
    await state.set_state(AdminStates.t_traffic)
    await message.answer(l10n.format_value("admin-cp-create-step3"))

@router.message(AdminStates.t_traffic)
async def t_set_traffic(message: types.Message, state: FSMContext, l10n: FluentLocalization):
    try:
        limit = float(message.text.strip().replace(",", "."))
        await state.update_data(traffic=limit)
        await state.set_state(AdminStates.t_duration)
        await message.answer(l10n.format_value("admin-cp-create-step4"))
    except ValueError:
        await message.answer(l10n.format_value("admin-cp-val-number"))

@router.message(AdminStates.t_duration)
async def t_set_duration(message: types.Message, state: FSMContext, l10n: FluentLocalization):
    try:
        dur = int(message.text.strip())
        await state.update_data(duration=dur)
        await state.set_state(AdminStates.t_tag)
        await message.answer(l10n.format_value("admin-cp-create-step5"))
    except ValueError:
        await message.answer(l10n.format_value("admin-cp-val-int"))

@router.message(AdminStates.t_tag)
async def t_set_tag(message: types.Message, state: FSMContext, session, l10n: FluentLocalization):
    tag = message.text.strip()
    if tag.lower() in ["none", "0"]:
        tag = None
        
    data = await state.get_data()
    edit_id = data.get('edit_tariff_id')
    
    if edit_id:
        tariff = await session.get(models.Tariff, edit_id)
        if tariff:
            tariff.name = data['name']
            tariff.squad_uuid = data['squad']
            tariff.traffic_gb = data['traffic']
            tariff.duration_months = data['duration']
            tariff.tag = tag
            await session.commit()
            await message.answer(l10n.format_value("admin-cp-created", {"name": tariff.name}))
    else:
        new_tariff = models.Tariff(
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

@router.callback_query(F.data.startswith("t_edit_"))
async def t_edit_start(callback: types.CallbackQuery, state: FSMContext, l10n: FluentLocalization):
    try:
        tid = int(callback.data.split("_")[2])
        await state.update_data(edit_tariff_id=tid)
        await t_start_create(callback, state, l10n)
    except:
        pass

# View Tariff

@router.callback_query(F.data.startswith("t_view_"))
async def t_view(callback: types.CallbackQuery, state: FSMContext, session, l10n: FluentLocalization):
    try:
        tariff_id = int(callback.data.split("_")[2])
    except (IndexError, ValueError):
        await callback.answer(l10n.format_value("admin-invalid-id"))
        return

    tariff = await session.get(models.Tariff, tariff_id)
    
    if not tariff:
        await callback.answer(l10n.format_value("admin-cp-not-found"))
        await tariff_list(callback, state, session, l10n)
        return

    dur_display = "∞" if tariff.duration_months == 0 else f"{tariff.duration_months} {l10n.format_value('admin-month-short')}"

    # Resolve Squad Name
    squad_display = await resolve_squads_display(tariff.squad_uuid)

    text = (
        f"{l10n.format_value('admin-cp-view-title', {'name': tariff.name})}\n\n"
        f"{l10n.format_value('admin-cp-view-squad', {'squad': squad_display})}\n"
        f"{l10n.format_value('admin-cp-view-traffic', {'traffic': tariff.traffic_gb})}\n"
        f"{l10n.format_value('admin-cp-view-duration', {'duration': dur_display})}\n"
        f"{l10n.format_value('admin-cp-view-tag', {'tag': tariff.tag or 'None'})}"
    )
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=l10n.format_value("admin-cp-btn-grant"), callback_data=f"t_grant_{tariff.id}")],
        [types.InlineKeyboardButton(text=l10n.format_value("admin-cp-btn-edit"), callback_data=f"t_edit_{tariff.id}")],
        [types.InlineKeyboardButton(text=l10n.format_value("admin-cp-btn-delete"), callback_data=f"t_delete_{tariff.id}")],
        [types.InlineKeyboardButton(text=l10n.format_value("admin-cp-back-btn"), callback_data="admin_tariffs_list")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data.startswith("t_delete_"))
async def t_delete(callback: types.CallbackQuery, state: FSMContext, session, l10n: FluentLocalization):
    tariff_id = int(callback.data.split("_")[2])
    stmt = delete(models.Tariff).where(models.Tariff.id == tariff_id)
    await session.execute(stmt)
    await session.commit()
    await callback.answer(l10n.format_value("admin-deleted"))
    await tariff_list(callback, state, session, l10n)

# --- Change User Tariff Flow ---

@router.callback_query(F.data.startswith("adm_chtar_"))
async def admin_change_tariff_start(callback: types.CallbackQuery, state: FSMContext, session, l10n: FluentLocalization):
    user_uuid = callback.data.split("_")[2]
    await state.update_data(ch_uuid=user_uuid)
    
    # Show list of available tariffs
    stmt = select(models.Tariff).order_by(models.Tariff.id)
    result = await session.execute(stmt)
    tariffs = result.scalars().all()
    
    kb_rows = []
    for t in tariffs:
        kb_rows.append([types.InlineKeyboardButton(text=f"📦 {t.name}", callback_data=f"adm_ch_t_{t.id}")])
    
    kb_rows.append([types.InlineKeyboardButton(text=l10n.format_value("btn-cancel"), callback_data="adm_back_user_search")])
    
    await callback.message.edit_text(
        l10n.format_value("admin-ch-tar-select-title"),
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb_rows),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("adm_ch_t_"))
async def admin_change_tariff_duration(callback: types.CallbackQuery, state: FSMContext, session, l10n: FluentLocalization):
    tariff_id = int(callback.data.split("_")[3])
    tariff = await session.get(models.Tariff, tariff_id)
    if not tariff: return
    
    await state.update_data(ch_tariff_id=tariff_id)
    data = await state.get_data()
    user_uuid = data.get('ch_uuid')
    
    kb_rows = [
        [types.InlineKeyboardButton(text="📅 На год (365 дн)", callback_data="adm_ch_dur_year")],
        [types.InlineKeyboardButton(text="♾ Навсегда (2099)", callback_data="adm_ch_dur_inf")],
        [types.InlineKeyboardButton(text="🔢 Ввести вручную (мес)", callback_data="adm_ch_dur_manual")],
        [types.InlineKeyboardButton(text=l10n.format_value("btn-back"), callback_data=f"adm_chtar_{user_uuid}")]
    ]
    
    await callback.message.edit_text(
        l10n.format_value("admin-ch-tar-dur-title", {"tariff": tariff.name, "account": user_uuid[:8]}),
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=kb_rows),
        parse_mode="Markdown"
    )

@router.callback_query(F.data.startswith("adm_ch_dur_"))
async def admin_change_tariff_duration_select(callback: types.CallbackQuery, state: FSMContext, l10n: FluentLocalization):
    dur_type = callback.data.split("_")[3]
    
    if dur_type == "manual":
        await state.set_state(AdminStates.ch_tar_manual)
        await callback.message.edit_text(
            l10n.format_value("admin-ch-tar-manual-ask"),
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text=l10n.format_value("btn-cancel"), callback_data="admin_menu")]])
        )
        return
        
    await state.update_data(ch_dur_type=dur_type)
    await admin_change_tariff_confirm_view(callback.message, state, l10n)

@router.message(AdminStates.ch_tar_manual)
async def admin_change_tariff_manual_input(message: types.Message, state: FSMContext, l10n: FluentLocalization):
    try:
        months = int(message.text.strip())
        if months < 0: raise ValueError
        await state.update_data(ch_months=months, ch_dur_type="manual")
        await admin_change_tariff_confirm_view(message, state, l10n)
    except ValueError:
        await message.answer(l10n.format_value("admin-error-invalid-number"))

async def admin_change_tariff_confirm_view(message_or_callback_message: types.Message, state: FSMContext, l10n: FluentLocalization):
    data = await state.get_data()
    from bot.database import models
    from bot.database.core import get_session
    
    async with get_session() as session:
        t = await session.get(models.Tariff, data['ch_tariff_id'])
        
    dur_type = data['ch_dur_type']
    dur_str = ""
    if dur_type == "year": dur_str = "1 Year (365 days)"
    elif dur_type == "inf": dur_str = "Forever (2099)"
    else: dur_str = f"{data['ch_months']} months"
    
    text = l10n.format_value("admin-ch-tar-confirm-title", {
        "tg_id": data.get('search_target_id') or "Unknown",
        "uuid": data['ch_uuid'],
        "tariff": t.name,
        "duration": dur_str
    })
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✅ Выполнить", callback_data="adm_ch_exec")],
        [types.InlineKeyboardButton(text="❌ Отмена", callback_data="admin_menu")]
    ])
    
    if isinstance(message_or_callback_message, types.Message):
         await message_or_callback_message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
         await message_or_callback_message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "adm_ch_exec")
async def admin_change_tariff_execute(callback: types.CallbackQuery, state: FSMContext, session, l10n: FluentLocalization):
    data = await state.get_data()
    user_uuid = data['ch_uuid']
    tariff_id = data['ch_tariff_id']
    dur_type = data['ch_dur_type']
    tg_id = data.get('search_target_id')
    
    t = await session.get(models.Tariff, tariff_id)
    if not t: return
    
    await callback.message.edit_text(l10n.format_value("admin-wait"))
    
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    if dur_type == "year":
        expire_dt = now + timedelta(days=365)
        dur_display = "1 год"
    elif dur_type == "inf":
        expire_dt = datetime(2099, 1, 1, tzinfo=timezone.utc)
        dur_display = "Навсегда"
    else:
        months = data.get('ch_months', 0)
        days = (months * 30) + (months // 2)
        expire_dt = now + timedelta(days=days)
        dur_display = f"{months} мес."
        
    try:
        from bot.services.remnawave import api
        # 1. Update Remnawave
        updates = {
            "trafficLimitBytes": int(t.traffic_gb * 1024 * 1024 * 1024),
            "trafficLimitStrategy": "MONTH" if t.traffic_gb > 0 else "NO_RESET",
            "expireAt": expire_dt.isoformat().replace("+00:00", "Z"),
            "activeInternalSquads": [t.squad_uuid] if t.squad_uuid and t.squad_uuid != "0" else []
        }
        if t.tag:
            updates["tag"] = t.tag
            
        await api.update_user(user_uuid, updates)
        
        # 2. Success Report
        await callback.message.edit_text(l10n.format_value("admin-ch-tar-success"), reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="🔙 В меню", callback_data="admin_menu")]]))
        
        # 3. Notify User
        if tg_id:
            try:
                msg = l10n.format_value("admin-ch-tar-notify-user", {"tariff": t.name, "duration": dur_display})
                await callback.bot.send_message(tg_id, msg, parse_mode="Markdown")
            except: pass
            
        # 4. Notify Admin Group
        if config.admin_group_id:
            try:
                admin_msg = l10n.format_value("admin-ch-tar-notify-admin-group", {
                    "tg_id": tg_id or "N/A",
                    "uuid": user_uuid,
                    "tariff": t.name,
                    "duration": dur_display,
                    "admin": f"@{callback.from_user.username or callback.from_user.id}"
                })
                await callback.bot.send_message(config.admin_group_id, admin_msg, parse_mode="HTML")
            except: pass
            
    except Exception as e:
        logger.error("change_tariff_error", error=str(e), user_uuid=user_uuid)
        await callback.message.edit_text(f"❌ Error: {e}", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")]]))
        
    await state.clear()

# --- Manual Grant Flow ---

@router.callback_query(F.data.startswith("t_grant_"))
async def t_grant_start(callback: types.CallbackQuery, state: FSMContext, session, l10n: FluentLocalization):
    tariff_id = int(callback.data.split("_")[2])
    tariff = await session.get(models.Tariff, tariff_id)
    if not tariff: return
    
    await state.update_data(grant_tariff_id=tariff.id)
    await state.set_state(AdminStates.prov_username)
    await callback.message.edit_text(l10n.format_value("admin-cp-grant-step1", {"name": tariff.name}), reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text=l10n.format_value("admin-cp-back-btn"), callback_data=f"t_view_{tariff.id}")]]), parse_mode="Markdown")

@router.message(AdminStates.prov_username)
async def t_grant_username(message: types.Message, state: FSMContext, l10n: FluentLocalization):
    await state.update_data(username=message.text.strip())
    await state.set_state(AdminStates.prov_tgid)
    await message.answer(l10n.format_value("admin-cp-grant-step2"))

@router.message(AdminStates.prov_tgid)
async def t_grant_tgid(message: types.Message, state: FSMContext, l10n: FluentLocalization):
    try:
        val = int(message.text)
        await state.update_data(tgid=val)
        await state.set_state(AdminStates.prov_desc)
        await message.answer(l10n.format_value("admin-cp-grant-step3"))
    except ValueError:
        await message.answer(l10n.format_value("admin-cp-val-error"))

@router.message(AdminStates.prov_desc)
async def t_grant_desc(message: types.Message, state: FSMContext, session, l10n: FluentLocalization):
    desc = message.text.strip()
    if desc == "0": desc = ""
    await state.update_data(desc=desc)
    
    data = await state.get_data()
    tariff = await session.get(models.Tariff, data['grant_tariff_id'])
    
    text = l10n.format_value("admin-cp-grant-confirm", {
        "name": tariff.name,
        "username": data['username'],
        "tgid": data['tgid'],
        "desc": data['desc']
    })
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=l10n.format_value("admin-cp-btn-confirm"), callback_data="t_grant_done")],
        [types.InlineKeyboardButton(text=l10n.format_value("admin-cp-btn-cancel"), callback_data="admin_tariffs_list")]
    ])
    
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

@router.callback_query(F.data == "t_grant_done")
async def t_grant_execute(callback: types.CallbackQuery, state: FSMContext, session, l10n: FluentLocalization):
    data = await state.get_data()
    tariff = await session.get(models.Tariff, data['grant_tariff_id'])
    
    username = data['username']
    tgid = data['tgid']
    desc = data['desc']
    
    await callback.message.edit_text(l10n.format_value("admin-wait"))
    
    from datetime import datetime, timedelta
    if tariff.duration_months == 0:
        expire_dt = datetime(2099, 2, 19)
    else:
        days = (tariff.duration_months * 30) + (tariff.duration_months // 2)
        expire_dt = datetime.utcnow() + timedelta(days=days)
        
    try:
        from bot.services.remnawave import api
        resp = await api.create_custom_user(username, desc)
        if 'response' in resp:
            uuid = resp['response'].get('uuid') or resp['response'].get('id')
        else:
            uuid = resp.get('uuid') or resp.get('id')
            
        if not uuid:
            raise Exception("No UUID in response")
            
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
        
        if tariff.squad_uuid and tariff.squad_uuid != "0":
            await api.add_user_to_squad(uuid, tariff.squad_uuid)
             
        if tgid > 0:
            user = await session.get(models.User, tgid)
            if not user:
                user = models.User(id=tgid, username=f"imported_{username}", remnawave_uuid=uuid)
                session.add(user)
            else:
                user.remnawave_uuid = uuid
            await session.commit()
            
        sub_link = None
        if 'response' in resp:
             sub_link = resp['response'].get('subscriptionUrl')
        else:
             sub_link = resp.get('subscriptionUrl')
             
        if not sub_link:
            sub_link = f"{config.remnawave_url}/sub/{uuid}"

        expire_str = "∞" if tariff.duration_months == 0 else expire_dt.strftime('%d.%m.%Y')
        
        msg = l10n.format_value("admin-cp-grant-success", {
            "username": username,
            "link": sub_link,
            "traffic": tariff.traffic_gb,
            "expire": expire_str
        })
        
        await callback.message.edit_text(msg, parse_mode="Markdown")
        kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text=l10n.format_value("admin-cp-btn-to-menu"), callback_data="admin_tariffs_list")]])
        await callback.message.edit_reply_markup(reply_markup=kb)
        
    except Exception as e:
        logger.error("grant_error", error=str(e))
        await callback.message.edit_text(l10n.format_value("admin-error", {"error": str(e)}), reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text=l10n.format_value("admin-cp-btn-to-menu"), callback_data="admin_tariffs_list")]]))

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
        [types.InlineKeyboardButton(text=l10n.format_value("admin-cp-back-btn"), callback_data="admin_menu")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "admin_promo_add")
async def admin_promo_add_start(callback: types.CallbackQuery, state: FSMContext, l10n: FluentLocalization):
    await callback.message.edit_text(l10n.format_value("admin-promo-ask"))
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

# --- Routing Settings --- #
@router.callback_query(F.data == "admin_routing_menu")
async def admin_routing_menu(callback: types.CallbackQuery, state: FSMContext, l10n: FluentLocalization):
    if callback.from_user.id not in config.admin_ids: return
    
    settings = await SettingsService.get_routing_settings()
    desc = settings.get("description") or "N/A"
    btns = settings.get("buttons") or []
    
    text = (
        f"{l10n.format_value('admin-routing-title')}\n\n"
        f"{l10n.format_value('admin-routing-desc', {'desc': desc})}\n\n"
        f"{l10n.format_value('admin-routing-btns-count', {'count': len(btns)})}"
    )
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=l10n.format_value("admin-routing-btn-edit-desc"), callback_data="admin_routing_edit_desc")],
        [types.InlineKeyboardButton(text=l10n.format_value("admin-routing-btn-manage"), callback_data="admin_routing_manage_list")],
        [types.InlineKeyboardButton(text=l10n.format_value("admin-routing-btn-add-button"), callback_data="admin_routing_add_btn")],
        [types.InlineKeyboardButton(text=l10n.format_value("admin-routing-btn-clear-buttons"), callback_data="admin_routing_clear")],
        [types.InlineKeyboardButton(text=l10n.format_value("admin-btn-back"), callback_data="admin_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

@router.callback_query(F.data == "admin_routing_edit_desc")
async def admin_routing_edit_desc(callback: types.CallbackQuery, state: FSMContext, l10n: FluentLocalization):
    await state.set_state(AdminStates.routing_edit_desc)
    await callback.message.answer(l10n.format_value("admin-routing-input-desc"))
    await callback.answer()

@router.message(AdminStates.routing_edit_desc)
async def process_routing_desc(message: types.Message, state: FSMContext, l10n: FluentLocalization):
    settings = await SettingsService.get_routing_settings()
    settings["description"] = message.text
    await SettingsService.update_routing_settings(settings)
    await message.answer(l10n.format_value("admin-routing-success"))
    await state.clear()
    await cmd_admin(message, state, l10n)

@router.callback_query(F.data == "admin_routing_add_btn")
async def admin_routing_add_btn_start(callback: types.CallbackQuery, state: FSMContext, l10n: FluentLocalization):
    await state.set_state(AdminStates.routing_add_btn_title)
    await callback.message.answer(l10n.format_value("admin-routing-input-btn-title"))
    await callback.answer()

@router.message(AdminStates.routing_add_btn_title)
async def process_routing_btn_title(message: types.Message, state: FSMContext, l10n: FluentLocalization):
    await state.update_data(btn_title=message.text)
    await state.set_state(AdminStates.routing_add_btn_url)
    await message.answer(l10n.format_value("admin-routing-input-btn-url"))

@router.message(AdminStates.routing_add_btn_url)
async def process_routing_btn_url(message: types.Message, state: FSMContext, l10n: FluentLocalization):
    url = message.text.strip()
    if not url.startswith("happ://"):
        await message.answer("❌ Ошибка: Ссылка должна начинаться с `happ://` (например, `happ://routing/config`)")
        return

    full_url = f"https://go.cyni.cc/?url={url}"
    data = await state.get_data()
    title = data.get("btn_title")
    
    settings = await SettingsService.get_routing_settings()
    if "buttons" not in settings: settings["buttons"] = []
    settings["buttons"].append({"title": title, "url": full_url})
    
    await SettingsService.update_routing_settings(settings)
    await message.answer(l10n.format_value("admin-routing-success"))
    await state.clear()
    await cmd_admin(message, state, l10n)

@router.callback_query(F.data == "admin_routing_clear")
async def admin_routing_clear(callback: types.CallbackQuery, state: FSMContext, l10n: FluentLocalization):
    settings = await SettingsService.get_routing_settings()
    settings["buttons"] = []
    await SettingsService.update_routing_settings(settings)
    await callback.answer(l10n.format_value("admin-routing-success"))
    await admin_routing_menu(callback, state, l10n)

# --- Button Management List --- #
@router.callback_query(F.data == "admin_routing_manage_list")
async def admin_routing_manage_list(callback: types.CallbackQuery, l10n: FluentLocalization):
    settings = await SettingsService.get_routing_settings()
    btns = settings.get("buttons") or []
    
    keyboard_grid = []
    for idx, btn in enumerate(btns):
        keyboard_grid.append([types.InlineKeyboardButton(
            text=btn.get("title") or f"Button {idx+1}", 
            callback_data=f"admin_routing_view_{idx}"
        )])
        
    keyboard_grid.append([types.InlineKeyboardButton(text=l10n.format_value("admin-btn-back"), callback_data="admin_routing_menu")])
    kb = types.InlineKeyboardMarkup(inline_keyboard=keyboard_grid)
    
    await callback.message.edit_text(l10n.format_value("admin-routing-manage-title"), reply_markup=kb)
    await callback.answer()

@router.callback_query(F.data.startswith("admin_routing_view_"))
async def admin_routing_item_menu(callback: types.CallbackQuery, l10n: FluentLocalization):
    idx = int(callback.data.split("_")[-1])
    settings = await SettingsService.get_routing_settings()
    btns = settings.get("buttons") or []
    
    if idx >= len(btns):
        await callback.answer("Error: Button not found")
        await admin_routing_manage_list(callback, l10n)
        return
        
    btn = btns[idx]
    text = l10n.format_value("admin-routing-item-edit-title", {"title": btn["title"], "url": btn["url"]})
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=l10n.format_value("admin-routing-btn-edit-title"), callback_data=f"admin_routing_edit_title_{idx}")],
        [types.InlineKeyboardButton(text=l10n.format_value("admin-routing-btn-edit-url"), callback_data=f"admin_routing_edit_url_{idx}")],
        [types.InlineKeyboardButton(text=l10n.format_value("admin-routing-btn-delete"), callback_data=f"admin_routing_delete_{idx}")],
        [types.InlineKeyboardButton(text=l10n.format_value("admin-btn-back"), callback_data="admin_routing_manage_list")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
    await callback.answer()

@router.callback_query(F.data.startswith("admin_routing_delete_"))
async def admin_routing_delete_btn(callback: types.CallbackQuery, l10n: FluentLocalization):
    idx = int(callback.data.split("_")[-1])
    settings = await SettingsService.get_routing_settings()
    btns = settings.get("buttons") or []
    
    if idx < len(btns):
        btns.pop(idx)
        settings["buttons"] = btns
        await SettingsService.update_routing_settings(settings)
        await callback.answer(l10n.format_value("admin-routing-success"))
    
    await admin_routing_manage_list(callback, l10n)

# --- Edit Button Handlers --- #
@router.callback_query(F.data.startswith("admin_routing_edit_title_"))
async def admin_routing_edit_title_start(callback: types.CallbackQuery, state: FSMContext, l10n: FluentLocalization):
    idx = int(callback.data.split("_")[-1])
    await state.set_state(AdminStates.routing_edit_btn_title)
    await state.update_data(edit_idx=idx)
    await callback.message.answer(l10n.format_value("admin-routing-input-btn-title"))
    await callback.answer()

@router.message(AdminStates.routing_edit_btn_title)
async def process_routing_edit_title(message: types.Message, state: FSMContext, l10n: FluentLocalization):
    data = await state.get_data()
    idx = data.get("edit_idx")
    
    settings = await SettingsService.get_routing_settings()
    btns = settings.get("buttons") or []
    
    if idx is not None and idx < len(btns):
        btns[idx]["title"] = message.text
        settings["buttons"] = btns
        await SettingsService.update_routing_settings(settings)
        await message.answer(l10n.format_value("admin-routing-success"))
    
    await state.clear()
    await cmd_admin(message, state, l10n)

@router.callback_query(F.data.startswith("admin_routing_edit_url_"))
async def admin_routing_edit_url_start(callback: types.CallbackQuery, state: FSMContext, l10n: FluentLocalization):
    idx = int(callback.data.split("_")[-1])
    await state.set_state(AdminStates.routing_edit_btn_url)
    await state.update_data(edit_idx=idx)
    await callback.message.answer(l10n.format_value("admin-routing-input-btn-url"))
    await callback.answer()

@router.message(AdminStates.routing_edit_btn_url)
async def process_routing_edit_url(message: types.Message, state: FSMContext, l10n: FluentLocalization):
    url = message.text.strip()
    if not url.startswith("happ://"):
        await message.answer("❌ Ошибка: Ссылка должна начинаться с `happ://` (например, `happ://routing/config`)")
        return

    full_url = f"https://go.cyni.cc/?url={url}"
    data = await state.get_data()
    idx = data.get("edit_idx")
    
    settings = await SettingsService.get_routing_settings()
    btns = settings.get("buttons") or []
    
    if idx is not None and idx < len(btns):
        btns[idx]["url"] = full_url
        settings["buttons"] = btns
        await SettingsService.update_routing_settings(settings)
        await message.answer(l10n.format_value("admin-routing-success"))
    
    await state.clear()
    await cmd_admin(message, state, l10n)
