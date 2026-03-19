import aiohttp
import ssl
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

    async def _request(self, method: str, endpoint: str, data: dict = None, params: dict = None):
        url = f"{self.base_url}/api/{endpoint.lstrip('/')}"
        
        # Consistent connector across requests for pooling would be better, but we keep isolated for now.
        # We ensure SSL is handled as per env requirements.
        connector = aiohttp.TCPConnector(ssl=False)
        
        logger.debug("remnawave_outgoing", method=method, url=url, params=params)

        async with aiohttp.ClientSession(connector=connector) as session:
            try:
                async with session.request(method, url, headers=self.headers, json=data, params=params) as response:
                    raw_text = await response.text()
                    if not response.ok:
                        logger.error("remnawave_api_fail", 
                                     method=method, 
                                     url=url,
                                     status=response.status, 
                                     body=raw_text)
                    response.raise_for_status()
                    
                    try:
                        res = await response.json()
                    except:
                        # Some endpoints might return empty/text
                        return {"text": raw_text}

                    # Unwrap common wrappers in Remnawave (response or data)
                    if isinstance(res, dict):
                        # Some versions use 'data', some use 'response'
                        return res.get('response') or res.get('data') or res
                    return res

            except Exception as e:
                logger.error("remnawave_api_exception", method=method, endpoint=endpoint, error=str(e))
                raise e

    async def create_user(self, telegram_id: int, username: str):
        from datetime import datetime, timedelta, timezone
        # Spec (CreateUserRequestDto): username (req), expireAt (req), description, tag, telegramId, etc.
        expire_dt = datetime.now(timezone.utc) + timedelta(minutes=5)
        
        data = {
            "username": f"tg_{telegram_id}",
            "telegramId": telegram_id,
            "description": f"User {username} ({telegram_id})",
            "status": "ACTIVE",
            "proxies": {},
            "inbounds": {},
            "expireAt": expire_dt.isoformat().replace("+00:00", "Z")
        }
        return await self._request("POST", "users", data)

    async def create_custom_user(self, username: str, note: str = ""):
        from datetime import datetime, timedelta, timezone
        expire_dt = datetime.now(timezone.utc) + timedelta(minutes=5)
        data = {
            "username": username,
            "status": "ACTIVE",
            "description": note,
            "proxies": {},
            "inbounds": {},
            "expireAt": expire_dt.isoformat().replace("+00:00", "Z")
        }
        return await self._request("POST", "users", data)

    async def get_user_by_telegram_id(self, telegram_id: int):
        # Spec: GET /api/users/by-telegram-id/{telegramId}
        return await self._request("GET", f"users/by-telegram-id/{telegram_id}")

    async def get_user(self, uuid: str):
        # Spec: GET /api/users/{uuid}
        return await self._request("GET", f"users/{uuid}")

    async def update_user(self, uuid: str, data: dict):
        # Spec: PATCH /api/users
        # Body: UpdateUserRequestDto (uuid is used to identify the user)
        payload = data.copy()
        payload['uuid'] = uuid
        return await self._request("PATCH", "users", payload)

    async def add_duration(self, uuid: str, days: int):
        from datetime import datetime, timedelta, timezone
        import dateutil.parser

        user = await self.get_user(uuid)
        current_expire = user.get('expireAt')
        
        if current_expire:
            try:
                expire_dt = dateutil.parser.isoparse(current_expire)
                if expire_dt.tzinfo is None:
                    expire_dt = expire_dt.replace(tzinfo=timezone.utc)
                
                now = datetime.now(timezone.utc)
                if expire_dt < now:
                    expire_dt = now
            except:
                expire_dt = datetime.now(timezone.utc)
        else:
            expire_dt = datetime.now(timezone.utc)
            
        new_expire = expire_dt + timedelta(days=days)
        return await self.update_user(uuid, {"expireAt": new_expire.isoformat().replace("+00:00", "Z")})

    async def get_users(self, search: str = None, limit: int = 100, offset: int = 0):
        # Spec: GET /api/users (supports pagination with size and start)
        params = {
            "size": limit,
            "start": offset
        }
        if search:
            params['search'] = search
        
        return await self._request("GET", "users", params=params)

    async def get_squads(self):
        return await self._request("GET", "internal-squads")

    async def get_squad(self, uuid: str):
        return await self._request("GET", f"internal-squads/{uuid}")

    async def add_traffic(self, uuid: str, gigabytes: int):
        user = await self.get_user(uuid)
        current_limit = user.get('dataLimit', 0) or 0
        
        bytes_to_add = int(gigabytes * 1024 * 1024 * 1024)
        new_limit = int(current_limit) + bytes_to_add
        
        return await self.update_user(uuid, {"dataLimit": new_limit, "trafficLimitStrategy": "NO_RESET"})

    async def add_user_to_squad(self, user_uuid: str, squad_uuid: str):
        # Using PATCH /api/users to update activeInternalSquads as per user suggestion
        # This replaces the faulty bulk-actions endpoint
        logger.info("adding_user_to_squad_via_patch", user_uuid=user_uuid, squad_uuid=squad_uuid)
        return await self.update_user(user_uuid, {
            "activeInternalSquads": [squad_uuid]
        })

    async def get_user_devices(self, user_uuid: str):
        # API seems to ignore userId filter and returns global list.
        # We must filter manually.
        # API uses 'size' param, not 'limit'. default 25.
        res = await self._request("GET", "hwid/devices?size=1000") 
        if res and isinstance(res, dict):
             # Some panels wrap inside another 'devices' or 'response' object
             all_devices = res.get('devices') or res.get('response', {}).get('devices') or []
             if not isinstance(all_devices, list) and isinstance(res, list):
                 all_devices = res
             # Filter strictly by UUID
             if isinstance(all_devices, list):
                return [d for d in all_devices if d.get('userUuid') == user_uuid]
        elif isinstance(res, list):
             return [d for d in res if d.get('userUuid') == user_uuid]
        return []

    async def delete_user_device(self, hwid: str, user_uuid: str):
        # API requires userUuid for deletion validation
        return await self._request("POST", "hwid/devices/delete", {
            "hwid": hwid,
            "userUuid": user_uuid
        })

api = RemnawaveAPI()
