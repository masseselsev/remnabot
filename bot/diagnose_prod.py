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
    
    queries = [
        {"search": "85751735"},
        {"search": "tg_85751735"},
        {"search": "Masse13"},
        {"limit": 10},
        {} # Default
    ]
    
    for q in queries:
        print(f"--- Query: {q} ---")
        try:
            users = await global_api.get_users(**q)
            count = len(users) if isinstance(users, list) else "Not List"
            print(f"Result count: {count}")
            if isinstance(users, list) and count > 0:
                print(f"First user: {users[0].get('username')}")
                # Check for masse13
                found = any(str(u.get('telegramId')) == "85751735" for u in users)
                print(f"Found 85751735: {found}")
        except Exception as e:
            print(f"Error: {e}")



if __name__ == "__main__":
    asyncio.run(main())
