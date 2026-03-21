import asyncio
from bot.services.remnawave import RemnawaveAPI

async def main():
    api = RemnawaveAPI()
    try:
        user_by_tid = await api.get_user_by_telegram_id(85751735)
        print("get_user_by_telegram_id type:", type(user_by_tid))
        print("get_user_by_telegram_id repr:", repr(user_by_tid)[:500])
    except Exception as e:
        print("get_user_by_telegram_id error:", e)

    try:
        users = await api.get_users(search="85751735")
        if isinstance(users, dict) and 'users' in users:
            print("get_users list:", [u.get('username') for u in users['users']])
        elif isinstance(users, list):
            print("get_users list directly:", [u.get('username') for u in users])
        else:
            print("get_users structure:", repr(users)[:500])
    except Exception as e:
        print("get_users error:", e)

if __name__ == "__main__":
    asyncio.run(main())
