import asyncio
from bot.services.remnawave import RemnawaveAPI

async def main():
    api = RemnawaveAPI()
    users = await api.get_users(limit=1000)
    lst = users.get('users', []) if isinstance(users, dict) else users
    for u in lst:
        if u.get('username') in ['testGoose', 'masse13']:
            print(f"{u.get('username')}: telegramId={u.get('telegramId')}")
if __name__ == "__main__":
    asyncio.run(main())
