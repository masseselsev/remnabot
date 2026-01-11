import aiohttp
from bot.config import config
import structlog

logger = structlog.get_logger()

class RemnawaveAPI:
    def __init__(self):
        self.base_url = config.remnawave_url.rstrip("/")
        self.api_key = config.remnawave_api_key.get_secret_value()
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def _request(self, method: str, endpoint: str, data: dict = None):
        url = f"{self.base_url}/api/{endpoint.lstrip('/')}"
        async with aiohttp.ClientSession() as session:
            try:
                async with session.request(method, url, headers=self.headers, json=data) as response:
                    if not response.ok:
                        text = await response.text()
                        if response.status == 404:
                            logger.debug("remnawave_api_404", method=method, url=url, body=text)
                        else:
                            logger.error("remnawave_api_fail", 
                                         method=method, 
                                         url=url,
                                         status=response.status, 
                                         body=text)
                    response.raise_for_status()
                    return await response.json()
            except Exception as e:
                if "example.com" in self.base_url:
                     logger.warning("Using MOCK API response")
                     return {"uuid": "mock-uuid-1234", "status": "active"}
                
                # If it's a 404 error from raise_for_status, we might want to log it as debug or info
                is_404 = False
                if hasattr(e, 'status') and e.status == 404: is_404 = True
                
                if is_404:
                    logger.debug("remnawave_api_exception_404", method=method, endpoint=endpoint, error=str(e))
                else:
                    logger.error("remnawave_api_exception", method=method, endpoint=endpoint, error=str(e))
                raise e

    async def create_user(self, telegram_id: int, username: str):
        # Guessing endpoint structure based on common panels
        # Usually POST /api/users
        from datetime import datetime
        data = {
            "username": f"tg_{telegram_id}",
            "telegramId": telegram_id,
            "note": f"User {username} ({telegram_id})",
            "status": "ACTIVE",
            "proxies": {},
            "inbounds": {},
            "expireAt": datetime.utcnow().isoformat() + "Z"
        }
        return await self._request("POST", "users", data)

    async def get_user(self, uuid: str):
        return await self._request("GET", f"users/{uuid}")

    async def update_user(self, uuid: str, data: dict):
        payload = data.copy()
        payload['uuid'] = uuid
        # Per docs: PATCH /api/users
        return await self._request("PATCH", "users", payload)

    async def add_duration(self, uuid: str, days: int):
        from datetime import datetime, timedelta
        import dateutil.parser

        user = await self.get_user(uuid)
        current_expire = user.get('expireAt')
        
        if current_expire:
            try:
                # Handle Z or timezone
                expire_dt = dateutil.parser.isoparse(current_expire)
                # Ensure we are working with UTC (naive or aware)
                if expire_dt.tzinfo is None:
                    expire_dt = expire_dt.replace(tzinfo=None) # naive to naive
                else:
                    expire_dt = expire_dt.astimezone(datetime.utcnow().tzinfo)

                now = datetime.now(expire_dt.tzinfo) if expire_dt.tzinfo else datetime.utcnow()
                
                if expire_dt < now:
                    expire_dt = now
            except:
                expire_dt = datetime.utcnow()
        else:
            expire_dt = datetime.utcnow()
            
        new_expire = expire_dt + timedelta(days=days)
        # Remnawave expects ISO string
        return await self.update_user(uuid, {"expireAt": new_expire.isoformat().replace("+00:00", "Z")})

    async def get_users(self, search: str = None):
        params = {}
        if search:
            params['search'] = search
        
        url = f"{self.base_url}/api/users"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.headers, params=params) as response:
                if not response.ok:
                    text = await response.text()
                    logger.error("remnawave_get_users_fail", status=response.status, body=text)
                    return []
                return await response.json()

    async def get_squads(self):
        return await self._request("GET", "internal-squads")

    async def add_traffic(self, uuid: str, gigabytes: int):
        user = await self.get_user(uuid)
        current_limit = user.get('dataLimit', 0) or 0
        
        bytes_to_add = int(gigabytes * 1024 * 1024 * 1024)
        new_limit = int(current_limit) + bytes_to_add
        
        return await self.update_user(uuid, {"dataLimit": new_limit, "trafficLimitStrategy": "NO_RESET"})

    async def add_user_to_squad(self, user_uuid: str, squad_uuid: str):
        return await self._request("POST", f"internal-squads/{squad_uuid}/bulk-actions/add-users", data={"users": [user_uuid]})

api = RemnawaveAPI()
