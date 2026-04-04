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
        signature = request.query.get("s")
        
        if not all([user_id_str, btn_idx_str, signature]):
            return web.Response(text="Missing parameters", status=400)
            
        user_id = int(user_id_str)
        btn_idx = int(btn_idx_str)
        
        # Verify signature
        if not verify_routing_signature(user_id, btn_idx, signature):
            logger.warning("invalid_routing_signature", user_id=user_id, btn_idx=btn_idx)
            return web.Response(text="Invalid signature", status=403)
            
        # Get button URL
        settings = await SettingsService.get_routing_settings()
        btns = settings.get("buttons") or []
        
        if btn_idx >= len(btns):
            return web.Response(text="Button not found", status=404)
            
        btn = btns[btn_idx]
        title = btn.get("title", "Unknown")
        final_url = btn.get("url")
        
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
