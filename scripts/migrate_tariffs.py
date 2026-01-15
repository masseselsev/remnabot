import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from bot.database.core import engine

async def migrate():
    print("Starting migration...")
    async with engine.begin() as conn:
        # Check if columns exist to avoid error, or just catch it. 
        # Postgres allows ADD COLUMN IF NOT EXISTS in newer versions, else try/except.
        
        try:
            await conn.execute(text("ALTER TABLE tariffs ADD COLUMN IF NOT EXISTS price_rub FLOAT DEFAULT 0.0;"))
            print("Added price_rub")
        except Exception as e:
            print(f"Skipped price_rub: {e}")

        try:
            await conn.execute(text("ALTER TABLE tariffs ADD COLUMN IF NOT EXISTS price_stars INTEGER DEFAULT 0;"))
            print("Added price_stars")
        except Exception as e:
            print(f"Skipped price_stars: {e}")

        try:
             await conn.execute(text("ALTER TABLE tariffs ADD COLUMN IF NOT EXISTS price_usd FLOAT DEFAULT 0.0;"))
             print("Added price_usd")
        except Exception as e:
             print(f"Skipped price_usd: {e}")
             
    print("Migration finished.")

if __name__ == "__main__":
    asyncio.run(migrate())
