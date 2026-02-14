import asyncio
import sys
import os
import json

# Ensure we can import bot modules
sys.path.append("/app")

from bot.services.remnawave import RemnawaveAPI

async def main():
    api = RemnawaveAPI()
    # UUID from logs for user 85751735
    target_uuid = "48802c7f-9210-492d-9999-89e5bc57e974"
    
    print(f"--- Debugging User: {target_uuid} ---")
    
    # 1. Verify User exists
    try:
        user_info = await api.get_user(target_uuid)
        print(f"User Info Response: {json.dumps(user_info, indent=2)}")
    except Exception as e:
        print(f"Failed to get user: {e}")

    # 2. Check Devices with userId filter
    try:
        url = f"hwid/devices?userId={target_uuid}"
        print(f"\nQuerying: GET /api/{url}")
        res = await api._request("GET", url)
        print(f"Response: {json.dumps(res, indent=2)}")
        
        if 'response' in res and 'devices' in res['response']:
            devs = res['response']['devices']
            print(f"Devices found count: {len(devs)}")
        else:
             print("Structure unexpected!")

    except Exception as e:
        print(f"Error querying with userId: {e}")

    # 3. Check ALL devices and filter manually to see if it exists
    print("\n--- Checking ALL devices list for this user ---")
    try:
        res_all = await api._request("GET", "hwid/devices")
        # Don't print everything, it's huge.
        if 'response' in res_all and 'devices' in res_all['response']:
            all_devs = res_all['response']['devices']
            print(f"Total devices in system: {len(all_devs)}")
            
            # Filter
            found = [d for d in all_devs if d.get('userUuid') == target_uuid]
            print(f"Found {len(found)} devices for this UUID manually:")
            print(json.dumps(found, indent=2))
        else:
            print("Failed to get all devices list structure")
            
    except Exception as e:
        print(f"Error checking all devices: {e}")

if __name__ == "__main__":
    asyncio.run(main())
