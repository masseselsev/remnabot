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

async def main():
    print(f"DEBUG: Config Remnawave URL: {config.remnawave_url}")
    url = f"{config.remnawave_url}/api/users"
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
            print(f"Body: {text[:500]}...") # Print first 500 chars



if __name__ == "__main__":
    asyncio.run(main())
