import socket
import ipaddress
import hashlib
import secrets
import datetime
from urllib.parse import urlparse
from typing import Tuple, Optional, Any
try:
    from sqlalchemy.orm import Session
    from backend.app.models.organization import ApiKey, Organization
    from backend.app.models.user import User
except ImportError:
    Session = Any # type: ignore
    ApiKey = Any # type: ignore
    Organization = Any # type: ignore
    User = Any # type: ignore

BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"), # Link-local & cloud metadata (169.254.169.254)
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

class SecurityService:
    @staticmethod
    def hash_key(raw_key: str) -> str:
        """SHA-256 one-way cryptographic hash of secret keys."""
        return hashlib.sha256(raw_key.strip().encode("utf-8")).hexdigest()

    @classmethod
    def generate_api_key(
        cls,
        db: Session,
        org_id: str,
        user_id: str,
        name: str,
        role: str = "member",
        expires_days: Optional[int] = 365
    ) -> Tuple[str, ApiKey]:
        """
        Generates a secure API key with prefix `mk_live_...`.
        Stores only the SHA-256 hash in the database. Returns (raw_key, api_key_model).
        """
        random_entropy = secrets.token_urlsafe(32)
        raw_key = f"mk_live_{random_entropy}"
        key_hash = cls.hash_key(raw_key)
        prefix = f"mk_live_...{raw_key[-6:]}"

        expires_at = None
        if expires_days:
            expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=expires_days)

        api_key = ApiKey(
            key_hash=key_hash,
            key_prefix=prefix,
            name=name,
            role=role,
            user_id=user_id,
            org_id=org_id,
            expires_at=expires_at,
            is_revoked=False
        )
        db.add(api_key)
        db.commit()
        db.refresh(api_key)
        return raw_key, api_key

    @classmethod
    def verify_api_key(cls, db: Session, raw_key: str) -> Optional[Tuple[ApiKey, Organization, User]]:
        """
        Validates API key against database.
        Enforces revocation, expiration, and active tenant status.
        Updates last_used_at on success.
        """
        if not raw_key or not raw_key.startswith("mk_live_"):
            return None

        key_hash = cls.hash_key(raw_key)
        api_key = db.query(ApiKey).filter(
            ApiKey.key_hash == key_hash,
            ApiKey.is_revoked == False
        ).first()

        if not api_key:
            return None

        # Check expiration
        now = datetime.datetime.utcnow()
        if api_key.expires_at and api_key.expires_at < now:
            return None

        # Check tenant status
        org = db.query(Organization).filter(Organization.id == api_key.org_id).first()
        if not org or org.status != "active":
            return None

        user = db.query(User).filter(User.id == api_key.user_id).first()
        if not user:
            return None

        # Update last_used_at
        api_key.last_used_at = now
        db.commit()

        return api_key, org, user

    @classmethod
    def revoke_api_key(cls, db: Session, key_id: str, org_id: str) -> bool:
        """Revokes an API key for a tenant."""
        key = db.query(ApiKey).filter(ApiKey.id == key_id, ApiKey.org_id == org_id).first()
        if key:
            key.is_revoked = True
            db.commit()
            return True
        return False

    @staticmethod
    def validate_url_safe_for_ssrf(url: str) -> Tuple[bool, str]:
        """
        Validates whether a URL is safe to fetch externally and does not target
        private infrastructure, cloud metadata endpoints, or loopback interfaces.
        """
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return False, "Unsupported URL scheme (only http/https allowed)"

            hostname = parsed.hostname
            if not hostname:
                return False, "Invalid URL hostname"

            # Resolve DNS
            addr_info = socket.getaddrinfo(hostname, None)
            if not addr_info:
                return False, "Could not resolve hostname"

            for entry in addr_info:
                ip_str = entry[4][0]
                ip_obj = ipaddress.ip_address(ip_str)

                # Check if IP falls within any blocked network
                for network in BLOCKED_IP_NETWORKS:
                    if ip_obj in network:
                        return False, f"URL resolves to disallowed address range: {ip_str}"

            return True, ""
        except Exception as e:
            return False, f"SSRF validation failed: {str(e)}"

    @staticmethod
    def wrap_untrusted_content(content: str) -> str:
        """
        Wraps external untrusted text inside strict structural boundaries
        to prevent prompt injection hijacking.
        """
        # Strip null bytes and normalize
        sanitized = content.replace("\x00", "").strip()
        # Protect against delimiter breakout
        sanitized = sanitized.replace("</UNTRUSTED_EXTERNAL_EVIDENCE>", "[ESCAPED_DELIMITER]")
        
        return (
            "<UNTRUSTED_EXTERNAL_EVIDENCE>\n"
            f"{sanitized}\n"
            "</UNTRUSTED_EXTERNAL_EVIDENCE>"
        )

security_service = SecurityService()
