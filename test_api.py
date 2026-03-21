import asyncio
from bot.services.remnawave import RemnawaveAPI

async def main():
    api = RemnawaveAPI()
    try:
        user_by_tid = await api.get_user_by_telegram_id(85751735)
        print("get_user_by_telegram_id:", type(user_by_tid), user_by_tid)
    except Exception as e:
        print("get_user_by_telegram_id error:", e)

    try:
        users = await api.get_users(search="85751735")
        print("get_users length:", type(users), len(users) if isinstance(users, list) else (len(users.get('users', [])) if isinstance(users, dict) else users))
        if isinstance(users, dict) and 'users' in users:
            for u in users['users']:
                print(u.get('username'))
        elif isinstance(users, list):
            for u in users:
                print(u.get('username'))
    except Exception as e:
        print("get_users error:", e)

if __name__ == "__main__":
    asyncio.run(main())
