import asyncio
import json
from bot.services.remnawave import api
from bot.config import config

async def test():
    # masse13 uuid was seen in previous logs or I can search for it.
    # From the screenshot, masse13 has subscriptionUrl .../6-t6o51TegN08Zvh
    # In Remnawave, the part after /sub/ is the uuid.
    uuid = "6-t6o51TegN08Zvh" # Wait, this might be a short uuid or a custom link.
    
    # Let's search for user masse13
    users = await api.get_users(search="masse13")
    print(f"Users found: {len(users)}")
    if users:
        user = users[0]
        print(json.dumps(user, indent=2))
        
        # Also check the individual get_user call
        details = await api.get_user(user['uuid'])
        print("\nFull Details:")
        print(json.dumps(details, indent=2))

if __name__ == "__main__":
    asyncio.run(test())
