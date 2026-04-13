from aiohttp import web
import structlog
from bot.database.core import get_session
from bot.database.models import User
from bot.services.settings import SettingsService
from bot.utils.crypto import verify_routing_signature
from sqlalchemy import select, update

logger = structlog.get_logger()

async def handle_routing_redirect(request: web.Request):
    """Handle secure routing redirection and tracking."""
    try:
        user_id_str = request.query.get("u")
        btn_idx_str = request.query.get("i")
        target_url = request.query.get("url")
        signature = request.query.get("s")
        
        if not all([user_id_str, signature]) or (not btn_idx_str and not target_url):
            return web.Response(text="Missing parameters", status=400)
            
        user_id = int(user_id_str)
        
        from bot.utils.crypto import generate_url_signature
        
        final_url = None
        title = "Generic Link"
        
        # 1. Handle Routing Button Redirect
        if btn_idx_str:
            btn_idx = int(btn_idx_str)
            if not verify_routing_signature(user_id, btn_idx, signature):
                logger.warning("invalid_routing_signature", user_id=user_id, btn_idx=btn_idx)
                return web.Response(text="Invalid signature", status=403)
            
            settings = await SettingsService.get_routing_settings()
            btns = settings.get("buttons") or []
            if btn_idx < len(btns):
                btn = btns[btn_idx]
                title = btn.get("title", "Unknown")
                final_url = btn.get("url")
        
        # 2. Handle Generic URL Redirect
        elif target_url:
            expected_sig = generate_url_signature(user_id, target_url)
            from hmac import compare_digest
            if not compare_digest(expected_sig, signature):
                logger.warning("invalid_url_signature", user_id=user_id, url=target_url)
                return web.Response(text="Invalid signature", status=403)
            final_url = target_url
            title = "Subscription Link"
        
        if not final_url:
            return web.Response(text="URL not found", status=404)
            
        # Log click
        logger.info("routing_click", user_id=user_id, button_title=title, url=final_url)
        
        # Update user's last used configuration
        async with get_session() as session:
            await session.execute(
                update(User)
                .where(User.id == user_id)
                .values(last_routing_url=final_url)
            )
            await session.commit()
            
        # Redirect to final destination
        return web.HTTPFound(final_url)
        
    except Exception as e:
        logger.error("routing_redirect_error", error=str(e))
        return web.Response(text="Internal server error", status=500)
