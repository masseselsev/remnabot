from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from bot.database import models
from bot.states import ShopState
from fluent.runtime import FluentLocalization
from datetime import datetime

router = Router()

@router.message(F.text == "🛒 Buy VPN")
@router.message(F.text == "🛒 Купить VPN")
async def show_tariffs(message: types.Message, session, l10n: FluentLocalization):
    stmt = select(models.Tariff).where(models.Tariff.is_active == True, models.Tariff.is_trial == False).order_by(models.Tariff.price)
    result = await session.execute(stmt)
    tariffs = result.scalars().all()
    
    if not tariffs:
        await message.answer("😔 No tariffs available at the moment.")
        return

    kb = []
    for t in tariffs:
        text = f"{t.name} - {t.price} {t.currency}"
        kb.append([types.InlineKeyboardButton(text=text, callback_data=f"buy_tariff_{t.id}")])
        
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=kb)
    await message.answer(l10n.format_value("shop-select-tariff"), reply_markup=keyboard)

@router.callback_query(F.data.startswith("buy_tariff_"))
async def select_tariff(callback: types.CallbackQuery, state: FSMContext, session, l10n: FluentLocalization):
    tariff_id = int(callback.data.split("_")[2])
    tariff = await session.get(models.Tariff, tariff_id)
    
    if not tariff:
        await callback.answer("Tariff not found", show_alert=True)
        return
        
    await state.update_data(tariff_id=tariff.id, price=tariff.price, currency=tariff.currency)
    await state.set_state(ShopState.entering_promo)
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Skip", callback_data="skip_promo")]
    ])
    await callback.message.answer("Have a promo code? Enter it below or click Skip.", reply_markup=kb)
    await callback.answer()

@router.callback_query(ShopState.entering_promo, F.data == "skip_promo")
async def skip_promo(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(ShopState.selecting_payment)
    await show_payment_methods(callback.message, state)
    await callback.answer()

@router.message(ShopState.entering_promo)
async def process_promo(message: types.Message, state: FSMContext, session):
    code = message.text.strip()
    promo = await session.get(models.Promocode, code)
    
    if not promo:
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Skip", callback_data="skip_promo")]
        ])
        await message.answer("❌ Invalid promo code. Try again or Skip.", reply_markup=kb)
        return
    
    # Check expiry
    if promo.active_until and promo.active_until < datetime.utcnow():
        await message.answer("❌ Promo code expired.")
        return
    if promo.max_uses > 0 and promo.used_count >= promo.max_uses:
        await message.answer("❌ Promo code limit reached.")
        return

    await state.update_data(promo_code=code)
    await message.answer(f"✅ Promo code {code} applied!")
    await state.set_state(ShopState.selecting_payment)
    await show_payment_methods(message, state)

async def show_payment_methods(message: types.Message, state: FSMContext):
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="💳 Банковская карта (РФ)", callback_data="pay_yookassa")],
        # [types.InlineKeyboardButton(text="⭐️ Telegram Stars", callback_data="pay_stars")],
    ])
    await message.answer("Выберите способ оплаты:", reply_markup=kb)

@router.callback_query(ShopState.selecting_payment)
async def payment_selected(callback: types.CallbackQuery, state: FSMContext, session):
    method = callback.data # pay_yookassa
    data = await state.get_data()
    
    # Calculate final price
    price = data['price']
    
    if 'promo_code' in data:
        promo = await session.get(models.Promocode, data['promo_code'])
        if promo:
            if promo.is_percent:
                price = price * (1 - promo.value / 100)
            else:
                price = max(0, price - promo.value)
    
    # Payment Provider Logic
    from bot.services.orders import create_order
    from bot.services.payment import get_payment_service
    
    provider = models.PaymentProvider.MANUAL
    if method == "pay_yookassa":
        provider = models.PaymentProvider.YOOKASSA
    elif method == "pay_stars":
        provider = models.PaymentProvider.STARS
        
    # Create DB Order
    order = await create_order(callback.from_user.id, data['tariff_id'], price, provider, session)
    
    try:
        service = get_payment_service(provider)
        
        # Metadata must be strings for some gateways
        pid, url = await service.create_payment(
            amount=price, 
            description=f"Order #{order.id}", 
            metadata={"order_id": str(order.id)}
        )
        
        # Save invoice_id
        order.invoice_id = pid
        await session.commit()
        
        kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="💳 Оплатить", url=url)]])
        await callback.message.answer(f"✅ Заказ #{order.id} создан.\nСумма к оплате: {price} RUB", reply_markup=kb)
        
    except NotImplementedError:
        await callback.message.answer("❌ Этот способ оплаты еще не настроен.")
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка создания платежа: {e}")
        
    await callback.answer()

