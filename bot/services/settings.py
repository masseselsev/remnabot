from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from bot.database import models
from bot.database.core import async_session

class SettingsService:
    @staticmethod
    async def get_setting(key: str, default: str = None) -> str:
        async with async_session() as session:
            result = await session.get(models.KeyValue, key)
            return result.value if result else default

    @staticmethod
    async def set_setting(key: str, value: str):
        async with async_session() as session:
            # Upsert
            stmt = insert(models.KeyValue).values(key=key, value=str(value)).on_conflict_do_update(
                index_elements=['key'],
                set_=dict(value=str(value))
            )
            await session.execute(stmt)
            await session.commit()
            
    # Typed helpers
    @staticmethod
    async def get_trial_settings():
        async with async_session() as session:
            result = await session.execute(select(models.KeyValue).where(models.KeyValue.key.in_([
                "trial_days", "trial_traffic_gb", "trial_squad_uuid"
            ])))
            items = {row.KeyValue.key: row.KeyValue.value for row in result}
            
            return {
                "days": int(items.get("trial_days", 3)),
                "traffic": float(items.get("trial_traffic_gb", 100.0)),
                "squad_uuid": items.get("trial_squad_uuid", "")
            }
