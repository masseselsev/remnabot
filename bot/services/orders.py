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

async def fulfill_order(order_id: int, session, payment_id: str = None, note: str = None) -> bool:
    order = await session.get(models.Order, order_id)
    if not order or order.status == models.OrderStatus.PAID:
        return False
        
    if payment_id:
        order.invoice_id = payment_id
    
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
        
        # Override values if Trial
        target_traffic_gb = tariff.traffic_limit_gb
        target_duration_days = tariff.duration_days
        
        if tariff.is_trial:
             from bot.services.settings import SettingsService
             try:
                 settings = await SettingsService.get_trial_settings()
                 target_traffic_gb = settings.get('traffic', target_traffic_gb)
                 target_duration_days = settings.get('days', target_duration_days)
                 # squad uuid is handled below
                 logger.info("using_dynamic_trial_settings", traffic=target_traffic_gb, days=target_duration_days)
             except Exception as e:
                 logger.error("failed_to_load_settings", error=str(e))

        logger.info("applying_tariff_settings", uuid=rw_uuid, tariff_limit=target_traffic_gb, duration=target_duration_days)
        
        # Fetch user state to calculate updates
        rw_user = await api.get_user(rw_uuid)

        # Tags (Spec: single string matching ^[A-Z0-9_]+$)
        current_tag = rw_user.get('tag') or ""
        
        if tariff.is_trial and current_tag == "TRIAL_YES":
             logger.warning("fulfillment_rejected", reason="Trial already used (tag found)")
             return False

        # Prepare update payload
        updates = {
            "onHold": False
        }
        if note:
             updates["description"] = note

        # Tags
        if tariff.is_trial:
             updates["tag"] = "TRIAL_YES"

        # Traffic
        if target_traffic_gb:
             current_limit = rw_user.get('trafficLimitBytes', 0) or rw_user.get('dataLimit', 0) or 0
             bytes_to_add = int(target_traffic_gb * 1024 * 1024 * 1024)
             updates["trafficLimitBytes"] = int(current_limit) + bytes_to_add
             updates["trafficLimitStrategy"] = "NO_RESET"
        
        # Duration
        if target_duration_days:
             current_expire = rw_user.get('expireAt')
             from datetime import datetime, timedelta, timezone
             from dateutil import parser
             
             now = datetime.now(timezone.utc)
             base_dt = now
             
             if current_expire:
                 try:
                     dt = parser.isoparse(current_expire)
                     if dt.tzinfo is None:
                         dt = dt.replace(tzinfo=timezone.utc)
                     if dt > now:
                         base_dt = dt
                 except Exception:
                     pass
             
             new_expire_dt = base_dt + timedelta(days=target_duration_days)
             # Remnawave expects ISO string with Z
             updates["expireAt"] = new_expire_dt.isoformat().replace("+00:00", "Z")

        # Apply updates
        update_resp = await api.update_user(rw_uuid, updates)
        logger.info("settings_applied_successfully", uuid=rw_uuid, response_tags=update_resp.get('tag') or update_resp.get('tags'), updates=updates)

        # 4. Squad Assignment
        # 4. Squad Assignment
        target_squad_uuid = None
        
        if tariff.is_trial:
             from bot.services.settings import SettingsService
             try:
                 target_squad_uuid = await SettingsService.get_setting("trial_squad_uuid")
             except:
                 pass
        elif tariff.squad_uuid:
             target_squad_uuid = tariff.squad_uuid
             
        if target_squad_uuid:
             try:
                await api.add_user_to_squad(rw_uuid, target_squad_uuid)
                logger.info("user_added_to_squad", squad_uuid=target_squad_uuid)
             except Exception as e:
                logger.error("squad_assignment_failed", error=str(e))

        # Trial handled by API tags
        
        order.status = models.OrderStatus.PAID
        await session.commit()
        logger.info("order_fulfilled_complete", order_id=order_id, user_id=user.id)
        return True
        
    except Exception as e:
        logger.error("fulfillment_crashed", order_id=order_id, error=str(e))
        return False
