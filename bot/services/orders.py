from bot.database import models
from bot.database.core import async_session
from bot.services.remnawave import api
from sqlalchemy import select
from datetime import datetime
import structlog

logger = structlog.get_logger()

async def create_order(user_id: int, tariff_id: int, amount: float, provider: str, session) -> models.Order:
    order = models.Order(
        user_id=user_id,
        tariff_id=tariff_id,
        amount=amount,
        payment_provider=provider,
        status=models.OrderStatus.PENDING
    )
    session.add(order)
    await session.commit()
    return order

async def fulfill_order(order_id: int, session) -> bool:
    order = await session.get(models.Order, order_id)
    if not order or order.status == models.OrderStatus.PAID:
        return False
    
    user = await session.get(models.User, order.user_id)
    tariff = await session.get(models.Tariff, order.tariff_id)
    
    logger.info("fulfillment_started", order_id=order_id, user_id=user.id, tariff=tariff.name, is_trial=tariff.is_trial)
    
    try:
        # Check if user exists in Remnawave
        rw_uuid = user.remnawave_uuid
        
        # 1. Self-healing check
        if rw_uuid:
             logger.info("verifying_user_existence", uuid=rw_uuid)
             try:
                 await api.get_user(rw_uuid)
                 logger.info("user_verified_in_remnawave", uuid=rw_uuid)
             except Exception:
                 logger.info("user_not_found_on_remote", details="Local UUID invalid or user deleted. clearing_local_data_to_reprovision")
                 rw_uuid = None
                 user.remnawave_uuid = None

        # 2. User Provisioning
        if not rw_uuid:
            logger.info("provisioning_new_user", username=f"tg_{user.id}")
            try:
                resp = await api.create_user(user.id, user.username)
                if resp:
                    if 'response' in resp:
                        rw_uuid = resp['response'].get('uuid') or resp['response'].get('id')
                    else:
                        rw_uuid = resp.get('uuid') or resp.get('id')
                    
                    user.remnawave_uuid = rw_uuid
                    logger.info("user_created_successfully", uuid=rw_uuid)
            except Exception as e:
                # Creation failed, might already exist
                logger.info("user_creation_failed_checking_existing", error=str(e))
                
                # Recover
                logger.info("searching_user_by_username", username=f"tg_{user.id}")
                users = await api.get_users(search=f"tg_{user.id}")

                found_user = None
                # Handle various API response formats
                candidates = []
                if isinstance(users, list): candidates = users
                elif isinstance(users, dict):
                     if 'users' in users: candidates = users['users']
                     elif 'data' in users: candidates = users['data']
                     elif 'items' in users: candidates = users['items']
                     elif 'response' in users and 'users' in users['response']: candidates = users['response']['users']
                
                for u in candidates:
                     if u.get('username') == f"tg_{user.id}":
                         found_user = u
                         break
                
                if found_user:
                    rw_uuid = found_user.get('uuid') or found_user.get('id')
                    user.remnawave_uuid = rw_uuid
                    logger.info("user_recovered_successfully", uuid=rw_uuid, details="Found existing user, relinking.")
                else:
                    logger.error("provisioning_failed_fatal", user_id=user.id, details="Could not create nor find user.")
                    return False
            
            if not rw_uuid:
                 logger.error("provisioning_failed_no_uuid", response="API response missing UUID")
                 return False

        # 3. Applying Settings (Tariff logic)
        logger.info("applying_tariff_settings", uuid=rw_uuid, tariff_limit=tariff.traffic_limit_gb, duration=tariff.duration_days)
        
        # Optimization: Fetch user ONCE and calculate all updates
        rw_user = await api.get_user(rw_uuid)
        current_tags = rw_user.get('tag') or ""
        
        if tariff.is_trial and "TRIAL_YES" in current_tags:
             logger.warning("fulfillment_rejected", reason="Trial already used (tag found)")
             return False

        # Prepare update payload
        updates = {
            "onHold": False
        }

        # Tags
        if tariff.is_trial:
             if "TRIAL_YES" not in current_tags:
                 updates["tag"] = f"{current_tags},TRIAL_YES" if current_tags else "TRIAL_YES"
        
        # Traffic
        if tariff.traffic_limit_gb:
             current_limit = rw_user.get('trafficLimitBytes', 0) or 0
             bytes_to_add = int(tariff.traffic_limit_gb * 1024 * 1024 * 1024)
             updates["trafficLimitBytes"] = int(current_limit) + bytes_to_add
             updates["trafficLimitStrategy"] = "NO_RESET"
        
        # Duration
        if tariff.duration_days:
             current_expire = rw_user.get('expireAt')
             import time
             from datetime import datetime, timedelta
             from dateutil import parser
             
             now_ts = time.time()
             base_ts = now_ts
             
             if current_expire:
                 try:
                     dt = parser.isoparse(current_expire)
                     ts = dt.timestamp()
                     if ts > now_ts:
                         base_ts = ts
                 except Exception:
                     pass
             
             new_expire_dt = datetime.fromtimestamp(base_ts) + timedelta(days=tariff.duration_days)
             updates["expireAt"] = new_expire_dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        # Apply updates
        await api.update_user(rw_uuid, updates)
        logger.info("settings_applied_successfully", uuid=rw_uuid)

        # 4. Squad Assignment
        if tariff.is_trial:
             kv = await session.get(models.KeyValue, "trial_squad_uuid")
             trial_squad_uuid = kv.value if kv else None
             
             if not trial_squad_uuid:
                 logger.error("squad_assignment_skipped", reason="Trial squad UUID not configured")
             else:
                 try:
                    await api.add_user_to_squad(rw_uuid, trial_squad_uuid)
                    logger.info("user_added_to_trial_squad", squad_uuid=trial_squad_uuid)
                 except Exception as e:
                    logger.error("squad_assignment_failed", error=str(e))

        user.is_trial_used = True
        
        order.status = models.OrderStatus.PAID
        await session.commit()
        logger.info("order_fulfilled_complete", order_id=order_id, user_id=user.id)
        return True
        
    except Exception as e:
        logger.error("fulfillment_crashed", order_id=order_id, error=str(e))
        return False
