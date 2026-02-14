import asyncio
import sys
import os
import json
import random

# Ensure we can import bot modules
sys.path.append("/app")

from bot.services.remnawave import RemnawaveAPI

async def main():
    api = RemnawaveAPI()
    try:
        print("--- Creating Test User ---")
        # Create a random user to avoid conflicts
        tid = random.randint(100000, 999999)
        username = f"debug_{tid}"
        
        try:
            # We use create_custom_user or create_user
            user = await api.create_user(tid, username)
            print(f"User created: {json.dumps(user, indent=2)}")
            # Extract UUID correctly
            if 'response' in user:
                uuid = user['response']['uuid']
            else:
                uuid = user.get('uuid')
                
            if not uuid:
                print("Could not extract UUID from response.")
                return
                
        except Exception as e:
            print(f"Failed to create user: {e}")
            # Try to fetch existing users again
            users = await api.get_users()
            if users and 'users' in users and users['users']:
                target = users['users'][0]
                uuid = target['uuid']
                print(f"Using existing user: {uuid}")
            else:
                print("No user available to test.")
                return

        print(f"\n--- Testing Endpoints for UUID: {uuid} ---")
        
        endpoints = [
            f"hwid/devices",
            f"hwid/devices?userId={uuid}",
            f"hwid/devices/{uuid}",
            f"users/{uuid}/hwid/devices"
        ]

        for ep in endpoints:
            print(f"\nTesting GET /api/{ep} ...")
            try:
                res = await api._request("GET", ep)
                print(f"SUCCESS: {json.dumps(res, indent=2)}")
            except Exception as e:
                print(f"FAILED: {e}")

    except Exception as e:
        print(f"Fatal Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
