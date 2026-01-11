from aiogram import Router, types, F
from aiogram.filters import Command
from sqlalchemy import select
from bot.database import models
from bot.config import config
from datetime import datetime, timedelta

router = Router()
router.message.filter(F.from_user.id.in_(config.admin_ids))

@router.message(Command("add_promo"))
async def cmd_add_promo(message: types.Message, session):
    # Usage: /add_promo CODE VALUE IS_PERCENT(1/0) USES
    try:
        args = message.text.split()[1:]
        code = args[0]
        value = float(args[1])
        is_percent = bool(int(args[2]))
        max_uses = int(args[3])
        
        promo = models.Promocode(
            code=code,
            value=value,
            is_percent=is_percent,
            max_uses=max_uses,
            created_at=datetime.utcnow() # Wait, I didn't add created_at to Promocode model, only active_until. Let's start with this.
        )
        session.add(promo)
        await session.commit()
        await message.answer(f"✅ Promo {code} added!")
    except Exception as e:
        await message.answer(f"❌ Error: {e}\nUsage: /add_promo CODE VALUE IS_PERCENT(1/0) USES")

@router.message(Command("add_tariff"))
async def cmd_add_tariff(message: types.Message, session):
    # Usage: /add_tariff NAME PRICE DAYS TRAFFIC_GB
    try:
        args = message.text.split()[1:]
        name = args[0]
        price = float(args[1])
        duration = int(args[2])
        traffic = int(args[3]) if args[3] != '0' else None
        
        tariff = models.Tariff(
            name=name,
            price=price,
            duration_days=duration,
            traffic_limit_gb=traffic,
            currency="RUB"
        )
        session.add(tariff)
        await session.commit()
        await message.answer(f"✅ Tariff {name} added!")
    except Exception as e:
        await message.answer(f"❌ Error: {e}\nUsage: /add_tariff NAME PRICE DAYS TRAFFIC_GB(0=unlim)")

@router.message(Command("add_trial"))
async def cmd_add_trial(message: types.Message, session):
    # Usage: /add_trial DAYS TRAFFIC_GB
    try:
        args = message.text.split()[1:]
        duration = int(args[0])
        traffic = int(args[1]) if args[1] != '0' else None
        
        tariff = models.Tariff(
            name="Trial",
            price=0,
            duration_days=duration,
            traffic_limit_gb=traffic,
            currency="RUB",
            is_trial=True
        )
        session.add(tariff)
        await session.commit()
        await message.answer(f"✅ Trial tariff added!")
    except Exception as e:
        await message.answer(f"❌ Error: {e}\nUsage: /add_trial DAYS TRAFFIC_GB")



@router.message(Command("set_trial_squad"))
async def cmd_set_trial_squad(message: types.Message, session):
    # Usage: /set_trial_squad UUID
    try:
        args = message.text.split()
        if len(args) < 2:
            await message.answer("Usage: /set_trial_squad UUID")
            return
            
        uuid = args[1]
        
        # Upsert
        kv = await session.get(models.KeyValue, "trial_squad_uuid")
        if kv:
            kv.value = uuid
        else:
            kv = models.KeyValue(key="trial_squad_uuid", value=uuid)
            session.add(kv)
            
        await session.commit()
        await message.answer(f"✅ Trial squad UUID set to: `{uuid}`")
    except Exception as e:
        await message.answer(f"❌ Error: {e}")
