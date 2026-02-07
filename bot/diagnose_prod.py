import asyncio
import sys
import os

# Ensure we can import bot modules
sys.path.insert(0, "/app")
sys.path.append("/opt/stacks/remnabot")

from bot.services.remnawave import RemnawaveAPI
import inspect

from bot.handlers.user import check_existing_accounts, generate_profile_content
from bot.database.core import get_session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from bot.config import config

class MockL10n:
    def format_value(self, key, args=None):
        return f"[{key}]"

async def main():
    api = RemnawaveAPI()
    tg_id = 85751735 # masse13
    
    print("Checking connection to API...")
    print("Skipping preliminary check, proceeding to account check...")

    std, man = await check_existing_accounts(tg_id)
    
    print(f"Standard Account: {std['username'] if std else 'None'}")
    print(f"Manual Accounts: {[m['username'] for m in man]}")
    
    # Init DB
    print("Initializing DB...")
    # config.database_url might need fix if inside docker it is different? 
    # Usually it is postgresql+asyncpg://user:pass@db:5432/db
    # Inside docker 'db' hostname resolves.
    
    from bot.database.core import async_session
    
    async with async_session() as session:
        print("Running generate_profile_content...")
        text, kb = await generate_profile_content(tg_id, session, MockL10n())
        print("--- PROFILE TEXT ---")
        print(text)
        print("--------------------")


if __name__ == "__main__":
    asyncio.run(main())
