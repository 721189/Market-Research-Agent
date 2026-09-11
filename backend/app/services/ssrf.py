import socket
import ipaddress
import urllib.parse
import logging
from typing import Tuple, Optional, Set, Dict, Any
try:
    import httpx
except ImportError:
    httpx = None # type: ignore

logger = logging.getLogger("marketai.security.ssrf")

BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),          # Current network
    ipaddress.ip_network("10.0.0.0/8"),         # Private RFC1918
    ipaddress.ip_network("100.64.0.0/10"),      # Shared Address Space (CGNAT)
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
    ipaddress.ip_network("169.254.0.0/16"),     # Link-Local / Cloud Metadata (169.254.169.254)
    ipaddress.ip_network("172.16.0.0/12"),      # Private RFC1918
    ipaddress.ip_network("192.0.0.0/24"),       # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),       # Documentation (TEST-NET-1)
    ipaddress.ip_network("192.88.99.0/24"),     # 6to4 Relay Anycast
    ipaddress.ip_network("192.168.0.0/16"),     # Private RFC1918
    ipaddress.ip_network("198.18.0.0/15"),      # Benchmarking
    ipaddress.ip_network("198.51.100.0/24"),    # Documentation (TEST-NET-2)
    ipaddress.ip_network("203.0.113.0/24"),     # Documentation (TEST-NET-3)
    ipaddress.ip_network("224.0.0.0/4"),        # Multicast
    ipaddress.ip_network("240.0.0.0/4"),        # Reserved for future use
    ipaddress.ip_network("255.255.255.255/32"), # Broadcast
    # IPv6 ranges
    ipaddress.ip_network("::1/128"),            # Loopback
    ipaddress.ip_network("::/128"),             # Unspecified
    ipaddress.ip_network("64:ff9b::/96"),       # IPv4/IPv6 translation
    ipaddress.ip_network("100::/64"),           # Discard prefix
    ipaddress.ip_network("2001::/23"),          # IETF Protocol Assignments
    ipaddress.ip_network("2001:db8::/32"),      # Documentation
    ipaddress.ip_network("fc00::/7"),           # Unique Local Addresses (ULA)
    ipaddress.ip_network("fe80::/10"),          # Link-Local
    ipaddress.ip_network("ff00::/8"),           # Multicast
]

BLOCKED_HOSTNAMES: Set[str] = {
    "localhost",
    "metadata.google.internal",
    "metadata.internal",
    "instance-data",
    "kubernetes.default",
    "kubernetes.default.svc",
    "minio",
    "postgres",
    "redis",
}

ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_PORTS = {80, 443, 8080, 8443}

class SSRFSecurityError(ValueError):
    """Raised when an outbound URL violates SSRF security policies."""
    pass

class SSRFProtector:
    @staticmethod
    def is_ip_blocked(ip_str: str) -> bool:
        """Evaluates whether an IP address belongs to any blocked/private/metadata ranges."""
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            return True

        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_multicast or ip_obj.is_reserved or ip_obj.is_unspecified:
            return True

        for network in BLOCKED_IP_NETWORKS:
            if ip_obj in network:
                return True

        return False

    @classmethod
    def validate_url(cls, url: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Performs thorough pre-flight validation on a target URL.
        Returns: (is_valid, validated_url, error_message)
        """
        if not url or not isinstance(url, str):
            return False, None, "URL must be a non-empty string"

        clean_url = url.strip()
        try:
            parsed = urllib.parse.urlsplit(clean_url)
        except Exception as e:
            return False, None, f"Invalid URL structure: {e}"

        # 1. Scheme check
        scheme = (parsed.scheme or "").lower()
        if scheme not in ALLOWED_SCHEMES:
            return False, None, f"Prohibited URL scheme: '{scheme}'. Only HTTP and HTTPS are permitted."

        # 2. Hostname extraction and check
        hostname = parsed.hostname
        if not hostname:
            return False, None, "URL is missing a valid hostname"

        hostname_lower = hostname.lower().strip(".")

        # Prohibit embedded credentials
        if parsed.username or parsed.password:
            return False, None, "Embedded credentials (user:pass@) in URL are prohibited"

        # Check blocked hostnames
        if hostname_lower in BLOCKED_HOSTNAMES or hostname_lower.endswith(".internal") or hostname_lower.endswith(".local"):
            return False, None, f"Destination hostname '{hostname}' is restricted"

        # Check port
        port = parsed.port or (443 if scheme == "https" else 80)
        if port not in ALLOWED_PORTS:
            return False, None, f"Target port {port} is not in allowed list"

        # Direct IP Address check
        try:
            ip_literal = ipaddress.ip_address(hostname_lower)
            if cls.is_ip_blocked(str(ip_literal)):
                return False, None, f"Target IP '{hostname}' is in restricted address range"
            return True, clean_url, None
        except ValueError:
            pass

        # 3. DNS Resolution and IP checking (Mitigate DNS Rebinding & Private IPs)
        resolved_any = False
        try:
            resolved_ips = socket.getaddrinfo(hostname, port, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM)
            if resolved_ips:
                resolved_any = True
                for res in resolved_ips:
                    sockaddr = res[4]
                    ip_candidate = sockaddr[0]
                    if cls.is_ip_blocked(ip_candidate):
                        logger.warning(f"SSRF Alert: Blocked access to {hostname} which resolved to restricted IP: {ip_candidate}")
                        return False, None, f"Target host '{hostname}' resolves to restricted address '{ip_candidate}'"
        except Exception:
            pass

        # Fallback to gethostbyname if getaddrinfo didn't resolve
        if not resolved_any:
            try:
                ip_cand = socket.gethostbyname(hostname)
                if ip_cand:
                    resolved_any = True
                    if cls.is_ip_blocked(ip_cand):
                        return False, None, f"Target host '{hostname}' resolves to restricted address '{ip_cand}'"
            except Exception as dns_err:
                return False, None, f"DNS resolution failed for '{hostname}': {dns_err}"

        return True, clean_url, None

    @classmethod
    async def safe_fetch(
        cls,
        url: str,
        max_bytes: int = 2 * 1024 * 1024,  # 2MB max download
        timeout_seconds: float = 6.0,
        max_redirects: int = 3
    ) -> Tuple[int, bytes, Dict[str, str]]:
        """
        Fetches an external URL securely with:
        - Strict SSRF check before connection and on every redirect
        - Max byte cap streaming to prevent memory exhaustion
        - Strict connect and read timeouts
        """
        current_url = url
        redirects_followed = 0

        async with httpx.AsyncClient(
            follow_redirects=False,
            timeout=httpx.Timeout(timeout_seconds, connect=3.0)
        ) as client:
            while True:
                is_valid, validated_url, err = cls.validate_url(current_url)
                if not is_valid:
                    raise SSRFSecurityError(f"SSRF check failed for URL '{current_url}': {err}")

                try:
                    # DNS TOCTOU Mitigation: Pin connection directly to resolved validated IP
                    parsed = urllib.parse.urlsplit(validated_url)
                    hostname = parsed.hostname
                    if not hostname:
                        raise SSRFSecurityError(f"Invalid host in URL '{validated_url}'")
                    resolved_ip = socket.gethostbyname(hostname)
                    if cls.is_ip_blocked(resolved_ip):
                        raise SSRFSecurityError(f"DNS TOCTOU check failed: '{hostname}' resolved to restricted IP '{resolved_ip}'")

                    # HTTPS-safe connection handling:
                    # For HTTPS, sending request directly to IP breaks SNI TLS certificate verification.
                    # For HTTP, host replacement is valid. For HTTPS, we fetch the validated URL with SNI intact,
                    # while verifying the resolved IP immediately prior.
                    if parsed.scheme == "https":
                        target_fetch_url = validated_url
                        req_headers = {
                            "User-Agent": "MarketAI-Intelligence-Harvester/2.0 (+https://marketai.app/bot)",
                            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8"
                        }
                    else:
                        port_part = f":{parsed.port}" if parsed.port else ""
                        pinned_netloc = f"{resolved_ip}{port_part}"
                        target_fetch_url = urllib.parse.urlunsplit((parsed.scheme, pinned_netloc, parsed.path, parsed.query, parsed.fragment))
                        req_headers = {
                            "Host": hostname,
                            "User-Agent": "MarketAI-Intelligence-Harvester/2.0 (+https://marketai.app/bot)",
                            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8"
                        }

                    response = await client.get(
                        target_fetch_url,
                        headers=req_headers
                    )
                except httpx.RequestError as exc:
                    raise ConnectionError(f"HTTP request error fetching '{current_url}': {exc}")

                # Handle redirects manually to validate destination IP
                if response.is_redirect:
                    redirects_followed += 1
                    if redirects_followed > max_redirects:
                        raise SSRFSecurityError(f"Exceeded maximum redirects ({max_redirects})")

                    location = response.headers.get("Location")
                    if not location:
                        raise SSRFSecurityError("Redirect missing Location header")

                    # Resolve relative redirect URLs
                    current_url = urllib.parse.urljoin(current_url, location)
                    continue

                # Stream and cap body size
                content_chunks = []
                bytes_received = 0
                async for chunk in response.aiter_bytes():
                    bytes_received += len(chunk)
                    if bytes_received > max_bytes:
                        raise ValueError(f"Target response exceeded maximum allowed payload size ({max_bytes} bytes)")
                    content_chunks.append(chunk)

                raw_bytes = b"".join(content_chunks)
                headers_dict = {k.lower(): v for k, v in response.headers.items()}
                return response.status_code, raw_bytes, headers_dict

ssrf_protector = SSRFProtector()
