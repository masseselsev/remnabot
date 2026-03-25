import aiohttp
import structlog

logger = structlog.get_logger()

async def get_crypto_link(url: str) -> str:
    """
    Encrypts a URL using Happ Cryptolink API.
    """
    api_url = "https://crypto.happ.su/api-v2.php"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json={"url": url}, timeout=10) as resp:
                if resp.status == 200:
                    encrypted_url = await resp.text()
                    if encrypted_url.startswith("http"):
                        return encrypted_url.strip()
                    else:
                        logger.warning("crypto_api_unexpected_response", response=encrypted_url)
                else:
                    logger.warning("crypto_api_error_status", status=resp.status)
    except Exception as e:
        logger.error("crypto_api_failed", error=str(e), url=url)
    
    return url # Fallback to original if API fails
