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
    print(f"DEBUG: Global API Key Len: {len(global_api.api_key)}")
    
    print("--- Testing Global API directly ---")
    try:
        users = await global_api.get_users(search="85751735")
        print(f"Global API list len: {len(users) if isinstance(users, list) else 'Not List'}")
    except Exception as e:
        print(f"Global API Error: {e}")

    print("--- Testing NEW API Instance ---")
    local_api = RemnawaveAPI()
    print(f"DEBUG: Local API Base URL: {local_api.base_url}")
    print(f"DEBUG: Local API Key Len: {len(local_api.api_key)}")
    try:
        users_local = await local_api.get_users(search="85751735")
        print(f"Local API list len: {len(users_local) if isinstance(users_local, list) else 'Not List'}")
    except Exception as e:
        print(f"Local API Error: {e}")



if __name__ == "__main__":
    asyncio.run(main())
