from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from fluent.runtime import FluentLocalization
from bot.config import config
from bot.services.settings import SettingsService

router = Router()

class AdminStates(StatesGroup):
    menu = State()
    edit_trial_days = State()
    edit_trial_traffic = State()
    edit_trial_plan = State()

async def get_main_kb():
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🎁 Настройки Триала", callback_data="admin_trial")],
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
