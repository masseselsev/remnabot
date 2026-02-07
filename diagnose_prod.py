import asyncio
import sys
import os

# Ensure we can import bot modules
sys.path.append("/opt/stacks/remnabot")

from bot.services.remnawave import RemnawaveAPI

# Copied from bot/handlers/user.py (with minimal modifications for standalone run)
async def check_existing_accounts(api, user_id: int):
    print(f"--- Running check_existing_accounts for {user_id} ---")
    try:
        # Use search to find user by ID (more reliable than fetching all)
        # This is the fix we implemented
        users = await api.get_users(search=str(user_id))
        
        candidates = []
        if isinstance(users, list): candidates = users
        elif isinstance(users, dict):
             if 'response' in users:
                 r = users['response']
                 if isinstance(r, list): candidates = r
                 elif isinstance(r, dict):
                     candidates = r.get('users', []) or r.get('data', [])

        standard = None
        manual = []
        
        target_username = f"tg_{user_id}"
        
        print(f"Candidates found: {len(candidates)}")

        for u in candidates:
            # Check explicit telegramId match (robust) or username match
            tid = u.get('telegramId')
            uname = u.get('username')
            uuid = u.get('uuid')
            
            print(f"Candidate: {uname} (ID: {tid}, UUID: {uuid})")
            
            # API search is fuzzy, so verify ID or exact username
            is_match = False
            if str(tid) == str(user_id): is_match = True
            if uname == target_username: is_match = True
            
            if is_match:
                if uname == target_username:
                    standard = u
                else:
                    manual.append(u)
            
        return standard, manual
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return None, []

async def main():
    api = RemnawaveAPI()
    tg_id = 85751735 # masse13
    
    print("Checking connection to API...")
    try:
        me = await api.get_users(limit=1)
        print("API connection OK.")
    except Exception as e:
        print(f"API connection FAILED: {e}")
        return

    std, man = await check_existing_accounts(api, tg_id)
    
    print(f"Standard Account: {std['username'] if std else 'None'}")
    print(f"Manual Accounts: {[m['username'] for m in man]}")
    
    if std or man:
        print("SUCCESS: Found accounts using search!")
    else:
        print("FAILURE: Did not find accounts.")

if __name__ == "__main__":
    asyncio.run(main())
