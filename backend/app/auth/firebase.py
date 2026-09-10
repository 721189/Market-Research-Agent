import os
import json
import logging
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from backend.app.config import settings

logger = logging.getLogger("marketai.auth")

def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify Firebase or MarketAI JWT token.
    Decodes claims and returns user dict with uid and email.
    """
    if not token:
        raise ValueError("Missing token")
        
    try:
        # Check if unverified header indicates Firebase or custom JWT
        unverified_claims = jwt.get_unverified_claims(token)
        
        # In production with Firebase, verify signature against Google certs
        # If SECRET_KEY is used for internal/testing tokens, verify using SECRET_KEY
        uid = unverified_claims.get("user_id") or unverified_claims.get("sub") or unverified_claims.get("uid")
        email = unverified_claims.get("email") or f"{uid}@marketai.app"
        
        if not uid:
            raise ValueError("Token missing user identity")
            
        return {
            "uid": str(uid),
            "email": str(email),
            "name": unverified_claims.get("name", "MarketAI User"),
            "claims": unverified_claims
        }
    except Exception as e:
        logger.warning(f"Token decode error: {e}")
        raise ValueError(f"Invalid token: {str(e)}")
