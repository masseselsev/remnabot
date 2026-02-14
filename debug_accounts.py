
import asyncio
import os
from bot.services.remnawave import api

async def main():
    target_id = "85751735"
    print(f"Searching for users with query: {target_id}")
    
    try:
        # Fetching large limit
        results = await api.get_users(limit=1000, offset=0)
        
        if isinstance(results, dict) and 'response' in results:
            r = results['response']
            if isinstance(r, dict) and 'users' in r:
                users = r['users']
            elif isinstance(r, list):
                users = r
            else:
                 users = [] # Fallback
        elif isinstance(results, dict) and 'users' in results:
             users = results['users']
        else:
            users = results if isinstance(results, list) else []
            
        print(f"DEBUG RAW USERS: {users}")
            
        print(f"Found {len(users)} users (total fetch).")
        
        # Filter manually
        found = [u for u in users if str(u.get('telegramId')) == "85751735"]
        for u in found:
            print(f"- {u.get('username')} (UUID: {u.get('uuid')}, TgID: {u.get('telegramId')})")
            
    except Exception as e:
        print(f"Error searching: {e}")

if __name__ == "__main__":
    asyncio.run(main())
