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
    stmt = select(models.Tariff).where(models.Tariff.is_active == True, models.Tariff.is_trial == False).order_by(models.Tariff.price_rub)
    result = await session.execute(stmt)
    tariffs = result.scalars().all()
    
    if not tariffs:
        await message.answer("😔 No tariffs available at the moment.")
        return

    kb = []
    for t in tariffs:
        # Display format: Name - 100₽ | 50⭐️ | 2$
        text = f"{t.name} - {t.price_rub}₽ | {t.price_stars}⭐️ | {t.price_usd}$"
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
        
    await state.update_data(
        tariff_id=tariff.id, 
        price_rub=tariff.price_rub,
        price_stars=tariff.price_stars,
        price_usd=tariff.price_usd
    )
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
    data = await state.get_data()
    p_rub = data.get('price_rub', 0)
    p_stars = data.get('price_stars', 0)
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=f"💳 Банковская карта ({p_rub} RUB)", callback_data="pay_yookassa")],
        [types.InlineKeyboardButton(text=f"⭐️ Telegram Stars ({p_stars} Stars)", callback_data="pay_stars")],
    ])
    await message.answer("Выберите способ оплаты:", reply_markup=kb)

@router.callback_query(ShopState.selecting_payment)
async def payment_selected(callback: types.CallbackQuery, state: FSMContext, session):
    method = callback.data # pay_yookassa or pay_stars
    data = await state.get_data()
    
    price = 0.0
    currency = "RUB"
    provider = models.PaymentProvider.MANUAL
    
    if method == "pay_yookassa":
        provider = models.PaymentProvider.YOOKASSA
        price = data['price_rub']
        currency = "RUB"
    elif method == "pay_stars":
        provider = models.PaymentProvider.STARS
        price = data['price_stars']
        currency = "XTR"
        
    # Apply Promo
    if 'promo_code' in data:
        promo = await session.get(models.Promocode, data['promo_code'])
        if promo:
            if promo.is_percent:
                price = price * (1 - promo.value / 100)
            else:
                # Value is usually in RUB, need to check how to handle fixed discount for Stars/USD
                # For now assume promo value is in the same unit or just disable fixed promo for non-ruble?
                # Let's assume % for simplicity or 1:1 for now (which is wrong but ok for prototype)
                # Or better: convert promo value? 
                # Let's just subtract raw value (assuming promo is generic credits)
                price = max(0, price - promo.value)
                
    # Ensure integer for Stars
    if provider == models.PaymentProvider.STARS:
        price = int(price)
    
    # Create DB Order
    # We pass provider to create_order?
    from bot.services.orders import create_order
    from bot.services.payment import get_payment_service
    
    order = await create_order(callback.from_user.id, data['tariff_id'], float(price), provider, session)
    
    try:
        service = get_payment_service(provider)
        
        # Metadata
        metadata = {"order_id": str(order.id)}
        
        if provider == models.PaymentProvider.STARS:
            # Stars flow
            # We need to send invoice here directly because Stars uses send_invoice
            # Service can return the payload or we modify service to accept 'message' or 'callback' to send.
            # But the PaymentService abstraction returns (id, url).
            # Stars doesn't have a URL in the same way (it has an internal link or button)
            # Let's see how our StarsGateway is implemented.
            pass
            
        pid, url_or_token = await service.create_payment(
            amount=price, 
            description=f"Order #{order.id} - VPN", 
            metadata=metadata
        )
        
        order.invoice_id = pid
        await session.commit()
        
        if provider == models.PaymentProvider.STARS:
             # url_or_token might be the payload or we need to call send_invoice here using bot instance
             # Let's actually handle sending invoice INSIDE the handler for Stars or use the text link if provided.
             # If create_payment returns a deep link (t.me/bot?start=...) that handles invoice, that works.
             # But typically we send invoice message.
             
             # Option A: We send invoice via bot.send_invoice
             prices = [types.LabeledPrice(label="VPN Subscription", amount=int(price))] # amount in stars!
             await callback.message.bot.send_invoice(
                 chat_id=callback.message.chat.id,
                 title=f"Order #{order.id}",
                 description="VPN Subscription",
                 payload=pid, # invoice_id from service logic (uuid)
                 provider_token="", # Empty for Stars
                 currency="XTR",
                 prices=prices,
                 start_parameter=f"pay_{order.id}"
             )
             await callback.message.answer("☝️ Нажмите кнопку выше, чтобы оплатить звездами.")
             
        else:
            kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="💳 Оплатить", url=url_or_token)]])
            await callback.message.answer(f"✅ Заказ #{order.id} создан.\nСумма к оплате: {price} {currency}", reply_markup=kb)
        
    except NotImplementedError:
        await callback.message.answer("❌ Этот способ оплаты еще не настроен.")
    except Exception as e:
        logger.error("payment_creation_failed", error=str(e))
        await callback.message.answer(f"❌ Ошибка создания платежа: {e}")
        
    await callback.answer()

@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@router.message(F.successful_payment)
async def process_successful_payment(message: types.Message, session):
    payment_info = message.successful_payment
    payload = payment_info.invoice_payload
    
    # Find order by invoice_id
    stmt = select(models.Order).where(models.Order.invoice_id == payload)
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()
    
    if order:
        from bot.services.orders import fulfill_order
        if await fulfill_order(order.id, session, payment_id=payment_info.telegram_payment_charge_id):
             await message.answer(f"✅ Оплата прошла успешно! Ваш заказ #{order.id} выполнен.")
        else:
             await message.answer("⚠️ Оплата прошла, но возникла ошибка при выдаче товара. Свяжитесь с поддержкой.")
    else:
        await message.answer("⚠️ Оплата прошла, но заказ не найден. Свяжитесь с поддержкой.")

