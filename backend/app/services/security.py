import socket
import ipaddress
from urllib.parse import urlparse
from typing import Tuple

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
