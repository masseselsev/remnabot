import asyncio
import sys
import json

# Ensure we can import bot modules
sys.path.append("/app")

from bot.services.remnawave import RemnawaveAPI

async def main():
    api = RemnawaveAPI()
    tg_id = 85751735 # My ID from logs
    
    print(f"--- Searching for user by TG ID: {tg_id} ---")
    try:
        # Search using the string representation of ID
        res = await api.get_users(search=str(tg_id))
        print(f"Result raw type: {type(res)}")
        
        candidates = []
        if isinstance(res, list): candidates = res
        elif isinstance(res, dict):
             if 'response' in res:
                 r = res['response']
                 if isinstance(r, list): candidates = r
                 elif isinstance(r, dict):
                     if 'users' in r: candidates = r['users']
                     elif 'data' in r: candidates = r['data']

        print(f"Candidates found: {len(candidates)}")
        print(json.dumps(candidates, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
