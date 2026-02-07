import asyncio
import sys
import os

# Ensure we can import bot modules
sys.path.insert(0, "/app")
sys.path.append("/opt/stacks/remnabot")

from bot.services.remnawave import RemnawaveAPI
import inspect

from bot.handlers.user import check_existing_accounts

async def main():
    api = RemnawaveAPI()
    tg_id = 85751735 # masse13
    
    print("Checking connection to API...")
    # Skip limit check as it might fail on server version
    print("Skipping preliminary check, proceeding to account check...")

    std, man = await check_existing_accounts(tg_id)
    
    print(f"Standard Account: {std['username'] if std else 'None'}")
    if std:
         print(f"  Expiry: {std.get('expireAt')}")
         print(f"  Traffic: {std.get('trafficLimitBytes')}")
         
    print(f"Manual Accounts: {[m['username'] for m in man]}")
    for m in man:
        print(f"  Account: {m['username']}")
        print(f"  Expiry: {m.get('expireAt')}")
        print(f"  Traffic: {m.get('trafficLimitBytes')}")
        
    if std or man:
        print("SUCCESS: Found accounts using search!")
    else:
        print("FAILURE: Did not find accounts.")

if __name__ == "__main__":
    asyncio.run(main())
