import asyncio
import sys
import os

# Ensure we can import bot modules
sys.path.insert(0, "/app")
sys.path.append("/opt/stacks/remnabot")

from bot.services.remnawave import RemnawaveAPI
import inspect

from bot.handlers.user import check_existing_accounts, generate_profile_content
from bot.services.remnawave import api as global_api, RemnawaveAPI
from bot.database.core import get_session, async_session
from bot.config import config

class MockL10n:
    def format_value(self, key, args=None):
        return f"[{key}]"

async def main():
    print(f"DEBUG: Config Remnawave URL: {config.remnawave_url}")
    print(f"DEBUG: Global API Base URL: {global_api.base_url}")
    
    print("--- Testing Global API directly ---")
    users = await global_api.get_users(search="85751735")
    print(f"Global API returned type: {type(users)}")
    if isinstance(users, dict):
         print(f"Global API keys: {users.keys()}")
         if 'response' in users:
             print(f"Global API response len: {len(users['response'])}")
    elif isinstance(users, list):
         print(f"Global API list len: {len(users)}")
    else:
         print(f"Global API raw: {users}")

    print("--- Testing check_existing_accounts ---")
    std, man = await check_existing_accounts(85751735)
    print(f"STD: {std is not None}, MANUAL: {len(man)}")



if __name__ == "__main__":
    asyncio.run(main())
