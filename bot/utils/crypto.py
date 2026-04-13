import hmac
import hashlib
import aiohttp
import structlog
from bot.config import config

logger = structlog.get_logger()
SECRET_KEY = config.bot_token.get_secret_value()

async def get_crypto_link(url: str) -> str:
    """
    Encrypts a URL using Happ Cryptolink API.
    Used for general link short-circuiting and obfuscation.
    """
    api_url = "https://crypto.happ.su/api-v2.php"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json={"url": url}, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    encrypted_url = data.get("encrypted_link")
                    if encrypted_url:
                        return encrypted_url.strip()
                    else:
                        logger.warning("crypto_api_missing_key", response=await resp.text())
                else:
                    logger.warning("crypto_api_error_status", status=resp.status)
    except Exception as e:
        logger.error("crypto_api_failed", error=str(e), url=url)
    
    return url # Fallback to original if API fails

def generate_routing_signature(user_id: int, btn_index: int) -> str:
    """Generate a signature for the routing redirect URL."""
    msg = f"{user_id}:{btn_index}".encode()
    return hmac.new(SECRET_KEY.encode(), msg, hashlib.sha256).hexdigest()[:16]

def verify_routing_signature(user_id: int, btn_index: int, signature: str) -> bool:
    """Verify if the provided signature is valid."""
    expected = generate_routing_signature(user_id, btn_index)
    return hmac.compare_digest(expected, signature)

def generate_url_signature(user_id: int, url: str) -> str:
    """Generate a signature for a generic URL redirect."""
    msg = f"{user_id}:{url}".encode()
    return hmac.new(SECRET_KEY.encode(), msg, hashlib.sha256).hexdigest()[:16]

def get_routing_redirect_url(user_id: int, btn_index: int) -> str:
    """Generate the full routing redirect URL with signature for tracking."""
    base_url = config.webhook_url.rstrip("/")
    # We use a simple path like /r for redirection
    sig = generate_routing_signature(user_id, btn_index)
    return f"{base_url}/r?u={user_id}&i={btn_index}&s={sig}"

def get_generic_redirect_url(user_id: int, target_url: str) -> str:
    """Generate a full signed redirect URL for a generic target."""
    import urllib.parse
    base_url = config.webhook_url.rstrip("/")
    sig = generate_url_signature(user_id, target_url)
    safe_url = urllib.parse.quote(target_url, safe='')
    return f"{base_url}/r?u={user_id}&url={safe_url}&s={sig}"
