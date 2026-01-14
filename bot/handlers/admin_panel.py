from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from fluent.runtime import FluentLocalization
from bot.config import config
from bot.services.settings import SettingsService
from bot.database import models
from sqlalchemy import select, delete
from bot.services.remnawave import api
from datetime import datetime, timedelta
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

async def get_main_kb():
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🎁 Настройки Триала", callback_data="admin_trial")],
        [types.InlineKeyboardButton(text="💎 Спецтарифы", callback_data="admin_cp_list")],
        [types.InlineKeyboardButton(text="❌ Выйти", callback_data="admin_exit")]
    ])

# ... cmd_admin ...

@router.message(Command("admin"))
async def cmd_admin(message: types.Message, state: FSMContext):
    if message.from_user.id not in config.admin_ids:
        return
        
    await state.clear()
    await message.answer("🔧 **Админ-панель**\nВыберите раздел:", reply_markup=await get_main_kb(), parse_mode="Markdown")

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
        [types.KeyboardButton(text=btn_shop), types.KeyboardButton(text=btn_profile)],
        [types.KeyboardButton(text=btn_trial), types.KeyboardButton(text=btn_support)]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    await callback.message.answer("👋 Вы вышли из админ-панели.", reply_markup=keyboard)

@router.callback_query(F.data == "admin_menu")
async def back_to_menu(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🔧 **Админ-панель**\nВыберите раздел:", reply_markup=await get_main_kb(), parse_mode="Markdown")

# --- Trial Settings ---

@router.callback_query(F.data == "admin_trial")
async def trial_settings_menu(callback: types.CallbackQuery, state: FSMContext):
    settings = await SettingsService.get_trial_settings()
    
    text = (
        "🎁 **Настройки Триала**\n\n"
        f"⏳ Длительность: `{settings['days']}` дней\n"
        f"📊 Трафик: `{settings['traffic']}` GB\n"
        f"🆔 Internal Squad UUID: `{settings['squad_uuid']}`"
    )
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="✏️ Задать Дни", callback_data="a_edit_days"),
         types.InlineKeyboardButton(text="✏️ Задать Трафик", callback_data="a_edit_traffic")],
        [types.InlineKeyboardButton(text="✏️ Изменить Squad UUID", callback_data="a_edit_squad")],
        [types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")]
    ])
    
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

# Edit Handlers

@router.callback_query(F.data == "a_edit_days")
async def ask_days(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.edit_trial_days)
    await callback.message.edit_text("Введите новую длительность (в днях):", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_trial")]]))

@router.message(AdminStates.edit_trial_days)
async def set_days(message: types.Message, state: FSMContext):
    try:
        val = int(message.text)
        await SettingsService.set_setting("trial_days", str(val))
        await message.answer(f"✅ Установлено: {val} дней")
        await cmd_admin(message, state) 
    except ValueError:
        await message.answer("❌ Нужно ввести число.")

@router.callback_query(F.data == "a_edit_traffic")
async def ask_traffic(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.edit_trial_traffic)
    await callback.message.edit_text("Введите лимит трафика (в GB):", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_trial")]]))

@router.message(AdminStates.edit_trial_traffic)
async def set_traffic(message: types.Message, state: FSMContext):
    try:
        val = float(message.text)
        await SettingsService.set_setting("trial_traffic_gb", str(val))
        await message.answer(f"✅ Установлено: {val} GB")
        await cmd_admin(message, state)
    except ValueError:
        await message.answer("❌ Нужно ввести число (можно дробное, через точку).")

@router.callback_query(F.data == "a_edit_squad")
async def ask_squad(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.edit_trial_plan) # Reuse state or rename? Reuse is fine but confusing. Let's keep state name.
    await callback.message.edit_text("Введите новый Squad UUID:", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_trial")]]))

@router.message(AdminStates.edit_trial_plan)
async def set_squad(message: types.Message, state: FSMContext):
    await SettingsService.set_setting("trial_squad_uuid", message.text.strip())
    await message.answer(f"✅ Установлено Squad UUID: {message.text}")
    await cmd_admin(message, state)

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
    await cmd_admin(message, state)

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
        await callback.answer("Invalid ID")
        return

    tariff = await session.get(models.SpecialTariff, tariff_id)
    
    if not tariff:
        await callback.answer(l10n.format_value("admin-cp-not-found"))
        await cp_list(callback, state, session, l10n)
        return

    dur_display = "∞" if tariff.duration_months == 0 else f"{tariff.duration_months} mo"

    text = (
        f"{l10n.format_value('admin-cp-view-title', {'name': tariff.name})}\n\n"
        f"{l10n.format_value('admin-cp-view-squad', {'squad': tariff.squad_uuid})}\n"
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
    await callback.answer("Deleted")
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
    
    await callback.message.edit_text("⏳ ...")
    
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
        link_url = f"{config.remnawave_url}/sub/{uuid}"
        expire_str = "∞" if tariff.duration_months == 0 else expire_dt.strftime('%d.%m.%Y')
        
        msg = l10n.format_value("admin-cp-grant-success", {
            "username": username,
            "link": link_url,
            "traffic": tariff.traffic_gb,
            "expire": expire_str
        })
        
        await callback.message.edit_text(msg, parse_mode="Markdown")
        # Add button "To Menu"
        kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text=l10n.format_value("admin-cp-btn-to-menu"), callback_data="admin_cp_list")]])
        await callback.message.edit_reply_markup(reply_markup=kb)
        
    except Exception as e:
        logger.error("grant_error", error=str(e))
        await callback.message.edit_text(f"❌ Error: {str(e)}", reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text=l10n.format_value("admin-cp-btn-to-menu"), callback_data="admin_cp_list")]]))
