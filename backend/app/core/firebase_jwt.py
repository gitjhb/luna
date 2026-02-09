"""
Lightweight Firebase JWT Token Verification
Uses PyJWT instead of firebase-admin SDK to reduce bundle size for Vercel.
"""

import os
import jwt
import httpx
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Firebase public keys URL
FIREBASE_KEYS_URL = "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"

# Cache for public keys
_cached_keys: Dict[str, str] = {}
_keys_fetched_at: Optional[datetime] = None
_KEYS_CACHE_TTL = timedelta(hours=6)

FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "luna-f0af5")


async def _fetch_firebase_public_keys() -> Dict[str, str]:
    """Fetch Firebase public keys from Google."""
    global _cached_keys, _keys_fetched_at
    
    # Return cached if fresh
    if _cached_keys and _keys_fetched_at:
        if datetime.utcnow() - _keys_fetched_at < _KEYS_CACHE_TTL:
            return _cached_keys
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(FIREBASE_KEYS_URL)
            response.raise_for_status()
            _cached_keys = response.json()
            _keys_fetched_at = datetime.utcnow()
            logger.debug("Fetched Firebase public keys")
            return _cached_keys
    except Exception as e:
        logger.error(f"Failed to fetch Firebase keys: {e}")
        if _cached_keys:
            return _cached_keys
        raise


async def verify_firebase_token(id_token: str) -> Dict[str, Any]:
    """
    Verify a Firebase ID token and return the decoded payload.
    
    Args:
        id_token: The Firebase ID token from client
        
    Returns:
        Decoded token payload with uid, email, etc.
        
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
        public_keys = await _fetch_firebase_public_keys()
        
        if kid not in public_keys:
            # Keys might have rotated, try refreshing
            global _keys_fetched_at
            _keys_fetched_at = None
            public_keys = await _fetch_firebase_public_keys()
            
            if kid not in public_keys:
                raise ValueError(f"Unknown key ID: {kid}")
        
        # Get the certificate and extract public key
        certificate_pem = public_keys[kid]
        
        # Firebase returns X.509 PEM certificates, need to extract public key
        from cryptography.x509 import load_pem_x509_certificate
        from cryptography.hazmat.backends import default_backend
        
        cert = load_pem_x509_certificate(certificate_pem.encode(), default_backend())
        public_key = cert.public_key()
        
        # Verify and decode the token
        decoded = jwt.decode(
            id_token,
            public_key,
            algorithms=["RS256"],
            audience=FIREBASE_PROJECT_ID,
            issuer=f"https://securetoken.google.com/{FIREBASE_PROJECT_ID}",
        )
        
        # Additional validation
        if not decoded.get("sub"):
            raise ValueError("Token missing subject (uid)")
            
        # Add uid field (Firebase uses 'sub' for user ID)
        decoded["uid"] = decoded["sub"]
        
        return decoded
        
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token: {e}")
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise ValueError(f"Token verification failed: {e}")


def verify_firebase_token_sync(id_token: str) -> Dict[str, Any]:
    """
    Synchronous version using cached keys only.
    Use this only if you're sure keys are cached.
    """
    import asyncio
    return asyncio.get_event_loop().run_until_complete(verify_firebase_token(id_token))
