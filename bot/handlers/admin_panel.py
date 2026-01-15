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

    # Standard Tariffs
    t_name = State()
    t_price_rub = State()
    t_price_stars = State()
    t_price_usd = State()
    t_days = State()
    t_traffic = State()
    t_grant_id = State()

async def get_main_kb(l10n: FluentLocalization):
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=l10n.format_value("admin-btn-tariffs"), callback_data="admin_tariffs_list")],
        [types.InlineKeyboardButton(text=l10n.format_value("admin-btn-trial"), callback_data="admin_trial")],
        [types.InlineKeyboardButton(text=l10n.format_value("admin-btn-cp"), callback_data="admin_cp_list")],
        [types.InlineKeyboardButton(text=l10n.format_value("admin-btn-exit"), callback_data="admin_exit")]
    ])

# ... cmd_admin ...

@router.message(Command("admin"))
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
        [types.KeyboardButton(text=btn_shop), types.KeyboardButton(text=btn_profile)],
        [types.KeyboardButton(text=btn_trial), types.KeyboardButton(text=btn_support)]
    ]
    keyboard = types.ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
    
    await callback.message.answer(l10n.format_value("admin-exit-msg"), reply_markup=keyboard)

@router.callback_query(F.data == "admin_menu")
async def back_to_menu(callback: types.CallbackQuery, state: FSMContext, l10n: FluentLocalization):
    await state.clear()
    await callback.message.edit_text(l10n.format_value("admin-title"), reply_markup=await get_main_kb(l10n), parse_mode="Markdown")

# --- Trial Settings ---

@router.callback_query(F.data == "admin_trial")
async def trial_settings_menu(callback: types.CallbackQuery, state: FSMContext, l10n: FluentLocalization):
    settings = await SettingsService.get_trial_settings()
    
    text = f"{l10n.format_value('admin-trial-title')}\n\n" + \
           l10n.format_value("admin-trial-info", {
               "days": settings['days'],
               "traffic": settings['traffic'],
               "squad": settings['squad_uuid']
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
            # Note: We don't have username/fullname if user never started bot.
            # We can try to get it from Chat member info if bot is admin in a chat with user, but unlikely.
            # Just proceed with minimal info.

        tariff = await session.get(models.Tariff, tid)
        if not tariff:
            await message.answer("Tariff not found")
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
        
        order.status = models.OrderStatus.PAID
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
                     link = rw_user.get('subscriptionUrl') or rw_user.get('subUrl') or "Link not found in API"
                 except Exception as e:
                     link = f"Error fetching link: {e}"
             
             msg_text = l10n.format_value("admin-t-grant-success-full", {
                 "tariff": tariff.name,
                 "user_id": target_user_id,
                 "username": u.username or "Unknown",
                 "days": tariff.duration_days,
                 "traffic": tariff.traffic_limit_gb or "∞",
                 "link": link
             })
             
             await message.answer(msg_text, parse_mode="Markdown")
             
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
        data = await state.get_data()
        
        t = models.Tariff(
            name=data['name'],
            price_rub=data['rub'],
            price_stars=data['stars'],
            price_usd=data['usd'],
            duration_days=data['days'],
            traffic_limit_gb=limit if limit > 0 else None,
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
        
    text = (
        f"{l10n.format_value('admin-t-view-title', {'name': t.name})}\n"
        f"{l10n.format_value('admin-t-view-prices', {'rub': t.price_rub, 'stars': t.price_stars, 'usd': t.price_usd})}\n"
        f"{l10n.format_value('admin-t-view-duration', {'days': t.duration_days})}\n"
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
            await message.answer("Tariff not found")
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
                     link = rw_user.get('subscriptionUrl') or rw_user.get('subUrl') or "Link not found in API"
                 except Exception as e:
                     link = f"Error fetching link: {e}"
             
             msg_text = l10n.format_value("admin-t-grant-success-full", {
                 "tariff": tariff.name,
                 "user_id": target_user_id,
                 "username": u.username or "Unknown",
                 "days": tariff.duration_days,
                 "traffic": tariff.traffic_limit_gb or "∞",
                 "link": link
             })
             
             await message.answer(msg_text, parse_mode="Markdown")
             
             # Notify user
             try:
                 await message.bot.send_message(target_user_id, f"🎁 You have been granted a subscription: {tariff.name}!")
             except:
                 pass
        else:
             await message.answer(l10n.format_value("admin-t-grant-error", {"error": "Fulfillment failed"}))
             
        await state.clear()
        
    except ValueError:
        await message.answer(l10n.format_value("admin-t-val-int"))
    except Exception as e:
        logger.error("grant_tariff_error", error=str(e))
        await message.answer(l10n.format_value("admin-t-grant-error", {"error": str(e)}))
    
    # Return to menu? No, just clear state. Or better: show tariff list again.
    # But t_grant_process is a message handler, so we send message.
    # Let's add a button to go back.
    kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text=l10n.format_value("admin-t-list-btn"), callback_data="admin_tariffs_list")]])
    await message.answer("---", reply_markup=kb)

@router.callback_query(F.data.startswith("t_del_"))
async def t_delete(callback: types.CallbackQuery, session, l10n: FluentLocalization):
    tid = int(callback.data.split("_")[2])
    stmt = delete(models.Tariff).where(models.Tariff.id == tid)
    await session.execute(stmt)
    await session.commit()
    await callback.answer(l10n.format_value("admin-deleted"))
    await callback.message.edit_text(l10n.format_value("admin-deleted"), reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text=l10n.format_value("admin-t-list-btn"), callback_data="admin_tariffs_list")]]))

