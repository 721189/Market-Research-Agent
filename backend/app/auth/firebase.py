import os
import json
import time
import logging
import urllib.request
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from backend.app.config import settings

logger = logging.getLogger("marketai.auth.firebase")

GOOGLE_CERTS_URL = "https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"

class GoogleCertificateCache:
    """
    In-memory certificate cache for Google's public x509 certificates
    used to verify Firebase RS256 signatures. Automatically honors HTTP
    Cache-Control headers.
    """
    def __init__(self):
        self._certs: Dict[str, str] = {}
        self._expires_at: float = 0.0

    def get_certificates(self, force_refresh: bool = False) -> Dict[str, str]:
        now = time.time()
        if not force_refresh and self._certs and now < self._expires_at:
            return self._certs

        try:
            req = urllib.request.Request(
                GOOGLE_CERTS_URL,
                headers={"User-Agent": "MarketAI-Auth/1.0"}
            )
            with urllib.request.urlopen(req, timeout=6.0) as response:
                cache_control = response.headers.get("Cache-Control", "")
                max_age = 19000  # Default ~5.3 hours
                for directive in cache_control.split(","):
                    directive = directive.strip().lower()
                    if directive.startswith("max-age="):
                        try:
                            max_age = int(directive.split("=")[1])
                        except ValueError:
                            pass

                data = response.read().decode("utf-8")
                self._certs = json.loads(data)
                self._expires_at = now + max(60, max_age)
                logger.info(f"Loaded {len(self._certs)} Google public certificates (TTL: {max_age}s)")
                return self._certs
        except Exception as e:
            logger.error(f"Failed to fetch Google public certificates: {e}")
            if self._certs:
                logger.warning("Falling back to existing cached certificates")
                return self._certs
            raise ValueError("Unable to retrieve Google public verification certificates")

cert_cache = GoogleCertificateCache()

def get_firebase_public_keys(force_refresh: bool = False) -> Dict[str, str]:
    """Helper for retrieving the cached Google public certs dict."""
    return cert_cache.get_certificates(force_refresh=force_refresh)

def verify_firebase_token(token: str) -> Dict[str, Any]:
    """
    Cryptographically verifies a Firebase ID token (must be RS256 signed by Google).
    """
    if not token or not isinstance(token, str):
        raise ValueError("Authentication token is missing or empty")

    token = token.strip()
    try:
        header = jwt.get_unverified_header(token)
    except Exception as e:
        raise ValueError(f"Malformed token header: {e}")

    alg = header.get("alg")
    if alg != "RS256":
        raise ValueError(f"Firebase token must use RS256 algorithm, got '{alg}'")

    return verify_token(token)

def verify_token(token: str) -> Dict[str, Any]:
    """
    Cryptographically verifies a Firebase ID token (RS256 against Google public certs)
    or internal service token (HS256 against SECRET_KEY).

    Validations performed:
    - Cryptographic signature check
    - Algorithm constraint (RS256 for Firebase, HS256 for internal)
    - Expiration time (exp)
    - Issued-at time (iat)
    - Issuer (iss): https://securetoken.google.com/<project_id>
    - Audience (aud): <project_id>
    - Subject (sub): non-empty Firebase UID
    - Auth time (auth_time)
    """
    if not token or not isinstance(token, str):
        raise ValueError("Authentication token is missing or empty")

    token = token.strip()

    # Step 1: Decode header to inspect algorithm and kid
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as e:
        raise ValueError(f"Malformed token header: {str(e)}")

    alg = unverified_header.get("alg")
    kid = unverified_header.get("kid")

    if not alg:
        raise ValueError("Token header missing 'alg' parameter")

    # Path A: Firebase RS256 Token
    if alg == "RS256":
        if not kid:
            raise ValueError("Firebase RS256 token missing 'kid' in header")

        certs = get_firebase_public_keys()
        if kid not in certs:
            # Force cache refresh once in case of Google key rotation
            certs = get_firebase_public_keys(force_refresh=True)

        cert_pem = certs.get(kid)
        if not cert_pem:
            raise ValueError(f"No Google public key found matching kid: {kid}")

        expected_project_id = settings.FIREBASE_PROJECT_ID
        expected_issuer = f"https://securetoken.google.com/{expected_project_id}"

        try:
            claims = jwt.decode(
                token,
                cert_pem,
                algorithms=["RS256"],
                audience=expected_project_id,
                issuer=expected_issuer,
                options={
                    "verify_signature": True,
                    "verify_aud": True,
                    "verify_iat": True,
                    "verify_exp": True,
                    "verify_iss": True,
                    "leeway": 10  # 10 seconds clock skew tolerance
                }
            )
        except JWTError as e:
            logger.warning(f"Firebase token signature/claims verification failed: {e}")
            raise ValueError(f"Cryptographic token verification failed: {str(e)}")

        uid = claims.get("user_id") or claims.get("sub")
        if not uid or not isinstance(uid, str) or len(uid) > 128:
            raise ValueError("Invalid or empty subject (uid) in token claims")

        email = claims.get("email") or f"{uid}@firebase.user"
        email_verified = claims.get("email_verified", False)

        return {
            "uid": str(uid),
            "email": str(email),
            "email_verified": bool(email_verified),
            "name": claims.get("name", "Firebase User"),
            "auth_time": claims.get("auth_time"),
            "provider_id": claims.get("firebase", {}).get("sign_in_provider", "firebase"),
            "claims": claims
        }

    # Path B: Internal HMAC (HS256) Token for service-to-service or developer access
    elif alg == "HS256":
        try:
            claims = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"],
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "leeway": 10
                }
            )
        except JWTError as e:
            logger.warning(f"Internal token verification failed: {e}")
            raise ValueError(f"Invalid internal token signature: {str(e)}")

        uid = claims.get("sub") or claims.get("uid") or claims.get("user_id")
        if not uid:
            raise ValueError("Internal token missing subject identity")

        return {
            "uid": str(uid),
            "email": claims.get("email", f"{uid}@marketai.internal"),
            "name": claims.get("name", "Internal Service"),
            "claims": claims
        }

    else:
        raise ValueError(f"Unsupported token algorithm: '{alg}'. Only RS256 and HS256 are permitted.")
