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

import aiohttp

    # override url
    url = "https://catapult.cyni.cc/api/users"
    print(f"DEBUG: Forcing URL: {url}")
    
    headers = {
        "Authorization": f"Bearer {config.remnawave_api_key.get_secret_value()}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    params = {"limit": "10"}
    
    print(f"--- RAW REQUEST to {url} ---")
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            print(f"Status: {response.status}")
            text = await response.text()
            print(f"Body len: {len(text)}")
            print(f"Body start: {text[:200]}")
            if response.ok:
                 try:
                     data = await response.json()
                     # Handle list or dict
                     users = []
                     if isinstance(data, list): users = data
                     elif isinstance(data, dict): users = data.get('users', []) or data.get('data', [])
                     
                     print(f"User count: {len(users)}")
                     if users:
                         print(f"First user: {users[0].get('username')}")
                 except:
                     pass



if __name__ == "__main__":
    asyncio.run(main())
