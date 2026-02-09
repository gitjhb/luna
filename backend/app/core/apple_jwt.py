"""
Apple Identity Token Verification
Verifies Apple Sign In tokens directly without Firebase.
"""

import jwt
import httpx
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Apple public keys URL
APPLE_KEYS_URL = "https://appleid.apple.com/auth/keys"

# Cache for public keys
_cached_keys: Dict[str, Any] = {}
_keys_fetched_at: Optional[datetime] = None
_KEYS_CACHE_TTL = timedelta(hours=24)

# Your app's bundle ID (audience)
APPLE_BUNDLE_ID = "com.luna.companion"


async def _fetch_apple_public_keys() -> Dict[str, Any]:
    """Fetch Apple's public keys."""
    global _cached_keys, _keys_fetched_at
    
    # Return cached if fresh
    if _cached_keys and _keys_fetched_at:
        if datetime.utcnow() - _keys_fetched_at < _KEYS_CACHE_TTL:
            return _cached_keys
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(APPLE_KEYS_URL)
            response.raise_for_status()
            data = response.json()
            # Convert to dict keyed by 'kid'
            _cached_keys = {key["kid"]: key for key in data.get("keys", [])}
            _keys_fetched_at = datetime.utcnow()
            logger.debug("Fetched Apple public keys")
            return _cached_keys
    except Exception as e:
        logger.error(f"Failed to fetch Apple keys: {e}")
        if _cached_keys:
            return _cached_keys
        raise


def _jwk_to_pem(jwk: Dict[str, Any]) -> str:
    """Convert JWK to PEM format."""
    from jwt.algorithms import RSAAlgorithm
    return RSAAlgorithm.from_jwk(jwk)


async def verify_apple_token(id_token: str) -> Dict[str, Any]:
    """
    Verify an Apple Identity Token.
    
    Args:
        id_token: The identityToken from Apple Sign In
        
    Returns:
        Decoded token payload with sub (user ID), email, etc.
        
    Raises:
        ValueError: If token is invalid
    """
    try:
        # Get the key ID from token header
        unverified_header = jwt.get_unverified_header(id_token)
        kid = unverified_header.get("kid")
        
        if not kid:
            raise ValueError("Token missing key ID")
        
        # Fetch public keys
        public_keys = await _fetch_apple_public_keys()
        
        if kid not in public_keys:
            # Keys might have rotated, try refreshing
            global _keys_fetched_at
            _keys_fetched_at = None
            public_keys = await _fetch_apple_public_keys()
            
            if kid not in public_keys:
                raise ValueError(f"Unknown Apple key ID: {kid}")
        
        # Get the public key
        jwk = public_keys[kid]
        public_key = _jwk_to_pem(jwk)
        
        # Verify and decode the token
        decoded = jwt.decode(
            id_token,
            public_key,
            algorithms=["RS256"],
            audience=APPLE_BUNDLE_ID,
            issuer="https://appleid.apple.com",
        )
        
        # Validate required fields
        if not decoded.get("sub"):
            raise ValueError("Token missing subject (user ID)")
        
        # Add uid field for consistency with Firebase tokens
        decoded["uid"] = decoded["sub"]
        
        return decoded
        
    except jwt.ExpiredSignatureError:
        raise ValueError("Apple token has expired")
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid Apple token: {e}")
    except Exception as e:
        logger.error(f"Apple token verification failed: {e}")
        raise ValueError(f"Apple token verification failed: {e}")


def is_apple_token(id_token: str) -> bool:
    """Check if a token is from Apple (vs Firebase)."""
    try:
        # Decode without verification to check issuer
        unverified = jwt.decode(id_token, options={"verify_signature": False})
        return unverified.get("iss") == "https://appleid.apple.com"
    except:
        return False
