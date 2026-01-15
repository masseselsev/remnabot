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
        await message.answer(l10n.format_value("shop-no-tariffs"))
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
        [types.InlineKeyboardButton(text=l10n.format_value("shop-promo-skip"), callback_data="skip_promo")]
    ])
    await callback.message.answer(l10n.format_value("shop-promo-ask"), reply_markup=kb)
    await callback.answer()

@router.callback_query(ShopState.entering_promo, F.data == "skip_promo")
async def skip_promo(callback: types.CallbackQuery, state: FSMContext, l10n: FluentLocalization):
    await state.set_state(ShopState.selecting_payment)
    await show_payment_methods(callback.message, state, l10n)
    await callback.answer()

@router.message(ShopState.entering_promo)
async def process_promo(message: types.Message, state: FSMContext, session, l10n: FluentLocalization):
    code = message.text.strip()
    promo = await session.get(models.Promocode, code)
    
    if not promo:
        kb = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text=l10n.format_value("shop-promo-skip"), callback_data="skip_promo")]
        ])
        await message.answer(l10n.format_value("shop-promo-invalid"), reply_markup=kb)
        return
    
    # Check expiry
    if promo.active_until and promo.active_until < datetime.utcnow():
        await message.answer(l10n.format_value("shop-promo-expired"))
        return
    if promo.max_uses > 0 and promo.used_count >= promo.max_uses:
        await message.answer(l10n.format_value("shop-promo-limit"))
        return

    await state.update_data(promo_code=code)
    await message.answer(l10n.format_value("shop-promo-applied", {"code": code}))
    await state.set_state(ShopState.selecting_payment)
    await show_payment_methods(message, state, l10n)

async def show_payment_methods(message: types.Message, state: FSMContext, l10n: FluentLocalization):
    data = await state.get_data()
    p_rub = data.get('price_rub', 0)
    p_stars = data.get('price_stars', 0)
    
    # shop-pay-card = 💳 Card ({ $price } RUB)
    # shop-pay-stars = ⭐️ Telegram Stars ({ $price } Stars)
    
    btn_card = l10n.format_value("shop-pay-card", {"price": p_rub})
    btn_stars = l10n.format_value("shop-pay-stars", {"price": p_stars})
    
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=btn_card, callback_data="pay_yookassa")],
        [types.InlineKeyboardButton(text=btn_stars, callback_data="pay_stars")],
    ])
    await message.answer(l10n.format_value("shop-payment-method-desc"), reply_markup=kb)

@router.callback_query(ShopState.selecting_payment)
async def payment_selected(callback: types.CallbackQuery, state: FSMContext, session, l10n: FluentLocalization):
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
                price = max(0, price - promo.value)
                
    # Ensure integer for Stars
    if provider == models.PaymentProvider.STARS:
        price = int(price)
    
    # Create DB Order
    from bot.services.orders import create_order
    from bot.services.payment import get_payment_service
    
    order = await create_order(callback.from_user.id, data['tariff_id'], float(price), provider, session)
    
    try:
        service = get_payment_service(provider)
        
        # Metadata
        metadata = {"order_id": str(order.id)}
            
        pid, url_or_token = await service.create_payment(
            amount=price, 
            description=f"Order #{order.id} - VPN", 
            metadata=metadata
        )
        
        order.invoice_id = pid
        await session.commit()
        
        if provider == models.PaymentProvider.STARS:
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
             await callback.message.answer(l10n.format_value("shop-pay-stars-hint"))
             
        else:
            kb = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text=l10n.format_value("shop-pay-btn"), url=url_or_token)]])
            msg = l10n.format_value("shop-order-created", {"id": order.id, "price": price, "currency": currency})
            await callback.message.answer(msg, reply_markup=kb)
        
    except NotImplementedError:
        await callback.message.answer(l10n.format_value("shop-payment-not-configured"))
    except Exception as e:
        logger.error("payment_creation_failed", error=str(e))
        await callback.message.answer(l10n.format_value("shop-payment-error", {"error": str(e)}))
        
    await callback.answer()

@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@router.message(F.successful_payment)
async def process_successful_payment(message: types.Message, session, l10n: FluentLocalization):
    payment_info = message.successful_payment
    payload = payment_info.invoice_payload
    
    # Find order by invoice_id
    stmt = select(models.Order).where(models.Order.invoice_id == payload)
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()
    
    if order:
        from bot.services.orders import fulfill_order
        if await fulfill_order(order.id, session, payment_id=payment_info.telegram_payment_charge_id):
             await message.answer(l10n.format_value("shop-success", {"id": order.id}))
        else:
             await message.answer(l10n.format_value("shop-error-fulfillment"))
    else:
        await message.answer(l10n.format_value("shop-error-not-found"))

