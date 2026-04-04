import hmac
import hashlib
from bot.config import config

SECRET_KEY = config.bot_token.get_secret_value()

def generate_routing_signature(user_id: int, btn_index: int) -> str:
    """Generate a signature for the routing redirect URL."""
    msg = f"{user_id}:{btn_index}".encode()
    return hmac.new(SECRET_KEY.encode(), msg, hashlib.sha256).hexdigest()[:16]

def verify_routing_signature(user_id: int, btn_index: int, signature: str) -> bool:
    """Verify if the provided signature is valid."""
    expected = generate_routing_signature(user_id, btn_index)
    return hmac.compare_digest(expected, signature)

def get_routing_redirect_url(user_id: int, btn_index: int) -> str:
    """Generate the full redirect URL with signature."""
    base_url = config.webhook_url.rstrip("/")
    # We use a simple path like /r for redirection
    sig = generate_routing_signature(user_id, btn_index)
    return f"{base_url}/r?u={user_id}&i={btn_index}&s={sig}"
