
import asyncio
import os
from bot.services.remnawave import api

async def main():
    user_uuid = "a402ad1d-e982-48b7-b4a4-784c14d07892" # masse13
    print(f"Checking devices for UUID: {user_uuid}")
    
    print("\n--- Test 1: Size=1000 ---")
    try:
        # size works!
        print("Fetching size=1000...")
        res1 = await api._request("GET", "hwid/devices?size=1000")
        if res1 and 'response' in res1:
             devs1 = res1['response'].get('devices', [])
             print(f"Size 1000 fetched: {len(devs1)}")
             # Check if masse13 devices are here
             found = [d for d in devs1 if d.get('userUuid') == user_uuid]
             print(f"Found for masse13: {len(found)}")
             for d in found:
                 print(f" - {d.get('model')} ({d.get('hwid')})")
    except Exception as e:
        print(f"Error Test 1: {e}")

if __name__ == "__main__":
    asyncio.run(main())
